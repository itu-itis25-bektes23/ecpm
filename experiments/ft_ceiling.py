"""Information ceiling per condition, computed from the payload files.

A second implementation of the question `ecpm_baseline.py` answers, written
independently for the finetuning arm and kept separate on purpose. The two
agree that deterministic silent break is solved by counting and that the
stochastic conditions differ in how much room a model has. A number reached
twice by different routes is a different kind of number, so these are not
merged. See the "independent check on the ceiling" section of the README.

Where they differ: `ecpm_baseline.py` answers all four probes by arithmetic
over the prompt view and is the null model every result is read against.
This computes localization only, and adds an exact posterior under the true
generative process, which bounds any method that reads only the counts.

  chance         1 / number of legal pairs
  rule_drop      largest drop in visible success rate, tie-aware
  rule_deadB     the only pair that never succeeds in period B
  bayes_flat     exact posterior argmax, uniform prior over legal pairs.
                 The ceiling for a localizer that reads only counts.
  bayes_route    the same posterior with the prior restricted to the optimal
                 route estimated from period A alone. Uses structure as well,
                 so it is not an upper bound; it shows counts alone are not
                 the limit.

Reading. A model at or below rule_drop has not beaten counting. Between
rule_drop and bayes_flat it extracts more from the counts than the rule.
Above bayes_flat it must be using structure.

Note `redirect` is not covered: it preserves every success rate, so every
rule here is blind to it by construction, which is the point of that
condition. `experiments/baseline_k_sweep.py` measures it.

Usage, from the repository root:

  python3 experiments/gen_payloads.py payloads_deg --seeds 0-79 \
      --condition degradation --stochastic
  python3 experiments/ft_ceiling.py payloads_deg
"""


from __future__ import annotations

import collections
import glob
import heapq
import json
import math
import os
import re
import sys

TRIPLE = re.compile(r"\(([A-Z]), (a\d+), ([A-Z])\)")
P_LO, P_HI = 0.60, 0.95      # resource_mdp p_range for healthy links
FACTOR = 0.5                 # degradation_factor
GRID = 200
_PS = [P_LO + (P_HI - P_LO) * (i + 0.5) / GRID for i in range(GRID)]


def blocks(evidence):
    head, rest = evidence.split("Observations, period A:", 1)
    a, b = rest.split("Observations, period B:", 1)
    return a, b


def observe(text):
    cnt = collections.defaultdict(lambda: [0, 0])
    dest = collections.defaultdict(collections.Counter)
    for u, a, v in TRIPLE.findall(text):
        cnt[(u, a)][1] += 1
        if v != u:                       # a self-loop is a failed attempt
            cnt[(u, a)][0] += 1
            dest[(u, a)][v] += 1
    return ({k: tuple(v) for k, v in cnt.items()},
            {k: c.most_common(1)[0][0] for k, c in dest.items()})


def _binom(n, s, p):
    return math.comb(n, s) * (p ** s) * ((1 - p) ** (n - s))


def _marginal(sa, na, sb, nb, degraded):
    tot = 0.0
    for p in _PS:
        q = max(0.05, p * FACTOR) if degraded else p
        tot += _binom(na, sa, p) * _binom(nb, sb, q)
    return tot / GRID


def posterior(ca, cb, pairs):
    out = {}
    for i in pairs:
        sa, na = ca.get(i, (0, 0))
        sb, nb = cb.get(i, (0, 0))
        if na == 0 or nb == 0:
            continue
        den = _marginal(sa, na, sb, nb, False)
        out[i] = (_marginal(sa, na, sb, nb, True) / den) if den else 0.0
    return out


def estimated_route(ca, da, start, goal):
    """Min expected-cost route on the graph estimated from period A.
    Taking (u, a) costs attempts/successes and lands on the majority
    destination."""
    adj = collections.defaultdict(list)
    for (u, a), (s, n) in ca.items():
        v = da.get((u, a))
        if v is not None and s > 0:
            adj[u].append((a, v, n / s))
    dist, prev, pq = {start: 0.0}, {}, [(0.0, start)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, math.inf) + 1e-12:
            continue
        if u == goal:
            break
        for a, v, w in adj[u]:
            if d + w < dist.get(v, math.inf) - 1e-12:
                dist[v], prev[v] = d + w, (u, a)
                heapq.heappush(pq, (d + w, v))
    if goal not in prev:
        return None
    out, cur = [], goal
    while cur in prev:
        u, a = prev[cur]
        out.append((u, a))
        cur = u
    return out[::-1]


def evaluate(directory):
    paths = sorted(glob.glob(os.path.join(directory, "payload_seed*.json")),
                   key=lambda p: int(re.search(r"seed(\d+)", p).group(1)))
    if not paths:
        raise SystemExit(f"no payloads in {directory}")
    hit = collections.Counter()
    node_hit = collections.Counter()
    n, npairs, on_route = 0, [], 0
    cond = mode = None
    for path in paths:
        pay = json.load(open(path))
        cond = pay["condition"]
        mode = "det" if pay["deterministic"] else "sto"
        target = pay["facts"]["target_pair"]
        if target is None:
            continue                      # no_change has nothing to localize
        gold = tuple(target)
        ev = pay["single"][pay["probes"][0]]
        a_txt, b_txt = blocks(ev)
        ca, da = observe(a_txt)
        cb, _ = observe(b_txt)
        pairs = sorted(set(ca) | set(cb))
        n += 1
        npairs.append(len(pairs))

        def rate(c, p):
            s, m = c.get(p, (0, 0))
            return s / m if m else 0.0

        drop = max(pairs, key=lambda p: (rate(ca, p) - rate(cb, p), p))
        dead = [p for p in pairs if rate(cb, p) == 0]
        deadb = dead[0] if len(dead) == 1 else None
        post = posterior(ca, cb, pairs)
        flat = max(post, key=lambda p: (post[p], p)) if post else None
        route = estimated_route(ca, da, pay["facts"]["start"],
                                pay["facts"]["goal"])
        cand = [p for p in (route or []) if p in post] or list(post)
        rt = max(cand, key=lambda p: (post[p], p)) if cand else None
        on_route += bool(route and gold in route)

        for name, pick in (("rule_drop", drop), ("rule_deadB", deadb),
                           ("bayes_flat", flat), ("bayes_route", rt)):
            hit[name] += pick == gold
            if pick is not None and pick[0] == gold[0]:
                node_hit[name] += 1
    mp = sum(npairs) / len(npairs) if npairs else 1
    print(f"\n{directory}  condition={cond} mode={mode} n={n}")
    print(f"  chance                {1 / mp:.3f}")
    for name in ("rule_drop", "rule_deadB", "bayes_flat", "bayes_route"):
        print(f"  {name:<20}  {hit[name]}/{n} = {hit[name] / n:.2f}"
              f"   (node-level {node_hit[name] / n:.2f})")
    print(f"  target on the estimated period-A route: {on_route}/{n}")
    print(f"  headroom above the rule: "
          f"{(hit['bayes_flat'] - hit['rule_drop']) / n:+.2f} "
          f"(counts only), "
          f"{(hit['bayes_route'] - hit['rule_drop']) / n:+.2f} "
          f"(counts + structure)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    for d in sys.argv[1:]:
        evaluate(d)

"""Evidence-only baseline for the ECPM probes (no model, no reasoning).

Why this exists
---------------
The methodology fixes two rules that need a non-reasoning reference point:

  * H1/H3 are scored *over the instances the baseline also solves*.
  * "models cannot localize" is an inadmissible claim unless the
    baseline reaches >= 0.8 on the same instances.

Without an implementation those rules cannot be applied, and a model
result has no denominator. This module supplies that reference.

What it is
----------
A counter, not a planner-with-insight. It sees exactly what the model
sees -- a `prompt_view()` projection at the same rendering and the same
per-pair budget -- and answers the same four probes by arithmetic:

  detection ....... any pair left the menu, or the largest success-rate
                    swing between periods clears `delta_threshold`
  localization .... the pair with the largest |rate_post - rate_pre|
                    (a menu removal wins outright: it is not a rate
                    question)
  preservation .... of the queried pairs, exactly the localized one is
                    reported changed
  adaptation ...... shortest expected-cost route under the *observed*
                    post-period rates and observed destinations,
                    1/p_hat per hop (Dijkstra)

Deliberately excluded: any use of `counts_*`, `world_*`, `change`,
`oracle`, or `evaluator_only`. The baseline is handed a prompt view and
nothing else, so it cannot outperform the evidence by construction.
`assert_prompt_safe()` enforces this at runtime.

Reading the output
------------------
A high baseline score means the change is *visible in the logs* --
the instance carries no headroom, and a model matching it has
demonstrated nothing. A low baseline score means the evidence is
genuinely ambiguous, and a model failing there has not made a mistake.
Both directions are informative; neither is a model result.

stdlib only, consistent with the rest of the frozen tree.
"""

import heapq
import json
import math
import re
from collections import defaultdict

SCHEMA_VERSION = "2.1"

# Fields that would leak ground truth. A prompt view never carries them.
FORBIDDEN_KEYS = ("counts_pre", "counts_post", "world_pre", "world_post",
                  "change", "oracle", "evaluator_only", "seeds")

# Renderings the baseline can read. F3_stats gives rates but no
# destinations, so it cannot support the adaptation probe.
EVENT_RENDERINGS = ("F2_ordered", "F2_shuffled")
STATS_RENDERING = "F3_stats"

_EVENT_RE = re.compile(r"\(\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)\s*\)")
_STATS_RE = re.compile(
    r"^(\w+)\s+(\w+):\s*(\d+)\s+attempts,\s*(\d+)\s+delivered")

# Swing a pair must show before the baseline calls a change.
#
# Calibrated on stochastic seeds 1-30 (see experiments/baseline_k_sweep.py)
# by maximising the gap between the hit rate on silent_break/degradation
# and the false-alarm rate on no_change. A single fixed threshold does
# not work: the noise floor shrinks as K grows, so a value tuned at
# K=20 is far too strict at K=10 and vice versa.
#
#   K=5  -> no usable operating point exists. The best achievable gap is
#           0.11, because at five attempts a healthy link swings as hard
#           as a broken one. Detection at K=5 in stochastic mode is not
#           measurable from the evidence, and the baseline says so.
#   K=10 -> 0.50 (false alarms 0.17, silent break 0.96, degradation 0.61)
#   K=20 -> 0.30 (false alarms 0.20, silent break 1.00, degradation 0.91)
#
# Deterministic mode needs no threshold in practice: a broken pair is the
# only one that ever fails, so any positive value separates cleanly.
CALIBRATED_DELTA_THRESHOLD = {5: 0.70, 10: 0.50, 20: 0.30}
DEFAULT_DELTA_THRESHOLD = 0.50

# K values where *stochastic* detection has no usable operating point.
# Deterministic mode is unaffected: a broken pair is the only one that
# ever fails, so false alarms are 0.00 at every K measured.
UNRELIABLE_DETECTION_K = (5,)


def looks_deterministic(pre_stats, post_stats):
    """True when every observed rate is exactly 0 or 1.

    A prompt view does not carry the mode -- deliberately, since the
    model is not told either. But deterministic evidence is
    self-identifying: p = 1 links always deliver and a broken link never
    does, so no intermediate rate can appear. With at least a few pairs
    observed, a false positive would require every stochastic link to
    land on a clean 0 or 1 by chance, which is why the check also
    requires a minimum number of observations.
    """
    rates = [rate(e) for e in list(pre_stats.values()) + list(post_stats.values())]
    rates = [r for r in rates if r is not None]
    if len(rates) < 6:
        return False
    return all(r in (0.0, 1.0) for r in rates)


def default_threshold(budget_per_pair):
    """Calibrated threshold for a budget, falling back to the nearest K."""
    if budget_per_pair in CALIBRATED_DELTA_THRESHOLD:
        return CALIBRATED_DELTA_THRESHOLD[budget_per_pair]
    if not budget_per_pair:
        return DEFAULT_DELTA_THRESHOLD
    nearest = min(CALIBRATED_DELTA_THRESHOLD,
                  key=lambda k: abs(k - budget_per_pair))
    return CALIBRATED_DELTA_THRESHOLD[nearest]


class EvidenceLeak(Exception):
    """Raised when the baseline is handed more than a prompt view."""


def assert_prompt_safe(pv):
    """Fail loudly if `pv` carries anything the model could not see."""
    leaked = [k for k in FORBIDDEN_KEYS if k in pv]
    if leaked:
        raise EvidenceLeak(
            "baseline received evaluator-only fields: "
            + ", ".join(sorted(leaked))
            + ". Pass resource_mdp.prompt_view(record, ...), not the record."
        )
    if "evidence" not in pv:
        raise EvidenceLeak("prompt view has no 'evidence' block")


# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------

def parse_events(text):
    """`(node, action, dest)` tuples -> list of (node, action, dest).

    A row whose destination equals its origin is a drop, matching the
    renderer: failure leaves the packet in place.
    """
    return [(m.group(1), m.group(2), m.group(3))
            for m in _EVENT_RE.finditer(text)]


def parse_stats(text):
    """F3_stats lines -> {(node, action): {attempts, delivered}}."""
    out = {}
    for line in text.splitlines():
        m = _STATS_RE.match(line.strip())
        if m:
            node, action, attempts, delivered = m.groups()
            out[(node, action)] = {"attempts": int(attempts),
                                   "delivered": int(delivered)}
    return out


def tally(events):
    """Events -> per-pair attempts/successes and observed destinations.

    `dests` is a Counter per pair: a pair can show more than one
    destination only under a `redirect`-style edit, so keeping the full
    distribution (rather than a single winner) leaves room for that
    condition without a reader change.
    """
    stats = defaultdict(lambda: {"attempts": 0, "delivered": 0})
    dests = defaultdict(lambda: defaultdict(int))
    for node, action, dest in events:
        pair = (node, action)
        stats[pair]["attempts"] += 1
        if dest != node:
            stats[pair]["delivered"] += 1
            dests[pair][dest] += 1
    return dict(stats), {k: dict(v) for k, v in dests.items()}


def rate(entry):
    """Observed success rate, or None when the pair was never attempted."""
    if not entry or entry["attempts"] == 0:
        return None
    return entry["delivered"] / entry["attempts"]


def read_periods(pv):
    """Prompt view -> (pre_stats, post_stats, pre_dests, post_dests).

    Works from either an event rendering or F3_stats; destinations come
    back empty for the latter, which disables adaptation.
    """
    assert_prompt_safe(pv)
    rendering = pv.get("rendering")
    evidence = pv["evidence"]
    for period in ("pre", "post"):
        if period not in evidence:
            raise ValueError(
                f"prompt view is missing the '{period}' period; the baseline "
                "compares two periods and cannot run on one"
            )

    if rendering in EVENT_RENDERINGS:
        pre_stats, pre_dests = tally(parse_events(evidence["pre"]))
        post_stats, post_dests = tally(parse_events(evidence["post"]))
        return pre_stats, post_stats, pre_dests, post_dests

    if rendering == STATS_RENDERING:
        return parse_stats(evidence["pre"]), parse_stats(evidence["post"]), {}, {}

    raise ValueError(
        f"rendering {rendering!r} is not machine-readable by the baseline; "
        f"use one of {EVENT_RENDERINGS + (STATS_RENDERING,)}"
    )


# --------------------------------------------------------------------------
# probes
# --------------------------------------------------------------------------

def menu_removals(pv):
    """Pairs present in the pre-period menu and absent from the post one.

    This is the `hard_removal` giveaway: it needs no evidence at all,
    which is exactly why hard_removal is a control rather than a test.
    """
    pre = pv.get("legal_actions_pre") or {}
    post = pv.get("legal_actions_post") or {}
    removed = []
    for node, actions in pre.items():
        still = set(post.get(node, ()))
        removed.extend((node, a) for a in actions if a not in still)
    return sorted(removed)


def rank_pairs(pre_stats, post_stats):
    """Pairs ordered by |rate_post - rate_pre|, largest swing first.

    Pairs unobserved in either period are skipped: an absent rate is not
    a drop to zero, and treating it as one would manufacture detections.
    """
    ranked = []
    for pair in sorted(set(pre_stats) | set(post_stats)):
        r_pre, r_post = rate(pre_stats.get(pair)), rate(post_stats.get(pair))
        if r_pre is None or r_post is None:
            continue
        ranked.append({
            "pair": pair,
            "rate_pre": r_pre,
            "rate_post": r_post,
            "delta": r_post - r_pre,
            "abs_delta": abs(r_post - r_pre),
        })
    ranked.sort(key=lambda d: (-d["abs_delta"], d["pair"]))
    return ranked


def plan_route(dests, stats, start, goal, legal_actions):
    """Cheapest observed route start -> goal, 1/p_hat per hop (Dijkstra).

    Uses only what the log showed: a link the evidence never exercised
    does not exist for the baseline, and a pair with zero observed
    successes has infinite cost, so a silent break is routed around
    without ever being *named*. That gap -- routing around a break the
    baseline cannot localize -- is the same dissociation the ICL arm is
    measuring, which is why the baseline reports both.
    """
    best_edge = {}
    for pair, seen in dests.items():
        node, action = pair
        if legal_actions and action not in legal_actions.get(node, ()):
            continue
        p_hat = rate(stats.get(pair))
        if not p_hat:
            continue
        dest = max(sorted(seen), key=lambda d: seen[d])
        cost = 1.0 / p_hat
        prev = best_edge.get((node, dest))
        if prev is None or cost < prev["cost"]:
            best_edge[(node, dest)] = {"action": action, "cost": cost}

    dist = {start: 0.0}
    prev_hop = {}
    queue = [(0.0, start)]
    seen_nodes = set()
    while queue:
        d, node = heapq.heappop(queue)
        if node in seen_nodes:
            continue
        seen_nodes.add(node)
        if node == goal:
            break
        for (src, dest), edge in best_edge.items():
            if src != node:
                continue
            nd = d + edge["cost"]
            if nd < dist.get(dest, math.inf):
                dist[dest] = nd
                prev_hop[dest] = (node, edge["action"])
                heapq.heappush(queue, (nd, dest))

    if goal not in dist:
        return {"route": None, "expected_cost": None,
                "reason": "goal unreachable under observed evidence"}

    route, node = [], goal
    while node != start:
        src, action = prev_hop[node]
        route.append({"node": src, "action": action})
        node = src
    route.reverse()
    return {"route": route, "expected_cost": dist[goal], "reason": None}


def run_baseline(pv, queried_pairs=None, delta_threshold=None):
    """Answer all four probes from a prompt view alone.

    `queried_pairs` are the preservation pairs the model was shown, as
    (node, action) tuples. Omit it to skip that probe. `delta_threshold`
    defaults to the calibrated value for the view's budget.
    """
    budget = pv.get("budget_per_pair")
    if delta_threshold is None:
        delta_threshold = default_threshold(budget)
    pre_stats, post_stats, _pre_dests, post_dests = read_periods(pv)
    removed = menu_removals(pv)
    ranked = rank_pairs(pre_stats, post_stats)
    top = ranked[0] if ranked else None

    # Handbook 24.4: "no violations found" and "nothing was examined" must be
    # different exit states. With no comparable pairs the baseline would
    # otherwise return detection=False, localization=None and preservation
    # all-unchanged, which is indistinguishable from a correct no_change
    # answer and would score as one. Count what was actually measured and
    # refuse rather than pass.
    if not ranked and not removed:
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "could_not_run",
            "reason": ("no (node, action) pair was observed in both periods, "
                       "so no comparison exists; this is not a finding of "
                       "'no change'"),
            "rendering": pv.get("rendering"),
            "budget_per_pair": pv.get("budget_per_pair"),
            "n_pairs_compared": 0,
            "detection": None,
            "detection_reliable": False,
            "localization": None,
            "localization_basis": None,
            "margin": None,
            "ranking": [],
            "menu_removals": [],
            "preservation": None,
            "adaptation": {"route": None, "expected_cost": None,
                           "reason": "no evidence to plan from"},
        }

    if removed:
        localized, basis = removed[0], "menu_removal"
        detected = True
    elif top and top["abs_delta"] >= delta_threshold:
        localized, basis = top["pair"], "rate_swing"
        detected = True
    else:
        localized, basis = (top["pair"] if top else None), "rate_swing"
        detected = False

    deterministic = looks_deterministic(pre_stats, post_stats)
    result = {
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "n_pairs_compared": len(ranked),
        "rendering": pv.get("rendering"),
        "budget_per_pair": budget,
        "delta_threshold": delta_threshold,
        "threshold_calibrated": budget in CALIBRATED_DELTA_THRESHOLD,
        "evidence_looks_deterministic": deterministic,
        "detection": detected,
        # Localization is threshold-free (it is an argmax), so it stands
        # even where detection does not. Callers should drop the detection
        # column rather than reinterpret it when this flag is false.
        # Deterministic evidence and menu removals are always reliable:
        # neither depends on separating a signal from sampling noise.
        "detection_reliable": bool(
            removed or deterministic
            or budget not in UNRELIABLE_DETECTION_K),
        "localization": list(localized) if localized else None,
        "localization_basis": basis,
        # Margin is the gap between the top two rate swings. It says
        # nothing when the answer came from a menu diff, so it is not
        # reported in that case rather than reported misleadingly.
        "margin": (None if basis == "menu_removal" else
                   (ranked[0]["abs_delta"] - ranked[1]["abs_delta"]
                    if len(ranked) > 1 else None)),
        "ranking": [{**r, "pair": list(r["pair"])} for r in ranked[:5]],
        "menu_removals": [list(p) for p in removed],
    }

    if queried_pairs is not None:
        pairs = [tuple(p) for p in queried_pairs]
        result["preservation"] = {
            "/".join(p): (p == tuple(localized) if localized else False)
            for p in pairs
        }

    if post_dests:
        result["adaptation"] = plan_route(
            post_dests, post_stats, pv["start"], pv["goal"],
            pv.get("legal_actions_post"))
    else:
        result["adaptation"] = {
            "route": None, "expected_cost": None,
            "reason": f"rendering {pv.get('rendering')!r} carries no "
                      "destinations; adaptation needs an event rendering"}

    return result


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main():
    import argparse
    import resource_mdp

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("record", help="instance JSON (a full record)")
    ap.add_argument("--rendering", default="F2_shuffled",
                    choices=list(EVENT_RENDERINGS) + [STATS_RENDERING])
    ap.add_argument("--budget", type=int, default=5,
                    help="per-pair budget; match what the model was shown")
    ap.add_argument("--delta-threshold", type=float,
                    default=DEFAULT_DELTA_THRESHOLD)
    ap.add_argument("--pairs", nargs="*", default=None,
                    help="preservation pairs as NODE/ACTION, e.g. D/a2")
    args = ap.parse_args()

    with open(args.record) as fh:
        record = json.load(fh)

    pv = resource_mdp.prompt_view(record, rendering=args.rendering,
                                  budget_per_pair=args.budget)
    pairs = ([tuple(p.split("/")) for p in args.pairs]
             if args.pairs else None)
    print(json.dumps(
        run_baseline(pv, pairs, args.delta_threshold), indent=2))


if __name__ == "__main__":
    main()

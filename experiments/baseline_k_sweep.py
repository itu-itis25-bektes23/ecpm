"""Baseline localization accuracy vs per-pair budget K, on real logs.

The methodology doc reports that halving a link produces the largest
observed swing 31-60% of the time at K=10, rising to 56-90% at K=20 --
and states plainly that those figures come from simulation and have not
been measured on the collected evidence. This script measures them.

No API calls: the baseline is arithmetic, so the whole sweep runs
locally in seconds. That makes it the cheapest way to establish which
(condition, K) cells carry any headroom for a model at all, which in
turn decides where the Azure budget should go.

Output is one row per (condition, mode, K): the fraction of seeds where
the evidence-only baseline names the truly changed pair, plus the
fraction where it is tied at the top (ambiguous evidence rather than a
wrong answer), and mean rank of the true pair.

Usage:
    python3 experiments/baseline_k_sweep.py
    python3 experiments/baseline_k_sweep.py --seeds 1-30 --k 5 10 20 \
        --conditions silent_break degradation --json out.json
"""

import argparse
import math
import time
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ecpm_baseline as B
import resource_mdp as R

DEFAULT_CONDITIONS = ("silent_break", "hard_removal", "irrelevant",
                      "degradation", "no_change")
DEFAULT_K = (5, 10, 20)


def parse_seeds(spec):
    out = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-")
            out.extend(range(int(lo), int(hi) + 1))
        elif part:
            out.append(int(part))
    return out


def true_pair(record):
    """Ground-truth changed pair, or None for no_change."""
    ch = record.get("change")
    if not ch or not ch.get("edge"):
        return None
    return (ch["edge"]["from"], ch["action"])


def evaluate(seed, condition, deterministic, k, rendering, threshold):
    """One instance -> baseline verdict, or None if the seed is ineligible."""
    try:
        inst = R.make_pair(seed, condition, deterministic=deterministic,
                           matched=True)
        # Coverage needs room to grow with K: the collector must reach at
        # least K attempts on *every* pair, and a silently broken link is
        # the slowest to fill. Scaling the episode budget keeps ineligible
        # seeds a property of the graph, not of the collector.
        ev = R.paired_evidence(inst, k=k, max_episodes=300 * max(1, k // 5),
                               horizon=60 * max(1, k // 5))
        record = R.pair_to_json(inst, ev)
    except (ValueError, AssertionError, KeyError, RuntimeError):
        return None

    pv = R.prompt_view(record, rendering=rendering, budget_per_pair=k)
    res = B.run_baseline(pv, delta_threshold=threshold)

    truth = true_pair(record)
    ranked = B.rank_pairs(*B.read_periods(pv)[:2])
    order = [tuple(d["pair"]) for d in ranked]

    if truth is None:
        # no_change: the only meaningful quantity is the false-alarm rate.
        return {"kind": "no_change", "false_alarm": bool(res["detection"])}

    rank = order.index(truth) + 1 if truth in order else None
    top_delta = ranked[0]["abs_delta"] if ranked else None
    tied = (rank is not None and ranked[rank - 1]["abs_delta"] == top_delta)
    localized = res["localization"] and tuple(res["localization"]) == truth

    return {
        "kind": "change",
        "correct": bool(localized),
        "tied_at_top": bool(tied and not localized),
        "rank": rank,
        "detected": bool(res["detection"]),
        "basis": res["localization_basis"],
    }



# ---------------------------------------------------------------- --references
# Evidence-only references (rate, transition, bayes, generator-aware) on the paper's seeds:
#   python3 experiments/baseline_k_sweep.py --references --seeds 31-130 --json runs/references/references.json
def _peak_rss_mb():
    try:
        import resource   # not available on Windows
    except ImportError:
        return None
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)


REFERENCE_CONDITIONS = ("no_change", "irrelevant", "silent_break", "hard_removal", "redirect", "degradation")
GRID = [0.60 + 0.35 * (i + 0.5) / 400 for i in range(400)]


def outcomes(events):
    """Per pair: Counter of outcomes, where a drop is 'drop' and a delivery is its destination."""
    out = {}
    for node, action, dest in events:
        d = out.setdefault((node, action), {})
        key = "drop" if dest == node else dest
        d[key] = d.get(key, 0) + 1
    return out


def periods(pv):
    ev = pv["evidence"]
    pre = outcomes(B.parse_events(ev["pre"]))
    post = outcomes(B.parse_events(ev["post"]))
    return pre, post


def tv(a, b):
    na, nb = sum(a.values()), sum(b.values())
    # Fix addition order: hash-randomized set iteration changes float rounding.
    keys = sorted(set(a) | set(b))
    return 0.5 * sum(abs(a.get(k, 0) / na - b.get(k, 0) / nb) for k in keys)


def log_dm(counts, keys):
    n = sum(counts.get(k, 0) for k in keys)
    A = len(keys)
    return math.lgamma(A) - math.lgamma(n + A) + sum(math.lgamma(counts.get(k, 0) + 1) for k in keys)


def log_bf(a, b):
    keys = sorted(set(a) | set(b))
    both = {k: a.get(k, 0) + b.get(k, 0) for k in keys}
    return log_dm(a, keys) + log_dm(b, keys) - log_dm(both, keys)


def _lse(xs):
    m = max(xs)
    return m if m == -math.inf else m + math.log(sum(math.exp(x - m) for x in xs))


def gen_loglik(a, b, grid):
    """Log likelihood of one pair's (pre, post) outcomes under unchanged / zero / halve / redirect."""
    s0 = sum(v for k, v in a.items() if k != "drop"); f0 = a.get("drop", 0)
    s1 = sum(v for k, v in b.items() if k != "drop"); f1 = b.get("drop", 0)
    d0 = {k for k in a if k != "drop"}; d1 = {k for k in b if k != "drop"}
    same_dest = not d0 or not d1 or (d1 <= d0 and len(d0 | d1) == 1)
    moved_dest = bool(d0) and bool(d1) and not (d0 & d1) and len(d1) == 1

    def lp(p, s, f):
        if p <= 0:
            return 0.0 if s == 0 else -math.inf
        if p >= 1:
            return 0.0 if f == 0 else -math.inf
        return s * math.log(p) + f * math.log(1 - p)
    G = math.log(len(grid))
    unch = _lse([lp(p, s0 + s1, f0 + f1) for p in grid]) - G if same_dest else -math.inf
    zero = (_lse([lp(p, s0, f0) for p in grid]) - G) if s1 == 0 else -math.inf
    halve = (_lse([lp(p, s0, f0) + lp(max(0.05, round(p * 0.5, 2)), s1, f1) for p in grid]) - G) if same_dest else -math.inf
    redir = (_lse([lp(p, s0 + s1, f0 + f1) for p in grid]) - G - math.log(6)) if moved_dest else -math.inf
    return unch, {"zero": zero, "halve": halve, "redirect": redir}


PRIOR = {"zero": 2 / 6, "halve": 1 / 6, "redirect": 1 / 6}  # irrelevant + silent break both zero p


def ranked(scores):
    """Pairs sorted by score descending, ties broken by pair name (as ecpm_baseline does)."""
    return sorted(scores, key=lambda k: (-scores[k], k))


def references(pv, deterministic):
    pre, post = periods(pv)
    common = [k for k in pre if k in post]
    removed = [tuple(p) for p in B.menu_removals(pv)]
    out = {}
    tvs = {k: tv(pre[k], post[k]) for k in common}
    bfs = {k: log_bf(pre[k], post[k]) for k in common}
    grid = [1.0] if deterministic else GRID
    post_ratio = {}
    for k in common:
        u, ch = gen_loglik(pre[k], post[k], grid)
        for t, l in ch.items():
            post_ratio[(k, t)] = math.log(PRIOR[t]) + l - (u if u > -math.inf else -1e9)
    for name, sc in (("transition", tvs), ("bayes", bfs)):
        if removed:
            out[name] = {"loc": removed[0], "score": math.inf}
        elif sc:
            top = ranked(sc)[0]
            out[name] = {"loc": top, "score": sc[top]}
        else:
            out[name] = None
    if removed:
        out["generator"] = {"loc": removed[0], "score": math.inf}
    elif post_ratio:
        best = max(post_ratio, key=lambda kt: (post_ratio[kt], [-ord(c) for c in "".join(kt[0])]))
        # P(no change) vs P(best change): log odds; prior of no change is 1/6 spread over all pairs.
        n = len(common)
        lo = _lse([v - math.log(n) for v in post_ratio.values()]) - math.log(1 / 6)
        out["generator"] = {"loc": best[0], "score": lo}
    else:
        out["generator"] = None
    return out


def pair_scores(pv, deterministic):
    """Additive: every pair's score under each reference, {name: {pair: score}}.

    rate is |rate_post - rate_pre| (ecpm_baseline.rank_pairs), transition
    and bayes as in references(), generator the best change-type log
    posterior ratio per pair. A pair removed from the menu scores inf under
    every reference, as references() localizes it outright. Higher means
    more likely the changed pair; argmax with ranked() tie-breaking."""
    pre, post = periods(pv)
    common = [k for k in pre if k in post]
    grid = [1.0] if deterministic else GRID
    out = {"rate": {tuple(x["pair"]): x["abs_delta"]
                    for x in B.rank_pairs(*B.read_periods(pv)[:2])},
           "transition": {k: tv(pre[k], post[k]) for k in common},
           "bayes": {k: log_bf(pre[k], post[k]) for k in common},
           "generator": {}}
    for k in common:
        u, ch = gen_loglik(pre[k], post[k], grid)
        vals = [math.log(PRIOR[t]) + l - (u if u > -math.inf else -1e9)
                for t, l in ch.items()]
        if vals:
            out["generator"][k] = max(vals)
    for pair in B.menu_removals(pv):
        for name in out:
            out[name][tuple(pair)] = math.inf
    return out


def reference_instance(seed, condition, deterministic, k, rendering="F2_shuffled", n_nodes=None):
    try:
        kw = {} if n_nodes is None else {"n_nodes": n_nodes}
        inst = R.make_pair(seed, condition, deterministic=deterministic, matched=True, **kw)
        ev = R.paired_evidence(inst, k=k, max_episodes=300 * max(1, k // 5), horizon=60 * max(1, k // 5))
        record = R.pair_to_json(inst, ev)
    except (ValueError, AssertionError, KeyError, RuntimeError, TypeError):
        return None
    return inst, record, R.prompt_view(record, rendering=rendering, budget_per_pair=k)


def reference_row(seed, condition, deterministic, k, threshold):
    got = reference_instance(seed, condition, deterministic, k)
    if got is None:
        return None
    inst, record, pv = got
    t0 = time.process_time()
    res = B.run_baseline(pv, delta_threshold=threshold)
    t_rate = time.process_time() - t0
    t0 = time.process_time()
    refs = references(pv, deterministic)
    t_refs = time.process_time() - t0
    truth = true_pair(record)
    _, post_stats, _, _ = B.read_periods(pv)
    top = B.rank_pairs(*B.read_periods(pv)[:2])
    route = (res.get("adaptation") or {}).get("route") or []
    path = R.route_from_actions(inst.start, [s["action"] for s in route], inst.labels, inst.m1) if route else None
    sc = R.score_route(inst.m1, path, inst.start)
    r = {"seed": seed, "condition": condition, "mode": "det" if deterministic else "sto", "k": k,
         "truth": list(truth) if truth else None,
         "rate": {"loc": list(res["localization"]) if res.get("localization") else None,
                  "detected": bool(res.get("detection")),
                  "score": (math.inf if res.get("localization_basis") == "menu_removal"
                            else (top[0]["abs_delta"] if top else 0.0))},
         "route_optimal": bool(sc.get("status") == "valid_finite" and abs(sc.get("regret", 1)) < 1e-9),
         "cpu_s": {"rate": t_rate, "others": t_refs},
         "prompt_bytes": len(json.dumps(pv["evidence"]).encode())}
    for name in ("transition", "bayes", "generator"):
        v = refs.get(name)
        r[name] = {"loc": list(v["loc"]) if v else None, "score": v["score"] if v else None}
    return r


def references_main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="31-130")
    ap.add_argument("--k", type=int, nargs="+", default=[5, 10, 20])
    ap.add_argument("--modes", nargs="+", default=["sto", "det"])
    ap.add_argument("--conditions", nargs="+", default=list(REFERENCE_CONDITIONS))
    ap.add_argument("--json", required=True)
    a = ap.parse_args(argv)
    rows, t = [], time.time()
    for mode in a.modes:
        for k in a.k:
            thr = B.CALIBRATED_DELTA_THRESHOLD.get(k)
            for cond in a.conditions:
                if mode == "det" and cond == "degradation":
                    continue
                for s in parse_seeds(a.seeds):
                    r = reference_row(s, cond, mode == "det", k, thr)
                    if r:
                        rows.append(r)
    for r in rows:  # json cannot hold inf
        for name in ("rate", "transition", "bayes", "generator"):
            if r[name] and r[name]["score"] == math.inf:
                r[name]["score"] = "inf"
    cpu = {"rate": 0.0, "others": 0.0}
    for r in rows:  # timings vary from run to run: kept out of the artifact
        c = r.pop("cpu_s")
        cpu["rate"] += c["rate"]
        cpu["others"] += c["others"]
    os.makedirs(os.path.dirname(os.path.abspath(a.json)), exist_ok=True)
    meta = {"seeds": a.seeds, "k": a.k, "modes": a.modes, "n_rows": len(rows)}
    with open(a.json, "w") as fh:
        json.dump({"meta": meta, "rows": rows}, fh)
    timing = {**meta, "wall_s": round(time.time() - t, 1),
              "peak_rss_mb": _peak_rss_mb(),
              "cpu_s": {k: round(v, 2) for k, v in cpu.items()}}
    tpath = os.path.join(os.path.dirname(os.path.abspath(a.json)), "timing_" + os.path.basename(a.json))
    with open(tpath, "w") as fh:
        json.dump(timing, fh)
    print(json.dumps(timing))


def main():
    if "--references" in sys.argv:
        return references_main([a for a in sys.argv[1:] if a != "--references"])
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="1-30")
    ap.add_argument("--k", type=int, nargs="+", default=list(DEFAULT_K))
    ap.add_argument("--conditions", nargs="+", default=list(DEFAULT_CONDITIONS))
    ap.add_argument("--modes", nargs="+", default=["sto", "det"],
                    choices=["sto", "det"])
    ap.add_argument("--rendering", default="F2_shuffled")
    ap.add_argument("--delta-threshold", type=float,
                    default=None)
    ap.add_argument("--json", default=None, help="write full rows here")
    args = ap.parse_args()

    seeds = parse_seeds(args.seeds)
    rows, raw = [], []

    for mode in args.modes:
        deterministic = (mode == "det")
        for condition in args.conditions:
            for k in args.k:
                results = []
                for seed in seeds:
                    r = evaluate(seed, condition, deterministic, k,
                                 args.rendering, args.delta_threshold)
                    if r:
                        r.update(seed=seed, condition=condition, mode=mode, k=k)
                        results.append(r)
                        raw.append(r)
                if not results:
                    continue

                n = len(results)
                if results[0]["kind"] == "no_change":
                    fa = sum(r["false_alarm"] for r in results)
                    rows.append({"mode": mode, "condition": condition, "k": k,
                                 "n": n, "false_alarm_rate": fa / n,
                                 "localized": None, "tied": None,
                                 "mean_rank": None, "detected": None})
                    continue

                ranks = [r["rank"] for r in results if r["rank"]]
                rows.append({
                    "mode": mode, "condition": condition, "k": k, "n": n,
                    "localized": sum(r["correct"] for r in results) / n,
                    "tied": sum(r["tied_at_top"] for r in results) / n,
                    "detected": sum(r["detected"] for r in results) / n,
                    "mean_rank": statistics.mean(ranks) if ranks else None,
                    "false_alarm_rate": None,
                })

    hdr = (f"{'mode':<5}{'condition':<15}{'K':>3}{'n':>5}"
           f"{'localized':>11}{'tied':>7}{'detect':>8}{'meanRank':>10}")
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        if r["localized"] is None:
            print(f"{r['mode']:<5}{r['condition']:<15}{r['k']:>3}{r['n']:>5}"
                  f"{'--':>11}{'--':>7}"
                  f"{r['false_alarm_rate']:>8.2f}{'(FA)':>10}")
        else:
            # mean_rank is undefined when the true pair left the menu
            # (hard_removal): it is not in the rate ranking at all.
            rank = (f"{r['mean_rank']:>10.2f}" if r["mean_rank"] is not None
                    else f"{'n/a':>10}")
            print(f"{r['mode']:<5}{r['condition']:<15}{r['k']:>3}{r['n']:>5}"
                  f"{r['localized']:>11.2f}{r['tied']:>7.2f}"
                  f"{r['detected']:>8.2f}{rank}")

    print("\nlocalized = baseline names the true pair; tied = true pair is at "
          "the top but not uniquely;\ndetect = baseline calls a change; "
          "(FA) = false-alarm rate on no_change.")

    if args.json:
        with open(args.json, "w") as fh:
            json.dump({"rows": rows, "raw": raw,
                       "params": vars(args)}, fh, indent=2)
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()

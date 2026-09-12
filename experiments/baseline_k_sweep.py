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


def main():
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

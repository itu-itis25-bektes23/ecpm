"""Seed eligibility audit.

The methodology document states three criteria a seed must meet:

  1. the goal stays reachable under every scenario
  2. the control scenarios leave the best route untouched, while the
     route-changing scenarios move it
  3. the best route is unique before and after the edit, since under a tie
     a correct re-plan is indistinguishable from a lucky choice

It then reports that only seeds 13 and 25 pass all three in stochastic mode.
That figure predates v2.2. Before `651f8d7`, `degradation` drew its own
target link rather than sharing T*, so a seed had to satisfy eligibility for
two independent links. With degradation sharing T*, eligibility rises.

This script recomputes the criteria from the code rather than quoting the
document, so the numbers in the paper have a generator.

The fourth column
-----------------
Criterion 2 is applied per condition, not per seed. On nine stochastic seeds
`degradation` raises the cost of T* without making any alternative route
cheaper, so the optimal route does not move. Those seeds are NOT excluded.
They are labelled `restraint`, because the correct answer there is to notice
the change and keep the route.

That distinction matters for scoring. On a restraint instance a completely
stale plan scores regret 0.0, since the old route really is still optimal.
Adaptation therefore cannot separate "correctly concluded no re-plan was
needed" from "ignored the change entirely", and must not be reported as a
re-planning score. Detection, localization and preservation stay fully
informative, and the combination (all three correct AND the route kept) is a
test of restraint that no other condition in the battery provides.

Usage:
    python3 experiments/seed_eligibility.py
    python3 experiments/seed_eligibility.py --seeds 1-60 --json out.json
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import resource_mdp as R

ROUTE_CHANGING = ("silent_break", "hard_removal", "degradation", "redirect")
CONTROLS = ("no_change", "irrelevant")
ALL_CONDITIONS = ROUTE_CHANGING + CONTROLS


def conditions_for(deterministic):
    """degradation halves a success probability, undefined when p = 1."""
    return [c for c in ALL_CONDITIONS
            if not (c == "degradation" and deterministic)]


def audit_one(seed, condition, deterministic):
    """One (seed, condition) cell against the three criteria."""
    try:
        inst = R.make_pair(seed, condition, deterministic=deterministic,
                           matched=True)
    except Exception as exc:
        return {"status": "not_built", "reason": str(exc)[:120]}

    pre, post = inst.oracle["pre"], inst.oracle["post"]
    moved = pre["optimal_route"] != post["optimal_route"]
    unique = bool(pre["route_unique"] and post["route_unique"])

    out = {
        "reachable": bool(post["solvable"]),
        "unique_pre_post": unique,
        "route_moved": bool(moved),
        "pre_cost": pre["optimal_cost"],
        "post_cost": post["optimal_cost"],
    }

    if not post["solvable"]:
        out["status"] = "excluded"
        out["reason"] = "goal unreachable after the edit"
        return out
    if not unique:
        out["status"] = "excluded"
        out["reason"] = "optimal route is not unique before and after"
        return out
    if condition in CONTROLS and moved:
        out["status"] = "excluded"
        out["reason"] = "a control scenario moved the optimal route"
        return out

    if condition in ROUTE_CHANGING and not moved:
        # Not a failure. The edit is real and detectable; it simply does not
        # change the best plan. Scored on the first three probes, plus
        # adaptation read as restraint rather than as re-planning.
        out["status"] = "restraint"
        out["reason"] = ("the edit did not move the optimal route; a stale "
                         "plan scores regret 0, so adaptation here measures "
                         "restraint, not re-planning")
        out["stale_plan_regret"] = stale_regret(inst)
        return out

    out["status"] = "eligible"
    return out


def stale_regret(inst):
    """Regret of replaying the pre-change optimal route in the post world.

    Reported on restraint cells to make the degeneracy explicit in the
    artifact rather than leaving a reader to rediscover it.
    """
    try:
        scored = R.score_route(inst.m1, inst.oracle["pre"]["optimal_route"],
                               inst.start)
        return scored.get("regret")
    except Exception:
        return None


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="1-30")
    ap.add_argument("--json", default="runs/seed_eligibility.json")
    args = ap.parse_args()

    seeds = parse_seeds(args.seeds)
    cells, summary = {}, {}

    for mode, det in (("sto", False), ("det", True)):
        for cond in conditions_for(det):
            usable, restraint, excluded, not_built = [], [], [], []
            for seed in seeds:
                r = audit_one(seed, cond, det)
                cells[f"{mode}|{cond}|{seed}"] = r
                st = r["status"]
                (usable if st == "eligible" else
                 restraint if st == "restraint" else
                 not_built if st == "not_built" else excluded).append(seed)
            summary[f"{mode}|{cond}"] = {
                "eligible": usable, "restraint": restraint,
                "excluded": excluded, "not_built": not_built,
                "n_scoreable": len(usable) + len(restraint),
            }

    hdr = (f"{'mode':<5}{'condition':<15}{'eligible':>9}{'restraint':>10}"
           f"{'excluded':>9}{'not built':>10}{'scoreable':>10}")
    print(hdr)
    print("-" * len(hdr))
    for key, s in summary.items():
        mode, cond = key.split("|")
        print(f"{mode:<5}{cond:<15}{len(s['eligible']):>9}"
              f"{len(s['restraint']):>10}{len(s['excluded']):>9}"
              f"{len(s['not_built']):>10}{s['n_scoreable']:>10}")

    print("\neligible  = all three criteria met; adaptation is a re-planning "
          "score")
    print("restraint = edit real but the optimal route did not move; a stale "
          "plan scores\n            regret 0, so adaptation measures "
          "restraint and is reported apart")
    print("scoreable = eligible + restraint; both are run, with adaptation "
          "read differently")

    # The primary output is the INTERSECTION, not the per-condition lists.
    # Matched mode exists so that a seed gives the same graph, start, goal
    # and T* across conditions. Running no_change on 30 seeds and
    # silent_break on 23 would confound the intervention with the seven
    # extra graphs, so the surplus is reported and not used.
    intersections = {}
    for mode, det in (("sto", False), ("det", True)):
        sets = []
        for cond in conditions_for(det):
            s = summary[f"{mode}|{cond}"]
            sets.append(set(s["eligible"]) | set(s["restraint"]))
        inter = sorted(set.intersection(*sets)) if sets else []
        intersections[mode] = inter
        surplus = sorted(set.union(*sets) - set(inter)) if sets else []
        print(f"\nRUN SET, {mode} (intersection of all conditions): "
              f"n={len(inter)}")
        print("  " + " ".join(str(x) for x in inter))
        if surplus:
            print(f"  surplus, not used ({len(surplus)}): "
                  + " ".join(str(x) for x in surplus))
            print("  no_change and irrelevant build on these, the break "
                  "family does not;\n  using them would compare conditions "
                  "on different graphs.")

    os.makedirs(os.path.dirname(args.json) or ".", exist_ok=True)
    with open(args.json, "w") as fh:
        json.dump({
            "criteria": {
                "1": "goal reachable under every scenario",
                "2": "controls leave the optimal route untouched; "
                     "route-changing scenarios move it",
                "3": "optimal route unique before and after the edit",
            },
            "note": ("Criterion 2 is applied per condition. Route-changing "
                     "cells that fail it are labelled restraint rather than "
                     "excluded; see the module docstring."),
            "seeds_examined": seeds,
            "summary": summary,
            "run_set": intersections,
            "cells": cells,
        }, fh, indent=2)
    print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()

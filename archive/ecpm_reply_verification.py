#!/usr/bin/env python3
"""Reproduce the numbers quoted in the pre-freeze reply (2026-08-19).

Against the v2.0 code this reproduced the review findings: 75/160
silent-vs-hard target mismatches, 1000/1000 deterministic-irrelevant
instances with a stochastic post world, seed 60 = 5390 post attempts.
Against v2.1 it doubles as a regression check: expect different_target=0,
post_world_has_stochastic_edge=0, and both examples regenerating with
the evidence_seed stored in the files (now the default, 0).

v2.1.1 adds matched_anchor_check: among seeds where matched=True
constructs in both modes (794/1000), expect start and target equality
100%; the shared-pre-route count is informational (the residual route
difference is the uncertainty manipulation itself).

Read-only. Run from the repo root:  python3 ecpm_reply_verification.py
Checks:
  - seed-7 examples regenerate identically (with the evidence_seed stored
    in the files, which is 11, not the signature default 0)
  - the model_visible leak (evidence + true-edge counts_*)
  - F2_shuffled is an exact permutation of F2_ordered
  - deterministic `irrelevant` leaves a stochastic edge in the post world
  - matched-mode option (i) yield: seeds with a shared breakable
    on-route edge in BOTH modes
  - silent_break vs hard_removal target mismatch
  - worst-case evidence budget (seed 60 / seed 44)
"""

from __future__ import annotations

import os
import sys

# Moved to archive/ on 2026-09-13. These scripts import the environment
# modules, which live at the repository root, so put the root on the path
# rather than requiring a particular working directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))



import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from resource_mdp import make_pair, pair_to_json, paired_evidence  # noqa: E402

INF = float("inf")


def _f1_text(f1) -> str:
    return f1 if isinstance(f1, str) else "\n".join(map(str, f1))


def check_examples() -> dict:
    out = {}
    for det, name in (
        (True, "example_deterministic_silent_break.json"),
        (False, "example_stochastic_silent_break.json"),
    ):
        r = json.loads(Path(name).read_text())
        es = r["evidence"]["evidence_seed"]
        k = r["evidence"]["k_per_pair"]
        inst = make_pair(7, "silent_break", deterministic=det,
                         matched=r["params"].get("matched", False))
        rec = json.loads(
            json.dumps(pair_to_json(inst, paired_evidence(inst, k=k, evidence_seed=es)))
        )
        po = r["evidence"]["post"]
        t1 = collections.Counter(re.findall(r"\([^()]*\)", po["F2_ordered"]))
        t2 = collections.Counter(re.findall(r"\([^()]*\)", po["F2_shuffled"]))
        out[name] = {
            "regenerates_identically": rec == r,
            "evidence_seed_in_file": es,
            "evidence_inside_model_visible": "evidence" in r["model_visible"],
            "counts_keyed_by_true_edges": sorted(r["evidence"]["counts_pre"])[:2],
            "n_state_action_pairs": len(r["evidence"]["counts_pre"]),
            "shuffled_is_permutation_of_ordered": t1 == t2 and sum(t1.values()) > 0,
        }
    return out


def det_irrelevant(n: int) -> dict:
    eligible = stochastic_post = 0
    for seed in range(n):
        try:
            inst = make_pair(seed, "irrelevant", deterministic=True)
        except ValueError:
            continue
        eligible += 1
        stochastic_post += any(0.0 < p < 1.0 for p in inst.m1.p.values())
    return {"eligible": eligible, "post_world_has_stochastic_edge": stochastic_post}


def matched_option_i_yield(n: int) -> dict:
    def route_edges(route):
        return set(zip(route, route[1:]))

    eligible = surviving = 0
    for seed in range(n):
        try:
            det = make_pair(seed, "silent_break", deterministic=True)
            sto = make_pair(seed, "silent_break", deterministic=False)
        except ValueError:
            continue
        eligible += 1
        shared = route_edges(det.oracle["pre"]["optimal_route"]) & route_edges(
            sto.oracle["pre"]["optimal_route"]
        )
        hit = False
        for (u, v) in shared:
            g = det.m0.copy()
            g.break_link(u, v, "silent")
            dist, _ = g.optimal()
            if dist[det.start] < INF and dist[sto.start] < INF:
                hit = True
                break
        surviving += hit
    return {"eligible": eligible, "shared_breakable_on_route_edge": surviving}


def silent_vs_hard(n: int) -> dict:
    pairs = same = 0
    for deterministic in (False, True):
        for seed in range(n):
            try:
                a = make_pair(seed, "silent_break", deterministic=deterministic)
                b = make_pair(seed, "hard_removal", deterministic=deterministic)
            except ValueError:
                continue
            pairs += 1
            same += a.change["edge"] == b.change["edge"]
    return {"seed_mode_pairs": pairs, "same_target": same, "different_target": pairs - same}


def matched_anchor_check(n: int) -> dict:
    eligible = start_eq = target_eq = route_eq = 0
    for seed in range(n):
        try:
            a = make_pair(seed, "silent_break", deterministic=True,
                          matched=True)
            b = make_pair(seed, "silent_break", deterministic=False,
                          matched=True)
        except ValueError:
            continue
        eligible += 1
        start_eq += a.start == b.start
        target_eq += a.change["edge"] == b.change["edge"]
        route_eq += (a.oracle["pre"]["optimal_route"]
                     == b.oracle["pre"]["optimal_route"])
    return {"eligible": eligible, "start_equal": start_eq,
            "target_equal": target_eq,
            "same_pre_optimal_route": route_eq}


def worst_case() -> dict:
    i60 = make_pair(60, "silent_break", deterministic=True)
    e60 = paired_evidence(i60, k=5, evidence_seed=0)
    i44 = make_pair(44, "hard_removal", deterministic=True)
    e44 = paired_evidence(i44, k=5, evidence_seed=0)
    return {
        "seed60_total_post_attempts": sum(
            v["attempts"] for v in e60["counts_post"].values()
        ),
        "seed60_post_episodes": e60["episodes_post"],
        "seed60_F1_post_tokens_approx": len(_f1_text(e60["post"]["F1_log"])) // 4,
        "seed44_max_pair_post_attempts": max(
            v["attempts"] for v in e44["counts_post"].values()
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=1000)
    parser.add_argument("--pair-seeds", type=int, default=80)
    args = parser.parse_args()
    report = {
        "seed7_examples": check_examples(),
        "det_irrelevant_stochastic_post": det_irrelevant(args.seeds),
        "matched_option_i_yield": matched_option_i_yield(args.seeds),
        "silent_vs_hard_target": silent_vs_hard(args.pair_seeds),
        "matched_anchors": matched_anchor_check(args.seeds),
        "worst_case_budget": worst_case(),
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

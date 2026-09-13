#!/usr/bin/env python3
"""Independent adversarial checks for the ECPM pre-freeze patch.

Original: Pavlos (2026-08-19), run against v2.1. Committed with two
v2.1.1 adaptations: prompt_view(budget_per_pair=6) now RAISES by
design (0 < B <= k is enforced), so the call is wrapped to record the
rejection; and the seed count is a CLI argument so the sweep can be
smoke-tested quickly (default remains 1000 -> 9000 instances).
Expected v2.1.1 preservation statuses: incomplete_response /
duplicate_pair (was accuracy=1.0 with a movable denominator)."""

import os
import sys

# Moved to archive/ on 2026-09-13. These scripts import the environment
# modules, which live at the repository root, so put the root on the path
# rather than requiring a particular working directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sys

import json

from ecpm_parser import parse_detection, run_probe
from resource_mdp import CONDITIONS, make_pair, pair_to_json, paired_evidence, prompt_view


def preservation_checks():
    rec = json.loads(json.dumps(pair_to_json(make_pair(7, "silent_break"))))
    ch = rec["change"]
    target = {"node": ch["edge"]["from"], "action": ch["action"]}
    unchanged = next(
        {"node": e["from"], "action": e["action"]}
        for e in rec["world_pre"]["edges"]
        if (e["from"], e["action"]) != (target["node"], target["action"])
    )
    queried = [unchanged, target]
    one_only = json.dumps({"pairs": [{**unchanged, "changed": False}]})
    duplicate = json.dumps(
        {"pairs": [{**unchanged, "changed": False}] * 10}
    )
    empty = json.dumps({"pairs": []})
    return {
        "one_of_two_queried": run_probe(
            rec, "preservation", one_only, queried_pairs=queried
        )["scored"],
        "duplicate_one_of_two": run_probe(
            rec, "preservation", duplicate, queried_pairs=queried
        )["scored"],
        "empty": run_probe(
            rec, "preservation", empty, queried_pairs=queried
        )["scored"],
    }


def budget_checks():
    inst = make_pair(7, "silent_break")
    ev = paired_evidence(inst, k=5, evidence_seed=0)
    rec = json.loads(json.dumps(pair_to_json(inst, ev)))
    pairs_pre = len(ev["counts_pre"])
    pairs_post = len(ev["counts_post"])
    exact_default = prompt_view(rec, "F2_shuffled", budget_per_pair=5)
    try:
        above_k = prompt_view(rec, "F2_shuffled", budget_per_pair=6)
        above_k_events = {
            period: above_k["realized"][period]["events"]
            for period in ("pre", "post")
        }
    except ValueError as exc:
        above_k_events = {"rejected": str(exc)}
    return {
        "pair_counts": {"pre": pairs_pre, "post": pairs_post},
        "budget_5_events": {
            period: exact_default["realized"][period]["events"]
            for period in ("pre", "post")
        },
        "budget_6_events": above_k_events,
        "budget_6_claimed_exact_totals": {
            "pre": 6 * pairs_pre,
            "post": 6 * pairs_post,
        },
    }


def parser_first_object_check():
    raw = '{not valid json} then {"changed": true}'
    return {"raw": raw, "parsed": parse_detection(raw)}


def capped_collection_sweep(n=1000):
    generation_failures = []
    evidence_failures = []
    resampled = 0
    max_resamples = 0
    completed = 0
    for deterministic in (False, True):
        mode = "deterministic" if deterministic else "stochastic"
        for seed in range(n):
            for condition in CONDITIONS:
                if deterministic and condition == "degradation":
                    continue
                try:
                    inst = make_pair(seed, condition, deterministic=deterministic)
                except ValueError as exc:
                    generation_failures.append(
                        {"seed": seed, "mode": mode, "condition": condition,
                         "error": str(exc)}
                    )
                    continue
                try:
                    ev = paired_evidence(inst, k=5, evidence_seed=0)
                except RuntimeError as exc:
                    evidence_failures.append(
                        {"seed": seed, "mode": mode, "condition": condition,
                         "error": str(exc)}
                    )
                    continue
                completed += 1
                resampled += ev["resamples"] > 0
                max_resamples = max(max_resamples, ev["resamples"])
    return {
        "requested_allowed_instances": n * 9,
        "completed": completed,
        "generation_failure_count": len(generation_failures),
        "generation_failure_examples": generation_failures[:5],
        "evidence_failure_count": len(evidence_failures),
        "evidence_failure_examples": evidence_failures[:5],
        "instances_requiring_resample": resampled,
        "max_resamples_used": max_resamples,
    }


if __name__ == "__main__":
    print(json.dumps({
        "preservation": preservation_checks(),
        "budget": budget_checks(),
        "first_object_contract": parser_first_object_check(),
        "capped_collection_1000_seed_sweep": capped_collection_sweep(
            int(sys.argv[1]) if len(sys.argv) > 1 else 1000),
    }, indent=2, sort_keys=True))

#!/usr/bin/env python3
"""Aggregate icl_two_response_v1 artifacts by level.

experiments/summarize_run.py reads the legacy two-turn artifacts and finds
nothing under an ICL run directory, so this is the equivalent for the ICL
protocol. It reports Turn B outcomes per level, plus the Turn A baseline,
plus the operational facts that decide whether a cell is readable at all
(malformed answers, truncation, reasoning tokens).

    python3 summarize_icl_run.py pilot_artifacts/icl_graph_sol_det
    python3 summarize_icl_run.py pilot_artifacts/... --json out.json

Rates are printed as k/n. Every cell carries its n because a cell without
its n cannot be read, and n is 3 per level here. These are demonstrations,
not estimates of a rate.
"""

import argparse
import collections
import glob
import json
import os


def load(root):
    artifacts = []
    pattern = os.path.join(root, "**", "*.json")
    for path in sorted(glob.glob(pattern, recursive=True)):
        if os.path.basename(path) == "summary.json":
            continue
        try:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("protocol") == "icl_two_response_v1":
            artifacts.append(data)
    return artifacts


def reasoning_tokens(turn):
    usage = turn.get("provider_usage") or {}
    details = usage.get("completion_tokens_details") or {}
    return details.get("reasoning_tokens")


def row_for(artifact):
    turn_a, turn_b = artifact["turns"]["A"], artifact["turns"]["B"]
    a_scored, b_scored = turn_a.get("scored", {}), turn_b.get("scored", {})
    dl = b_scored.get("detection_localization", {})
    tokens = [reasoning_tokens(turn_a), reasoning_tokens(turn_b)]
    prompt_tokens = sum((turn.get("provider_usage") or {}).get(
        "prompt_tokens", 0) for turn in (turn_a, turn_b))
    completion_tokens = sum((turn.get("provider_usage") or {}).get(
        "completion_tokens", 0) for turn in (turn_a, turn_b))
    return {
        "level": artifact["level"],
        "seed": artifact["scenario"]["seed"],
        "budget": artifact["scenario"]["budget"],
        "condition": artifact["scenario"]["condition"],
        "repeat": artifact["repeat"],
        "detection": bool(dl.get("detection_correct")),
        "localization": bool(dl.get("localization_correct")),
        "preservation": bool(b_scored.get("control_preservation", {}).get(
            "all_controls_correct", b_scored.get(
                "control_preservation", {}).get(
                "all_four_controls_correct"))),
        "route_a_optimal": a_scored.get("route", {}).get("is_optimal") is True,
        "route_b_optimal": b_scored.get("route", {}).get("is_optimal") is True,
        "belief_acc_a": a_scored.get("beliefs", {}).get("accuracy", 0.0),
        "belief_acc_b": b_scored.get("beliefs", {}).get("accuracy", 0.0),
        "mae_truth": b_scored.get("beliefs", {}).get("p_mae_truth"),
        "mae_visible": b_scored.get("beliefs", {}).get("p_mae_visible"),
        "well_formed": bool(a_scored.get("well_formed")) and bool(
            b_scored.get("well_formed")),
        "truncated": bool(turn_a.get("truncated") or turn_b.get("truncated")),
        "reasoning_tokens": [t for t in tokens if t is not None],
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
    }


FIELDS = ("detection", "localization", "preservation",
          "route_a_optimal", "route_b_optimal", "well_formed")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="run directory holding the artifacts")
    ap.add_argument("--json", default=None, help="also write the rows here")
    args = ap.parse_args()

    artifacts = load(args.root)
    if not artifacts:
        raise SystemExit(f"no ICL artifacts found under {args.root}")
    rows = [row_for(a) for a in artifacts]
    # A directory can hold more than one cell when two runs shared a tag,
    # so group by the settings that define a cell, not by level alone.
    by_cell = collections.defaultdict(list)
    for row in rows:
        by_cell[(row["condition"], row["seed"], row["budget"],
                 row["level"])].append(row)

    cells = sorted({key[:3] for key in by_cell})
    print(f"{len(rows)} conversations in {len(cells)} cell(s)\n")
    if len(cells) > 1:
        print("WARNING: this directory holds more than one condition, seed "
              "or budget. They are reported separately below; do not read "
              "them as one run.\n")
    header = (f"{'level':11s} {'n':>2s} " +
              " ".join(f"{name:>14s}" for name in FIELDS) +
              f" {'belief_B':>9s} {'MAEtruth':>9s} {'MAEvis':>7s}")
    for condition, seed, budget in cells:
        print(f"{condition}, seed {seed}, budget {budget}")
        print(header)
        print("-" * len(header))
        for level in sorted(l for c, s_, b, l in by_cell
                            if (c, s_, b) == (condition, seed, budget)):
            group = by_cell[(condition, seed, budget, level)]
            n = len(group)
            body = " ".join(
                f"{sum(row[name] for row in group):>11d}/{n:<2d}"
                for name in FIELDS)
            belief = sum(row["belief_acc_b"] for row in group) / n
            def avg(field):
                vals = [r[field] for r in group if r[field] is not None]
                return sum(vals) / len(vals) if vals else float("nan")
            print(f"{level:11s} {n:>2d} {body} {belief:>9.2f} "
                  f"{avg('mae_truth'):>9.3f} {avg('mae_visible'):>7.3f}")
        print()

    ok = [row for row in rows if not row["truncated"]]
    if len(ok) != len(rows):
        print(f"NOTE: {len(rows) - len(ok)} truncated conversation(s) are "
              f"counted in the table above but are not scoreable; rerun "
              f"them with a larger --max-tokens before reading the cell.\n")
    truncated = [row for row in rows if row["truncated"]]
    malformed = [row for row in rows if not row["well_formed"]]
    tokens = [t for row in rows for t in row["reasoning_tokens"]]
    print()
    print(f"malformed answers: {len(malformed)} of {len(rows)}")
    print(f"truncated: {len(truncated)} of {len(rows)}")
    if tokens:
        print(f"reasoning tokens per turn: min {min(tokens)}, "
              f"max {max(tokens)}, mean {sum(tokens) / len(tokens):.0f}")
        if max(tokens) > 0:
            print("  reasoning tokens are non-zero, so this run is not 'off'")
    else:
        print("reasoning tokens: not reported by this provider")
    print(f"prompt tokens: {sum(row['prompt_tokens'] for row in rows)}")
    print(f"completion tokens: {sum(row['completion_tokens'] for row in rows)}")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump({"root": args.root, "rows": rows}, handle, indent=2)
        print(f"\nrows -> {args.json}")


if __name__ == "__main__":
    main()

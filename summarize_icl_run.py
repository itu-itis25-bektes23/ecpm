#!/usr/bin/env python3
"""Aggregate icl_two_response_v1 artifacts by level.

experiments/summarize_run.py reads the legacy two-turn artifacts and finds
nothing under an ICL run directory, so this is the equivalent for the ICL
protocol. It reports Turn B outcomes per level, plus the Turn A baseline,
plus the operational facts that decide whether a cell is readable at all
(malformed answers, truncation, reasoning tokens).

    python3 summarize_icl_run.py pilot_artifacts/icl_graph_sol_det
    python3 summarize_icl_run.py pilot_artifacts/... --json out.json
    python3 summarize_icl_run.py --tables RESULTS_DIR/metrics.csv[.gz]   # expanded ICL: Results-tab tables

Rates are printed as k/n. Every cell carries its n because a cell without
its n cannot be read, and n is 3 per level here. These are demonstrations,
not estimates of a rate.
"""

import argparse
import collections
import csv
import glob
import gzip
import json
import os
import sys


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
            "all_four_controls_correct")),
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


ICL_ARMS = ("task_only", "model_first", "graph_given")
ICL_CHANGED = ("silent_break", "hard_removal", "redirect", "degradation", "irrelevant")


def icl_tables(path):
    """Results-tab tables for expanded ICL, from the metrics.csv its export writes (one row per metric)."""
    convs = collections.defaultdict(dict)   # conversation -> {(period, metric): (numerator, denominator)}, queries summed
    meta = {}
    opener = gzip.open if path.endswith(".gz") else open   # metrics.csv is large; the repo keeps it gzipped
    for r in csv.DictReader(opener(path, "rt", encoding="utf-8")):
        if r["operational_status"] != "valid":
            continue                          # valid conversations only
        key = (r["model"], r["run_id"], r["history_policy"], r["reasoning_mode"])
        meta[key] = r
        num = {"True": 1, "False": 0}.get(r["numerator"], r["numerator"])
        try:
            n0, d0 = convs[key].get((r["period"], r["metric"]), (0.0, 0.0))
            convs[key][(r["period"], r["metric"])] = (n0 + float(num), d0 + float(r["denominator"]))
        except ValueError:
            pass
    def rate(keys, period, metric):           # pooled: summed numerators over summed denominators
        n = d = 0
        for k in keys:
            v = convs[k].get((period, metric))
            if v and v[1] > 0: n, d = n + v[0], d + v[1]
        return f"{n / d:.0%}" if d else "n/a"
    hist = lambda h: "retained" if h.startswith("retained") else "separate"
    out = []
    for model in sorted({k[0] for k in convs}):
        K = [k for k in convs if k[0] == model]
        ch = [k for k in K if meta[k]["scenario"] != "no_change"]
        out += [f"## {model}: {len(K)} conversations (expanded ICL)", "",
                "**Table 1. Reading, reporting and acting by arm (scenarios with a change)**", "",
                "| Reasoning | Arm | History | Convs | A transitions exact | A routes optimal | B detection | B localization | B necessary updates | B routes optimal |",
                "|---|---|---|---|---|---|---|---|---|---|"]
        for rs in sorted({k[3] for k in K}):
            for a in ICL_ARMS:
                for h in sorted({k[2] for k in K}):
                    sub = [k for k in ch if k[3] == rs and k[2] == h and meta[k]["condition"] == a]
                    if sub:
                        out.append(f"| {rs} | {a} | {hist(h)} | {len(sub)} | {rate(sub, 'A', 'transition_exact')} "
                                   f"| {rate(sub, 'A', 'route_optimal')} | {rate(sub, 'B', 'detection_correct')} "
                                   f"| {rate(sub, 'B', 'localization_correct')} | {rate(sub, 'B', 'necessary_update_rate')} "
                                   f"| {rate(sub, 'B', 'route_optimal')} |")
        need = [k for k in ch if (convs[k].get(("B", "necessary_update_rate")) or (0, 0))[1] > 0]
        said = [k for k in need if (convs[k].get(("B", "detection_correct")) or (0, 0))[0] > 0]
        missed = [k for k in need if k not in said]
        out += ["", "**Table 2. Reporting a change vs acting on it (conversations where a route had to change)**", "",
                "| Conversations | n | Necessary updates made |", "|---|---|---|",
                f"| Reported the change (detection correct) | {len(said)} | {rate(said, 'B', 'necessary_update_rate')} |",
                f"| Did not report it | {len(missed)} | {rate(missed, 'B', 'necessary_update_rate')} |", "",
                "**Table 3. Detection / necessary updates by scenario (history and reasoning pooled)**", "",
                "| Scenario | Convs per arm | " + " | ".join(f"{a} detection / updates" for a in ICL_ARMS) + " |",
                "|---|---|" + "---|" * len(ICL_ARMS)]
        for sc in ICL_CHANGED:
            cells = [[k for k in K if meta[k]["scenario"] == sc and meta[k]["condition"] == a] for a in ICL_ARMS]
            if any(cells):
                out.append(f"| {sc} | {len(cells[0])} | " + " | ".join(
                    f"{rate(c, 'B', 'detection_correct')} / {rate(c, 'B', 'necessary_update_rate')}" for c in cells) + " |")
        nc = [k for k in K if meta[k]["scenario"] == "no_change"]
        if nc:
            out += ["", "**Table 4. No-change control: reports no change / replans anyway**", "",
                    "| Reasoning | Convs per arm | " + " | ".join(ICL_ARMS) + " |", "|---|---|" + "---|" * len(ICL_ARMS)]
            for rs in sorted({k[3] for k in nc}):
                cells = [[k for k in nc if k[3] == rs and meta[k]["condition"] == a] for a in ICL_ARMS]
                out.append(f"| {rs} | {len(cells[0])} | " + " | ".join(
                    f"{rate(c, 'B', 'detection_correct')} / {rate(c, 'B', 'unnecessary_replan_rate')}" for c in cells) + " |")
        out += ["", f"Rates pool numerators over denominators across conversations. Preparation answers flagged for review: "
                f"{sum(1 for k in K for p in 'AB' if (convs[k].get((p, 'preparation_needs_review')) or (0, 0))[0] > 0)}.", ""]
    target = os.path.join(os.path.dirname(os.path.abspath(path)), "icl_tables.md")
    open(target, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out)); print(f"wrote {target} ({len(convs)} conversations)")


def main():
    if "--tables" in sys.argv:
        rest = [a for a in sys.argv[1:] if a != "--tables"]
        return icl_tables(rest[0] if rest else "metrics.csv")
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

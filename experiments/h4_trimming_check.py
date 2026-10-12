"""H4 trimming check: were the six failures still in the agent's context when it chose again?

    python experiments/h4_trimming_check.py --grid UNZIPPED_GRID_FOLDER [--grid ...] [--out FILE.md]

The failure streak carries across M0 and M1, but must reach the threshold in
M1, matching explore_metrics. Check the first subsequent non-aborted decision
at the changed source. This checks six specific reports, not retention of all
earlier target observations. Inputs are unzipped confirmatory GRID archives.
--coverage writes portable identities, source hashes and every skip reason.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import explore_agent as A  # noqa: E402


def wilson_lower(k, n, z=2.128):
    if not n:
        return None
    p = k / n
    d = 1 + z * z / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d


def check_run(a):
    ex = a["explore"]
    cu = ex["metrics"]["changed_action_usage"]
    node, lab = cu["node"], cu["action_label"]
    if not node or not lab:
        raise ValueError("missing_changed_pair")
    saved = ex["metrics"]["choices_after_consecutive_failures"]
    steps = [s for e in ex["m0_episodes"] for s in e["steps"]]
    m0n = len(steps)
    steps += [s for e in ex["m1_episodes"] for s in e["steps"]]
    # In these two scenarios the label retains its destination in both phases.
    target = lambda s: s["node"] == node and s["action_label"] == lab and bool(s["chosen"])
    fails, hit, six = [], None, []
    for i, s in enumerate(steps):
        if target(s):
            fails = [] if s["success"] else fails + [i]
            if i >= m0n and hit is None and len(fails) >= 6:
                hit, six = i, fails[-6:]
    decisions = [] if hit is None else [
        i for i in range(hit + 1, len(steps))
        if steps[i]["node"] == node and steps[i]["parse_status"] != "retries_exhausted"]
    broken = sum(bool(target(steps[i])) for i in decisions)
    expected = dict(version="consecutive_failures_v1", n_failures=6,
                    reached_in_m1=hit is not None,
                    reached_at_m1_step=None if hit is None else hit - m0n,
                    decisions_at_source=None if hit is None else len(decisions),
                    broken_choices=None if hit is None else broken,
                    chose_again=None if hit is None else broken > 0)
    if saved != expected:
        raise ValueError("saved_scorer_mismatch")
    result = dict(qualifying=hit is not None, chose_again=saved["chose_again"],
                  m0_carried_failures=sum(i < m0n for i in six),
                  failure_steps=";".join(str(i - m0n) for i in six),
                  decision_m1_step=None, removed_messages=None)
    if hit is None:
        return dict(result, status="not_qualifying")
    if not decisions:
        return dict(result, status="no_later_source_decision")
    dec = decisions[0]
    tr = ex["transcript"]
    ai, si = [], 0
    for k, m in enumerate(tr):
        if m["role"] == "assistant" and si < len(steps) and m["content"] == steps[si]["raw_text"]:
            ai.append(k)
            si += 1
    if len(ai) != len(steps):
        raise ValueError("transcript_step_alignment")
    # Feedback for a step must actually occur before the next decision.
    if any(ai[i] + 1 >= ai[dec] or tr[ai[i] + 1]["role"] != "user" for i in six):
        raise ValueError("missing_failure_feedback")
    hist = [dict(role=m["role"], content=m["content"]) for m in tr[:ai[dec]]]
    cfg = ex["config"]
    kept = A.trim_history(hist, cfg["max_context_tokens_est"], cfg["keep_last_n_turns_min"])
    first_kept = len(hist) - len(kept)
    status = "visible" if all(ai[i] + 1 >= first_kept for i in six) else "trimmed"
    return dict(result, status=status, decision_m1_step=dec - m0n, removed_messages=first_kept)


def check_grid(root):
    root = Path(root)
    records, seen = [], set()
    for f in sorted(root.rglob("pilot_stochastic_active.json")):
        record = dict(grid=root.name, path=f.relative_to(root).as_posix(),
                      sha256=hashlib.sha256(f.read_bytes()).hexdigest())
        records.append(record)
        cf = f.parent / "condition.json"
        if not cf.is_file():
            record.update(status="error", reason="missing_condition")
            continue
        record["condition_sha256"] = hashlib.sha256(cf.read_bytes()).hexdigest()
        try:
            meta, a = json.loads(cf.read_text()), json.loads(f.read_text())
            ins = a["instance"]
            record.update(model=a["model"]["model"], seed=ins["graph_seed"],
                          scenario=ins["condition"], arm=meta["condition"],
                          matched_prep=meta["matched_prep"], repeat=meta["repeat"],
                          history=meta["history"], deterministic=ins["deterministic"])
            identity = tuple(record[k] for k in ("model", "seed", "scenario", "arm",
                             "matched_prep", "repeat", "history", "deterministic"))
            if identity in seen:
                raise ValueError("duplicate_identity")
            seen.add(identity)
            if (record["arm"] != "task_only" or ins["deterministic"]
                    or ins["condition"] not in ("silent_break", "degradation")):
                record["status"] = "out_of_scope"
            else:
                record.update(check_run(a))
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            # Error names only: never copy raw model text or private paths.
            reason = str(exc) if isinstance(exc, ValueError) and str(exc) in {
                "duplicate_identity", "saved_scorer_mismatch", "missing_changed_pair",
                "transcript_step_alignment", "missing_failure_feedback"} else "invalid_input"
            record.update(status="error", reason=reason)
    tally = {s: [sum(r.get("chose_again") is True for r in records if r["status"] == s),
                 sum(r["status"] == s for r in records)] for s in ("visible", "trimmed")}
    models = sorted({r["model"] for r in records if r["status"] in ("visible", "trimmed", "not_qualifying", "no_later_source_decision")})
    counts = dict(Counter(r["status"] for r in records))
    status = "incomplete" if counts.get("error") else (
        "checked" if tally["visible"][1] + tally["trimmed"][1] else "could_not_run")
    return dict(grid=root.name, models=models, status=status, counts=counts,
                tally=tally, records=records)


def check(root):
    """Compatibility interface, now fail explicitly on incomplete/empty checks."""
    report = check_grid(root)
    if report["status"] != "checked" or len(report["models"]) != 1:
        raise ValueError(report["status"])
    return report["models"][0], report["tally"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", action="append", required=True)
    ap.add_argument("--out")
    ap.add_argument("--coverage", help="CSV containing every input identity and status")
    a = ap.parse_args()
    reports = [check_grid(g) for g in a.grid]
    L = ["# H4 trimming check", "",
         "Failure streaks carry across M0 and M1 and reset on target-link success. "
         "The threshold must be reached in M1, as in the saved scorer. "
         "The check rebuilds the first subsequent non-aborted decision at the changed source "
         "with the saved trimming settings. It checks the six qualifying failure reports, "
         "not every earlier target observation or every later decision. Original scores are not rewritten.", "",
         "The k/n entries below are repeat-choice fractions: runs that chose the changed link again / "
         "qualifying runs in the indicated subset, not counts of retained reports. "
         "0/0 means that subset contains no runs. Coverage counts are listed separately.", "",
         "| Grid | Model | Chose again / all qualifying runs | Chose again / runs retaining all six reports | Chose again / runs missing at least one report | Wilson lower bound on repeat-choice rate, all six retained |",
         "|---|---|---|---|---|---|"]
    for report in reports:
        t = report["tally"]
        v, tr = t["visible"], t["trimmed"]
        q = [r for r in report["records"] if r.get("qualifying")]
        lb = wilson_lower(*v)
        L.append(f"| {report['grid']} | {', '.join(report['models']) or 'unknown'} | "
                 f"{sum(r['chose_again'] is True for r in q)}/{len(q)} | {v[0]}/{v[1]} | "
                 f"{tr[0]}/{tr[1]} | {'N/A' if lb is None else f'{lb:.2f}'} |")
    L += ["", "## Coverage", "",
          "| Grid | Inputs | Out of scope | Not qualifying | Checked | No later source decision | Errors | Status |",
          "|---|---|---|---|---|---|---|---|"]
    for report in reports:
        c = report["counts"]
        L.append(f"| {report['grid']} | {len(report['records'])} | {c.get('out_of_scope', 0)} | "
                 f"{c.get('not_qualifying', 0)} | {c.get('visible', 0) + c.get('trimmed', 0)} | "
                 f"{c.get('no_later_source_decision', 0)} | {c.get('error', 0)} | {report['status']} |")
    L += ["", "## Cross-phase qualifiers", "",
          "The previous M1-only checker could miss an M0-carried streak or locate its threshold too late. "
          "These records carry failures from M0; negative failure indices in the coverage file refer to M0.", ""]
    for report in reports:
        for r in report["records"]:
            if r.get("m0_carried_failures"):
                L.append(f"- {r['grid']}, seed {r['seed']}, {r['scenario']}, repeat {r['repeat']}: "
                         f"{r['m0_carried_failures']} M0 failure(s); {r['status']}; "
                         f"chose again: {r['chose_again']}; first subsequent source decision: "
                         f"M1 step {r['decision_m1_step']} (zero-based).")
    L += ["", "Visibility is an observed result of reconstructing these histories, not a guarantee "
          "from FIFO trimming. The six failures need not be adjacent in the transcript. "
          "A qualifier with no later source decision remains in the H4 denominator but has no visibility check. "
          "The existing Wilson calculation (z=2.128) is retained, not a new dependence-adjusted analysis.", "",
          "Reproduce with `python3 -B experiments/h4_trimming_check.py --grid GRID_DIRECTORY` "
          "(repeat `--grid` for each of the six named archives), "
          "`--out REPORT.md --coverage COVERAGE.csv`. The input archives remain outside Git."]
    if a.coverage:
        records = [r for report in reports for r in report["records"]]
        fields = sorted({k for r in records for k in r}) or ["grid", "path", "status"]
        with open(a.coverage, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(records)
    text = "\n".join(L)
    print(text)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text + "\n")
    return 0 if all(r["status"] == "checked" for r in reports) else 1


if __name__ == "__main__":
    sys.exit(main())

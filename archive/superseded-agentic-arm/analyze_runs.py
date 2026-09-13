"""Analyze one or more agentic run files.

Usage:
  python3 analyze_runs.py run1.jsonl [run2.jsonl ...]

For each file it reports:
  - config and facts if the run persisted a summary record
  - the break metrics, recomputed from the step records
  - well-formed rate, share of steps without a malformed fallback
  - belief calibration, stated probabilities against the success rates
    the agent actually experienced up to that report, plus how many
    estimated pairs had never been tried
  - which queried preservation pairs the run never attempted (Note E)
  - the knowing versus doing box from the stored localization answer

Files from older runner versions without the summary tail still work,
seed-7 deterministic facts are assumed for those and flagged.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict

import break_metrics as bm

DEFAULT_FACTS = {"break_pair": ("D", "a2"), "oracle_pre_cost": 4.0,
                 "oracle_post_cost": 5.0}


def load(path):
    steps, beliefs, probes, summary = [], [], None, None
    for line in open(path):
        r = json.loads(line)
        if r.get("type") == "belief":
            beliefs.append(r)
        elif r.get("type") == "probes":
            probes = r["probes"]
        elif r.get("type") == "summary":
            summary = r
        elif "status" in r:
            steps.append(r)
    return steps, beliefs, probes, summary


def empirical_rates(steps, upto_t):
    ok = defaultdict(int)
    n = defaultdict(int)
    for r in steps:
        if r["t"] > upto_t:
            break
        key = f"{r['node']} {r['action']}"
        n[key] += 1
        ok[key] += (r["status"] == "OK")
    return {k: ok[k] / n[k] for k in n}


def belief_calibration(steps, beliefs):
    rows = []
    for b in beliefs:
        est = b.get("estimates") or {}
        if not isinstance(est, dict):
            continue
        rates = empirical_rates(steps, b["t"])
        seen = {k: v for k, v in est.items()
                if k in rates and isinstance(v, (int, float))}
        unseen = [k for k in est if k not in rates]
        mae = (sum(abs(v - rates[k]) for k, v in seen.items()) / len(seen)
               if seen else None)
        rows.append({"phase": b["phase"], "t": b["t"], "mae": mae,
                     "n_scored": len(seen), "n_never_tried": len(unseen)})
    return rows


def preservation_visitedness(steps, probes):
    if not probes or "preservation" not in probes:
        return None
    parsed = probes["preservation"].get("parsed") or {}
    if isinstance(parsed.get("pairs"), list):
        queried = [f"{p.get('node')} {p.get('action')}" for p in parsed["pairs"]]
    elif isinstance(parsed, dict):
        queried = [k for k in parsed if k not in ("status",)]
    else:
        return None
    attempted = {f"{r['node']} {r['action']}" for r in steps}
    return {"queried": queried,
            "never_attempted": [q for q in queried if q not in attempted]}


def analyze(path):
    steps, beliefs, probes, summary = load(path)
    print(f"===== {path} =====")
    if summary:
        cfg, facts = summary.get("config", {}), summary["facts"]
        bp = tuple(facts["break_pair"]) if facts.get("break_pair") else None
        pre_c, post_c = facts["oracle_pre_cost"], facts["oracle_post_cost"]
        print("config:", json.dumps(cfg))
    else:
        bp = DEFAULT_FACTS["break_pair"]
        pre_c, post_c = 4.0, 5.0
        print("no summary record, assuming seed-7 deterministic facts")
    goal_counts = defaultdict(int)
    legal = sorted({(r["node"], r["action"]) for r in steps})
    # goal node: prefer the summary, else infer from the last OK arrival
    goal = None
    if summary:
        goal = None  # metrics need it, take from records below
    for r in steps:
        goal_counts[r["next_node"]] += 1
    # the goal is the node that is arrived at but never acted from
    acted_from = {r["node"] for r in steps}
    arrived = set(goal_counts)
    candidates = arrived - acted_from
    goal = sorted(candidates)[0] if candidates else "F"

    if summary and summary.get("metrics"):
        bm.print_report("metrics (persisted at run time)", summary["metrics"])
    else:
        m = bm.summarize(steps, bp, goal, pre_c, post_c, legal)
        m["coverage"] = m["coverage"].split("/")[0] + "/? (legacy file, " \
            "full legal set unknown, numerator only)"
        bm.print_report("metrics (recomputed, legacy file)", m)

    if bp and not hasattr(bm, "retry_profile"):
        print("  retry profile: unavailable, break_metrics.py on this "
              "machine predates retry_profile, replace that file")
    if bp and hasattr(bm, "retry_profile"):
        rp = bm.retry_profile(steps, bp)
        print(f"  retry profile: encounters {rp['encounters']}, "
              f"switched within visit {rp['switched_within_visit']}/"
              f"{rp['visits_attempting_break']}, "
              f"returned after leaving {rp['returned_after_leaving']}, "
              f"p(retry right after a drop) "
              f"{rp['p_retry_immediately_after_drop']}")

    total = len(steps)
    malformed = sum(1 for r in steps if r.get("note") == "malformed_fallback")
    print(f"  well_formed_rate: {(total - malformed)}/{total}"
          f" = {(total - malformed) / total:.3f}" if total else "  no steps")

    cal = belief_calibration(steps, beliefs)
    if cal:
        for phase in ("pre", "post"):
            rows = [r for r in cal if r["phase"] == phase and r["mae"] is not None]
            if rows:
                avg = sum(r["mae"] for r in rows) / len(rows)
                print(f"  belief MAE vs experienced rates, {phase}: "
                      f"{avg:.3f} over {len(rows)} reports")
        never = sum(r["n_never_tried"] for r in cal)
        if never:
            print(f"  belief reports included never-tried pairs "
                  f"{never} times across {len(cal)} reports")

    vis = preservation_visitedness(steps, probes)
    if vis:
        print(f"  preservation queried pairs never attempted: "
              f"{vis['never_attempted'] or 'none'}")

    if summary and summary.get("knowing_vs_doing"):
        print("  knowing_vs_doing:", json.dumps(summary["knowing_vs_doing"]))
    print()


def aggregate(paths):
    n = det_ok = loc_ok = with_probes = 0
    boxes, covs, p_retries, returns = {}, [], [], 0
    for path in paths:
        steps, beliefs, probes, summary = load(path)
        if not summary:
            continue
        n += 1
        facts = summary["facts"]
        bp = tuple(facts["break_pair"]) if facts.get("break_pair") else None
        box = summary.get("knowing_vs_doing") or {}
        if box:
            boxes[box.get("box")] = boxes.get(box.get("box"), 0) + 1
        cov = summary["metrics"].get("coverage", "")
        if "/" in str(cov):
            covs.append(int(str(cov).split("/")[0]))
        if probes:
            with_probes += 1
            det = (probes.get("detection", {}).get("parsed") or {})
            det_ok += det.get("changed") is True
            loc = (probes.get("localization", {}).get("parsed") or {})
            if bp:
                loc_ok += (loc.get("node") == bp[0]
                           and loc.get("action") == bp[1])
        if bp and hasattr(bm, "retry_profile"):
            rp = bm.retry_profile(steps, bp)
            if rp["p_retry_immediately_after_drop"] is not None:
                p_retries.append(rp["p_retry_immediately_after_drop"])
            returns += rp["returned_after_leaving"]
    print("===== AGGREGATE =====")
    print(f"  runs with summary: {n}, with probes: {with_probes}")
    if with_probes:
        print(f"  detection correct: {det_ok}/{with_probes}, "
              f"localization correct: {loc_ok}/{with_probes}")
    if boxes:
        print(f"  knowing_vs_doing boxes: {boxes}")
    if covs:
        print(f"  coverage numerator mean: {sum(covs) / len(covs):.1f} "
              f"over {len(covs)} runs")
    if p_retries:
        print(f"  p(retry right after drop) mean: "
              f"{sum(p_retries) / len(p_retries):.3f}, "
              f"total returns after leaving: {returns}")


if __name__ == "__main__":
    argv = sys.argv[1:]
    agg = "--aggregate" in argv
    paths = [a for a in argv if a != "--aggregate"]
    if not paths:
        print(__doc__)
        sys.exit(0)
    for p in paths:
        analyze(p)
    if agg:
        aggregate(paths)

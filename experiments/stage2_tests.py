"""Confirmatory H2, H3 and H5 on the stage-2 two-turn runs (stochastic silent break, held-out seeds).

    python experiments/stage2_tests.py <stage-2 run folder> [<output folder>]

Reads <run folder>/<model>_<condition>_s<seed>/pilot_*.json, as written by stage2_runner.py, and writes
confirmatory_tests.md and stage2_runs.csv to the output folder (default: the run folder).

Analysis plan (Appendix A): the seed is the unit, one answer per instance, and an answer that does not
parse counts as incorrect. Differences are paired over seeds that have both runs, with a 95% percentile
bootstrap interval (10,000 resamples), a one-sided bootstrap p-value and Holm correction across the three
models within each hypothesis.
  H2  Localization, counts given (counts2) minus core (core2), K=10     prediction > 0
  H3  optimal Period B route, single-turn (core1) minus two-turn (core2) prediction > 0
  H5  Localization, K=20 (k20) minus K=5 (k5)                           prediction > 0
Secondary (plan rule 7): the same tests over seeds where both answers parsed. Runs whose reasoning
control was not honoured ("off" but reasoning tokens > 0) are counted.
Stdlib only.
"""
import csv, glob, json, os, random, sys
from collections import defaultdict

HYPS = [("H2", "localization", "counts2", "core2", "Localization, counts given minus core (K=10)"),
        ("H3", "route", "core1", "core2", "Optimal route, single-turn minus two-turn (K=10)"),
        ("H5", "localization", "k20", "k5", "Localization, K=20 minus K=5")]
NAMES = {"sol": "GPT-5.6 Sol", "haiku": "Claude Haiku 5.5", "deepseek": "DeepSeek V4.1 Flash"}
B, ALPHA = 10_000, 0.05
UNPARSED = {None, "malformed_json", "invalid_object", "too_long"}   # parser statuses: no answer was read


def load(root):
    rows = []
    for f in sorted(glob.glob(os.path.join(root, "*", "pilot_*.json"))):
        tag = os.path.basename(os.path.dirname(f))
        model, cond, seed = tag.split("_")
        a = json.load(open(f, encoding="utf-8"))
        probes = a.get("probes") or {}
        loc = ((probes.get("localization") or {}).get("scored") or {}).get("correct")
        route = ((probes.get("adaptation") or {}).get("scored") or {}).get("is_optimal")
        loc_status = ((probes.get("localization") or {}).get("scored") or {}).get("status")
        route_status = ((probes.get("adaptation") or {}).get("scored") or {}).get("status")
        det = ((probes.get("detection") or {}).get("parsed") or {}).get("changed")
        rc = a.get("reasoning_control") or {}
        rows.append({"model": model, "condition": cond, "seed": int(seed[1:]),
                     "localization": 1 if loc is True else 0,       # parse failure or wrong = 0
                     "route": 1 if route is True else 0,
                     "localization_parsed": int(loc_status == "ok"),
                     "route_parsed": int(route_status not in UNPARSED),
                     "route_status": route_status,
                     "detection_changed": None if det is None else int(det is True),
                     "reasoning_mode": rc.get("mode"), "reasoning_tokens": rc.get("reasoning_tokens_total"),
                     "violation": rc.get("violation"), "commit": (a.get("env") or {}).get("git_head")})
    return rows


def paired_test(diffs, rng):
    n = len(diffs)
    est = sum(diffs) / n
    boots = sorted(sum(rng.choice(diffs) for _ in range(n)) / n for _ in range(B))
    lo, hi = boots[int(0.025 * B)], boots[int(0.975 * B) - 1]
    p = (1 + sum(b <= 0 for b in boots)) / (B + 1)                 # one-sided, prediction > 0
    return est, lo, hi, p


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - rank) * ps[i]))
        adj[i] = run
    return adj


def main():
    root = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else root
    os.makedirs(out, exist_ok=True)
    rows = load(root)
    if not rows:
        sys.exit(f"no pilot_*.json under {root}")
    with open(os.path.join(out, "stage2_runs.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    by = defaultdict(dict)
    for r in rows:
        by[(r["model"], r["condition"])][r["seed"]] = r
    models = [m for m in NAMES if any(k[0] == m for k in by)]
    rng = random.Random(0)
    lines = ["# Confirmatory tests of H2, H3 and H5 (two-turn ICL)", "",
             "Stochastic silent break, eight-node family, held-out seeds, reasoning off, one answer per "
             "instance; an unparsed answer counts as incorrect. Paired differences over seeds with both runs, "
             f"95% percentile bootstrap ({B:,} resamples, seed 0), one-sided bootstrap p, Holm across models. "
             "Script: experiments/stage2_tests.py.", "",
             "## Primary: unparsed answers count as incorrect", "",
             "| Hyp. | Quantity | Model | Seeds | Treatment | Comparison | Difference | 95% interval | p (Holm) | Reading |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    def table(only_parsed):
      out_lines = []
      for hyp, metric, treat, comp, label in HYPS:
        res = []
        for m in models:
            t, c = by.get((m, treat), {}), by.get((m, comp), {})
            seeds = sorted(set(t) & set(c))
            if only_parsed:
                seeds = [x for x in seeds if t[x][metric + "_parsed"] and c[x][metric + "_parsed"]]
            if not seeds:
                continue
            diffs = [t[s][metric] - c[s][metric] for s in seeds]
            res.append((m, seeds, sum(t[s][metric] for s in seeds) / len(seeds),
                        sum(c[s][metric] for s in seeds) / len(seeds), *paired_test(diffs, rng)))
        adj = holm([r[7] for r in res])
        for (m, seeds, tr, cr, est, lo, hi, p), pa in zip(res, adj):
            reading = "supported" if pa < ALPHA else "not shown"
            out_lines.append(f"| {hyp} | {label} | {NAMES[m]} | {len(seeds)} | {tr:.2f} | {cr:.2f} | {est:+.2f} | "
                             f"[{lo:+.2f}, {hi:+.2f}] | {pa:.3f} | {reading} |")
      return out_lines
    header = ["| Hyp. | Quantity | Model | Seeds | Treatment | Comparison | Difference | 95% interval | p (Holm) | Reading |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    lines += table(False)
    lines += ["", "## Secondary: seeds where both answers parsed", ""] + header + table(True)
    lines += ["", "## Runs per model and condition", "",
              "| Model | Condition | Runs | Reports a change | Localization | Localization unparsed | Optimal route | Route through broken link | Route unparsed | Reasoning off violated |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for m in models:
        for cond in ("core2", "counts2", "core1", "k5", "k20"):
            rs = list(by.get((m, cond), {}).values())
            if rs:
                n = len(rs)
                lines.append(f"| {NAMES[m]} | {cond} | {n} | {sum(r['detection_changed'] or 0 for r in rs) / n:.2f} | "
                             f"{sum(r['localization'] for r in rs) / n:.2f} | {n - sum(r['localization_parsed'] for r in rs)} | "
                             f"{sum(r['route'] for r in rs) / n:.2f} | {sum(r['route_status'] == 'silent_broken_edge' for r in rs)} | "
                             f"{n - sum(r['route_parsed'] for r in rs)} | {sum(bool(r['violation']) for r in rs)} |")
    unrecorded = sum(r["reasoning_mode"] is None for r in rows)
    commits = sorted({r["commit"] for r in rows if r["commit"]})
    lines += ["", f"Runs: {len(rows)}. Runs without a recorded reasoning control (made before the fix): "
                  f"{unrecorded}. Commits: {', '.join(c[:7] for c in commits) or 'not recorded'}."]
    open(os.path.join(out, "confirmatory_tests.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

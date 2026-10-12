"""H4 and H6 under the registered analysis rules, from the confirmatory agentic tables on main.

    python experiments/h4_h6_uncertainty.py [--out runs/results/confirmatory/agentic_h4_h6/uncertainty.md]

Inputs: runs/results/confirmatory/agentic_h4_h6/<model>/<grid>/agentic_runs.csv (grids no_prep and matched_prep).
H4 (rule 3): task-only, stochastic silent break and degradation; among runs that reached six consecutive failures of
the changed link (h4_reached), the share that chose it again (h4_chose_again). One-sided Wilson lower bound with
Bonferroni over the three models (z = 2.128); supported if the bound exceeds 0.10 with at least 10 qualifying runs.
H6 (rule 3): model-first minus task-only on the H4 outcome, paired over seed and scenario where both arms qualify;
one-sided percentile bootstrap (10,000 resamples, seed 0) of a mean difference below 0, Holm over models.
These replace the Clopper-Pearson and Fisher tests of confirmatory_tests.md, as the registered plan specifies.
Stdlib only.
"""
import argparse, csv, glob, math, os, random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "runs", "results", "confirmatory", "agentic_h4_h6")
b = lambda v: v in (True, "True", "true", "1")


def wilson_lower(k, n, z=2.128):
    if not n:
        return None
    p = k / n
    d = 1 + z * z / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - r) * ps[i]))
        adj[i] = run
    return adj


def rows(model, grid):
    f = os.path.join(BASE, model, grid, "agentic_runs.csv")
    return [r for r in csv.DictReader(open(f, encoding="utf-8")) if r["mode"] == "sto"
            and r["scenario"] in ("silent_break", "degradation")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(BASE, "uncertainty.md"))
    a = ap.parse_args()
    models = sorted(d for d in os.listdir(BASE) if os.path.isdir(os.path.join(BASE, d)))
    L = ["# H4 and H6 under the registered analysis rules", "",
         "Script: experiments/h4_h6_uncertainty.py. Inputs: agentic_runs.csv per model and grid in this folder.", ""]
    for grid in ("no_prep", "matched_prep"):
        L += [f"## Grid: {grid}", "", "| Model | H4 chose again / qualifying | Share | Wilson lower bound (Bonferroni) | H4 | "
              "H6 pairs | H6 mean difference (model-first minus task-only) | 95% interval | p (Holm) | H6 |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        res = []
        for m in models:
            R = rows(m, grid)
            q = [r for r in R if r["arm"] == "task_only" and b(r["h4_reached"])]
            k, n = sum(b(r["h4_chose_again"]) for r in q), len(q)
            lb = wilson_lower(k, n)
            h4 = "too few" if n < 10 else ("supported" if lb > 0.10 else "not shown")
            by = {}
            for r in R:
                if b(r["h4_reached"]) and r["arm"] in ("task_only", "model_first"):
                    by.setdefault((r["seed"], r["scenario"]), {})[r["arm"]] = int(b(r["h4_chose_again"]))
            d = [v["model_first"] - v["task_only"] for v in by.values() if len(v) == 2]
            rng = random.Random(0)
            boots = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(10000)) if d else []
            mean = sum(d) / len(d) if d else float("nan")
            p = (1 + sum(x >= 0 for x in boots)) / (len(boots) + 1) if boots else 1.0
            ci = (boots[249], boots[9749]) if boots else (float("nan"),) * 2
            res.append([m, k, n, lb, h4, len(d), mean, ci, p])
        for r, ph in zip(res, holm([r[8] for r in res])):
            m, k, n, lb, h4, npair, mean, ci, p = r
            h6 = "supported" if ph < 0.05 else "not shown"
            L.append(f"| {m} | {k}/{n} | {k / n if n else float('nan'):.2f} | {lb:.2f} | {h4} | {npair} | {mean:+.2f} | "
                     f"[{ci[0]:+.2f}, {ci[1]:+.2f}] | {ph:.3f} | {h6} |")
        L.append("")
    L.append("H6 pairs are seed and scenario combinations in which both arms reached six consecutive failures. With 8 to 22 "
             "pairs the paired test has little power, so \"not shown\" does not mean \"no effect\".")
    open(a.out, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()

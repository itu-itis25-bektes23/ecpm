"""H4 secondary analyses: localization-conditioned H4 and a seed-clustered sensitivity bound.

    python experiments/h4_secondary.py --grid UNZIPPED_GRID [--grid ...] [--out table.md]

Task-only runs, stochastic silent break and degradation, as the registered H4. For each confirmatory grid and model:
the registered H4 count with its one-sided Wilson bound (Bonferroni over three models, z = 2.128); the same measure
among qualifying runs whose localization probe was correct; and a seed-clustered bootstrap lower bound (10,000
resamples of seeds, seed 0, one-sided at 0.05/3), because a seed can contribute one run per scenario. The Wilson
bound stays the registered analysis; the clustered bound is a sensitivity check. Inputs are the GRID zips kept
outside the repository.
"""
import argparse, collections, math, os, random, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import summarize_agentic_runs as S  # noqa: E402
b = lambda v: v is True or v == "True"


def wilson(k, n, z=2.128):
    if not n:
        return None
    p = k / n
    d = 1 + z * z / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", action="append", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    L = ["| Grid | Model | H4: chose again / qualifying | Wilson bound | Seeds (repeated) | Seed-clustered bound | "
         "Localized and chose again / localized | Wilson bound, localized |", "|---|---|---|---|---|---|---|---|"]
    for root in a.grid:
        R = [r for r in S.load(root) if r["arm"] == "task_only" and r["mode"] == "sto"
             and r["scenario"] in ("silent_break", "degradation")]
        if not R:
            continue
        q = [r for r in R if b(r["h4_reached"])]
        k, n = sum(b(r["h4_chose_again"]) for r in q), len(q)
        by = collections.defaultdict(list)
        for r in q:
            by[r["seed"]].append(int(b(r["h4_chose_again"])))
        keys, rng, boots = list(by), random.Random(0), []
        for _ in range(10000):
            xs = [x for s in (rng.choice(keys) for _ in keys) for x in by[s]]
            boots.append(sum(xs) / len(xs))
        boots.sort()
        lb_c = boots[int(0.05 / 3 * len(boots))]
        ql = [r for r in q if b(r["localization"])]
        kl = sum(b(r["h4_chose_again"]) for r in ql)
        f = lambda x: "–" if x is None else f"{x:.2f}"
        L.append(f"| {os.path.basename(os.path.normpath(root))} | {R[0]['model']} | {k}/{n} | {f(wilson(k, n))} | "
                 f"{len(by)} ({sum(1 for v in by.values() if len(v) > 1)}) | {lb_c:.2f} | {kl}/{len(ql)} | {f(wilson(kl, len(ql)))} |")
    text = "\n".join(L)
    print(text)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text + "\n")


if __name__ == "__main__":
    main()

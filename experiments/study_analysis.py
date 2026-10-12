"""Analysis for study plan v1 (docs/STUDY_PLAN_v1.md), the same script for exploratory and confirmatory rounds.

    python experiments/study_analysis.py --round exploratory --acting DIR [--acting ...] \\
        [--bridge DIR/bridge.csv] [--icl-export DIR] --out DIR

--acting   folders holding acting run folders (batch folders or unzipped GRID folders)
--bridge   bridge.csv from experiments/bridge_probes.py
--icl-export  folder with one subfolder per model holding metrics.csv.gz (experiments/study_icl.py export)

Claims (one-sided, per plan):
  C1  acting, task-only, nudge off, stochastic silent break and degradation: share of qualifying runs (six consecutive
      failures of the changed link reached in M1) that chose the link again; Wilson lower bound with Bonferroni over
      models > 0.10, tested with at least 10 qualifying runs.
  C2  acting, task-only, same cells: share of runs reaching six consecutive failures, nudge on against off, paired by
      seed and cell; exact one-sided McNemar, Holm over models.
  C3  bridge decisions, all models pooled: retrying with the complete log against the agent's own log; exact one-sided
      McNemar. Per-model counts are descriptive.
Secondary, descriptive: nudge cost under no change and irrelevant; detection and localization by cell, prompt or
arm, in both families, against evidence-only references on the same views; exposure.
Writes DIR/report.md and CSVs. Stdlib only.
"""
import argparse, csv, glob, gzip, json, math, os, sys
from collections import defaultdict
from math import comb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
Z_BONF3 = 2.1280            # one-sided z for alpha 0.05/3
_b = lambda v: v is True or v == "True" or v == "true"


def wilson_lower(k, n, z=Z_BONF3):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d


def mcnemar_one_sided(b, c):
    """P(X >= b | n = b + c, p = 1/2): evidence that b > c."""
    n = b + c
    if n == 0:
        return 1.0
    return sum(comb(n, i) for i in range(b, n + 1)) / 2 ** n


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - rank) * ps[i]))
        adj[i] = run
    return adj


def short(model):
    return model.split("/")[-1]


# ------------------------------------------------------------------------------------------------- loading
def acting_rows(dirs, seeds):
    import summarize_agentic_runs as S
    rows = []
    for d in dirs:
        rows += S.load(d)
    seen, out = set(), []
    for r in rows:
        key = (r["model"], r["seed"], r["mode"], r["scenario"], r["arm"], bool(_b(r.get("nudge"))), r.get("repeat", 0))
        if r["seed"] in seeds and key not in seen:
            seen.add(key)
            out.append(r)
    return out


def icl_rows(export_dir):
    rows = []
    for f in sorted(glob.glob(os.path.join(export_dir, "*", "metrics.csv.gz"))):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            rows += [r for r in csv.DictReader(fh) if r["metric"] in (
                "detection_correct", "localization_correct", "route_optimal",
                "updating_necessary_update_correct", "updating_necessary_update_eligible") and r["period"] == "B"]
    return rows


# ------------------------------------------------------------------------------------------------- claims
def claim_c1(rows):
    out = []
    for m in sorted({r["model"] for r in rows}):
        q = [r for r in rows if r["model"] == m and r["arm"] == "task_only" and not _b(r.get("nudge"))
             and r["mode"] == "sto" and r["scenario"] in ("silent_break", "degradation") and _b(r["h4_reached"])]
        k, n = sum(_b(r["h4_chose_again"]) for r in q), len(q)
        lb = wilson_lower(k, n)
        verdict = "too few" if n < 10 else ("holds" if lb is not None and lb > 0.10 else "not shown")
        out.append(dict(model=m, chose_again=k, qualifying=n, share=k / n if n else None, lower_bound=lb, verdict=verdict))
    return out


def claim_c2(rows):
    out = []
    for m in sorted({r["model"] for r in rows}):
        cell = defaultdict(dict)
        for r in rows:
            if (r["model"] == m and r["arm"] == "task_only" and r["mode"] == "sto"
                    and r["scenario"] in ("silent_break", "degradation")):
                cell[(r["seed"], r["scenario"])][bool(_b(r.get("nudge")))] = _b(r["h4_reached"])
        pairs = [(v[False], v[True]) for v in cell.values() if False in v and True in v]
        b = sum(off and not on for off, on in pairs)
        c = sum(on and not off for off, on in pairs)
        out.append(dict(model=m, pairs=len(pairs), reach_off=sum(o for o, _ in pairs), reach_on=sum(n for _, n in pairs),
                        off_only=b, on_only=c, p=mcnemar_one_sided(b, c)))
    for r, pa in zip(out, holm([r["p"] for r in out])):
        r["p_holm"] = pa
        r["verdict"] = "holds" if pa < 0.05 else "not shown"
    return out


def claim_c3(bridge_csv):
    rows = list(csv.DictReader(open(bridge_csv, encoding="utf-8")))
    valid = [r for r in rows if r["own_reuse"] in ("True", "False") and r["full_reuse"] in ("True", "False")]
    per = []
    for m in sorted({r["model"] for r in valid}) + ["pooled"]:
        sub = valid if m == "pooled" else [r for r in valid if r["model"] == m]
        b = sum(r["own_reuse"] == "True" and r["full_reuse"] == "False" for r in sub)
        c = sum(r["full_reuse"] == "True" and r["own_reuse"] == "False" for r in sub)
        per.append(dict(model=m, decisions=len(sub), own_reuse=sum(r["own_reuse"] == "True" for r in sub),
                        full_reuse=sum(r["full_reuse"] == "True" for r in sub), own_only=b, full_only=c,
                        p=mcnemar_one_sided(b, c)))
    for r in per:
        r["verdict"] = ("holds" if r["p"] < 0.05 else "not shown") if r["model"] == "pooled" else "descriptive"
    return per, len(rows) - len(valid)


# ------------------------------------------------------------------------------------------------- secondary
def nudge_cost(rows):
    out = []
    for m in sorted({r["model"] for r in rows}):
        for scen in ("no_change", "irrelevant"):
            cell = defaultdict(dict)
            for r in rows:
                if r["model"] == m and r["scenario"] == scen:
                    cell[(r["seed"], r["mode"], r["arm"])][bool(_b(r.get("nudge")))] = r
            for metric in ("goal_success_m1", "steps_m1", "regret_m1"):
                d = [float(v[True][metric]) - float(v[False][metric]) for v in cell.values()
                     if False in v and True in v and v[True].get(metric) not in (None, "")
                     and v[False].get(metric) not in (None, "")]
                if len(d) > 1:
                    mean = sum(d) / len(d)
                    sd = math.sqrt(sum((x - mean) ** 2 for x in d) / (len(d) - 1))
                    half = 1.96 * sd / math.sqrt(len(d))
                    flag = metric == "goal_success_m1" and mean < -0.10
                    out.append(dict(model=m, scenario=scen, metric=metric, pairs=len(d), difference=mean,
                                    low=mean - half, high=mean + half, cost=flag))
    return out


def acting_noticing(rows):
    agg = defaultdict(lambda: [0, 0, 0, 0])
    for r in rows:
        if _b(r.get("nudge")):
            continue
        k = (r["model"], r["mode"], r["scenario"], r["arm"])
        if r.get("detection") not in (None, ""):
            agg[k][0] += _b(r["detection"]); agg[k][1] += 1
        if r.get("localization") not in (None, ""):
            agg[k][2] += _b(r["localization"]); agg[k][3] += 1
    return agg


def exposure(rows):
    agg = defaultdict(lambda: [0, 0, 0, 0])
    for r in rows:
        if _b(r.get("nudge")) or r["scenario"] in ("no_change",) or r.get("exposed") in (None, ""):
            continue
        k = (r["model"], "exposed" if _b(r["exposed"]) else "not exposed")
        if r.get("detection") not in (None, ""):
            agg[k][0] += _b(r["detection"]); agg[k][1] += 1
        if r.get("localization") not in (None, ""):
            agg[k][2] += _b(r["localization"]); agg[k][3] += 1
    return agg


def reading_noticing(rows):
    agg = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for r in rows:
        k = (r["model"], r["mode"], r["scenario"], r["condition"])
        num = 0 if r["numerator"] in ("", "null") else float(r["numerator"])
        den = 0 if r["denominator"] in ("", "null") else float(r["denominator"])
        agg[k][r["metric"]][0] += num
        agg[k][r["metric"]][1] += den
    return agg


def references(seeds):
    """Localization by the evidence-only references, on the exact prompt views the ICL arm shows."""
    os.environ["ECPM_ICL_SEEDS"] = ",".join(map(str, seeds))
    import icl_expanded as X, icl_study_seeds
    icl_study_seeds.apply(X)
    sys.path.insert(0, os.path.join(ROOT, "experiments"))
    import baseline_k_sweep as K
    agg = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for seed in seeds:
        for mode in ("det", "sto"):
            for scen in X.SCENARIOS:
                if mode == "det" and scen == "degradation" or scen == "no_change":
                    continue
                try:
                    w = X._base_world(seed, mode, scen)
                except ValueError:
                    continue
                truth = tuple(w["true_changes"][0]) if w.get("true_changes") else None
                pv, det = w["visible"], mode == "det"
                scores = K.pair_scores(pv, det)
                refs = K.references(pv, det)
                picks = {"rate": K.ranked(scores["rate"])[0] if scores["rate"] else None,
                         **{n: (refs.get(n) or {}).get("loc") for n in ("transition", "bayes", "generator")}}
                for name, pick in picks.items():
                    agg[(mode, scen)][name][1] += 1
                    agg[(mode, scen)][name][0] += int(truth is not None and pick is not None and tuple(pick) == truth)
    return agg


# ------------------------------------------------------------------------------------------------- report
def pct(k, n):
    return "–" if not n else f"{100 * k / n:.0f}% ({int(k)}/{int(n)})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", required=True)
    ap.add_argument("--acting", action="append", default=[])
    ap.add_argument("--bridge")
    ap.add_argument("--icl-export")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-references", action="store_true")
    ap.add_argument("--seed-limit", type=int, default=0, help="testing only: the first N seeds")
    a = ap.parse_args()
    seeds = json.load(open(os.path.join(ROOT, "runs", "study_v1_seeds.json")))[a.round]
    seeds = seeds[:a.seed_limit] if a.seed_limit else seeds
    os.makedirs(a.out, exist_ok=True)
    L = [f"# Study v1, {a.round} round", "",
         f"Seeds: {len(seeds)} ({', '.join(map(str, seeds))}). Claims and tests as in docs/STUDY_PLAN_v1.md."
         + (" **Exploratory round: these numbers guide the design and test nothing.**" if a.round != "confirmatory" else ""),
         ""]
    rows = acting_rows(a.acting, set(seeds)) if a.acting else []
    if rows:
        with open(os.path.join(a.out, "acting_runs.csv"), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        L += [f"Acting runs: {len(rows)}. Billed cost: ${sum(float(r.get('billed_cost') or 0) for r in rows):.2f}.", "",
              "## C1. Choosing the link again after six consecutive failures", "",
              "| Model | Chose again / qualifying | Share | Lower bound (Wilson, Bonferroni) | Verdict |", "|---|---|---|---|---|"]
        for r in claim_c1(rows):
            share = "–" if r["share"] is None else f"{r['share']:.2f}"
            lb = "–" if r["lower_bound"] is None else f"{r['lower_bound']:.2f}"
            L.append(f"| {short(r['model'])} | {r['chose_again']}/{r['qualifying']} | {share} | {lb} | {r['verdict']} |")
        L += ["", "## C2. The nudge: runs reaching six consecutive failures, nudge on against off", "",
              "| Model | Seed-cell pairs | Reached, off | Reached, on | Off only | On only | p (Holm) | Verdict |",
              "|---|---|---|---|---|---|---|---|"]
        for r in claim_c2(rows):
            L.append(f"| {short(r['model'])} | {r['pairs']} | {r['reach_off']} | {r['reach_on']} | {r['off_only']} | "
                     f"{r['on_only']} | {r['p_holm']:.4f} | {r['verdict']} |")
        L += ["", "## Nudge cost (no change and irrelevant), nudge on minus off", "",
              "| Model | Scenario | Measure | Pairs | Difference | 95% interval | Cost flag |", "|---|---|---|---|---|---|---|"]
        for r in nudge_cost(rows):
            L.append(f"| {short(r['model'])} | {r['scenario']} | {r['metric']} | {r['pairs']} | {r['difference']:+.3f} | "
                     f"[{r['low']:+.3f}, {r['high']:+.3f}] | {'yes' if r['cost'] else ''} |")
        L += ["", "## Acting: detection and localization by cell and prompt (nudge off)", "",
              "| Model | Mode | Scenario | Prompt | Detection | Localization |", "|---|---|---|---|---|---|"]
        for (m, mo, sc, arm), v in sorted(acting_noticing(rows).items()):
            L.append(f"| {short(m)} | {mo} | {sc} | {arm} | {pct(v[0], v[1])} | {pct(v[2], v[3])} |")
        L += ["", "## Acting: exposure (nudge off, changed scenarios)", "",
              "| Model | Runs | Detection | Localization |", "|---|---|---|---|"]
        for (m, ex), v in sorted(exposure(rows).items()):
            L.append(f"| {short(m)} | {ex} | {pct(v[0], v[1])} | {pct(v[2], v[3])} |")
    if a.bridge and os.path.exists(a.bridge):
        per, bad = claim_c3(a.bridge)
        L += ["", "## C3. The bridge: retrying with the complete log against the agent's own log", "",
              "| Model | Decisions | Retry, own log | Retry, complete log | Own only | Complete only | p | Verdict |",
              "|---|---|---|---|---|---|---|---|"]
        for r in per:
            L.append(f"| {r['model'] if r['model'] == 'pooled' else short(r['model'])} | {r['decisions']} | {r['own_reuse']} | "
                     f"{r['full_reuse']} | {r['own_only']} | {r['full_only']} | {r['p']:.4f} | {r['verdict']} |")
        L.append(f"\nDecisions without a valid action in either probe: {bad}.")
    if a.icl_export and os.path.isdir(a.icl_export):
        agg = reading_noticing(icl_rows(a.icl_export))
        L += ["", "## Reading: detection, localization, routes and necessary updates (histories pooled)", "",
              "| Model | Mode | Scenario | Arm | Detection | Localization | Optimal routes | Necessary updates |",
              "|---|---|---|---|---|---|---|---|"]
        for (m, mo, sc, arm), v in sorted(agg.items()):
            L.append(f"| {short(m)} | {mo} | {sc} | {arm} | {pct(*v['detection_correct'])} | {pct(*v['localization_correct'])} | "
                     f"{pct(*v['route_optimal'])} | {pct(v['updating_necessary_update_correct'][0], v['updating_necessary_update_eligible'][0])} |")
    if not a.no_references:
        ref = references(seeds)
        L += ["", "## Evidence-only references: localization on the same views (K = 10)", "",
              "| Mode | Scenario | Rate counter | Transition counter | Bayesian | Generator-aware |", "|---|---|---|---|---|---|"]
        for (mo, sc), v in sorted(ref.items()):
            L.append(f"| {mo} | {sc} | " + " | ".join(pct(*v[n]) for n in ("rate", "transition", "bayes", "generator")) + " |")
    open(os.path.join(a.out, "report.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()

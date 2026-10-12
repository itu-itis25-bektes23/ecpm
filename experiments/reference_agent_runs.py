"""Run the evidence-only reference agent (reference_agent.py) on a seed set, with the agentic arm's settings.

    python experiments/reference_agent_runs.py --round exploratory [--out DIR]
    python experiments/reference_agent_runs.py --seeds 33,34,35 --modes sto --scenarios silent_break,degradation --out DIR

Same worlds (run_pilot.make_pair, matched), 4 M0 and 4 M1 episodes, H = 20, change not announced. Metrics come from
explore_metrics, the functions the language-model runs use, so the rows are directly comparable: M1 goal success,
mean steps and regret, the H4 measure (choices of the changed link after six consecutive failures), the decision lag
of the first switch after feedback, and exposure. No API calls; minutes for a full seed set. Stdlib only.
"""
import argparse, csv, json, os, statistics, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import run_pilot, explore_agent as E, explore_metrics as M, reference_agent as R  # noqa: E402

SCEN = {"det": ["no_change", "irrelevant", "silent_break", "hard_removal", "redirect"],
        "sto": ["no_change", "irrelevant", "silent_break", "hard_removal", "redirect", "degradation"]}


def one(seed, mode, scen):
    inst = run_pilot.make_pair(seed, scen, deterministic=(mode == "det"), matched=True)
    cfg = E.ExploreConfig(max_episodes_m0=4, max_episodes_m1=4, max_steps_per_episode=20, seed=seed)
    ag = R.ReferenceAgent(inst.labels, inst.m0.goal, inst.start, cfg.max_steps_per_episode, deterministic=(mode == "det"))
    res = E.run_explore_instance(inst, cfg, node_policy_fn=ag.factory)
    m = M.compute_explore_metrics(inst, res["m0_episodes"], res["m1_episodes"])
    h4 = m.get("choices_after_consecutive_failures") or {}
    cu = m.get("changed_action_usage") or {}
    sw = m.get("changed_action_switch") or {}
    return dict(seed=seed, mode=mode, scenario=scen, goal_success_m1=m.get("goal_success_rate_m1"),
                steps_m1=(m.get("steps_to_goal_m1") or {}).get("mean"), regret_m1=m.get("route_regret_m1"),
                h4_reached=bool(h4.get("reached_in_m1")), h4_chose_again=bool(h4.get("chose_again")),
                decision_lag=sw.get("decision_lag"), switch_status=sw.get("status"),
                exposed=cu.get("m0_route_uses"),
                explore_steps=sum(1 for _, _, w in ag.decisions if w.startswith("explore")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round")
    ap.add_argument("--seeds")
    ap.add_argument("--modes", default="det,sto")
    ap.add_argument("--scenarios", default="all")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.round:
        seeds = json.load(open(os.path.join(ROOT, "runs", "study_v1_seeds.json")))[a.round]
    else:
        seeds = [int(x) for x in a.seeds.split(",")]
    out = a.out or os.path.join(ROOT, "runs", "results", "reference_agent", a.round or "custom")
    os.makedirs(out, exist_ok=True)
    rows = []
    for mode in a.modes.split(","):
        for scen in SCEN[mode] if a.scenarios == "all" else [s for s in a.scenarios.split(",") if s in SCEN[mode]]:
            for s in seeds:
                rows.append(one(s, mode, scen))
    with open(os.path.join(out, "reference_runs.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    L = [f"# Evidence-only reference agent", "",
         f"Seeds: {seeds}. Agent: reference_agent.py. Runner: experiments/reference_agent_runs.py. Same worlds, "
         "episodes, step budget and metric functions as the language-model agents.", "",
         "| Mode | Scenario | Runs | M1 goal success | Mean steps M1 | H4: chose again / qualifying | Median decision lag | Exposed runs |",
         "|---|---|---|---|---|---|---|---|"]
    for mode in a.modes.split(","):
        for scen in SCEN[mode]:
            sub = [r for r in rows if r["mode"] == mode and r["scenario"] == scen]
            if not sub:
                continue
            gs = [r["goal_success_m1"] for r in sub if r["goal_success_m1"] is not None]
            st = [r["steps_m1"] for r in sub if r["steps_m1"] is not None]
            q = [r for r in sub if r["h4_reached"]]
            lag = [r["decision_lag"] for r in sub if isinstance(r["decision_lag"], (int, float))]
            L.append(f"| {mode} | {scen} | {len(sub)} | {statistics.mean(gs):.2f} | "
                     f"{(statistics.mean(st) if st else float('nan')):.1f} | "
                     f"{sum(r['h4_chose_again'] for r in q)}/{len(q)} | "
                     f"{(statistics.median(lag) if lag else '–')} | {sum(bool(r['exposed']) for r in sub)} |")
    open(os.path.join(out, "summary.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()

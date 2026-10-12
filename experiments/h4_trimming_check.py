"""H4 trimming check: were the six failures still in the agent's context when it chose again?

    python experiments/h4_trimming_check.py --grid UNZIPPED_GRID_FOLDER [--grid ...] [--out FILE.md]

For every task-only run of a confirmatory H4/H6 grid (stochastic silent break and degradation) that reached six
consecutive failures of the changed link in M1, it takes the first decision at the changed node after the sixth
failure, rebuilds the history the agent was sent at that decision with explore_agent.trim_history and the run's own
settings, and checks whether the reports of all six failures were still in it. H4 is then given separately for runs
where all six were visible and runs where some were trimmed away. Counting matches H4 (failures counted across M1
episodes, reset on a success of the link). Inputs are the GRID zips kept outside the repository (the team Drive).
"""
import argparse, glob, json, math, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import explore_agent as A  # noqa: E402


def wilson_lower(k, n, z=2.128):
    if not n:
        return None
    p = k / n
    d = 1 + z * z / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d


def check(root):
    tally = {"visible": [0, 0], "trimmed": [0, 0]}
    model = None
    for f in glob.glob(os.path.join(root, "**", "pilot_stochastic_active.json"), recursive=True):
        d = os.path.dirname(f)
        cf = os.path.join(d, "condition.json")
        if not os.path.exists(cf):
            continue
        meta, a = json.load(open(cf, encoding="utf-8")), json.load(open(f, encoding="utf-8"))
        ins = a["instance"]
        if (meta.get("condition") != "task_only" or ins.get("deterministic")
                or ins.get("condition") not in ("silent_break", "degradation")):
            continue
        model = a["model"]["model"]
        ex = a["explore"]
        cu = ex["metrics"].get("changed_action_usage") or {}
        node, lab = cu.get("node"), cu.get("action_label")
        if not node:
            continue
        steps = [s for e in ex["m0_episodes"] for s in e["steps"]]
        m0n = len(steps)
        for e in ex["m1_episodes"]:
            steps += e["steps"]
        consec, fails, hit, chose, six = 0, [], None, False, []
        for i in range(m0n, len(steps)):
            s = steps[i]
            if hit is not None and s["node"] == node and s["action_label"] == lab:
                chose = True
            if s["node"] == node and s["action_label"] == lab:
                if s["success"]:
                    consec, fails = 0, []
                else:
                    consec += 1
                    fails.append(i)
                if consec >= 6 and hit is None:
                    hit, six = i, fails[-6:]
        if hit is None:
            continue
        dec = next((j for j in range(hit + 1, len(steps)) if steps[j]["node"] == node), None)
        if dec is None:
            continue
        tr = ex["transcript"]
        ai, si = [], 0
        for k, m in enumerate(tr):
            if m["role"] == "assistant" and si < len(steps) and m["content"] == steps[si]["raw_text"]:
                ai.append(k)
                si += 1
        if len(ai) <= dec:
            continue
        hist = [dict(role=m["role"], content=m["content"]) for m in tr[:ai[dec]]]
        cfg = ex["config"]
        kept = A.trim_history(hist, cfg["max_context_tokens_est"], cfg["keep_last_n_turns_min"])
        first_kept = len(hist) - len(kept)
        key = "visible" if all(ai[i] + 1 >= first_kept for i in six) else "trimmed"
        tally[key][1] += 1
        tally[key][0] += chose
    return model, tally


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", action="append", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    L = ["| Grid | Model | Chose again / qualifying | All six failures in context | Some trimmed away | Wilson lower bound, visible only |",
         "|---|---|---|---|---|---|"]
    for g in a.grid:
        model, t = check(g)
        v, tr = t["visible"], t["trimmed"]
        lb = wilson_lower(*v)
        L.append(f"| {os.path.basename(os.path.normpath(g))} | {model} | {v[0] + tr[0]}/{v[1] + tr[1]} | {v[0]}/{v[1]} | "
                 f"{tr[0]}/{tr[1]} | {'–' if lb is None else f'{lb:.2f}'} |")
    text = "\n".join(L)
    print(text)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text + "\n")


if __name__ == "__main__":
    main()

"""Bridge probes for study plan v1 (claim C3): does complete evidence lower retrying at the same decision?

For every acting run with the nudge off, stochastic silent break, prompt task-only or model-first, it takes the first
decision at the changed node in an M1 episode after the changed link failed six times in a row (as in the reuse
pilot). A fresh model of the same family then reads, once each, (a) the agent's own observations as a log and (b) a
log covering every link before and after the change, built as the ICL arm builds its logs, and names the next
action. The prompts, settings and parsing are those of experiments/reuse_pilot.py (reader, reader_full).

    python experiments/bridge_probes.py --runs ROUND_FOLDER [--runs ...] --out DIR [--workers 24] [--dry]

Writes DIR/bridge.csv (one row per decision), DIR/bridge_calls.jsonl (every answer) and DIR/bridge_decisions.json.
A transport failure is retried; a returned answer is never re-asked. Needs OPENROUTER_API_KEY. Stdlib only.
"""
import argparse, csv, glob, json, os, re, sys, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "experiments"))
import reuse_pilot as RP          # noqa: E402  (prompts, API call and parsing shared with the pilot)
import run_pilot                  # noqa: E402
import explore_agent              # noqa: E402

CONDITIONS = ("reader", "reader_full")
SIX = 6


def full_logs(seed):
    sc = dict(run_pilot.SCENARIO_DEFAULTS)
    sc.update(seed=seed, condition="silent_break", k=10, budget=10)
    ev = run_pilot.build_record(sc, False)["evidence"]
    return ev["pre"]["F2_shuffled"], ev["post"]["F2_shuffled"]


def decisions(run_dirs):
    out = []
    for root in run_dirs:
        for f in sorted(glob.glob(os.path.join(root, "**", "pilot_stochastic_active.json"), recursive=True)):
            d = os.path.dirname(f)
            cf = os.path.join(d, "condition.json")
            if not os.path.exists(cf):
                continue
            a, meta = json.load(open(f, encoding="utf-8")), json.load(open(cf, encoding="utf-8"))
            ins = a["instance"]
            if (ins.get("condition") != "silent_break" or ins.get("deterministic") or meta.get("nudge")
                    or meta.get("condition") not in ("task_only", "model_first")):
                continue
            ex = a["explore"]
            cu = ex["metrics"].get("changed_action_usage") or {}
            node, lab = cu.get("node"), cu.get("action_label")
            if not node or not lab:
                continue
            steps = [s for e in ex["m0_episodes"] for s in e["steps"]]
            m0n = len(steps)
            found, idx = None, m0n
            for e in ex["m1_episodes"]:
                consec = 0
                for s in e["steps"]:
                    if found is None and s["node"] == node and consec >= SIX:
                        found = idx
                    if s["node"] == node and s["action_label"] == lab:
                        consec = 0 if s["success"] else consec + 1
                    idx += 1
                    steps.append(s)
            if found is None:
                continue
            tr = ex["transcript"]
            ai, si = [], 0
            for k, msg in enumerate(tr):
                if msg["role"] == "assistant" and si < len(steps) and msg["content"] == steps[si]["raw_text"]:
                    ai.append(k)
                    si += 1
            if len(ai) <= found or tr[ai[found] - 1]["role"] != "user":
                continue
            obs_k = ai[found] - 1
            world = a.get("world") or json.loads(json.dumps(run_pilot.pair_to_json(run_pilot.make_pair(
                ins["graph_seed"], "silent_break", deterministic=False, matched=True))))
            pre, post = full_logs(ins["graph_seed"])
            out.append({
                "id": os.path.relpath(d, root), "grid": os.path.basename(os.path.normpath(root)),
                "arm": meta["condition"], "seed": ins["graph_seed"], "node": node, "broken": lab, "goal": world["goal"],
                "original": steps[found]["action_label"], "steps_left_line": tr[obs_k]["content"],
                "system": meta.get("system_prompt", ""), "history": [], "route": None,
                "observations": [(s["node"], s["action_label"], s["next_node"], s["success"], i >= m0n)
                                 for i, s in enumerate(steps[:found])],
                "full_pre": pre, "full_post": post,
                "model": a["model"]["model"], "temperature": a["model"].get("temperature", 0),
                "reasoning": (a.get("reasoning_control") or {}).get("request_fields") or {}})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", action="append", required=True, help="folder holding acting run folders (repeatable)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not args.dry and not key:
        sys.exit("Set OPENROUTER_API_KEY first.")
    pts = decisions([os.path.abspath(r) for r in args.runs])
    os.makedirs(args.out, exist_ok=True)
    print(f"{len(pts)} bridge decisions, {2 * len(pts)} calls{' [dry run]' if args.dry else ''}", flush=True)
    rows, lock = [], threading.Lock()
    with open(os.path.join(args.out, "bridge_calls.jsonl"), "w", encoding="utf-8") as fh, \
            ThreadPoolExecutor(args.workers) as ex:
        futs = [ex.submit(RP.run_one, p, c, 0, key, args.dry, args.max_tokens) for p in pts for c in CONDITIONS]
        for fut in as_completed(futs):
            r = fut.result()
            if r is None:
                continue
            with lock:
                rows.append(r)
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    by = {}
    for r in rows:
        by.setdefault((r["model"], r["id"]), {})[r["condition"]] = r
    with open(os.path.join(args.out, "bridge.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["model", "id", "arm", "broken", "original", "own_choice", "own_reuse", "full_choice", "full_reuse",
                    "own_error", "full_error"])
        for p in pts:
            rr = by.get((p["model"], p["id"]), {})
            o, fu = rr.get("reader", {}), rr.get("reader_full", {})
            w.writerow([p["model"], p["id"], p["arm"], p["broken"], p["original"], o.get("choice"), o.get("reuse"),
                        fu.get("choice"), fu.get("reuse"), o.get("error"), fu.get("error")])
    json.dump([{k: v for k, v in p.items() if k not in ("history", "system", "full_pre", "full_post")} for p in pts],
              open(os.path.join(args.out, "bridge_decisions.json"), "w", encoding="utf-8"), indent=1)
    print(f"bridge.csv written: {len(pts)} decisions", flush=True)


if __name__ == "__main__":
    main()

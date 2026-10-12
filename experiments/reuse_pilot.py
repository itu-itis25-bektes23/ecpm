"""Reuse pilot: why do agents retry a link that failed six times in a row?

Resumes each agent at the exact decision where it had seen the changed link fail six times in a row
(first such decision per run, at that node, in an M1 episode), with the same system prompt, history
(trimmed as the run trimmed it), model and settings, and changes one thing per condition:

  resume       exact replay of the decision (sanity check against the original choice)
  hint         the last observation adds one route to the goal that avoids the failing link
  budget       the last observation says 20 more steps remain than it did
  hint_first_step  the last observation names only the first step of that route
  nudge        the last observation adds: when an action keeps failing, consider untried actions or routes
  reader       a fresh model reads the agent's own observations as a log and advises the next action
  reader_full  a fresh model reads a log covering every link before and after the change (as in the ICL arm)
  reader_hint  the agent's own log plus the same route

Outcome per call: does the reply choose the failing link again? Paired against resume.

Usage (from any folder; needs the team repo for world rebuild and trimming):
  python reuse_pilot.py --grid C:\\...\\GRID_haiku_folder [--grid ...] --repo C:\\Users\\efebe\\ecpm --out C:\\...\\reuse_pilot
  add --dry to check extraction without API calls.
Needs OPENROUTER_API_KEY. Stdlib only.
"""
import argparse, glob, heapq, json, os, re, sys, threading, time, urllib.error, urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

URL = "https://openrouter.ai/api/v1/chat/completions"
CONDITIONS = ["resume", "hint", "hint_first_step", "nudge", "budget", "reader", "reader_full", "reader_hint"]
NUDGE = "\n\nNote: when an action keeps failing, consider trying actions or routes you have not tried yet."
ACTION_RE = re.compile(r'\{\s*"action"\s*:\s*"(a\d+)"\s*\}')


# ---------- decision points ----------
def decision_points(grid_dirs, rp):
    points = []
    for gd in grid_dirs:
        for f in sorted(glob.glob(os.path.join(gd, "**", "pilot_stochastic_active.json"), recursive=True)):
            run_dir = os.path.dirname(f)
            cond_file = os.path.join(run_dir, "condition.json")
            if not os.path.exists(cond_file):
                continue
            a = json.load(open(f, encoding="utf-8"))
            cond = json.load(open(cond_file, encoding="utf-8"))
            ex = a["explore"]
            cu = ex["metrics"].get("changed_action_usage") or {}
            node, lab = cu.get("node"), cu.get("action_label")
            if not node or not lab or cond.get("condition") == "graph_given":
                continue
            scen = "degradation" if "degradation" in run_dir else "silent_break"
            if scen != "silent_break":
                continue
            steps = [s for e in ex["m0_episodes"] for s in e["steps"]]
            m0n = len(steps)
            m1_eps = ex["m1_episodes"]
            found = None
            idx = m0n
            for e in m1_eps:
                consec = 0
                for t, s in enumerate(e["steps"]):
                    if found is None and s["node"] == node and consec >= 6:
                        found = (idx, t, e["episode_idx"])
                    if s["node"] == node and s["action_label"] == lab:
                        consec = 0 if s["success"] else consec + 1
                    idx += 1
                    steps.append(s)
            if found is None:
                continue
            step_i, t, ep = found
            # map step index -> transcript index of its user observation
            tr = ex["transcript"]
            ai, si = [], 0
            for k, m in enumerate(tr):
                if m["role"] == "assistant" and si < len(steps) and m["content"] == steps[si]["raw_text"]:
                    ai.append(k)
                    si += 1
            if len(ai) <= step_i:
                continue
            obs_k = ai[step_i] - 1
            if tr[obs_k]["role"] != "user":
                continue
            history = [dict(role=m["role"], content=m["content"]) for m in tr[:obs_k + 1]]
            cfg = ex["config"]
            history = rp["trim"](history, cfg["max_context_tokens_est"], cfg["keep_last_n_turns_min"])
            seed = a["instance"]["graph_seed"]
            rec = rp["world"](seed)
            goal = rec["goal"]
            route = alt_route(rec["world_post"]["edges"], node, goal, (node, lab))
            full_pre, full_post = rp["full"](seed)
            left_m = re.search(r"Steps remaining this episode: (\d+)", tr[obs_k]["content"])
            steps_left = int(left_m.group(1)) if left_m else None
            points.append({
                "id": os.path.relpath(run_dir, gd), "grid": os.path.basename(os.path.normpath(gd)),
                "arm": cond["condition"], "seed": seed, "node": node, "broken": lab, "goal": goal,
                "original": steps[step_i]["action_label"], "steps_left_line": tr[obs_k]["content"],
                "system": cond["system_prompt"], "history": history, "route": route, "steps_left": steps_left,
                "route_fits": bool(route) and steps_left is not None and len(route) <= steps_left,
                "observations": [(s["node"], s["action_label"], s["next_node"], s["success"], i >= m0n)
                                 for i, s in enumerate(steps[:step_i])],
                "full_pre": full_pre, "full_post": full_post,
                "model": a["model"]["model"], "temperature": a["model"].get("temperature", 0),
                "reasoning": (a.get("reasoning_control") or {}).get("request_fields") or {}})
    return points


def alt_route(edges, start, goal, banned):
    """Most reliable route (min sum of 1/p) from start to goal avoiding the banned link."""
    adj = defaultdict(list)
    for e in edges:
        if e["p"] > 0 and (e["from"], e["action"]) != banned:
            adj[e["from"]].append((1 / e["p"], e["to"], e["action"]))
    dist, prev, pq = {start: 0}, {}, [(0, start)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == goal:
            break
        if d > dist.get(u, 9e9):
            continue
        for w, v, act in adj[u]:
            if d + w < dist.get(v, 9e9):
                dist[v], prev[v] = d + w, (u, act)
                heapq.heappush(pq, (d + w, v))
    if goal not in dist:
        return None
    path, v = [], goal
    while v != start:
        u, act = prev[v]
        path.append((u, act, v))
        v = u
    return path[::-1]


def route_text(route):
    return "; ".join(f"from {u} take {a} to {v}" for u, a, v in route)


# ---------- prompts ----------
def build(point, cond):
    hint = (f"\n\nNote: a route to {point['goal']} that does not use {point['broken']} at {point['node']} "
            f"exists: {route_text(point['route'])}.") if point["route"] else None
    if cond in ("resume", "hint", "hint_first_step", "nudge", "budget"):
        msgs = [{"role": "system", "content": point["system"]}] + [dict(m) for m in point["history"]]
        if cond == "hint":
            if not hint:
                return None
            msgs[-1]["content"] += hint
        if cond == "hint_first_step":
            if not point["route"]:
                return None
            u, a, v = point["route"][0]
            msgs[-1]["content"] += f"\n\nNote: from {u}, action {a} leads to {v}."
        if cond == "nudge":
            msgs[-1]["content"] += NUDGE
        if cond == "budget":
            new, n = re.subn(r"Steps remaining this episode: (\d+)",
                             lambda m: f"Steps remaining this episode: {int(m.group(1)) + 20}", msgs[-1]["content"])
            if not n:
                return None
            msgs[-1]["content"] = new
        return msgs
    # reader: the same observations as a log, read by a fresh model
    if cond == "reader_full":
        lines_a = [l.strip().replace("(", "[").replace(")", "]") for l in point["full_pre"].splitlines() if l.strip()]
        lines_b = [l.strip().replace("(", "[").replace(")", "]") for l in point["full_post"].splitlines() if l.strip()]
    else:
        lines_a = [f"[{u}, {a}, {v if ok else u}]" for u, a, v, ok, m1 in point["observations"] if not m1]
        lines_b = [f"[{u}, {a}, {v if ok else u}]" for u, a, v, ok, m1 in point["observations"] if m1]
    left = re.search(r"Steps remaining this episode: (\d+)", point["steps_left_line"])
    legal = re.search(r"Legal actions here: ([^\n]+)", point["steps_left_line"])
    which = ("log of attempts covering every action, one record per attempt: [location, action, location after "
             "the attempt]. The earlier block is from before the agent was placed back at the start, the later "
             "block from after.\n\n" if cond == "reader_full" else
             "agent's own log, one record per attempt: [location, action, location after the attempt].\n\n")
    text = ("An agent is moving through a courier network of locations connected by one-way links. An attempt "
            "on an action either moves the agent to that action's destination or fails and leaves it where it "
            "is. Each attempt costs one step, and an attempt succeeds with some fixed probability. The network's "
            "reliabilities may have changed between the earlier episodes and the current one. Below is the " + which +
            "Earlier episodes:\n" + "\n".join(lines_a) + "\n\nLater episodes, up to now:\n" + "\n".join(lines_b) +
            f"\n\nThe agent is now at {point['node']}, its goal is {point['goal']}, and it has "
            f"{left.group(1) if left else 'some'} steps left in this episode. Legal actions here: "
            f"{legal.group(1).strip().rstrip('.') if legal else 'see the log'}. Which action should it take next? You may "
            "reason briefly first, but end your reply with exactly one JSON object of the form {\"action\": \"aK\"}.")
    if cond == "reader_hint":
        if not hint:
            return None
        text += hint
    return [{"role": "user", "content": text}]


# ---------- API ----------
def call(body, key, tries=4):
    data = json.dumps(body).encode()
    for attempt in range(tries):
        req = urllib.request.Request(URL, data=data, headers={"Authorization": "Bearer " + key,
                                                             "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < tries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            return {"error": f"HTTP {e.code}: {e.read()[:300].decode(errors='replace')}"}
        except Exception as e:
            if attempt < tries - 1:
                time.sleep(5 * (attempt + 1))
                continue
            return {"error": repr(e)}


def run_one(point, cond, sample, key, dry, max_tokens):
    msgs = build(point, cond)
    if msgs is None:
        return None
    if dry:
        text, err, usage = (f'{{"action": "{point["original"]}"}}' if cond == "resume" else ""), None, {}
    else:
        body = {"model": point["model"], "messages": msgs, "max_tokens": max_tokens,
                "temperature": point["temperature"]}
        body.update(point["reasoning"])
        resp = call(body, key)
        err = resp.get("error")
        text = "" if err else ((resp.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        usage = resp.get("usage") or {}
    found = ACTION_RE.findall(text)
    choice = found[-1] if found else None
    return {"id": point["id"], "model": point["model"], "grid": point["grid"], "arm": point["arm"], "condition": cond, "sample": sample,
            "broken": point["broken"], "original": point["original"], "choice": choice,
            "reuse": None if choice is None else choice == point["broken"], "error": err,
            "cost": usage.get("cost"), "text": text}


# ---------- summary ----------
def summarize(rows, points):
    lines = ["| Condition | Decisions | Reuse the failing link | Switch | No valid action | Errors |",
             "|---|---|---|---|---|---|"]
    by = defaultdict(list)
    for r in rows:
        by[r["condition"]].append(r)
    for c in CONDITIONS:
        rs = by.get(c, [])
        ok = [r for r in rs if not r["error"]]
        valid = [r for r in ok if r["reuse"] is not None]
        reuse = sum(r["reuse"] for r in valid)
        lines.append(f"| {c} | {len(rs)} | {reuse}/{len(valid)} ({100 * reuse / max(1, len(valid)):.0f}%) | "
                     f"{len(valid) - reuse} | {len(ok) - len(valid)} | {len(rs) - len(ok)} |")
    orig = sum(p["original"] == p["broken"] for p in points)
    lines.append("")
    lines.append(f"Original runs: {orig}/{len(points)} of these decisions reused the failing link. "
                 f"Decisions with a route around it: {sum(1 for p in points if p['route'])}/{len(points)}.")
    # paired against resume
    res = {(r["id"], r["sample"]): r for r in by.get("resume", []) if r["reuse"] is not None}
    lines += ["", "| Condition | Paired decisions | Reuse, resume | Reuse, condition | Resume reused, condition switched | Resume switched, condition reused |",
              "|---|---|---|---|---|---|"]
    for c in CONDITIONS[1:]:
        pairs = [(res[(r["id"], r["sample"])]["reuse"], r["reuse"]) for r in by.get(c, [])
                 if r["reuse"] is not None and (r["id"], r["sample"]) in res]
        if pairs:
            lines.append(f"| {c} | {len(pairs)} | {sum(a for a, _ in pairs)} | {sum(b for _, b in pairs)} | "
                         f"{sum(a and not b for a, b in pairs)} | {sum(b and not a for a, b in pairs)} |")
    fits = {p["id"]: p["route_fits"] for p in points}
    lines += ["", "| Condition | Route around fits the steps left | Reuse | Route does not fit | Reuse |", "|---|---|---|---|---|"]
    for c in CONDITIONS:
        a = [r["reuse"] for r in by.get(c, []) if r["reuse"] is not None and fits.get(r["id"])]
        b = [r["reuse"] for r in by.get(c, []) if r["reuse"] is not None and not fits.get(r["id"])]
        lines.append(f"| {c} | {len(a)} | {sum(a)}/{len(a)} | {len(b)} | {sum(b)}/{len(b)} |")
    by_arm = defaultdict(lambda: [0, 0])
    for r in by.get("resume", []):
        if r["reuse"] is not None:
            by_arm[r["arm"]][0] += r["reuse"]
            by_arm[r["arm"]][1] += 1
    lines += ["", "Resume by arm: " + ", ".join(f"{a} {k}/{n}" for a, (k, n) in sorted(by_arm.items())),
              f"Cost: ${sum(r['cost'] or 0 for r in rows):.4f}"]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", action="append", required=True, help="unzipped GRID folder (repeatable)")
    ap.add_argument("--repo", default=r"C:\Users\efebe\ecpm")
    ap.add_argument("--out", default=r"C:\Users\efebe\reuse_pilot")
    ap.add_argument("--samples", type=int, default=1)
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not args.dry and not key:
        sys.exit("Set OPENROUTER_API_KEY first.")
    args.grid = [os.path.abspath(g) for g in args.grid]
    args.out = os.path.abspath(args.out)
    sys.path.insert(0, args.repo)
    os.chdir(args.repo)
    import run_pilot, explore_agent
    def full(seed):
        sc = dict(run_pilot.SCENARIO_DEFAULTS)
        sc.update(seed=seed, condition="silent_break", k=10, budget=10)
        ev = run_pilot.build_record(sc, False)["evidence"]
        return ev["pre"]["F2_shuffled"], ev["post"]["F2_shuffled"]
    rp = {"trim": explore_agent.trim_history, "full": full,
          "world": lambda seed: json.loads(json.dumps(run_pilot.pair_to_json(
              run_pilot.make_pair(seed, "silent_break", deterministic=False, matched=True))))}
    os.makedirs(args.out, exist_ok=True)
    grids = []
    for g in args.grid:
        if g.lower().endswith(".zip"):
            import zipfile
            dest = os.path.join(args.out, "grids", os.path.splitext(os.path.basename(g))[0])
            if not os.path.isdir(dest):
                print(f"unzipping {os.path.basename(g)} ...")
                zipfile.ZipFile(g).extractall(dest)
            grids.append(dest)
        else:
            grids.append(g)
    points = decision_points(grids, rp)
    if not points:
        sys.exit("No decision points found. Check the --grid folders (unzipped, with pilot_stochastic_active.json).")
    os.makedirs(args.out, exist_ok=True)
    jobs = [(p, c, s) for p in points for c in CONDITIONS for s in range(args.samples)]
    print(f"{len(points)} decisions, up to {len(jobs)} calls, {args.workers} workers{' [dry run]' if args.dry else ''}")
    rows, lock, t0 = [], threading.Lock(), time.time()
    path = os.path.join(args.out, "calls.jsonl")
    with open(path, "w", encoding="utf-8") as fh, ThreadPoolExecutor(args.workers) as ex:
        futs = [ex.submit(run_one, p, c, s, key, args.dry, args.max_tokens) for p, c, s in jobs]
        for i, fut in enumerate(as_completed(futs), 1):
            r = fut.result()
            if r is None:
                continue
            with lock:
                rows.append(r)
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
                fh.flush()
            if i % 25 == 0 or i == len(futs):
                print(f"  {i}/{len(futs)} done, {time.time() - t0:.0f}s")
    json.dump([{k: v for k, v in p.items() if k not in ("history", "system")} for p in points],
              open(os.path.join(args.out, "decisions.json"), "w", encoding="utf-8"), indent=1)
    md = ""
    for m in sorted({p["model"] for p in points}):
        md += f"## {m}\n\n" + summarize([r for r in rows if r["model"] == m], [p for p in points if p["model"] == m]) + "\n"
    open(os.path.join(args.out, "summary.md"), "w", encoding="utf-8").write(md)
    print("\n" + md + f"\nFiles: {os.path.abspath(args.out)}")


if __name__ == "__main__":
    main()

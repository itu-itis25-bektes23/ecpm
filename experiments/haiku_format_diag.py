"""Haiku 5.5 format diagnostic: why do reasoning-off ICL answers carry prose before the JSON?

Replays saved task-turn requests from the expanded-ICL run folder, exactly as sent, under five conditions,
and scores each answer for format and content with a self-contained scorer (routes in the true world,
change detection and localization).

  orig         the original saved answer, no API call (baseline)
  off          exact replay, reasoning off (as run)
  silent_user  reasoning off, "output only the JSON object" appended to the last user message
  json_object  reasoning off, API JSON mode (response_format json_object)
  json_schema  reasoning off, API structured output with the exact answer schema
  schema_scratch  structured output with a required "reasoning" string field before the answer fields
  prompt_scratch  instruction to put all reasoning in a "reasoning" field inside the JSON, not enforced
  on_low          reasoning on, effort low
  on_1k           reasoning on, capped at 1,024 reasoning tokens
(Version 1 ran prefill, a system-message instruction and reasoning on. Version 2 ran an end-of-message
instruction, JSON mode and the plain answer schema.)

Usage (PowerShell or cmd):
  python haiku_format_diag.py --runs C:\\Users\\efebe\\ecpm-haiku-runs --out C:\\Users\\efebe\\haiku_diag
  python haiku_format_diag.py --runs ... --out ... --dry      (no API calls, scores the original answers only)

Needs OPENROUTER_API_KEY. Stdlib only. Writes calls.jsonl (one row per call), summary.md and summary.csv,
and prints summary.md. About 70 calls, under $0.20, a few minutes with 8 parallel workers.
"""
import argparse, csv, glob, heapq, json, os, random, sys, time, urllib.error, urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

URL = "https://openrouter.ai/api/v1/chat/completions"
PER_GROUP = 6
SILENT = ("\n\nWork out any reasoning silently. Your reply must be only the JSON object requested, "
          "with no text before or after it.")
CONDITIONS = [("off", 1), ("schema_scratch", 1), ("prompt_scratch", 1), ("on_low", 1), ("on_1k", 1)]
SCRATCH_SUFFIX = ("\n\nYou may reason before answering, but put all of that reasoning inside the JSON object, "
                  "as the first field, \"reasoning\" (a string). Return exactly one JSON object: the \"reasoning\" "
                  "field followed by the required fields. No text before or after the object.")
USER_SUFFIX = ("\n\nOutput only the JSON object. Do not write any reasoning, explanation or other text "
               "before or after it.")


def answer_schema(period, scratch=False):
    step = {"type": "object", "additionalProperties": False, "required": ["state", "action"],
            "properties": {"state": {"type": "string"}, "action": {"type": "string"}}}
    route = {"type": "object", "additionalProperties": False, "required": ["query_id", "reachable", "steps"],
             "properties": {"query_id": {"type": "string"}, "reachable": {"type": "boolean"},
                            "steps": {"type": "array", "items": step}}}
    props = {"reasoning": {"type": "string"}} if scratch else {}
    props["routes"] = {"type": "array", "items": route}
    if period == "B":
        props["changed"] = {"type": "boolean"}
        props["changed_pair"] = {"anyOf": [{"type": "null"}, step]}
    return {"type": "object", "additionalProperties": False, "required": list(props), "properties": props}


# ---------- sample ----------
def all_turns(runs):
    """Every reasoning-off A_task and B_task turn of every run (version 4, full scale)."""
    out = []
    for f in sorted(glob.glob(os.path.join(runs, "haiku_off_*", "icl_*.json"))):
        a = json.load(open(f, encoding="utf-8-sig"))
        arm = a["identity"]["condition"]
        for name in ("A_task", "B_task"):
            t = a["turns"].get(name)
            if t:
                out.append(((arm, name, bool((t.get("parsed") or {}).get("well_formed"))), (f, name)))
    return out


def pick_turns(runs, seed=7):
    """Malformed task-only and graph-given task turns plus well-formed model-first ones (control)."""
    pools = defaultdict(list)
    for f in sorted(glob.glob(os.path.join(runs, "haiku_off_*", "icl_*.json"))):
        a = json.load(open(f, encoding="utf-8-sig"))
        arm = a["identity"]["condition"]
        for name in ("A_task", "B_task"):
            t = a["turns"].get(name)
            if not t:
                continue
            wf = (t.get("parsed") or {}).get("well_formed")
            key = (arm, name, bool(wf))
            pools[key].append((f, name))
    rng = random.Random(seed)
    plan = [(("task_only", "A_task", False), 3), (("task_only", "B_task", False), 3),
            (("graph_given", "B_task", False), 3), (("model_first", "A_task", True), 3)]
    plan = [(k, n * PER_GROUP // 3) for k, n in plan]
    chosen = []
    for key, n in plan:
        pool = pools.get(key, [])
        chosen += [(key, x) for x in rng.sample(pool, min(n, len(pool)))]
    return chosen


# ---------- scoring ----------
def shape(text):
    s = text.strip()
    if s.startswith("{") and s.endswith("}"):
        return "pure_json"
    if s.startswith("```") and s.endswith("```"):
        return "fenced_only"
    if "{" in s:
        return "prose_then_json"
    return "no_json"


def strict_obj(text):
    try:
        o = json.loads(text.strip())
        return o if isinstance(o, dict) else None
    except Exception:
        return None


def content_obj(text):
    """Last complete JSON object carrying the answer field (routes), as the agentic parser does."""
    dec = json.JSONDecoder()
    for i in [k for k, ch in enumerate(text) if ch == "{"][::-1]:
        try:
            o, _ = dec.raw_decode(text[i:])
        except Exception:
            continue
        if isinstance(o, dict) and "routes" in o:
            return o
    return None


def graph(world, period):
    return {(r["node"], r["action"]): r for r in world[period]["graph"]}


def optimal_cost(g, start, goal):
    adj = defaultdict(list)
    for (u, a), r in g.items():
        if r["available"] and (r["p_success"] or 0) > 0 and r["destination"]:
            adj[u].append((1.0 / r["p_success"], r["destination"]))
    dist, pq = {start: 0.0}, [(0.0, start)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == goal:
            return d
        if d > dist.get(u, float("inf")):
            continue
        for w, v in adj[u]:
            if d + w < dist.get(v, float("inf")):
                dist[v] = d + w
                heapq.heappush(pq, (d + w, v))
    return float("inf")


def route_optimal(g, q, entry):
    opt = optimal_cost(g, q["start"], q["goal"])
    if opt == float("inf") or not isinstance(entry, dict):
        return False
    if entry.get("reachable") is False:
        return False          # as the harness: routes optimal counts only valid zero-regret routes
    cur, cost = q["start"], 0.0
    for st in entry.get("steps") or []:
        if not isinstance(st, dict) or cur == q["goal"] or st.get("state") != cur:
            return False
        r = g.get((cur, st.get("action")))
        if not r or not r["available"] or not (r["p_success"] or 0) > 0:
            return False
        cost += 1.0 / r["p_success"]
        cur = r["destination"]
    return cur == q["goal"] and cost <= opt + 1e-9


def score(obj, world, period):
    out = {"routes_optimal": None, "detection_correct": None, "localization_correct": None}
    if obj is None:
        return out
    g = graph(world, period)
    by_id = {e.get("query_id"): e for e in (obj.get("routes") or []) if isinstance(e, dict)}
    qs = world["route_queries"]
    out["routes_optimal"] = sum(route_optimal(g, q, by_id.get(q["query_id"])) for q in qs) / len(qs)
    if period == "B":
        changed = bool(world["true_changes"])
        out["detection_correct"] = obj.get("changed") is changed
        cp = obj.get("changed_pair")
        expected = world["true_changes"][0] if changed else None
        got = [cp.get("state"), cp.get("action")] if isinstance(cp, dict) else None
        out["localization_correct"] = got == expected
    return out


def evaluate(text, world, period):
    s, c = strict_obj(text), content_obj(text)
    return {"shape": shape(text), "strict_parsed": s is not None, "content_parsed": c is not None,
            "strict": score(s, world, period), "content": score(c, world, period)}


# ---------- API ----------
def call(body, key, tries=4):
    data = json.dumps(body).encode()
    for attempt in range(tries):
        req = urllib.request.Request(URL, data=data, headers={
            "Authorization": "Bearer " + key, "Content-Type": "application/json"})
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


def build(body, cond, period="B"):
    b = json.loads(json.dumps(body))
    msgs = b["messages"]
    if cond == "silent_user":
        msgs[-1] = dict(msgs[-1], content=msgs[-1]["content"] + USER_SUFFIX)
    elif cond == "json_object":
        b["response_format"] = {"type": "json_object"}
    elif cond in ("json_schema", "schema_scratch"):
        b["response_format"] = {"type": "json_schema", "json_schema": {
            "name": "answer", "strict": True, "schema": answer_schema(period, cond == "schema_scratch")}}
    elif cond == "prompt_scratch":
        msgs[-1] = dict(msgs[-1], content=msgs[-1]["content"] + SCRATCH_SUFFIX)
    elif cond == "on_low":
        b["reasoning"] = {"effort": "low", "exclude": False}
    elif cond == "on_1k":
        b["reasoning"] = {"max_tokens": 1024, "exclude": False}
    if cond == "prefill":
        msgs.append({"role": "assistant", "content": "{"})
    elif cond == "silent":
        msgs[0] = dict(msgs[0], content=msgs[0]["content"] + SILENT)
    elif cond == "on":
        b["reasoning"] = {"effort": "medium", "exclude": False}
    return b


def run_one(job, key, dry):
    f, name, cond, sample, original, world, body = job
    period = name[0]
    provider = finish = None
    if cond == "orig" or dry:
        text, usage, err = original, {}, None
    else:
        resp = call(build(body, cond, period), key)
        err = resp.get("error")
        msg = ((resp.get("choices") or [{}])[0].get("message") or {}) if not err else {}
        text = (msg.get("content") or "") if not err else ""
        if cond == "prefill" and text and not text.lstrip().startswith("{"):
            text = "{" + text
        usage = resp.get("usage") or {}
        provider = resp.get("provider")
        finish = ((resp.get("choices") or [{}])[0].get("finish_reason")) if not err else None
    ev = evaluate(text, world, period) if not err else None
    return {"run": os.path.basename(os.path.dirname(f)), "turn": name, "condition": cond, "sample": sample,
            "error": err, "eval": ev, "completion_tokens": usage.get("completion_tokens"),
            "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
            "cost": usage.get("cost"), "provider": provider, "finish_reason": finish, "text": text}


# ---------- summary ----------
def summarize(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[(r["condition"], r["arm_turn"])].append(r)
        groups[(r["condition"], "ALL")].append(r)
    order = ["orig", "off", "json_schema", "schema_scratch", "prompt_scratch", "on_low", "on_1k",
             "silent_user", "json_object", "prefill", "silent", "on"]
    lines = ["| Condition | Turns | Calls | Errors | Pure JSON | Strict parses | Routes optimal, strict | Routes optimal, content | Localization (B), content | Mean output tokens | Mean reasoning tokens | Cost |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    csv_rows = []
    def pct(xs):
        xs = [x for x in xs if x is not None]
        return f"{100 * sum(xs) / len(xs):.0f}%" if xs else "–"
    for cond in order:
        for grp in sorted({k[1] for k in groups if k[0] == cond}, key=lambda s: (s != "ALL", s)):
            rs = groups[(cond, grp)]
            ok = [r for r in rs if not r["error"]]
            ev = [r["eval"] for r in ok]
            row = [cond, grp, len(rs), len(rs) - len(ok),
                   pct([e["shape"] == "pure_json" for e in ev]), pct([e["strict_parsed"] for e in ev]),
                   pct([e["strict"]["routes_optimal"] if e["strict_parsed"] else 0 for e in ev]),
                   pct([e["content"]["routes_optimal"] for e in ev]),
                   pct([e["content"]["localization_correct"] for e in ev]),
                   (f"{sum(r['completion_tokens'] for r in ok if r['completion_tokens']) / max(1, sum(1 for r in ok if r['completion_tokens'])):.0f}"
                    if any(r["completion_tokens"] for r in ok) else "–"),
                   (f"{sum(r['reasoning_tokens'] or 0 for r in ok) / max(1, len(ok)):.0f}" if ok and cond != "orig" else "–"),
                   f"${sum(r['cost'] or 0 for r in ok):.4f}"]
            csv_rows.append(row)
            lines.append("| " + " | ".join(str(x) for x in row) + " |")
    note = ("\nRoutes optimal is the share of the four route queries answered with a valid, zero-regret route. "
            "Strict counts an answer that is not pure JSON as 0. Content reads the last JSON object carrying "
            "the routes. Groups: arm and turn of the sampled turns (the original answers of task-only and "
            "graph-given were malformed, those of model-first well-formed).")
    return "\n".join(lines) + "\n" + note + "\n", csv_rows


def paired(rows):
    """Per-turn paired differences of each condition against the exact replay (off) and the original answer."""
    by = defaultdict(dict)
    for r in rows:
        if r["error"] or r["eval"] is None:
            continue
        e = r["eval"]
        by[(r["run"], r["turn"])][r["condition"]] = {
            "pure_json": float(e["shape"] == "pure_json"),
            "routes_strict": e["strict"]["routes_optimal"] if e["strict_parsed"] else 0.0,
            "routes_content": e["content"]["routes_optimal"] or 0.0,
            "localization": (None if e["content"]["localization_correct"] is None
                             else float(bool(e["content"]["localization_correct"]))),
            "detection": (None if e["content"]["detection_correct"] is None
                          else float(bool(e["content"]["detection_correct"])))}
    conds = sorted({c for v in by.values() for c in v} - {"orig", "off"})
    lines = ["| Condition | Against | Measure | Turns | Condition mean | Baseline mean | Difference | 95% interval |",
             "|---|---|---|---|---|---|---|---|"]
    for base in ("off", "orig"):
        for c in conds:
            for m in ("pure_json", "routes_strict", "routes_content", "detection", "localization"):
                pairs = [(v[c][m], v[base][m]) for v in by.values()
                         if c in v and base in v and v[c][m] is not None and v[base][m] is not None]
                if len(pairs) < 2:
                    continue
                d = [a - b for a, b in pairs]
                n, mean = len(d), sum(d) / len(d)
                sd = (sum((x - mean) ** 2 for x in d) / (n - 1)) ** 0.5
                half = 1.96 * sd / n ** 0.5
                lines.append(f"| {c} | {base} | {m} | {n} | {sum(a for a, _ in pairs) / n:.2f} | "
                             f"{sum(b for _, b in pairs) / n:.2f} | {mean:+.2f} | [{mean - half:+.2f}, {mean + half:+.2f}] |")
    note = ("\nPaired over the same turns. routes_strict counts an answer that is not pure JSON as 0 (the paper's "
            "primary scoring), routes_content reads the last JSON object carrying the routes. Detection and "
            "localization exist for Period B turns only. 95% interval: normal approximation of the paired mean.")
    return "\n".join(lines) + "\n" + note + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=r"C:\Users\efebe\ecpm-haiku-runs")
    ap.add_argument("--out", default=r"C:\Users\efebe\haiku_diag")
    ap.add_argument("--workers", type=int, default=None, help="parallel calls (default 8, or 32 with --all)")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--all", action="store_true",
                    help="version 4: every reasoning-off task turn, conditions off, json_schema, schema_scratch, prompt_scratch")
    args = ap.parse_args()
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not args.dry and not key:
        sys.exit("Set OPENROUTER_API_KEY first.")
    global CONDITIONS
    if args.all:
        CONDITIONS = [("off", 1), ("json_schema", 1), ("schema_scratch", 1), ("prompt_scratch", 1)]
    args.workers = args.workers or (32 if args.all else 8)
    turns = all_turns(args.runs) if args.all else pick_turns(args.runs)
    if not turns:
        sys.exit(f"No haiku_off_* run folders under {os.path.abspath(args.runs)}")
    os.makedirs(args.out, exist_ok=True)
    jobs, meta = [], []
    for (arm, name, wf), (f, tname) in turns:
        a = json.load(open(f, encoding="utf-8-sig"))
        t = a["turns"][tname]
        group = f"{arm} {tname}" if not args.all else f"{arm} {tname} {'well-formed' if wf else 'malformed'}"
        for cond, n in [("orig", 1)] + CONDITIONS:
            for s in range(n):
                jobs.append((f, tname, cond, s, t["raw_response"], a["world"], t["request_body"]))
                meta.append(group)
    print(f"{len(turns)} turns, {len(jobs)} jobs ({sum(1 for j in jobs if j[2] != 'orig')} API calls), "
          f"{args.workers} workers{' [dry run]' if args.dry else ''}")
    path = os.path.join(args.out, "calls.jsonl")
    done_rows = {}
    if os.path.exists(path) and not args.dry:            # resume: keep finished calls, redo failed ones
        for line in open(path, encoding="utf-8"):
            try:
                r = json.loads(line)
            except Exception:
                continue
            if not r.get("error"):
                done_rows[(r["run"], r["turn"], r["condition"], r["sample"])] = r
    rows, t0, lock = [None] * len(jobs), time.time(), __import__("threading").Lock()
    todo = []
    for i, j in enumerate(jobs):
        k = (os.path.basename(os.path.dirname(j[0])), j[1], j[2], j[3])
        if k in done_rows:
            rows[i] = done_rows[k]
            rows[i]["arm_turn"] = meta[i]
        else:
            todo.append(i)
    if len(todo) < len(jobs):
        print(f"  resuming: {len(jobs) - len(todo)} jobs already done, {len(todo)} to run")
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            if r is not None:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(path, "a", encoding="utf-8") as fh, ThreadPoolExecutor(args.workers) as ex:
        futs = {ex.submit(run_one, jobs[i], key, args.dry): i for i in todo}
        for done, fut in enumerate(as_completed(futs), 1):
            i = futs[fut]
            rows[i] = fut.result()
            rows[i]["arm_turn"] = meta[i]
            with lock:
                fh.write(json.dumps(rows[i], ensure_ascii=False) + "\n")
                fh.flush()
            if done % 50 == 0 or done == len(todo):
                el = time.time() - t0
                print(f"  {done}/{len(todo)} done, {el:.0f}s, about {el / done * (len(todo) - done):.0f}s left")
    md, csv_rows = summarize(rows)
    md += "\n## Paired comparisons\n\n" + paired(rows)
    provs = {r["provider"] for r in rows if r.get("provider")}
    fins = defaultdict(int)
    for r in rows:
        if r.get("finish_reason"):
            fins[r["finish_reason"]] += 1
    md += f"\nServing providers: {', '.join(sorted(provs)) or 'none recorded'}. Finish reasons: {dict(fins) or 'none recorded'}.\n"
    open(os.path.join(args.out, "summary.md"), "w", encoding="utf-8").write(md)
    with open(os.path.join(args.out, "summary.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["condition", "group", "calls", "errors", "pure_json", "strict_parses", "routes_opt_strict",
                    "routes_opt_content", "loc_content", "mean_output_tokens", "mean_reasoning_tokens", "cost"])
        w.writerows(csv_rows)
    errs = [r for r in rows if r["error"]]
    print("\n" + md)
    if errs:
        print(f"{len(errs)} calls failed, first error: {errs[0]['error']}")
    print(f"Files: {os.path.abspath(args.out)}\\summary.md, summary.csv, calls.jsonl")


if __name__ == "__main__":
    main()

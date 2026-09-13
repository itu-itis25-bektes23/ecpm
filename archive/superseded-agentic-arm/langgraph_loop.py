"""LangGraph adapter for the ECPM agentic arm.

Status 26/08: first executed on Maciek's machine, langgraph 1.x on
Python 3.14. The graph machinery ran. One bug surfaced and was fixed,
the dry backend crashed on the belief probe fork because it assumed
every message is an observation JSON. It now answers the belief probe
with the policy's own estimates and returns an empty JSON object for
the frozen probes. Full dry run pending, real model paths still
unexecuted. Everything framework free (prompts, parsing, retries,
record schema) reuses agent_loop.py and break_metrics.py, which are
tested. Install: pip install -U langgraph langchain langchain-openai
langchain-ollama

Design, matching the doc's Method flow section:
  - One shared message transcript for the whole run. M0 episodes first,
    then a silent switch to M1. The transcript persists across the
    switch, so the model's memory of M0 carries into M1.
  - Each step the model sees one observation JSON and must reply with
    one JSON object {"reason": "...", "action": "aK"}. The reason gives
    Sruthi the per-step reasoning log she asked for.
  - Belief probes and the four frozen probes are asked on a FORK of the
    transcript, so probing never contaminates the main run.
  - Unparseable replies: retry with a corrective message up to
    max_retries, then fall back to the first listed action and log the
    status malformed_fallback. The cost rule for this case is still an
    open interface question (Note D, Efe signs off). The fallback keeps
    runs alive without deciding that question.

Run (after install):
  python3 langgraph_loop.py --backend dry
  AZURE_OPENAI_API_KEY=... AZURE_OPENAI_ENDPOINT=... OPENAI_API_VERSION=... \
      python3 langgraph_loop.py --backend azure_openai:gpt-4o
  python3 langgraph_loop.py --backend ollama:gemma3:4b
"""

from __future__ import annotations

import argparse
import json
import re
from typing import Annotated, TypedDict

from seed7_world import make_pair, BREAK_PAIR, GOAL
from agent_loop import AdaptiveMaskPolicy, save_jsonl
import break_metrics as bm

MAX_RETRIES = 3
BELIEF_EVERY = 10  # env steps between forked belief probes, None to disable

SYSTEM_PROMPT = """You are routing a packet through an unknown network.
You only ever see your current node, the action labels listed there, your
total cost so far, and the goal node. Labels are opaque. You do not know
where any action leads until you try it. A successful attempt returns
"OK, arrive X". A failed attempt returns "DROP, stay X". Every attempt
costs 1. Reach the goal in as few attempts as you can. After a reset you
are back at the start node, but the network is the same one you already
explored unless your observations tell you otherwise.
Reply with exactly one JSON object and nothing else:
{"reason": "<at most 20 words>", "action": "<one listed label>"}"""

BELIEF_PROBE = """Bookkeeping question, it does not cost an attempt and
does not move the packet. For every pair you have tried, estimate the
probability that the action succeeds now. Reply with one JSON object
mapping "NODE label" to a number between 0 and 1, for example
{"E a1": 1.0, "D a2": 0.2}. Include only pairs you have evidence about."""

FROZEN_PROBES = {
    "detection": ('Did the network dynamics change at any point during '
                  'your run? Reply {"changed": true} or {"changed": false}.'),
    "localization": ('Exactly one state-action pair changed. Name it. '
                     'Reply {"node": "...", "action": "..."}.'),
    "preservation": ('For each pair below, say whether its behavior '
                     'changed. Reply one JSON object mapping "NODE label" '
                     'to "changed" or "unchanged": {pairs}'),
    "adaptation": ('Give the lowest-cost route from {start} to {goal} in '
                   'the current network. Reply {{"route": [{{"node": "...", '
                   '"action": "..."}}, ...]}} with at most 32 steps.'),
}


def extract_last_json(text):
    """Return the last balanced JSON object in the text, or None."""
    depth, start, last = 0, None, None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth:
            depth -= 1
            if depth == 0 and start is not None:
                last = text[start:i + 1]
    if last is None:
        return None
    try:
        return json.loads(last)
    except json.JSONDecodeError:
        try:
            return json.loads(re.sub(r",\s*}", "}", last))
        except json.JSONDecodeError:
            return None


def render_observation(node, menu, cost, goal, note=""):
    obs = {"node": node, "actions": menu, "cost_so_far": cost, "goal": goal}
    if note:
        obs["last_result"] = note
    return json.dumps(obs)


# ---------------------------------------------------------------------------
# Model backends
# ---------------------------------------------------------------------------

class DryBackend:
    """Wraps the tested AdaptiveMaskPolicy so the whole LangGraph app can be
    exercised with zero API calls."""

    def __init__(self, pre_world, k=3):
        self.policy = AdaptiveMaskPolicy(pre_world, k=k)

    def invoke(self, messages):
        content = messages[-1]["content"]
        try:
            obs = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            obs = None
        if isinstance(obs, dict) and "node" in obs and "actions" in obs:
            action, _ = self.policy.act(obs["node"], obs["actions"])
            return json.dumps({"reason": "dry run", "action": action})
        # Probe fork: the message is a plain-text question, not an
        # observation. For the belief probe, answer with the policy's own
        # estimates so dry mode exercises the belief pipeline end to end.
        # For the frozen probes, a scripted policy has no answer, return
        # an empty JSON object, which parses and is logged as junk.
        if content.startswith("Bookkeeping question"):
            pairs = [(u, a) for u in sorted(self.policy.map)
                     for a in sorted(self.policy.map[u])]
            est = self.policy.belief(pairs)
            return json.dumps(est if est else {})
        return "{}"

    def observe(self, *args):
        self.policy.observe(*args)


def make_backend(spec, pre_world):
    if spec == "dry":
        return DryBackend(pre_world)
    from langchain.chat_models import init_chat_model  # lazy import
    llm = init_chat_model(spec, temperature=0)

    class LC:
        def __init__(self):
            self.usage = {"input_tokens": 0, "output_tokens": 0, "calls": 0}

        def invoke(self, messages):
            resp = llm.invoke(messages)
            um = getattr(resp, "usage_metadata", None) or {}
            self.usage["input_tokens"] += um.get("input_tokens", 0) or 0
            self.usage["output_tokens"] += um.get("output_tokens", 0) or 0
            self.usage["calls"] += 1
            return resp.content

        def observe(self, *args):
            pass

    return LC()


# ---------------------------------------------------------------------------
# LangGraph state machine: decide -> act -> (decide | end)
# ---------------------------------------------------------------------------

class RunState(TypedDict):
    messages: list          # the one shared transcript, dicts with role/content
    node: str
    cost: int               # episode cost
    t: int                  # global attempt counter
    phase: str
    episode: int
    records: list
    done: bool


def build_app(world_ref, backend, run_id, max_steps):
    from langgraph.graph import StateGraph, START, END

    def decide(state: RunState):
        world = world_ref["world"]
        menu = world.menu(state["node"])
        obs = render_observation(state["node"], menu, state["cost"], world.goal)
        messages = state["messages"] + [{"role": "user", "content": obs}]
        action, raw, status_note = None, "", ""
        for attempt in range(MAX_RETRIES + 1):
            raw = backend.invoke(messages)
            parsed = extract_last_json(raw)
            if parsed and parsed.get("action") in menu:
                action = parsed["action"]
                break
            messages = messages + [
                {"role": "assistant", "content": raw},
                {"role": "user", "content":
                    f"Invalid reply. Choose one of {menu}. JSON only."}]
        if action is None:
            action = menu[0]
            status_note = "malformed_fallback"  # Note D, cost rule open
        messages = messages + [{"role": "assistant", "content": raw}]
        reason = (extract_last_json(raw) or {}).get("reason", "")
        return {"messages": messages,
                "records": state["records"] + [{"_pending":
                    {"action": action, "reason": reason,
                     "note": status_note, "menu": menu}}]}

    def act(state: RunState):
        world = world_ref["world"]
        pending = state["records"][-1].pop("_pending")
        state["records"].pop()
        status, nxt = world.step(state["node"], pending["action"])
        cost, t = state["cost"] + 1, state["t"] + 1
        rec = {"run_id": run_id, "phase": state["phase"],
               "episode": state["episode"], "t": t, "node": state["node"],
               "menu": pending["menu"], "action": pending["action"],
               "status": status, "next_node": nxt, "cost": cost,
               "reason": pending["reason"]}
        if pending["note"]:
            rec["note"] = pending["note"]
        backend.observe(state["node"], pending["action"], status, nxt)
        messages = state["messages"] + [
            {"role": "user", "content": f"{status}, "
             f"{'arrive' if status == 'OK' else 'stay'} {nxt}"}]
        if BELIEF_EVERY and t % BELIEF_EVERY == 0:
            fork = messages + [{"role": "user", "content": BELIEF_PROBE}]
            est = extract_last_json(backend.invoke(fork))
            state["records"].append({"type": "belief", "run_id": run_id,
                                     "phase": state["phase"],
                                     "episode": state["episode"], "t": t,
                                     "estimates": est})
        done = (nxt == world.goal) or (cost >= max_steps)
        return {"messages": messages, "node": nxt, "cost": cost, "t": t,
                "records": state["records"] + [rec], "done": done}

    g = StateGraph(RunState)
    g.add_node("decide", decide)
    g.add_node("act", act)
    g.add_edge(START, "decide")
    g.add_edge("decide", "act")
    g.add_conditional_edges("act", lambda s: END if s["done"] else "decide")
    return g.compile()


def ask_frozen_probes(messages, backend, world_pre, world_post):
    """Fork the transcript once per probe, frozen answer schemas. Scoring
    here is local and unofficial. Official scores come from
    ecpm_parser.run_probe on the frozen commit."""
    out = {}
    queried = ["H a2", "D a2", "D a1", "C a1"]  # frozen pilot preservation set
    prompts = dict(FROZEN_PROBES)
    prompts["preservation"] = prompts["preservation"].format(pairs=queried)
    prompts["adaptation"] = prompts["adaptation"].format(
        start=world_post.start, goal=world_post.goal)
    for name, q in prompts.items():
        fork = messages + [{"role": "user", "content": q}]
        raw = backend.invoke(fork)
        out[name] = {"raw": raw, "parsed": extract_last_json(raw)}
    route = (out["adaptation"]["parsed"] or {}).get("route") or []
    node, cost, valid = world_post.start, 0, True
    for hop in route[:32]:
        try:
            status, node = world_post.step(hop.get("node"), hop.get("action"))
            cost += 1
        except Exception:
            valid = False
            break
        if node == world_post.goal:
            break
    oracle_cost, _ = world_post.oracle()
    reached = valid and node == world_post.goal
    out["adaptation"]["local_score"] = {
        "valid": reached, "cost": cost,
        "regret": (cost - oracle_cost) if reached else None}
    return out


def finalize_run(records, probes, facts, m0, run_id, args, usage=None):
    """Compute the summary and the 2x2 from the model's actual answers,
    persist everything into the out file, print the report."""
    bp = facts["break_pair"]
    summary = bm.summarize(records, bp, m0.goal,
                           facts["oracle_pre_cost"],
                           facts["oracle_post_cost"], m0.legal_pairs())
    loc = (probes.get("localization", {}) or {}).get("parsed") or {}
    knows = (bp is not None
             and loc.get("node") == bp[0] and loc.get("action") == bp[1])
    box = bm.knowing_vs_doing(localized_correctly=knows, records=records,
                              break_pair=bp) if bp else None
    tail = [{"type": "probes",
             "probes": {k: {"raw": v.get("raw"), "parsed": v.get("parsed"),
                            "local_score": v.get("local_score")}
                        for k, v in probes.items()}},
            {"type": "summary", "run_id": run_id, "facts": facts,
             "config": {"seed": args.seed, "stochastic": args.stochastic,
                        "condition": args.condition,
                        "episodes_pre": args.episodes_pre,
                        "episodes_post": args.episodes_post,
                        "max_steps": args.max_steps,
                        "backend": args.backend},
             "metrics": summary, "knowing_vs_doing": box}]
    if usage:
        tail.append({"type": "usage", **usage})
    save_jsonl(records + tail, args.out)
    bm.print_report(run_id, summary)
    print(json.dumps({k: v.get("parsed") for k, v in probes.items()},
                     indent=2))
    if box:
        print("knowing vs doing (from the actual localization answer):",
              json.dumps(box))
    if usage:
        print("token usage:", json.dumps(usage))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="dry")
    ap.add_argument("--episodes-pre", type=int, default=10)
    ap.add_argument("--episodes-post", type=int, default=10)
    ap.add_argument("--max-steps", type=int, default=20)
    ap.add_argument("--out", default="agentic_run.jsonl")
    ap.add_argument("--seed", type=int, default=7,
                    help="graph seed, needs --repo for anything but 7")
    ap.add_argument("--stochastic", action="store_true",
                    help="stochastic sibling instead of deterministic, "
                         "needs --repo")
    ap.add_argument("--condition", default="silent_break",
                    help="frozen change condition, needs --repo for "
                         "anything but silent_break")
    ap.add_argument("--repo", default=None,
                    help="path to the frozen ecpm checkout. If given, every "
                         "environment step executes the frozen resource_mdp "
                         "code through frozen.py instead of the local "
                         "reconstruction.")
    args = ap.parse_args()

    if args.repo:
        import frozen
        inst, _ = frozen.load_pair(args.repo, condition=args.condition,
                                   deterministic=not args.stochastic,
                                   seed=args.seed)
        m0, m1 = frozen.worlds_from_instance(inst)
        facts = frozen.instance_facts(inst)
    else:
        if args.seed != 7 or args.stochastic or args.condition != "silent_break":
            raise SystemExit("--seed, --stochastic and --condition need "
                             "--repo, the local reconstruction is the "
                             "seed-7 deterministic silent break only")
        m0, m1 = make_pair("silent_break")
        facts = {"break_pair": BREAK_PAIR, "oracle_pre_cost": 4.0,
                 "oracle_post_cost": 5.0, "condition": "silent_break",
                 "deterministic": True, "change": {}}
    world_ref = {"world": m0}
    backend = make_backend(args.backend, m0)
    run_id = f"lg-{args.backend.replace(':', '-')}"
    app = build_app(world_ref, backend, run_id, args.max_steps)

    state = {"messages": [{"role": "system", "content": SYSTEM_PROMPT}],
             "node": m0.start, "cost": 0, "t": 0, "phase": "pre",
             "episode": 0, "records": [], "done": False}
    for phase, world, n in (("pre", m0, args.episodes_pre),
                            ("post", m1, args.episodes_post)):
        world_ref["world"] = world
        for e in range(n):
            state.update({"node": world.start, "cost": 0, "phase": phase,
                          "episode": e, "done": False})
            state = app.invoke(state, config={"recursion_limit": 500})

    probes = ask_frozen_probes(state["messages"], backend, m0, m1)
    usage = getattr(backend, "usage", None)
    finalize_run(state["records"], probes, facts, m0, run_id, args, usage)


if __name__ == "__main__":
    main()

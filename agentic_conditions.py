"""Model-first / task-only / graph-given conditions for the agentic arm.

One file, no edits to explore_agent.py or run_pilot.py: it wraps them at runtime.
task_only applies no wrapping at all, so it is the existing arm unchanged.

  model_first  Before every episode after the first, the model writes a free-text
               model of the network (wording from icl_model_first.MODEL_A/MODEL_B).
               The reply stays in the transcript and is not scored.
  graph_given  At each phase start the model receives the current specification
               (destinations and success probabilities). M1 shows the change.

Commands (repository root):
  python3 -B agentic_conditions.py test
  python3 -B agentic_conditions.py run CONDITION [--repeat R] [--mode-prompts]
        [--history none|retained_reports_v2|separate_reports_post_task_v1] [--matched-prep] -- <run_pilot.py arguments>
  python3 -B agentic_conditions.py batch OUTDIR [CONDITION ...] -- <provider arguments>
  python3 -B agentic_conditions.py estimate [--seeds 51]
  python3 -B agentic_conditions.py exposure RUNS_DIR      # writes RUNS_DIR/exposure.csv

Exposure. An agent can only show that it adapted to a change if its own route
used the changed link. If its route before the change never went through that
link, keeping the same route is correct anyway and its later answers about the
change are guesses. Every run therefore records, for the changed link:
  m0_route_uses  the agent's own route before the change (its last M0 episode)
                 used the changed link. This is the flag that decides whether a
                 run counts for adaptation metrics ("exposed").
  m0_any_use     the agent used the changed link at least once in M0.
  m1_attempts    how often it tried the changed link after the change.
No change runs have no changed link, so their exposure fields are empty.

Repeats. --repeat R (default 0) changes only the random outcomes of attempts
(environment seed = graph seed * 100 + R); the graph itself stays the same. In the
deterministic mode attempts are not random, so repeats differ only through the model.

Token log. Every model call (steps, preparation turns, probes) records the
provider's usage report in usage.json next to the run. Complete reports yield
token totals; missing or conflicting reports yield null totals with reported
subtotals and counts. Aliases are counted once. The exposure CSV includes these
totals and completeness fields. Monetary cost still requires verified rates and
billing reconciliation, including any unreported or failed attempts.
"""
import json, os, re, statistics as st, sys
import explore_agent as A
from model_clients import usage_totals as _usage_totals
from resource_mdp import make_pair

CONDITIONS = ("task_only", "model_first", "graph_given")
MODEL_FIRST_FIRST = (
    "Before the next episode, construct a model of how this network behaves "
    "from what you have observed so far. Use whatever representation you find "
    "useful. Describe the current network so that your model can be used to "
    "choose actions later. Reply in free text; do not include a JSON object.")
MODEL_FIRST_UPDATE = (
    "Before the next episode, update your model of how this network behaves "
    "using everything you have observed so far. Use whatever representation "
    "you find useful. Describe the current network so that your model can be "
    "used to choose actions later. Reply in free text; do not include a JSON "
    "object.")
# Ablation switches, named as in the ICL arm (icl_model_first.py) so both arms line up.
HISTORY_POLICIES = ("none", "retained_reports_v2", "separate_reports_post_task_v1")
PREPARE_TEXT = (   # ICL PREPARE_A wording, adapted to acting
    "Before the next episode, review what you have observed so far and prepare "
    "for the episodes ahead. Write any notes you find useful. Reply in free text; "
    "do not include a JSON object.")
REPORT_TEXT = (    # the Period A report, asked once after the M0 episodes
    "Report what you currently believe about every action you have tried. For each "
    "location and action label give whether the action is available, the location it "
    "leads to, and its success probability as a number from 0 to 1. Reply with exactly "
    "one JSON object of the form {\"transitions\": [{\"location\": \"A\", \"action\": "
    "\"a1\", \"available\": true, \"destination\": \"B\", \"p_success\": 0.8}]}.")
SEEDS_51 = [33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 48, 49, 51, 52, 53, 54, 55, 56,
            57, 58, 59, 60, 61, 62, 63, 64, 66, 68, 69, 70, 71, 72, 73, 74, 76, 77, 78, 79, 81,
            83, 84, 85, 86, 87, 88, 89, 90, 91]

_ORIG = {"prompt": A.build_system_prompt, "policy": A._build_recording_policy, "run": A.run_explore_instance}
_STATE = {"condition": "task_only", "episodes": 0, "mdp": None, "descriptions": [],
          "history": "none", "matched_prep": False, "reports": [],
          "mode_prompts": False, "deterministic": False, "nudge": False}
# Opt-in with --nudge (study plan v1): one sentence added at the end of the system prompt.
NUDGE_SENTENCE = ("When an action keeps failing, consider trying actions or routes you have not "
                  "tried yet.")


# Sentences in explore_agent's system prompt that say the network must be learned by trying.
# The first is the prompt on main, the second the reworded prompt on the editPrompts branch.
LEARN_SENTENCES = (
    "You do not know the network's structure or reliabilities in advance: "
    "you must learn them by trying actions and observing what happens. ",
    "You can learn where any action leads or how reliable the link is only by trying "
    "actions and watching the outcomes. ")
# Mode-specific system-prompt sentence (opt-in with --mode-prompts). Proposed wording;
# the team agreed deterministic and stochastic runs need different prompts.
MODE_SENTENCES = {
    True: ("In this network every link behaves the same way each time: an attempt on a "
           "given link either always succeeds or always fails. "),
    False: ("In this network an attempt on a link succeeds with some fixed probability, "
            "so the same link can succeed one time and fail the next. "),
}
GRAPH_SENTENCE = ("At the start of each phase you receive the network's current "
                  "specification: every location's actions with their "
                  "destinations and success probabilities. ")


def system_prompt(args, condition):
    """args: whatever explore_agent.build_system_prompt takes (goal, or goal, start, horizon)."""
    text = _ORIG["prompt"](*args)
    if condition == "graph_given":
        hit = [s for s in LEARN_SENTENCES if s in text]
        assert hit, "explore_agent prompt changed; add its learn-by-trying sentence to LEARN_SENTENCES"
        text = text.replace(hit[0], GRAPH_SENTENCE)
    if _STATE["mode_prompts"]:
        hit = [s for s in LEARN_SENTENCES if s in text]
        assert hit or condition == "graph_given", "explore_agent prompt changed; add its learn-by-trying sentence to LEARN_SENTENCES"
        anchor = (GRAPH_SENTENCE if condition == "graph_given" else hit[0]) if hit or condition == "graph_given" else None
        text = text.replace(anchor, anchor + MODE_SENTENCES[_STATE["deterministic"]])
    if condition == "model_first":
        text += (" Between episodes you will also be asked to describe your "
                 "current model of the network; that reply needs no JSON object.")
    if _STATE["nudge"]:
        text = text.rstrip() + " " + NUDGE_SENTENCE
    _STATE["system_prompt"] = text
    return text


def graph_text(mdp, labels):
    rows = ["Current network specification:", "location | action | destination | p_success"]
    for (u, v), p in sorted(mdp.p.items(), key=lambda e: (e[0][0], labels[e[0]])):
        rows.append(f"{u} | {labels[(u, v)]} | {v} | {p:g}")
    return "\n".join(rows)


def _policy(mdp, labels, cfg, messages, step_meta, **kw):
    """Called once per episode by run_explore_instance; adds the condition's extra input."""
    cond = _STATE["condition"]
    phase_start = mdp is not _STATE["mdp"]
    _STATE["mdp"] = mdp
    if cond == "graph_given" and phase_start:
        spec = graph_text(mdp, labels)
        kw["initial_note"] = spec if kw.get("initial_note") is None else kw["initial_note"] + "\n\n" + spec
    act = kw.get("act_fn")
    def call(msgs):
        return act(kw["system_prompt"], msgs) if act else (_STATE.get("dry_text", "(dry-run reply)"), "")
    if _STATE["history"] != "none" and phase_start and _STATE["episodes"] > 0:
        # Period A report after the M0 episodes: retained keeps it for M1, separate asks it on a copy.
        probe = [dict(m) for m in messages]
        if probe and probe[-1]["role"] == "user":
            probe[-1] = {"role": "user", "content": probe[-1]["content"] + "\n\n" + REPORT_TEXT}
        else:
            probe.append({"role": "user", "content": REPORT_TEXT})
        text, reasoning = call(probe)
        _STATE["reports"].append({"after_episode": _STATE["episodes"], "history": _STATE["history"],
                                  "text": text, "reasoning": reasoning})
        if _STATE["history"] == "retained_reports_v2":
            messages[:] = probe + [{"role": "assistant", "content": text}]
    prep = cond == "model_first" or (_STATE["matched_prep"] and cond in ("task_only", "graph_given"))
    if prep and _STATE["episodes"] > 0:
        if cond == "model_first":
            ask = MODEL_FIRST_FIRST if _STATE["episodes"] == 1 else MODEL_FIRST_UPDATE
        else:
            ask = PREPARE_TEXT
        if messages and messages[-1]["role"] == "user":       # keep roles alternating
            messages[-1] = {"role": "user", "content": messages[-1]["content"] + "\n\n" + ask}
        else:
            messages.append({"role": "user", "content": ask})
        text, reasoning = call(messages)
        messages.append({"role": "assistant", "content": text})
        _STATE["descriptions"].append({"before_episode": _STATE["episodes"], "text": text,
                                       "reasoning": reasoning, "scored": "not_scored_by_design"})
    _STATE["episodes"] += 1
    return _ORIG["policy"](mdp, labels, cfg, messages, step_meta, **kw)


def _run(inst, cfg, act_fn=None, node_policy_fn=None):
    _STATE.update(episodes=0, mdp=None, descriptions=[], reports=[], deterministic=bool(getattr(inst, "deterministic", False)))
    res = _ORIG["run"](inst, cfg, act_fn=act_fn, node_policy_fn=node_policy_fn)
    res["descriptions"], res["condition"] = list(_STATE["descriptions"]), _STATE["condition"]
    res["reports"] = list(_STATE["reports"])
    return res


def activate(condition, mode_prompts=False, history="none", matched_prep=False, nudge=False):
    """Switch explore_agent to `condition`. With every switch off, task_only restores the originals."""
    if condition not in CONDITIONS:
        raise ValueError(f"unknown condition {condition!r}; expected one of {CONDITIONS}")
    if history not in HISTORY_POLICIES:
        raise ValueError(f"unknown history {history!r}; expected one of {HISTORY_POLICIES}")
    _STATE.update(condition=condition, mode_prompts=mode_prompts, history=history, matched_prep=matched_prep,
                  nudge=nudge)
    if condition == "task_only" and not mode_prompts and history == "none" and not matched_prep and not nudge:
        A.build_system_prompt, A._build_recording_policy, A.run_explore_instance = \
            _ORIG["prompt"], _ORIG["policy"], _ORIG["run"]
    else:
        A.build_system_prompt = lambda *args: system_prompt(args, condition)
        A._build_recording_policy, A.run_explore_instance = _policy, _run


def tokens_of(artifact):
    """Token totals from run_pilot's token_usage_total, used when a run has no usage.json."""
    t = artifact.get("token_usage_total") or {}
    return {"calls": t.get("n_calls", ""), "input_tokens": t.get("prompt_tokens", ""),
            "output_tokens": t.get("completion_tokens", "")}


# ---------------------------------------------------------------- exposure
def must_update(artifact, inst=None):
    """True if the agent's own last M0 route became invalid or more expensive after the change
    (restraint cases, where the old route stays best, are False); "" if it never reached the goal."""
    ins = artifact.get("instance", {})
    m0 = artifact.get("explore", {}).get("m0_episodes")
    if inst is None and ("graph_seed" not in ins or not m0):
        return ""   # not enough information in this artifact (e.g. a metrics-only record)
    inst = inst or make_pair(ins["graph_seed"], ins["condition"], matched=ins.get("matched", True),
                             deterministic=ins.get("deterministic", False))
    if not m0:
        return ""
    moves = [(st["node"], st["next_node"]) for st in m0[-1]["steps"] if st.get("success")]
    if not moves or moves[-1][1] != inst.m1.goal:
        return ""
    ps = [inst.m1.p.get(e, 0) for e in moves]
    cost = sum(1 / p for p in ps) if all(p > 0 for p in ps) else float("inf")
    return cost > inst.oracle["post"]["optimal_cost"] + 5e-4


def exposure(artifact):
    """Did the agent's own route meet the changed link? See the module docstring."""
    ins = artifact["instance"]
    cond = ins["condition"]
    if cond == "no_change":
        return {"changed_link": "", "m0_route_uses": "", "must_update": "", "m0_any_use": "", "m1_attempts": "", "exposed": ""}
    usage = artifact['explore'].get('metrics', {}).get('changed_action_usage', {})
    if 'm0_route_uses' in usage:
        return {'changed_link': f"{usage['node']}:{usage['action_label']}",
                'm0_route_uses': usage['m0_route_uses'],
                'must_update': must_update(artifact),
                'm0_any_use': usage['m0']['n_choices'] > 0,
                'm1_attempts': usage['m1']['n_choices'],
                'exposed': usage['m0_route_uses']}
    # Compatibility fallback for old artifacts; their saved scores are unchanged.
    inst = make_pair(ins["graph_seed"], cond, matched=ins.get("matched", True), deterministic=ins.get("deterministic", False))
    u, v = inst.change["edge"]
    label = inst.labels[(u, v)]
    uses = lambda ep: any(st["node"] == u and st.get("action_label") == label for st in ep["steps"])
    m0 = artifact["explore"]["m0_episodes"]
    m1 = artifact["explore"]["m1_episodes"]
    route_uses = bool(m0) and uses(m0[-1])
    return {"changed_link": f"{u}:{label}", "m0_route_uses": route_uses, "must_update": must_update(artifact, inst),
            "m0_any_use": any(uses(ep) for ep in m0),
            "m1_attempts": sum(1 for ep in m1 for st in ep["steps"] if st["node"] == u and st.get("action_label") == label),
            "exposed": route_uses}


def exposure_csv(runs_dir):
    import csv
    rows = []
    for root, _, files in os.walk(runs_dir):
        for f in sorted(files):
            if f.startswith("pilot_") and f.endswith(".json"):
                a = json.load(open(os.path.join(root, f)))
                if "explore" not in a:
                    continue
                meta_p = os.path.join(root, "condition.json")
                meta = json.load(open(meta_p)) if os.path.exists(meta_p) else {}
                tot = meta.get("usage_totals") or tokens_of(a)   # fall back to run_pilot's token_usage_total
                rows.append({"run": os.path.relpath(os.path.join(root, f), runs_dir), "seed": a["instance"]["graph_seed"],
                             "mode": "det" if a["instance"].get("deterministic") else "sto",
                             "scenario": a["instance"]["condition"], "prompt_condition": meta.get("condition", "task_only"),
                             "repeat": meta.get("repeat", 0), "model": (a.get("model") or {}).get("model", "") if isinstance(a.get("model"), dict) else a.get("model", ""),
                             "calls": tot.get("calls", ""), "input_tokens": tot.get("input_tokens", ""),
                             "output_tokens": tot.get("output_tokens", ""),
                             "usage_complete": tot.get("usage_complete", ""),
                             "n_input_reported": tot.get("n_input_reported", ""),
                             "n_output_reported": tot.get("n_output_reported", ""), **exposure(a)})
    out = os.path.join(runs_dir, "exposure.csv")
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]) if rows else ["run"])
        w.writeheader(); w.writerows(rows)
    n_exp = sum(1 for r in rows if r["exposed"] is True)
    print(f"{len(rows)} runs, {n_exp} exposed, written to {out}")
    return rows


# ---------------------------------------------------------------- run / batch
def run(condition, pilot_args, repeat=0, mode_prompts=False, history="none", matched_prep=False, nudge=False):
    activate(condition, mode_prompts, history, matched_prep, nudge)
    import run_pilot
    calls = []
    orig_retry = run_pilot.with_retry
    def logged(fn, *a, **kw):
        res = orig_retry(fn, *a, **kw)
        if isinstance(res, tuple) and res and isinstance(res[-1], dict):
            calls.append(res[-1])
        return res
    run_pilot.with_retry = logged
    orig_cfg = A.ExploreConfig
    if repeat:
        def cfg_factory(*a, **kw):
            kw["seed"] = kw.get("seed", 0) * 100 + repeat
            return orig_cfg(*a, **kw)
        A.ExploreConfig = cfg_factory
    sys.argv = ["run_pilot.py"] + pilot_args
    try:
        run_pilot.main()
    finally:
        run_pilot.with_retry, A.ExploreConfig = orig_retry, orig_cfg
    out = pilot_args[pilot_args.index("--out") + 1] if "--out" in pilot_args else "pilot_artifacts"
    tag = pilot_args[pilot_args.index("--tag") + 1] if "--tag" in pilot_args else None
    if tag:   # sidecar: the condition and exposure are not in run_pilot's artifact schema
        d = os.path.join(out, tag); os.makedirs(d, exist_ok=True)
        meta = {"history": history, "matched_prep": matched_prep, "nudge": nudge, "reports": list(_STATE["reports"]), "condition": condition, "repeat": repeat, "mode_prompts": mode_prompts,
                "system_prompt": _STATE.get("system_prompt", "(original explore_agent prompt)"),
                "usage_totals": _usage_totals(calls)}
        json.dump({"calls": calls, "totals": _usage_totals(calls)}, open(os.path.join(d, "usage.json"), "w"), indent=1)
        for f in os.listdir(d):
            if f.startswith("pilot_") and f.endswith(".json"):
                a = json.load(open(os.path.join(d, f)))
                if "explore" in a:
                    meta["exposure"] = exposure(a)
        json.dump(meta, open(os.path.join(d, "condition.json"), "w"))


def batch(outdir, conditions, provider_args):
    import subprocess
    failed = 0
    for cond in conditions:
        for s in SEEDS_51:
            tag = f"s{s}_{cond}"
            if any(f.startswith("pilot_") for f in os.listdir(os.path.join(outdir, tag))) if os.path.isdir(os.path.join(outdir, tag)) else False:
                continue   # resume
            cmd = [sys.executable, "-B", __file__, "run", cond, "--", "--pilot-type", "active", "--mode", "sto",
                   "--scenario", "seed7_silent_break", "--seed", str(s), "--tag", tag, "--out", outdir] + provider_args
            if subprocess.run(cmd, stdout=subprocess.DEVNULL).returncode != 0:
                failed += 1; print(f"FAILED seed {s} {cond}", file=sys.stderr)
    print(f"done, {failed} failures")


# ---------------------------------------------------------------- cost estimate
def estimate(n_seeds=51, desc_tokens=250, step_out=(50, 1000), probe_out=300):
    """Offline: dry-run every seed, rebuild each call's input (system + trimmed transcript,
    as the live loop sends it) and count tokens with the harness estimate len(text)//4."""
    tok = lambda t: len(t) // 4
    wander = lambda mdp, labels: (lambda u, rng: rng.choice(sorted(v for (a, v) in mdp.p if a == u)))
    rows = {}
    for cond in CONDITIONS:
        for name, pol in (("efficient", A.dry_run_policy), ("wandering", wander)):
            ins, outs_n, outs_r = [], [], []
            for s in SEEDS_51[:n_seeds]:
                activate(cond); _STATE["dry_text"] = "x" * (4 * desc_tokens)
                inst = make_pair(s, "silent_break", matched=True)
                cfg = A.ExploreConfig(seed=s)
                res = A.run_explore_instance(inst, cfg, node_policy_fn=lambda m: pol(m, inst.labels))
                system, msgs = A.build_system_prompt(*(inst.m0.goal, inst.start, cfg.max_steps_per_episode)[:len(__import__("inspect").signature(_ORIG["prompt"]).parameters)]), res["messages"]
                total = steps = descs = 0
                for i, m in enumerate(msgs):
                    if m["role"] == "assistant":
                        if m["content"].startswith("xxxx"): descs += 1
                        else: steps += 1
                        total += tok(system) + sum(tok(x["content"]) for x in
                                                   A.trim_history(msgs[:i], cfg.max_context_tokens_est, cfg.keep_last_n_turns_min))
                total += 4 * (tok(system) + sum(tok(m["content"]) for m in msgs) + 150)   # four probes
                ins.append(total)
                outs_n.append(steps * step_out[0] + descs * desc_tokens + 4 * probe_out)
                outs_r.append(steps * step_out[1] + descs * (desc_tokens + step_out[1]) + 4 * (probe_out + step_out[1]))
            rows[(cond, name)] = tuple(st.mean(x) * n_seeds / 1e6 for x in (ins, outs_n, outs_r))
    activate("task_only"); _STATE.pop("dry_text", None)
    print(f"per model, {n_seeds} seeds; output assumes {step_out[0]} / {step_out[1]} tokens per step (no reasoning / reasoning)")
    print(f"{'condition':12} {'behaviour':10} {'input M':>8} {'out M':>7} {'out M reas.':>11} {'gpt-4o $':>9}")
    for (c, b), (i, on, orr) in rows.items():
        print(f"{c:12} {b:10} {i:8.1f} {on:7.2f} {orr:11.1f} {i * 2.5 + on * 10:9.0f}")
    return rows


# ---------------------------------------------------------------- tests
def test():
    import unittest
    import inspect
    n_args = len(inspect.signature(_ORIG["prompt"]).parameters)
    pargs = ("C", "A", 20)[:n_args]
    golden = _ORIG["prompt"](*pargs)
    def scripted(log):
        def act(system, messages):
            last = messages[-1]["content"]
            log.append("describe" if "construct a model" in last or "update your model" in last else "step")
            if log[-1] == "describe":
                return "A has two actions; the route via B looks reliable.", ""
            legal = re.findall(r"Legal actions here: ([a0-9, ]+)", last)
            return '{"action": "%s"}' % (legal[-1].split(",")[0].strip() if legal else "a1"), ""
        return act
    def go(cond):
        activate(cond); log = []
        inst = make_pair(33, "silent_break", matched=True)
        cfg = A.ExploreConfig(max_episodes_m0=2, max_episodes_m1=2, max_steps_per_episode=6, seed=33)
        return inst, A.run_explore_instance(inst, cfg, act_fn=scripted(log)), log
    class T(unittest.TestCase):
        def test_task_only_untouched(self):
            activate("task_only")
            self.assertIs(A.build_system_prompt, _ORIG["prompt"])
            self.assertIs(A.run_explore_instance, _ORIG["run"])
        def test_unknown_rejected(self):
            with self.assertRaises(ValueError): activate("graph_first")
        def test_model_first(self):
            inst, res, log = go("model_first")
            self.assertEqual(len(res["descriptions"]), 3); self.assertEqual(log.count("describe"), 3)
            roles = [m["role"] for m in res["messages"]]
            self.assertTrue(all(a != b for a, b in zip(roles, roles[1:])))
            self.assertNotEqual(A.build_system_prompt(*pargs), golden)
        def test_graph_given(self):
            inst, res, log = go("graph_given")
            specs = [m["content"] for m in res["messages"] if "Current network specification" in m["content"]]
            self.assertEqual(len(specs), 2)
            u, v = inst.change["edge"]
            self.assertIn(f"{u} | {inst.labels[(u, v)]} | {v} | 0", specs[1])
            self.assertEqual(res["descriptions"], [])
        def test_exposure(self):
            activate("task_only")
            inst = make_pair(33, "silent_break", matched=True)
            u, v = inst.change["edge"]; lab = inst.labels[(u, v)]
            other = next(l for (a, b), l in inst.labels.items() if a == u and b != v)
            step = lambda node, l: {"node": node, "action_label": l}
            art = lambda last: {"instance": {"graph_seed": 33, "condition": "silent_break", "matched": True, "deterministic": False},
                                "explore": {"m0_episodes": [{"steps": [step(u, lab)]}, {"steps": [step(u, last)]}],
                                            "m1_episodes": [{"steps": [step(u, lab), step(u, lab), step(u, other)]}]}}
            e = exposure(art(lab))
            self.assertTrue(e["exposed"]); self.assertEqual(e["m1_attempts"], 2); self.assertEqual(e["changed_link"], f"{u}:{lab}")
            e = exposure(art(other))             # last M0 route avoids the link: not exposed, though used earlier
            self.assertFalse(e["exposed"]); self.assertTrue(e["m0_any_use"])
            nc = {"instance": {"graph_seed": 33, "condition": "no_change"}, "explore": {"m0_episodes": [], "m1_episodes": []}}
            self.assertEqual(exposure(nc)["exposed"], "")
        def test_usage_totals_missing_and_aliases(self):
            with self.subTest(guard="missing_usage_is_unknown"):
                totals = _usage_totals([{}])
                self.assertIsNone(totals["input_tokens"])
                self.assertIsNone(totals["output_tokens"])
            with self.subTest(guard="token_aliases_count_once"):
                totals = _usage_totals([{"prompt_tokens": 10, "input_tokens": 10,
                                        "completion_tokens": 5, "output_tokens": 5}])
                self.assertEqual((totals["input_tokens"], totals["output_tokens"]), (10, 5))
            with self.subTest(guard="mixed_usage_fields"):
                totals = _usage_totals([{"input_tokens": 9, "output_tokens": 4},
                                        {"prompt_tokens": 7, "completion_tokens": 2}])
                self.assertEqual((totals["input_tokens"], totals["output_tokens"]), (16, 6))
            with self.subTest(guard="partial_usage_keeps_reported_counts"):
                totals = _usage_totals([{"prompt_tokens": 10, "completion_tokens": 5}, {}])
                self.assertIsNone(totals["input_tokens"])
                self.assertEqual(totals["reported_input_tokens"], 10)
                self.assertEqual(totals["n_input_reported"], 1)
                self.assertFalse(totals["usage_complete"])
            with self.subTest(guard="conflicting_aliases_are_unknown"):
                totals = _usage_totals([{"prompt_tokens": 10, "input_tokens": 12,
                                        "completion_tokens": 5}])
                self.assertIsNone(totals["input_tokens"])
                self.assertEqual(totals["alias_conflicts"], [{"call": 0, "field": "input"}])
            with self.subTest(guard="zero_calls_are_explicit"):
                totals = _usage_totals([])
                self.assertEqual((totals["calls"], totals["input_tokens"], totals["output_tokens"]), (0, 0, 0))
                self.assertTrue(totals["usage_complete"])
            with self.subTest(guard="invalid_counts_are_unknown"):
                for value in (True, -1, "10", 10.5):
                    totals = _usage_totals([{"prompt_tokens": value, "completion_tokens": 5}])
                    self.assertIsNone(totals["input_tokens"])
                    self.assertEqual(totals["n_input_reported"], 0)
                    self.assertFalse(totals["usage_complete"])
        def test_mode_prompts(self):
            for det in (True, False):
                activate("task_only", mode_prompts=True)
                inst = make_pair(33, "silent_break", matched=True, deterministic=det)
                cfg = A.ExploreConfig(max_episodes_m0=1, max_episodes_m1=1, max_steps_per_episode=4, seed=33)
                captured = []
                def act(system, messages):
                    captured.append(system); return '{"action": "a1"}', ""
                A.run_explore_instance(inst, cfg, act_fn=act)
                want, other = ("always succeeds or always fails", "fixed probability") if det else ("fixed probability", "always succeeds or always fails")
                self.assertIn(want, captured[0]); self.assertNotIn(other, captured[0])
            activate("task_only")
            self.assertIs(A.build_system_prompt, _ORIG["prompt"])      # off by default
        def test_nudge(self):
            inst = make_pair(33, "silent_break", matched=True, deterministic=False)
            cfg = A.ExploreConfig(max_episodes_m0=1, max_episodes_m1=1, max_steps_per_episode=3, seed=33)
            for cond in CONDITIONS:
                for nudge in (False, True):
                    activate(cond, mode_prompts=True, nudge=nudge)
                    captured = []
                    def act(system, messages):
                        captured.append(system); return '{"action": "a1"}', ""
                    A.run_explore_instance(inst, cfg, act_fn=act)
                    self.assertEqual(captured[0].endswith(NUDGE_SENTENCE), nudge, (cond, nudge))
                    self.assertEqual(captured[0].count(NUDGE_SENTENCE), int(nudge))
            activate("task_only")
            self.assertIs(A.build_system_prompt, _ORIG["prompt"])      # off by default
        def test_history_and_prep_switches(self):
            for hist in ("retained_reports_v2", "separate_reports_post_task_v1"):
                activate("task_only", history=hist, matched_prep=True)
                inst = make_pair(33, "silent_break", matched=True)
                cfg = A.ExploreConfig(max_episodes_m0=2, max_episodes_m1=2, max_steps_per_episode=6, seed=33)
                res = A.run_explore_instance(inst, cfg, act_fn=scripted([]))
                text = "".join(m["content"] for m in res["messages"])
                self.assertEqual(len(res["reports"]), 1)
                self.assertEqual(REPORT_TEXT in text, hist == "retained_reports_v2")
                self.assertIn("prepare for the episodes ahead", text)
            with self.assertRaises(ValueError): activate("task_only", history="kept")
        def test_must_update(self):
            activate("task_only")
            inst = make_pair(33, "silent_break", matched=True)
            route = inst.oracle["pre"]["optimal_route"]
            ep = {"steps": [{"node": a, "next_node": b, "success": True, "action_label": inst.labels[(a, b)]} for a, b in zip(route, route[1:])]}
            art = {"instance": {"graph_seed": 33, "condition": "silent_break", "matched": True, "deterministic": False},
                   "explore": {"m0_episodes": [ep], "m1_episodes": []}}
            self.assertTrue(must_update(art))
            art["instance"]["condition"] = "irrelevant"
            self.assertFalse(must_update(art))
        def tearDown(self): activate("task_only")
    r = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(T))
    sys.exit(0 if r.wasSuccessful() else 1)


if __name__ == "__main__":
    argv = sys.argv[1:]
    rest = argv[argv.index("--") + 1:] if "--" in argv else []
    head = argv[:argv.index("--")] if "--" in argv else argv
    if not head or head[0] not in ("run", "batch", "estimate", "test", "exposure"):
        print(__doc__); sys.exit(2)
    if head[0] == "test": test()
    elif head[0] == "run": run(head[1], rest, int(head[head.index("--repeat") + 1]) if "--repeat" in head else 0,
                               "--mode-prompts" in head,
                               head[head.index("--history") + 1] if "--history" in head else "none",
                               "--matched-prep" in head, "--nudge" in head)
    elif head[0] == "batch": batch(head[1], head[2:] or list(CONDITIONS), rest)
    elif head[0] == "exposure": exposure_csv(head[1])
    else:
        n = int(head[head.index("--seeds") + 1]) if "--seeds" in head else 51
        estimate(n)

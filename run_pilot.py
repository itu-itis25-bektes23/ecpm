#!/usr/bin/env python3
"""ECPM Phase-2 pilot harness (runs INSIDE the repo, pinned to the freeze).

One harness for every pilot condition. What used to be three near-identical
files (`run_pilot.py`, `run_pilot_lmstudio.py`, `run_pilot_multiturn.py`) is
now this file plus flags:

  * `--scenario`  named entry in SCENARIOS (see below), or build one ad hoc
                  with --condition/--seed/--stochastic/--rendering/...
  * `--tag`       free label for the run; names the output subdirectory and
                  is recorded in every artifact, so a new experimental
                  condition never needs a new .py file
  * `--turn-mode` single (four independent calls, the frozen behaviour),
                  multi (legacy: four turns, both periods sent once) or
                  two_turn (v2.2: period A only first, period B revealed
                  after the turn-1 answers are in context)
  * `--timeout`   per-request seconds; raise it for slow local endpoints

For each pilot, the probes are run end to end:

  prompt_view (prompt-safe payload) -> prompt text -> model ->
  raw response -> frozen parser -> scoring -> artifact JSON

Each artifact retains the agreed list: prompt-safe payload, raw model
response, parser and execution statuses, route/regret outputs, seeds/model
settings, and realized event/token counts, plus the env freeze SHA the run
is pinned to. Multi-turn runs additionally record per-phase metrics and the
full conversation.

A second pilot type, active exploration (--pilot-type active), runs the
model as a live agent instead: it picks its own actions on M0, then on M1
after a reset, and answers the same 4 probes as a continuation of its own
transcript rather than from a handed-over evidence log. See
explore_agent.py. The default passive pilot is unchanged.

Usage (from the repo root):

  python3 run_pilot.py                                   # dry-run, no API
  ANTHROPIC_API_KEY=... python3 run_pilot.py \
      --provider anthropic --model claude-sonnet-4-6
  OPENAI_API_KEY=... python3 run_pilot.py \
      --provider openai --model gpt-4o --base-url https://api.openai.com/v1
  AZURE_OPENAI_API_KEY=... python3 run_pilot.py \
      --provider azure --model YOUR-DEPLOYMENT \
      --azure-endpoint https://YOUR-RESOURCE.openai.azure.com
  python3 run_pilot.py --pilot-type active                # active exploration instead

  # local LM Studio (OpenAI-compatible, slow: needs the long timeout)
  OPENAI_API_KEY=lm-studio python3 run_pilot.py \
      --provider openai --model gemma-4-e4b \
      --base-url http://localhost:1234/v1 --timeout 900 \
      --tag 2026-08-23_gemma4e4b_lmstudio

  # v2.2 two-turn protocol (period A -> route_pre, belief_pre; then
  # period B revealed -> detection, localization, preservation,
  # adaptation), optionally with belief re-elicitation
  python3 run_pilot.py --turn-mode two_turn --reelicit --tag twoturn_v1
  # legacy multi-turn and its single-turn A/B baseline
  python3 run_pilot.py --turn-mode multi --tag multiturn_probe
  python3 run_pilot.py --turn-mode single --tag multiturn_probe

  # a different environment condition, no new file needed
  python3 run_pilot.py --scenario seed7_hard_removal --tag hardremoval_v1
  python3 run_pilot.py --condition irrelevant --seed 11 --tag adhoc_seed11

  python3 run_pilot.py --list-scenarios

Outputs: <out>/<tag>/pilot_deterministic.json, pilot_stochastic.json
(with _multi / _dryrun suffixes as applicable). Default out is
pilot_artifacts/ (an "_active" part is added for --pilot-type active).
stdlib only.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import random
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import asdict

import explore_agent
import explore_metrics
from ecpm_parser import (PARSERS, belief_self_consistency, run_probe,
                         score_belief, score_route_pre)
from resource_mdp import (CONDITIONS, PROMPT_RENDERINGS, SCHEMA_VERSION,
                          make_pair, pair_to_json, paired_evidence,
                          prompt_view)

FROZEN_SHA = "5318c3e113438c563c5676d58252d84fda22aa49"
ALL_PROBES = ("detection", "localization", "preservation", "adaptation")
# v2.2 two-turn protocol: turn 1 sees period A only and answers these two;
# turn 2 reveals period B (turn 1 stays in context) and asks ALL_PROBES.
TURN1_PROBES = ("route_pre", "belief_pre")
REELICIT_PROBE = "belief_post"

# ---------------------------------------------------------------- scenarios
#
# A scenario is everything about WHAT is asked, independent of WHICH model
# answers. Add an entry here instead of copying this file. Any key may also
# be overridden on the command line.
#
#   condition      one of resource_mdp.CONDITIONS
#   seed           graph seed
#   matched        matched-pair generation
#   k              evidence episodes per (state, action) pair
#   evidence_seed  evidence sampling seed
#   rendering      one of resource_mdp.PROMPT_RENDERINGS
#   budget         budget_per_pair passed to prompt_view
#   probes         which probes to run, in order
#   variants       which of det / sto this condition is defined for

SCENARIO_DEFAULTS = {
    "condition": "silent_break",
    "seed": 7,
    "matched": True,
    "k": 5,
    "evidence_seed": 0,
    "rendering": "F2_shuffled",
    "budget": 5,
    "probes": ALL_PROBES,
    "variants": ("det", "sto"),
}

SCENARIOS = {
    # the frozen showcase pair; this is what runs/ was produced with
    "seed7_silent_break": {},
    "seed7_hard_removal": {"condition": "hard_removal"},
    # degradation is undefined in deterministic worlds (v2.1): stochastic only
    "seed7_degradation": {"condition": "degradation", "variants": ("sto",)},
    "seed7_irrelevant": {"condition": "irrelevant"},
    # no change happened: localization has a false premise, so it is dropped
    "seed7_no_change": {
        "condition": "no_change",
        "probes": ("detection", "preservation", "adaptation"),
    },
    # rendering ablation on the frozen instance
    "seed7_silent_break_narrative": {"rendering": "F4_narrative"},
    "seed7_silent_break_stats": {"rendering": "F3_stats"},
}


def resolve_scenario(args):
    """SCENARIO_DEFAULTS <- named scenario <- explicit CLI overrides."""
    if args.scenario not in SCENARIOS:
        raise SystemExit(f"unknown scenario {args.scenario!r}; "
                         f"known: {', '.join(sorted(SCENARIOS))}")
    sc = dict(SCENARIO_DEFAULTS)
    sc.update(SCENARIOS[args.scenario])
    sc["name"] = args.scenario
    for key, val in (("condition", args.condition), ("seed", args.seed),
                     ("rendering", args.rendering), ("budget", args.budget),
                     ("k", args.k), ("evidence_seed", args.evidence_seed)):
        if val is not None:
            sc[key] = val
    if args.probes:
        sc["probes"] = tuple(args.probes)
    if sc["condition"] not in CONDITIONS:
        raise SystemExit(f"unknown condition {sc['condition']!r}; "
                         f"known: {', '.join(CONDITIONS)}")
    if sc["rendering"] not in PROMPT_RENDERINGS:
        raise SystemExit(f"unknown rendering {sc['rendering']!r}; "
                         f"known: {', '.join(PROMPT_RENDERINGS)}")
    if sc["condition"] == "no_change" and "localization" in sc["probes"]:
        raise SystemExit("localization asserts a change occurred; drop it "
                         "for condition=no_change (--probes detection "
                         "preservation adaptation)")
    return sc


# ------------------------------------------------------------- prompt parts

INTRO = """You are analysing a courier network. Nodes are locations; at each
node you may attempt the listed actions (aK). An attempt either delivers
you to that action's destination or you stay and retry (each attempt
costs 1). You observed the network in two periods.

Nodes: {nodes}
Start: {start}   Goal: {goal}

Action menu, period A (earlier): {menu_pre}
Action menu, period B (later): {menu_post}

Observations, period A:
{ev_pre}

Observations, period B:
{ev_post}
"""

# v2.2 two-turn protocol. INTRO_A is the turn-1 header (period A only);
# REVEAL_B is prepended to the first turn-2 ask. INTRO_A + REVEAL_B carry
# exactly the same facts as INTRO.
INTRO_A = """You are analysing a courier network. Nodes are locations; at each
node you may attempt the listed actions (aK). An attempt either delivers
you to that action's destination or you stay and retry (each attempt
costs 1). You observed the network in an earlier period (period A). A
later period (period B) will be shown afterwards.

Nodes: {nodes}
Start: {start}   Goal: {goal}

Action menu, period A (earlier): {menu_pre}

Observations, period A:
{ev_pre}
"""

REVEAL_B = """Here is the later period (period B) of the same network.

Action menu, period B (later): {menu_post}

Observations, period B:
{ev_post}
"""

ASKS = {
    "route_pre": (
        'Plan a route for period A from {start} to {goal}. Answer with '
        'exactly one JSON object of the form {{"route": [{{"node": "...", '
        '"action": "..."}}, ...]}}: at most 32 steps, the first step\'s '
        'node must be {start}, each next step\'s node must be where the '
        'previous action leads, and the route must end at {goal}. No other '
        'text.'),
    "belief_pre": (
        'For EACH of the following (node, action) pairs, state what you '
        'believe from the period A observations: the destination node the '
        'action leads to, and its probability of success per attempt '
        '(a number in [0, 1]):\n{queried}\n'
        'Answer with exactly one JSON object of the form '
        '{{"beliefs": [{{"node": "...", "action": "...", "destination": '
        '"...", "p": 0.0}}, ...]}} containing every listed pair exactly '
        'once. No other text.'),
    "belief_post": (
        'Now, for the SAME (node, action) pairs, state your beliefs for '
        'period B: destination node and probability of success per '
        'attempt:\n{queried}\n'
        'Answer with exactly one JSON object of the form '
        '{{"beliefs": [{{"node": "...", "action": "...", "destination": '
        '"...", "p": 0.0}}, ...]}} containing every listed pair exactly '
        'once. No other text.'),
    "detection": (
        'Question: did the network\'s dynamics change between period A and '
        'period B?\nAnswer with exactly one JSON object: '
        '{"changed": true} or {"changed": false}. No other text.'),
    "localization": (
        'The dynamics changed between the periods. Question: which single '
        '(node, action) pair changed?\nAnswer with exactly one JSON '
        'object: {"node": "<node>", "action": "<aK>"}. No other text.'),
    "preservation": (
        'For EACH of the following (node, action) pairs, judge whether its '
        'dynamics changed between period A and period B:\n{queried}\n'
        'Answer with exactly one JSON object of the form '
        '{{"pairs": [{{"node": "...", "action": "...", "changed": '
        'true|false}}, ...]}} containing every listed pair exactly once. '
        'No other text.'),
    "adaptation": (
        'Plan a route for period B (the later network) from {start} to '
        '{goal}. Answer with exactly one JSON object of the form '
        '{{"route": [{{"node": "...", "action": "..."}}, ...]}}: at most '
        '32 steps, the first step\'s node must be {start}, each next '
        'step\'s node must be where the previous action leads, and the '
        'route must end at {goal}. No other text.'),
}

# Same 4 probes, worded for the active-exploration pilot: the model refers
# to its own exploration episodes instead of a handed-over period A/B log.
ASKS_ACTIVE = {
    "detection": (
        'Question: across your two rounds of exploring this network (the '
        'first set of episodes, then the reset and second set), did the '
        'network\'s dynamics change at any point?\nAnswer with exactly '
        'one JSON object: {"changed": true} or {"changed": false}. No '
        'other text.'),
    "localization": (
        'The dynamics changed at some point during your exploration. '
        'Question: which single (node, action) pair changed?\nAnswer '
        'with exactly one JSON object: {"node": "<node>", "action": '
        '"<aK>"}. No other text.'),
    "preservation": (
        'For EACH of the following (node, action) pairs, judge whether '
        'its dynamics changed at any point during your exploration:\n'
        '{queried}\nAnswer with exactly one JSON object of the form '
        '{{"pairs": [{{"node": "...", "action": "...", "changed": '
        'true|false}}, ...]}} containing every listed pair exactly once. '
        'No other text.'),
    "adaptation": (
        'Plan a route for the current network (as of your most recent '
        'exploration) from {start} to {goal}. Answer with exactly one '
        'JSON object of the form {{"route": [{{"node": "...", "action": '
        '"..."}}, ...]}}: at most 32 steps, the first step\'s node must '
        'be {start}, each next step\'s node must be where the previous '
        'action leads, and the route must end at {goal}. No other '
        'text.'),
}


def git_head():
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"],
                             capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except Exception:
        return None


def build_record(sc, deterministic):
    inst = make_pair(sc["seed"], sc["condition"],
                     deterministic=deterministic, matched=sc["matched"])
    ev = paired_evidence(inst, k=sc["k"], evidence_seed=sc["evidence_seed"])
    return json.loads(json.dumps(pair_to_json(inst, ev)))


def queried_pairs_for(record, sc, n_other=3):
    """Deterministic probe set: the target pair (if any) + n_other unchanged
    pairs, order shuffled by a fixed seed. Under no_change there is no
    target, so n_other + 1 unchanged pairs are drawn instead."""
    ch = record["change"]
    target = (None if ch["edge"] is None
              else (ch["edge"]["from"], ch["action"]))
    everyone = sorted((node, a) for node, menu in
                      record["legal_actions_pre"].items() for a in menu)
    others = [p for p in everyone if p != target]
    # seed string unchanged from the frozen harness: archived runs stay
    # reproducible bit-for-bit
    rng = random.Random(f"pilot|{sc['seed']}|preservation")
    picked = rng.sample(others, n_other if target else n_other + 1)
    if target:
        picked = picked + [target]
    rng.shuffle(picked)
    return [{"node": n, "action": a} for n, a in picked]


def _menus(view):
    return {p: "; ".join(f"{node}: {', '.join(m)}" for node, m in
                         sorted(view[f"legal_actions_{p}"].items()))
            for p in ("pre", "post")}


def context_block(view):
    """The shared evidence header (both periods): sent once in the legacy
    multi mode, prepended to every ask in single-turn mode. Frozen text."""
    menus = _menus(view)
    return INTRO.format(nodes=", ".join(view["nodes"]),
                        start=view["start"], goal=view["goal"],
                        menu_pre=menus["pre"], menu_post=menus["post"],
                        ev_pre=view["evidence"]["pre"],
                        ev_post=view["evidence"]["post"])


def context_block_a(view):
    """v2.2 turn-1 header: period A only."""
    menus = _menus(view)
    return INTRO_A.format(nodes=", ".join(view["nodes"]),
                          start=view["start"], goal=view["goal"],
                          menu_pre=menus["pre"],
                          ev_pre=view["evidence"]["pre"])


def reveal_block_b(view):
    """v2.2 turn-2 reveal: period B only (turn 1 stays in context)."""
    menus = _menus(view)
    return REVEAL_B.format(menu_post=menus["post"],
                           ev_post=view["evidence"]["post"])


def ask_block(view, probe, queried):
    """The probe question alone (no evidence)."""
    ask = ASKS[probe]
    if probe in ("preservation", "belief_pre", "belief_post"):
        listed = "\n".join(f'- node {q["node"]}, action {q["action"]}'
                           for q in queried)
        ask = ask.format(queried=listed)
    elif probe in ("adaptation", "route_pre"):
        ask = ask.format(start=view["start"], goal=view["goal"])
    return ask + "\n"


# ------------------------------------------------------------------ metrics


def phase_metrics(probe, scored):
    """Normalise one probe's scored output to a comparable per-phase row.

    `score` is the single primary 0..1 number for that phase, so phases can
    be plotted on one axis; probe-specific detail is kept alongside."""
    status = scored.get("status")
    parse_ok = status not in ("malformed_json", "invalid_object", "too_long")
    m = {"probe": probe, "status": status, "parse_ok": parse_ok,
         "scored_ok": status == "ok", "score": 0.0, "detail": {}}
    if probe in ("detection", "localization"):
        m["score"] = 1.0 if scored.get("correct") else 0.0
        m["detail"] = {"correct": bool(scored.get("correct")),
                       "predicted": scored.get("predicted",
                                               scored.get("pair")),
                       "truth": scored.get("truth")}
    elif probe == "preservation":
        acc = scored.get("accuracy")
        m["score"] = float(acc) if acc is not None else 0.0
        m["detail"] = {"accuracy": acc, "n_queried": scored.get("n_queried"),
                       "n_scored": scored.get("n_scored")}
    elif probe in ("belief_pre", "belief_post"):
        acc = scored.get("accuracy")
        m["score"] = float(acc) if acc is not None else 0.0
        m["detail"] = {"accuracy": acc,
                       "destination_accuracy":
                           scored.get("destination_accuracy"),
                       "p_mae": scored.get("p_mae"),
                       "n_queried": scored.get("n_queried"),
                       "n_scored": scored.get("n_scored")}
    elif probe in ("adaptation", "route_pre"):
        # graded: optimal route only. regret/cost reported separately.
        m["score"] = 1.0 if scored.get("is_optimal") else 0.0
        m["scored_ok"] = status == "valid_finite"
        m["detail"] = {"is_optimal": bool(scored.get("is_optimal")),
                       "regret": scored.get("regret"),
                       "expected_cost": scored.get("expected_cost"),
                       "optimal_cost": scored.get("optimal_cost"),
                       "path": scored.get("path")}
    return m


def cumulative(rows):
    """Running totals after the phases seen so far."""
    n = len(rows)
    return {
        "phases_done": n,
        "phases_parse_ok": sum(1 for r in rows if r["parse_ok"]),
        "phases_scored_ok": sum(1 for r in rows if r["scored_ok"]),
        "score_sum": round(sum(r["score"] for r in rows), 4),
        "score_mean": (round(sum(r["score"] for r in rows) / n, 4)
                       if n else None),
        "prompt_tokens_est": sum(r.get("prompt_tokens_est", 0) for r in rows),
        "latency_s": round(sum(r.get("latency_s", 0.0) for r in rows), 3),
    }


def phase_line(idx, row, cum):
    d = row["detail"]
    extra = ""
    if row["probe"] in ("adaptation", "route_pre"):
        extra = (f" regret={d.get('regret')} cost={d.get('expected_cost')}"
                 f"/{d.get('optimal_cost')}")
    elif row["probe"] in ("preservation", "belief_pre", "belief_post"):
        extra = f" acc={d.get('accuracy')} ({d.get('n_queried')} pairs)"
        if row["probe"] != "preservation":
            extra += f" dest={d.get('destination_accuracy')} pMAE={d.get('p_mae')}"
    return (f"  phase {idx} {row['probe']:<13} status={str(row['status']):<20}"
            f" score={row['score']:.2f}{extra}"
            f" | cum mean={cum['score_mean']} tok~{cum['prompt_tokens_est']}"
            f" {cum['latency_s']}s")


# ---------------------------------------------------------------- providers
#
# All three take a full `messages` list, so the same call works for a
# one-shot probe and for a later turn that carries history.


class TransientLLMError(Exception):
    """Empty/unparseable LLM response body -- treated as retryable by
    with_retry, same spirit as a network error."""


def with_retry(fn, *args, max_attempts=6, base_delay=1.0, max_delay=30.0,
               **kwargs):
    """Call fn(*args, **kwargs), retrying transient failures with jittered
    exponential backoff (honoring a Retry-After header when present).
    Retryable: HTTP 429/500/502/503/504, network/timeout errors, and
    empty/unparseable response bodies (TransientLLMError, KeyError,
    json.JSONDecodeError). Everything else (4xx auth/bad-request errors)
    raises immediately. Stdlib only -- reimplements the retry pattern seen
    in reference material, no third-party dependency added, matching this
    repo's stdlib-only convention."""
    last_exc = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn(*args, **kwargs)
        except urllib.error.HTTPError as ex:
            if ex.code not in (429, 500, 502, 503, 504):
                raise
            last_exc = ex
            retry_after = ex.headers.get("Retry-After") if ex.headers else None
            delay = (float(retry_after) if retry_after
                     else min(max_delay, base_delay * 2 ** (attempt - 1)))
        except (urllib.error.URLError, TimeoutError, ConnectionError,
                json.JSONDecodeError, KeyError, TransientLLMError) as ex:
            last_exc = ex
            delay = min(max_delay, base_delay * 2 ** (attempt - 1))
        if attempt == max_attempts:
            raise last_exc
        delay *= random.uniform(0.5, 1.5)
        print(f"retryable error (attempt {attempt}/{max_attempts}), "
              f"retrying in {delay:.1f}s: {last_exc}")
        time.sleep(delay)


def call_anthropic(model, messages, max_tokens, timeout):
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps({"model": model, "max_tokens": max_tokens,
                         "temperature": 0,
                         "messages": messages}).encode(),
        headers={"content-type": "application/json",
                 "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                 "anthropic-version": "2023-06-01"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    text = "".join(b.get("text", "") for b in data.get("content", []))
    return text, data.get("usage", {})


def call_azure(deployment, messages, max_tokens, endpoint, api_version,
               timeout):
    url = (endpoint.rstrip("/") + "/openai/deployments/" + deployment
           + "/chat/completions?api-version=" + api_version)
    req = urllib.request.Request(
        url,
        data=json.dumps({"max_tokens": max_tokens, "temperature": 0,
                         "messages": messages}).encode(),
        headers={"content-type": "application/json",
                 "api-key": os.environ["AZURE_OPENAI_API_KEY"]})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"], data.get("usage", {})


def call_openai(model, messages, max_tokens, base_url, timeout):
    """OpenAI-compatible chat endpoint. Also covers LM Studio and any other
    local server exposing /v1/chat/completions -- point --base-url at it; the
    key falls back to a placeholder, which local servers ignore."""
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps({"model": model, "max_tokens": max_tokens,
                         "temperature": 0,
                         "messages": messages}).encode(),
        headers={"content-type": "application/json",
                 "authorization":
                     f"Bearer {os.environ.get('OPENAI_API_KEY', 'local')}"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"], data.get("usage", {})


# Multi-turn variants for the active-exploration pilot (system + a growing
# message list, matching explore_agent.py's act_fn(system, messages)
# contract) instead of a single one-shot prompt. Wrapped in with_retry,
# unlike the single-shot passive-mode callers above.


def call_anthropic_chat(model, system, messages, max_tokens, thinking_budget=0):
    """Calls Claude with the given system prompt and message history.
    If thinking_budget > 0, enables Extended Thinking with that token
    budget (Anthropic requires temperature 1 and max_tokens greater than
    thinking_budget in that case) and returns the thinking content
    separately from the visible answer."""
    body = {"model": model, "max_tokens": max_tokens, "system": system,
            "messages": messages}
    if thinking_budget > 0:
        body["thinking"] = {"type": "enabled",
                            "budget_tokens": thinking_budget}
        body["temperature"] = 1
    else:
        body["temperature"] = 0
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json",
                 "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                 "anthropic-version": "2023-06-01"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    reasoning = "".join(b.get("thinking", "") for b in data.get("content", [])
                        if b.get("type") == "thinking")
    text = "".join(b.get("text", "") for b in data.get("content", [])
                   if b.get("type") == "text")
    if not text.strip():
        raise TransientLLMError("empty Anthropic response content")
    return text, reasoning, data.get("usage", {})


def call_openai_chat(model, system, messages, max_tokens, base_url):
    full_messages = [{"role": "system", "content": system}] + list(messages)
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps({"model": model, "max_tokens": max_tokens,
                         "temperature": 0,
                         "messages": full_messages}).encode(),
        headers={"content-type": "application/json",
                 "authorization":
                     f"Bearer {os.environ['OPENAI_API_KEY']}"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    text = data["choices"][0]["message"]["content"]
    if not text.strip():
        raise TransientLLMError("empty OpenAI response content")
    return text, data.get("usage", {})


def call_azure_chat(deployment, system, messages, max_tokens, endpoint,
                    api_version):
    full_messages = [{"role": "system", "content": system}] + list(messages)
    url = (endpoint.rstrip("/") + "/openai/deployments/" + deployment
           + "/chat/completions?api-version=" + api_version)
    req = urllib.request.Request(
        url,
        data=json.dumps({"max_tokens": max_tokens, "temperature": 0,
                         "messages": full_messages}).encode(),
        headers={"content-type": "application/json",
                 "api-key": os.environ["AZURE_OPENAI_API_KEY"]})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    text = data["choices"][0]["message"]["content"]
    if not text.strip():
        raise TransientLLMError("empty Azure response content")
    return text, data.get("usage", {})


def dry_run_answer(record, probe, queried):
    """Oracle-derived canned replies (wrapped in prose/fences to exercise
    the extractor). Pipeline demo only; provider is labeled 'dry-run'."""
    ch = record["change"]
    changed = ch["edge"] is not None
    if probe == "detection":
        return ('Looking at period B: ```json\n'
                + json.dumps({"changed": changed}) + '\n```')
    if probe == "localization":
        obj = {"node": ch["edge"]["from"], "action": ch["action"]}
        return "My answer: " + json.dumps(obj)
    if probe == "preservation":
        target = (ch["edge"]["from"], ch["action"]) if changed else None
        pairs = [{"node": q["node"], "action": q["action"],
                  "changed": (q["node"], q["action"]) == target}
                 for q in queried]
        return json.dumps({"pairs": pairs})
    if probe in ("belief_pre", "belief_post"):
        period = "pre" if probe == "belief_pre" else "post"
        truth = {(e["from"], e["action"]): e
                 for e in record[f"world_{period}"]["edges"]}
        beliefs = []
        for q in queried:
            e = truth.get((q["node"], q["action"]))
            beliefs.append({"node": q["node"], "action": q["action"],
                            "destination": e["to"] if e else "?",
                            "p": (e["p"] if e else 0.0)})
        return "Beliefs: " + json.dumps({"beliefs": beliefs})
    o = record["oracle"]["pre" if probe == "route_pre" else "post"]
    steps = [{"node": n, "action": a}
             for n, a in zip(o["optimal_route"], o["optimal_actions"])]
    return json.dumps({"route": steps})


def score_any(record, probe, raw, queried):
    """Frozen probes go through run_probe unchanged; v2.2 turn-1 probes
    are scored by the additive scorers."""
    if probe in ALL_PROBES:
        return run_probe(record, probe, raw,
                         queried_pairs=(queried if probe == "preservation"
                                        else None))
    parsed = PARSERS[probe](raw)
    if probe == "route_pre":
        scored = score_route_pre(record, parsed)
    else:
        scored = score_belief(record, parsed, queried,
                              "pre" if probe == "belief_pre" else "post")
    return {"parsed": parsed, "scored": scored}


def dispatch(args, record, probe, queried, messages):
    if args.provider == "anthropic":
        return call_anthropic(args.model, messages, args.max_tokens,
                              args.timeout)
    if args.provider == "azure":
        return call_azure(args.model, messages, args.max_tokens,
                          args.azure_endpoint, args.api_version, args.timeout)
    if args.provider == "openai":
        return call_openai(args.model, messages, args.max_tokens,
                           args.base_url, args.timeout)
    return dry_run_answer(record, probe, queried), {}


# ------------------------------------------------------------------- pilot


def run_pilot(sc, deterministic, args):
    """Passive pilot: evidence is collected up front and handed to the
    model as text. See run_pilot_active for the live-agent counterpart."""
    probes = tuple(sc["probes"])
    record = build_record(sc, deterministic)
    view = prompt_view(record, rendering=sc["rendering"],
                       periods=("pre", "post"),
                       budget_per_pair=sc["budget"])
    queried = queried_pairs_for(record, sc)
    context = context_block(view)
    head = git_head()

    artifact = {
        "pilot": "deterministic" if deterministic else "stochastic",
        "tag": args.tag,
        "scenario": dict(sc, probes=list(probes),
                         variants=list(sc["variants"])),
        "turn_mode": args.turn_mode,
        "phase_order": list(probes),
        "created_utc": datetime.datetime.now(
            datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "env": {"schema_version": SCHEMA_VERSION, "frozen_sha": FROZEN_SHA,
                "git_head": head, "pinned_to_freeze": head == FROZEN_SHA},
        "instance": {"graph_seed": sc["seed"], "condition": sc["condition"],
                     "deterministic": deterministic,
                     "matched": sc["matched"],
                     "k_per_pair": record["evidence"]["k_per_pair"],
                     "evidence_seed": record["evidence"]["evidence_seed"],
                     "seeds": record["seeds"]},
        "model": {"provider": args.provider, "model": args.model,
                  "temperature": 0, "max_tokens": args.max_tokens,
                  "timeout_s": args.timeout,
                  "rendering": sc["rendering"],
                  "budget_per_pair": sc["budget"]},
        "prompt_safe_payload": view,
        "probes": {},
        "metrics_by_phase": [],
        "conversation": [],
    }

    two_turn = args.turn_mode == "two_turn"
    turn1 = list(TURN1_PROBES) if two_turn else []
    turn2 = list(probes) + ([REELICIT_PROBE] if (two_turn and args.reelicit)
                            else [])
    schedule = ([(p, 1) for p in turn1] + [(p, 2) for p in turn2])
    artifact["phase_order"] = [p for p, _ in schedule]
    artifact["turn_of_phase"] = {p: t for p, t in schedule}
    artifact["belief_pairs"] = queried if two_turn else None

    messages, rows = [], []
    print(f"[{artifact['pilot']}] tag={args.tag} scenario={sc['name']} "
          f"turn_mode={args.turn_mode} provider={args.provider}")

    for idx, (probe, turn) in enumerate(schedule, start=1):
        ask = ask_block(view, probe, queried)
        if args.turn_mode == "multi":
            # legacy: both periods in message 1; later asks rely on history
            user_msg = (context + "\n" + ask) if idx == 1 else ask
        elif two_turn:
            # turn 1 header on the first ask; period-B reveal on the first
            # turn-2 ask; everything else rides on the conversation
            first_of_turn = (idx == 1) or (turn == 2 and
                                            schedule[idx - 2][1] == 1)
            if turn == 1 and first_of_turn:
                user_msg = context_block_a(view) + "\n" + ask
            elif turn == 2 and first_of_turn:
                user_msg = reveal_block_b(view) + "\n" + ask
            else:
                user_msg = ask
        else:
            messages = []                  # no history: one-shot per probe
            user_msg = context + "\n" + ask
        messages = messages + [{"role": "user", "content": user_msg}]

        t0 = time.time()
        raw, usage = dispatch(args, record, probe, queried, messages)
        latency = round(time.time() - t0, 3)
        messages = messages + [{"role": "assistant", "content": raw}]

        result = score_any(record, probe, raw, queried)
        row = phase_metrics(probe, result["scored"])
        row.update({"phase": idx, "turn": turn,
                    "sent_chars": len(user_msg),
                    "context_chars": sum(len(m["content"]) for m in messages),
                    "prompt_tokens_est":
                        sum(len(m["content"]) for m in messages[:-1]) // 4,
                    "latency_s": latency})
        rows.append(row)
        cum = cumulative(rows)

        artifact["probes"][probe] = {
            "phase": idx,
            "turn": turn,
            # legacy field names kept so archived runs/ stay comparable
            "prompt_text": user_msg,
            "prompt_chars": len(user_msg),
            "prompt_tokens_est": row["prompt_tokens_est"],
            "latency_s": latency,
            "queried_pairs": (queried if probe in ("preservation",
                                                   "belief_pre",
                                                   "belief_post")
                              else None),
            "raw_response": raw,
            "provider_usage": usage,
            "parsed": result["parsed"],
            "scored": result["scored"],
            "metrics": row,
            "metrics_cumulative": cum,
        }
        artifact["metrics_by_phase"].append({**row, "cumulative": cum})
        print(phase_line(idx, row, cum))

    if two_turn and args.reelicit:
        sc_pres = belief_self_consistency(
            record, artifact["probes"]["belief_pre"]["scored"],
            artifact["probes"]["belief_post"]["scored"])
        artifact["self_consistency_preservation"] = sc_pres
        print(f"  self-consistency preservation: status={sc_pres['status']} "
              f"acc={sc_pres.get('accuracy')}")

    artifact["conversation"] = (messages if args.turn_mode != "single"
                                else [])
    artifact["metrics_final"] = cumulative(rows)
    artifact["metrics_final"]["per_phase_score"] = {
        r["probe"]: r["score"] for r in rows}
    artifact["metrics_final"]["per_phase_status"] = {
        r["probe"]: r["status"] for r in rows}
    return artifact


def _episode_to_json(ep):
    return asdict(ep)


def run_pilot_active(sc, deterministic, args):
    """Active-exploration pilot: the model explores M0 then M1 itself and
    answers the 4 probes on a fork of its own transcript. The loop lives in
    explore_agent.py; this only wires it to a provider and writes the
    artifact."""
    inst = make_pair(sc["seed"], sc["condition"],
                     deterministic=deterministic, matched=True)
    record = json.loads(json.dumps(pair_to_json(inst)))
    queried = queried_pairs_for(record, sc)
    cfg = explore_agent.ExploreConfig(
        max_episodes_m0=args.m0_episodes, max_episodes_m1=args.m1_episodes,
        max_steps_per_episode=args.max_steps_per_episode,
        announce_change=args.announce_change,
        max_context_tokens_est=args.explore_context_budget,
        seed=sc["seed"])

    last_usage = {}

    def act_fn(system, messages):
        nonlocal last_usage  # so the caller can read usage after the call, since only (text, reasoning) is returned
        reasoning = ""
        if args.provider == "anthropic":
            text, reasoning, usage = with_retry(
                call_anthropic_chat, args.model, system, messages,
                args.max_tokens, args.thinking_budget)
        elif args.provider == "azure":
            text, usage = with_retry(call_azure_chat, args.model, system,
                                     messages, args.max_tokens,
                                     args.azure_endpoint, args.api_version)
        elif args.provider == "openai":
            text, usage = with_retry(call_openai_chat, args.model, system,
                                     messages, args.max_tokens,
                                     args.base_url)
        else:
            raise AssertionError("dry-run must not call act_fn")
        last_usage = usage
        return text, reasoning

    if args.provider == "dry-run":
        # no API calls: a scripted policy stands in for the model's actions
        result = explore_agent.run_explore_instance(
            inst, cfg, node_policy_fn=lambda mdp: explore_agent.dry_run_policy(
                mdp, inst.labels))
    else:
        result = explore_agent.run_explore_instance(inst, cfg, act_fn=act_fn)

    metrics = explore_metrics.compute_explore_metrics(
        inst, result["m0_episodes"], result["m1_episodes"])
    head = git_head()
    artifact = {
        "pilot": "deterministic" if deterministic else "stochastic",
        "created_utc": datetime.datetime.now(
            datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "env": {"schema_version": SCHEMA_VERSION,
                "frozen_sha": FROZEN_SHA,
                "git_head": head,
                "pinned_to_freeze": head == FROZEN_SHA},
        "instance": {"graph_seed": sc["seed"], "condition": sc["condition"],
                     "deterministic": deterministic, "matched": True,
                     "seeds": record["seeds"]},
        "model": {"provider": args.provider, "model": args.model,
                  "temperature": 0, "max_tokens": args.max_tokens},
        "explore": {
            "config": asdict(cfg),
            "transcript": result["messages"],
            "m0_episodes": [_episode_to_json(e)
                            for e in result["m0_episodes"]],
            "m1_episodes": [_episode_to_json(e)
                            for e in result["m1_episodes"]],
            "metrics": metrics,
        },
        "probes": {},
    }

    system_prompt = explore_agent.build_system_prompt(record["goal"])
    for probe in ALL_PROBES:
        ask = ASKS_ACTIVE[probe]
        if probe == "preservation":
            listed = "\n".join(f'- node {q["node"]}, action {q["action"]}'
                               for q in queried)
            ask = ask.format(queried=listed)
        elif probe == "adaptation":
            ask = ask.format(start=record["start"], goal=record["goal"])
        # each probe appends to a copy of the exploration transcript, not a fresh one
        forked_messages = list(result["messages"]) + [
            {"role": "user", "content": ask}]

        if args.provider == "dry-run":
            raw, reasoning, usage = dry_run_answer(record, probe, queried), "", {}
        else:
            raw, reasoning = act_fn(system_prompt, forked_messages)
            usage = last_usage

        probe_result = run_probe(record, probe, raw,
                                 queried_pairs=(queried
                                                if probe == "preservation"
                                                else None))
        artifact["probes"][probe] = {
            "prompt_chars": len(ask),
            "prompt_tokens_est": len(ask) // 4,
            "queried_pairs": queried if probe == "preservation" else None,
            "raw_response": raw,
            "reasoning": reasoning,
            "provider_usage": usage,
            "parsed": probe_result["parsed"],
            "scored": probe_result["scored"],
        }
    return artifact


def main():
    ap = argparse.ArgumentParser()
    # what is asked
    ap.add_argument("--scenario", default="seed7_silent_break")
    ap.add_argument("--list-scenarios", action="store_true")
    ap.add_argument("--tag", default=None,
                    help="run label; names the output subdirectory and is "
                         "recorded in the artifact (default: scenario name)")
    ap.add_argument("--condition", default=None, choices=list(CONDITIONS))
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--rendering", default=None,
                    choices=list(PROMPT_RENDERINGS))
    ap.add_argument("--budget", type=int, default=None)
    ap.add_argument("--k", type=int, default=None)
    ap.add_argument("--evidence-seed", type=int, default=None)
    ap.add_argument("--probes", nargs="+", default=None,
                    choices=list(ALL_PROBES))
    ap.add_argument("--turn-mode", default="single",
                    choices=["single", "multi", "two_turn"],
                    help="single: independent call per probe (frozen "
                         "baseline); multi: one conversation, both periods "
                         "sent once (legacy); two_turn (v2.2): turn 1 shows "
                         "period A only and asks route_pre + belief_pre, "
                         "turn 2 reveals period B and asks the four probes")
    ap.add_argument("--reelicit", action="store_true",
                    help="two_turn only: re-elicit beliefs on the same "
                         "pairs after period B and score self-consistency "
                         "preservation")
    ap.add_argument("--mode", default="both", choices=["both", "det", "sto"])
    # who answers
    ap.add_argument("--provider", default="dry-run",
                    choices=["dry-run", "anthropic", "openai", "azure"])
    ap.add_argument("--model", default="dry-run")
    ap.add_argument("--base-url", default="https://api.openai.com/v1")
    ap.add_argument("--azure-endpoint",
                    default="https://YOUR-RESOURCE.openai.azure.com")
    ap.add_argument("--api-version", default="2024-06-01")
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--timeout", type=int, default=120,
                    help="per-request seconds; local endpoints need ~900")
    ap.add_argument("--out", default="pilot_artifacts")
    ap.add_argument("--pilot-type", default="passive",
                    choices=["passive", "active"],
                    help="passive (default): hand the model a "
                         "pre-collected evidence log, as before. active: "
                         "let the model explore the MDP itself, picking "
                         "its own actions (see explore_agent.py).")
    ap.add_argument("--m0-episodes", type=int, default=4,
                    help="active pilot-type only")
    ap.add_argument("--m1-episodes", type=int, default=4,
                    help="active pilot-type only")
    ap.add_argument("--max-steps-per-episode", type=int, default=25,
                    help="active pilot-type only")
    ap.add_argument("--announce-change", action="store_true",
                    help="active pilot-type only: explicitly tell the "
                         "model reliabilities may have changed at the "
                         "M0->M1 reset (ablation; default is silent, "
                         "requiring the model to infer the change from "
                         "observation alone)")
    ap.add_argument("--explore-context-budget", type=int, default=12000,
                    help="active pilot-type only")
    ap.add_argument("--thinking-budget", type=int, default=0,
                    help="active pilot-type only, Anthropic provider "
                         "only: greater than 0 enables Claude Extended "
                         "Thinking with this token budget (requires "
                         "--max-tokens greater than this value)")
    args = ap.parse_args()

    if args.list_scenarios:
        for name in sorted(SCENARIOS):
            sc = dict(SCENARIO_DEFAULTS)
            sc.update(SCENARIOS[name])
            print(f"{name:<32} condition={sc['condition']:<13} "
                  f"seed={sc['seed']} rendering={sc['rendering']} "
                  f"variants={'/'.join(sc['variants'])} "
                  f"probes={','.join(sc['probes'])}")
        return

    sc = resolve_scenario(args)
    if args.tag is None:
        args.tag = sc["name"]
    outdir = os.path.join(args.out, args.tag)
    os.makedirs(outdir, exist_ok=True)

    wanted = {"both": ("det", "sto"), "det": ("det",),
              "sto": ("sto",)}[args.mode]
    todo = [v for v in wanted if v in sc["variants"]]
    if not todo:
        raise SystemExit(f"scenario {sc['name']} is only defined for "
                         f"{'/'.join(sc['variants'])}; --mode {args.mode} "
                         f"leaves nothing to run")
    for det in [v == "det" for v in todo]:
        if args.pilot_type == "active":
            art = run_pilot_active(sc, det, args)
        else:
            art = run_pilot(sc, det, args)
        parts = ["pilot_deterministic" if det else "pilot_stochastic"]
        if args.pilot_type == "active":
            parts.append("active")
        elif args.turn_mode != "single":
            parts.append(args.turn_mode)
        if args.provider == "dry-run":
            parts.append("dryrun")
        path = os.path.join(outdir, "_".join(parts) + ".json")
        with open(path, "w") as fh:
            json.dump(art, fh, indent=2)
        mf = art.get("metrics_final")
        if mf is None:
            em = art.get("explore", {}).get("metrics", {})
            print(f"{path}: pinned={art['env']['pinned_to_freeze']} "
                  f"opt_rate m0={em.get('optimal_action_rate_m0'):.2f} "
                  f"m1={em.get('optimal_action_rate_m1'):.2f} "
                  f"lag={em.get('adaptation_lag_steps')}\n")
        else:
            print(f"{path}: pinned={art['env']['pinned_to_freeze']} "
                  f"final={mf['per_phase_score']} "
                  f"mean={mf['score_mean']}\n")


if __name__ == "__main__":
    main()

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
  * `--turn-mode` single (four independent calls, the frozen behaviour) or
                  multi (four turns of one conversation, evidence sent once)
  * `--timeout`   per-request seconds; raise it for slow local endpoints

For each pilot, the probes are run end to end:

  prompt_view (prompt-safe payload) -> prompt text -> model ->
  raw response -> frozen parser -> scoring -> artifact JSON

Each artifact retains the agreed list: prompt-safe payload, raw model
response, parser and execution statuses, route/regret outputs, seeds/model
settings, and realized event/token counts, plus the env freeze SHA the run
is pinned to. Multi-turn runs additionally record per-phase metrics and the
full conversation.

Usage (from the repo root):

  python3 run_pilot.py                                   # dry-run, no API
  ANTHROPIC_API_KEY=... python3 run_pilot.py \
      --provider anthropic --model claude-sonnet-4-6
  OPENAI_API_KEY=... python3 run_pilot.py \
      --provider openai --model gpt-4o --base-url https://api.openai.com/v1
  AZURE_OPENAI_API_KEY=... python3 run_pilot.py \
      --provider azure --model YOUR-DEPLOYMENT \
      --azure-endpoint https://YOUR-RESOURCE.openai.azure.com

  # local LM Studio (OpenAI-compatible, slow: needs the long timeout)
  OPENAI_API_KEY=lm-studio python3 run_pilot.py \
      --provider openai --model gemma-4-e4b \
      --base-url http://localhost:1234/v1 --timeout 900 \
      --tag 2026-08-23_gemma4e4b_lmstudio

  # multi-turn condition, and its matched single-turn A/B baseline
  python3 run_pilot.py --turn-mode multi --tag multiturn_probe
  python3 run_pilot.py --turn-mode single --tag multiturn_probe

  # a different environment condition, no new file needed
  python3 run_pilot.py --scenario seed7_hard_removal --tag hardremoval_v1
  python3 run_pilot.py --condition irrelevant --seed 11 --tag adhoc_seed11

  python3 run_pilot.py --list-scenarios

Outputs: <out>/<tag>/pilot_deterministic.json, pilot_stochastic.json
(with _multi / _dryrun suffixes as applicable). Default out is
pilot_artifacts/. stdlib only.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import random
import subprocess
import time
import urllib.request

from ecpm_parser import run_probe
from resource_mdp import (CONDITIONS, PROMPT_RENDERINGS, SCHEMA_VERSION,
                          make_pair, pair_to_json, paired_evidence,
                          prompt_view)

FROZEN_SHA = "5318c3e113438c563c5676d58252d84fda22aa49"
ALL_PROBES = ("detection", "localization", "preservation", "adaptation")

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

ASKS = {
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


def context_block(view):
    """The shared evidence header: sent once in multi-turn mode, prepended
    to every ask in single-turn mode. Identical text in both."""
    menus = {p: "; ".join(f"{node}: {', '.join(m)}" for node, m in
                          sorted(view[f"legal_actions_{p}"].items()))
             for p in ("pre", "post")}
    return INTRO.format(nodes=", ".join(view["nodes"]),
                        start=view["start"], goal=view["goal"],
                        menu_pre=menus["pre"], menu_post=menus["post"],
                        ev_pre=view["evidence"]["pre"],
                        ev_post=view["evidence"]["post"])


def ask_block(view, probe, queried):
    """The probe question alone (no evidence)."""
    ask = ASKS[probe]
    if probe == "preservation":
        listed = "\n".join(f'- node {q["node"]}, action {q["action"]}'
                           for q in queried)
        ask = ask.format(queried=listed)
    elif probe == "adaptation":
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
    elif probe == "adaptation":
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
    if row["probe"] == "adaptation":
        extra = (f" regret={d.get('regret')} cost={d.get('expected_cost')}"
                 f"/{d.get('optimal_cost')}")
    elif row["probe"] == "preservation":
        extra = f" acc={d.get('accuracy')} ({d.get('n_queried')} pairs)"
    return (f"  phase {idx} {row['probe']:<13} status={str(row['status']):<20}"
            f" score={row['score']:.2f}{extra}"
            f" | cum mean={cum['score_mean']} tok~{cum['prompt_tokens_est']}"
            f" {cum['latency_s']}s")


# ---------------------------------------------------------------- providers
#
# All three take a full `messages` list, so the same call works for a
# one-shot probe and for a later turn that carries history.


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
    o = record["oracle"]["post"]
    steps = [{"node": n, "action": a}
             for n, a in zip(o["optimal_route"], o["optimal_actions"])]
    return json.dumps({"route": steps})


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

    messages, rows = [], []
    print(f"[{artifact['pilot']}] tag={args.tag} scenario={sc['name']} "
          f"turn_mode={args.turn_mode} provider={args.provider}")

    for idx, probe in enumerate(probes, start=1):
        ask = ask_block(view, probe, queried)
        if args.turn_mode == "multi":
            # evidence only in turn 1; later turns rely on the history
            user_msg = (context + "\n" + ask) if idx == 1 else ask
        else:
            messages = []                  # no history: one-shot per probe
            user_msg = context + "\n" + ask
        messages = messages + [{"role": "user", "content": user_msg}]

        t0 = time.time()
        raw, usage = dispatch(args, record, probe, queried, messages)
        latency = round(time.time() - t0, 3)
        messages = messages + [{"role": "assistant", "content": raw}]

        result = run_probe(record, probe, raw,
                           queried_pairs=(queried if probe == "preservation"
                                          else None))
        row = phase_metrics(probe, result["scored"])
        row.update({"phase": idx,
                    "sent_chars": len(user_msg),
                    "context_chars": sum(len(m["content"]) for m in messages),
                    "prompt_tokens_est":
                        sum(len(m["content"]) for m in messages[:-1]) // 4,
                    "latency_s": latency})
        rows.append(row)
        cum = cumulative(rows)

        artifact["probes"][probe] = {
            "phase": idx,
            # legacy field names kept so archived runs/ stay comparable
            "prompt_text": user_msg,
            "prompt_chars": len(user_msg),
            "prompt_tokens_est": row["prompt_tokens_est"],
            "latency_s": latency,
            "queried_pairs": queried if probe == "preservation" else None,
            "raw_response": raw,
            "provider_usage": usage,
            "parsed": result["parsed"],
            "scored": result["scored"],
            "metrics": row,
            "metrics_cumulative": cum,
        }
        artifact["metrics_by_phase"].append({**row, "cumulative": cum})
        print(phase_line(idx, row, cum))

    artifact["conversation"] = messages if args.turn_mode == "multi" else []
    artifact["metrics_final"] = cumulative(rows)
    artifact["metrics_final"]["per_phase_score"] = {
        r["probe"]: r["score"] for r in rows}
    artifact["metrics_final"]["per_phase_status"] = {
        r["probe"]: r["status"] for r in rows}
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
                    choices=["single", "multi"],
                    help="single: independent call per probe (frozen "
                         "baseline); multi: one conversation, evidence "
                         "sent once")
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
        art = run_pilot(sc, det, args)
        parts = ["pilot_deterministic" if det else "pilot_stochastic"]
        if args.turn_mode == "multi":
            parts.append("multi")
        if args.provider == "dry-run":
            parts.append("dryrun")
        path = os.path.join(outdir, "_".join(parts) + ".json")
        with open(path, "w") as fh:
            json.dump(art, fh, indent=2)
        print(f"{path}: pinned={art['env']['pinned_to_freeze']} "
              f"final={art['metrics_final']['per_phase_score']} "
              f"mean={art['metrics_final']['score_mean']}\n")


if __name__ == "__main__":
    main()

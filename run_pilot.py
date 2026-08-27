#!/usr/bin/env python3
"""ECPM Phase-2 pilot harness (runs INSIDE the repo, pinned to the freeze).

Two pilots: the matched seed-7 pair (deterministic + stochastic,
silent_break). For each pilot, all four probes are run end to end:

  prompt_view (prompt-safe payload) -> prompt text -> model ->
  raw response -> frozen parser -> scoring -> artifact JSON

Each artifact retains exactly the agreed list: prompt-safe payload,
raw model response, parser and execution statuses, route/regret outputs,
seeds/model settings, and realized event/token counts, plus the env
freeze SHA the run is pinned to.

Usage (from the repo root, branch v2.1-prefreeze):

  python3 run_pilot.py                                   # dry-run, no API
  ANTHROPIC_API_KEY=... python3 run_pilot.py \
      --provider anthropic --model claude-sonnet-4-6
  OPENAI_API_KEY=... python3 run_pilot.py \
      --provider openai --model gpt-4o --base-url https://api.openai.com/v1
  AZURE_OPENAI_API_KEY=... python3 run_pilot.py \
      --provider azure --model YOUR-DEPLOYMENT \
      --azure-endpoint https://YOUR-RESOURCE.openai.azure.com

Outputs: pilot_deterministic.json / pilot_stochastic.json (or *_dryrun.json)
in --out (default: pilot_artifacts/). stdlib only.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import random
import subprocess
import urllib.request

from ecpm_parser import run_probe
from resource_mdp import (SCHEMA_VERSION, make_pair, pair_to_json,
                          paired_evidence, prompt_view)

FROZEN_SHA = "5318c3e113438c563c5676d58252d84fda22aa49"
GRAPH_SEED = 7
PROBES = ("detection", "localization", "preservation", "adaptation")

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


def build_record(deterministic):
    inst = make_pair(GRAPH_SEED, "silent_break",
                     deterministic=deterministic, matched=True)
    ev = paired_evidence(inst, k=5, evidence_seed=0)
    return json.loads(json.dumps(pair_to_json(inst, ev)))


def queried_pairs_for(record, n_other=3):
    """Deterministic probe set: the target pair + n_other unchanged pairs,
    order shuffled by a fixed seed."""
    ch = record["change"]
    target = (ch["edge"]["from"], ch["action"])
    everyone = sorted((node, a) for node, menu in
                      record["legal_actions_pre"].items() for a in menu)
    others = [p for p in everyone if p != target]
    rng = random.Random(f"pilot|{GRAPH_SEED}|preservation")
    picked = rng.sample(others, n_other) + [target]
    rng.shuffle(picked)
    return [{"node": n, "action": a} for n, a in picked]


def build_prompt(record, view, probe, queried):
    menus = {p: "; ".join(f"{node}: {', '.join(m)}" for node, m in
                          sorted(view[f"legal_actions_{p}"].items()))
             for p in ("pre", "post")}
    intro = INTRO.format(nodes=", ".join(view["nodes"]),
                         start=view["start"], goal=view["goal"],
                         menu_pre=menus["pre"], menu_post=menus["post"],
                         ev_pre=view["evidence"]["pre"],
                         ev_post=view["evidence"]["post"])
    ask = ASKS[probe]
    if probe == "preservation":
        listed = "\n".join(f'- node {q["node"]}, action {q["action"]}'
                           for q in queried)
        ask = ask.format(queried=listed)
    elif probe == "adaptation":
        ask = ask.format(start=view["start"], goal=view["goal"])
    return intro + "\n" + ask + "\n"


# ---------------------------------------------------------------- providers


def call_anthropic(model, prompt, max_tokens):
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps({"model": model, "max_tokens": max_tokens,
                         "temperature": 0,
                         "messages": [{"role": "user",
                                       "content": prompt}]}).encode(),
        headers={"content-type": "application/json",
                 "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                 "anthropic-version": "2023-06-01"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    text = "".join(b.get("text", "") for b in data.get("content", []))
    return text, data.get("usage", {})


def call_azure(deployment, prompt, max_tokens, endpoint, api_version):
    url = (endpoint.rstrip("/") + "/openai/deployments/" + deployment
           + "/chat/completions?api-version=" + api_version)
    req = urllib.request.Request(
        url,
        data=json.dumps({"max_tokens": max_tokens, "temperature": 0,
                         "messages": [{"role": "user",
                                       "content": prompt}]}).encode(),
        headers={"content-type": "application/json",
                 "api-key": os.environ["AZURE_OPENAI_API_KEY"]})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    text = data["choices"][0]["message"]["content"]
    return text, data.get("usage", {})


def call_openai(model, prompt, max_tokens, base_url):
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps({"model": model, "max_tokens": max_tokens,
                         "temperature": 0,
                         "messages": [{"role": "user",
                                       "content": prompt}]}).encode(),
        headers={"content-type": "application/json",
                 "authorization":
                     f"Bearer {os.environ['OPENAI_API_KEY']}"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    text = data["choices"][0]["message"]["content"]
    return text, data.get("usage", {})


def dry_run_answer(record, probe, queried):
    """Oracle-derived canned replies (wrapped in prose/fences to exercise
    the extractor). Pipeline demo only; provider is labeled 'dry-run'."""
    ch = record["change"]
    if probe == "detection":
        return 'Looking at period B: ```json\n{"changed": true}\n```'
    if probe == "localization":
        obj = {"node": ch["edge"]["from"], "action": ch["action"]}
        return "My answer: " + json.dumps(obj)
    if probe == "preservation":
        target = (ch["edge"]["from"], ch["action"])
        pairs = [{"node": q["node"], "action": q["action"],
                  "changed": (q["node"], q["action"]) == target}
                 for q in queried]
        return json.dumps({"pairs": pairs})
    o = record["oracle"]["post"]
    steps = [{"node": n, "action": a}
             for n, a in zip(o["optimal_route"], o["optimal_actions"])]
    return json.dumps({"route": steps})


# ------------------------------------------------------------------- pilot


def run_pilot(deterministic, args):
    record = build_record(deterministic)
    view = prompt_view(record, rendering=args.rendering,
                       periods=("pre", "post"),
                       budget_per_pair=args.budget)
    queried = queried_pairs_for(record)
    head = git_head()
    artifact = {
        "pilot": "deterministic" if deterministic else "stochastic",
        "created_utc": datetime.datetime.now(
            datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "env": {"schema_version": SCHEMA_VERSION,
                "frozen_sha": FROZEN_SHA,
                "git_head": head,
                "pinned_to_freeze": head == FROZEN_SHA},
        "instance": {"graph_seed": GRAPH_SEED, "condition": "silent_break",
                     "deterministic": deterministic, "matched": True,
                     "k_per_pair": record["evidence"]["k_per_pair"],
                     "evidence_seed": record["evidence"]["evidence_seed"],
                     "seeds": record["seeds"]},
        "model": {"provider": args.provider, "model": args.model,
                  "temperature": 0, "max_tokens": args.max_tokens,
                  "rendering": args.rendering,
                  "budget_per_pair": args.budget},
        "prompt_safe_payload": view,
        "probes": {},
    }
    for probe in PROBES:
        prompt = build_prompt(record, view, probe, queried)
        if args.provider == "anthropic":
            raw, usage = call_anthropic(args.model, prompt, args.max_tokens)
        elif args.provider == "azure":
            raw, usage = call_azure(args.model, prompt, args.max_tokens,
                                    args.azure_endpoint, args.api_version)
        elif args.provider == "openai":
            raw, usage = call_openai(args.model, prompt, args.max_tokens,
                                     args.base_url)
        else:
            raw, usage = dry_run_answer(record, probe, queried), {}
        result = run_probe(record, probe, raw,
                           queried_pairs=(queried if probe == "preservation"
                                          else None))
        artifact["probes"][probe] = {
            "prompt_chars": len(prompt),
            "prompt_tokens_est": len(prompt) // 4,
            "queried_pairs": queried if probe == "preservation" else None,
            "prompt_text": prompt,
            "raw_response": raw,
            "provider_usage": usage,
            "parsed": result["parsed"],
            "scored": result["scored"],
        }
    return artifact


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="dry-run",
                    choices=["dry-run", "anthropic", "openai", "azure"])
    ap.add_argument("--azure-endpoint",
                    default="https://YOUR-RESOURCE.openai.azure.com")
    ap.add_argument("--api-version", default="2024-06-01")
    ap.add_argument("--model", default="dry-run")
    ap.add_argument("--base-url", default="https://api.openai.com/v1")
    ap.add_argument("--rendering", default="F2_shuffled")
    ap.add_argument("--budget", type=int, default=5)
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--mode", default="both",
                    choices=["both", "det", "sto"])
    ap.add_argument("--out", default="pilot_artifacts")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    todo = {"both": (True, False), "det": (True,), "sto": (False,)}[args.mode]
    for det in todo:
        art = run_pilot(det, args)
        suffix = "_dryrun" if args.provider == "dry-run" else ""
        name = ("pilot_deterministic" if det else "pilot_stochastic")
        path = os.path.join(args.out, f"{name}{suffix}.json")
        with open(path, "w") as fh:
            json.dump(art, fh, indent=2)
        summary = {p: art["probes"][p]["scored"].get("status",
                   art["probes"][p]["scored"].get("correct"))
                   for p in PROBES}
        print(f"{path}: pinned={art['env']['pinned_to_freeze']} "
              f"statuses={summary}")


if __name__ == "__main__":
    main()

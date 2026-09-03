#!/usr/bin/env python3
"""ECPM Phase-2 MULTI-TURN pilot harness (outside the frozen tree).

Difference from `run_pilot.py`: the four probes are asked as four turns of
ONE conversation instead of four independent single-turn calls. The
evidence block is sent once, in turn 1; turns 2-4 carry only the ask, and
the model's own earlier answers stay in the history. Metrics are computed
and printed AFTER EACH PHASE, so a phase-by-phase curve (and any
contamination from the model's own earlier answers) is visible.

Phases run in the fixed order: detection -> localization -> preservation
-> adaptation.

Everything else is unchanged and reused from `run_pilot.py`: instance
construction, `prompt_view` payload, queried-pair selection, prompt
wording, and the frozen parser/scorer (`ecpm_parser.run_probe`).

Usage (from the repo root):

  python3 run_pilot_multiturn.py                          # dry-run, no API
  ANTHROPIC_API_KEY=... python3 run_pilot_multiturn.py \
      --provider anthropic --model claude-sonnet-4-6
  OPENAI_API_KEY=... python3 run_pilot_multiturn.py \
      --provider openai --model gpt-4o
  AZURE_OPENAI_API_KEY=... python3 run_pilot_multiturn.py \
      --provider azure --model YOUR-DEPLOYMENT \
      --azure-endpoint https://YOUR-RESOURCE.openai.azure.com

  # A/B against the existing one-shot-per-probe condition, same code path:
  python3 run_pilot_multiturn.py --turn-mode single

Outputs: pilot_multiturn_deterministic.json /
pilot_multiturn_stochastic.json (or *_dryrun.json) in --out
(default: pilot_artifacts/). stdlib only.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import time
import urllib.request

from ecpm_parser import run_probe
from resource_mdp import SCHEMA_VERSION, prompt_view
from run_pilot import (ASKS, FROZEN_SHA, GRAPH_SEED, INTRO, PROBES,
                       build_record, dry_run_answer, git_head,
                       queried_pairs_for)


# ------------------------------------------------------------- prompt parts


def context_block(view):
    """The shared evidence header: sent once in multi-turn, prepended to
    every ask in single-turn. Identical text in both modes."""
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

    `score` is the single primary 0..1 number for that phase, so phases
    can be plotted on one axis; probe-specific detail is kept alongside.
    """
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
        "score_mean": round(sum(r["score"] for r in rows) / n, 4) if n else None,
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
    return (f"  phase {idx} {row['probe']:<13} status={row['status']:<20}"
            f" score={row['score']:.2f}{extra}"
            f" | cum mean={cum['score_mean']} tok~{cum['prompt_tokens_est']}"
            f" {cum['latency_s']}s")


# ---------------------------------------------------------------- providers
# All three take a full `messages` list so the same call works for turn 1
# and for the later turns that carry history.


def call_anthropic(model, messages, max_tokens):
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps({"model": model, "max_tokens": max_tokens,
                         "temperature": 0,
                         "messages": messages}).encode(),
        headers={"content-type": "application/json",
                 "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                 "anthropic-version": "2023-06-01"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    text = "".join(b.get("text", "") for b in data.get("content", []))
    return text, data.get("usage", {})


def call_azure(deployment, messages, max_tokens, endpoint, api_version):
    url = (endpoint.rstrip("/") + "/openai/deployments/" + deployment
           + "/chat/completions?api-version=" + api_version)
    req = urllib.request.Request(
        url,
        data=json.dumps({"max_tokens": max_tokens, "temperature": 0,
                         "messages": messages}).encode(),
        headers={"content-type": "application/json",
                 "api-key": os.environ["AZURE_OPENAI_API_KEY"]})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"], data.get("usage", {})


def call_openai(model, messages, max_tokens, base_url):
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps({"model": model, "max_tokens": max_tokens,
                         "temperature": 0,
                         "messages": messages}).encode(),
        headers={"content-type": "application/json",
                 "authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"], data.get("usage", {})


def dispatch(args, record, probe, queried, messages):
    if args.provider == "anthropic":
        return call_anthropic(args.model, messages, args.max_tokens)
    if args.provider == "azure":
        return call_azure(args.model, messages, args.max_tokens,
                          args.azure_endpoint, args.api_version)
    if args.provider == "openai":
        return call_openai(args.model, messages, args.max_tokens,
                           args.base_url)
    return dry_run_answer(record, probe, queried), {}


# ------------------------------------------------------------------- pilot


def run_pilot(deterministic, args):
    record = build_record(deterministic)
    view = prompt_view(record, rendering=args.rendering,
                       periods=("pre", "post"), budget_per_pair=args.budget)
    queried = queried_pairs_for(record)
    context = context_block(view)
    head = git_head()

    artifact = {
        "pilot": "deterministic" if deterministic else "stochastic",
        "turn_mode": args.turn_mode,
        "phase_order": list(PROBES),
        "created_utc": datetime.datetime.now(
            datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "env": {"schema_version": SCHEMA_VERSION, "frozen_sha": FROZEN_SHA,
                "git_head": head, "pinned_to_freeze": head == FROZEN_SHA},
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
        "metrics_by_phase": [],
        "conversation": [],
    }

    messages, rows = [], []
    print(f"[{artifact['pilot']}] turn_mode={args.turn_mode} "
          f"provider={args.provider}")

    for idx, probe in enumerate(PROBES, start=1):
        ask = ask_block(view, probe, queried)
        if args.turn_mode == "multi":
            # evidence only in turn 1; later turns rely on the history
            user_msg = (context + "\n" + ask) if idx == 1 else ask
        else:
            messages = []                      # no history: one-shot per probe
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
            "sent_text": user_msg,
            "sent_chars": len(user_msg),
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

    artifact["conversation"] = messages
    artifact["metrics_final"] = cumulative(rows)
    artifact["metrics_final"]["per_phase_score"] = {
        r["probe"]: r["score"] for r in rows}
    artifact["metrics_final"]["per_phase_status"] = {
        r["probe"]: r["status"] for r in rows}
    return artifact


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="dry-run",
                    choices=["dry-run", "anthropic", "openai", "azure"])
    ap.add_argument("--turn-mode", default="multi", choices=["multi", "single"],
                    help="multi: one conversation, evidence sent once; "
                         "single: independent call per probe (baseline)")
    ap.add_argument("--azure-endpoint",
                    default="https://YOUR-RESOURCE.openai.azure.com")
    ap.add_argument("--api-version", default="2024-06-01")
    ap.add_argument("--model", default="dry-run")
    ap.add_argument("--base-url", default="https://api.openai.com/v1")
    ap.add_argument("--rendering", default="F2_shuffled")
    ap.add_argument("--budget", type=int, default=5)
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--mode", default="both", choices=["both", "det", "sto"])
    ap.add_argument("--out", default="pilot_artifacts")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    todo = {"both": (True, False), "det": (True,), "sto": (False,)}[args.mode]
    for det in todo:
        art = run_pilot(det, args)
        suffix = "_dryrun" if args.provider == "dry-run" else ""
        tag = "" if args.turn_mode == "multi" else "_single"
        name = "pilot_multiturn_" + ("deterministic" if det else "stochastic")
        path = os.path.join(args.out, f"{name}{tag}{suffix}.json")
        with open(path, "w") as fh:
            json.dump(art, fh, indent=2)
        print(f"{path}: pinned={art['env']['pinned_to_freeze']} "
              f"final={art['metrics_final']['per_phase_score']} "
              f"mean={art['metrics_final']['score_mean']}\n")


if __name__ == "__main__":
    main()

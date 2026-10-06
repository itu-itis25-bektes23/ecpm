#!/usr/bin/env python3
"""Resumable batch runner over the two-turn stochastic matrix.

Cells:
  K=10  no_change irrelevant silent_break hard_removal redirect degradation
  K=5   silent_break degradation no_change
  K=20  silent_break degradation no_change

Every cell runs stochastic mode in the paper's two-turn protocol,
--protocol icl_two_response_v1 with --period-b-every-pair (the Period B
answer states a belief about every listed pair), budget equal to K, over the seed run set in --seeds-file (run_set.sto, the
intersection across conditions, so a seed gives the same graph in every
condition). Each instance shells out to run_pilot.py with --telemetry and
writes a .done marker on success, so a re-run skips finished work.

As in the paper, each instance is answered at the explained_logs evidence
level only (--icl-levels explained_logs), once (--icl-repeats 1), or N
times for silent_break when the profile sets "samples_silent_break": N
(gpt56_sol: three answers per silent-break instance). Every answer is two
calls (Turn A, Turn B). --queried-target-half puts the target among the
five queried pairs on half of the seeds (seed-only coin), as the paper
describes; otherwise all five are unchanged links.

Real (non --dry-run) runs require a clean committed git worktree:
run_pilot refuses to start otherwise, so run_matrix checks up front that
HEAD exists and `git status --porcelain` is empty, and exits with a clear
message if not. --plan and --dry-run skip the check.

Model profiles come from experiments/models.json (--model NAME).

Usage:
  python3 experiments/run_matrix.py --model gpt4o --seeds-file \\
      runs/seed_eligibility.json --out pilot_artifacts/matrix_gpt4o
  python3 experiments/run_matrix.py --model gpt4o --seeds-file \\
      runs/seed_eligibility.json --plan --plan-csv matrix.csv
  ... --dry-run --limit-seeds 2      no API calls, provider dry-run

Stops after 5 consecutive failures (usually auth, quota or a bad model
id). --max-cost stops before the next instance once the summed telemetry
cost reaches the cap; it can only be enforced when the profile has prices.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUN_PILOT = os.path.join(ROOT, "run_pilot.py")
MODELS = os.path.join(HERE, "models.json")

K10_CONDITIONS = ("no_change", "irrelevant", "silent_break", "hard_removal",
                  "redirect", "degradation")
K_SWEEP_CONDITIONS = ("silent_break", "degradation", "no_change")
MAX_CONSECUTIVE_FAILURES = 5
CONFIRMATORY_SEEDS = "runs/seed_eligibility_31_130.json"


def matrix_cells():
    cells = [(c, 10) for c in K10_CONDITIONS]
    for k in (5, 20):
        cells += [(c, k) for c in K_SWEEP_CONDITIONS]
    return cells


ICL_LEVELS = ("explained_logs",)
ICL_CALLS_PER_RUN = 2


def icl_repeats(profile, condition):
    """Answers per instance: one, or the profile's samples_silent_break
    for silent_break (gpt56_sol: 3)."""
    if condition == "silent_break":
        return int((profile or {}).get("samples_silent_break", 1) or 1)
    return 1


def calls_per_instance(condition, profile=None):
    """icl_two_response_v1: each run is exactly two calls (Turn A, Turn B),
    one run per repeat at the explained_logs level."""
    return icl_repeats(profile, condition) * len(ICL_LEVELS) * \
        ICL_CALLS_PER_RUN


def load_profile(name, path=MODELS):
    with open(path) as fh:
        models = json.load(fh)
    if name not in models or name.startswith("_"):
        known = ", ".join(k for k in models if not k.startswith("_"))
        raise SystemExit(f"unknown model profile {name!r}; known: {known}")
    return models[name]


def load_seeds(path, limit=None):
    try:
        with open(path) as fh:
            data = json.load(fh)
        seeds = list(data["run_set"]["sto"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise SystemExit(f"could not run: cannot read run_set.sto from "
                         f"{path}: {type(exc).__name__}: {exc}")
    if not seeds:
        raise SystemExit(f"could not run: {path}: run_set.sto is empty, "
                         f"nothing to run")
    return seeds[:limit] if limit else seeds


def pilot_command(profile, condition, k, seed, outdir, dry_run=False):
    cmd = [sys.executable, "-B", RUN_PILOT,
           "--condition", condition, "--seed", str(seed), "--mode", "sto",
           "--protocol", "icl_two_response_v1", "--period-b-every-pair",
           "--queried-target-half",
           "--k", str(k), "--budget", str(k),
           "--out", outdir, "--tag", "run", "--telemetry",
           "--icl-levels", *ICL_LEVELS,
           "--icl-repeats", str(icl_repeats(profile, condition))]
    if condition == "no_change":
        cmd += ["--probes", "detection", "preservation", "adaptation"]
    priced = (profile.get("in_price") is not None
              and profile.get("out_price") is not None)
    prices = (["--in-price", str(profile["in_price"]),
               "--out-price", str(profile["out_price"])] if priced else [])
    if dry_run:
        # Prices pass through so a dry run with injected usage exercises
        # --max-cost; plain dry runs report no usage and stay unpriced.
        return cmd + ["--provider", "dry-run", "--model", "dry-run"] + prices
    prov = profile["provider"]
    cmd += ["--provider", prov, "--model", profile["model"],
            "--timeout", str(profile.get("timeout", 120))]
    if prov == "azure":
        cmd += ["--azure-endpoint",
                os.environ.get("AZURE_OPENAI_ENDPOINT",
                               "https://YOUR-RESOURCE.openai.azure.com")]
    elif profile.get("base_url"):
        cmd += ["--base-url", profile["base_url"]]
    if prov in ("openai", "deepseek", "moonshot") and profile.get(
            "api_key_env"):
        cmd += ["--api-key-env", profile["api_key_env"]]
    if profile.get("omit_temperature"):
        cmd += ["--omit-temperature"]
    return cmd + prices


def plan_rows(model_name, profile, n_seeds, est_prompt, est_completion):
    priced = (profile.get("in_price") is not None
              and profile.get("out_price") is not None)
    rows = []
    for cond, k in matrix_cells():
        calls = calls_per_instance(cond, profile) * n_seeds
        cost = ""
        if priced:
            cost = round(calls * (est_prompt * profile["in_price"]
                                  + est_completion * profile["out_price"])
                         / 1e6, 4)
        rows.append({"model": model_name, "condition": cond, "K": k,
                     "n_seeds": n_seeds, "calls_estimate": calls,
                     "cost_estimate_usd": cost})
    return rows


def write_plan(rows, seeds_file, path=None):
    buf = io.StringIO()
    buf.write(f"# seeds from {seeds_file} (run_set.sto)\n")
    if os.path.exists(os.path.join(ROOT, CONFIRMATORY_SEEDS)):
        buf.write(f"# confirmatory seed file for seeds 31-130: "
                  f"{CONFIRMATORY_SEEDS}\n")
    else:
        buf.write(f"# confirmatory seed file for seeds 31-130 would be "
                  f"{CONFIRMATORY_SEEDS} (not present yet)\n")
    buf.write("# cost_estimate_usd is blank when the profile price is null\n")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
    text = buf.getvalue()
    if path:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(text)
    print(text, end="")


def artifact_cost(stamp_dir):
    total = 0.0
    for dirpath, _, files in os.walk(stamp_dir):
        for f in files:
            if f.endswith(".json"):
                try:
                    with open(os.path.join(dirpath, f)) as fh:
                        tel = json.load(fh).get("telemetry") or {}
                except (OSError, ValueError):
                    continue
                amt = (tel.get("cost") or {}).get("amount")
                if amt is not None:
                    total += amt
    return total


def git_clean_check(cwd=ROOT, runner=subprocess.run):
    """None when HEAD exists and the worktree is clean, else a message."""
    try:
        head = runner(["git", "rev-parse", "--verify", "HEAD"], cwd=cwd,
                      capture_output=True, text=True)
        status = runner(["git", "status", "--porcelain"], cwd=cwd,
                        capture_output=True, text=True)
    except OSError as exc:
        return f"git is not available ({exc})"
    if head.returncode != 0:
        return "no git HEAD (not a git repository, or no commit yet)"
    if status.returncode != 0:
        return f"git status failed: {status.stderr.strip()}"
    if status.stdout.strip():
        n = len(status.stdout.strip().splitlines())
        return f"worktree has {n} uncommitted or untracked path(s)"
    return None


def run(args, runner=subprocess.run):
    profile = load_profile(args.model, args.models_file)
    seeds = load_seeds(args.seeds_file, args.limit_seeds)
    if args.plan:
        write_plan(plan_rows(args.model, profile, len(seeds),
                             args.est_prompt_tokens,
                             args.est_completion_tokens),
                   args.seeds_file, args.plan_csv)
        return 0
    if not args.dry_run:
        problem = git_clean_check()
        if problem:
            print(f"could not run: real icl_two_response_v1 runs require a "
                  f"clean committed git worktree; {problem}. Commit or "
                  f"stash, or use --dry-run.", file=sys.stderr)
            return 2
    if args.max_cost is not None and profile.get("in_price") is None:
        print(f"warning: profile {args.model} has no price; --max-cost "
              f"cannot be enforced", file=sys.stderr)
    os.makedirs(args.out, exist_ok=True)
    log_path = os.path.join(args.out, "run.log")
    ok = skipped = failed = consecutive = 0
    spent = 0.0
    with open(log_path, "a") as log:
        for cond, k in matrix_cells():
            for seed in seeds:
                stamp = f"{cond}_k{k}_s{seed}"
                stamp_dir = os.path.join(args.out, stamp)
                marker = os.path.join(stamp_dir, ".done")
                if os.path.exists(marker):
                    skipped += 1
                    spent += artifact_cost(stamp_dir)
                    continue
                if args.max_cost is not None and spent >= args.max_cost:
                    print(f"STOPPING: spent ${spent:.4f} >= --max-cost "
                          f"{args.max_cost}")
                    print(f"summary: ok={ok} skipped={skipped} "
                          f"failed={failed}")
                    return 3
                cmd = pilot_command(profile, cond, k, seed, stamp_dir,
                                    dry_run=args.dry_run)
                proc = runner(cmd, stdout=log, stderr=subprocess.STDOUT,
                              cwd=ROOT)
                if proc.returncode == 0:
                    os.makedirs(stamp_dir, exist_ok=True)
                    open(marker, "w").close()
                    spent += artifact_cost(stamp_dir)
                    ok += 1
                    consecutive = 0
                    print(f"  ok   {stamp}")
                else:
                    failed += 1
                    consecutive += 1
                    print(f"  FAIL {stamp} (see {log_path})")
                    if consecutive >= MAX_CONSECUTIVE_FAILURES:
                        print(f"STOPPING: {MAX_CONSECUTIVE_FAILURES} "
                              f"consecutive failures", file=sys.stderr)
                        print(f"summary: ok={ok} skipped={skipped} "
                              f"failed={failed}")
                        return 1
    print(f"summary: ok={ok} skipped={skipped} failed={failed} "
          f"cost_usd={round(spent, 4) if profile.get('in_price') is not None else 'unpriced'}")
    return 0 if failed == 0 else 1


def build_parser():
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n\nUsage:")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True,
                    help="profile name in experiments/models.json")
    ap.add_argument("--models-file", default=MODELS)
    ap.add_argument("--seeds-file", required=True,
                    help="seed eligibility JSON with run_set.sto")
    ap.add_argument("--out", default=None)
    ap.add_argument("--dry-run", action="store_true",
                    help="use run_pilot's dry-run provider, no API calls")
    ap.add_argument("--plan", action="store_true",
                    help="print the cell plan as CSV and exit")
    ap.add_argument("--plan-csv", default=None,
                    help="with --plan, also write the CSV here")
    ap.add_argument("--est-prompt-tokens", type=int, default=3000,
                    help="--plan cost estimate: prompt tokens per call")
    ap.add_argument("--est-completion-tokens", type=int, default=600,
                    help="--plan cost estimate: completion tokens per call")
    ap.add_argument("--max-cost", type=float, default=None,
                    help="USD cap on summed telemetry cost")
    ap.add_argument("--limit-seeds", type=int, default=None,
                    help="use only the first N seeds (smoke tests)")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not args.plan and not args.out:
        raise SystemExit("--out is required unless --plan")
    return run(args)


if __name__ == "__main__":
    sys.exit(main())

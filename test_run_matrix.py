#!/usr/bin/env python3
"""Tests for experiments/run_matrix.py and the additive run_pilot options it
uses: --icl-levels/--icl-repeats and --telemetry on icl_two_response_v1.

Run from the repository root: python3 test_run_matrix.py
"""

from __future__ import annotations

import argparse
import glob
import io
import json
import os
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout

import run_pilot
from test_every_pair import ARGS, GOLDEN

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "experiments"))
import run_matrix  # noqa: E402

PASSED = []


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"FAIL {name}: {detail}")
    PASSED.append(name)
    print(f"PASS {name}")


def pilot(outdir, extra=()):
    subprocess.run([sys.executable, "-B", os.path.join(HERE, "run_pilot.py")]
                   + ARGS + list(extra) + ["--out", outdir],
                   cwd=HERE, check=True, stdout=subprocess.DEVNULL)
    paths = sorted(p for p in glob.glob(os.path.join(outdir, "p", "*.json"))
                   if not p.endswith("summary.json"))
    summary = json.load(open(os.path.join(outdir, "p", "summary.json")))
    return [json.load(open(p)) for p in paths], summary


def test_level_repeat_option(tmp):
    for n in (1, 3):
        arts, summary = pilot(os.path.join(tmp, f"r{n}"),
                              ["--icl-levels", "explained_logs",
                               "--icl-repeats", str(n)])
        check(f"--icl-repeats {n}: exactly {n} run(s)", len(arts) == n,
              str(len(arts)))
        check(f"--icl-repeats {n}: explained_logs only, golden prompts",
              all(a["level"] == "explained_logs"
                  and (a["turns"]["A"]["prompt_sha256"],
                       a["turns"]["B"]["prompt_sha256"])
                  == GOLDEN["explained_logs"] for a in arts))
        check(f"--icl-repeats {n}: repeats 1..{n}, distinct sampling seeds",
              sorted(a["repeat"] for a in arts) == list(range(1, n + 1))
              and len({a["model"]["sampling_seed"] for a in arts}) == n)
        check(f"--icl-repeats {n}: summary gate passes with {n} expected",
              summary["expected_runs"] == n
              and summary["operational_gate_pass"] is True, str(summary))
        check(f"--icl-repeats {n}: no telemetry without --telemetry",
              all("telemetry" not in a for a in arts))


def test_flag_off_unchanged(tmp):
    arts, summary = pilot(os.path.join(tmp, "off"))
    check("flags off: nine runs, 3x3 summary",
          len(arts) == 9 and summary["expected_runs"] == 9
          and summary["every_level_repeat_present"])
    check("flags off: golden prompts, no new fields",
          all((a["turns"]["A"]["prompt_sha256"],
               a["turns"]["B"]["prompt_sha256"]) == GOLDEN[a["level"]]
              and "telemetry" not in a and "icl_level_subset" not in a
              for a in arts))
    proc = subprocess.run(
        [sys.executable, "-B", os.path.join(HERE, "run_pilot.py"),
         "--condition", "silent_break", "--seed", "33", "--mode", "sto",
         "--icl-repeats", "1", "--out", tmp], cwd=HERE,
        capture_output=True, text=True)
    check("--icl-repeats refused outside icl_two_response_v1",
          proc.returncode != 0 and "require" in proc.stderr)


def test_icl_telemetry_unit():
    art = {"turns": {
        "A": {"raw_response": "a", "network_retries": [{"attempt": 1}],
              "provider_usage": {"prompt_tokens": 1000,
                                 "completion_tokens": 200}},
        "B": {"raw_response": "b", "network_retries": [],
              "provider_usage": {"prompt_tokens": 3000,
                                 "completion_tokens": 400}}}}
    tel = run_pilot.build_icl_telemetry(art, 1.5, 2.0, 10.0)
    check("icl telemetry sums both turns",
          tel["calls"] == 2 and tel["prompt_tokens"] == 4000
          and tel["completion_tokens"] == 600
          and tel["network_retries"] == 1 and tel["artifact_bytes"] > 0)
    check("icl telemetry cost estimated",
          tel["cost"]["status"] == "estimated"
          and abs(tel["cost"]["amount"] - 0.014) < 1e-9, str(tel["cost"]))
    check("icl telemetry unpriced without prices",
          run_pilot.build_icl_telemetry(art, 1.0)["cost"]["status"]
          == "unpriced")


# Each dispatched call reports 1000 prompt + 500 completion tokens; at
# 100 USD per 1M each, one call costs 0.15 and one run (two calls) 0.30.
WRAPPER = """
import sys
sys.path.insert(0, {root!r})
import run_pilot
orig = run_pilot.dispatch_icl
def patched(*a, **kw):
    r = orig(*a, **kw)
    r["usage"] = {{"prompt_tokens": 1000, "completion_tokens": 500}}
    return r
run_pilot.dispatch_icl = patched
sys.argv = [{script!r}] + sys.argv[1:]
run_pilot.main()
"""


def matrix_args(tmp, **kw):
    models = os.path.join(tmp, "models.json")
    with open(models, "w") as fh:
        json.dump({"fake_priced": {"provider": "openai", "model": "x",
                                   "in_price": 100, "out_price": 100,
                                   "samples_silent_break": 3}}, fh)
    seeds = os.path.join(tmp, "seeds.json")
    with open(seeds, "w") as fh:
        json.dump({"run_set": {"sto": [33]}}, fh)
    base = dict(model="fake_priced", models_file=models, seeds_file=seeds,
                out=os.path.join(tmp, "matrix"), dry_run=True, plan=False,
                plan_csv=None, est_prompt_tokens=3000,
                est_completion_tokens=600, max_cost=None, limit_seeds=None)
    base.update(kw)
    return argparse.Namespace(**base)


def test_cost_cap(tmp):
    wrapper = os.path.join(tmp, "wrapper.py")
    with open(wrapper, "w") as fh:
        fh.write(WRAPPER.format(root=HERE,
                                script=os.path.join(HERE, "run_pilot.py")))
    calls = []

    def runner(cmd, **kw):
        calls.append(cmd)
        assert cmd[2] == run_matrix.RUN_PILOT
        return subprocess.run([cmd[0], "-B", wrapper] + cmd[3:], **kw)

    args = matrix_args(tmp, max_cost=0.5)
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = run_matrix.run(args, runner=runner)
    out = buf.getvalue()
    done = glob.glob(os.path.join(args.out, "*", ".done"))
    check("cost cap: stops with code 3 after 2 instances (0.60 >= 0.5)",
          rc == 3 and len(calls) == 2 and len(done) == 2
          and "STOPPING: spent $0.6000" in out, out)
    spent = sum(run_matrix.artifact_cost(os.path.dirname(d)) for d in done)
    check("cost cap: cost summed from run artifacts' telemetry",
          abs(spent - 0.6) < 1e-9, str(spent))
    # Defect: the same run without the injected usage costs nothing and
    # runs every cell, so the cap above was driven by the telemetry.
    args2 = matrix_args(tmp, max_cost=0.5, out=os.path.join(tmp, "m2"))
    with redirect_stdout(io.StringIO()):
        rc2 = run_matrix.run(args2)
    check("cost cap: no usage (plain dry run) never trips the cap",
          rc2 == 0 and len(glob.glob(os.path.join(args2.out, "*", ".done")))
          == len(run_matrix.matrix_cells()))
    sb = glob.glob(os.path.join(args2.out, "silent_break_k10_s33", "run",
                                "*explained_logs*.json"))
    nc = glob.glob(os.path.join(args2.out, "no_change_k10_s33", "run",
                                "*explained_logs*.json"))
    check("matrix: 3 answers per silent_break instance, 1 otherwise",
          len(sb) == 3 and len(nc) == 1, f"{len(sb)} {len(nc)}")


def test_empty_seeds(tmp):
    for name, body in (("zero_bytes", ""),
                       ("empty_sto", json.dumps({"run_set": {"sto": []}}))):
        path = os.path.join(tmp, name + ".json")
        with open(path, "w") as fh:
            fh.write(body)
        try:
            run_matrix.load_seeds(path)
            msg = None
        except SystemExit as exc:
            msg = str(exc)
        check(f"empty seeds file ({name}) => could not run",
              msg is not None and msg.startswith("could not run"), str(msg))


def test_plan_and_git_check(tmp):
    sol = run_matrix.load_profile("gpt56_sol")
    gpt4o = run_matrix.load_profile("gpt4o")
    check("calls per instance: gpt56_sol silent_break 6, others 2",
          run_matrix.calls_per_instance("silent_break", sol) == 6
          and run_matrix.calls_per_instance("no_change", sol) == 2
          and run_matrix.calls_per_instance("silent_break", gpt4o) == 2)
    cmd = run_matrix.pilot_command(sol, "silent_break", 10, 33, tmp, True)
    check("pilot command: explained_logs, 3 repeats for gpt56_sol",
          cmd[cmd.index("--icl-levels") + 1] == "explained_logs"
          and cmd[cmd.index("--icl-repeats") + 1] == "3")

    class P:
        def __init__(self, rc, out=""):
            self.returncode, self.stdout, self.stderr = rc, out, ""

    def fake(head_rc, status_out):
        return lambda cmd, **kw: (P(head_rc) if "rev-parse" in cmd
                                  else P(0, status_out))
    check("git check: clean committed worktree passes",
          run_matrix.git_clean_check(runner=fake(0, "")) is None)
    check("git check: dirty worktree refused",
          "uncommitted" in run_matrix.git_clean_check(
              runner=fake(0, " M run_pilot.py\n")))
    check("git check: missing HEAD refused",
          "HEAD" in run_matrix.git_clean_check(runner=fake(128, "")))
    orig = run_matrix.git_clean_check
    run_matrix.git_clean_check = lambda: "worktree has 1 uncommitted path(s)"
    try:
        launched = []
        err = io.StringIO()
        old, sys.stderr = sys.stderr, err
        try:
            rc = run_matrix.run(matrix_args(tmp, dry_run=False,
                                            out=os.path.join(tmp, "real")),
                                runner=lambda *a, **k: launched.append(a))
        finally:
            sys.stderr = old
        check("real run refused up front on a dirty worktree",
              rc == 2 and not launched
              and "clean committed git worktree" in err.getvalue())
    finally:
        run_matrix.git_clean_check = orig


CONDS = ("no_change", "irrelevant", "silent_break", "hard_removal",
         "redirect", "degradation")


def _queried(seed, cond, target_half):
    sc = dict(run_pilot.SCENARIO_DEFAULTS)
    sc.update({"name": "t", "seed": seed, "condition": cond, "k": 10,
               "budget": 10})
    record = run_pilot.build_record(sc, False)
    return (run_pilot.queried_pairs_for_icl(record, sc,
                                            target_half=target_half),
            run_pilot.protocol_target_pair(record, sc), record)


# irrelevant is left out: protocol_target_pair takes its own changed
# (irrelevant) pair as T*, so its set differed before this flag too.
SAME_SET_CONDS = tuple(c for c in CONDS if c != "irrelevant")


def same_set_across_conditions(seeds):
    for seed in seeds:
        sets = {cond: _queried(seed, cond, True)[0]
                for cond in SAME_SET_CONDS}
        if len({json.dumps(v) for v in sets.values()}) != 1:
            return False
    return True


def test_queried_target_half(tmp):
    seeds = (33, 34, 35, 36, 38, 39)
    coins = {s: run_pilot.queried_target_included(s) for s in seeds}
    check("target-half coin: both outcomes among test seeds",
          set(coins.values()) == {True, False}, str(coins))
    check("target-half: same queried set in the five conditions "
          "other than irrelevant",
          same_set_across_conditions(seeds))
    for seed in seeds:
        q_on, target, record = _queried(seed, "silent_break", True)
        q_off = _queried(seed, "silent_break", False)[0]
        keys = [(q["node"], q["action"]) for q in q_on]
        if coins[seed]:
            check(f"seed {seed} (coin in): selection equals default",
                  q_on == q_off)
        else:
            pre = {(e["from"], e["action"]): (e["to"], e["p"])
                   for e in record["world_pre"]["edges"]}
            post = {(e["from"], e["action"]): (e["to"], e["p"])
                    for e in record["world_post"]["edges"]}
            check(f"seed {seed} (coin out): five unchanged, no target",
                  len(keys) == 5 and target not in keys
                  and all(pre[k] == post.get(k) for k in keys))
    # Injected defect: a coin that reads the condition breaks the
    # every-condition-same-set property, and the check above catches it.
    orig_coin, orig_q = run_pilot.queried_target_included, \
        run_pilot.queried_pairs_for_icl
    cur = {}

    def leaky(record, sc, target_half=False):
        cur["cond"] = sc["condition"]
        return orig_q(record, sc, target_half)
    run_pilot.queried_pairs_for_icl = leaky
    run_pilot.queried_target_included = lambda seed: (
        orig_coin(seed) if cur.get("cond") != "redirect"
        else not orig_coin(seed))
    cur["cond"] = None
    try:
        caught = not same_set_across_conditions(seeds[:2])
    finally:
        run_pilot.queried_pairs_for_icl = orig_q
        run_pilot.queried_target_included = orig_coin
    check("target-half defect (condition-dependent coin) is detected", caught)

    arts, summary = pilot(os.path.join(tmp, "qth"),
                          ["--queried-target-half", "--period-b-every-pair",
                           "--icl-levels", "explained_logs",
                           "--icl-repeats", "1"])
    art = arts[0]
    cp = art["turns"]["B"]["scored"]["control_preservation"]
    check("target-half artifact records queried_target_included",
          art["protocol_options"]["queried_target_included"] is False
          and art["protocol_options"]["period_b_every_pair"] is True)
    check("target-half: five controls scored, dry answer fully correct",
          cp["n_controls"] == 5 and cp["all_controls_correct"] is True
          and art["turns"]["B"]["scored"]["correct"] is True
          and summary["operational_gate_pass"])


def test_pair_scores_match_references():
    from experiments import reference_sweep as RS
    for seed in (33, 35, 38):
        _, _, pv = RS.instance(seed, "silent_break", False, 10)
        refs, scores = RS.references(pv, False), RS.pair_scores(pv, False)
        for name in ("transition", "bayes"):
            check(f"pair_scores seed {seed} {name}: argmax matches references()",
                  RS.ranked(scores[name])[0] == tuple(refs[name]["loc"]))


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        test_level_repeat_option(tmp)
        test_flag_off_unchanged(tmp)
        test_icl_telemetry_unit()
        os.makedirs(os.path.join(tmp, "cap"))
        test_cost_cap(os.path.join(tmp, "cap"))
        test_empty_seeds(tmp)
        test_plan_and_git_check(tmp)
        test_queried_target_half(tmp)
    test_pair_scores_match_references()
    print(f"\n{len(PASSED)} passed, 0 failed")

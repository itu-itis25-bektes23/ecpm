#!/usr/bin/env python3
"""Tests for --period-b-every-pair (icl_two_response_v1, additive).

The Period B answer states a belief about every listed pair, and the route
is scored for self-consistency against those beliefs. With the flag off the
prompts and artifacts must stay exactly as before; the golden hashes below
were taken from a dry run of the code before the flag existed.

Run from the repository root: python3 test_every_pair.py
"""

from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
import tempfile

import ecpm_parser
import run_pilot

HERE = os.path.dirname(os.path.abspath(__file__))
PASSED = []

ARGS = ["--scenario", "seed7_silent_break", "--condition", "silent_break",
        "--seed", "33", "--mode", "sto", "--provider", "dry-run",
        "--tag", "p", "--protocol", "icl_two_response_v1",
        "--k", "10", "--budget", "10"]

# sha256 of (prompt A, prompt B) per level, seed 33 sto silent break K=10,
# from the pre-flag code path. Flag off must reproduce these exactly.
GOLDEN = {
    "empirical_table": (
        "de8b38a2b9e74f83d2852ecf0c2c21990c8f30e4376829a4d559907c696c07af",
        "10aeb81b1196f2a57dba8169fe4366dc61203662640178eae0686df044a693cc"),
    "explained_logs": (
        "d3505408d64ecbd8ee3cd9a475ef1977081849befd61311e281b9f5f33a12f26",
        "e165891299af576aec915a6d37deef0da400fccfb667df098a2bbcbd741d0e60"),
    "minimal_logs": (
        "722ec4d55e5325f78d1c4e8b3ca8e2606e200f2304dcf5a79199cf3d2c906f21",
        "a2326d86d35a454c88336fdf43bb0a4ae125ab43a60ce78107450a58e97783ed"),
}


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"FAIL {name}: {detail}")
    PASSED.append(name)
    print(f"PASS {name}")


def dry_run(outdir, extra=()):
    subprocess.run([sys.executable, "-B", os.path.join(HERE, "run_pilot.py")]
                   + ARGS + list(extra) + ["--out", outdir],
                   cwd=HERE, check=True, stdout=subprocess.DEVNULL)
    paths = sorted(p for p in glob.glob(os.path.join(outdir, "p", "*.json"))
                   if not p.endswith("summary.json"))
    if not paths:
        raise AssertionError(f"dry run wrote no artifacts in {outdir}")
    return {p: json.load(open(p, encoding="utf-8")) for p in paths}


def explained_r1(arts):
    hits = [a for p, a in arts.items() if "_r1_explained_logs_" in p]
    if len(hits) != 1:
        raise AssertionError(f"expected one r1 explained_logs artifact, got {len(hits)}")
    return hits[0]


def test_flag_off_byte_identical(tmp):
    arts = dry_run(os.path.join(tmp, "off"))
    check("flag off: nine artifacts", len(arts) == 9, str(len(arts)))
    for art in arts.values():
        a, b = GOLDEN[art["level"]]
        check(f"flag off: {art['run_id'][:48]} prompts match pre-flag code",
              art["turns"]["A"]["prompt_sha256"] == a
              and art["turns"]["B"]["prompt_sha256"] == b
              and run_pilot.sha256_text(art["turns"]["B"]["prompt"]) == b)
        check(f"flag off: {art['run_id'][:48]} has no new fields",
              "protocol_options" not in art
              and "route_self_consistency" not in art["turns"]["B"]["scored"]
              and "every_pair_beliefs" not in art["turns"]["B"]["parsed"])
    return arts


def test_flag_on(tmp, off_arts):
    arts = dry_run(os.path.join(tmp, "on"), ["--period-b-every-pair"])
    art = explained_r1(arts)
    off = explained_r1(off_arts)
    listed = art["protocol_options"]["listed_pairs_b"]
    menu_pairs = {(n, a) for period in ("pre", "post")
                  for n, acts in art["menus"][period].items() for a in acts}
    check("flag on: listed pairs are every menu pair",
          {(q["node"], q["action"]) for q in listed} == menu_pairs
          and len(listed) == len(menu_pairs) > 5, str(len(listed)))
    check("flag on: queried five come first",
          listed[:5] == art["queried_pairs"])
    prompt_b = art["turns"]["B"]["prompt"]
    block = prompt_b.split("Pairs to report in this order:\n", 1)[1]
    block = block.split("\n\n", 1)[0].split("\n")
    check("flag on: turn-B prompt lists every pair in order",
          block == [f"- {q['node']} {q['action']}" for q in listed],
          "\n".join(block))
    check("flag on: turn-B schema text is the every-pair schema",
          run_pilot.ICL_TURN_B_EVERY_PAIR_SCHEMA in prompt_b
          and "exactly five pairs" not in prompt_b)
    check("flag on: turn A unchanged",
          art["turns"]["A"]["prompt"] == off["turns"]["A"]["prompt"])
    check("flag on: run id differs from flag off",
          art["run_id"] != off["run_id"])
    parsed = art["turns"]["B"]["parsed"]
    scored = art["turns"]["B"]["scored"]
    check("flag on: dry-run answer parses with every pair",
          parsed["well_formed"] and parsed["every_pair_beliefs"]["status"] == "ok"
          and len(parsed["every_pair_beliefs"]["pairs"]) == len(listed)
          and len(parsed["beliefs"]["pairs"]) == 5)
    check("flag on: five-pair scores unchanged on the oracle answer",
          scored["beliefs"]["accuracy"] == off["turns"]["B"]["scored"]["beliefs"]["accuracy"]
          and scored["correct"] is True)
    check("flag on: oracle route is self-consistent",
          scored["route_self_consistency"]["self_consistent"] is True,
          str(scored["route_self_consistency"]))
    return art


def test_parser_rejects_defects(art):
    listed = art["protocol_options"]["listed_pairs_b"]
    queried = art["queried_pairs"]
    raw = json.loads(art["turns"]["B"]["raw_response"])

    def parse(obj):
        return ecpm_parser.parse_icl_turn_b_every_pair(
            json.dumps(obj), listed, queried)

    good = parse(raw)
    check("parser: clean answer accepted", good["well_formed"])

    # injected defect: drop one non-queried pair
    missing = dict(raw, pairs=raw["pairs"][:-1])
    got = parse(missing)
    check("parser: missing pair rejected and named",
          not got["well_formed"]
          and got["every_pair_beliefs"]["status"] == "missing_pair"
          and got["beliefs"]["status"] == "missing_pair"
          and got["every_pair_beliefs"]["missing_pairs"] == [
              {"node": raw["pairs"][-1]["node"],
               "action": raw["pairs"][-1]["action"]}],
          str(got["every_pair_beliefs"]))
    scored = run_pilot.score_icl_turn(
        run_pilot.build_record(run_pilot.resolve_scenario(
            run_pilot.argparse.Namespace(
                scenario="seed7_silent_break", condition="silent_break",
                seed=33, k=10, budget=10, evidence_seed=None,
                rendering=None, probes=None)),
            False), got, queried, "post",
        (art["evaluator_only"]["intervention_target"]["node"],
         art["evaluator_only"]["intervention_target"]["action"]),
        {}, pre_beliefs=art["turns"]["A"]["scored"]["beliefs"])
    check("parser: missing pair scores as not well formed",
          scored["well_formed"] is False and scored["correct"] is False)

    # a five-pair answer (the old schema) is a missing-pair answer here
    five = dict(raw, pairs=[p for p in raw["pairs"]
                            if {"node": p["node"], "action": p["action"]}
                            in queried])
    check("parser: five-pair answer rejected under the flag",
          parse(five)["every_pair_beliefs"]["status"] == "missing_pair")
    dup = dict(raw, pairs=raw["pairs"] + raw["pairs"][:1])
    check("parser: duplicate pair rejected",
          parse(dup)["every_pair_beliefs"]["status"] == "duplicate_pair")
    extra = dict(raw, pairs=raw["pairs"] + [
        {"node": "Z", "action": "a9", "available": False, "changed": False,
         "destination": None, "p_success": None}])
    check("parser: unlisted pair rejected",
          parse(extra)["every_pair_beliefs"]["status"] == "unknown_pair")


def _beliefs(rows):
    return {"status": "ok", "pairs": [
        {"node": n, "action": a, "available": av, "changed": False,
         "destination": d, "p_success": p} for n, a, av, d, p in rows]}


def _route(steps):
    return {"status": "ok",
            "route": [{"node": n, "action": a} for n, a in steps]}


def test_self_consistency():
    # S -a1-> G direct at p=0.2 (cost 5); S -a2-> M -a1-> G at p=1 (cost 2)
    beliefs = _beliefs([("S", "a1", True, "G", 0.2),
                        ("S", "a2", True, "M", 1.0),
                        ("M", "a1", True, "G", 1.0),
                        ("M", "a2", False, None, None)])
    ok = ecpm_parser.route_self_consistency(
        _route([("S", "a2"), ("M", "a1")]), beliefs, "S", "G")
    check("self_consistent true: optimal under stated beliefs",
          ok["self_consistent"] is True and ok["reasons"] == [], str(ok))
    worse = ecpm_parser.route_self_consistency(
        _route([("S", "a1")]), beliefs, "S", "G")
    check("self_consistent false: suboptimal under stated beliefs",
          worse["self_consistent"] is False
          and worse["reasons"] == ["not_optimal_under_stated_beliefs"],
          str(worse))
    low = _beliefs([("S", "a1", True, "G", 0.05),
                    ("S", "a2", True, "M", 0.5),
                    ("M", "a1", True, "G", 0.5),
                    ("M", "a2", False, None, None)])
    floor = ecpm_parser.route_self_consistency(
        _route([("S", "a1")]), low, "S", "G")
    check("self_consistent false: p_hat <= 0.05",
          floor["self_consistent"] is False and floor["reasons"]
          == ["uses_action_with_p_hat_at_or_below_floor"], str(floor))
    gone = ecpm_parser.route_self_consistency(
        _route([("S", "a2"), ("M", "a2")]), beliefs, "S", "G")
    check("self_consistent false: action stated unavailable",
          gone["self_consistent"] is False and gone["reasons"]
          == ["uses_action_stated_unavailable"], str(gone))
    bad = ecpm_parser.route_self_consistency(
        _route([("S", "a1")]), {"status": "missing_pair", "pairs": []},
        "S", "G")
    check("self_consistent not scored when beliefs did not validate",
          bad["status"] == "not_scored" and bad["self_consistent"] is None)


def test_flag_guards():
    proc = subprocess.run(
        [sys.executable, "-B", os.path.join(HERE, "run_pilot.py"),
         "--condition", "silent_break", "--seed", "33", "--mode", "sto",
         "--period-b-every-pair", "--out", tempfile.mkdtemp()],
        cwd=HERE, capture_output=True, text=True)
    check("flag refused outside icl_two_response_v1",
          proc.returncode != 0 and "requires --protocol" in proc.stderr,
          proc.stderr[-300:])


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        off_arts = test_flag_off_byte_identical(tmp)
        art = test_flag_on(tmp, off_arts)
        test_parser_rejects_defects(art)
    test_self_consistency()
    test_flag_guards()
    print(f"\n{len(PASSED)} passed, 0 failed")

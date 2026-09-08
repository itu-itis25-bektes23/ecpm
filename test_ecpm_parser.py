"""Acceptance tests for the frozen Section 7 parser/scorer (ECPM v2.1).

Run:  python3 test_ecpm_parser.py     (stdlib only)

Covers:
  - format-level cases from parser_fixtures.json (json extraction,
    invalid objects, too-long routes, code fences, extra fields)
  - instance-level cases built on the seed-7 records: optimal route,
    zero-regret scoring, stale route through a silent break, stale route
    through a hard removal, discontinuity, unknown label, incomplete
    route, detection/localization/preservation ground truth
"""

import json

from ecpm_parser import (PARSERS, run_probe)
from resource_mdp import make_pair, pair_to_json


def record_for(condition, deterministic=True):
    inst = make_pair(7, condition, deterministic=deterministic)
    return json.loads(json.dumps(pair_to_json(inst)))


def steps_from(record, which="post"):
    o = record["oracle"][which]
    return [{"node": n, "action": a}
            for n, a in zip(o["optimal_route"], o["optimal_actions"])]


def test_format_fixtures():
    with open("parser_fixtures.json") as fh:
        cases = json.load(fh)["cases"]
    n = 0
    for case in cases:
        if "raw_route_repeat" in case:
            raw = json.dumps({"route": [case["raw_route_repeat"]]
                              * case["raw_route_repeat_n"]})
        else:
            raw = case["raw"]
        parsed = PARSERS[case["probe"]](raw)
        assert parsed["status"] == case["expect_status"], \
            f"{case['probe']}: {parsed['status']} != {case['expect_status']}"
        for key, val in case.get("expect", {}).items():
            assert parsed[key] == val
        n += 1
    print(f"PASS format fixtures ({n} cases)")


def test_adaptation_scoring():
    rec = record_for("silent_break")
    # optimal route -> valid_finite, regret 0, is_optimal
    ok = run_probe(rec, "adaptation",
                   json.dumps({"route": steps_from(rec, "post")}))
    assert ok["scored"]["status"] == "valid_finite"
    assert ok["scored"]["is_optimal"] and abs(ok["scored"]["regret"]) < 1e-9
    # stale (pre-optimal) route -> silent_broken_edge
    stale = run_probe(rec, "adaptation",
                      json.dumps({"route": steps_from(rec, "pre")}))
    assert stale["scored"]["status"] == "silent_broken_edge"
    assert stale["scored"]["expected_cost"] is None
    # same stale route on the matched hard removal -> illegal_action
    hard = record_for("hard_removal")
    ill = run_probe(hard, "adaptation",
                    json.dumps({"route": steps_from(hard, "pre")}))
    assert ill["scored"]["status"] == "illegal_action"
    # discontinuity
    broken = steps_from(rec, "post")
    assert len(broken) >= 2, "seed-7 route long enough for the test"
    broken[1] = {"node": rec["goal"], "action": broken[1]["action"]}
    disc = run_probe(rec, "adaptation", json.dumps({"route": broken}))
    assert disc["scored"]["status"] == "discontinuous_route"
    # unknown label at the start node
    unk = run_probe(rec, "adaptation", json.dumps(
        {"route": [{"node": rec["start"], "action": "a99"}]}))
    assert unk["scored"]["status"] == "unknown_reference"
    # incomplete route (drop the last hop)
    inc = run_probe(rec, "adaptation",
                    json.dumps({"route": steps_from(rec, "post")[:-1]}))
    assert inc["scored"]["status"] == "incomplete_route"
    print("PASS adaptation scoring: optimal / silent / illegal / "
          "discontinuous / unknown / incomplete all distinct")


def test_other_probes():
    rec = record_for("silent_break")
    d = run_probe(rec, "detection", '{"changed": true}')
    assert d["scored"]["correct"] is True
    d2 = run_probe(rec, "detection", '{"changed": false}')
    assert d2["scored"]["correct"] is False
    nc = record_for("no_change", deterministic=False)
    d3 = run_probe(nc, "detection", '{"changed": false}')
    assert d3["scored"]["correct"] is True
    # localization ground truth comes from the exact diff
    ch = rec["change"]
    loc = run_probe(rec, "localization", json.dumps(
        {"node": ch["edge"]["from"], "action": ch["action"]}))
    assert loc["scored"]["correct"] is True
    loc2 = run_probe(rec, "localization", json.dumps(
        {"node": ch["edge"]["from"], "action": "a99"}))
    assert loc2["scored"]["correct"] is False
    # preservation: STRICT contract -- every queried pair exactly once
    target = (ch["edge"]["from"], ch["action"])
    other = next((e["from"], e["action"])
                 for e in rec["world_pre"]["edges"]
                 if (e["from"], e["action"]) != target)
    queried = [{"node": other[0], "action": other[1]},
               {"node": target[0], "action": target[1]}]
    full = json.dumps({"pairs": [
        {"node": other[0], "action": other[1], "changed": False},
        {"node": target[0], "action": target[1], "changed": True}]})
    pres = run_probe(rec, "preservation", full, queried_pairs=queried)
    assert pres["scored"]["status"] == "ok"
    assert pres["scored"]["accuracy"] == 1.0
    assert pres["scored"]["n_scored"] == 2
    one = json.dumps({"pairs": [
        {"node": other[0], "action": other[1], "changed": False}]})
    assert run_probe(rec, "preservation", one,
                     queried_pairs=queried)["scored"]["status"] == \
        "incomplete_response"
    dup = json.dumps({"pairs": [
        {"node": other[0], "action": other[1], "changed": False}] * 2})
    assert run_probe(rec, "preservation", dup,
                     queried_pairs=queried)["scored"]["status"] == \
        "duplicate_pair"
    unk = json.dumps({"pairs": [
        {"node": other[0], "action": "a99", "changed": False}]})
    assert run_probe(rec, "preservation", unk,
                     queried_pairs=queried)["scored"]["status"] == \
        "unknown_pair"
    empty = json.dumps({"pairs": []})
    assert run_probe(rec, "preservation", empty,
                     queried_pairs=queried)["scored"]["status"] == \
        "incomplete_response"
    try:
        run_probe(rec, "preservation", full)
        raise AssertionError("queried_pairs must be required")
    except ValueError:
        pass
    print("PASS detection / localization ground truth; preservation "
          "strict: exact cover required, duplicates/unknown/missing "
          "rejected")



def test_v22_turn1_probes():
    """belief parse/score, route_pre on the PRE world, self-consistency."""
    from ecpm_parser import (belief_self_consistency, parse_belief,
                             score_belief, score_route_pre)
    from resource_mdp import make_pair, pair_to_json, paired_evidence
    inst = make_pair(7, "silent_break", matched=True)
    rec = json.loads(json.dumps(pair_to_json(inst, paired_evidence(inst))))
    ch = rec["change"]
    tgt = {"node": ch["edge"]["from"], "action": ch["action"]}
    other = next({"node": e["from"], "action": e["action"]}
                 for e in rec["world_pre"]["edges"]
                 if (e["from"], e["action"]) != (tgt["node"], tgt["action"]))
    q = [tgt, other]
    truth = {(e["from"], e["action"]): e for e in rec["world_pre"]["edges"]}
    def b(pair, p_off=0.0, period="pre"):
        e = {(x["from"], x["action"]): x
             for x in rec[f"world_{period}"]["edges"]}[(pair["node"],
                                                        pair["action"])]
        return {"node": pair["node"], "action": pair["action"],
                "destination": e["to"], "p": round(e["p"] + p_off, 3)}
    # exact -> 1.0; within tol -> 1.0; outside tol -> per-pair miss
    for off, want in ((0.0, 1.0), (0.14, 1.0), (0.2, 0.5)):
        parsed = parse_belief(json.dumps({"beliefs": [b(tgt, off), b(other)]}))
        sc = score_belief(rec, parsed, q, "pre")
        assert sc["status"] == "ok" and sc["accuracy"] == want, (off, sc)
    assert parse_belief('{"beliefs": [{"node": "A"}]}')["status"] == "invalid_object"
    assert parse_belief("nope")["status"] == "malformed_json"
    # duplicate / missing pair -> invalid
    sc = score_belief(rec, parse_belief(json.dumps({"beliefs": [b(tgt)]})),
                      q, "pre")
    assert sc["status"] == "invalid_object"
    # route_pre: M0 optimum scores 0 regret on the PRE world even though
    # it crosses the (later) broken link
    o = rec["oracle"]["pre"]
    route = [{"node": n, "action": a}
             for n, a in zip(o["optimal_route"], o["optimal_actions"])]
    from ecpm_parser import parse_adaptation
    sr = score_route_pre(rec, parse_adaptation(json.dumps({"route": route})))
    assert sr["status"] == "valid_finite" and sr["is_optimal"], sr
    # self-consistency: target dropped to 0 post, other unchanged
    pre = score_belief(rec, parse_belief(json.dumps(
        {"beliefs": [b(tgt), b(other)]})), q, "pre")
    post = score_belief(rec, parse_belief(json.dumps(
        {"beliefs": [b(tgt, period="post"), b(other, period="post")]})),
        q, "post")
    sc = belief_self_consistency(rec, pre, post)
    assert sc["status"] == "ok" and sc["accuracy"] == 1.0, sc
    print("PASS v2.2 turn-1 probes: belief tolerance, strict cover, "
          "route_pre on M0, self-consistency preservation")


if __name__ == "__main__":
    test_format_fixtures()
    test_adaptation_scoring()
    test_other_probes()
    test_v22_turn1_probes()
    print("\nALL PARSER TESTS PASSED")

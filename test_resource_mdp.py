"""
Sanity tests for resource_mdp.py v2 (ECPM Phase 2). Stdlib only.

Run:  python3 test_resource_mdp.py

Covers the handoff checklist:
  - seeds reproduce (graphs, pairs, and evidence are bit-identical)
  - deterministic mode is the same code path (identical topology per seed)
  - all five conditions behave as specified; diff matches ground truth
  - irrelevant-change invariant: the optimal route is preserved
  - the eligible break is randomized (not candidates[0])
  - coverage balance holds pre AND post (>= k attempts per listed pair)
  - opaque labels: per-node unique, stable across the pair, removal safe
  - execution-based scoring: optimal -> regret 0, garbage -> invalid
  - stale vs adapted broken-link usage endpoints
  - the full paired record is JSON-serializable and round-trips
"""

import json
import random
import resource_mdp as R

from resource_mdp import (CONDITIONS, RoutingMDP, assign_labels,
                          breakable_route_links, broken_link_usage,
                          collect_balanced, edges_off_all_optimal_routes,
                          fixed_policy, legal_actions, make_pair,
                          optimal_policy, pair_to_json, paired_evidence,
                          prompt_view, rollout, route_from_actions,
                          score_route)

INF = float("inf")


def eligible_seeds(n_wanted=6, det=False):
    """First seeds that admit an eligible (reachability-preserving) break."""
    out, s = [], 0
    while len(out) < n_wanted and s < 200:
        try:
            make_pair(s, "silent_break", deterministic=det)
            out.append(s)
        except ValueError:
            pass
        s += 1
    assert len(out) == n_wanted, "could not find enough eligible seeds"
    return out


SEEDS = eligible_seeds(6)


def test_reproducibility():
    for seed in SEEDS[:3]:
        a = make_pair(seed, "silent_break")
        b = make_pair(seed, "silent_break")
        assert a.m0.p == b.m0.p and a.m1.p == b.m1.p
        assert a.change == b.change and a.labels == b.labels
        assert a.oracle == b.oracle
        ea = paired_evidence(a, k=3, evidence_seed=5)
        eb = paired_evidence(b, k=3, evidence_seed=5)
        assert ea["pre"]["F1_log"] == eb["pre"]["F1_log"]
        assert ea["post"]["F2_shuffled"] == eb["post"]["F2_shuffled"]
    print("PASS reproducibility (graphs, diffs, labels, evidence)")


def test_deterministic_same_code_path():
    for seed in SEEDS[:4]:
        sto = RoutingMDP.generate(seed=seed)
        det = RoutingMDP.generate(seed=seed, p_range=(1.0, 1.0))
        assert set(sto.p) == set(det.p), "topology must match across modes"
        assert all(v == 1.0 for v in det.p.values())
        route, cost = det.optimal_route(
            max((n for n in det.nodes if n != det.goal),
                key=lambda n: det.optimal()[0][n]))
        assert abs(cost - (len(route) - 1)) < 1e-9, \
            "deterministic cost == hop count"
    print("PASS deterministic mode: same topology per seed, p==1, "
          "cost==hops")


def test_conditions():
    for seed in SEEDS[:3]:
        for cond in CONDITIONS:
            inst = make_pair(seed, cond)
            o, ch = inst.oracle, inst.change
            assert o["pre"]["solvable"], "pre-world always solvable"
            assert o["post"]["solvable"], \
                "every condition must keep the goal reachable from start"
            route0 = o["pre"]["optimal_route"]
            r0_edges = set(zip(route0, route0[1:]))
            if cond == "no_change":
                assert inst.m1.p == inst.m0.p and ch["edge"] is None
                assert not o["route_changed"] and o["cost_delta"] == 0.0
            else:
                e = ch["edge"]
                assert e is not None
                assert inst.m1.changes[-1]["edge"] == e, \
                    "diff record matches environment ground truth"
            if cond == "irrelevant":
                assert ch["edge"] not in r0_edges
                assert ch["on_optimal_route"] is False
                assert ch["new_p"] == 0.0, "v2.2: irrelevant breaks U*"
                assert o["post"]["optimal_route"] == route0, \
                    "off-route break must preserve the optimum"
            if cond == "degradation":
                assert ch["edge"] in r0_edges and ch["on_optimal_route"]
                assert 0 < ch["new_p"] < ch["old_p"]
            if cond == "silent_break":
                u, v = ch["edge"]
                assert ch["edge"] in r0_edges
                assert inst.m1.p[(u, v)] == 0.0
                assert v in inst.m1.out_edges(u), "still listed"
                assert ch["route_position"] is not None
                assert (u, v) in inst.m1.broken
            if cond == "hard_removal":
                u, v = ch["edge"]
                assert (u, v) not in inst.m1.p
                assert v not in inst.m1.out_edges(u)
                assert ch["new_p"] is None
            # M0 is never mutated
            assert not inst.m0.changes and not inst.m0.broken
    print("PASS all five conditions on %d seeds (incl. irrelevant-change "
          "invariant, M0 frozen)" % len(SEEDS[:3]))


def test_break_randomization():
    # find a seed with >= 2 eligible breaks, then redraw with change_seed
    for seed in SEEDS:
        inst = make_pair(seed, "silent_break")
        cands = breakable_route_links(inst.m0.copy(), inst.start)
        if len(cands) >= 2:
            chosen = {make_pair(seed, "silent_break",
                                change_seed=i).change["edge"]
                      for i in range(12)}
            assert len(chosen) >= 2, "break must be randomized"
            assert chosen <= set(cands), "only eligible breaks drawn"
            print("PASS break randomization: %d distinct edges drawn from "
                  "%d candidates (seed %d)"
                  % (len(chosen), len(cands), seed))
            return
    raise AssertionError("no seed with >=2 candidates found")


def test_balance():
    inst = make_pair(SEEDS[0], "silent_break")
    ev = paired_evidence(inst, k=4, evidence_seed=1)
    assert ev["min_attempts_pre"] >= 4 and ev["min_attempts_post"] >= 4
    u, v = inst.change["edge"]
    rec = ev["counts_post"][f"{u}->{v}"]
    assert rec["attempts"] >= 4 and rec["delivered"] == 0, \
        "broken pair gets >= k attempts, all drops"
    # per-pair counts must equal the rendered evidence
    total = sum(r["attempts"] for r in ev["counts_pre"].values())
    assert total == sum(1 for ln in ev["pre"]["F2_ordered"].split("\n")
                        if ln.strip())
    # shuffled facts are a permutation of the ordered facts
    assert (sorted(ev["pre"]["F2_shuffled"].split("\n"))
            == sorted(ln for ln in ev["pre"]["F2_ordered"].split("\n")
                      if ln.strip()))
    assert (ev["pre"]["F2_shuffled"].split("\n")
            != [ln for ln in ev["pre"]["F2_ordered"].split("\n")
                if ln.strip()]), "shuffle must actually permute"
    print("PASS balance: >=k per listed pair pre & post; broken pair all "
          "drops; shuffled facts == permutation of ordered facts")


def test_labels():
    inst = make_pair(SEEDS[1], "hard_removal")
    # every M0 edge labeled; per-node labels unique
    for u in inst.m0.nodes:
        labs = [inst.labels[(u, v)] for v in inst.m0.out_edges(u)]
        assert len(labs) == len(set(labs))
    assert set(inst.labels) == set(inst.m0.p)
    # stable across the pair: M1 menu is a subset of M0 menu
    la0 = legal_actions(inst.m0, inst.labels)
    la1 = legal_actions(inst.m1, inst.labels)
    u, v = inst.change["edge"]
    gone = inst.labels[(u, v)]
    assert gone in la0[u] and gone not in la1[u]
    for w in inst.m1.nodes:
        if w in la1:
            assert set(la1[w]) <= set(la0[w]), \
                "surviving labels must not shift after removal"
    # labels reveal nothing lexical about destinations
    assert all(lab[0] == "a" and lab[1:].isdigit()
               for lab in inst.labels.values())
    # translation: optimal action plan -> optimal node route
    o = inst.oracle
    path = route_from_actions(inst.start, o["pre"]["optimal_actions"],
                              inst.labels)
    assert path == o["pre"]["optimal_route"]
    # a plan through the removed edge translates but scores invalid on M1
    if o["pre"]["optimal_route"] != o["post"]["optimal_route"]:
        stale_path = o["pre"]["optimal_route"]
        assert score_route(inst.m1, stale_path, inst.start)["valid"] is False
    print("PASS labels: per-node unique, stable across pair, opaque, "
          "translation + removal semantics correct")


def test_scoring():
    inst = make_pair(SEEDS[2], "silent_break")
    o = inst.oracle
    s = score_route(inst.m1, o["post"]["optimal_route"], inst.start)
    assert s["valid"] and abs(s["regret"]) < 1e-9
    assert score_route(inst.m1, None, inst.start)["valid"] is False
    assert score_route(inst.m1, [inst.start], inst.start)["valid"] is False
    assert score_route(inst.m1, ["ZZ", inst.m1.goal],
                       inst.start)["valid"] is False
    # alternative route is proper, distinct, and no cheaper than optimal
    alt, alt_c = o["pre"]["alternative_route"], o["pre"]["alternative_cost"]
    assert alt is not None and alt != o["pre"]["optimal_route"]
    assert alt_c >= o["pre"]["optimal_cost"] - 1e-9
    assert score_route(inst.m0, alt, inst.start)["valid"]
    print("PASS scoring: optimal regret 0, invalid plans rejected, "
          "alternative route proper & distinct")


def test_usage_metric_endpoints():
    inst = make_pair(7, "silent_break")   # seed 7 = the write-up instance
    u, v = inst.change["edge"]
    rng = random.Random("t|usage")
    stale = fixed_policy(inst.m0.optimal()[1], inst.m1)
    adapted = optimal_policy(inst.m1)
    stale_att = [a for _ in range(30)
                 for a in rollout(inst.m1, inst.start, stale, rng, 40)[0]]
    adapt_att = [a for _ in range(30)
                 for a in rollout(inst.m1, inst.start, adapted, rng, 40)[0]]
    assert broken_link_usage(stale_att, u, v) == 1.0
    au = broken_link_usage(adapt_att, u, v)
    assert au in (None, 0.0), "adapted planner never re-chooses the break"
    print("PASS usage metric: stale=1.00, adapted=%s"
          % ("n/a (node avoided)" if au is None else "0.00"))


def test_json_roundtrip():
    for det in (False, True):
        inst = make_pair(SEEDS[0], "silent_break", deterministic=det)
        ev = paired_evidence(inst, k=3, evidence_seed=9)
        blob = json.dumps(pair_to_json(inst, ev))
        back = json.loads(blob)
        assert back["schema_version"] == "2.1"
        assert back["change"]["edge"]["from"] == inst.change["edge"][0]
        assert back["oracle"]["post"]["optimal_cost"] is not None
        for f in ("F1_log", "F2_ordered", "F2_shuffled", "F3_stats",
                  "F4_narrative"):
            assert back["evidence"]["pre"][f]
    # no_change serializes with a null edge
    inst = make_pair(SEEDS[0], "no_change")
    back = json.loads(json.dumps(pair_to_json(inst, None)))
    assert back["change"]["edge"] is None
    print("PASS JSON round-trip (both modes; null edge under no_change)")


def test_multi_seed_sweep():
    ok = 0
    for seed in SEEDS:
        for cond in CONDITIONS:
            inst = make_pair(seed, cond)
            assert inst.oracle["post"]["solvable"]
            ok += 1
    print("PASS sweep: %d condition x seed pairs all solvable post-change"
          % ok)


def test_v21_shared_break_target():
    for det in (False, True):
        for seed in SEEDS[:4]:
            s = make_pair(seed, "silent_break", deterministic=det)
            h = make_pair(seed, "hard_removal", deterministic=det)
            assert s.change["edge"] == h.change["edge"], \
                "silent break and hard removal must hit the same link"
    print("PASS v2.1 shared target: silent_break == hard_removal per "
          "(seed, mode)")


def test_v21_irrelevant_off_all_optimal_routes():
    hits = 0
    for seed in SEEDS:
        for det in (False, True):
            try:
                inst = make_pair(seed, "irrelevant", deterministic=det)
            except ValueError:
                continue
            hits += 1
            off = set(edges_off_all_optimal_routes(inst.m0, inst.start))
            assert inst.change["edge"] in off, \
                "target must be off EVERY optimal route"
            assert (inst.oracle["pre"]["route_unique"]
                    == inst.oracle["post"]["route_unique"]), \
                "irrelevant change must not flip route uniqueness"
            assert (inst.oracle["pre"]["optimal_route"]
                    == inst.oracle["post"]["optimal_route"])
            if det:
                assert inst.change["new_p"] == 0.0
                assert all(p in (0.0, 1.0) for p in inst.m1.p.values()), \
                    "deterministic post world must stay binary"
    assert hits
    print("PASS v2.1 irrelevant: off every optimal route, uniqueness "
          "preserved, det post world binary (%d instances)" % hits)


def test_v22_degradation_shares_target():
    """v2.2: degradation, silent_break and hard_removal intervene on the
    SAME on-route link T* for a given (seed, mode, matched)."""
    n = 0
    for seed in range(1, 40):
        for matched in (False, True):
            try:
                d = make_pair(seed, "degradation", matched=matched)
                s = make_pair(seed, "silent_break", matched=matched)
                h = make_pair(seed, "hard_removal", matched=matched)
            except ValueError:
                continue
            assert d.change["edge"] == s.change["edge"] == h.change["edge"], \
                (seed, matched, "degradation must share T*")
            assert d.change["mode"] == "degrade" and 0 < d.change["new_p"]
            if matched:
                ds = make_pair(seed, "silent_break", deterministic=True,
                               matched=True)
                assert ds.change["edge"] == d.change["edge"], \
                    "matched det silent_break sibling shares T*"
            n += 1
    assert n > 0
    print("PASS v2.2 degradation shares T* with the break family "
          "(%d instances)" % n)


def test_v21_det_degradation_undefined():
    try:
        make_pair(SEEDS[0], "degradation", deterministic=True)
    except ValueError as exc:
        assert "deterministic" in str(exc)
        print("PASS v2.1 deterministic degradation raises ValueError")
        return
    raise AssertionError("deterministic degradation must be rejected")


def test_v21_obfuscation_pure_relabeling():
    for seed in SEEDS[:4]:
        plain = RoutingMDP.generate(seed=seed, obfuscate=False)
        opaque = RoutingMDP.generate(seed=seed, obfuscate=True)
        ip = {n: i for i, n in enumerate(plain.nodes)}
        io = {n: i for i, n in enumerate(opaque.nodes)}
        assert (sorted((ip[u], ip[v], p) for (u, v), p in plain.p.items())
                == sorted((io[u], io[v], p)
                          for (u, v), p in opaque.p.items())), \
            "obfuscation must be pure relabeling"
    print("PASS v2.1 obfuscation: identical indexed weighted graph")


def test_v21_score_statuses():
    inst = make_pair(SEEDS[2], "silent_break")
    stale = inst.oracle["pre"]["optimal_route"]
    s = score_route(inst.m1, stale, inst.start)
    assert s["status"] == "silent_broken_edge" and not s["valid"]
    assert s["expected_cost"] is None
    hard = make_pair(SEEDS[2], "hard_removal")
    h = score_route(hard.m1, hard.oracle["pre"]["optimal_route"],
                    hard.start)
    assert h["status"] == "illegal_action" and not h["valid"]
    ok = score_route(inst.m1, inst.oracle["post"]["optimal_route"],
                     inst.start)
    assert ok["status"] == "valid_finite" and abs(ok["regret"]) < 1e-9
    bad = score_route(inst.m1, [inst.start], inst.start)
    assert bad["status"] == "invalid_route"
    assert score_route(inst.m1, None, inst.start)["status"] == \
        "invalid_route"
    print("PASS v2.1 score statuses: silent / illegal / valid / invalid "
          "are distinct")


def test_v21_prompt_view():
    inst = make_pair(SEEDS[0], "silent_break")
    ev = paired_evidence(inst, k=4, evidence_seed=3)
    record = json.loads(json.dumps(pair_to_json(inst, ev)))
    view = prompt_view(record, rendering="F3_stats", budget_per_pair=4)
    blob = json.dumps(view)
    for banned in ("counts_", "world_pre", "world_post", "oracle",
                   "\"change\"", "graph_seed"):
        assert banned not in blob, f"leak: {banned}"
    n_pairs_post = len(record["evidence"]["counts_post"])
    assert view["realized"]["post"]["events"] == 4 * n_pairs_post, \
        "exact per-pair budget"
    u, v = inst.change["edge"]
    lab = inst.labels[(u, v)]
    assert f"{u} {lab}: 4 attempts, 0 delivered" in view["evidence"]["post"], \
        "broken pair keeps exactly budget all-drop observations"
    big = prompt_view(record, rendering="F3_stats", budget_per_pair=None)
    assert big["evidence"]["post"] == record["evidence"]["post"]["F3_stats"], \
        "budget=None reproduces the stored rendering"
    try:
        prompt_view(record, rendering="F3_stats", budget_per_pair=5)
        raise AssertionError("B > k must be rejected")
    except ValueError:
        pass
    one = prompt_view(record, rendering="F2_shuffled", periods=("post",),
                      budget_per_pair=4)
    assert "legal_actions_pre" not in one and "pre" not in one["evidence"]
    print("PASS v2.1 prompt_view: no evaluator leak, exact per-pair "
          "budget, stored renderings reproduced at full budget")


def test_v211_matched_mode():
    eligible = 0
    first = None
    for seed in range(40):
        try:
            d = make_pair(seed, "silent_break", deterministic=True,
                          matched=True)
            s = make_pair(seed, "silent_break", deterministic=False,
                          matched=True)
            h = make_pair(seed, "hard_removal", deterministic=False,
                          matched=True)
        except ValueError:
            continue
        eligible += 1
        first = first or d
        assert d.start == s.start == h.start, "matched start"
        assert d.m0.goal == s.m0.goal
        assert d.change["edge"] == s.change["edge"] == h.change["edge"], \
            "matched target across modes and break kinds"
        assert d.change["on_optimal_route"] and s.change["on_optimal_route"]
        assert d.oracle["post"]["solvable"] and s.oracle["post"]["solvable"]
        rec = json.loads(json.dumps(pair_to_json(d)))
        assert rec["params"]["matched"] is True
        try:
            di = make_pair(seed, "irrelevant", deterministic=True,
                           matched=True)
            si = make_pair(seed, "irrelevant", deterministic=False,
                           matched=True)
            assert di.start == si.start
            assert di.change["edge"] == si.change["edge"], \
                "matched irrelevant target"
        except ValueError:
            pass
    assert eligible >= 10, f"matched yield too low in 40 seeds ({eligible})"
    # matched records rebuild and project cleanly
    ev = paired_evidence(first, k=3, evidence_seed=1)
    rec = json.loads(json.dumps(pair_to_json(first, ev)))
    v = prompt_view(rec, "F3_stats", periods=("post",), budget_per_pair=3)
    assert (v["realized"]["post"]["events"]
            == 3 * len(rec["evidence"]["counts_post"]))
    print("PASS v2.1.1 matched mode: shared start/goal/target across "
          "modes; records rebuild (%d/40 seeds eligible)" % eligible)


def test_v21_examples_in_sync():
    import os
    checked = 0
    for det, name in ((True, "example_deterministic_silent_break.json"),
                      (False, "example_stochastic_silent_break.json")):
        if not os.path.exists(name):
            continue
        rec = json.load(open(name))
        inst = make_pair(7, "silent_break", deterministic=det,
                         matched=rec["params"].get("matched", False))
        ev = paired_evidence(inst, k=rec["evidence"]["k_per_pair"],
                             evidence_seed=rec["evidence"]["evidence_seed"])
        assert json.loads(json.dumps(pair_to_json(inst, ev))) == rec, \
            f"{name} is stale -- regenerate with `python3 resource_mdp.py`"
        checked += 1
    print("PASS v2.1 shipped examples regenerate exactly (%d files)"
          % checked)



def test_redirect_keeps_the_menu_identical():
    """The defining property: nothing visible changes except where
    attempts land. A menu diff must reveal nothing."""
    inst = R.make_pair(7, "redirect", matched=True)
    rec = R.pair_to_json(inst, R.paired_evidence(inst, k=5))
    assert rec["legal_actions_pre"] == rec["legal_actions_post"], (
        "redirect leaked through the action menu")
    ch = rec["change"]
    assert ch["mode"] == "redirect"
    assert ch["old_p"] == ch["new_p"], "redirect must preserve the rate"
    assert ch["new_edge"]["from"] == ch["edge"]["from"]
    assert ch["new_edge"]["to"] != ch["edge"]["to"]
    print("PASS redirect: menu identical, success rate preserved, "
          "destination moved")


def test_redirect_shares_the_break_target():
    """redirect joins the break family, so it edits the SAME T* that
    silent_break and hard_removal do for a given seed. Without this the
    conditions are not comparable."""
    for seed in (7, 1, 4):
        try:
            a = R.make_pair(seed, "silent_break", matched=True)
            b = R.make_pair(seed, "redirect", matched=True)
        except ValueError:
            continue
        assert a.change["edge"] == b.change["edge"], (
            f"seed {seed}: redirect target {b.change['edge']} != "
            f"break target {a.change['edge']}")
    print("PASS redirect shares T* with the break family")


def test_redirect_moves_the_optimal_route():
    """It is a route-changing condition, not a control."""
    inst = R.make_pair(7, "redirect", matched=True)
    pre, post = inst.oracle["pre"], inst.oracle["post"]
    assert pre["optimal_route"] != post["optimal_route"]
    assert post["solvable"], "goal must stay reachable"
    print("PASS redirect moves the optimal route and keeps the goal "
          "reachable")


def test_label_inversion_is_period_scoped():
    """Under redirect one action label has two edges. A period-blind
    inversion resolves a period A route with the period B destination,
    which both mis-scores and leaks the change."""
    inst = R.make_pair(7, "redirect", matched=True)
    u, v = inst.change["edge"]
    w = inst.change["new_edge"][1]
    lab = inst.labels[(u, v)]
    assert R.invert_labels(inst.labels, inst.m0)[(u, lab)] == v
    assert R.invert_labels(inst.labels, inst.m1)[(u, lab)] == w
    # and the unscoped form is genuinely ambiguous, which is why callers
    # must pass a world
    assert inst.labels[(u, v)] == inst.labels[(u, w)]
    print("PASS invert_labels is period-scoped under redirect")


def test_redirect_is_deterministic_per_seed():
    inst1 = R.make_pair(7, "redirect", matched=True)
    inst2 = R.make_pair(7, "redirect", matched=True)
    assert inst1.change == inst2.change
    print("PASS redirect is reproducible for a fixed seed")

if __name__ == "__main__":
    test_reproducibility()
    test_deterministic_same_code_path()
    test_conditions()
    test_break_randomization()
    test_balance()
    test_labels()
    test_scoring()
    test_usage_metric_endpoints()
    test_json_roundtrip()
    test_multi_seed_sweep()
    test_v21_shared_break_target()
    test_v21_irrelevant_off_all_optimal_routes()
    test_v21_det_degradation_undefined()
    test_v22_degradation_shares_target()
    test_v21_obfuscation_pure_relabeling()
    test_v21_score_statuses()
    test_v21_prompt_view()
    test_v211_matched_mode()
    test_v21_examples_in_sync()
    test_redirect_keeps_the_menu_identical()
    test_redirect_shares_the_break_target()
    test_redirect_moves_the_optimal_route()
    test_label_inversion_is_period_scoped()
    test_redirect_is_deterministic_per_seed()
    print("\nALL TESTS PASSED")

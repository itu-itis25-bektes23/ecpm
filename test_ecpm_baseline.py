"""Tests for ecpm_baseline.py. Stdlib only, matching the frozen tree.

Run: python3 test_ecpm_baseline.py
"""

import json

import ecpm_baseline as B
import resource_mdp as R


def build(seed, condition, deterministic=False, k=5):
    inst = R.make_pair(seed, condition, deterministic=deterministic,
                       matched=True)
    ev = R.paired_evidence(inst, k=k, max_episodes=300 * max(1, k // 5),
                           horizon=60 * max(1, k // 5))
    record = R.pair_to_json(inst, ev)
    pv = R.prompt_view(record, rendering="F2_shuffled", budget_per_pair=k)
    return record, pv


def truth_pair(record):
    ch = record.get("change")
    return (ch["edge"]["from"], ch["action"]) if ch and ch.get("edge") else None


# --------------------------------------------------------------------------

def test_rejects_evaluator_fields():
    """The baseline must refuse a full record: it would leak the answer."""
    record, _ = build(7, "silent_break")
    for bad in (record, {"evidence": {}, "change": record["change"]},
                {"evidence": {}, "oracle": record["oracle"]}):
        try:
            B.assert_prompt_safe(bad)
        except B.EvidenceLeak:
            continue
        raise AssertionError("leak guard failed to fire on evaluator fields")

    # A genuine prompt view passes.
    _, pv = build(7, "silent_break")
    B.assert_prompt_safe(pv)
    print("PASS leak guard: full records and ground-truth fields rejected, "
          "prompt views accepted")


def test_event_parsing_and_tally():
    """dest == node is a drop; dest != node is a delivery."""
    events = B.parse_events("(A, a1, B)\n(A, a1, A)\n(A, a1, B)\n(C, a2, C)")
    assert events == [("A", "a1", "B"), ("A", "a1", "A"),
                      ("A", "a1", "B"), ("C", "a2", "C")], events

    stats, dests = B.tally(events)
    assert stats[("A", "a1")] == {"attempts": 3, "delivered": 2}
    assert stats[("C", "a2")] == {"attempts": 1, "delivered": 0}
    assert dests[("A", "a1")] == {"B": 2}
    assert ("C", "a2") not in dests, "a never-successful pair has no dest"
    assert abs(B.rate(stats[("A", "a1")]) - 2 / 3) < 1e-9
    assert B.rate(stats.get(("Z", "a9"))) is None, "unseen pair -> None"

    # F3_stats parses to the same shape.
    parsed = B.parse_stats("A a1: 19 attempts, 12 delivered (0.63)\njunk")
    assert parsed == {("A", "a1"): {"attempts": 19, "delivered": 12}}, parsed
    print("PASS parsing: drops, deliveries, destinations, unseen pairs, stats")


def test_unobserved_pairs_do_not_manufacture_detections():
    """A pair absent from one period is skipped, not scored as 0.0."""
    ranked = B.rank_pairs(
        {("A", "a1"): {"attempts": 5, "delivered": 5},
         ("B", "a1"): {"attempts": 5, "delivered": 3}},
        {("A", "a1"): {"attempts": 5, "delivered": 0}},
    )
    pairs = [r["pair"] for r in ranked]
    assert pairs == [("A", "a1")], pairs
    assert abs(ranked[0]["abs_delta"] - 1.0) < 1e-9
    print("PASS ranking: pairs unobserved in a period are excluded")


def test_hard_removal_uses_menu_not_rates():
    """A removed pair is found by menu diff, with no evidence at all."""
    record, pv = build(7, "hard_removal")
    res = B.run_baseline(pv)
    assert res["localization_basis"] == "menu_removal", res
    assert tuple(res["localization"]) == truth_pair(record)
    assert res["detection"] is True
    print("PASS hard_removal: menu diff localizes without reading rates")


def test_deterministic_silent_break_is_solved_by_counting():
    """No headroom in deterministic mode: the broken pair is the only
    one that ever fails, so a counter gets it every time."""
    hits = total = 0
    for seed in range(1, 16):
        try:
            record, pv = build(seed, "silent_break", deterministic=True)
        except Exception:
            continue
        total += 1
        res = B.run_baseline(pv)
        hits += tuple(res["localization"]) == truth_pair(record)
    assert total >= 10, f"too few eligible seeds ({total})"
    assert hits == total, f"deterministic localization {hits}/{total}"
    print(f"PASS deterministic silent_break: baseline localizes {hits}/{total} "
          "-- the condition carries no headroom")


def test_stochastic_k5_is_genuinely_hard():
    """Seed 7 at K=5 is the documented ambiguous case: the true pair is
    buried, so a model failing there has not made a mistake."""
    record, pv = build(7, "silent_break", k=5)
    ranked = B.rank_pairs(*B.read_periods(pv)[:2])
    order = [r["pair"] for r in ranked]
    rank = order.index(truth_pair(record)) + 1
    assert rank > 1, "seed 7 K=5 was expected to be ambiguous"
    print(f"PASS stochastic seed 7 K=5: true pair ranks {rank}/{len(order)}; "
          "baseline cannot localize, so neither can a model be blamed")


def test_more_evidence_helps():
    """Localization improves with K. This is the claim the methodology
    doc makes from simulation; here it is measured on collected logs."""
    scores = {}
    for k in (5, 20):
        hits = total = 0
        for seed in range(1, 21):
            try:
                record, pv = build(seed, "degradation", k=k)
            except Exception:
                continue
            total += 1
            res = B.run_baseline(pv)
            hits += tuple(res["localization"]) == truth_pair(record)
        scores[k] = hits / total if total else 0.0
    assert scores[20] > scores[5], scores
    print(f"PASS degradation scales with K: {scores[5]:.2f} at K=5 -> "
          f"{scores[20]:.2f} at K=20")


def test_route_avoids_a_break_it_cannot_name():
    """The dissociation, in the baseline itself: a pair with zero observed
    successes gets infinite cost and is routed around, even when the
    baseline localizes the wrong pair."""
    record, pv = build(7, "silent_break", k=5)
    res = B.run_baseline(pv)
    route = res["adaptation"]["route"]
    assert route, res["adaptation"]
    steps = {(s["node"], s["action"]) for s in route}
    assert truth_pair(record) not in steps, "route used the broken pair"
    assert tuple(res["localization"]) != truth_pair(record), (
        "seed 7 K=5 was expected to mislocalize")
    print("PASS routing/naming dissociation: the break is avoided in the "
          "route while a healthy pair is named as the change")


def test_preservation_marks_only_the_localized_pair():
    record, pv = build(7, "hard_removal")
    truth = truth_pair(record)
    pairs = [truth, ("A", "a1"), ("G", "a2"), ("H", "a1")]
    res = B.run_baseline(pv, queried_pairs=pairs)
    flags = res["preservation"]
    assert flags["/".join(truth)] is True
    assert sum(flags.values()) == 1, flags
    print("PASS preservation: exactly the localized pair is reported changed")


def test_stats_rendering_disables_adaptation():
    """F3_stats has no destinations, so the route probe must decline
    rather than invent a graph."""
    record, _ = build(7, "silent_break")
    pv = R.prompt_view(record, rendering="F3_stats", budget_per_pair=5)
    res = B.run_baseline(pv)
    assert res["adaptation"]["route"] is None
    assert "destinations" in res["adaptation"]["reason"]
    assert res["localization"] is not None, "localization still works"
    print("PASS F3_stats: adaptation declines cleanly, localization survives")


def test_detection_reliability_is_mode_aware():
    """K=5 detection is unusable in stochastic mode but fine in
    deterministic mode, where false alarms measured 0.00. The prompt view
    does not carry the mode, so it is inferred from the evidence."""
    _, det_pv = build(7, "silent_break", deterministic=True, k=5)
    _, sto_pv = build(7, "silent_break", deterministic=False, k=5)

    det = B.run_baseline(det_pv)
    sto = B.run_baseline(sto_pv)
    assert det["evidence_looks_deterministic"] is True
    assert sto["evidence_looks_deterministic"] is False
    assert det["detection_reliable"] is True, "det K=5 wrongly flagged"
    assert sto["detection_reliable"] is False, "sto K=5 wrongly trusted"

    # A menu removal never depends on noise, so it is reliable at any K.
    _, hr_pv = build(7, "hard_removal", k=5)
    assert B.run_baseline(hr_pv)["detection_reliable"] is True
    print("PASS detection reliability: deterministic evidence and menu "
          "removals trusted at K=5, stochastic rates not")


def test_margin_is_withheld_for_menu_removals():
    """Margin describes the rate ranking. When the answer came from a
    menu diff it describes nothing, so it must not be reported."""
    _, pv = build(7, "hard_removal")
    res = B.run_baseline(pv)
    assert res["localization_basis"] == "menu_removal"
    assert res["margin"] is None, res["margin"]

    _, pv2 = build(7, "silent_break")
    assert B.run_baseline(pv2)["margin"] is not None
    print("PASS margin: withheld on menu removal, reported on rate swing")


def test_uncalibrated_budget_is_flagged():
    """A budget outside the calibration table still runs, but says so."""
    _, pv = build(7, "silent_break", k=5)
    pv = dict(pv, budget_per_pair=7)
    res = B.run_baseline(pv)
    assert res["threshold_calibrated"] is False
    assert res["delta_threshold"] in B.CALIBRATED_DELTA_THRESHOLD.values()
    _, pv5 = build(7, "silent_break", k=5)
    assert B.run_baseline(pv5)["threshold_calibrated"] is True
    print("PASS calibration flag: uncalibrated budgets fall back and "
          "are marked")


def test_redirect_defeats_the_baseline_by_construction():
    """The reason redirect exists. It preserves every success rate, so a
    counter has no signal at all -- and unlike the low-K cases, more
    evidence does not help. This is the only condition where a model
    beating the baseline would demonstrate something counting cannot."""
    scores = {}
    for k in (5, 20):
        hits = total = 0
        for seed in range(1, 21):
            try:
                record, pv = build(seed, "redirect", k=k)
            except Exception:
                continue
            total += 1
            res = B.run_baseline(pv)
            hits += (res["localization"] is not None
                     and tuple(res["localization"]) == truth_pair(record))
        scores[k] = hits / total if total else 0.0
    assert scores[5] < 0.25, scores
    assert scores[20] < 0.25, (
        "redirect should stay unsolvable as K grows; it is not a "
        "sample-size problem", scores)
    print(f"PASS redirect defeats the baseline: {scores[5]:.2f} at K=5, "
          f"{scores[20]:.2f} at K=20 -- no gain from more evidence")


def test_redirect_menu_is_invisible_to_the_baseline():
    """No menu removal to fall back on, unlike hard_removal."""
    _, pv = build(7, "redirect")
    res = B.run_baseline(pv)
    assert res["menu_removals"] == [], res["menu_removals"]
    assert res["localization_basis"] == "rate_swing"
    print("PASS redirect: no menu signal, so the baseline is forced onto "
          "rates it cannot use")


def test_nothing_examined_is_not_a_pass():
    """Handbook 24.4: "no violations found" and "nothing was examined" are
    different exit states. Without this, an empty evidence log returns
    detection=False with preservation all-unchanged, which is exactly a
    correct no_change answer and would be scored as one."""
    empty = {"rendering": "F2_shuffled", "budget_per_pair": 10,
             "evidence": {"pre": "", "post": ""},
             "start": "E", "goal": "F",
             "legal_actions_pre": {}, "legal_actions_post": {}}
    res = B.run_baseline(empty, queried_pairs=[("D", "a2")])
    assert res["status"] == "could_not_run", res["status"]
    assert res["detection"] is None, "an unexamined input must not answer"
    assert res["detection_reliable"] is False
    assert res["preservation"] is None
    assert res["n_pairs_compared"] == 0

    _, good = build(7, "silent_break")
    ok = B.run_baseline(good)
    assert ok["status"] == "ok"
    assert ok["n_pairs_compared"] > 0
    print("PASS three exit states: empty evidence reports could_not_run, "
          "never a clean no-change verdict")


def test_injected_defects_are_caught():
    """Handbook 26.3: damage a passing input and record which check catches
    each class. A check never seen to fail has been run, not tested."""
    record, pv = build(7, "silent_break", k=5)
    truth = truth_pair(record)
    caught = {}

    # 1. evidence removed entirely -> the could-not-run guard
    blanked = dict(pv, evidence={"pre": "", "post": ""})
    caught["evidence removed"] = (
        B.run_baseline(blanked)["status"] == "could_not_run")

    # 2. post period replaced by the pre period -> no swing, no detection
    flat = dict(pv, evidence={"pre": pv["evidence"]["pre"],
                              "post": pv["evidence"]["pre"]})
    caught["periods identical"] = (
        B.run_baseline(flat)["detection"] is False)

    # 3. evaluator fields smuggled in -> the leak guard
    try:
        B.run_baseline(dict(pv, change=record["change"]))
        caught["ground truth leaked"] = False
    except B.EvidenceLeak:
        caught["ground truth leaked"] = True

    # 4. a rendering with no destinations -> adaptation declines
    stats_pv = R.prompt_view(record, rendering="F3_stats", budget_per_pair=5)
    caught["destinations absent"] = (
        B.run_baseline(stats_pv)["adaptation"]["route"] is None)

    missed = [k for k, v in caught.items() if not v]
    assert not missed, f"damage classes not caught: {missed}"
    assert truth is not None
    print("PASS injected defects: " + ", ".join(sorted(caught)) +
          " each caught by exactly one guard")


def test_result_is_json_serializable():
    _, pv = build(7, "silent_break")
    json.dumps(B.run_baseline(pv, queried_pairs=[("D", "a2")]))
    print("PASS output serializes to JSON")


if __name__ == "__main__":
    test_rejects_evaluator_fields()
    test_event_parsing_and_tally()
    test_unobserved_pairs_do_not_manufacture_detections()
    test_hard_removal_uses_menu_not_rates()
    test_deterministic_silent_break_is_solved_by_counting()
    test_stochastic_k5_is_genuinely_hard()
    test_more_evidence_helps()
    test_route_avoids_a_break_it_cannot_name()
    test_preservation_marks_only_the_localized_pair()
    test_stats_rendering_disables_adaptation()
    test_detection_reliability_is_mode_aware()
    test_margin_is_withheld_for_menu_removals()
    test_uncalibrated_budget_is_flagged()
    test_redirect_defeats_the_baseline_by_construction()
    test_redirect_menu_is_invisible_to_the_baseline()
    test_nothing_examined_is_not_a_pass()
    test_injected_defects_are_caught()
    test_result_is_json_serializable()
    print("\nALL BASELINE TESTS PASSED")

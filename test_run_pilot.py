#!/usr/bin/env python3
"""Acceptance tests for the additive ICL two-response protocol."""

import hashlib
import json
import os
import tempfile
from types import SimpleNamespace

import run_pilot
from ecpm_parser import (diagnose_route_beliefs, parse_icl_turn_a,
                         parse_icl_turn_b, score_icl_beliefs,
                         score_icl_localization)
from resource_mdp import prompt_view
from run_pilot import (COST_STATUSES, ICL_LEVELS, SCENARIO_DEFAULTS, SCENARIOS,
                       _call_icl_provider_once, _cost_provenance,
                       _dry_run_icl_answer, _icl_run_id, _icl_run_identity,
                       _reasoning_evidence, build_icl_prompt, build_record,
                       context_block, context_block_a, deterministic_gate,
                       empirical_table_from_visible, endpoint_provenance,
                       first_deterministic_gate_seed, icl_level_order,
                       protocol_target_pair, queried_pairs_for,
                       queried_pairs_for_icl, raw_visible_rows,
                       reasoning_provenance, sampling_seed_provenance,
                       reveal_block_b, run_icl_two_response_once,
                       run_icl_two_response_suite, score_any,
                       visible_transition_stats, write_icl_summary)


def scenario(seed=8, condition="silent_break", k=10, budget=10):
    sc = dict(SCENARIO_DEFAULTS)
    sc.update({"name": "icl_det_gate_seed8", "seed": seed,
               "condition": condition, "k": k, "budget": budget})
    if condition == "no_change":
        sc["probes"] = ("detection", "preservation", "adaptation")
    return sc


def args(tag="test"):
    return SimpleNamespace(
        provider="dry-run", model="dry-run", temperature=0.0,
        top_p=None, top_k=None,
        max_tokens=4096, timeout=120, reasoning_mode="off",
        reasoning_control_json=None, reasoning_control_source=None,
        sampling_seed_support="auto",
        thinking_budget=0, base_url="http://localhost:1234/v1",
        azure_endpoint="", api_version="2024-06-01", tag=tag,
        pilot_type="passive", repeats=3, sampling_seeds=[0, 1, 2])


def record_and_view(sc=None):
    sc = sc or scenario()
    record = build_record(sc, deterministic=True)
    view = prompt_view(record, rendering="F2_shuffled",
                       periods=("pre", "post"),
                       budget_per_pair=sc["budget"], budget_seed=0)
    return sc, record, view


def test_legacy_prompt_and_scorer_regression():
    sc = dict(SCENARIO_DEFAULTS)
    sc.update(SCENARIOS["seed7_silent_break"])
    sc["name"] = "seed7_silent_break"
    record = build_record(sc, deterministic=True)
    view = prompt_view(record, rendering=sc["rendering"],
                       periods=("pre", "post"),
                       budget_per_pair=sc["budget"])
    expected = (
        "023b0581f9489e673cc63a2ce43f00a6d46a3f6a52689fbd18da74056fad4999",
        "56349b55fed1bdb790af36cb0b9a97a4de6aff3d7f392ef454f91d4311ebd9f4",
        "42b4b00a315944b96f750a75abd21e792fffde210e957014d854bfda5fb01bf8",
    )
    actual = tuple(hashlib.sha256(text.encode()).hexdigest() for text in
                   (context_block(view), context_block_a(view),
                    reveal_block_b(view)))
    assert actual == expected
    queried = queried_pairs_for(record, sc)
    scored = score_any(record, "adaptation",
                       run_pilot.dry_run_answer(record, "adaptation", queried),
                       queried)["scored"]
    assert scored["status"] == "valid_finite"
    assert scored["regret"] == 0.0 and scored["is_optimal"]
    print("PASS legacy prompt hashes and frozen scorer regression")


def test_levels_share_visible_evidence_and_raw_order():
    sc, record, view = record_and_view()
    queried = queried_pairs_for_icl(record, sc)
    prompts = {level: {period: build_icl_prompt(
        view, level, period, queried) for period in ("pre", "post")}
        for level in ICL_LEVELS}
    for period in ("pre", "post"):
        raw = "\n".join(raw_visible_rows(view, period))
        assert raw in prompts["explained_logs"][period]
        assert raw in prompts["minimal_logs"][period]
    assert "Each action has one destination" in prompts["empirical_table"]["pre"]
    assert "Each action has one destination" in prompts["explained_logs"]["pre"]
    for level in ICL_LEVELS:
        assert "destination is the node the action is estimated to reach" in \
            prompts[level]["pre"]
        assert "p_success is the estimated probability" in prompts[level]["pre"]
        for period in ("pre", "post"):
            assert ("A route lists actions only. Its first item must be at "
                    "Start. The successful destination of its final action "
                    "must be Goal. Do not add a route item for Goal after "
                    "arrival.") in prompts[level][period]
            assert "finish at Goal" not in prompts[level][period]
    minimal = prompts["minimal_logs"]["pre"]
    assert "failed attempt" not in minimal and "retried" not in minimal
    print("PASS all levels share evidence; Levels 2/3 have byte-identical rows")


def test_icl_route_terminal_action_contract():
    sc, record, _ = record_and_view()
    queried = queried_pairs_for_icl(record, sc)
    for period, parser in (("pre", parse_icl_turn_a),
                           ("post", parse_icl_turn_b)):
        payload = json.loads(_dry_run_icl_answer(record, queried, period))
        parsed = parser(json.dumps(payload))
        route = parsed["route"]["route"]
        final = route[-1]
        truth = {(edge["from"], edge["action"]): edge["to"]
                 for edge in record[f"world_{period}"]["edges"]}
        assert truth[(final["node"], final["action"])] == record["goal"]

        payload["route"].append({"node": record["goal"], "action": None})
        rejected = parser(json.dumps(payload))["route"]
        assert rejected == {"status": "invalid_object", "route": []}
    print("PASS ICL routes end with the arrival action; Goal items stay invalid")


def test_empirical_table_uses_visible_inputs_only():
    rows = ["[A, a1, B]", "[A, a1, A]", "[A, a1, B]"]
    current = {"A": ["a1"], "B": []}
    prior = {"A": ["a1", "a2"], "B": []}
    table = empirical_table_from_visible(rows, current, prior)
    assert '3 | {"A": 1, "B": 2} | {"A": 0.3333, "B": 0.6667}' in table
    assert "A | a2 | false | 0 | {} | {}" in table
    assert "oracle" not in table and "true_p" not in table
    stats = visible_transition_stats(rows, current, prior)
    assert stats[("A", "a1")]["p_success"] == 2 / 3
    print("PASS empirical table is derived only from visible rows and menus")


def test_period_boundary_and_prompt_neutrality():
    sc, record, view = record_and_view()
    queried = queried_pairs_for_icl(record, sc)
    first = build_icl_prompt(view, "explained_logs", "pre", queried)
    later = build_icl_prompt(view, "explained_logs", "post", queried)
    assert "Period B" not in first
    assert "may or may not differ" in later
    for forbidden in ("change occurred", "has changed", "target", "control",
                      "intervention", "scenario type"):
        assert forbidden not in later.lower()
    sentinel = json.loads(json.dumps(view))
    sentinel["evidence"]["post"] = "(SECRET, a9, SECRET)"
    sentinel["legal_actions_post"] = {"SECRET": ["a9"]}
    assert "SECRET" not in build_icl_prompt(
        sentinel, "explained_logs", "pre", queried)
    assert len(queried) == 5 and len({(q["node"], q["action"])
                                     for q in queried}) == 5
    print("PASS Period A excludes B; Turn B is neutral; pair roles never leak")


def test_five_pairs_stable_and_no_change_counterfactual():
    sc, record, _ = record_and_view()
    expected = queried_pairs_for_icl(record, sc)
    assert len(expected) == 5
    for _repeat in range(3):
        for _level in ICL_LEVELS:
            assert queried_pairs_for_icl(record, sc) == expected
    target = protocol_target_pair(record, sc)
    assert sum((q["node"], q["action"]) == target for q in expected) == 1

    nc_sc, nc_record, _ = record_and_view(scenario(condition="no_change"))
    nc_target = protocol_target_pair(nc_record, nc_sc)
    sibling = build_record(scenario(), deterministic=True)
    sibling_target = (sibling["change"]["edge"]["from"],
                      sibling["change"]["action"])
    assert nc_target == sibling_target
    print("PASS fixed ordered five pairs include T* and no-change sibling T*")


def test_availability_and_no_change_dry_answers():
    hard_sc, hard, hard_view = record_and_view(
        scenario(condition="hard_removal"))
    queried = queried_pairs_for_icl(hard, hard_sc)
    target = protocol_target_pair(hard, hard_sc)
    answer = json.loads(_dry_run_icl_answer(hard, queried, "post"))
    row = next(row for row in answer["pairs"]
               if (row["node"], row["action"]) == target)
    assert row["available"] is False
    assert row["destination"] is None and row["p_success"] is None
    parsed = parse_icl_turn_b(json.dumps(answer))
    visible = visible_transition_stats(
        raw_visible_rows(hard_view, "post"),
        hard["legal_actions_post"], hard["legal_actions_pre"])
    scored = score_icl_beliefs(
        hard, parsed["beliefs"], queried, "post", visible)
    assert scored["status"] == "ok" and scored["accuracy"] == 1.0
    assert scored["n_destination_scored"] == 4
    assert scored["destination_accuracy"] == 1.0

    silent_sc, silent, _ = record_and_view()
    queried = queried_pairs_for_icl(silent, silent_sc)
    target = protocol_target_pair(silent, silent_sc)
    answer = json.loads(_dry_run_icl_answer(silent, queried, "post"))
    row = next(row for row in answer["pairs"]
               if (row["node"], row["action"]) == target)
    assert row["available"] is True and row["p_success"] == 0.0

    nc_sc, no_change, _ = record_and_view(scenario(condition="no_change"))
    queried = queried_pairs_for_icl(no_change, nc_sc)
    parsed = parse_icl_turn_b(_dry_run_icl_answer(
        no_change, queried, "post"))
    assert parsed["detection"]["changed"] is False
    assert parsed["localization"]["changed_pair"] is None
    print("PASS silent/removal availability and no-change null localization")


def _truth_pair(record, query, period, changed=False):
    truth = {(e["from"], e["action"]): e
             for e in record[f"world_{period}"]["edges"]}
    key = (query["node"], query["action"])
    edge = truth.get(key)
    row = {**query, "available": edge is not None,
           "destination": edge["to"] if edge else None,
           "p_success": edge["p"] if edge else None}
    if period == "post":
        row["changed"] = changed
    return row


def test_combined_parser_component_independence_and_pair_errors():
    _, record, _ = record_and_view()
    route = [{"node": node, "action": action}
             for node, action in zip(
                 record["oracle"]["pre"]["optimal_route"],
                 record["oracle"]["pre"]["optimal_actions"])]
    parsed = parse_icl_turn_a(json.dumps(
        {"pairs": [{"node": "G"}], "route": route}))
    assert parsed["beliefs"]["status"] == "invalid_object"
    assert parsed["route"]["status"] == "ok"

    queries = [{"node": e["from"], "action": e["action"]}
               for e in record["world_pre"]["edges"][:5]]
    rows = [_truth_pair(record, query, "pre") for query in queries]
    assert score_icl_beliefs(
        record, {"status": "ok", "pairs": rows}, queries,
        "pre")["accuracy"] == 1.0
    assert score_icl_beliefs(
        record, {"status": "ok", "pairs": rows + [rows[0]]}, queries,
        "pre")["status"] == "duplicate_pair"
    assert score_icl_beliefs(
        record, {"status": "ok", "pairs": rows[:-1]}, queries,
        "pre")["status"] == "missing_pair"
    unknown = [dict(rows[0], action="a99"), *rows[1:]]
    assert score_icl_beliefs(
        record, {"status": "ok", "pairs": unknown}, queries,
        "pre")["status"] == "unknown_pair"

    unavailable_bad = json.dumps({"pairs": [{
        "node": "G", "action": "a1", "available": False,
        "destination": "E", "p_success": None}], "route": []})
    assert parse_icl_turn_a(unavailable_bad)["beliefs"]["status"] == \
        "invalid_unavailable"
    out_of_range = json.dumps({"pairs": [{
        "node": "G", "action": "a1", "available": True,
        "destination": "E", "p_success": 1.1}], "route": []})
    assert parse_icl_turn_a(out_of_range)["beliefs"]["status"] == \
        "out_of_range"
    print("PASS combined parser preserves valid route and handles pair errors")


def test_visible_and_truth_probability_mae():
    _, record, _ = record_and_view()
    edge = record["world_pre"]["edges"][0]
    query = {"node": edge["from"], "action": edge["action"]}
    row = _truth_pair(record, query, "pre")
    row["p_success"] = 0.4
    visible = {(query["node"], query["action"]): {"p_success": 0.4}}
    scored = score_icl_beliefs(
        record, {"status": "ok", "pairs": [row]}, [query], "pre", visible)
    assert scored["p_mae_visible"] == 0.0
    assert scored["p_mae_truth"] == 0.6
    print("PASS visible-frequency and evaluator-truth MAE are separate")


def test_nullable_localization_and_route_belief_diagnostics():
    _, changed, _ = record_and_view()
    target = {"node": changed["change"]["edge"]["from"],
              "action": changed["change"]["action"]}
    scored = score_icl_localization(
        changed, {"status": "ok", "changed": True},
        {"status": "ok", "changed_pair": target})
    assert scored["detection_correct"] and scored["localization_correct"]
    _, no_change, _ = record_and_view(scenario(condition="no_change"))
    scored = score_icl_localization(
        no_change, {"status": "ok", "changed": False},
        {"status": "ok", "changed_pair": None})
    assert scored["detection_correct"]
    assert scored["localization_applicable"] is False
    assert scored["localization_correct"] is None
    assert scored["null_changed_pair_correct"] is True

    parsed = parse_icl_turn_b(json.dumps({
        "changed": False, "changed_pair": None, "pairs": [], "route": []}))
    assert parsed["localization"] == {"status": "ok", "changed_pair": None}
    invalid = parse_icl_turn_b(json.dumps({
        "changed": False, "changed_pair": target, "pairs": [], "route": []}))
    assert invalid["localization"]["status"] == "invalid_object"

    route = {"status": "ok", "route": [
        {"node": "G", "action": "a1"},
        {"node": "E", "action": "a2"}]}
    beliefs = {"status": "ok", "pairs": [{
        "node": "E", "action": "a2", "available": True,
        "destination": "B", "p_success": 1.0}]}
    diagnosed = diagnose_route_beliefs(route, beliefs, "D")
    assert diagnosed["status"] == "route_inconsistent"
    assert diagnosed["unresolved_pairs"] == [{"node": "G", "action": "a1"}]
    assert len(diagnosed["pairs"]) == 2
    beliefs["pairs"][0]["destination"] = "D"
    assert diagnose_route_beliefs(route, beliefs, "D")["status"] == \
        "route_unresolvable"
    print("PASS nullable localization and route belief diagnostics")


def test_gate_and_rotation():
    gate_scenario = SCENARIOS["icl_det_gate_seed8"]
    assert gate_scenario == {
        "condition": "silent_break", "seed": 8, "k": 10, "budget": 10,
        "variants": ("det",)}
    rejected = deterministic_gate(1)
    accepted = deterministic_gate(8)
    assert not rejected["eligible"]
    assert "pre_optimum_unique" in rejected["reasons"]
    assert accepted["eligible"]
    assert accepted["pre_route"] == ["G", "E", "D"]
    assert accepted["post_route"] == ["G", "B", "H", "D"]
    assert accepted["target"] == {"node": "G", "action": "a1",
                                  "destination": "E"}
    assert first_deterministic_gate_seed()["seed"] == 8
    assert icl_level_order(1) == ICL_LEVELS
    assert icl_level_order(2) == ICL_LEVELS[1:] + ICL_LEVELS[:1]
    assert icl_level_order(3) == ICL_LEVELS[2:] + ICL_LEVELS[:2]
    print("PASS deterministic gate selects seed 8 and level order rotates")


def test_provider_sampling_and_reasoning_controls():
    dry = args()
    sampling = sampling_seed_provenance(dry, 7)
    assert sampling["sampling_seed_status"] == "not_applied_dry_run"
    assert sampling["top_p"] is None and sampling["top_k"] is None
    provenance = reasoning_provenance(dry)
    assert provenance["status"] == "not_applied_dry_run"
    assert provenance["request_fields"] == {}

    openai = args()
    openai.provider = "openai"
    openai.model = "test-model"
    openai.base_url = "https://api.openai.com/v1"
    openai.reasoning_mode = "unspecified"
    sampling = sampling_seed_provenance(openai, 7)
    assert sampling["sampling_seed_status"] == "supported"

    anthropic = args()
    anthropic.provider = "anthropic"
    anthropic.model = "test-model"
    anthropic.reasoning_mode = "unspecified"
    unsupported = sampling_seed_provenance(anthropic, 7)
    assert unsupported["sampling_seed_status"] == "unsupported"

    azure = args()
    azure.provider = "azure"
    azure.model = "deployment"
    azure.azure_endpoint = "https://example.openai.azure.com"
    azure.reasoning_mode = "unspecified"
    assert sampling_seed_provenance(
        azure, 7)["sampling_seed_status"] == "unsupported"
    azure.sampling_seed_support = "supported"
    azure_sampling = sampling_seed_provenance(azure, 7)
    assert azure_sampling["sampling_seed_status"] == "supported"

    compatible = args()
    compatible.provider = "openai"
    compatible.reasoning_mode = "unspecified"
    assert sampling_seed_provenance(
        compatible, 7)["sampling_seed_status"] == "unsupported"

    real_off = args()
    real_off.provider = "openai"
    try:
        reasoning_provenance(real_off)
        raise AssertionError("real off must require an explicit control")
    except ValueError as exc:
        assert "reasoning-control-json" in str(exc)
    real_off.reasoning_control_json = '{"reasoning_effort":"none"}'
    try:
        reasoning_provenance(real_off)
        raise AssertionError("real off must require a control source")
    except ValueError as exc:
        assert "reasoning-control-source" in str(exc)
    real_off.reasoning_control_source = "OpenAI Chat API documentation"
    real_off.top_p = 0.95
    real_off.top_k = 64
    real_off_control = reasoning_provenance(real_off)
    assert real_off_control["request_fields"] == {
        "reasoning_effort": "none"}
    assert real_off_control["operator_json"] == \
        '{"reasoning_effort":"none"}'
    assert real_off_control["semantics_verified_by_runner"] is False
    real_off.reasoning_control_json = '{"model":"override"}'
    try:
        reasoning_provenance(real_off)
        raise AssertionError("control must not override request identity")
    except ValueError as exc:
        assert "cannot override" in str(exc)

    local = args()
    local.provider = "openai"
    local.model = "gemma"
    local.reasoning_mode = "off"
    local.reasoning_control_json = \
        '{"chat_template_kwargs":{"enable_thinking":false}}'
    local.reasoning_control_source = "LM Studio model configuration"
    local_control = reasoning_provenance(local)
    assert local_control["source"] == "LM Studio model configuration"
    assert local_control["request_fields"]["chat_template_kwargs"] == {
        "enable_thinking": False}

    captured = []
    original_urlopen = run_pilot.urllib.request.urlopen
    old_key = os.environ.get("ANTHROPIC_API_KEY")
    old_azure_key = os.environ.get("AZURE_OPENAI_API_KEY")

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return json.dumps(self.payload).encode()

    def fake_urlopen(request, timeout):
        body = json.loads(request.data)
        captured.append(body)
        if "anthropic.com" in request.full_url:
            return FakeResponse({"content": [{"type": "text", "text": "{}"}],
                                 "stop_reason": "end_turn", "usage": {}})
        return FakeResponse({"choices": [{"message": {"content": "{}"},
                                          "finish_reason": "stop"}],
                             "usage": {"completion_tokens_details": {
                                 "reasoning_tokens": 2}}})

    try:
        run_pilot.urllib.request.urlopen = fake_urlopen
        controlled = _call_icl_provider_once(
            real_off, [{"role": "user", "content": "x"}],
            sampling_seed_provenance(real_off, 7), real_off_control)
        assert controlled["reasoning_evidence"] == "true"
        assert controlled["reasoning_control_violation"] is True
        _call_icl_provider_once(
            openai, [{"role": "user", "content": "x"}], sampling,
            reasoning_provenance(openai))
        os.environ["ANTHROPIC_API_KEY"] = "test-only"
        _call_icl_provider_once(
            anthropic, [{"role": "user", "content": "x"}], unsupported,
            reasoning_provenance(anthropic))
        os.environ["AZURE_OPENAI_API_KEY"] = "test-only"
        _call_icl_provider_once(
            azure, [{"role": "user", "content": "x"}], azure_sampling,
            reasoning_provenance(azure))
        run_pilot.call_openai(
            "legacy-model", [{"role": "user", "content": "x"}], 17,
            "http://localhost:1234/v1", 120)
    finally:
        run_pilot.urllib.request.urlopen = original_urlopen
        if old_key is None:
            os.environ.pop("ANTHROPIC_API_KEY", None)
        else:
            os.environ["ANTHROPIC_API_KEY"] = old_key
        if old_azure_key is None:
            os.environ.pop("AZURE_OPENAI_API_KEY", None)
        else:
            os.environ["AZURE_OPENAI_API_KEY"] = old_azure_key
    assert captured[0] == {
        "model": "dry-run", "messages": [{"role": "user", "content": "x"}],
        "max_tokens": 4096, "temperature": 0.0,
        "top_p": 0.95, "top_k": 64,
        "reasoning_effort": "none"}
    assert captured[1] == {
        "model": "test-model", "messages": [{"role": "user", "content": "x"}],
        "max_tokens": 4096, "temperature": 0.0, "seed": 7}
    assert captured[2] == {
        "model": "test-model", "messages": [{"role": "user", "content": "x"}],
        "max_tokens": 4096, "temperature": 0.0}
    assert captured[3] == {
        "messages": [{"role": "user", "content": "x"}],
        "max_tokens": 4096, "temperature": 0.0, "seed": 7}
    assert captured[4] == {
        "model": "legacy-model",
        "messages": [{"role": "user", "content": "x"}],
        "max_tokens": 17, "temperature": 0}
    assert "top_p" not in captured[1] and "top_k" not in captured[1]

    for field, value in (("top_p", 0), ("top_p", 1.01),
                         ("top_k", 0), ("top_k", 1.5)):
        invalid = args()
        setattr(invalid, field, value)
        try:
            sampling_seed_provenance(invalid, 0)
            raise AssertionError(f"invalid {field} must be rejected")
        except ValueError:
            pass
    assert _reasoning_evidence("openai", {"usage": {
        "completion_tokens_details": {"reasoning_tokens": 0}}}, None) == \
        "false"
    assert _reasoning_evidence("openai", {"usage": {}}, None) == "unknown"
    print("PASS supported/unsupported seeds and explicit reasoning controls")


def test_cost_and_endpoint_provenance():
    assert COST_STATUSES == ("exact", "estimated", "unavailable",
                             "local_unpriced")
    dry = args()
    assert _cost_provenance(dry) == {
        "status": "unavailable", "amount": None,
        "reason": "dry_run_no_provider_call"}
    local = args()
    local.provider = "openai"
    assert _cost_provenance(local)["status"] == "local_unpriced"
    external = args()
    external.provider = "openai"
    external.base_url = "https://api.openai.com/v1"
    external.reasoning_mode = "unspecified"
    assert _cost_provenance(external)["status"] == "unavailable"

    sc, record, view = record_and_view()
    queried = queried_pairs_for_icl(record, sc)
    prompt_a = build_icl_prompt(view, "minimal_logs", "pre", queried)
    prompt_b = build_icl_prompt(view, "minimal_logs", "post", queried)
    sampling = sampling_seed_provenance(external, 0)
    reasoning = reasoning_provenance(external)
    identity_a = _icl_run_identity(
        sc, True, external, "minimal_logs", 1, sampling, reasoning,
        prompt_a, prompt_b, queried)
    with_top_p = SimpleNamespace(**vars(external))
    with_top_p.top_p = 0.95
    identity_top_p = _icl_run_identity(
        sc, True, with_top_p, "minimal_logs", 1,
        sampling_seed_provenance(with_top_p, 0),
        reasoning_provenance(with_top_p), prompt_a, prompt_b, queried)
    with_top_k = SimpleNamespace(**vars(external))
    with_top_k.top_k = 64
    identity_top_k = _icl_run_identity(
        sc, True, with_top_k, "minimal_logs", 1,
        sampling_seed_provenance(with_top_k, 0),
        reasoning_provenance(with_top_k), prompt_a, prompt_b, queried)
    assert identity_a != identity_top_p != identity_top_k
    assert _icl_run_id(identity_a) != _icl_run_id(identity_top_p)
    assert _icl_run_id(identity_a) != _icl_run_id(identity_top_k)
    other = SimpleNamespace(**vars(external))
    other.base_url = "https://example.com/v1"
    identity_b = _icl_run_identity(
        sc, True, other, "minimal_logs", 1,
        sampling_seed_provenance(other, 0), reasoning_provenance(other),
        prompt_a, prompt_b, queried)
    assert identity_a["endpoint"] != identity_b["endpoint"]
    azure = args()
    azure.provider = "azure"
    first = endpoint_provenance(azure)
    azure.api_version = "2025-01-01"
    assert endpoint_provenance(azure) != first
    print("PASS cost statuses and endpoint/API identity provenance")


def test_two_calls_persistence_hashes_and_safe_resume():
    sc, record, view = record_and_view()
    call_count = 0
    saw_raw_before_parse = False
    original_dispatch = run_pilot.dispatch_icl
    original_parser = run_pilot.parse_icl_turn_a
    with tempfile.TemporaryDirectory() as outdir:
        def counted(*call_args, **call_kwargs):
            nonlocal call_count
            call_count += 1
            response = original_dispatch(*call_args, **call_kwargs)
            if call_count == 2:
                response = dict(response, finish_reason="length",
                                truncated=True)
            return response

        def checked_parser(raw):
            nonlocal saw_raw_before_parse
            paths = [os.path.join(outdir, name) for name in os.listdir(outdir)
                     if name.endswith(".json")]
            assert len(paths) == 1
            with open(paths[0]) as fh:
                saved = json.load(fh)
            saw_raw_before_parse = (
                saved["state"] == "turn_a_raw_saved"
                and saved["turns"]["A"]["raw_response"] == raw)
            return original_parser(raw)

        run_pilot.dispatch_icl = counted
        run_pilot.parse_icl_turn_a = checked_parser
        try:
            artifact, path, skipped = run_icl_two_response_once(
                record, view, sc, True, args(), "empirical_table", 1, 0,
                outdir)
            assert not skipped and call_count == 2 and saw_raw_before_parse
            assert artifact["state"] == "completed"
            assert [event["event"] for event in artifact["persistence_events"]] == [
                "initialized", "turn_a_raw_saved", "turn_a_complete",
                "turn_b_raw_saved", "completed"]
            assert artifact["turns"]["B"]["previous_response_sha256"] == \
                artifact["turns"]["A"]["response_sha256"]
            for name in ("A", "B"):
                turn = artifact["turns"][name]
                assert turn["response_sha256"] == hashlib.sha256(
                    turn["raw_response"].encode()).hexdigest()
                assert turn["provider_usage"] == {}
            assert artifact["turns"]["A"]["provider_finish_reason"] == \
                "dry_run"
            assert artifact["turns"]["A"]["truncated"] is False
            assert artifact["turns"]["B"]["provider_finish_reason"] == \
                "length"
            assert artifact["turns"]["B"]["truncated"] is True
            summary, _ = write_icl_summary(
                outdir, [{"run_id": artifact["run_id"], "path": path,
                          "skipped": False}])
            assert summary["any_response_truncated"] is True
            assert summary["operational_gate_pass"] is False
            assert call_count == 2
            with open(path, "rb") as fh:
                before = fh.read()
            _, _, skipped = run_icl_two_response_once(
                record, view, sc, True, args(), "empirical_table", 1, 0,
                outdir)
            assert skipped and call_count == 2
            with open(path, "rb") as fh:
                assert fh.read() == before

            partial = json.loads(before)
            partial["state"] = "turn_a_complete"
            partial["turns"]["B"] = {
                "prompt": partial["turns"]["B"]["prompt"],
                "prompt_sha256": partial["turns"]["B"]["prompt_sha256"]}
            partial.pop("metrics", None)
            partial.pop("conversation", None)
            partial.pop("completed_utc", None)
            partial["persistence_events"] = partial["persistence_events"][:3]
            with open(path, "w") as fh:
                json.dump(partial, fh)
            resumed, _, skipped = run_icl_two_response_once(
                record, view, sc, True, args(), "empirical_table", 1, 0,
                outdir)
            assert not skipped and call_count == 3
            assert resumed["state"] == "completed"

            broken = resumed
            broken["state"] = "turn_b_raw_saved"
            del broken["turns"]["B"]["raw_response"]
            with open(path, "w") as fh:
                json.dump(broken, fh)
            try:
                run_icl_two_response_once(
                    record, view, sc, True, args(), "empirical_table", 1, 0,
                    outdir)
                raise AssertionError("unsafe partial run must stop")
            except RuntimeError as exc:
                assert "cannot safely resume" in str(exc)
        finally:
            run_pilot.dispatch_icl = original_dispatch
            run_pilot.parse_icl_turn_a = original_parser
    print("PASS two calls, raw-first persistence, hash link, finish metadata, resume")


def test_summary_generation_and_safe_replay():
    sc = scenario()
    runner_args = args(tag="summary-test")
    runner_args.top_p = 0.95
    runner_args.top_k = 64
    with tempfile.TemporaryDirectory() as outdir:
        run_icl_two_response_suite(sc, True, runner_args, outdir)
        summary_path = os.path.join(outdir, "summary.json")
        with open(summary_path, "rb") as fh:
            before = fh.read()
        summary = json.loads(before)
        assert summary["expected_runs"] == summary["completed_runs"] == 9
        assert len(summary["runs"]) == 9
        assert summary["operational_gate_pass"] is True
        assert summary["every_level_repeat_present"] is True
        assert summary["any_response_truncated"] is False
        first_artifact = next(
            path for path in os.listdir(outdir) if path.startswith("icl_"))
        with open(os.path.join(outdir, first_artifact)) as fh:
            model = json.load(fh)["model"]
        assert model["top_p"] == 0.95 and model["top_k"] == 64
        assert {(row["repeat"], row["level"]) for row in summary["runs"]} == {
            (repeat, level) for repeat in (1, 2, 3) for level in ICL_LEVELS}
        results = run_icl_two_response_suite(sc, True, runner_args, outdir)
        with open(summary_path, "rb") as fh:
            assert fh.read() == before

        first_path = results[0]["path"]
        with open(first_path) as fh:
            first = json.load(fh)
        first["turns"]["A"]["reasoning_control_violation"] = True
        with open(first_path, "w") as fh:
            json.dump(first, fh)
        violated, _ = write_icl_summary(outdir, results)
        assert violated["any_reasoning_control_violation"] is True
        assert violated["operational_gate_pass"] is False
        first["turns"]["A"]["reasoning_control_violation"] = False
        with open(first_path, "w") as fh:
            json.dump(first, fh)
        replayed, _ = write_icl_summary(outdir, results)
        assert replayed == summary
    print("PASS deterministic operational summary and safe replay")


if __name__ == "__main__":
    test_legacy_prompt_and_scorer_regression()
    test_levels_share_visible_evidence_and_raw_order()
    test_icl_route_terminal_action_contract()
    test_empirical_table_uses_visible_inputs_only()
    test_period_boundary_and_prompt_neutrality()
    test_five_pairs_stable_and_no_change_counterfactual()
    test_availability_and_no_change_dry_answers()
    test_combined_parser_component_independence_and_pair_errors()
    test_visible_and_truth_probability_mae()
    test_nullable_localization_and_route_belief_diagnostics()
    test_gate_and_rotation()
    test_provider_sampling_and_reasoning_controls()
    test_cost_and_endpoint_provenance()
    test_two_calls_persistence_hashes_and_safe_resume()
    test_summary_generation_and_safe_replay()
    print("\nALL RUNNER TESTS PASSED")

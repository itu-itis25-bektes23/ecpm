#!/usr/bin/env python3
"""Tests for the sequential response parser. Stdlib only."""

import json

from response_parser import MAX_ROUTE_STEPS, parse_response


QUERIED = [
    {"node": "A", "action": "a1"},
    {"node": "B", "action": "a1"},
]


def response(**updates):
    value = {
        "transitions": [
            {"node": "A", "action": "a1", "available": True,
             "destination": "B", "p_success": 0.8},
            {"node": "B", "action": "a1", "available": True,
             "destination": "C", "p_success": 0.7},
        ],
        "route": [
            {"node": "A", "action": "a1"},
            {"node": "B", "action": "a1"},
        ],
    }
    value.update(updates)
    return value


def parsed(value, turn="A", completion_status="complete"):
    return parse_response(json.dumps(value), turn, QUERIED,
                          completion_status=completion_status)


def test_valid_turns_and_extraction():
    assert parsed(response())["well_formed"]
    turn_b = response(changed=True,
                      changed_pair={"node": "A", "action": "a1"},
                      keep_route=False)
    assert parsed(turn_b, "B")["well_formed"]
    no_change = response(changed=False, changed_pair=None, keep_route=True)
    assert parsed(no_change, "B")["well_formed"]
    fenced = "Answer:\n```json\n" + json.dumps(response()) + "\n```"
    assert parse_response(fenced, "A", QUERIED)["well_formed"]


def test_format_and_completion_failures():
    assert parse_response("not json", "A", QUERIED)["parse_status"] == \
        "malformed_json"
    invalid = response()
    invalid["transitions"][0]["p_success"] = 1.2
    assert parsed(invalid)["parse_status"] == "invalid_object"
    long_route = response(route=[{"node": "A", "action": "a1"}]
                          * (MAX_ROUTE_STEPS + 1))
    assert parsed(long_route)["parse_status"] == "too_long"
    truncated = parsed(response(), completion_status="truncated")
    assert truncated["parse_status"] == "ok"
    assert not truncated["well_formed"]


def test_strict_transition_coverage():
    missing = response()
    missing["transitions"].pop()
    assert parsed(missing)["coverage_status"] == "incomplete_response"
    duplicate = response()
    duplicate["transitions"][1] = duplicate["transitions"][0].copy()
    assert parsed(duplicate)["coverage_status"] == "duplicate_pair"
    unknown = response()
    unknown["transitions"][1]["node"] = "Z"
    assert parsed(unknown)["coverage_status"] == "unknown_pair"


def test_route_consistency_is_not_truth_scoring():
    unresolvable = response()
    unresolvable["route"][1] = {"node": "B", "action": "a2"}
    assert parsed(unresolvable)["parse_status"] == "route_unresolvable"

    inconsistent = response()
    inconsistent["route"][1]["node"] = "C"
    assert parsed(inconsistent)["parse_status"] == "route_inconsistent"

    unavailable = response()
    unavailable["transitions"][0].update(
        available=False, destination=None, p_success=None)
    assert parsed(unavailable)["parse_status"] == "route_inconsistent"

    wrong_but_self_consistent = response()
    wrong_but_self_consistent["transitions"][0]["destination"] = "Z"
    wrong_but_self_consistent["transitions"][1]["node"] = "Z"
    wrong_but_self_consistent["route"][1]["node"] = "Z"
    wrong_pairs = [
        {"node": "A", "action": "a1"},
        {"node": "Z", "action": "a1"},
    ]
    result = parse_response(json.dumps(wrong_but_self_consistent),
                            "A", wrong_pairs)
    assert result["parse_status"] == "ok"
    assert result["coverage_status"] == "ok"


if __name__ == "__main__":
    test_valid_turns_and_extraction()
    test_format_and_completion_failures()
    test_strict_transition_coverage()
    test_route_consistency_is_not_truth_scoring()
    print("ALL SEQUENTIAL RESPONSE TESTS PASSED")

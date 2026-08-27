#!/usr/bin/env python3
"""Parse the two-turn sequential evaluation response.

This module reads only model-visible inputs and the model response. It never
reads the hidden world, intervention, oracle, route cost, or regret.
"""

from __future__ import annotations

import json


MAX_ROUTE_STEPS = 32
SCHEMA_VERSION = "provisional-0.3"


def extract_json_object(text):
    """Return the first balanced, parseable JSON object in text."""
    if not isinstance(text, str):
        return None
    start = text.find("{")
    while start != -1:
        depth, in_string, escaped = 0, False, False
        for end in range(start, len(text)):
            char = text[end]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
            elif char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    try:
                        value = json.loads(text[start:end + 1])
                    except json.JSONDecodeError:
                        break
                    if isinstance(value, dict):
                        return value
                    break
        start = text.find("{", start + 1)
    return None


def _pair(value):
    if not isinstance(value, dict):
        return None
    node, action = value.get("node"), value.get("action")
    if not (isinstance(node, str) and isinstance(action, str)):
        return None
    return node, action


def _parse_transitions(value):
    if not isinstance(value, list):
        return None
    rows = []
    for item in value:
        pair = _pair(item)
        if pair is None or not isinstance(item.get("available"), bool):
            return None
        available = item["available"]
        destination = item.get("destination")
        probability = item.get("p_success")
        if available:
            if not isinstance(destination, str):
                return None
            if (not isinstance(probability, (int, float))
                    or isinstance(probability, bool)
                    or not 0 <= probability <= 1):
                return None
            probability = float(probability)
        elif destination is not None or probability is not None:
            return None
        rows.append({
            "node": pair[0],
            "action": pair[1],
            "available": available,
            "destination": destination,
            "p_success": probability,
        })
    return rows


def _parse_route(value):
    if not isinstance(value, list) or len(value) > MAX_ROUTE_STEPS:
        return None, "too_long" if isinstance(value, list) else "invalid_object"
    route = []
    for item in value:
        pair = _pair(item)
        if pair is None:
            return None, "invalid_object"
        route.append({"node": pair[0], "action": pair[1]})
    return route, "ok"


def _coverage_status(transitions, queried_pairs):
    wanted = []
    for item in queried_pairs:
        pair = _pair(item)
        if pair is None or pair in wanted:
            raise ValueError("queried_pairs must contain unique node-action pairs")
        wanted.append(pair)
    wanted_set = set(wanted)
    seen = set()
    for row in transitions:
        pair = (row["node"], row["action"])
        if pair not in wanted_set:
            return "unknown_pair"
        if pair in seen:
            return "duplicate_pair"
        seen.add(pair)
    return "ok" if seen == wanted_set else "incomplete_response"


def _route_status(route, transitions):
    table = {(row["node"], row["action"]): row for row in transitions}
    for index, step in enumerate(route):
        row = table.get((step["node"], step["action"]))
        if row is None:
            return "route_unresolvable"
        if not row["available"]:
            return "route_inconsistent"
        if index + 1 < len(route):
            expected = row["destination"]
            if route[index + 1]["node"] != expected:
                return "route_inconsistent"
    return "ok"


def parse_response(raw_text, turn, queried_pairs,
                   completion_status="complete"):
    """Parse Turn A or B and return independent format/coverage results."""
    if completion_status not in {"complete", "truncated", "request_error"}:
        raise ValueError("unknown completion_status")
    if turn not in {"A", "B"}:
        raise ValueError("turn must be A or B")

    result = {
        "schema_version": SCHEMA_VERSION,
        "completion_status": completion_status,
        "parse_status": "malformed_json",
        "coverage_status": None,
        "well_formed": False,
        "parsed": None,
    }
    obj = extract_json_object(raw_text)
    if obj is None:
        return result

    transitions = _parse_transitions(obj.get("transitions"))
    route, route_parse_status = _parse_route(obj.get("route"))
    if transitions is None or route_parse_status == "invalid_object":
        result["parse_status"] = "invalid_object"
        return result
    if route_parse_status == "too_long":
        result["parse_status"] = "too_long"
        return result

    parsed = {"transitions": transitions, "route": route}
    if turn == "B":
        changed = obj.get("changed")
        changed_pair = obj.get("changed_pair")
        keep_route = obj.get("keep_route")
        valid_changed_pair = (
            changed is False and changed_pair is None
        ) or (
            changed is True and _pair(changed_pair) is not None
        )
        if (not isinstance(changed, bool)
                or not isinstance(keep_route, bool)
                or not valid_changed_pair):
            result["parse_status"] = "invalid_object"
            return result
        parsed.update({
            "changed": changed,
            "changed_pair": None if changed_pair is None else {
                "node": changed_pair["node"],
                "action": changed_pair["action"],
            },
            "keep_route": keep_route,
        })

    coverage_status = _coverage_status(transitions, queried_pairs)
    route_status = _route_status(route, transitions)
    result.update({
        "parse_status": route_status,
        "coverage_status": coverage_status,
        "parsed": parsed,
    })
    result["well_formed"] = (
        completion_status == "complete"
        and route_status == "ok"
        and coverage_status == "ok"
    )
    return result

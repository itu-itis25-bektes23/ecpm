#!/usr/bin/env python3
"""ECPM v2.1 -- FROZEN Section 7 response parser + scorer.

Consumes raw model output (free text) and the instance JSON record
produced by `pair_to_json`. Pure stdlib; needs nothing but the record.

Frozen response objects (one JSON object per probe; the FIRST balanced
{...} block that parses as JSON is used -- earlier non-parsing brace
blocks, surrounding prose, and code fences are skipped/ignored; unknown
extra fields inside the object are ignored):

  detection ...... {"changed": true|false}
  localization ... {"node": "<node>", "action": "aK"}
  preservation ... {"pairs": [{"node": "<node>", "action": "aK",
                               "changed": true|false}, ...]}
                   optional numeric "p" per pair is recorded, not
                   required. Scoring is STRICT (v2.1.1): exactly one
                   response per queried pair -- an unqueried pair gives
                   status unknown_pair, a repeated pair duplicate_pair,
                   a missing pair incomplete_response; accuracy is
                   reported only when every queried pair is answered
                   exactly once.
  adaptation ..... {"route": [{"node": "<node>", "action": "aK"}, ...]}
                   canonical route representation: explicit state-action
                   steps; at most MAX_ROUTE_STEPS steps; the route must
                   start at `start`, and step i+1's node must equal the
                   destination implied by step i.

Parse statuses:   ok | malformed_json | invalid_object | too_long
Preservation:     unknown_pair | duplicate_pair | incomplete_response
Adaptation walk:  unknown_reference | discontinuous_route |
                  incomplete_route
Adaptation score: valid_finite | silent_broken_edge | illegal_action
                  (statuses shared with resource_mdp.score_route; a
                  valid_finite route with regret == 0 is optimal --
                  exact equality with the oracle route is NOT required).
"""

from __future__ import annotations

import json

MAX_ROUTE_STEPS = 32
EPS = 1e-9


# --------------------------------------------------------------------------
# JSON extraction
# --------------------------------------------------------------------------


def extract_json_object(text):
    """First balanced, parseable {...} object in `text`, else None."""
    if not isinstance(text, str):
        return None
    i = text.find("{")
    while i != -1:
        depth, in_str, esc = 0, False, False
        for j in range(i, len(text)):
            c = text[j]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[i:j + 1])
                        if isinstance(obj, dict):
                            return obj
                    except json.JSONDecodeError:
                        pass
                    break
        i = text.find("{", i + 1)
    return None


# --------------------------------------------------------------------------
# Per-probe parsers (format only; no ground truth touched)
# --------------------------------------------------------------------------


def parse_detection(text):
    obj = extract_json_object(text)
    if obj is None:
        return {"status": "malformed_json"}
    if not isinstance(obj.get("changed"), bool):
        return {"status": "invalid_object"}
    return {"status": "ok", "changed": obj["changed"]}


def parse_localization(text):
    obj = extract_json_object(text)
    if obj is None:
        return {"status": "malformed_json"}
    node, action = obj.get("node"), obj.get("action")
    if not (isinstance(node, str) and isinstance(action, str)):
        return {"status": "invalid_object"}
    return {"status": "ok", "node": node, "action": action}


def parse_preservation(text):
    obj = extract_json_object(text)
    if obj is None:
        return {"status": "malformed_json"}
    pairs = obj.get("pairs")
    if not isinstance(pairs, list):
        return {"status": "invalid_object"}
    out = []
    for item in pairs:
        if not (isinstance(item, dict)
                and isinstance(item.get("node"), str)
                and isinstance(item.get("action"), str)
                and isinstance(item.get("changed"), bool)):
            return {"status": "invalid_object"}
        rec = {"node": item["node"], "action": item["action"],
               "changed": item["changed"]}
        if "p" in item:
            if not isinstance(item["p"], (int, float)) \
                    or isinstance(item["p"], bool):
                return {"status": "invalid_object"}
            rec["p"] = float(item["p"])
        out.append(rec)
    return {"status": "ok", "pairs": out}


def parse_adaptation(text):
    obj = extract_json_object(text)
    if obj is None:
        return {"status": "malformed_json"}
    route = obj.get("route")
    if not isinstance(route, list):
        return {"status": "invalid_object"}
    steps = []
    for item in route:
        if not (isinstance(item, dict)
                and isinstance(item.get("node"), str)
                and isinstance(item.get("action"), str)):
            return {"status": "invalid_object"}
        steps.append({"node": item["node"], "action": item["action"]})
    if len(steps) > MAX_ROUTE_STEPS:
        return {"status": "too_long"}
    return {"status": "ok", "route": steps}


# --------------------------------------------------------------------------
# Scorers (evaluator side; may read the full record)
# --------------------------------------------------------------------------


def _maps(record):
    pre_dest = {(e["from"], e["action"]): e["to"]
                for e in record["world_pre"]["edges"]}
    post_p = {(e["from"], e["to"]): e["p"]
              for e in record["world_post"]["edges"]}
    return pre_dest, post_p


def score_detection(record, parsed):
    truth = record["condition"] != "no_change"
    if parsed["status"] != "ok":
        return {"status": parsed["status"], "truth": truth, "correct": False}
    return {"status": "ok", "truth": truth, "predicted": parsed["changed"],
            "correct": parsed["changed"] is truth}


def score_localization(record, parsed):
    ch = record["change"]
    if ch["edge"] is None:
        return {"status": parsed["status"], "applicable": False,
                "correct": None}
    if parsed["status"] != "ok":
        return {"status": parsed["status"], "applicable": True,
                "correct": False}
    correct = (parsed["node"] == ch["edge"]["from"]
               and parsed["action"] == ch["action"])
    return {"status": "ok", "applicable": True, "correct": correct,
            "truth": {"node": ch["edge"]["from"], "action": ch["action"]}}


def score_preservation(record, parsed, queried_pairs):
    """STRICT scoring (v2.1.1). `queried_pairs` (list of {"node",
    "action"}) is REQUIRED: the probe always names the pairs it asks
    about. The response must answer every queried pair exactly once:

      any pair not in the queried set .... status "unknown_pair"
      any queried pair repeated .......... status "duplicate_pair"
      any queried pair missing ........... status "incomplete_response"

    Accuracy (over ALL queried pairs) is reported only under "ok", so a
    model can neither omit hard pairs nor inflate the denominator.
    Ground truth: a pair changed iff it is the intervention target."""
    if queried_pairs is None:
        raise ValueError("preservation scoring requires queried_pairs")
    wanted = [(q["node"], q["action"]) for q in queried_pairs]
    wset = set(wanted)
    ch = record["change"]
    target = (None if ch["edge"] is None
              else (ch["edge"]["from"], ch["action"]))
    base = {"n_queried": len(wanted), "n_scored": 0, "accuracy": None}
    if parsed["status"] != "ok":
        return {"status": parsed["status"], **base}
    seen = {}
    for item in parsed["pairs"]:
        key = (item["node"], item["action"])
        if key not in wset:
            return {"status": "unknown_pair", **base}
        if key in seen:
            return {"status": "duplicate_pair", **base}
        seen[key] = item["changed"]
    if len(seen) < len(wset):
        return {"status": "incomplete_response", **base}
    correct = sum(seen[key] is (key == target) for key in wanted)
    return {"status": "ok", "n_queried": len(wanted),
            "n_scored": len(wanted), "accuracy": correct / len(wanted)}


def score_adaptation(record, parsed):
    """Translate the state-action route and score it on the POST world by
    execution semantics. Status priority: parse status -> walk statuses
    (unknown_reference, discontinuous_route, incomplete_route) -> cost
    statuses (illegal_action, silent_broken_edge, valid_finite)."""
    out = {"status": parsed["status"], "path": None, "expected_cost": None,
           "optimal_cost": record["oracle"]["post"]["optimal_cost"],
           "regret": None, "is_optimal": False}
    if parsed["status"] != "ok":
        return out
    pre_dest, post_p = _maps(record)
    pos, path = record["start"], [record["start"]]
    for step in parsed["route"]:
        if step["node"] != pos:
            out["status"] = "discontinuous_route"
            return out
        dest = pre_dest.get((pos, step["action"]))
        if dest is None:
            out["status"] = "unknown_reference"
            return out
        path.append(dest)
        pos = dest
    if pos != record["goal"]:
        out["status"] = "incomplete_route"
        return out
    out["path"] = path
    cost = 0.0
    for u, v in zip(path, path[1:]):
        pr = post_p.get((u, v))
        if pr is None:
            out["status"] = "illegal_action"
            return out
        if pr <= 0:
            out["status"] = "silent_broken_edge"
            return out
        cost += 1.0 / pr
    out["status"] = "valid_finite"
    out["expected_cost"] = round(cost, 4)
    if out["optimal_cost"] is not None:
        out["regret"] = round(cost - out["optimal_cost"], 4)
        out["is_optimal"] = out["regret"] <= EPS
    return out


PARSERS = {"detection": parse_detection,
           "localization": parse_localization,
           "preservation": parse_preservation,
           "adaptation": parse_adaptation}

SCORERS = {"detection": score_detection,
           "localization": score_localization,
           "preservation": score_preservation,
           "adaptation": score_adaptation}


def run_probe(record, kind, raw_text, queried_pairs=None):
    """parse + score in one call. kind in PARSERS."""
    parsed = PARSERS[kind](raw_text)
    if kind == "preservation":
        scored = score_preservation(record, parsed, queried_pairs)
    else:
        scored = SCORERS[kind](record, parsed)
    return {"parsed": parsed, "scored": scored}


# --------------------------------------------------------------------------
# v2.2 additions: turn-1 (period-A-only) probes for the two-turn protocol.
# Additive -- the frozen four-probe contract above is unchanged.
# --------------------------------------------------------------------------

BELIEF_P_TOL_STOCHASTIC = 0.15   # frozen before results (PO review)
BELIEF_P_TOL_DETERMINISTIC = 0.0


def parse_belief(text):
    """{"beliefs": [{"node", "action", "destination", "p"}, ...]}"""
    obj = extract_json_object(text)
    if obj is None:
        return {"status": "malformed_json"}
    items = obj.get("beliefs")
    if not isinstance(items, list):
        return {"status": "invalid_object"}
    beliefs = []
    for it in items:
        if not (isinstance(it, dict) and isinstance(it.get("node"), str)
                and isinstance(it.get("action"), str)
                and isinstance(it.get("destination"), str)
                and isinstance(it.get("p"), (int, float))
                and not isinstance(it.get("p"), bool)):
            return {"status": "invalid_object"}
        beliefs.append({"node": it["node"], "action": it["action"],
                        "destination": it["destination"],
                        "p": float(it["p"])})
    return {"status": "ok", "beliefs": beliefs}


def _belief_tol(record):
    return (BELIEF_P_TOL_DETERMINISTIC if record["deterministic"]
            else BELIEF_P_TOL_STOCHASTIC)


def _world_map(record, period):
    return {(e["from"], e["action"]): (e["to"], e["p"])
            for e in record[f"world_{period}"]["edges"]}


def score_belief(record, parsed, queried_pairs, period):
    """Per-pair truth check against the true `period` world. A pair is
    correct iff destination matches exactly AND |p - true_p| <= tol.
    Strict cover like preservation: every queried pair exactly once."""
    out = {"status": parsed["status"], "period": period,
           "n_queried": len(queried_pairs), "n_scored": 0,
           "accuracy": None, "destination_accuracy": None,
           "p_mae": None, "per_pair": [], "tolerance": _belief_tol(record)}
    if parsed["status"] != "ok":
        return out
    want = {(q["node"], q["action"]) for q in queried_pairs}
    got = {}
    for b in parsed["beliefs"]:
        key = (b["node"], b["action"])
        if key not in want or key in got:
            out["status"] = "invalid_object"
            return out
        got[key] = b
    if set(got) != want:
        out["status"] = "invalid_object"
        return out
    truth = _world_map(record, period)
    tol = out["tolerance"]
    rows, ok_dest, ok_all, abs_err = [], 0, 0, []
    for q in queried_pairs:
        key = (q["node"], q["action"])
        b = got[key]
        t = truth.get(key)
        t_dest, t_p = (t if t else (None, None))
        d_ok = t_dest is not None and b["destination"] == t_dest
        p_ok = t_p is not None and abs(b["p"] - t_p) <= tol + 1e-9
        rows.append({"node": q["node"], "action": q["action"],
                     "destination": b["destination"], "p": b["p"],
                     "true_destination": t_dest, "true_p": t_p,
                     "destination_ok": d_ok, "p_ok": p_ok,
                     "correct": d_ok and p_ok})
        ok_dest += d_ok
        ok_all += (d_ok and p_ok)
        if t_p is not None:
            abs_err.append(abs(b["p"] - t_p))
    n = len(rows)
    out.update({"n_scored": n, "per_pair": rows,
                "accuracy": round(ok_all / n, 4),
                "destination_accuracy": round(ok_dest / n, 4),
                "p_mae": (round(sum(abs_err) / len(abs_err), 4)
                          if abs_err else None)})
    return out


def score_route_pre(record, parsed):
    """Route-finding on period A, scored on the PRE world (evidence-only
    planning baseline). Same walk/cost semantics as score_adaptation."""
    pre = _world_map(record, "pre")
    out = {"status": parsed["status"], "path": None, "expected_cost": None,
           "optimal_cost": record["oracle"]["pre"]["optimal_cost"],
           "regret": None, "is_optimal": False}
    if parsed["status"] != "ok":
        return out
    pos, path, cost = record["start"], [record["start"]], 0.0
    for step in parsed["route"]:
        if step["node"] != pos:
            out["status"] = "discontinuous_route"
            return out
        t = pre.get((pos, step["action"]))
        if t is None:
            out["status"] = "unknown_reference"
            return out
        dest, pr = t
        if pr <= 0:
            out["status"] = "silent_broken_edge"
            return out
        cost += 1.0 / pr
        path.append(dest)
        pos = dest
    if pos != record["goal"]:
        out["status"] = "incomplete_route"
        return out
    out.update({"status": "valid_finite", "path": path,
                "expected_cost": round(cost, 4)})
    if out["optimal_cost"] is not None:
        out["regret"] = round(cost - out["optimal_cost"], 4)
        out["is_optimal"] = out["regret"] <= EPS
    return out


def belief_self_consistency(record, pre_scored, post_scored):
    """Preservation by self-consistency: a pair 'changed' in the model's
    own beliefs iff destination differs or |p_post - p_pre| > tol.
    Compared with ground truth (the intervention target)."""
    if pre_scored.get("status") != "ok" or post_scored.get("status") != "ok":
        return {"status": "unscored", "accuracy": None, "per_pair": []}
    tol = _belief_tol(record)
    ch = record["change"]
    target = (None if ch["edge"] is None
              else (ch["edge"]["from"], ch["action"]))
    post = {(r["node"], r["action"]): r for r in post_scored["per_pair"]}
    rows, ok = [], 0
    for r in pre_scored["per_pair"]:
        key = (r["node"], r["action"])
        q = post[key]
        said_changed = (r["destination"] != q["destination"]
                        or abs(r["p"] - q["p"]) > tol + 1e-9)
        truth = key == target
        rows.append({"node": r["node"], "action": r["action"],
                     "self_changed": said_changed, "truth_changed": truth,
                     "correct": said_changed == truth})
        ok += said_changed == truth
    return {"status": "ok", "accuracy": round(ok / len(rows), 4),
            "n_scored": len(rows), "per_pair": rows}


PARSERS.update({"route_pre": parse_adaptation, "belief_pre": parse_belief,
                "belief_post": parse_belief})


# --------------------------------------------------------------------------
# Additive combined-response contract for protocol icl_two_response_v1.
# The frozen schema 2.1 parsers and scorers above are unchanged.
# --------------------------------------------------------------------------


def _component_status(parts):
    statuses = [part["status"] for part in parts]
    if all(status == "ok" for status in statuses):
        return "ok"
    if all(status == "malformed_json" for status in statuses):
        return "malformed_json"
    return "partial"


def _parse_route_value(value):
    if not isinstance(value, list):
        return {"status": "invalid_object", "route": []}
    steps = []
    for item in value:
        if not (isinstance(item, dict)
                and isinstance(item.get("node"), str)
                and isinstance(item.get("action"), str)):
            return {"status": "invalid_object", "route": []}
        steps.append({"node": item["node"], "action": item["action"]})
    if len(steps) > MAX_ROUTE_STEPS:
        return {"status": "too_long", "route": []}
    return {"status": "ok", "route": steps}


def _parse_icl_pairs(value, require_changed):
    if not isinstance(value, list):
        return {"status": "invalid_object", "pairs": []}
    pairs = []
    for item in value:
        if not (isinstance(item, dict)
                and isinstance(item.get("node"), str)
                and isinstance(item.get("action"), str)
                and isinstance(item.get("available"), bool)):
            return {"status": "invalid_object", "pairs": []}
        if require_changed and not isinstance(item.get("changed"), bool):
            return {"status": "invalid_object", "pairs": []}
        available = item["available"]
        destination = item.get("destination")
        probability = item.get("p_success")
        if available:
            if not (isinstance(destination, str)
                    and isinstance(probability, (int, float))
                    and not isinstance(probability, bool)):
                return {"status": "invalid_object", "pairs": []}
            if not 0.0 <= float(probability) <= 1.0:
                return {"status": "out_of_range", "pairs": []}
            probability = float(probability)
        elif destination is not None or probability is not None:
            return {"status": "invalid_unavailable", "pairs": []}
        row = {"node": item["node"], "action": item["action"],
               "available": available, "destination": destination,
               "p_success": probability}
        if require_changed:
            row["changed"] = item["changed"]
        pairs.append(row)
    return {"status": "ok", "pairs": pairs}


def _malformed_icl(turn_b=False):
    bad = {"status": "malformed_json", "pairs": []}
    route = {"status": "malformed_json", "route": []}
    out = {"status": "malformed_json", "well_formed": False,
           "beliefs": bad, "route": route}
    if turn_b:
        out.update({"detection": {"status": "malformed_json"},
                    "localization": {"status": "malformed_json",
                                     "changed_pair": None}})
    return out


def parse_icl_turn_a(text):
    """Parse beliefs and route independently from the Turn A object."""
    obj = extract_json_object(text)
    if obj is None:
        return _malformed_icl()
    beliefs = _parse_icl_pairs(obj.get("pairs"), require_changed=False)
    route = _parse_route_value(obj.get("route"))
    status = _component_status((beliefs, route))
    return {"status": status, "well_formed": status == "ok",
            "beliefs": beliefs, "route": route}


def parse_icl_turn_b(text):
    """Parse detection, nullable localization, beliefs, and route separately."""
    obj = extract_json_object(text)
    if obj is None:
        return _malformed_icl(turn_b=True)
    if isinstance(obj.get("changed"), bool):
        detection = {"status": "ok", "changed": obj["changed"]}
    else:
        detection = {"status": "invalid_object"}
    changed_pair = obj.get("changed_pair")
    if detection["status"] != "ok":
        localization = {"status": "invalid_object", "changed_pair": None}
    elif not detection["changed"] and changed_pair is None:
        localization = {"status": "ok", "changed_pair": None}
    elif (detection["changed"] and isinstance(changed_pair, dict)
          and isinstance(changed_pair.get("node"), str)
          and isinstance(changed_pair.get("action"), str)):
        localization = {
            "status": "ok",
            "changed_pair": {"node": changed_pair["node"],
                             "action": changed_pair["action"]},
        }
    else:
        localization = {"status": "invalid_object", "changed_pair": None}
    beliefs = _parse_icl_pairs(obj.get("pairs"), require_changed=True)
    route = _parse_route_value(obj.get("route"))
    parts = (detection, localization, beliefs, route)
    status = _component_status(parts)
    return {"status": status, "well_formed": status == "ok",
            "detection": detection, "localization": localization,
            "beliefs": beliefs, "route": route}


def score_icl_beliefs(record, parsed, queried_pairs, period,
                      visible_stats=None):
    """Strict five-pair belief scoring for the additive ICL protocol."""
    wanted = [(q["node"], q["action"]) for q in queried_pairs]
    out = {"status": parsed["status"], "period": period,
           "n_queried": len(wanted), "n_scored": 0,
           "accuracy": 0.0, "availability_accuracy": 0.0,
           "destination_accuracy": None, "n_destination_scored": 0,
           "p_mae_visible": None, "n_p_visible_scored": 0,
           "p_mae_truth": None, "n_p_truth_scored": 0,
           "change_label_accuracy": None,
           "per_pair": []}
    if parsed["status"] != "ok":
        return out
    wset, got = set(wanted), {}
    for item in parsed["pairs"]:
        key = (item["node"], item["action"])
        if key not in wset:
            out["status"] = "unknown_pair"
            return out
        if key in got:
            out["status"] = "duplicate_pair"
            return out
        got[key] = item
    if set(got) != wset:
        out["status"] = "missing_pair"
        return out

    truth = _world_map(record, period)
    menu = record[f"legal_actions_{period}"]
    change = record["change"]
    target = (None if change["edge"] is None else
              (change["edge"]["from"], change["action"]))
    rows, truth_errors, visible_errors, destination_rows = [], [], [], []
    for key in wanted:
        item = got[key]
        true_available = key[1] in menu.get(key[0], [])
        true_transition = truth.get(key)
        true_destination, true_p = (true_transition if true_transition
                                    else (None, None))
        visible_p = ((visible_stats or {}).get(key) or {}).get("p_success")
        available_ok = item["available"] is true_available
        destination_ok = item["destination"] == true_destination
        if true_available:
            destination_rows.append(destination_ok)
        if true_p is None or item["p_success"] is None:
            probability_ok = item["p_success"] is true_p
            truth_error = None
        else:
            truth_error = abs(item["p_success"] - true_p)
            truth_errors.append(truth_error)
            probability_ok = truth_error <= _belief_tol(record) + EPS
        visible_error = (None if visible_p is None
                         or item["p_success"] is None else
                         abs(item["p_success"] - visible_p))
        if visible_error is not None:
            visible_errors.append(visible_error)
        transition_ok = available_ok and destination_ok and probability_ok
        changed_ok = None
        if period == "post":
            changed_ok = item["changed"] is (key == target)
        correct = transition_ok and (changed_ok is not False)
        rows.append({**item, "true_available": true_available,
                     "true_destination": true_destination,
                     "true_p_success": true_p,
                     "availability_ok": available_ok,
                     "destination_ok": destination_ok,
                     "probability_ok": probability_ok,
                     "visible_p_success": visible_p,
                     "p_error_visible": visible_error,
                     "p_error_truth": truth_error,
                     "transition_correct": transition_ok,
                     "change_label_ok": changed_ok, "correct": correct})

    n = len(rows)
    out.update({
        "status": "ok", "n_scored": n, "per_pair": rows,
        "accuracy": round(sum(r["correct"] for r in rows) / n, 4),
        "availability_accuracy": round(
            sum(r["availability_ok"] for r in rows) / n, 4),
        "destination_accuracy": (round(
            sum(destination_rows) / len(destination_rows), 4)
            if destination_rows else None),
        "n_destination_scored": len(destination_rows),
        "p_mae_visible": (round(sum(visible_errors) / len(visible_errors), 4)
                          if visible_errors else None),
        "n_p_visible_scored": len(visible_errors),
        "p_mae_truth": (round(sum(truth_errors) / len(truth_errors), 4)
                        if truth_errors else None),
        "n_p_truth_scored": len(truth_errors),
        "change_label_accuracy": (round(
            sum(r["change_label_ok"] for r in rows) / n, 4)
            if period == "post" else None),
    })
    return out


def score_icl_localization(record, parsed_detection, parsed_localization):
    truth_changed = record["condition"] != "no_change"
    predicted = parsed_detection.get("changed")
    detection_ok = (parsed_detection["status"] == "ok"
                    and predicted is truth_changed)
    truth_pair = (None if not truth_changed else
                  {"node": record["change"]["edge"]["from"],
                   "action": record["change"]["action"]})
    predicted_pair = parsed_localization.get("changed_pair")
    localization_applicable = truth_changed
    localization_ok = (None if not localization_applicable else
                       parsed_localization["status"] == "ok"
                       and predicted_pair == truth_pair)
    null_contract_applicable = predicted is False
    null_contract_ok = (None if not null_contract_applicable else
                        parsed_localization["status"] == "ok"
                        and predicted_pair is None)
    return {"detection_status": parsed_detection["status"],
            "detection_correct": detection_ok,
            "predicted_changed": predicted, "truth_changed": truth_changed,
            "localization_status": parsed_localization["status"],
            "localization_applicable": localization_applicable,
            "localization_correct": localization_ok,
            "null_changed_pair_applicable": null_contract_applicable,
            "null_changed_pair_correct": null_contract_ok,
            "predicted_changed_pair": predicted_pair,
            "truth_changed_pair": truth_pair}


def diagnose_route_beliefs(parsed_route, parsed_beliefs, goal):
    """Compare a route with reported beliefs without changing route parsing."""
    if parsed_route["status"] != "ok":
        return {"status": "not_scored", "pairs": []}
    beliefs = {(p["node"], p["action"]): p
               for p in parsed_beliefs.get("pairs", [])}
    checked, unresolved, conflicts = [], [], []
    for index, step in enumerate(parsed_route["route"]):
        key = (step["node"], step["action"])
        expected = (parsed_route["route"][index + 1]["node"]
                    if index + 1 < len(parsed_route["route"]) else goal)
        belief = beliefs.get(key)
        if belief is None:
            unresolved.append({"node": key[0], "action": key[1]})
            checked.append({"node": key[0], "action": key[1],
                            "route_destination": expected,
                            "belief_destination": None,
                            "status": "unresolvable"})
            continue
        conflict = (not belief["available"]
                    or belief["destination"] != expected
                    or belief["p_success"] is None
                    or belief["p_success"] <= 0)
        checked.append({"node": key[0], "action": key[1],
                        "route_destination": expected,
                        "belief_destination": belief["destination"],
                        "status": ("inconsistent" if conflict else
                                   "consistent")})
        if conflict:
            conflicts.append({"node": key[0], "action": key[1]})
    if conflicts:
        return {"status": "route_inconsistent", "pairs": checked,
                "conflicting_pairs": conflicts,
                "unresolved_pairs": unresolved}
    if unresolved:
        return {"status": "route_unresolvable", "pairs": checked,
                "unresolved_pairs": unresolved}
    return {"status": "consistent", "pairs": checked}


def score_control_preservation(record, pre_beliefs, post_beliefs,
                               queried_pairs, target_pair):
    """Primary self-consistency and secondary truth checks on four controls."""
    controls = [(q["node"], q["action"]) for q in queried_pairs
                if (q["node"], q["action"]) != target_pair]
    base = {"status": "unscored", "n_controls": len(controls),
            "mean_control_preservation": 0.0,
            "all_four_controls_correct": False,
            "truth_mean_control_preservation": 0.0, "per_pair": []}
    if (pre_beliefs.get("status") != "ok"
            or post_beliefs.get("status") != "ok"):
        return base
    pre = {(r["node"], r["action"]): r for r in pre_beliefs["per_pair"]}
    post = {(r["node"], r["action"]): r for r in post_beliefs["per_pair"]}
    rows = []
    for key in controls:
        a, b = pre[key], post[key]
        if a["p_success"] is None or b["p_success"] is None:
            same_p = a["p_success"] is b["p_success"]
        else:
            same_p = abs(a["p_success"] - b["p_success"]) <= \
                _belief_tol(record) + EPS
        same_belief = (a["available"] is b["available"]
                       and a["destination"] == b["destination"] and same_p)
        self_ok = same_belief and b.get("changed") is False
        truth_ok = b["transition_correct"] and b.get("change_label_ok") is True
        rows.append({"node": key[0], "action": key[1],
                     "belief_preserved": same_belief,
                     "reported_unchanged": b.get("changed") is False,
                     "self_consistent": self_ok,
                     "truth_correct": truth_ok})
    mean = sum(r["self_consistent"] for r in rows) / len(rows)
    truth_mean = sum(r["truth_correct"] for r in rows) / len(rows)
    return {"status": "ok", "n_controls": len(rows),
            "mean_control_preservation": round(mean, 4),
            "all_four_controls_correct": len(rows) == 4 and mean == 1.0,
            "truth_mean_control_preservation": round(truth_mean, 4),
            "per_pair": rows}

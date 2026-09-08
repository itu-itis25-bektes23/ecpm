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

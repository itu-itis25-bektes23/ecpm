"""Runner + scorer for the ICL / finetuning arms, on the frozen contract.

Written 8 September 2026 to replace the per-notebook scorers.

Why this exists. The notebooks each carried their own `bare_json` and
`run_route`. That produced numbers the rest of the project cannot read:

  * `run_route` hard-coded START, GOAL = "E", "F". Only seed 7 has that
    start and goal, so the route column was walking 31 of 32 official
    seeds from the wrong node.
  * `bare_json` required the whole reply to be one JSON object. The
    frozen contract (INTERFACE.md section 7) takes the FIRST balanced
    parseable {...} block and ignores prose and fences around it, so the
    two disagree on 16 of 64 ICL preservation replies here.
  * "route reaches goal" is more generous than the official metric,
    which is regret against `oracle.post.optimal_cost`.

Everything scored here goes through `ecpm_parser` at the environment
repo. Strictness is kept as a separate diagnostic column (`bare_json`),
not as a scoring rule, so the dose-sweep failure mode (prose with JSON
buried inside) stays visible without changing the shared contract.

Usage:

    import ecpm_eval as E
    E.attach("/kaggle/input/ecpm-repo")     # env repo on sys.path
    payloads = E.load_payloads("/kaggle/input/ecpm-payloads")
    rows = E.run_arm(payloads, ask_fn, arm="icl", mode="single")
    print(E.table(rows))
"""

from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys
import collections

_EP = None          # ecpm_parser module, set by attach()
_REPO = "."         # environment tree, set by attach()

FROZEN_SHA = "5318c3e"


def _git_head(repo="."):
    """Short HEAD of the working tree, or None outside a checkout."""
    try:
        out = subprocess.run(["git", "-C", repo, "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def provenance():
    """Stamped into every row, so a result traces to an environment tree."""
    head = _git_head(_REPO)
    return {"frozen_sha": FROZEN_SHA, "git_head": head,
            "pinned_to_freeze": head == FROZEN_SHA}

MAX_NEW_TOKENS = {          # adaptation answers were truncating at 300
    "detection": 64,
    "localization": 64,
    "preservation": 400,
    "adaptation": 700,
    "route_pre": 700,
    "belief_pre": 500,
    "belief_post": 500,
}

SYSTEM = ("You are analyzing interaction logs from an unknown packet "
          "network. Each observation is (node, action, next node). If the "
          "next node equals the node, the attempt failed and the packet "
          "stayed in place. Answer with exactly one JSON object and "
          "nothing else.")


# --------------------------------------------------------------------------
# setup
# --------------------------------------------------------------------------

def attach(repo="."):
    """Put the environment repo on sys.path and import the frozen parser."""
    global _EP, _REPO
    _REPO = repo
    if not os.path.isfile(os.path.join(repo, "ecpm_parser.py")):
        raise SystemExit(f"{repo} has no ecpm_parser.py")
    sys.path.insert(0, repo)
    import ecpm_parser                                     # noqa: PLC0415
    _EP = ecpm_parser
    ver = "2.2" if hasattr(ecpm_parser, "score_belief") else "2.1 or older"
    print(f"ecpm_parser attached from {repo} (looks like v{ver})")
    return ecpm_parser


def load_payloads(directory, seeds=None, condition=None, mode=None):
    """Payloads written by gen_payloads.py. Sorted by seed."""
    pats = os.path.join(directory, "**", "payload_seed*.json")
    paths = sorted(glob.glob(pats, recursive=True),
                   key=lambda p: int(re.search(r"seed(\d+)", p).group(1)))
    out = []
    for p in paths:
        d = json.load(open(p))
        if "record" not in d or "single" not in d:
            raise SystemExit(
                f"{p} predates the v2.2 generator (no 'record'/'single'). "
                "Regenerate with the new gen_payloads.py.")
        if seeds is not None and d["seed"] not in seeds:
            continue
        if condition and d["condition"] != condition:
            continue
        if mode == "det" and not d["deterministic"]:
            continue
        if mode == "sto" and d["deterministic"]:
            continue
        out.append(d)
    if not out:
        raise SystemExit(f"no payloads matched in {directory}")
    return out


def load_rows(*paths):
    """Read scored rows back from JSONL. Accepts this module's own
    `out_path` files and the ones `run_agentic.py` writes, so the agentic
    arm lands in the same table as the offline arms. Both go through
    `ecpm_parser`, so the columns mean the same thing."""
    rows = []
    for pat in paths:
        for path in sorted(glob.glob(pat)):
            for line in open(path):
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    if not rows:
        raise SystemExit(f"no rows found in {paths}")
    return rows


def common_seeds(*payload_sets):
    """Seeds present in every set. Use this before pairing a changed
    condition with no_change: they have different eligibility, so
    unmatched sets compare different graphs."""
    sets = [{p["seed"] for p in ps} for ps in payload_sets]
    return sorted(set.intersection(*sets))


# --------------------------------------------------------------------------
# diagnostics that are NOT scoring
# --------------------------------------------------------------------------

_FENCE = re.compile(r"^```(?:json)?\s*")


def is_bare_json(raw):
    """True when the whole reply is one JSON object, fences aside.

    Diagnostic only. The frozen contract permits surrounding prose; this
    column records whether the model needed that permission.
    """
    s = _FENCE.sub("", (raw or "").strip())
    s = re.sub(r"\s*```$", "", s).strip()
    if not (s.startswith("{") and s.endswith("}")):
        return False
    try:
        json.loads(s)
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------
# scoring
# --------------------------------------------------------------------------

FROZEN = ("detection", "localization", "preservation", "adaptation")


def score(payload, probe, raw):
    """One reply -> {'parsed', 'scored'} using the frozen parser."""
    if _EP is None:
        raise SystemExit("call attach(repo) first")
    rec, queried = payload["record"], payload["queried_pairs"]
    if probe in FROZEN:
        return _EP.run_probe(rec, probe, raw,
                             queried_pairs=(queried if probe == "preservation"
                                            else None))
    parsed = _EP.PARSERS[probe](raw)
    if probe == "route_pre":
        scored = _EP.score_route_pre(rec, parsed)
    else:
        scored = _EP.score_belief(rec, parsed, queried,
                                  "pre" if probe == "belief_pre" else "post")
    return {"parsed": parsed, "scored": scored}


def self_consistency(payload, pre_scored, post_scored):
    return _EP.belief_self_consistency(payload["record"], pre_scored,
                                       post_scored)


# --------------------------------------------------------------------------
# running an arm
# --------------------------------------------------------------------------

def run_arm(payloads, ask_fn, arm, mode="single", probes=None,
            with_evidence=True, out_path=None, resume=True, verbose=True):
    """Ask every probe of every payload and score it.

    ask_fn(messages, max_new_tokens) -> raw string. `messages` is a list
    of {"role", "content"} including the system turn, so the caller
    controls the chat template and the model.

    mode "single": each probe is a fresh one-shot conversation carrying
    the whole evidence block, which is the frozen behaviour.
    mode "two_turn": one conversation. Period A, then route_pre and
    belief_pre, then period B is revealed and the frozen probes follow
    (v2.2). Requires payloads built by a v2.2 generator.

    with_evidence=False strips the evidence and asks the questions alone,
    which is the no-evidence control.

    Rows are appended to out_path as JSONL if given, and an interrupted
    run resumes from it.
    """
    done = set()
    rows = []
    if out_path and resume and os.path.exists(out_path):
        for line in open(out_path):
            r = json.loads(line)
            rows.append(r)
            done.add((r["arm"], r["seed"], r["condition"], r["mode"],
                      r["probe"]))
        if verbose:
            print(f"resuming, {len(rows)} rows already in {out_path}")
    sink = open(out_path, "a") if out_path else None

    for i, pay in enumerate(payloads):
        if mode == "two_turn":
            if not pay.get("two_turn"):
                raise SystemExit(f"seed {pay['seed']}: payload has no "
                                 "two_turn block, regenerate it")
            schedule = [(s["probe"], s["turn"])
                        for s in pay["two_turn"]["schedule"]]
        else:
            schedule = [(p, 2) for p in pay["probes"]]
        if probes:
            schedule = [(p, t) for p, t in schedule if p in probes]

        history, belief = [], {}
        for idx, (probe, turn) in enumerate(schedule, start=1):
            key = (arm, pay["seed"], pay["condition"], mode, probe)
            if key in done:
                prev = next(r for r in rows if tuple(
                    (r["arm"], r["seed"], r["condition"], r["mode"],
                     r["probe"])) == key)
                if mode == "two_turn":
                    history = history + [
                        {"role": "user", "content": prev["prompt"]},
                        {"role": "assistant", "content": prev["raw"]}]
                    if probe in ("belief_pre", "belief_post"):
                        belief[probe] = prev["scored"]
                continue

            user = _user_message(pay, probe, turn, idx, schedule, mode,
                                 with_evidence)
            msgs = ([{"role": "system", "content": SYSTEM}]
                    + history + [{"role": "user", "content": user}])
            raw = ask_fn(msgs, MAX_NEW_TOKENS.get(probe, 400))
            res = score(pay, probe, raw)

            row = {"arm": arm, "seed": pay["seed"],
                   "condition": pay["condition"],
                   "deterministic": pay["deterministic"], "mode": mode,
                   "probe": probe, "turn": turn, "prompt": user, "raw": raw,
                   "bare_json": is_bare_json(raw),
                   "target": pay["facts"]["target_pair"],
                   "provenance": provenance(),
                   "parsed": res["parsed"], "scored": res["scored"]}
            rows.append(row)
            if sink:
                sink.write(json.dumps(row) + "\n")
                sink.flush()
            if mode == "two_turn":
                history = history + [{"role": "user", "content": user},
                                     {"role": "assistant", "content": raw}]
                if probe in ("belief_pre", "belief_post"):
                    belief[probe] = res["scored"]

        sc_key = (arm, pay["seed"], pay["condition"], mode,
                  "preservation_self_consistency")
        if (mode == "two_turn" and sc_key not in done
                and {"belief_pre", "belief_post"} <= set(belief)):
            sc = self_consistency(pay, belief["belief_pre"],
                                  belief["belief_post"])
            row = {"arm": arm, "seed": pay["seed"],
                   "condition": pay["condition"],
                   "deterministic": pay["deterministic"], "mode": mode,
                   "probe": "preservation_self_consistency", "turn": 2,
                   "prompt": None, "raw": None, "bare_json": None,
                   "target": pay["facts"]["target_pair"],
                   "provenance": provenance(),
                   "parsed": None, "scored": sc}
            rows.append(row)
            if sink:
                sink.write(json.dumps(row) + "\n")
                sink.flush()
        if verbose and (i + 1) % 5 == 0:
            print(f"  {i + 1}/{len(payloads)} payloads")
    if sink:
        sink.close()
    return rows


def _user_message(pay, probe, turn, idx, schedule, mode, with_evidence):
    if mode != "two_turn":
        return _ask_only(pay, probe) if not with_evidence \
            else pay["single"][probe]
    tt = pay["two_turn"]
    ask = tt["asks"][probe]
    first_of_turn = (idx == 1) or (turn == 2 and schedule[idx - 2][1] == 1)
    if not with_evidence:
        return ask
    if turn == 1 and first_of_turn:
        return tt["turn1_header"] + "\n" + ask
    if turn == 2 and first_of_turn:
        return tt["reveal_b"] + "\n" + ask
    return ask


def _ask_only(pay, probe):
    """The probe question with the evidence header removed."""
    if pay.get("two_turn"):
        return pay["two_turn"]["asks"][probe]
    full = pay["single"][probe]
    # the ask is the tail after the last observation block
    marker = "Observations, period B:"
    if marker in full:
        tail = full.split(marker, 1)[1]
        return tail.split("\n\n", 1)[1] if "\n\n" in tail else tail
    return full


# --------------------------------------------------------------------------
# tables
# --------------------------------------------------------------------------

def _pick(rows, **kw):
    return [r for r in rows if all(r.get(k) == v for k, v in kw.items())]


def table(rows, arms=None):
    """One row per arm. Detection is a sensitivity/specificity pair, which
    is the project-wide reporting rule; preservation carries its constant
    baseline and its target-pair recall, because accuracy alone is met by
    answering 'nothing changed' every time."""
    order = ("none", "icl", "arm_c", "arm_d", "agentic")
    arms = arms or sorted({r["arm"] for r in rows},
                          key=lambda a: order.index(a) if a in order else 99)
    out = []
    for arm in arms:
        a = _pick(rows, arm=arm)
        rec = {"arm": arm}

        det = _pick(a, probe="detection")
        pos = [r for r in det if r["scored"].get("truth") is True]
        neg = [r for r in det if r["scored"].get("truth") is False]
        rec["sens"] = _frac(sum(r["scored"].get("correct") for r in pos),
                            len(pos))
        rec["spec"] = _frac(sum(r["scored"].get("correct") for r in neg),
                            len(neg))

        loc = [r for r in _pick(a, probe="localization")
               if r["scored"].get("applicable")]
        rec["localize"] = _frac(sum(r["scored"].get("correct") for r in loc),
                                len(loc))

        pres = _pick(a, probe="preservation")
        ok = [r for r in pres if r["scored"]["status"] == "ok"]
        rec["pres_parsed"] = _frac(len(ok), len(pres))
        rec["pres_acc"] = _mean([r["scored"]["accuracy"] for r in ok])
        rec["pres_const"] = _mean([_constant_baseline(r) for r in pres])
        rec["target_recall"] = _target_recall(a, ok)

        sc = _pick(a, probe="preservation_self_consistency")
        if sc:
            rec["pres_selfcons"] = _mean(
                [r["scored"]["accuracy"] for r in sc
                 if r["scored"].get("accuracy") is not None])

        ad = _pick(a, probe="adaptation")
        fin = [r for r in ad if r["scored"]["status"] == "valid_finite"]
        rec["route_valid"] = _frac(len(fin), len(ad))
        rec["route_optimal"] = _frac(sum(r["scored"]["is_optimal"]
                                         for r in fin), len(ad))
        rec["mean_regret"] = _mean([r["scored"]["regret"] for r in fin])
        rec["route_status"] = dict(collections.Counter(
            r["scored"]["status"] for r in ad).most_common(3))

        rp = _pick(a, probe="route_pre")
        if rp:
            f = [r for r in rp if r["scored"]["status"] == "valid_finite"]
            rec["routeA_optimal"] = _frac(
                sum(r["scored"]["is_optimal"] for r in f), len(rp))

        bp = _pick(a, probe="belief_post")
        if bp:
            okb = [r for r in bp if r["scored"]["status"] == "ok"]
            rec["belief_dest"] = _mean(
                [r["scored"]["destination_accuracy"] for r in okb])
            rec["belief_pmae"] = _mean(
                [r["scored"]["p_mae"] for r in okb
                 if r["scored"]["p_mae"] is not None])

        n_bare = sum(1 for r in a if r.get("bare_json") is not None)
        rec["bare_json"] = (_frac(sum(bool(r["bare_json"]) for r in a
                                      if r.get("bare_json") is not None),
                                  n_bare) if n_bare else None)
        out.append(rec)
    return out


def _constant_baseline(row):
    """What 'nothing changed' would score on this instance."""
    n = row["scored"].get("n_queried") or 0
    if not n:
        return None
    changed_here = 1 if row["condition"] != "no_change" else 0
    return (n - changed_here) / n


def _target_recall(arm_rows, ok_preservation):
    """Of the changed instances whose queried set holds the target, how
    often was the target itself called changed. This is the informative
    bit that accuracy hides."""
    hit = tot = 0
    for r in ok_preservation:
        if r["condition"] == "no_change":
            continue
        pairs = r["parsed"].get("pairs", [])
        tgt = _target_of(r)
        if tgt is None:
            continue
        for p in pairs:
            if (p["node"], p["action"]) == tgt:
                tot += 1
                hit += bool(p["changed"])
    return _frac(hit, tot)


def _target_of(row):
    t = row.get("target")
    return tuple(t) if t else None


def _frac(num, den):
    return f"{num}/{den}" + (f" = {num / den:.2f}" if den else "")


def _mean(vals):
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 4) if vals else None


def mcnemar(rows_a, rows_b, probe="localization"):
    """Exact two-sided McNemar on paired per-seed correctness."""
    import math
    ga = {r["seed"]: bool(r["scored"].get("correct"))
          for r in rows_a if r["probe"] == probe}
    gb = {r["seed"]: bool(r["scored"].get("correct"))
          for r in rows_b if r["probe"] == probe}
    seeds = sorted(set(ga) & set(gb))
    b = sum(ga[s] and not gb[s] for s in seeds)
    c = sum(gb[s] and not ga[s] for s in seeds)
    n = b + c
    if n == 0:
        return {"b": 0, "c": 0, "p": 1.0, "n_paired": len(seeds)}
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return {"b": b, "c": c, "p": min(1.0, 2 * tail), "n_paired": len(seeds)}

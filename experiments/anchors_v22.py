"""Anchor worlds for the finetuning arm, built on the frozen generator.

Replaces the hand-written `anchors.py`. That file had its own world
builder with `START, GOAL = "E", "F"` fixed, deterministic transitions
only, and its own copy of the probe wording. Three problems:

  * The official worlds have 19 distinct start/goal pairs across the 32
    graded seeds. Training on E->F only and evaluating on the rest is a
    distribution shift the eval never sees through.
  * Anchors were deterministic, so the adapter has never seen a
    stochastic world. Running it on stochastic payloads is untested
    transfer.
  * A second copy of the probe text drifts from the frozen one. Train and
    test wording disagreeing is the bug that voided the August runs.

Here every world comes from `resource_mdp.make_pair` and every prompt
from `run_pilot.context_block` / `ask_block`, so an anchor example is
byte-identical in shape to a graded payload. The only difference is the
seed.

Seeds start at 1000, well outside the official 0-79 range, and
`build_anchor_set` asserts it. No anchor world can collide with a graded
seed.

Usage:
  python3 anchors_v22.py ../ecpm-main --worlds 40 --out anchors.json
  python3 anchors_v22.py ../ecpm-main --worlds 60 --stochastic-share 0.5
"""

from __future__ import annotations

import argparse
import json
import os
import sys

OFFICIAL_MAX_SEED = 79
FIRST_ANCHOR_SEED = 1000

# Half the worlds carry a change and half do not, so detection gold is
# not constant. Within the changed half, the three break-family
# conditions are cycled so the adapter sees more than one way for a link
# to go wrong.
CHANGED_CONDITIONS = ("silent_break", "hard_removal", "irrelevant")
UNCHANGED_CONDITION = "no_change"

PROBES = ("detection", "localization", "preservation", "adaptation")
TURN1_PROBES = ("route_pre", "belief_pre")


def load_env(repo=".", pilot_from=None):
    if not os.path.isfile(os.path.join(repo, "resource_mdp.py")):
        raise SystemExit(f"{repo} has no resource_mdp.py")
    pilot_dir = pilot_from or repo
    missing = [f for f in ("explore_agent.py", "explore_metrics.py")
               if not os.path.isfile(os.path.join(pilot_dir, f))]
    if missing:
        raise SystemExit(
            f"{pilot_dir} is missing {', '.join(missing)}. Since Christian's "
            "fork was merged, run_pilot.py imports them at module level, so a "
            "partial copy of the repo no longer works. Upload the whole "
            "checkout.")
    sys.path.insert(0, pilot_dir)
    sys.path.insert(0, repo)
    import run_pilot as rp                                  # noqa: PLC0415
    for name in ("context_block", "ask_block", "queried_pairs_for",
                 "build_record", "SCENARIO_DEFAULTS"):
        if not hasattr(rp, name):
            raise SystemExit(f"run_pilot.py has no {name}; this needs v2.2")
    return rp


def _scenario(seed, condition, k):
    sc = dict()
    sc.update({"name": f"anchor{seed}_{condition}", "condition": condition,
               "seed": seed, "matched": True, "k": k, "evidence_seed": 0,
               "rendering": "F2_shuffled", "budget": k,
               "probes": PROBES, "variants": ("det", "sto")})
    return sc


def _gold(record, probe, queried):
    """The answer the frozen scorer would mark correct."""
    ch = record.get("change") or {}
    edge = ch.get("edge") or {}
    target = (edge["from"], ch["action"]) if edge.get("from") else None
    if probe == "detection":
        return {"changed": record["condition"] != "no_change"}
    if probe == "localization":
        if target is None:
            return None
        return {"node": target[0], "action": target[1]}
    if probe == "preservation":
        return {"pairs": [{"node": q["node"], "action": q["action"],
                           "changed": (q["node"], q["action"]) == target}
                          for q in queried]}
    if probe in ("adaptation", "route_pre"):
        o = record["oracle"]["post" if probe == "adaptation" else "pre"]
        return {"route": [{"node": n, "action": a} for n, a in
                          zip(o["optimal_route"], o["optimal_actions"])]}
    if probe == "belief_pre":
        beliefs = record["oracle"]["pre"]["beliefs"]
        return {"beliefs": [beliefs[f"{q['node']}|{q['action']}"]
                            for q in queried]}
    raise KeyError(probe)


def build_world(rp, seed, condition, deterministic, k=5, turn1=False):
    """One anchor world and its (prompt, gold) examples, or None if the
    seed is not constructible under this condition."""
    sc = _scenario(seed, condition, k)
    try:
        record = rp.build_record(sc, deterministic)
    except (ValueError, RuntimeError):
        return None
    view = rp.prompt_view(record, rendering="F2_shuffled",
                          periods=("pre", "post"), budget_per_pair=k)
    queried = rp.queried_pairs_for(record, sc)
    context = rp.context_block(view)

    probes = [p for p in PROBES
              if not (condition == "no_change" and p == "localization")]
    items = []
    for probe in probes:
        gold = _gold(record, probe, queried)
        if gold is None:
            continue
        items.append({"probe": probe,
                      "prompt": context + "\n" + rp.ask_block(view, probe,
                                                              queried),
                      "gold": json.dumps(gold)})
    if turn1 and hasattr(rp, "context_block_a"):
        head = rp.context_block_a(view)
        for probe in TURN1_PROBES:
            try:
                gold = _gold(record, probe, queried)
            except KeyError:
                continue
            items.append({"probe": probe,
                          "prompt": head + "\n" + rp.ask_block(view, probe,
                                                               queried),
                          "gold": json.dumps(gold)})

    ch = record.get("change") or {}
    edge = ch.get("edge") or {}
    return {"seed": seed, "condition": condition,
            "deterministic": deterministic,
            "changed": condition != "no_change",
            "target": [edge["from"], ch["action"]] if edge.get("from") else None,
            "start": record["start"], "goal": record["goal"],
            "queried_pairs": queried, "items": items}


def build_anchor_set(rp, n_worlds=40, k=5, stochastic_share=0.5,
                     first_seed=FIRST_ANCHOR_SEED, turn1=False,
                     preservation_changed_repeat=3):
    """Half changed and half not, break conditions cycled, deterministic
    and stochastic mixed.

    `preservation_changed_repeat` duplicates the preservation example of
    each changed world. The queried set holds exactly one changed pair of
    four, so at world-level balance the pair-level positive rate is
    12.5%, and answering "nothing changed" everywhere scores 0.875. That
    is exactly what the current adapter does on every graded reply.
    Repeating the positive examples raises the gradient the minority
    class gets. The realised rate is reported by `summarise` so it is
    visible rather than assumed.
    """
    assert first_seed > OFFICIAL_MAX_SEED, \
        f"anchor seeds must clear the official range ({OFFICIAL_MAX_SEED})"
    worlds, seed, tried = [], first_seed, 0
    while len(worlds) < n_worlds and tried < n_worlds * 40:
        i = len(worlds)
        changed = (i % 2 == 0)
        condition = (CHANGED_CONDITIONS[(i // 2) % len(CHANGED_CONDITIONS)]
                     if changed else UNCHANGED_CONDITION)
        deterministic = ((i % 4) >= 2) if stochastic_share >= 0.5 else True
        if stochastic_share == 0.0:
            deterministic = True
        w = build_world(rp, seed, condition, deterministic, k, turn1)
        tried += 1
        seed += 1
        if w is None:
            continue
        if changed and preservation_changed_repeat > 1:
            extra = [dict(it) for it in w["items"]
                     if it["probe"] == "preservation"]
            w["items"] += extra * (preservation_changed_repeat - 1)
        worlds.append(w)
    if len(worlds) < n_worlds:
        raise SystemExit(f"only built {len(worlds)} of {n_worlds} worlds")
    return worlds


def to_examples(worlds):
    """Flatten to the (prompt, gold) pairs the trainer consumes."""
    out = []
    for w in worlds:
        for it in w["items"]:
            out.append({"seed": w["seed"], "condition": w["condition"],
                        "deterministic": w["deterministic"],
                        "probe": it["probe"], "prompt": it["prompt"],
                        "gold": it["gold"]})
    return out


def summarise(worlds):
    import collections
    ex = to_examples(worlds)
    by_probe = collections.Counter(e["probe"] for e in ex)
    by_cond = collections.Counter(w["condition"] for w in worlds)
    det = sum(w["deterministic"] for w in worlds)
    pos = tot = 0
    for e in ex:
        if e["probe"] != "preservation":
            continue
        for p in json.loads(e["gold"])["pairs"]:
            tot += 1
            pos += bool(p["changed"])
    sg = {(w["start"], w["goal"]) for w in worlds}
    return {"worlds": len(worlds), "examples": len(ex),
            "changed_worlds": sum(w["changed"] for w in worlds),
            "deterministic_worlds": det,
            "stochastic_worlds": len(worlds) - det,
            "conditions": dict(by_cond), "examples_by_probe": dict(by_probe),
            "distinct_start_goal": len(sg),
            "preservation_pair_positive_rate": round(pos / tot, 4) if tot else None,
            "all_unchanged_would_score": round(1 - pos / tot, 4) if tot else None,
            "seed_range": [min(w["seed"] for w in worlds),
                           max(w["seed"] for w in worlds)]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--out", default="anchors.json")
    ap.add_argument("--worlds", type=int, default=40)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--stochastic-share", type=float, default=0.5)
    ap.add_argument("--first-seed", type=int, default=FIRST_ANCHOR_SEED)
    ap.add_argument("--turn1", action="store_true",
                    help="also emit route_pre and belief_pre examples")
    ap.add_argument("--preservation-repeat", type=int, default=3)
    ap.add_argument("--pilot-from", default=None)
    args = ap.parse_args()

    rp = load_env(args.repo, args.pilot_from)
    worlds = build_anchor_set(rp, args.worlds, args.k, args.stochastic_share,
                              args.first_seed, args.turn1,
                              args.preservation_repeat)
    json.dump(worlds, open(args.out, "w"))
    for key, val in summarise(worlds).items():
        print(f"  {key}: {val}")
    print(f"written to {args.out}")


if __name__ == "__main__":
    main()

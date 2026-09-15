"""Generate probe payloads for any seed, condition and mode.

Run from the repository root; the environment modules are in the same
tree. Nothing here is imported by the harness. Output is regenerated
rather than committed.

  python3 experiments/gen_payloads.py --validate
  python3 experiments/gen_payloads.py payloads_det --seeds 0-79
  python3 experiments/gen_payloads.py payloads_deg --seeds 0-79 \
      --condition degradation --stochastic
  python3 experiments/gen_payloads.py payloads_nc --seeds 0-79 \
      --condition no_change

Conditions are `resource_mdp.CONDITIONS`. `degradation` is stochastic
only. `no_change` has no localization probe, since that question asserts
a change that did not happen.

Every function that touches the instance, the evidence, the rendering,
the queried pairs or the prompt text comes from `resource_mdp` and
`run_pilot`. This script only loops over seeds and writes files.

What a payload carries:

  record          the full instance JSON, so `ecpm_parser.run_probe` can
                  score a reply without regenerating anything
  queried_pairs   from the frozen `queried_pairs_for`, target included
  single          {probe: full prompt text}, the one-shot mode
  two_turn        the turn-1 header, the period-B reveal, and every ask
                  in schedule order
  facts           the flat summary used by tables
  provenance      frozen_sha, git_head and pinned_to_freeze, matching
                  what `run_pilot.py` stamps into its artifacts

`--validate` rebuilds seed 7 and compares against the archived pilot
artifacts. It distinguishes two cases. A difference in `detection`,
`localization` or `preservation` is a regression and fails. A difference
in `adaptation` is expected: that prompt was reworded on 7 September
2026, after the archive was made, because three models read the old
ending as an instruction to append a step at the goal node. The old
wording ended "the route must end at F"; the new one ends "the
destination of the last action must be F. Do NOT include a step at F
itself."

Route numbers produced against the old wording are not comparable with
route numbers produced against the new one. See
`runs/2026-08-27_e1_qwen2.5-1.5b/README.md`.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

SIBLINGS = (".",)
FROZEN_SHA = "5318c3e"

# Probes whose wording is unchanged since the archive. A difference in any
# of these is a regression, not an expected edit.
STABLE_PROBES = ("detection", "localization", "preservation")
REWORDED_PROBES = ("adaptation",)


def _find(candidates, marker):
    for c in candidates:
        if c and os.path.exists(os.path.join(c, marker)):
            return c
    return None


def _git_head(repo):
    """Short HEAD of the working tree, or None outside a checkout."""
    try:
        out = subprocess.run(["git", "-C", repo, "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def load_env(repo, pilot_from=None):
    """Import run_pilot and ecpm_parser with the environment repo first."""
    if not os.path.isfile(os.path.join(repo, "resource_mdp.py")):
        raise SystemExit(f"{repo} has no resource_mdp.py; run this from the "
                         "repository root or pass the path as the first "
                         "argument")
    pilot = pilot_from or _find([repo] + list(SIBLINGS), "run_pilot.py")
    if pilot is None:
        raise SystemExit("run_pilot.py not found; pass --pilot-from")
    missing = [f for f in ("explore_agent.py", "explore_metrics.py")
               if not os.path.isfile(os.path.join(pilot, f))]
    if missing:
        raise SystemExit(
            f"{pilot} is missing {', '.join(missing)}. run_pilot.py imports "
            "them at module level, so a partial copy of the tree does not "
            "work.")
    sys.path.insert(0, pilot)
    sys.path.insert(0, repo)
    import run_pilot as rp                                # noqa: PLC0415
    import ecpm_parser as ep                              # noqa: PLC0415
    for name in ("context_block", "ask_block", "queried_pairs_for",
                 "build_record", "prompt_view"):
        if not hasattr(rp, name):
            raise SystemExit(
                f"run_pilot.py at {pilot} has no {name}. This generator "
                "targets the current harness.")
    if not hasattr(rp, "context_block_a"):
        print("note: this run_pilot has no two-turn support; writing "
              "single-turn payloads only")
    return rp, ep


def probes_for(condition):
    if condition == "no_change":
        # localization asserts a change occurred, so the harness drops it
        return ("detection", "preservation", "adaptation")
    return ("detection", "localization", "preservation", "adaptation")


def scenario_for(seed, condition, k, evidence_seed, rendering, budget):
    """The scenario dict run_pilot builds internally. `queried_pairs_for`
    reads sc['seed'], so this has to carry the same key."""
    return {"name": f"gen_seed{seed}_{condition}", "condition": condition,
            "seed": seed, "matched": True, "k": k,
            "evidence_seed": evidence_seed, "rendering": rendering,
            "budget": budget, "probes": list(probes_for(condition)),
            "variants": ("det", "sto")}


def build_for_seed(rp, seed, deterministic, k, condition="silent_break",
                   evidence_seed=0, rendering="F2_shuffled", budget=None,
                   git_head=None):
    """run_pilot's own record, view, queried pairs and prompt assembly for
    one seed. Raises ValueError for ineligible seeds."""
    budget = k if budget is None else budget
    sc = scenario_for(seed, condition, k, evidence_seed, rendering, budget)
    record = rp.build_record(sc, deterministic)
    view = rp.prompt_view(record, rendering=rendering,
                          periods=("pre", "post"), budget_per_pair=budget)
    queried = rp.queried_pairs_for(record, sc)

    probes = tuple(sc["probes"])
    context = rp.context_block(view)
    single = {p: context + "\n" + rp.ask_block(view, p, queried)
              for p in probes}

    two_turn = None
    if hasattr(rp, "context_block_a"):
        turn1 = list(rp.TURN1_PROBES)
        turn2 = list(probes) + [rp.REELICIT_PROBE]
        two_turn = {
            "turn1_header": rp.context_block_a(view),
            "reveal_b": rp.reveal_block_b(view),
            "schedule": [{"probe": p, "turn": 1} for p in turn1]
                        + [{"probe": p, "turn": 2} for p in turn2],
            "asks": {p: rp.ask_block(view, p, queried)
                     for p in turn1 + turn2},
        }

    ch = record.get("change") or {}
    edge = ch.get("edge") or {}
    has_change = bool(edge.get("from")) and bool(ch.get("action"))
    new_edge = ch.get("new_edge") or {}
    oracle = record["oracle"]
    return {
        "seed": seed, "deterministic": deterministic, "k": k,
        "budget_per_pair": budget, "rendering": rendering,
        "condition": condition, "schema_version": record["schema_version"],
        "provenance": {"frozen_sha": FROZEN_SHA, "git_head": git_head,
                       "pinned_to_freeze": git_head == FROZEN_SHA},
        "facts": {
            "condition": condition,
            "changed": condition != "no_change",
            "target_pair": [edge["from"], ch["action"]] if has_change else None,
            # redirect keeps the probability and moves the destination, so
            # the second endpoint only exists for that condition
            "new_destination": new_edge.get("to") if new_edge else None,
            "old_p": ch.get("old_p"), "new_p": ch.get("new_p"),
            "on_optimal_route": ch.get("on_optimal_route"),
            "start": record["start"], "goal": record["goal"],
            "oracle_pre_cost": oracle["pre"]["optimal_cost"],
            "oracle_post_cost": oracle["post"]["optimal_cost"],
            "route_changed": oracle["route_changed"],
            "post_route_unique": oracle["post"]["route_unique"],
            "post_alternative_cost": oracle["post"].get("alternative_cost"),
        },
        "record": record,
        "queried_pairs": queried,
        "probes": list(probes),
        "single": single,
        "two_turn": two_turn,
    }


def validate(rp, repo, archive=None):
    """Rebuild seed 7 and compare against the archived pilot artifacts.

    A difference in a stable probe is a regression and fails. A difference
    in adaptation is expected, because that prompt was reworded after the
    archive was made; it is reported rather than raised.
    """
    archive = archive or _find([repo] + list(SIBLINGS), "runs")
    if archive is None:
        raise SystemExit("no runs/ folder found; pass --archive")
    runs = os.path.join(archive, "runs")
    art_dir = sorted(d for d in os.listdir(runs)
                     if os.path.exists(os.path.join(
                         runs, d, "pilot_deterministic.json")))[0]

    matched, expected, regressions = 0, [], []
    for det, name in ((True, "pilot_deterministic.json"),
                      (False, "pilot_stochastic.json")):
        art = json.load(open(os.path.join(runs, art_dir, name)))
        built = build_for_seed(rp, 7, det, 5, "silent_break")
        for probe, p in art["probes"].items():
            if built["single"][probe] == p["prompt_text"]:
                matched += 1
            elif probe in REWORDED_PROBES:
                expected.append((name, probe))
            else:
                regressions.append((name, probe))
        qp = art["probes"]["preservation"]["queried_pairs"]
        if built["queried_pairs"] != qp:
            regressions.append((name, "queried_pairs"))

    print(f"archive: {art_dir}")
    print(f"  {matched} prompts reproduced byte for byte")
    for name, probe in expected:
        print(f"  {probe} differs in {name}: expected, reworded "
              "2026-09-07, see the module docstring")
    if regressions:
        for name, probe in regressions:
            print(f"  REGRESSION: {probe} differs in {name}")
        raise SystemExit("a stable probe changed; this is not an expected "
                         "edit")
    print("validation passed")


def parse_seeds(spec):
    if "-" in spec and "," not in spec:
        a, b = spec.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in spec.split(",")]


def main():
    ap = argparse.ArgumentParser(
        description="Build probe payloads from the frozen generator.")
    ap.add_argument("out_dir", nargs="?", default="payloads")
    ap.add_argument("--repo", default=".",
                    help="environment tree, defaults to the current "
                         "directory so this runs from the repository root")
    ap.add_argument("--seeds", default="0-79")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--budget", type=int, default=None,
                    help="budget_per_pair for prompt_view, defaults to k")
    ap.add_argument("--evidence-seed", type=int, default=0)
    ap.add_argument("--rendering", default="F2_shuffled")
    ap.add_argument("--stochastic", action="store_true")
    ap.add_argument("--condition", default="silent_break")
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--pilot-from", default=None)
    ap.add_argument("--archive", default=None)
    args = ap.parse_args()

    rp, _ = load_env(args.repo, args.pilot_from)

    from resource_mdp import CONDITIONS                   # noqa: PLC0415
    if args.condition not in CONDITIONS:
        raise SystemExit(f"--condition must be one of {list(CONDITIONS)}")

    if args.validate:
        validate(rp, args.repo, args.archive)
        return

    det = not args.stochastic
    if args.condition == "degradation" and det:
        raise SystemExit("degradation is undefined in deterministic mode. "
                         "Pass --stochastic.")

    git_head = _git_head(args.repo)
    os.makedirs(args.out_dir, exist_ok=True)
    tag = "det" if det else "sto"
    eligible, skipped, reasons = [], [], []
    for seed in parse_seeds(args.seeds):
        try:
            built = build_for_seed(rp, seed, det, args.k, args.condition,
                                   args.evidence_seed, args.rendering,
                                   args.budget, git_head)
        except (ValueError, RuntimeError) as e:
            skipped.append(seed)
            reasons.append(str(e)[:90])
            continue
        path = os.path.join(
            args.out_dir,
            f"payload_seed{seed}_{args.condition}_{tag}_k{args.k}.json")
        json.dump(built, open(path, "w"))
        eligible.append(seed)

    print(f"condition: {args.condition}, mode: {tag}, k: {args.k}, "
          f"budget: {args.budget or args.k}")
    print(f"git_head: {git_head}, frozen_sha: {FROZEN_SHA}")
    print(f"eligible: {len(eligible)} seeds {eligible}")
    print(f"ineligible: {len(skipped)} seeds {skipped}")
    if skipped:
        print(f"first rejection reasons: {sorted(set(reasons))[:3]}")
    print(f"written to {args.out_dir}/")


if __name__ == "__main__":
    main()

"""Generate official probe payloads for any eligible seed, on the frozen code.

Every function that touches the instance, the evidence, the rendering,
the queried pairs, or the prompt text is imported from the frozen
checkout's own run_pilot.py and resource_mdp.py. This script only loops
over seeds and writes files. The seed enters exactly where the pilot's
GRAPH_SEED constant sits, so seed 7 must reproduce the archived
artifacts byte for byte, and --validate proves that before anything
else is trusted.

Usage:
  python3 gen_payloads.py /path/to/frozen-checkout out_dir --seeds 0-79
  python3 gen_payloads.py /path/to/ecpm-main out_dir --validate

Options: --stochastic for the stochastic sibling, --k N for the
per-pair evidence budget (default 5, the pilot value), --seeds A-B or
a comma list.
"""

from __future__ import annotations

import os
import sys

# Merged into the main repository on 2026-09-13. Previously these scripts
# reached a separate ecpm checkout through sys.path, guarded by a check that
# resource_mdp.py and ecpm_parser.py existed there. In-tree that indirection
# is unnecessary: the modules are two directories up.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)



import argparse
import json
import os
import sys


SIBLINGS = ("../ecpm-efe", "../ecpm-main", "../ecpm")


def load_frozen(repo=None, pilot_from=None):
    """Import run_pilot from this repository.

    The repo and pilot_from arguments are accepted and ignored so existing
    call sites and command lines keep working. Before the merge they pointed
    at a separate checkout.
    """
    import run_pilot as rp  # noqa: PLC0415
    return rp


def build_for_seed(rp, seed, deterministic, k):
    """The pilot's build_record + view + queried, with the seed swapped
    in where GRAPH_SEED sits. Raises ValueError for ineligible seeds."""
    rp.GRAPH_SEED = seed
    inst = rp.make_pair(seed, "silent_break", deterministic=deterministic,
                        matched=True)
    ev = rp.paired_evidence(inst, k=k, evidence_seed=0)
    record = json.loads(json.dumps(rp.pair_to_json(inst, ev)))
    view = rp.prompt_view(record, rendering="F2_shuffled",
                          periods=("pre", "post"), budget_per_pair=k)
    queried = rp.queried_pairs_for(record)
    prompts = {p: rp.build_prompt(record, view, p, queried)
               for p in ("detection", "localization", "preservation",
                         "adaptation")}
    prefix = os.path.commonprefix(list(prompts.values()))
    cut = len(prefix)
    shared = prefix[:cut].rstrip("\n")
    questions = {p: t[len(shared):].lstrip("\n") for p, t in prompts.items()}
    ch = record["change"]
    return {"seed": seed, "deterministic": deterministic, "k": k,
            "facts": {"break_pair": [ch["edge"]["from"], ch["action"]],
                      "oracle_pre_cost": record["oracle"]["pre"]["optimal_cost"],
                      "oracle_post_cost": record["oracle"]["post"]["optimal_cost"]},
            "record": record, "queried_pairs": queried,
            "prompts": prompts, "shared_context": shared,
            "questions": questions}


def validate(rp, repo, archive=None):
    """Seed 7, k 5 must reproduce the archived artifacts byte for byte.

    The archive lives in runs/, which was pushed after the freeze, so for
    a frozen worktree the archive has to come from the main checkout.
    """
    archive = archive or _find([repo] + list(SIBLINGS), "runs")
    if archive is None:
        raise SystemExit(
            "no runs/ folder found. It was pushed after the freeze, so a "
            "frozen worktree does not have it.\n"
            "Pass --archive ../ecpm-efe")
    if os.path.abspath(archive) != os.path.abspath(repo):
        print(f"archive from {archive}, environment from {repo}")
    runs = os.path.join(archive, "runs")
    art_dir = sorted(d for d in os.listdir(runs)
                     if os.path.exists(os.path.join(runs, d,
                                                    "pilot_deterministic.json")))[0]
    checked = 0
    for det, name in ((True, "pilot_deterministic.json"),
                      (False, "pilot_stochastic.json")):
        art = json.load(open(os.path.join(runs, art_dir, name)))
        built = build_for_seed(rp, 7, det, 5)
        for probe, p in art["probes"].items():
            assert built["prompts"][probe] == p["prompt_text"], \
                (name, probe, "prompt text differs from the archive")
            checked += 1
        qp = art["probes"]["preservation"]["queried_pairs"]
        assert built["queried_pairs"] == qp, (name, "queried pairs differ")
    print(f"validation passed, {checked} archived prompts reproduced "
          f"byte for byte from {art_dir}")


def parse_seeds(spec):
    if "-" in spec and "," not in spec:
        a, b = spec.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in spec.split(",")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("out_dir", nargs="?", default="payloads")
    ap.add_argument("--seeds", default="0-79")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--stochastic", action="store_true")
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--pilot-from", default=None,
                    help="folder holding run_pilot.py, which is kept out "
                         "of the frozen tree. Defaults to the repo, then "
                         "sibling checkouts.")
    ap.add_argument("--archive", default=None,
                    help="folder holding runs/ for --validate. The archive "
                         "postdates the freeze, so a frozen worktree needs "
                         "this pointed at the main checkout.")
    args = ap.parse_args()
    rp = load_frozen(args.repo, args.pilot_from)
    if args.validate:
        validate(rp, args.repo, args.archive)
        return
    os.makedirs(args.out_dir, exist_ok=True)
    det = not args.stochastic
    tag = "det" if det else "sto"
    eligible, skipped = [], []
    for seed in parse_seeds(args.seeds):
        try:
            built = build_for_seed(rp, seed, det, args.k)
        except ValueError:
            skipped.append(seed)
            continue
        path = os.path.join(args.out_dir,
                            f"payload_seed{seed}_{tag}_k{args.k}.json")
        json.dump(built, open(path, "w"))
        eligible.append(seed)
    print(f"eligible: {len(eligible)} seeds {eligible}")
    print(f"ineligible: {len(skipped)} seeds {skipped}")
    print(f"written to {args.out_dir}/")


if __name__ == "__main__":
    main()

"""Re-score saved E1 notebook answers with the frozen parser.

This is the step that turns notebook numbers into official numbers.
The notebook saves raw model replies to e1_answers.json. This script
feeds each raw reply through ecpm_parser.run_probe on a checkout of the
frozen repo and writes e1_official_scores.json.

Usage:
  python3 rescore_e1.py e1_answers.json /path/to/frozen-checkout

Self test, proves this script reproduces the archived official scoring
byte for byte, needs a checkout that contains the runs folder:
  python3 rescore_e1.py --selftest /path/to/ecpm-main
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



import json
import os
import sys

PROBE_KINDS = ("detection", "localization", "preservation", "adaptation")

# The queried preservation pairs of the frozen seed-7 pilot, extracted
# from the archived official run artifacts. official_det_payload.json in
# this folder overrides this constant when present.
QUERIED_FALLBACK = [{"node": "H", "action": "a2"}, {"node": "D", "action": "a2"},
                    {"node": "D", "action": "a1"}, {"node": "C", "action": "a1"}]


def load_frozen(repo=None):
    """Import the frozen parser and a reference record from this repository.

    The repo argument is accepted and ignored; before the merge it pointed at
    a separate checkout.
    """
    import ecpm_parser  # noqa: PLC0415
    record = json.load(open(os.path.join(
        _ROOT, "example_deterministic_silent_break.json")))
    return ecpm_parser, record


def queried_pairs():
    here = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(here, "official_det_payload.json")
    if os.path.exists(p):
        return json.load(open(p))["queried_pairs"]
    return QUERIED_FALLBACK


def rescore(answers_path, repo):
    parser, record = load_frozen(repo)
    answers = json.load(open(answers_path))
    queried = queried_pairs()
    out = {}
    meta = {k: v for k, v in answers.items() if not isinstance(v, dict)
            or "detection" not in v}
    if meta:
        print("metadata:", json.dumps({k: str(v)[:60] for k, v in meta.items()}))
    for arm, probes in answers.items():
        if arm in meta:
            continue
        out[arm] = {}
        print(f"--- {arm} ---")
        for kind in PROBE_KINDS:
            raw = probes[kind]["raw"]
            res = parser.run_probe(record, kind, raw,
                                   queried_pairs=queried
                                   if kind == "preservation" else None)
            out[arm][kind] = res
            print(f"  {kind}: {json.dumps(res['scored'])}")
    dest = os.path.join(os.path.dirname(os.path.abspath(answers_path)),
                        "e1_official_scores.json")
    json.dump(out, open(dest, "w"), indent=1)
    print(f"written: {dest}")


def selftest(repo):
    """Feed the archived raw responses back through run_probe and require
    the output to equal the archived scored fields exactly."""
    parser, record = load_frozen(repo)
    runs = os.path.join(repo, "runs")
    tested = 0
    for rd in sorted(os.listdir(runs)):
        art_path = os.path.join(runs, rd, "pilot_deterministic.json")
        if not os.path.exists(art_path):
            continue
        art = json.load(open(art_path))
        for kind in PROBE_KINDS:
            probe = art["probes"][kind]
            res = parser.run_probe(record, kind, probe["raw_response"],
                                   queried_pairs=probe.get("queried_pairs")
                                   if kind == "preservation" else None)
            assert res["scored"] == probe["scored"], (rd, kind, res["scored"],
                                                      probe["scored"])
            assert res["parsed"] == probe["parsed"], (rd, kind)
            tested += 1
        print(f"  {rd}: all four probes reproduce the archived scoring")
    print(f"self test passed, {tested} probe scorings reproduced exactly")


def rescore_batch(answers_path, payload_dir, repo):
    """Score a multi-seed answers jsonl against per-seed payload records
    with the frozen parser, then print the aggregate table."""
    import glob
    parser, _ = load_frozen(repo)
    payloads = {}
    for p in glob.glob(os.path.join(payload_dir, "payload_*.json")):
        d = json.load(open(p))
        payloads[(d["seed"], d["deterministic"], d["k"])] = d
    agg = {}
    out_rows = []
    for line in open(answers_path):
        row = json.loads(line)
        key = (row["seed"], row.get("deterministic", True), row.get("k", 5))
        pay = payloads.get(key)
        if pay is None:
            print(f"seed {row['seed']}: no payload file, skipped")
            continue
        scored_row = {"seed": row["seed"]}
        for arm in ("none", "icl", "ft", "combo"):
            if arm not in row:
                continue
            scored_row[arm] = {}
            for kind in PROBE_KINDS:
                raw = row[arm][kind]["raw"]
                res = parser.run_probe(pay["record"], kind, raw,
                                       queried_pairs=pay["queried_pairs"]
                                       if kind == "preservation" else None)
                scored_row[arm][kind] = res
                a = agg.setdefault((arm, kind), {"n": 0, "correct": 0,
                                                 "acc_sum": 0.0, "acc_n": 0,
                                                 "regrets": [],
                                                 "statuses": {}})
                a["n"] += 1
                sc = res["scored"]
                st = sc.get("status", "?")
                a["statuses"][st] = a["statuses"].get(st, 0) + 1
                if "correct" in sc:
                    a["correct"] += bool(sc["correct"])
                if sc.get("accuracy") is not None:
                    a["acc_sum"] += sc["accuracy"]
                    a["acc_n"] += 1
                if sc.get("regret") is not None:
                    a["regrets"].append(sc["regret"])
        out_rows.append(scored_row)
    dest = os.path.join(os.path.dirname(os.path.abspath(answers_path)),
                        "batch_official_scores.json")
    json.dump(out_rows, open(dest, "w"), indent=1)
    print(f"written: {dest}\n")
    print(f"{'arm':6} {'probe':13} {'n':>3}  result")
    for (arm, kind), a in sorted(agg.items()):
        if kind == "preservation" and a["acc_n"]:
            res = f"mean accuracy {a['acc_sum'] / a['acc_n']:.3f} " \
                  f"over {a['acc_n']} scored"
        elif kind == "adaptation":
            r = a["regrets"]
            res = (f"{len(r)} valid routes, mean regret "
                   f"{sum(r) / len(r):.2f}" if r else "0 valid routes")
        else:
            res = f"accuracy {a['correct']}/{a['n']}"
        res += f"  statuses {a['statuses']}"
        print(f"{arm:6} {kind:13} {a['n']:>3}  {res}")


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "--batch":
        rescore_batch(sys.argv[2], sys.argv[3],
                      sys.argv[4] if len(sys.argv) > 4 else ".")
    elif len(sys.argv) >= 3 and sys.argv[1] == "--selftest":
        selftest(sys.argv[2])
    elif len(sys.argv) >= 3:
        rescore(sys.argv[1], sys.argv[2])
    else:
        print(__doc__)

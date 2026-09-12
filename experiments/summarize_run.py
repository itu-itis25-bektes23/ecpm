"""Aggregate two-turn artifacts into the Section 5 statistics.

Produces exactly the six figures the methodology document reports, plus the
2x2 that Figure 2 draws, computed from artifacts rather than transcribed.

    python3 experiments/summarize_run.py pilot_artifacts/premeet
    python3 experiments/summarize_run.py pilot_artifacts/premeet --json out.json

Reports per condition, with n attached to every cell, because a cell without
its n cannot be read. Instances where any scored probe failed to parse are
counted separately and excluded from the rates, since a format failure is not
a reasoning failure.
"""

import argparse
import glob
import json
import math
import os


def wilson(k, n, z=1.96):
    """95% interval for a proportion. Small n is the normal case here."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - half) / d), min(1.0, (c + half) / d))


def load(root):
    out = []
    for path in glob.glob(os.path.join(root, "**", "*.json"), recursive=True):
        if os.path.basename(path) == "summary.json":
            continue
        try:
            d = json.load(open(path))
        except Exception:
            continue
        if "probes" not in d or "scenario" not in d:
            continue
        out.append(d)
    return out


def probe(d, name):
    return (d.get("probes") or {}).get(name) or {}


def summarize(records):
    rows = {}
    for d in records:
        cond = d["scenario"]["condition"]
        r = rows.setdefault(cond, {
            "n": 0, "unparsed": 0, "detection": 0, "localization": 0,
            "loc_asked": 0, "pres_sum": 0.0, "pres_all4": 0,
            "route_valid": 0, "route_optimal": 0, "regret_sum": 0.0,
            "regret_n": 0, "cells": {(1, 1): 0, (1, 0): 0, (0, 1): 0, (0, 0): 0},
            "selfcons_sum": 0.0, "selfcons_n": 0,
        })

        scored = {k: probe(d, k).get("scored") or {} for k in
                  ("detection", "localization", "preservation", "adaptation")}
        # An instance counts only if every asked probe parsed.
        bad = any(s.get("status") in ("unparsed", "malformed_json", None)
                  for k, s in scored.items() if probe(d, k))
        if bad:
            r["unparsed"] += 1
            continue
        r["n"] += 1

        # Field names differ per probe: detection/localization use
        # `correct`, preservation uses `accuracy`, adaptation uses
        # `is_optimal`. metrics_final carries the per-phase score but not
        # the underlying detail, so read the scored blocks directly.
        r["detection"] += int(bool(scored["detection"].get("correct")))

        loc_ok = None
        if probe(d, "localization"):
            r["loc_asked"] += 1
            loc_ok = bool(scored["localization"].get("correct"))
            r["localization"] += int(loc_ok)

        pres = scored["preservation"].get("accuracy")
        if pres is not None:
            r["pres_sum"] += pres
            r["pres_all4"] += int(pres == 1.0)

        ad = scored["adaptation"]
        valid = ad.get("status") in ("valid_finite", "valid")
        r["route_valid"] += int(valid)
        opt = bool(ad.get("is_optimal") or (ad.get("regret") is not None
                                            and abs(ad["regret"]) < 1e-9))
        r["route_optimal"] += int(opt and valid)
        if ad.get("regret") is not None:
            r["regret_sum"] += abs(ad["regret"])
            r["regret_n"] += 1

        if loc_ok is not None:
            r["cells"][(int(loc_ok), int(opt and valid))] += 1

        sc = (d.get("self_consistency_preservation") or {}).get("accuracy")
        if sc is not None:
            r["selfcons_sum"] += sc
            r["selfcons_n"] += 1
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    records = load(args.root)
    if not records:
        raise SystemExit(f"no artifacts found under {args.root}")
    rows = summarize(records)

    for cond in sorted(rows):
        r = rows[cond]
        n = r["n"]
        if n == 0:
            print(f"\n{cond}: 0 scoreable instances "
                  f"({r['unparsed']} failed to parse)")
            continue
        lo, hi = wilson(r["localization"], r["loc_asked"] or 1)
        olo, ohi = wilson(r["route_optimal"], n)
        print(f"\n=== {cond}  (n={n}, unparsed={r['unparsed']}) ===")
        print(f"  Detection      : {r['detection']}/{n} "
              f"({r['detection']/n:.0%})")
        if r["loc_asked"]:
            print(f"  Localization   : {r['localization']}/{r['loc_asked']} "
                  f"({r['localization']/r['loc_asked']:.0%})  "
                  f"Wilson [{lo:.2f}, {hi:.2f}]")
        print(f"  Preservation   : mean {r['pres_sum']/n:.3f}, "
              f"all four correct in {r['pres_all4']}/{n}")
        if r["selfcons_n"]:
            print(f"  Self-consistency preservation: mean "
                  f"{r['selfcons_sum']/r['selfcons_n']:.3f} "
                  f"(n={r['selfcons_n']})")
        mr = r["regret_sum"] / r["regret_n"] if r["regret_n"] else float("nan")
        print(f"  Route-finding  : {r['route_valid']}/{n} valid, "
              f"{r['route_optimal']}/{n} optimal "
              f"({r['route_optimal']/n:.0%})  Wilson [{olo:.2f}, {ohi:.2f}], "
              f"mean regret {mr:.3f}")
        if r["loc_asked"]:
            c = r["cells"]
            print(f"  Figure 2 cells :")
            print(f"     localized and optimal      : {c[(1,1)]}")
            print(f"     localized, route not optimal: {c[(1,0)]}")
            print(f"     not localized, route optimal: {c[(0,1)]}")
            print(f"     neither                     : {c[(0,0)]}")
            off = c[(1, 0)] + c[(0, 1)]
            print(f"     off-diagonal                : {off} of "
                  f"{sum(c.values())}")

    if args.json:
        with open(args.json, "w") as fh:
            json.dump({k: {kk: (vv if not isinstance(vv, dict)
                                else {str(a): b for a, b in vv.items()})
                           for kk, vv in v.items()}
                       for k, v in rows.items()}, fh, indent=2)
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()

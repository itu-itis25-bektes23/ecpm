"""Verify the local reconstruction against the frozen repo.

Usage:
  python3 verify_against_frozen.py /path/to/ecpm-main

What it checks, in order:
  1. The 15 adjacency entries in seed7_world.SEED7_DET against
     world_pre.edges in the shipped example_deterministic_silent_break.json.
  2. Start, goal, and the full change record.
  3. The oracle facts, pre cost 4 with the tie at E, post cost 5 unique.
  4. That resource_mdp.make_pair(7, "silent_break", deterministic=True,
     matched=True) regenerates the shipped example exactly.
  5. The stochastic sibling, break pair old_p and oracle expected costs.
  6. That the local World reproduces the frozen oracle numbers.

Every check prints PASS or FAIL. Exit code 0 only if all pass.
"""

from __future__ import annotations

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seed7_world import SEED7_DET, START, GOAL, BREAK_PAIR, World

FAILED = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  {detail}" if detail else ""))
    if not ok:
        FAILED.append(name)


def adjacency_from_edges(edges):
    adj = {}
    for e in edges:
        adj.setdefault(e["from"], {})[e["action"]] = e["to"]
    return adj


def main(repo):
    sys.path.insert(0, repo)
    det_path = os.path.join(repo, "example_deterministic_silent_break.json")
    sto_path = os.path.join(repo, "example_stochastic_silent_break.json")
    det = json.load(open(det_path))
    sto = json.load(open(sto_path))

    print("1. adjacency, 15 entries against the shipped deterministic example")
    frozen_adj = adjacency_from_edges(det["world_pre"]["edges"])
    pairs_frozen = {(u, a) for u in frozen_adj for a in frozen_adj[u]}
    pairs_local = {(u, a) for u in SEED7_DET for a in SEED7_DET[u]}
    check("same 15 pairs listed", pairs_frozen == pairs_local,
          f"frozen {len(pairs_frozen)}, local {len(pairs_local)}")
    for u in sorted(SEED7_DET):
        for a in sorted(SEED7_DET[u]):
            f = frozen_adj.get(u, {}).get(a)
            l = SEED7_DET[u][a]
            check(f"{u} {a} -> {l}", f == l, "" if f == l else f"frozen says {f}")

    print("2. start, goal, change record")
    check("start E", det["start"] == START == "E")
    check("goal F", det["goal"] == GOAL == "F")
    ch = det["change"]
    check("break pair (D, a2)", (ch["edge"]["from"], ch["action"]) == BREAK_PAIR)
    check("break destination B", ch["edge"]["to"] == "B")
    check("old_p 1.0, new_p 0.0", ch["old_p"] == 1.0 and ch["new_p"] == 0.0)
    check("mode silent, on optimal route", ch["mode"] == "silent"
          and ch["on_optimal_route"] is True)

    print("3. frozen oracle facts")
    o = det["oracle"]
    check("pre cost 4", o["pre"]["optimal_cost"] == 4.0)
    check("pre route E,A,D,B,F", o["pre"]["optimal_route"] == ["E", "A", "D", "B", "F"])
    check("pre tie at E, alternative E,C,D,B,F",
          o["pre"]["route_unique"] is False
          and o["pre"]["alternative_route"] == ["E", "C", "D", "B", "F"])
    check("post cost 5", o["post"]["optimal_cost"] == 5.0)
    check("post route E,A,G,H,B,F unique",
          o["post"]["optimal_route"] == ["E", "A", "G", "H", "B", "F"]
          and o["post"]["route_unique"] is True)

    print("4. regeneration on the frozen code")
    try:
        import resource_mdp
        inst = resource_mdp.make_pair(7, "silent_break",
                                      deterministic=True, matched=True)
        regen = resource_mdp.pair_to_json(inst)
        if True:
            same = (adjacency_from_edges(regen["world_pre"]["edges"]) == frozen_adj
                    and regen["change"] == ch
                    and regen["oracle"]["pre"]["optimal_cost"] == 4.0
                    and regen["oracle"]["post"]["optimal_cost"] == 5.0)
            check("make_pair(7, silent_break, det, matched) matches example", same)
    except Exception as exc:  # noqa: BLE001
        check("make_pair regeneration", False, f"error: {exc}")

    print("5. stochastic sibling")
    sadj = adjacency_from_edges(sto["world_pre"]["edges"])
    check("same graph as deterministic", sadj == frozen_adj)
    sch = sto["change"]
    check("same break pair", (sch["edge"]["from"], sch["action"]) == BREAK_PAIR)
    check("old_p 0.62", abs(sch["old_p"] - 0.62) < 1e-9, f"got {sch['old_p']}")
    so = sto["oracle"]
    check("pre expected cost ~6.13", abs(so["pre"]["optimal_cost"] - 6.13) < 0.01,
          f"got {so['pre']['optimal_cost']}")
    check("post expected cost ~7.46", abs(so["post"]["optimal_cost"] - 7.46) < 0.01,
          f"got {so['post']['optimal_cost']}")

    print("6. local World reproduces the frozen oracle")
    m0 = World()
    m1 = m0.with_silent_break()
    pre_cost, pre_route = m0.oracle()
    post_cost, post_route = m1.oracle()
    check("local pre cost 4", pre_cost == 4.0)
    check("local post cost 5", post_cost == 5.0)
    local_post_nodes = [u for (u, _) in post_route] + [GOAL]
    check("local post route matches frozen",
          local_post_nodes == o["post"]["optimal_route"])
    sto_p = {(e["from"], e["action"]): e["p"] for e in sto["world_pre"]["edges"]}
    w = World(p=sto_p)
    sc, _ = w.oracle()
    check("local oracle on frozen stochastic p matches frozen to 4 dp",
          round(sc, 4) == so["pre"]["optimal_cost"], f"local {sc:.6f}")

    print()
    if FAILED:
        print(f"RESULT: {len(FAILED)} check(s) FAILED: {FAILED}")
        return 1
    print("RESULT: all checks passed. The reconstruction matches the frozen repo.")
    return 0


if __name__ == "__main__":
    repo = sys.argv[1] if len(sys.argv) > 1 else "."
    sys.exit(main(repo))

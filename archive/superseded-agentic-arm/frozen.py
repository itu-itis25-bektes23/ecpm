"""Connector to the frozen ECPM repo, which lives in its own repository.

This package stays a separate repository for now. Nothing from the
frozen repo is copied here. Everything below reaches the frozen code
through one configurable path and refuses to run if the environment
does not match the frozen seed-7 facts.

How the path is resolved, first hit wins:
  1. an explicit path argument to locate() or load_pair()
  2. the ECPM_REPO environment variable
  3. the sibling folders ../ecpm-main, ../ecpm, ./ecpm-main

Usage:
  import frozen
  m0, m1 = frozen.paired_worlds("/path/to/ecpm-main")
  # m0 and m1 satisfy the same interface as seed7_world.World, but every
  # step executes the frozen resource_mdp code, not the local copy.

Guard: on load, make_pair(7, silent_break, deterministic, matched) is
regenerated on the frozen code and compared with the shipped example
file. A mismatch raises immediately, so agent code can never silently
run against a drifted environment.
"""

from __future__ import annotations

import json
import os
import random
import sys

_CANDIDATES = ("../ecpm-main", "../ecpm", "./ecpm-main")


def locate(path=None):
    """Return the frozen repo path or raise with a clear message."""
    tried = []
    for p in ([path] if path else []) + [os.environ.get("ECPM_REPO")] + list(_CANDIDATES):
        if not p:
            continue
        tried.append(p)
        if os.path.isfile(os.path.join(p, "resource_mdp.py")):
            return os.path.abspath(p)
    raise FileNotFoundError(
        "frozen ECPM repo not found. Set ECPM_REPO or pass a path. "
        f"Tried: {tried}")


def _import_frozen(repo):
    if repo not in sys.path:
        sys.path.insert(0, repo)
    import resource_mdp  # noqa: PLC0415
    return resource_mdp


def guard(repo):
    """Fingerprint check: the frozen code must regenerate the shipped
    seed-7 deterministic example exactly. Raises AssertionError on drift."""
    rm = _import_frozen(repo)
    example = json.load(open(os.path.join(
        repo, "example_deterministic_silent_break.json")))
    inst = rm.make_pair(7, "silent_break", deterministic=True, matched=True)
    regen = rm.pair_to_json(inst)

    def adj(edges):
        out = {}
        for e in edges:
            out.setdefault(e["from"], {})[e["action"]] = e["to"]
        return out

    assert adj(regen["world_pre"]["edges"]) == adj(example["world_pre"]["edges"]), \
        "adjacency drift between frozen code and shipped example"
    assert regen["change"] == example["change"], "change record drift"
    assert regen["oracle"]["pre"]["optimal_cost"] == 4.0
    assert regen["oracle"]["post"]["optimal_cost"] == 5.0
    return inst


class FrozenWorld:
    """Adapter giving a frozen RoutingMDP the local World interface.

    Attributes and methods used by agent_loop and break_metrics:
    adj, start, goal, menu, step, legal_pairs. Every step call executes
    resource_mdp.RoutingMDP.step, the frozen dynamics, not local code.
    """

    def __init__(self, mdp, labels, start, goal, seed=0):
        self._mdp = mdp
        self._labels = dict(labels)            # (u, v) -> "aK"
        self._dest = {(u, a): v for (u, v), a in self._labels.items()}
        self.adj = {}
        for (u, v), a in self._labels.items():
            self.adj.setdefault(u, {})[a] = v
        self.start = start
        self.goal = goal
        self.rng = random.Random(seed)

    def menu(self, node):
        return sorted(self.adj.get(node, {}))

    def legal_pairs(self):
        return [(u, a) for u in sorted(self.adj) for a in self.menu(u)]

    def step(self, node, action):
        if (node, action) not in self._dest:
            raise ValueError(f"action {action} not listed at {node}")
        nxt, ok = self._mdp.step(node, self._dest[(node, action)], self.rng)
        return ("OK" if ok else "DROP"), nxt

    def oracle(self, source=None):
        """(expected_cost, route) with route as (node, action) pairs.

        Delegates to the frozen RoutingMDP.optimal_route, so the regret
        baseline comes from the frozen code, not from local Dijkstra.
        Matches the return shape of seed7_world.World.oracle.
        """
        source = source or self.start
        path, cost = self._mdp.optimal_route(source)
        if path is None:
            return float("inf"), []
        route = [(u, self._labels[(u, v)]) for u, v in zip(path, path[1:])]
        return cost, route


def load_pair(path=None, condition="silent_break", deterministic=True,
              seed=7, run_guard=True):
    """Build the frozen PairedInstance. Returns (instance, repo_path)."""
    repo = locate(path)
    rm = _import_frozen(repo)
    if run_guard:
        guard(repo)
    inst = rm.make_pair(seed, condition, deterministic=deterministic,
                        matched=True)
    return inst, repo


def worlds_from_instance(inst, env_seed=0):
    m0 = FrozenWorld(inst.m0, inst.labels, inst.start, inst.m0.goal,
                     seed=env_seed)
    m1 = FrozenWorld(inst.m1, inst.labels, inst.start, inst.m1.goal,
                     seed=env_seed)
    return m0, m1


def instance_facts(inst):
    """Break pair and oracle costs read from the frozen metadata, so the
    runner never hardcodes seed-7 values."""
    ch = inst.change or {}
    edge = ch.get("edge")
    if isinstance(edge, dict):          # serialized form
        src = edge.get("from")
    elif isinstance(edge, (tuple, list)):  # live PairedInstance form
        src = edge[0]
    else:
        src = None
    break_pair = (src, ch["action"]) if src else None
    return {"break_pair": break_pair,
            "oracle_pre_cost": inst.oracle["pre"]["optimal_cost"],
            "oracle_post_cost": inst.oracle["post"]["optimal_cost"],
            "condition": inst.condition,
            "deterministic": inst.deterministic,
            "change": ch}


def paired_worlds(path=None, condition="silent_break", deterministic=True,
                  seed=7, env_seed=0):
    """(m0, m1) FrozenWorld adapters over the frozen instance."""
    inst, _ = load_pair(path, condition, deterministic, seed)
    return worlds_from_instance(inst, env_seed)


def frozen_sha(path=None):
    """The git commit of the checkout, or None for a zip export."""
    repo = locate(path)
    head = os.path.join(repo, ".git", "HEAD")
    if not os.path.exists(head):
        return None
    ref = open(head).read().strip()
    if ref.startswith("ref:"):
        refpath = os.path.join(repo, ".git", ref.split(" ", 1)[1])
        return open(refpath).read().strip() if os.path.exists(refpath) else None
    return ref


if __name__ == "__main__":
    repo = sys.argv[1] if len(sys.argv) > 1 else None
    m0, m1 = paired_worlds(repo)
    sha = frozen_sha(repo)
    print(f"guard passed, repo at {locate(repo)}")
    print(f"commit: {sha if sha else 'no .git here, confirm 5318c3e on the real checkout'}")
    print(f"start {m0.start}, goal {m0.goal}, pairs {len(m0.legal_pairs())}")

    from agent_loop import AdaptiveMaskPolicy, run_paired
    import break_metrics as bm
    recs = run_paired(m0, m1, AdaptiveMaskPolicy(m0, k=3),
                      episodes_pre=2, episodes_post=2, max_steps=20,
                      run_id="frozen-adaptive")
    s = bm.summarize(recs, ("D", "a2"), m0.goal, 4, 5, m0.legal_pairs())
    bm.print_report("adaptive policy stepping the FROZEN environment", s)

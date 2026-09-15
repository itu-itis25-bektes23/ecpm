"""Local reconstruction of the seed-7 deterministic ECPM instance.

WARNING: this file exists so we can smoke-test the agent loop and the
metrics with zero API calls and without the frozen repo present. The
adjacency, start, goal, break target, and oracle facts below were read
from the frozen repo (schema 2.1, commit 5318c3e) in an earlier session
and are checked again by self_check(). Real runs must still build the
instance with resource_mdp.make_pair(seed=7, ...) on the frozen commit.
This file must never be committed as a replacement for the environment.

Interface contract (matches the frozen design):
  - The agent sees only its current node and an opaque action menu.
  - A successful attempt returns ("OK", next_node).
  - A failed attempt returns ("DROP", same_node). Nothing else leaks.
  - Every executed attempt costs 1. The goal F is absorbing.
"""

from __future__ import annotations

import heapq
import random

# Verified seed-7 deterministic adjacency: node -> {action_label: destination}.
SEED7_DET = {
    "A": {"a1": "D", "a2": "G"},
    "B": {"a1": "D", "a2": "F"},
    "C": {"a1": "E", "a2": "D"},
    "D": {"a1": "A", "a2": "B"},
    "E": {"a1": "C", "a2": "A"},
    "G": {"a1": "A", "a2": "C", "a3": "H"},
    "H": {"a1": "B", "a2": "C"},
}
START = "E"
GOAL = "F"
BREAK_PAIR = ("D", "a2")  # silent break: still listed, p becomes 0


class World:
    """Deterministic-by-default routing world with the frozen observation rules."""

    def __init__(self, adjacency=None, start=START, goal=GOAL, p=None, seed=0):
        self.adj = {u: dict(m) for u, m in (adjacency or SEED7_DET).items()}
        self.start = start
        self.goal = goal
        # success probability per (node, action); default 1.0 (deterministic)
        self.p = dict(p) if p else {(u, a): 1.0 for u in self.adj for a in self.adj[u]}
        self.rng = random.Random(seed)

    # -- construction of the paired instance ------------------------------

    def copy(self):
        w = World(self.adj, self.start, self.goal, self.p)
        return w

    def with_silent_break(self, pair=BREAK_PAIR):
        """M1 variant: the pair stays listed but never succeeds."""
        w = self.copy()
        w.p[pair] = 0.0
        return w

    def with_redirect(self, pair=BREAK_PAIR, new_dest="C"):
        """Sruthi's change type 6: same success rate, different destination.

        Success counting can never catch this. The agent has to notice that
        it arrives somewhere unexpected.
        """
        w = self.copy()
        u, a = pair
        w.adj[u][a] = new_dest
        return w

    # -- dynamics ----------------------------------------------------------

    def menu(self, node):
        return sorted(self.adj.get(node, {}))

    def legal_pairs(self):
        return [(u, a) for u in sorted(self.adj) for a in self.menu(u)]

    def step(self, node, action):
        """Attempt (node, action). Returns (status, next_node) with status
        "OK" or "DROP". Raises on an action not listed at the node."""
        if action not in self.adj.get(node, {}):
            raise ValueError(f"action {action} not listed at {node}")
        if self.rng.random() < self.p[(node, action)]:
            return "OK", self.adj[node][action]
        return "DROP", node

    # -- oracle (evaluator-only) ------------------------------------------

    def oracle(self, source=None):
        """Dijkstra with edge weight 1/p (expected attempts). Returns
        (expected_cost, route) where route is a list of (node, action).
        Pairs with p == 0 are unusable."""
        source = source or self.start
        dist = {source: 0.0}
        prev = {}
        pq = [(0.0, source)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist.get(u, float("inf")):
                continue
            if u == self.goal:
                break
            for a in self.menu(u):
                p = self.p[(u, a)]
                if p <= 0:
                    continue
                v, nd = self.adj[u][a], d + 1.0 / p
                if nd < dist.get(v, float("inf")) - 1e-12:
                    dist[v] = nd
                    prev[v] = (u, a)
                    heapq.heappush(pq, (nd, v))
        if self.goal not in dist:
            return float("inf"), []
        route, node = [], self.goal
        while node != source:
            u, a = prev[node]
            route.append((u, a))
            node = u
        return dist[self.goal], list(reversed(route))


def make_pair(change="silent_break"):
    """(m0, m1) sharing graph, start, goal. change: silent_break | redirect | none."""
    m0 = World()
    if change == "silent_break":
        m1 = m0.with_silent_break()
    elif change == "redirect":
        m1 = m0.with_redirect()
    else:
        m1 = m0.copy()
    return m0, m1


def self_check():
    """Check the reconstruction against the verified oracle facts."""
    m0, m1 = make_pair("silent_break")
    pre_cost, pre_route = m0.oracle()
    post_cost, post_route = m1.oracle()
    assert len(m0.legal_pairs()) == 15, "expected 15 legal state-action pairs"
    assert pre_cost == 4.0, f"pre-change oracle cost should be 4, got {pre_cost}"
    assert post_cost == 5.0, f"post-change oracle cost should be 5, got {post_cost}"
    post_nodes = [u for (u, _) in post_route] + [GOAL]
    assert post_nodes == ["E", "A", "G", "H", "B", "F"], post_nodes
    # the known pre-change tie: both cost-4 routes pass through D and use D a2
    alt = ["E", "C", "D", "B", "F"]
    cost = 0
    node = "E"
    for nxt in alt[1:]:
        act = next(a for a, v in m0.adj[node].items() if v == nxt)
        cost += 1
        node = nxt
    assert cost == 4 and node == GOAL
    return {
        "legal_pairs": 15,
        "pre_cost": pre_cost,
        "pre_route": pre_route,
        "post_cost": post_cost,
        "post_route": post_route,
    }


if __name__ == "__main__":
    facts = self_check()
    print("self check passed:", facts)

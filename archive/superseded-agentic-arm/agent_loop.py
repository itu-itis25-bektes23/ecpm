"""Framework-free agent loop for the ECPM agentic arm.

This is the testable core. It runs episodes with scripted policies and
produces step records in the shared contract below. langgraph_loop.py
wraps the same loop for real language models. break_metrics.py consumes
the records no matter which harness produced them, so Christian's agent
can emit the same records and reuse the metrics unchanged.

Step record contract (one dict per attempted action):
  run_id     str   identifier of the run
  phase      str   "pre" (M0) or "post" (M1)
  episode    int   episode index within the phase, from 0
  t          int   global attempt counter across the whole run, from 1
  node       str   node the packet was at
  menu       list  action labels listed at that node
  action     str   chosen action label
  status     str   "OK" or "DROP"
  next_node  str   node after the attempt
  cost       int   cumulative attempts in this episode so far
  reason     str   optional short model-stated reason, "" for scripted

Belief record (optional, from the self-report hook):
  type "belief", phase, episode, t, estimates {"NODE aK": prob, ...}
"""

from __future__ import annotations

import json
import random


# ---------------------------------------------------------------------------
# Scripted policies. All of them receive the pre-change map as given
# knowledge. That is deliberate: the point of "test the break, not just the
# map" is to hand the agent a perfect map and watch whether behavior updates
# once the map silently stops being true.
# ---------------------------------------------------------------------------

class StalePlannerPolicy:
    """fixed_policy analog: always replans on the original pre-change map.

    Never learns from DROPs. Expected broken-link usage after the break: 1.00.
    """

    def __init__(self, pre_world):
        self.map = {u: dict(m) for u, m in pre_world.adj.items()}
        self.goal = pre_world.goal

    def act(self, node, menu):
        return _bfs_first_action(self.map, node, self.goal), ""

    def observe(self, node, action, status, next_node):
        pass

    def belief(self, pairs):
        return None


class AdaptiveMaskPolicy:
    """Replans on the pre-change map but masks a pair after k DROPs on it.

    The simplest behavior that passes the break test. With k drops observed
    on the broken pair it stops using that pair and reroutes.
    """

    def __init__(self, pre_world, k=3):
        self.map = {u: dict(m) for u, m in pre_world.adj.items()}
        self.goal = pre_world.goal
        self.k = k
        self.drops = {}
        self.masked = set()

    def act(self, node, menu):
        return _bfs_first_action(self.map, node, self.goal, self.masked), ""

    def observe(self, node, action, status, next_node):
        if status == "DROP":
            self.drops[(node, action)] = self.drops.get((node, action), 0) + 1
            if self.drops[(node, action)] >= self.k:
                self.masked.add((node, action))

    def belief(self, pairs):
        """Report 0.0 for masked pairs and 1.0 otherwise. A stand-in for the
        transition-probability self-report Sruthi asked for."""
        return {f"{u} {a}": (0.0 if (u, a) in self.masked else 1.0)
                for (u, a) in pairs}


class EpsilonGreedyPolicy:
    """explore_policy analog: with probability eps take a random listed
    action, otherwise replan like AdaptiveMaskPolicy."""

    def __init__(self, pre_world, eps=0.5, k=3, seed=0):
        self.inner = AdaptiveMaskPolicy(pre_world, k=k)
        self.eps = eps
        self.rng = random.Random(seed)

    def act(self, node, menu):
        if self.rng.random() < self.eps:
            return self.rng.choice(menu), ""
        return self.inner.act(node, menu)

    def observe(self, *args):
        self.inner.observe(*args)

    def belief(self, pairs):
        return self.inner.belief(pairs)


def _bfs_first_action(adj, source, goal, masked=frozenset()):
    """First action of a shortest route on the given (believed) map,
    ignoring masked pairs. Stable tie break by action label. Falls back to
    the first listed action if the goal is unreachable on the believed map."""
    from collections import deque

    if source == goal:
        return None
    prev = {source: None}
    q = deque([source])
    while q:
        u = q.popleft()
        for a in sorted(adj.get(u, {})):
            if (u, a) in masked:
                continue
            v = adj[u][a]
            if v not in prev:
                prev[v] = (u, a)
                if v == goal:
                    q.clear()
                    break
                q.append(v)
    if goal not in prev:
        return sorted(adj.get(source, {}))[0]
    node = goal
    while prev[node][0] != source:
        node = prev[node][0]
    return prev[node][1]


# ---------------------------------------------------------------------------
# Episode runner
# ---------------------------------------------------------------------------

def run_episode(world, policy, phase, episode, records, run_id="local",
                max_steps=20, t0=0, belief_every=None):
    """One episode from world.start to the goal or the step budget.
    Appends step records. Returns (reached_goal, cost, t_final)."""
    node, cost, t = world.start, 0, t0
    while node != world.goal and cost < max_steps:
        menu = world.menu(node)
        action, reason = policy.act(node, menu)
        status, nxt = world.step(node, action)
        cost += 1
        t += 1
        records.append({
            "run_id": run_id, "phase": phase, "episode": episode, "t": t,
            "node": node, "menu": menu, "action": action, "status": status,
            "next_node": nxt, "cost": cost, "reason": reason,
        })
        policy.observe(node, action, status, nxt)
        if belief_every and t % belief_every == 0:
            est = policy.belief(world.legal_pairs())
            if est is not None:
                records.append({"type": "belief", "run_id": run_id,
                                "phase": phase, "episode": episode, "t": t,
                                "estimates": est})
        node = nxt
    return node == world.goal, cost, t


def run_paired(m0, m1, policy, episodes_pre=2, episodes_post=2,
               max_steps=20, run_id="local", belief_every=None):
    """M0 episodes, then a silent switch to M1, same policy object so its
    memory persists across the switch. Returns the list of records."""
    records, t = [], 0
    for e in range(episodes_pre):
        _, _, t = run_episode(m0, policy, "pre", e, records, run_id,
                              max_steps, t, belief_every)
    for e in range(episodes_post):
        _, _, t = run_episode(m1, policy, "post", e, records, run_id,
                              max_steps, t, belief_every)
    return records


def save_jsonl(records, path):
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

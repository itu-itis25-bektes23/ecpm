"""Evidence-only reference agent for the agentic arm: what a simple agent that uses its own evidence would do.

It acts in the same worlds, episodes and step budget as the language-model agents, through the agent loop's
rule-based policy hook (explore_agent.run_explore_instance(node_policy_fn=...)). It sees exactly what a model sees:
the action labels on the menu of its current node and the outcome of each attempt. It never reads the world's
success probabilities. The world object is used only to execute the chosen action, as for a model.

Per action (node, label) it keeps attempts, successes, consecutive failures since the last success and the last
destination seen. Each step:
  - success probability: posterior mean under the generator's prior, uniform on [0.60, 0.95] (400-point grid); in
    deterministic mode, which the models are told about, every working action succeeds and one failure proves a break;
  - probability that the action is broken: posterior after its consecutive failures, prior (2/6)/16 that a given
    action is the broken one (as the H4 threshold in the paper); the action is avoided once this exceeds 0.95;
  - if a route to the goal over actions with known destinations exists, it takes the first step of the route with the
    fewest expected attempts (cost 1 / (p * (1 - P(broken))) per action);
  - otherwise it explores: an untried action at this node, else the least-tried action that is not avoided, else the
    action least likely to be broken.
Memory persists across episodes and across the change, as a model's conversation does.
"""
import heapq

GRID = [0.60 + 0.35 * (i + 0.5) / 400 for i in range(400)]
PRIOR_BROKEN = (2 / 6) / 16
AVOID = 0.95


def posterior_mean(s, f):
    w = [p ** s * (1 - p) ** f for p in GRID]
    z = sum(w)
    return sum(p * x for p, x in zip(GRID, w)) / z if z > 0 else 0.775


def p_broken(consecutive_failures):
    if consecutive_failures == 0:
        return 0.0
    like_ok = sum((1 - p) ** consecutive_failures for p in GRID) / len(GRID)
    return PRIOR_BROKEN / (PRIOR_BROKEN + (1 - PRIOR_BROKEN) * like_ok)


class ReferenceAgent:
    def __init__(self, labels, goal, start, horizon, deterministic=False):
        self.labels, self.goal, self.start, self.horizon = labels, goal, start, horizon
        # The models are told when the world is deterministic; then one failure proves an action broken.
        self.deterministic = deterministic
        self.mem = {}                 # (node, label) -> dict(n, s, consec, dest)
        self.prev = None              # (node, label, intended_dest) of the last attempt
        self.t = 0                    # attempts in the current episode
        self.decisions = []           # (node, label, reason) per attempt, for inspection
        self.menus = {}               # node -> labels on its menu when last visited (kept across phases)

    # ------------------------------------------------------------------ learning from outcomes
    def _record(self, node, label, success, dest=None):
        m = self.mem.setdefault((node, label), dict(n=0, s=0, consec=0, dest=None))
        m["n"] += 1
        if success:
            m["s"] += 1
            m["consec"] = 0
            m["dest"] = dest
        else:
            m["consec"] += 1

    def _observe(self, u):
        """Infer the outcome of the previous attempt from where the agent now stands."""
        if self.prev is None:
            return
        pu, plab, pdest = self.prev
        new_episode = self.t >= self.horizon or (pdest == self.goal and u == self.start and pu != self.start)
        if new_episode:
            if pdest == self.goal and u == self.start:      # the last attempt delivered to the goal
                self._record(pu, plab, True, self.goal)
            self.t = 0                                     # a horizon cutoff leaves the last outcome unknown
        elif u == pu:
            self._record(pu, plab, False)
        else:
            self._record(pu, plab, True, u)
        self.prev = None

    def end_phase(self):
        """Called when the phase ends: the last attempt's outcome is unknown unless it reached the goal."""
        self.prev, self.t = None, 0

    # ------------------------------------------------------------------ choosing
    def _broken(self, m):
        if self.deterministic:
            return 1.0 if m["consec"] > 0 else 0.0
        return p_broken(m["consec"])

    def _cost(self, m):
        p = (1.0 if self.deterministic else posterior_mean(m["s"], m["n"] - m["s"])) * (1 - self._broken(m))
        return 1.0 / max(p, 1e-6)

    def _route_first_step(self, u, menus):
        dist, first, pq = {u: 0.0}, {}, [(0.0, u)]
        while pq:
            d, x = heapq.heappop(pq)
            if x == self.goal:
                return first.get(x)
            if d > dist.get(x, 9e9):
                continue
            for lab in menus.get(x, []):
                m = self.mem.get((x, lab))
                if not m or m["dest"] is None or self._broken(m) > AVOID:
                    continue
                nd = d + self._cost(m)
                if nd < dist.get(m["dest"], 9e9):
                    dist[m["dest"]] = nd
                    first[m["dest"]] = first.get(x, lab) if x != u else lab
                    heapq.heappush(pq, (nd, m["dest"]))
        return None

    def choose(self, u, menu, menus):
        lab = self._route_first_step(u, menus)
        if lab is not None:
            return lab, "route"
        untried = [l for l in menu if (u, l) not in self.mem]
        if untried:
            return sorted(untried)[0], "explore_untried"
        ok = [l for l in menu if self._broken(self.mem[(u, l)]) <= AVOID]
        if ok:
            return min(ok, key=lambda l: (self.mem[(u, l)]["n"], l)), "explore_least_tried"
        return min(menu, key=lambda l: (self._broken(self.mem[(u, l)]), l)), "least_likely_broken"

    # ------------------------------------------------------------------ the loop's node-policy hook
    def factory(self, mdp):
        """node_policy_fn for explore_agent.run_explore_instance: rebuilt per phase, memory kept here."""
        self.end_phase()
        inverse = {(a, lab): b for (a, b), lab in self.labels.items()}

        def policy(u, rng):
            self._observe(u)
            outs = mdp.out_edges(u)
            menu = sorted(self.labels[(u, v)] for v in outs if (u, v) in self.labels)
            self.menus[u] = menu                              # what a model sees at this node
            lab, why = self.choose(u, menu, self.menus)
            dest = inverse[(u, lab)]                          # execution only, as for a model
            self.prev, self.t = (u, lab, dest), self.t + 1
            self.decisions.append((u, lab, why))
            return dest
        return policy

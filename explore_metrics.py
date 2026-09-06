#!/usr/bin/env python3
"""Metrics computed from a completed live-exploration run (explore_agent.py).

Built on resource_mdp's frozen scoring seam (broken_link_usage, score_route),
called unmodified.

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

from resource_mdp import RoutingMDP, broken_link_usage, optimal_ties, score_route


def _outcome_counts(episodes) -> dict:
    """Count episodes by outcome.

    Args:
        episodes: List of EpisodeOutcome.

    Returns:
        {"reached_goal": n, "horizon_cutoff": n, "retries_exhausted": n}.
    """
    counts = {"reached_goal": 0, "horizon_cutoff": 0, "retries_exhausted": 0}
    for ep in episodes:
        counts[ep.outcome] = counts.get(ep.outcome, 0) + 1
    return counts


def _mean(xs) -> float | None:
    """Arithmetic mean of `xs`, or None if `xs` is empty."""
    return sum(xs) / len(xs) if xs else None


def _median(xs) -> float | None:
    """Median of `xs`, or None if `xs` is empty."""
    if not xs:
        return None
    s = sorted(xs)
    n, mid = len(s), len(s) // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def _optimal_action_rate(mdp, steps) -> float | None:
    """Share of steps whose chosen action matched an optimal one.

    Args:
        mdp: The RoutingMDP the steps were taken on.
        steps: List of LiveStep from one episode.

    Returns:
        Fraction in [0, 1] over steps that weren't a "retries_exhausted"
        fallback, or None if every step exhausted retries (nothing to score).
    """
    _, best = mdp.optimal()
    ties = optimal_ties(mdp)
    scored = [s for s in steps if s.parse_status != "retries_exhausted"]
    if not scored:
        return None
    hits = sum(1 for s in scored
              if s.chosen in ties.get(s.node, [best.get(s.node)]))
    return hits / len(scored)


def _episode_action_rates(mdp, episodes) -> list:
    """Per-episode optimal-action rates.

    Args:
        mdp: The RoutingMDP the episodes were run on.
        episodes: List of EpisodeOutcome.

    Returns:
        List of per-episode rates (floats in [0, 1]); episodes with
        nothing to score (see _optimal_action_rate) are skipped.
    """
    rates = [_optimal_action_rate(mdp, ep.steps) for ep in episodes]
    return [r for r in rates if r is not None]


def _route_regrets(mdp, start, episodes) -> list:
    """Regret of the realized route, for episodes that reached the goal.

    Args:
        mdp: The RoutingMDP the episodes were run on.
        start: Start node.
        episodes: List of EpisodeOutcome.

    Returns:
        List of regret values (0 = optimal route), one per episode that
        actually reached the goal on a valid route.
    """
    out = []
    for ep in episodes:
        if ep.outcome != "reached_goal":
            continue
        path = [start] + [s.next_node for s in ep.steps if s.success]
        if path[-1] != mdp.goal:
            continue
        regret = score_route(mdp, path, start)["regret"]
        if regret is not None:
            out.append(regret)
    return out


def _edge_mle(mdp, steps) -> dict:
    """Laplace-smoothed success-rate estimate per edge from `steps` alone
    (0.5 prior for edges never attempted) -- what the model could have
    believed the reliabilities to be, as opposed to the true `mdp.p`.

    Args:
        mdp: RoutingMDP whose edges (mdp.p keys) define the action set.
        steps: List of LiveStep/Attempt to estimate from.

    Returns:
        {(u, v): p_hat} for every edge in mdp.p.
    """
    attempts = {edge: 0 for edge in mdp.p}
    successes = {edge: 0 for edge in mdp.p}
    for s in steps:
        edge = (s.node, s.chosen)
        if edge in attempts:
            attempts[edge] += 1
            successes[edge] += s.success
    return {edge: (successes[edge] + 1) / (attempts[edge] + 2)
           for edge in mdp.p}


def _belief_mdp(mdp, steps) -> RoutingMDP:
    """Same topology as `mdp`, but with true probabilities replaced by the
    model's own MLE belief from `steps` (see _edge_mle). Used to test
    whether later actions track this stale self-derived model rather than
    the (possibly since-changed) real one -- see "Imperfect World Models
    are Exploitable" (arXiv:2605.15960)."""
    return RoutingMDP(mdp.nodes, mdp.goal, _edge_mle(mdp, steps))


def compute_explore_metrics(inst, m0_episodes, m1_episodes) -> dict:
    """Metrics computed from the LiveStep logs, reusing resource_mdp's frozen scoring primitives
    unmodified wherever possible.

    Args:
        inst: The resource_mdp.PairedInstance the episodes were run on.
        m0_episodes: List of EpisodeOutcome from the pre-change phase.
        m1_episodes: List of EpisodeOutcome from the post-change phase.

    Returns:
        Dict of named metrics -- optimal_action_rate_m0/m1,
        broken_link_usage_before/after_first_failure,
        adaptation_lag_steps, steps_to_goal_m0/m1 (mean/median),
        episode_outcome_counts_m0/m1, route_regret_m0/m1,
        parse_failure_rate_m0/m1, retries_exhausted_rate_m0/m1,
        optimal_action_rate_m1_by_m0_belief.
    """
    m0_steps = [s for ep in m0_episodes for s in ep.steps]
    m1_steps = [s for ep in m1_episodes for s in ep.steps]
    m0_belief = _belief_mdp(inst.m0, m0_steps)

    before = after = adaptation_lag = None
    edge = inst.change.get("edge")
    if edge is not None:
        u, v = edge
        # first M1 step where the model tried the now-broken edge and
        # failed -- the split point between "before" and "after" it
        # noticed
        first_fail = next((i for i, s in enumerate(m1_steps)
                           if s.node == u and s.chosen == v
                           and not s.success), None)
        if first_fail is None:
            before = broken_link_usage(m1_steps, u, v)
        else:
            before = broken_link_usage(m1_steps[:first_fail], u, v)
            after = broken_link_usage(m1_steps[first_fail:], u, v)
            # last step that still chose the broken edge, however long
            # after the first failure -- the "how long did it keep
            # trying" signal
            last_use = max((i for i, s in enumerate(m1_steps)
                           if s.node == u and s.chosen == v), default=None)
            if last_use is not None:
                adaptation_lag = max(0, last_use - first_fail)

    def parse_stats(episodes) -> tuple:
        """(parse_failure_rate, retries_exhausted_rate) across all steps in
        `episodes`, or (None, None) if there are no steps."""
        steps = [s for ep in episodes for s in ep.steps]
        if not steps:
            return None, None
        fail = sum(1 for s in steps if s.parse_status != "ok")
        exhausted = sum(1 for s in steps if s.parse_status == "retries_exhausted")
        return fail / len(steps), exhausted / len(steps)

    pf_m0, re_m0 = parse_stats(m0_episodes)
    pf_m1, re_m1 = parse_stats(m1_episodes)

    return {
        "optimal_action_rate_m0": _mean(_episode_action_rates(inst.m0,
                                                              m0_episodes)),
        "optimal_action_rate_m1": _mean(_episode_action_rates(inst.m1,
                                                              m1_episodes)),
        "broken_link_usage_before_first_failure": before,
        "broken_link_usage_after_first_failure": after,
        "adaptation_lag_steps": adaptation_lag,
        "steps_to_goal_m0": {
            "mean": _mean([len(e.steps) for e in m0_episodes
                          if e.outcome == "reached_goal"]),
            "median": _median([len(e.steps) for e in m0_episodes
                              if e.outcome == "reached_goal"])},
        "steps_to_goal_m1": {
            "mean": _mean([len(e.steps) for e in m1_episodes
                          if e.outcome == "reached_goal"]),
            "median": _median([len(e.steps) for e in m1_episodes
                              if e.outcome == "reached_goal"])},
        "episode_outcome_counts_m0": _outcome_counts(m0_episodes),
        "episode_outcome_counts_m1": _outcome_counts(m1_episodes),
        "route_regret_m0": _mean(_route_regrets(inst.m0, inst.start,
                                                m0_episodes)),
        "route_regret_m1": _mean(_route_regrets(inst.m1, inst.start,
                                                m1_episodes)),
        "parse_failure_rate_m0": pf_m0, "parse_failure_rate_m1": pf_m1,
        "retries_exhausted_rate_m0": re_m0, "retries_exhausted_rate_m1": re_m1,
        # high here alongside a low optimal_action_rate_m1 means the model
        # is still planning against its own stale M0 belief, not reality
        "optimal_action_rate_m1_by_m0_belief": _mean(
            _episode_action_rates(m0_belief, m1_episodes)),
    }

#!/usr/bin/env python3
"""Metrics computed from a completed live-exploration run (explore_agent.py).

Uses resource_mdp's frozen planning semantics without rounding intermediate
route costs, and scores changed-action usage by stable action label across
worlds.

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

from resource_mdp import RoutingMDP, optimal_ties


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


def _episode_route_regret(mdp, start, ep):
    """Regret of one episode's realized route (0 = optimal), or None if
    it didn't reach the goal on a valid route."""
    if ep.outcome != "reached_goal":
        return None
    path = [start] + [s.next_node for s in ep.steps if s.success]
    if path[-1] != mdp.goal:
        return None
    cost = mdp.plan_cost(path)
    optimal_cost = mdp.optimal()[0].get(start, float("inf"))
    if cost == float("inf") or optimal_cost == float("inf"):
        return None
    return cost - optimal_cost


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
    regrets = (_episode_route_regret(mdp, start, ep) for ep in episodes)
    return [r for r in regrets if r is not None]


def _per_episode_metrics(mdp, start, episodes) -> list:
    """Per-episode optimal-action rate and route regret, in episode order.

    Args:
        mdp: The RoutingMDP the episodes were run on.
        start: Start node.
        episodes: List of EpisodeOutcome, in run order.

    Returns:
        List of {"episode_idx", "outcome", "optimal_action_rate",
        "route_regret"}, one dict per episode.
    """
    return [{"episode_idx": ep.episode_idx, "outcome": ep.outcome,
            "optimal_action_rate": _optimal_action_rate(mdp, ep.steps),
            "route_regret": _episode_route_regret(mdp, start, ep)}
           for ep in episodes]


def _observed_m0_model(goal, steps):
    """Build a partial reference from M0 feedback and the public goal only.

    Never read evaluator-only chosen destinations or true topology. A
    destination becomes known only after a successful move. Failed-only
    actions retain unknown destinations; unavailable actions and parser
    aborts do not become graph edges. Probabilities use Laplace smoothing.
    This is the posterior mean with a Beta(1, 1) prior in both modes;
    the simulator's mode is not supplied to this reference.
    This is a reference over observed routes, not an elicited LLM belief.
    """
    nodes, actions = {goal}, {}
    for s in steps:
        if s.parse_status != "ok":
            continue
        nodes.add(s.node)
        key = (s.node, s.action_label)
        row = actions.setdefault(key, {"destination": None,
                                       "n_attempts": 0, "n_successes": 0})
        row["n_attempts"] += 1
        if s.success:
            if row["destination"] not in (None, s.next_node):
                raise ValueError(f"m0_destination_conflict: {key}")
            row["destination"] = s.next_node
            row["n_successes"] += 1
            nodes.add(s.next_node)
    edges = {}
    for (node, label), row in actions.items():
        row["p_hat"] = (row["n_successes"] + 1) / (row["n_attempts"] + 2)
        if row["destination"] is not None:
            edge = (node, row["destination"])
            if edge in edges:
                raise ValueError(f"m0_parallel_actions: {node}, {label}")
            edges[edge] = row["p_hat"]
    return RoutingMDP(sorted(nodes), goal, edges), actions


def _m0_observation_agreement(mdp, actions, episodes):
    """Score labels against known M0 routes, with explicit abstention counts.

    Unknown actions/destinations and actions without a known finite route
    are unscorable, not wrong. Each episode with scored decisions receives
    equal weight. M1 destinations and outcomes never update the reference.
    Optimality means minimum expected steps on the known routes, without a
    horizon cutoff, using point estimates of the success probabilities.
    """
    dist, _ = mdp.optimal()
    skipped = {"unobserved_action": 0, "unknown_destination": 0,
               "no_known_route": 0}
    per_episode = []
    for ep in episodes:
        scores, n_steps = [], 0
        for s in ep.steps:
            if s.parse_status == "retries_exhausted":
                continue
            n_steps += 1
            row = actions.get((s.node, s.action_label))
            if row is None:
                skipped["unobserved_action"] += 1
            elif row["destination"] is None:
                skipped["unknown_destination"] += 1
            elif (dist.get(s.node, float("inf")) == float("inf")
                  or dist.get(row["destination"], float("inf")) == float("inf")):
                skipped["no_known_route"] += 1
            else:
                cost = 1 / row["p_hat"] + dist[row["destination"]]
                scores.append(abs(cost - dist[s.node]) < 1e-9)
        per_episode.append({"episode_idx": ep.episode_idx,
                            "rate": _mean(scores), "n_steps": n_steps,
                            "n_scored_steps": len(scores),
                            "n_skipped_steps": n_steps - len(scores)})
    rates = [row["rate"] for row in per_episode if row["rate"] is not None]
    coverage = {"n_steps": sum(row["n_steps"] for row in per_episode),
                "n_scored_steps": sum(row["n_scored_steps"] for row in per_episode),
                "n_skipped_steps": sum(skipped.values()),
                "n_scored_episodes": len(rates),
                "skipped_by_reason": skipped, "per_episode": per_episode}
    return _mean(rates), coverage


def compute_explore_metrics(inst, m0_episodes, m1_episodes) -> dict:
    """Metrics computed from LiveStep logs using the frozen MDP semantics.

    Args:
        inst: The resource_mdp.PairedInstance the episodes were run on.
        m0_episodes: List of EpisodeOutcome from the pre-change phase.
        m1_episodes: List of EpisodeOutcome from the post-change phase.

    Returns:
        Dict of named metrics -- goal_success_rate_m0/m1 (None when empty),
        n_episodes_m0/m1 (denominators including all episode outcomes),
        optimal_action_rate_m0/m1 and their scored-episode counts,
        changed_action_usage, changed_action_switch,
        steps_to_goal_m0/m1 (mean/median),
        episode_outcome_counts_m0/m1, route_regret_m0/m1 and their valid-route
        counts,
        parse_failure_rate_m0/m1, retries_exhausted_rate_m0/m1,
        illegal_action_rate_m0/m1,
        m0_reference_action_agreement_m1, m0_observation_reference,
        m0_reference_agreement_coverage_m1, per_episode_m0/m1.
    """
    m0_steps = [s for ep in m0_episodes for s in ep.steps]
    # Usage and lag count executed actions, not parser-abort diagnostics.
    # Keep the original episodes intact for parse and outcome statistics.
    m1_steps = [s for ep in m1_episodes for s in ep.steps
                if s.parse_status != "retries_exhausted"]
    m0_reference, m0_actions = _observed_m0_model(inst.m0.goal, m0_steps)
    m0_agreement, m0_coverage = _m0_observation_agreement(
        m0_reference, m0_actions, m1_episodes)

    def usage(steps, node, label):
        decisions = [s for s in steps if s.node == node
                     and s.parse_status != "retries_exhausted"]
        choices = sum(s.action_label == label for s in decisions)
        return {"rate": choices / len(decisions) if decisions else None,
                "n_choices": choices, "n_decisions": len(decisions)}

    action_switch = {"version": "first_legal_alternative_after_feedback_v1",
                     "status": "no_reference_event", "decision_lag": None,
                     "n_decisions_after_feedback": 0,
                     "n_actions_after_feedback": 0,
                     "episode_idx": None, "t": None,
                     "changed_action_available": None}
    changed_usage = {"version": "action_label_phase_usage_v1",
                     "node": None, "action_label": None,
                     "m0": None, "m1": None, "after_feedback": None,
                     "feedback_event": {"status": "not_applicable"}}
    edge = inst.change.get("edge")
    if edge is not None:
        u, v = edge
        label = inst.labels[(u, v)]
        changed_usage.update(node=u, action_label=label,
                             m0=usage(m0_steps, u, label),
                             m1=usage(m1_steps, u, label))
        # This is an observed failure, not evidence of recognized change.
        first_fail = next((i for i, s in enumerate(m1_steps)
                           if s.node == u and s.action_label == label
                           and not s.success), None)
        event = {"status": "not_observed", "kind": None,
                 "episode_idx": None, "t": None, "n_actions_before_feedback": None}
        boundary = None
        if inst.condition == "hard_removal":
            event["kind"] = "menu_action_absent"
            # Every policy call renders the menu, even when parsing aborts.
            # A previous M0 visit establishes that the action was available.
            if not any(s.node == u for s in m0_steps):
                event["status"] = "missing_m0_menu_observation"
            else:
                executed = 0
                for ep in m1_episodes:
                    for s in ep.steps:
                        if s.node == u:
                            boundary = executed
                            event.update(status="observed", episode_idx=ep.episode_idx,
                                         t=s.t, n_actions_before_feedback=boundary)
                            break
                        executed += s.parse_status != "retries_exhausted"
                    if boundary is not None:
                        break
        elif inst.condition == "redirect":
            event["kind"] = "destination_mismatch"
            old = m0_actions.get((u, label), {}).get("destination")
            if old is None:
                event["status"] = "missing_m0_destination_observation"
            else:
                for i, s in enumerate(m1_steps):
                    if (s.node == u and s.action_label == label
                            and s.success and s.next_node != old):
                        boundary = i + 1
                        event.update(status="observed", episode_idx=s.episode_idx,
                                     t=s.t, n_actions_before_feedback=boundary)
                        break
        else:
            event["kind"] = "first_failure"
            if first_fail is not None:
                s = m1_steps[first_fail]
                boundary = first_fail + 1
                event.update(status="observed", episode_idx=s.episode_idx,
                             t=s.t, n_actions_before_feedback=boundary)
        changed_usage["feedback_event"] = event
        if boundary is not None:
            following = m1_steps[boundary:]
            changed_usage["after_feedback"] = usage(following, u, label)
            decisions = [s for s in following if s.node == u]
            action_switch.update(
                status="no_opportunity" if not decisions else "not_observed_before_end",
                n_decisions_after_feedback=len(decisions),
                n_actions_after_feedback=len(following),
                changed_action_available=inst.condition != "hard_removal")
            # Illegal choices consume an opportunity but are not a legal
            # alternative strategy. Parsing aborts were already excluded.
            for i, s in enumerate(decisions, 1):
                if s.action_label != label and s.parse_status == "ok":
                    action_switch.update(status="switch_observed", decision_lag=i,
                                         episode_idx=s.episode_idx, t=s.t)
                    break

    def parse_stats(episodes) -> tuple:
        """Format-error and abort rates per decision record, including
        corrected replies and final aborts. Illegal choices alone are not
        format errors. Return (None, None) when there are no records."""
        steps = [s for ep in episodes for s in ep.steps]
        if not steps:
            return None, None
        fail = sum(1 for s in steps if s.retries > 0 or s.parse_status in
                   ("malformed_json", "invalid_object", "retries_exhausted"))
        exhausted = sum(1 for s in steps if s.parse_status == "retries_exhausted")
        return fail / len(steps), exhausted / len(steps)

    pf_m0, re_m0 = parse_stats(m0_episodes)
    pf_m1, re_m1 = parse_stats(m1_episodes)
    action_rates_m0 = _episode_action_rates(inst.m0, m0_episodes)
    action_rates_m1 = _episode_action_rates(inst.m1, m1_episodes)
    route_regrets_m0 = _route_regrets(inst.m0, inst.start, m0_episodes)
    route_regrets_m1 = _route_regrets(inst.m1, inst.start, m1_episodes)
    successful_steps_m0 = [len(e.steps) for e in m0_episodes
                           if e.outcome == "reached_goal"]
    successful_steps_m1 = [len(e.steps) for e in m1_episodes
                           if e.outcome == "reached_goal"]

    def illegal_rate(steps):
        """Share of executed attempts with unavailable actions, excluding aborts."""
        return _mean([s.parse_status == "illegal_action" for s in steps
                      if s.parse_status != "retries_exhausted"])

    return {
        "goal_success_rate_m0": _mean([e.outcome == "reached_goal"
                                       for e in m0_episodes]),
        "goal_success_rate_m1": _mean([e.outcome == "reached_goal"
                                       for e in m1_episodes]),
        "n_episodes_m0": len(m0_episodes),
        "n_episodes_m1": len(m1_episodes),
        "optimal_action_rate_m0": _mean(action_rates_m0),
        "optimal_action_rate_m1": _mean(action_rates_m1),
        "optimal_action_rate_n_scored_episodes_m0": len(action_rates_m0),
        "optimal_action_rate_n_scored_episodes_m1": len(action_rates_m1),
        "changed_action_usage": changed_usage,
        "changed_action_switch": action_switch,
        "steps_to_goal_m0": {
            "mean": _mean(successful_steps_m0),
            "median": _median(successful_steps_m0),
            "n_successful_episodes": len(successful_steps_m0)},
        "steps_to_goal_m1": {
            "mean": _mean(successful_steps_m1),
            "median": _median(successful_steps_m1),
            "n_successful_episodes": len(successful_steps_m1)},
        "episode_outcome_counts_m0": _outcome_counts(m0_episodes),
        "episode_outcome_counts_m1": _outcome_counts(m1_episodes),
        "route_regret_m0": _mean(route_regrets_m0),
        "route_regret_m1": _mean(route_regrets_m1),
        "route_regret_n_valid_routes_m0": len(route_regrets_m0),
        "route_regret_n_valid_routes_m1": len(route_regrets_m1),
        "parse_failure_rate_m0": pf_m0, "parse_failure_rate_m1": pf_m1,
        "retries_exhausted_rate_m0": re_m0, "retries_exhausted_rate_m1": re_m1,
        "illegal_action_rate_m0": illegal_rate(m0_steps),
        "illegal_action_rate_m1": illegal_rate(m1_steps),
        # Agreement with a partial reference is not proof of an internal belief.
        "m0_reference_action_agreement_m1": m0_agreement,
        "m0_observation_reference": {
            "version": "observed_transitions_laplace_v1",
            "goal": inst.m0.goal,
            "actions": [{"node": node, "action_label": label, **row}
                        for (node, label), row in sorted(m0_actions.items())]},
        "m0_reference_agreement_coverage_m1": m0_coverage,
        "per_episode_m0": _per_episode_metrics(inst.m0, inst.start,
                                              m0_episodes),
        "per_episode_m1": _per_episode_metrics(inst.m1, inst.start,
                                              m1_episodes),
    }

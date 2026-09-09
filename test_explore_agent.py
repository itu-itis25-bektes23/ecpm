"""Acceptance tests for explore_agent.py (live self-exploration loop).

Run:  python3 test_explore_agent.py     (stdlib only, no network)

Covers:
  - extract_last_json_object returns the LAST balanced object, contrasted
    directly against ecpm_parser.extract_json_object's FIRST, on the same
    fixture text
  - parse_step_action status coverage (ok / malformed_json / invalid_object
    / illegal_action)
  - LiveStep objects fed unmodified into resource_mdp's frozen attempt-list
    consumers (broken_link_usage, emit_f1_log, emit_f2_triples,
    attempt_stats) to prove Attempt-compatible duck typing
  - a full dry-run run_explore_instance on the seed-7 silent_break matched
    pair: M0 and M1 each run their full, fixed episode budget, every M1
    attempt at the broken edge fails, and same-seed runs reproduce
    identically
"""

import json

from ecpm_parser import extract_json_object
from explore_agent import (ExploreConfig, LiveStep, dry_run_policy,
                           extract_last_json_object, parse_step_action,
                           run_explore_instance)
from explore_metrics import compute_explore_metrics
from resource_mdp import (attempt_stats, broken_link_usage, emit_f1_log,
                          emit_f2_triples, fixed_policy, make_pair)


def test_extract_last_json_object():
    """Verifies extract_last_json_object takes the LAST balanced JSON
    object in free text, contrasted with ecpm_parser.extract_json_object's
    FIRST-match behavior on the same fixtures."""
    text = 'reasoning {"action": "a1"} more reasoning {"action": "a2"}'
    assert extract_json_object(text) == {"action": "a1"}
    assert extract_last_json_object(text) == {"action": "a2"}
    # single object: both agree
    single = 'I choose ```json\n{"action": "a3"}\n``` because reasons'
    assert extract_json_object(single) == {"action": "a3"}
    assert extract_last_json_object(single) == {"action": "a3"}
    # no object at all
    assert extract_last_json_object("no json here") is None
    assert extract_last_json_object(123) is None
    print("PASS extract_last_json_object (last-match, contrasted with "
         "ecpm_parser's first-match)")


def test_parse_step_action():
    """Verifies parse_step_action's full status coverage: ok,
    malformed_json, invalid_object, illegal_action."""
    menu = ["a1", "a2", "a3"]
    ok = parse_step_action('thinking... {"action": "a2"}', menu)
    assert ok == {"status": "ok", "action": "a2"}
    assert parse_step_action("no json object", menu) == \
        {"status": "malformed_json"}
    assert parse_step_action('{"foo": "bar"}', menu) == \
        {"status": "invalid_object"}
    assert parse_step_action('{"action": 7}', menu) == \
        {"status": "invalid_object"}
    illegal = parse_step_action('{"action": "a9"}', menu)
    assert illegal["status"] == "illegal_action" and illegal["action"] == "a9"
    print("PASS parse_step_action (ok / malformed_json / invalid_object / "
         "illegal_action)")


def test_livestep_duck_typing():
    """Verifies a list of LiveStep can be fed unmodified into
    resource_mdp's frozen Attempt-list consumers (broken_link_usage,
    emit_f1_log, emit_f2_triples, attempt_stats)."""
    steps = [
        LiveStep(t=1, node="A", chosen="B", success=True, next_node="B",
                phase="m1", episode_idx=0, action_label="a1",
                parse_status="ok", retries=0, raw_text='{"action":"a1"}'),
        LiveStep(t=2, node="A", chosen="B", success=False, next_node="A",
                phase="m1", episode_idx=0, action_label="a1",
                parse_status="ok", retries=0, raw_text='{"action":"a1"}'),
        LiveStep(t=3, node="B", chosen="C", success=True, next_node="C",
                phase="m1", episode_idx=0, action_label="a1",
                parse_status="ok", retries=0, raw_text='{"action":"a1"}'),
    ]
    # broken_link_usage: among visits to A, share still choosing B
    usage = broken_link_usage(steps, "A", "B")
    assert usage == 1.0, usage
    # emit_f1_log / emit_f2_triples run without error over LiveStep objects
    f1 = emit_f1_log(steps)
    assert "OK, arrive B" in f1 and "DROP, stay A" in f1
    f2 = emit_f2_triples(steps)
    assert f2.count("(A, ->B, B)") == 1
    # attempt_stats over a list of LiveStep "episodes"
    tries, okc = attempt_stats([steps])
    assert tries[("A", "B")] == 2 and okc[("A", "B")] == 1
    print("PASS LiveStep duck-typed unmodified into broken_link_usage / "
         "emit_f1_log / emit_f2_triples / attempt_stats")


def _run(seed=7, **cfg_kwargs):
    """Shared helper: builds a matched silent_break pair for the given
    seed and runs a dry-run exploration instance over it."""
    inst = make_pair(seed, "silent_break", deterministic=True, matched=True)
    cfg = ExploreConfig(max_episodes_m0=4, max_episodes_m1=3,
                        max_steps_per_episode=20,
                        seed=seed, **cfg_kwargs)
    result = run_explore_instance(
        inst, cfg,
        node_policy_fn=lambda mdp: dry_run_policy(mdp, inst.labels, eps=0.0))
    return inst, cfg, result


def test_run_explore_instance_dry_run():
    """Verifies a full dry-run run_explore_instance on the seed-7
    silent_break pair: M0 and M1 each run their configured episode
    budget, and every M1 attempt at the broken edge fails."""
    inst, cfg, result = _run()
    m0, m1 = result["m0_episodes"], result["m1_episodes"]

    assert len(m0) == cfg.max_episodes_m0
    assert len(m1) == cfg.max_episodes_m1

    # A perfectly-adapted M1 policy (eps=0.0 against the POST-change world)
    # already routes around the break, so it may legitimately never even
    # attempt it -- but IF it ever does, that attempt must still fail
    # (p -> 0 in m1). The guaranteed-attempt case (a stale policy that
    # keeps choosing the broken edge) is covered separately in
    # test_broken_edge_always_fails_when_attempted.
    u, v = inst.change["edge"]
    m1_steps = [s for ep in m1 for s in ep.steps]
    broken_attempts = [s for s in m1_steps if s.node == u and s.chosen == v]
    assert all(not s.success for s in broken_attempts)

    metrics = compute_explore_metrics(inst, m0, m1)
    assert metrics["optimal_action_rate_m0"] == 1.0
    assert metrics["parse_failure_rate_m0"] == 0.0
    assert metrics["retries_exhausted_rate_m0"] == 0.0
    print(f"PASS run_explore_instance dry-run: M0 ran {len(m0)} episodes, "
         f"M1 ran {len(m1)} episodes, {len(broken_attempts)} attempts at "
         f"the broken edge {u}->{v}, all failed")


def test_dry_run_reaches_goal_e_to_f_deterministic():
    """Verifies the no-LLM (eps-greedy) policy actually reaches the goal:
    on the fixed seed-7 instance (start E, goal F) in deterministic mode,
    every M0 and M1 episode ends with outcome == reached_goal."""
    inst, cfg, result = _run(seed=7)
    assert inst.start == "E"
    assert inst.m0.goal == "F" and inst.m1.goal == "F"
    for ep in result["m0_episodes"] + result["m1_episodes"]:
        assert ep.outcome == "reached_goal", (ep.phase, ep.episode_idx,
                                              ep.outcome)
    print("PASS dry-run (no LLM) reaches the goal E->F on every M0/M1 "
         "episode, deterministic, seed=7")


def test_dry_run_reaches_goal_e_to_f_stochastic():
    """Verifies the no-LLM (eps-greedy) policy still reliably reaches the
    goal once healthy links can fail (deterministic=False): on the same
    seed-7 instance (start E, goal F), with a generous step budget, at
    least 90% of M0/M1 episodes end with outcome == reached_goal. Unlike
    the deterministic case, a single unlucky run of failures can still
    exhaust the step budget, so this checks a rate instead of every
    episode."""
    inst = make_pair(7, "silent_break", deterministic=False, matched=True)
    assert inst.start == "E"
    assert inst.m0.goal == "F" and inst.m1.goal == "F"
    cfg = ExploreConfig(max_episodes_m0=20, max_episodes_m1=20,
                        max_steps_per_episode=60, seed=7)
    result = run_explore_instance(
        inst, cfg,
        node_policy_fn=lambda mdp: dry_run_policy(mdp, inst.labels, eps=0.0))
    episodes = result["m0_episodes"] + result["m1_episodes"]
    reached = sum(1 for ep in episodes if ep.outcome == "reached_goal")
    rate = reached / len(episodes)
    assert rate >= 0.9, f"only {reached}/{len(episodes)} episodes reached the goal"
    print(f"PASS dry-run (no LLM) reaches the goal E->F in stochastic "
         f"mode: {reached}/{len(episodes)} episodes ({rate:.0%}), seed=7")


def test_broken_edge_always_fails_when_attempted():
    """A stale M1 policy (the frozen PRE-change optimum) keeps choosing
    the now-broken edge -- silent_break leaves it listed with p=0, so
    fixed_policy() never falls back off it. This guarantees at least one
    attempt, so unlike test_run_explore_instance_dry_run's fully-adapted
    policy, the "every attempt fails" invariant is exercised for real."""
    inst = make_pair(7, "silent_break", deterministic=True, matched=True)
    cfg = ExploreConfig(max_episodes_m0=1, max_episodes_m1=2,
                        max_steps_per_episode=20, seed=7)
    pre_best = inst.m0.optimal()[1]

    def node_policy_fn(mdp):
        if mdp is inst.m0:
            return dry_run_policy(mdp, inst.labels, eps=0.0)
        return fixed_policy(pre_best, mdp)

    result = run_explore_instance(inst, cfg, node_policy_fn=node_policy_fn)
    m1_steps = [s for ep in result["m1_episodes"] for s in ep.steps]
    u, v = inst.change["edge"]
    broken_attempts = [s for s in m1_steps if s.node == u and s.chosen == v]
    assert broken_attempts, "stale policy should probe the broken edge"
    assert all(not s.success for s in broken_attempts)

    metrics = compute_explore_metrics(inst, result["m0_episodes"],
                                      result["m1_episodes"])
    assert metrics["broken_link_usage_after_first_failure"] is not None
    print(f"PASS stale M1 policy always fails on the broken edge "
         f"({len(broken_attempts)} attempts), "
         f"adaptation_lag_steps={metrics['adaptation_lag_steps']}")


def test_reproducibility():
    """Verifies that running the same seed twice produces an identical
    transcript and step log."""
    _, _, result1 = _run(seed=11)
    _, _, result2 = _run(seed=11)
    assert result1["messages"] == result2["messages"]
    steps1 = [(s.node, s.chosen, s.success) for ep in result1["m1_episodes"]
             for s in ep.steps]
    steps2 = [(s.node, s.chosen, s.success) for ep in result2["m1_episodes"]
             for s in ep.steps]
    assert steps1 == steps2
    print("PASS same-seed run_explore_instance reproduces an identical "
         "transcript and step log")


if __name__ == "__main__":
    test_extract_last_json_object()
    test_parse_step_action()
    test_livestep_duck_typing()
    test_run_explore_instance_dry_run()
    test_dry_run_reaches_goal_e_to_f_deterministic()
    test_dry_run_reaches_goal_e_to_f_stochastic()
    test_broken_edge_always_fails_when_attempted()
    test_reproducibility()
    print("\nALL EXPLORE-AGENT TESTS PASSED")

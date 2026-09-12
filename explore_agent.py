#!/usr/bin/env python3
"""Active-exploration agent loop (live LLM policy over RoutingMDP).

A live, multi-turn loop where the model itself picks an action at each
step, observes the real outcome, and repeats across several episodes on
the pre-change world (M0), then several more on the
post-change world (M1).

Design notes:
  * One system prompt, then per-step observations as user messages, with
    the chosen action parsed from free text.
  * `LiveStep` is attribute-compatible with resource_mdp.Attempt (t,
    node, chosen, success, next_node), so it can be passed unmodified
    into resource_mdp's scoring primitives (used by explore_metrics.py).
  * No network I/O here. `run_explore_instance` takes either a real
    (retrying) `act_fn(system_prompt, messages) -> (raw_text, reasoning)`
    or a network-free `dry_run_policy(...)`-built node policy, so the
    whole loop is unit-testable without an API key. `reasoning` is a
    separate string for providers with a distinct reasoning channel
    (e.g. Claude Extended Thinking); pass "" when there is none.

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from typing import Callable

from ecpm_parser import extract_json_object  # noqa: F401  (kept for parity/reference; step-level parsing uses extract_last_json_object below)
from resource_mdp import (PolicyAborted, explore_policy, invert_labels,
                          legal_actions, rollout)


# --------------------------------------------------------------------------
# Records
# --------------------------------------------------------------------------


@dataclass
class LiveStep:
    """One live, model-chosen step. The first five fields exactly match
    resource_mdp.Attempt's shape (t, node, chosen, success, next_node), so a list of LiveStep is a drop-in
    replacement anywhere an Attempt list is expected."""
    t: int                  # step number in the episode
    node: str                # node the model was at
    chosen: str              # node it tried to move to
    success: bool             # did the move work?
    next_node: str            # node it's at now
    phase: str              # "m0" | "m1"
    episode_idx: int         # which episode (0-based)
    action_label: str       # the 'aK' label the model actually chose
    parse_status: str       # ok | malformed_json | invalid_object | illegal_action | retries_exhausted
    retries: int              # correction attempts before this action was accepted
    raw_text: str             # model's full reply for this step
    reasoning: str = ""      # model's reasoning for this step, kept separate from raw_text (empty for dry-run and for providers without a separate reasoning channel)


@dataclass
class EpisodeOutcome:
    """Summary of one exploration episode: its full step log, plus whether
    it reached the goal. An episode is a complete attempt to get from the start to the goal."""
    episode_idx: int          # which episode (0-based)
    phase: str                # "m0" | "m1"
    steps: list = field(default_factory=list)   # all LiveSteps in this episode
    outcome: str = "horizon_cutoff"      # reached_goal | horizon_cutoff | retries_exhausted


@dataclass
class ExploreConfig:
    """Tunable settings for one live-exploration run: episode/step
    budgets, early-stop and retry thresholds, context trimming, seed."""
    max_episodes_m0: int = 4            # max episodes on the pre-change world
    max_episodes_m1: int = 4            # episodes on the post-change world (always runs all of them)
    max_steps_per_episode: int = 25     # step limit per episode
    max_retries_per_step: int = 2       # retries for a bad action before giving up
    announce_change: bool = False       # tell the model the world may have changed (ablation)
    max_context_tokens_est: int = 12000  # trim old turns once the transcript gets this big
    keep_last_n_turns_min: int = 6      # never trim below this many recent turns
    seed: int = 0                       # base seed for reproducible runs


# --------------------------------------------------------------------------
# Per-step action parsing
# --------------------------------------------------------------------------


def extract_last_json_object(text) -> dict | None:
    """Extract the last valid JSON object from free-form text.

    Scans `text` for balanced {...} blocks (brace-depth tracking, aware
    of quoted strings) and tries to JSON-parse each one. Keeps the LAST
    one that parses successfully into a dict.
    This matches a "reason, then answer" convention where the model
    may think in prose before committing to a final action.

    Args:
        text: Raw model output to scan. Non-string input returns None.

    Returns:
        The last successfully parsed JSON object as a dict, or None if no
        balanced, parseable object was found.
    """
    if not isinstance(text, str):
        return None
    found = None
    i = text.find("{")
    while i != -1:
        depth, in_str, esc = 0, False, False
        for j in range(i, len(text)):
            c = text[j]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[i:j + 1])
                        if isinstance(obj, dict):
                            found = obj
                    except json.JSONDecodeError:
                        pass
                    break
        i = text.find("{", i + 1)
    return found


def parse_step_action(text, legal_menu) -> dict:
    """Parse a single-step action choice from free-form LLM text.

    Extracts the last JSON object from `text` (via
    extract_last_json_object) and validates it against the current
    node's legal action menu.

    Args:
        text: Raw model output for this step.
        legal_menu: List of legal 'aK' labels at the current node.

    Returns:
        {"status": "ok", "action": "aK"} on success, or a status-only
        dict with status one of malformed_json | invalid_object |
        illegal_action (illegal_action also includes the offending
        "action" value).
    """
    obj = extract_last_json_object(text)
    if obj is None:
        return {"status": "malformed_json"}
    action = obj.get("action")
    if not isinstance(action, str):
        return {"status": "invalid_object"}
    if action not in legal_menu:
        return {"status": "illegal_action", "action": action}
    return {"status": "ok", "action": action}


# --------------------------------------------------------------------------
# Prompt / message construction
# --------------------------------------------------------------------------


def build_system_prompt(goal) -> str:
    return (
        "You are exploring an unfamiliar courier network of locations "
        "connected by one-way links. At each location you may attempt one "
        "of the listed actions (aK). An attempt either delivers you to "
        "that action's destination, or fails and you stay where you are "
        "-- either way it costs one step. You do not know the network's "
        "structure or reliabilities in advance: you must learn them by "
        "trying actions and observing what happens. Your goal is to reach "
        f"{goal} in as few steps as possible, across several episodes. "
        "The network's reliabilities may or may not change between "
        "episodes; nothing will tell you this directly -- watch your own "
        "outcomes. For every step: you may reason briefly first, but end "
        'your reply with exactly one JSON object of the form '
        '{"action": "aK"} naming the single action you choose. Output no '
        "other JSON object in your reply."
    )


def render_step_observation(node, menu, steps_left, last_result=None,
                            note=None) -> str:
    """Build the text of one per-step observation message shown to the
    model.

    Assembles, in order: an optional note, feedback on the previous
    action's outcome, the current position and remaining step budget,
    the legal action menu, and the required JSON answer format.

    Args:
        node: The node the model is currently at.
        menu: List of legal 'aK' labels available at `node`.
        steps_left: Steps remaining in the current episode.
        last_result: Optional (label, success) tuple describing the
            outcome of the previous action.
        note: Optional extra line prepended to the message (e.g. a
            phase-transition note).

    Returns:
        The observation text as a single string, ready to be sent as a
        user message.
    """
    lines = []
    if note:
        lines.append(note)
    if last_result is not None:
        label, success = last_result
        outcome = "succeeded (you moved)" if success else "failed (you stayed)"
        lines.append(f"Your last action {label} {outcome}.")
    lines.append(f"You are at {node}. Steps remaining this episode: "
                f"{steps_left}.")
    lines.append(f"Legal actions here: {', '.join(menu)}.")
    lines.append('Choose one. End your reply with exactly one JSON object: '
                '{"action": "aK"}.')
    return "\n".join(lines)


def trim_history(messages, max_tokens_est, keep_last_n_turns_min) -> list:
    """Trim old turns from the message history to stay within budget.

    FIFO-drops the oldest complete user/assistant turn pairs once the
    estimated token count exceeds max_tokens_est.

    Args:
        messages: Full user/assistant turn history (no system entries).
        max_tokens_est: Token budget, estimated as len(text)//4
            (same heuristic run_pilot.py uses for prompt_tokens_est).
        keep_last_n_turns_min: Minimum number of most recent turn pairs
            to always keep, regardless of the token estimate.

    Returns:
        The (possibly shortened) message list, oldest pairs dropped
        first.
    """
    def est_tokens(msgs) -> int:
        return sum(len(m["content"]) for m in msgs) // 4

    pairs, i = [], 0
    while i + 1 < len(messages):
        pairs.append(messages[i:i + 2])
        i += 2
    tail = messages[i:]

    while (len(pairs) > keep_last_n_turns_min
           and est_tokens([m for p in pairs for m in p] + tail)
           > max_tokens_est):
        pairs.pop(0)
    return [m for p in pairs for m in p] + tail


# --------------------------------------------------------------------------
# Policies: a live-LLM policy and a network-free dry-run stand-in, both
# exposed as rollout()-compatible policy(u, rng) -> node once wrapped by
# _build_recording_policy below.
# --------------------------------------------------------------------------


def dry_run_policy(mdp, labels, eps=0.15) -> Callable:
    """Build a network-free, eps-greedy replacement for a live LLM.

    Wraps resource_mdp.explore_policy directly (no new policy logic),
    for smoke-testing the exploration loop without any API calls."""
    return explore_policy(mdp, eps=eps)


def _build_recording_policy(mdp, labels, cfg, messages, step_meta, *,
                            act_fn=None, system_prompt=None,
                            node_policy=None, initial_note=None,
                            abort_info=None) -> Callable:
    """Build the per-step policy that selects and logs one action at a
    time.

    Two mutually exclusive action sources are supported:
        - a retrying LLM call (`act_fn`)
        - a plain node-choosing heuristic (`node_policy`, e.g. from dry_run_policy)
    Whichever source is given, the result is wrapped into one `policy(u, rng) -> node`
    function. Along the way it appends the observation/response turns to
    `messages` and one metadata entry per call to `step_meta` (both
    mutated in place). rollout() calls the returned policy exactly once
    per Attempt, so the two lists stay in lockstep with rollout()'s own
    Attempt list.

    Args:
        mdp: The RoutingMDP being explored in this phase.
        labels: (u, v) -> 'aK' label mapping for this instance.
        cfg: ExploreConfig with the step/retry/context settings to use.
        messages: Shared, growing user/assistant transcript (mutated).
        step_meta: Shared list to append one metadata dict per step to
            (mutated); zipped with rollout()'s Attempt list afterward.
        act_fn: LLM call function (system, messages) -> (raw_text,
            reasoning). Give exactly one of act_fn or node_policy.
        system_prompt: System prompt to pass to act_fn (required if
            act_fn is given).
        node_policy: A plain policy(u, rng) -> node (e.g. from
            dry_run_policy) to use instead of a real LLM. Give exactly
            one of act_fn or node_policy.
        initial_note: Optional note shown only on the first step (e.g. a
            phase-transition message).
        abort_info: Optional dict (mutated in place) that gets filled
            with {"node", "retries", "raw_text", "reasoning"} the moment
            the policy gives up and raises resource_mdp.PolicyAborted,
            so the caller can tell an abort apart from a normal
            horizon cutoff after rollout() returns.

    Returns:
        A policy(u, rng) -> node callable (same contract
        resource_mdp.rollout() expects).
    """
    assert (act_fn is None) != (node_policy is None), \
        "give exactly one of act_fn, node_policy"
    menu_cache = legal_actions(mdp, labels)   # node -> legal 'aK' labels, computed once
    inv = invert_labels(labels, mdp)          # (node, "aK") -> destination node in THIS world
    prev = {"label": None, "target": None}    # last action taken, used to detect success/failure next call
    first_call = [True]                       # whether initial_note still needs to be shown

    def policy(u, rng) -> str:
        menu = menu_cache.get(u, [])

        # rollout() never tells us whether the last action succeeded;
        # infer it by comparing where we ended up (u) to where the last
        # action was aiming (prev["target"]).
        last_result = None
        if prev["label"] is not None:
            last_result = (prev["label"], u == prev["target"])
        note = initial_note if first_call[0] else None
        first_call[0] = False
        steps_left = cfg.max_steps_per_episode - len(step_meta)
        obs = render_step_observation(u, menu, steps_left,
                                      last_result=last_result, note=note)
        messages.append({"role": "user", "content": obs})   # log the observation turn

        if node_policy is not None:
            # dry-run path: no real model call, just fabricate a
            # matching JSON reply so the rest of the function stays uniform for both paths
            v = node_policy(u, rng)
            action_label = labels.get((u, v))
            raw = json.dumps({"action": action_label})
            reasoning = ""
            status, retries = "ok", 0
        else:
            # live-model path: ask, parse, and retry on a bad reply up to max_retries_per_step times
            trimmed = trim_history(messages, cfg.max_context_tokens_est,
                                   cfg.keep_last_n_turns_min)
            retries = 0
            parsed = {"status": "malformed_json"}
            raw, reasoning = "", ""
            while True:
                raw, reasoning = act_fn(system_prompt, trimmed)
                parsed = parse_step_action(raw, menu)
                if parsed["status"] == "ok" or retries >= cfg.max_retries_per_step:
                    break
                retries += 1
                correction = (f'That was not one of the legal actions '
                             f'({", ".join(menu)}). ' + obs)
                trimmed = trimmed + [
                    {"role": "assistant", "content": raw},
                    {"role": "user", "content": correction}]
            if parsed["status"] != "ok":
                # retries exhausted: end the episode here rather than
                # substituting a random move the model never chose
                messages.append({"role": "assistant", "content": raw})
                if abort_info is not None:
                    abort_info.update(node=u, retries=retries,
                                      raw_text=raw, reasoning=reasoning)
                raise PolicyAborted
            action_label, status = parsed["action"], "ok"
            v = inv.get((u, action_label))   # translate the chosen label back to a node
            if v is None:
                v = menu_cache.get(u) and inv.get((u, menu_cache[u][0]))

        messages.append({"role": "assistant", "content": raw})   # log the model's reply
        step_meta.append({"action_label": action_label,
                          "parse_status": status, "retries": retries,
                          "raw_text": raw, "reasoning": reasoning})
        prev["label"], prev["target"] = action_label, v   # remember for next call's success check
        return v
    return policy


def make_llm_policy(mdp, labels, cfg, act_fn, system_prompt, messages,
                    step_meta, initial_note=None, abort_info=None) -> Callable:
    """Build a live-LLM policy, already wrapped with logging.

    Public wrapper that always uses the act_fn path of
    _build_recording_policy.

    Args:
        mdp: The RoutingMDP being explored in this phase.
        labels: (u, v) -> 'aK' label mapping for this instance.
        cfg: ExploreConfig with the step/retry/context settings to use.
        act_fn: LLM call function (system, messages) -> (raw_text,
            reasoning) (expected to already include retry/backoff).
        system_prompt: System prompt passed to act_fn on every call.
        messages: Shared, growing user/assistant transcript (mutated).
        step_meta: Shared list to append one metadata dict per step to (mutated).
        initial_note: Optional note shown only on the first step.
        abort_info: Optional dict (mutated in place) filled when the
            policy gives up after exhausting retries -- see
            _build_recording_policy.

    Returns:
        A policy(u, rng) -> node callable, the same contract
        resource_mdp.rollout() expects. It raises resource_mdp.PolicyAborted
        instead of returning once retries are exhausted, ending the
        rollout() episode early.
    """
    return _build_recording_policy(mdp, labels, cfg, messages, step_meta,
                                   act_fn=act_fn, system_prompt=system_prompt,
                                   abort_info=abort_info,
                                   initial_note=initial_note)


# --------------------------------------------------------------------------
# Episode / phase orchestration
# --------------------------------------------------------------------------


def _zip_steps(attempts, step_meta, phase, episode_idx) -> list:
    """Merge rollout()'s Attempt log with our own per-step metadata into
    full LiveStep records.

    rollout() calls the policy exactly once per Attempt it appends, and
    _build_recording_policy's policy() appends exactly one step_meta
    entry per call. Both lists grow in lockstep, and zipping them
    pairs up the entries that belong to the same step.

    Args:
        attempts: List of resource_mdp.Attempt from one rollout() call.
        step_meta: Parallel list of per-step dicts (action_label,
            parse_status, retries, raw_text, reasoning) logged during
            that call.
        phase: "m0" | "m1", stamped onto every resulting LiveStep.
        episode_idx: Episode index, stamped onto every resulting
            LiveStep.

    Returns:
        A list of LiveStep, one per (attempt, step_meta) pair.
    """
    return [LiveStep(t=a.t, node=a.node, chosen=a.chosen, success=a.success,
                     next_node=a.next_node, phase=phase,
                     episode_idx=episode_idx,
                     action_label=m["action_label"],
                     parse_status=m["parse_status"], retries=m["retries"],
                     raw_text=m["raw_text"], reasoning=m["reasoning"])
            for a, m in zip(attempts, step_meta)]


def run_explore_instance(inst, cfg, act_fn=None, node_policy_fn=None) -> dict:
    """Run the two-phase (M0 then M1) live-exploration sequence for one
    instance.

    Runs cfg.max_episodes_m0 episodes on the pre-change world, then
    resets to the start and runs cfg.max_episodes_m1 episodes on the
    post-change world, sharing one continuous transcript across both
    phases (the model's memory persists across the reset).

    Args:
        inst: A resource_mdp.PairedInstance (provides m0, m1, start,
            labels, change).
        cfg: ExploreConfig with the episode/step/retry/context settings
            to use.
        act_fn: LLM call function (system, messages) -> (raw_text,
            reasoning). Give exactly one of act_fn or node_policy_fn.
        node_policy_fn: A FACTORY, `node_policy_fn(mdp) -> policy(u, rng)
            -> node` (e.g. `lambda mdp: dry_run_policy(mdp, inst.labels)`),
            called once per phase against that phase's actual world (m0
            for the M0 phase, m1 for M1) -- a single fixed policy built
            against m0 would stay wrongly anchored to the pre-change
            optimum once M1 starts, since the broken link's true cost
            only exists in m1. Give exactly one of act_fn or
            node_policy_fn.

    Returns:
        {"messages": [...], "m0_episodes": [EpisodeOutcome, ...],
         "m1_episodes": [EpisodeOutcome, ...]}.
    """
    labels = inst.labels
    system_prompt = build_system_prompt(inst.m0.goal)   # built once, reused for the whole run
    messages = []   # one shared, growing transcript across both phases

    def run_phase(mdp, phase, max_episodes, initial_note=None) -> list:
        """Run max_episodes episodes on `mdp`, each a full rollout() call
        with a freshly built, logging policy."""
        episodes = []
        # rebuilt against THIS phase's mdp every time -- see the
        # node_policy_fn docstring note above on why a shared/cached
        # policy across phases would be wrong
        node_policy = node_policy_fn(mdp) if node_policy_fn else None
        for ep_idx in range(max_episodes):
            step_meta = []
            abort_info = {}
            note = initial_note if ep_idx == 0 else None   # shown only on the phase's first step
            policy = _build_recording_policy(
                mdp, labels, cfg, messages, step_meta,
                act_fn=act_fn, system_prompt=system_prompt,
                node_policy=node_policy, initial_note=note,
                abort_info=abort_info)
            rng = random.Random(f"{cfg.seed}|explore|{phase}|{ep_idx}")
            attempts, delivered = rollout(mdp, inst.start, policy, rng,
                                          horizon=cfg.max_steps_per_episode)
            steps = _zip_steps(attempts, step_meta, phase, ep_idx)
            if abort_info:
                # retries exhausted mid-episode: append one diagnostic
                # step (no move actually taken) and end the episode here
                # instead of continuing on a fabricated random action
                steps.append(LiveStep(
                    t=len(steps) + 1, node=abort_info["node"], chosen="",
                    success=False, next_node=abort_info["node"], phase=phase,
                    episode_idx=ep_idx, action_label="",
                    parse_status="retries_exhausted",
                    retries=abort_info["retries"],
                    raw_text=abort_info["raw_text"],
                    reasoning=abort_info["reasoning"]))
                outcome = "retries_exhausted"
            else:
                outcome = "reached_goal" if delivered else "horizon_cutoff"
            episodes.append(EpisodeOutcome(
                episode_idx=ep_idx, phase=phase, steps=steps,
                outcome=outcome))
        return episodes

    m0_episodes = run_phase(inst.m0, "m0", cfg.max_episodes_m0)

    transition_note = ("You are placed back at the start. The network's "
                       "link reliabilities may have changed since your "
                       "last episode." if cfg.announce_change else
                       "You are placed back at the start. Continue.")
    m1_episodes = run_phase(inst.m1, "m1", cfg.max_episodes_m1,
                            initial_note=transition_note)

    return {"messages": messages, "m0_episodes": m0_episodes,
           "m1_episodes": m1_episodes}


# Smoke test: builds the seed-7 silent_break instance,
# runs a small dry-run exploration:
#       dry_run_policy, 3 episodes per phase, 15 steps each
# then prints the episode outcomes and metrics
# So the loop can be sanity-checked without an API key.
if __name__ == "__main__":
    from resource_mdp import make_pair
    from explore_metrics import compute_explore_metrics

    inst = make_pair(seed=7, condition="silent_break", deterministic=True,
                     matched=True)
    cfg = ExploreConfig(max_episodes_m0=3, max_episodes_m1=3,
                        max_steps_per_episode=15, seed=7)
    result = run_explore_instance(
        inst, cfg,
        node_policy_fn=lambda mdp: dry_run_policy(mdp, inst.labels))
    metrics = compute_explore_metrics(inst, result["m0_episodes"],
                                      result["m1_episodes"])
    print(f"start={inst.start} goal={inst.m0.goal} "
         f"broken_edge={inst.change['edge']}")
    print(f"M0 episodes: "
         f"{[e.outcome for e in result['m0_episodes']]}")
    print(f"M1 episodes: "
         f"{[e.outcome for e in result['m1_episodes']]}")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

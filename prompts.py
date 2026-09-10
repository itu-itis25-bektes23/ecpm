#!/usr/bin/env python3
"""
Prompt templates and their formatting helpers for run_pilot.py.
"""

from __future__ import annotations

# --------------------------------------------------------------------
# Passive-pilot prompts: the model is handed a pre-collected evidence
# log (period A / period B), rendered in one of three turn modes
# (single, multi, v2.2 two_turn). Used by run_pilot().
# --------------------------------------------------------------------

INTRO = """You are analysing a courier network. Nodes are locations; at each
node you may attempt the listed actions (aK). An attempt either delivers
you to that action's destination or you stay and retry (each attempt
costs 1). You observed the network in two periods.

Nodes: {nodes}
Start: {start}   Goal: {goal}

Action menu, period A (earlier): {menu_pre}
Action menu, period B (later): {menu_post}

Observations, period A:
{ev_pre}

Observations, period B:
{ev_post}
"""

# v2.2 two-turn protocol. INTRO_A is the turn-1 header (period A only);
# REVEAL_B is prepended to the first turn-2 ask. INTRO_A + REVEAL_B carry
# exactly the same facts as INTRO.
INTRO_A = """You are analysing a courier network. Nodes are locations; at each
node you may attempt the listed actions (aK). An attempt either delivers
you to that action's destination or you stay and retry (each attempt
costs 1). You observed the network in an earlier period (period A). A
later period (period B) will be shown afterwards.

Nodes: {nodes}
Start: {start}   Goal: {goal}

Action menu, period A (earlier): {menu_pre}

Observations, period A:
{ev_pre}
"""

REVEAL_B = """Here is the later period (period B) of the same network.

Action menu, period B (later): {menu_post}

Observations, period B:
{ev_post}
"""

ASKS = {
    "route_pre": (
        'Plan a route for period A from {start} to {goal}. Answer with '
        'exactly one JSON object of the form {{"route": [{{"node": "...", '
        '"action": "..."}}, ...]}}: at most 32 steps, the first step\'s '
        'node must be {start}, each next step\'s node must be where the '
        'previous action leads, and the route must end at {goal}. No other '
        'text.'),
    "belief_pre": (
        'For EACH of the following (node, action) pairs, state what you '
        'believe from the period A observations: the destination node the '
        'action leads to, and its probability of success per attempt '
        '(a number in [0, 1]):\n{queried}\n'
        'Answer with exactly one JSON object of the form '
        '{{"beliefs": [{{"node": "...", "action": "...", "destination": '
        '"...", "p": 0.0}}, ...]}} containing every listed pair exactly '
        'once. No other text.'),
    "belief_post": (
        'Now, for the SAME (node, action) pairs, state your beliefs for '
        'period B: destination node and probability of success per '
        'attempt:\n{queried}\n'
        'Answer with exactly one JSON object of the form '
        '{{"beliefs": [{{"node": "...", "action": "...", "destination": '
        '"...", "p": 0.0}}, ...]}} containing every listed pair exactly '
        'once. No other text.'),
    "detection": (
        'Question: did the network\'s dynamics change between period A and '
        'period B?\nAnswer with exactly one JSON object: '
        '{"changed": true} or {"changed": false}. No other text.'),
    "localization": (
        'The dynamics changed between the periods. Question: which single '
        '(node, action) pair changed?\nAnswer with exactly one JSON '
        'object: {"node": "<node>", "action": "<aK>"}. No other text.'),
    "preservation": (
        'For EACH of the following (node, action) pairs, judge whether its '
        'dynamics changed between period A and period B:\n{queried}\n'
        'Answer with exactly one JSON object of the form '
        '{{"pairs": [{{"node": "...", "action": "...", "changed": '
        'true|false}}, ...]}} containing every listed pair exactly once. '
        'No other text.'),
    "adaptation": (
        'Plan a route for period B (the later network) from {start} to '
        '{goal}. Answer with exactly one JSON object of the form '
        '{{"route": [{{"node": "...", "action": "..."}}, ...]}}: at most '
        '32 steps, the first step\'s node must be {start}, each next '
        'step\'s node must be where the previous action leads, and the '
        'route must end at {goal}. No other text.'),
}

# --------------------------------------------------------------------
# Active-pilot prompts: the model explored the MDP itself, so the probes
# refer to its own exploration episodes instead of a handed-over period
# A/B log. Used by run_pilot_active().
# --------------------------------------------------------------------

ASKS_ACTIVE = {
    "detection": (
        'Question: across your two rounds of exploring this network (the '
        'first set of episodes, then the reset and second set), did the '
        'network\'s dynamics change at any point?\nAnswer with exactly '
        'one JSON object: {"changed": true} or {"changed": false}. No '
        'other text.'),
    "localization": (
        'The dynamics changed at some point during your exploration. '
        'Question: which single (node, action) pair changed?\nAnswer '
        'with exactly one JSON object: {"node": "<node>", "action": '
        '"<aK>"}. No other text.'),
    "preservation": (
        'For EACH of the following (node, action) pairs, judge whether '
        'its dynamics changed at any point during your exploration:\n'
        '{queried}\nAnswer with exactly one JSON object of the form '
        '{{"pairs": [{{"node": "...", "action": "...", "changed": '
        'true|false}}, ...]}} containing every listed pair exactly once. '
        'No other text.'),
    "adaptation": (
        'Plan a route for the current network (as of your most recent '
        'exploration) from {start} to {goal}. Answer with exactly one '
        'JSON object of the form {{"route": [{{"node": "...", "action": '
        '"..."}}, ...]}}: at most 32 steps, the first step\'s node must '
        'be {start}, each next step\'s node must be where the previous '
        'action leads, and the route must end at {goal}. No other '
        'text.'),
}


# --------------------------------------------------------------------
# Passive-pilot formatting helpers (used by run_pilot()).
# --------------------------------------------------------------------

def _menus(view):
    return {p: "; ".join(f"{node}: {', '.join(m)}" for node, m in
                         sorted(view[f"legal_actions_{p}"].items()))
            for p in ("pre", "post")}


def context_block(view):
    """The shared evidence header (both periods): sent once in the legacy
    multi mode, prepended to every ask in single-turn mode. Frozen text."""
    menus = _menus(view)
    return INTRO.format(nodes=", ".join(view["nodes"]),
                        start=view["start"], goal=view["goal"],
                        menu_pre=menus["pre"], menu_post=menus["post"],
                        ev_pre=view["evidence"]["pre"],
                        ev_post=view["evidence"]["post"])


def context_block_a(view):
    """v2.2 turn-1 header: period A only."""
    menus = _menus(view)
    return INTRO_A.format(nodes=", ".join(view["nodes"]),
                          start=view["start"], goal=view["goal"],
                          menu_pre=menus["pre"],
                          ev_pre=view["evidence"]["pre"])


def reveal_block_b(view):
    """v2.2 turn-2 reveal: period B only (turn 1 stays in context)."""
    menus = _menus(view)
    return REVEAL_B.format(menu_post=menus["post"],
                           ev_post=view["evidence"]["post"])


def ask_block(view, probe, queried):
    """The probe question alone (no evidence)."""
    ask = ASKS[probe]
    if probe in ("preservation", "belief_pre", "belief_post"):
        listed = "\n".join(f'- node {q["node"]}, action {q["action"]}'
                           for q in queried)
        ask = ask.format(queried=listed)
    elif probe in ("adaptation", "route_pre"):
        ask = ask.format(start=view["start"], goal=view["goal"])
    return ask + "\n"


# --------------------------------------------------------------------
# Active-pilot formatting helper (used by run_pilot_active()).
# --------------------------------------------------------------------


def ask_block_active(record, probe, queried):
    """The active-pilot probe question alone (no evidence transcript)."""
    ask = ASKS_ACTIVE[probe]
    if probe == "preservation":
        listed = "\n".join(f'- node {q["node"]}, action {q["action"]}'
                           for q in queried)
        ask = ask.format(queried=listed)
    elif probe == "adaptation":
        ask = ask.format(start=record["start"], goal=record["goal"])
    return ask

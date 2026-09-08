#!/usr/bin/env python3
"""Checks for the controlled harder-ICL prompt variant."""

from run_pilot import (SCENARIO_DEFAULTS, SCENARIOS, build_record,
                       context_block, context_block_a, reveal_block_b)
from resource_mdp import prompt_view


def test_prompt_styles():
    sc = dict(SCENARIO_DEFAULTS)
    sc.update(SCENARIOS["seed7_silent_break_minimal"])
    record = build_record(sc, deterministic=True)
    view = prompt_view(record, rendering=sc["rendering"],
                       periods=("pre", "post"),
                       budget_per_pair=sc["budget"])

    described = context_block(view, "explicit")
    minimal = context_block(view, "minimal")
    assert "courier network" in described
    for word in ("courier", "network", "location", "delivers", "fails"):
        assert word not in minimal.lower(), word

    # Prompt framing changes; evidence and task inputs do not.
    for period in ("pre", "post"):
        assert view["evidence"][period] in described
        assert view["evidence"][period] in minimal
    for value in (view["start"], view["goal"], *view["nodes"]):
        assert value in minimal

    first = context_block_a(view, "minimal")
    later = reveal_block_b(view, "minimal")
    assert view["evidence"]["pre"] in first
    assert view["evidence"]["post"] not in first
    assert view["evidence"]["post"] in later
    assert view["evidence"]["pre"] not in later

    print("PASS prompt styles: same evidence, less framing, periods separate")


if __name__ == "__main__":
    test_prompt_styles()
    print("\nALL RUNNER TESTS PASSED")

"""Regression guard for the route-prompt wording.

Why this file exists
--------------------
The route asks once said "the route must end at {goal}". Three models read
that as an instruction to append a step at the goal node; the grader rejects
that step, and Sonnet 4.6 and GPT-4o lost all four route answers in the
23 Aug pilot to format errors rather than to wrong reasoning.

The fix is three edited strings. That makes it exactly the kind of change a
merge can lose without anything noticing: PR #5 moves ASKS out of
run_pilot.py into prompts.py, so resolving that conflict by taking the
incoming side drops the fix silently, and the result compiles, runs, and
passes every other test.

This test asserts the property rather than the location (handbook 28.1), so
it keeps working after the move. It is the check that turns a silent
regression into a loud one.

Run: python3 test_prompt_contract.py
"""

import sys

# The asks live in run_pilot.py today and in prompts.py after the extraction
# in PR #5. Accept either, and fail only if neither can be found.
ASKS = ASKS_ACTIVE = None
_source = None
try:
    import prompts as _p
    ASKS, ASKS_ACTIVE, _source = _p.ASKS, _p.ASKS_ACTIVE, "prompts.py"
except (ImportError, AttributeError):
    try:
        import run_pilot as _r
        ASKS, ASKS_ACTIVE, _source = _r.ASKS, _r.ASKS_ACTIVE, "run_pilot.py"
    except (ImportError, AttributeError):
        pass

BANNED = "route must end at"
REQUIRED = "destination of the last action must be"
NO_GOAL_STEP = "Do NOT include a step at"

ROUTE_ASKS = ("route_pre", "adaptation")


def test_asks_are_reachable():
    assert ASKS is not None, (
        "neither prompts.ASKS nor run_pilot.ASKS could be imported; if the "
        "asks moved again, extend the import block above rather than "
        "deleting this test")
    print(f"PASS asks located in {_source}")


def test_no_ask_asks_for_a_step_at_the_goal():
    """The banned phrasing, in any ask, in either dictionary."""
    offenders = []
    for name, table in (("ASKS", ASKS), ("ASKS_ACTIVE", ASKS_ACTIVE)):
        for probe, text in (table or {}).items():
            if BANNED in text:
                offenders.append(f"{name}[{probe!r}]")
    assert not offenders, (
        "the pre-fix route wording is back in: " + ", ".join(offenders)
        + ". This cost two models all four route answers in the 23 Aug "
          "pilot. See the Gist for the corrected text.")
    print("PASS no ask contains the pre-fix wording")


def test_route_asks_carry_the_corrected_contract():
    """Absence of the bad string is not presence of the good one."""
    missing = []
    for probe in ROUTE_ASKS:
        text = (ASKS or {}).get(probe)
        if text is None:
            continue
        if REQUIRED not in text or NO_GOAL_STEP not in text:
            missing.append(f"ASKS[{probe!r}]")
    adaptation = (ASKS_ACTIVE or {}).get("adaptation")
    if adaptation is not None and (REQUIRED not in adaptation
                                   or NO_GOAL_STEP not in adaptation):
        missing.append("ASKS_ACTIVE['adaptation']")
    assert not missing, (
        "route asks missing the corrected contract: " + ", ".join(missing))
    print("PASS every route ask states the destination rule and forbids a "
          "goal step")


if __name__ == "__main__":
    test_asks_are_reachable()
    test_no_ask_asks_for_a_step_at_the_goal()
    test_route_asks_carry_the_corrected_contract()
    print("\nALL PROMPT CONTRACT TESTS PASSED")

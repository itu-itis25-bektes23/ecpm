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

# The legacy asks live in run_pilot.py today and in prompts.py after the
# extraction in PR #5. Accept either, and fail only if neither can be found.
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

# Both phrasings were read by models as an instruction to append a step at
# the goal node. The first is the original legacy wording; the second is the
# equivalent in the ICL prompt layer, which hit the same failure
# independently and was corrected in PR #8.
BANNED = "route must end at"
BANNED_ICL = ("finish at Goal", "route must end at Goal")

# The ICL two-response protocol builds its own route instruction rather than
# reusing ASKS, so it needs its own guard. Absent on branches that predate
# PR #4, in which case the ICL checks skip rather than fail.
try:
    from run_pilot import (ICL_ROUTE_INSTRUCTION, ICL_TURN_A_SCHEMA,
                           ICL_TURN_B_SCHEMA)
except ImportError:
    ICL_ROUTE_INSTRUCTION = ICL_TURN_A_SCHEMA = ICL_TURN_B_SCHEMA = None
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




def test_icl_route_instruction_forbids_a_goal_step():
    """PR #8 fixed the same failure in the ICL prompt layer that the legacy
    asks hit in August: a route instruction phrased as "finish at Goal" is
    read as an instruction to append a step at the goal node, and the
    grader rejects it.

    The legacy fix and the ICL fix were made separately, weeks apart, in
    different files. This guard covers both so neither can regress alone.
    """
    if ICL_ROUTE_INSTRUCTION is None:
        print("SKIP ICL route instruction: not present on this branch")
        return
    for bad in BANNED_ICL:
        assert bad not in ICL_ROUTE_INSTRUCTION, (
            f"the pre-fix ICL wording {bad!r} is back in "
            "ICL_ROUTE_INSTRUCTION")
    assert "must be Goal" in ICL_ROUTE_INSTRUCTION, (
        "ICL_ROUTE_INSTRUCTION no longer states where the last action must "
        "land")
    assert "not add a route item for Goal" in ICL_ROUTE_INSTRUCTION, (
        "ICL_ROUTE_INSTRUCTION no longer forbids a step at the goal")
    print("PASS ICL route instruction: states the destination rule and "
          "forbids a goal step")


def test_icl_schemas_carry_the_route_instruction():
    """The instruction only protects the prompts that embed it."""
    if ICL_TURN_A_SCHEMA is None:
        print("SKIP ICL schemas: not present on this branch")
        return
    missing = [name for name, text in (("ICL_TURN_A_SCHEMA", ICL_TURN_A_SCHEMA),
                                       ("ICL_TURN_B_SCHEMA", ICL_TURN_B_SCHEMA))
               if ICL_ROUTE_INSTRUCTION not in text]
    assert not missing, (
        "route-requesting schemas without the shared instruction: "
        + ", ".join(missing))
    for name, text in (("ICL_TURN_A_SCHEMA", ICL_TURN_A_SCHEMA),
                       ("ICL_TURN_B_SCHEMA", ICL_TURN_B_SCHEMA)):
        for bad in BANNED_ICL:
            assert bad not in text, f"pre-fix wording {bad!r} back in {name}"
    print("PASS ICL schemas: both embed the shared route instruction")

if __name__ == "__main__":
    test_asks_are_reachable()
    test_no_ask_asks_for_a_step_at_the_goal()
    test_route_asks_carry_the_corrected_contract()
    test_icl_route_instruction_forbids_a_goal_step()
    test_icl_schemas_carry_the_route_instruction()
    print("\nALL PROMPT CONTRACT TESTS PASSED")

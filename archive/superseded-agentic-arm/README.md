# Superseded agentic arm

A second agentic implementation, built independently in August 2026 before
`explore_agent.py` was available. Dropped by its author once the two were
compared, on the grounds that it was duplicated work.

Kept because the data it produced is still data, and because the metrics
module was written to read step records from any harness.

- `agent_loop.py`, `langgraph_loop.py` the loop and a LangGraph adapter
- `break_metrics.py` does the model stop using the dead link
- `analyze_runs.py` aggregates run files into the knowing-versus-doing box
- `frozen.py` a connector to a separate ecpm checkout, obsolete here since
  the frozen modules are now in the same tree
- `main.py`, `seed7_world.py`, `smoke_test.py`, `verify_against_frozen.py`

Its runs live under `runs/2026-08-27_gemma3-4b_agentic/`. Nothing here is
maintained or covered by CI.

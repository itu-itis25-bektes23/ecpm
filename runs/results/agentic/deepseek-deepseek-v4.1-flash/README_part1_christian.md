# Agentic arm, DeepSeek V4.1 Flash (partial: 255 of 330 runs)

`deepseek/deepseek-v4.1-flash` via OpenRouter, launched with `run_agentic_cost_check.py`
from the `results-freeze` tag (10c93b5). Seeds 8, 13, 25, 0, 1; three arms (task_only,
model_first, graph_given); history none; one run per cell; output cap 65,536 for both
reasoning modes.

Files:

- `agentic_runs.csv`: one row per run (seed, mode, scenario, arm, reasoning, every metric,
  billed cost, token counts, `cut_off_calls`, `retried_attempts`).
- `agentic_summary.md`: mean and standard deviation per arm for every mode, scenario and
  reasoning combination, from `summarize_agentic_runs.py`.

## Status

- Reasoning off: complete (11 invocations, 165 runs).
- Reasoning on: 6 of 11 invocations (all five deterministic scenarios and stochastic
  `no_change`, 90 runs). The stochastic `irrelevant`, `silent_break`, `hard_removal`,
  `redirect` and `degradation` invocations (75 runs) are still to run. This folder is
  updated when they are in.

## Cost and run quality

| | Reasoning off | Reasoning on |
|---|---|---|
| Runs | 165 | 90 |
| Billed cost | $1.28 | $2.70 |
| Cost per run | about $0.008 (max $0.07) | about $0.030 (max $0.26) |
| Duration per run | about 1 min | about 3 min |
| Input / output tokens | 26.1M / 0.39M | 8.9M / 3.03M (2.93M reasoning) |
| Empty replies (retried) | 0 | 47 in 15 runs |
| of which cut off at the cap (`finish_reason=length`) | 0 | 32 |

An empty reply is billed and requested again, so no truncated answer enters a run. Two runs
(`task_only` seeds 13 and 25, deterministic) had six empty replies in a row, were put back
at the end of the queue and finished on the second attempt. Costs are summed from the
artifacts; the OpenRouter dashboard is the reference for the exact bill.

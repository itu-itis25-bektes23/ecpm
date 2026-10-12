# H4 trimming check

Failure streaks carry across M0 and M1 and reset on target-link success. The threshold must be reached in M1, as in the saved scorer. The check rebuilds the first subsequent non-aborted decision at the changed source with the saved trimming settings. It checks the six qualifying failure reports, not every earlier target observation or every later decision. Original scores are not rewritten.

The k/n entries below are repeat-choice fractions: runs that chose the changed link again / qualifying runs in the indicated subset, not counts of retained reports. 0/0 means that subset contains no runs. Coverage counts are listed separately.

| Grid | Model | Chose again / all qualifying runs | Chose again / runs retaining all six reports | Chose again / runs missing at least one report | Wilson lower bound on repeat-choice rate, all six retained |
|---|---|---|---|---|---|
| GRID_anthropic-claude-haiku-5.5_2026-10-11_130215 | anthropic/claude-haiku-5.5 | 19/21 | 19/21 | 0/0 | 0.69 |
| GRID_anthropic-claude-haiku-5.5_2026-10-11_133243 | anthropic/claude-haiku-5.5 | 15/20 | 15/20 | 0/0 | 0.51 |
| GRID_deepseek-deepseek-v4.1-flash_2026-10-11_130148 | deepseek/deepseek-v4.1-flash | 17/21 | 17/21 | 0/0 | 0.58 |
| GRID_deepseek-deepseek-v4.1-flash_2026-10-11_133021 | deepseek/deepseek-v4.1-flash | 27/31 | 27/31 | 0/0 | 0.69 |
| GRID_openai-gpt-5.6-sol_2026-10-11_130438 | openai/gpt-5.6-sol | 14/17 | 14/17 | 0/0 | 0.57 |
| GRID_openai-gpt-5.6-sol_2026-10-11_134333 | openai/gpt-5.6-sol | 8/14 | 8/14 | 0/0 | 0.31 |

## Coverage

| Grid | Inputs | Out of scope | Not qualifying | Checked | No later source decision | Errors | Status |
|---|---|---|---|---|---|---|---|
| GRID_anthropic-claude-haiku-5.5_2026-10-11_130215 | 306 | 204 | 81 | 21 | 0 | 0 | checked |
| GRID_anthropic-claude-haiku-5.5_2026-10-11_133243 | 306 | 204 | 82 | 20 | 0 | 0 | checked |
| GRID_deepseek-deepseek-v4.1-flash_2026-10-11_130148 | 306 | 204 | 81 | 21 | 0 | 0 | checked |
| GRID_deepseek-deepseek-v4.1-flash_2026-10-11_133021 | 306 | 204 | 71 | 31 | 0 | 0 | checked |
| GRID_openai-gpt-5.6-sol_2026-10-11_130438 | 306 | 204 | 85 | 17 | 0 | 0 | checked |
| GRID_openai-gpt-5.6-sol_2026-10-11_134333 | 306 | 204 | 88 | 14 | 0 | 0 | checked |

## Cross-phase qualifiers

The previous M1-only checker could miss an M0-carried streak or locate its threshold too late. These records carry failures from M0; negative failure indices in the coverage file refer to M0.

- GRID_deepseek-deepseek-v4.1-flash_2026-10-11_130148, seed 48, silent_break, repeat 0: 1 M0 failure(s); visible; chose again: False; first subsequent source decision: M1 step 22 (zero-based).
- GRID_deepseek-deepseek-v4.1-flash_2026-10-11_133021, seed 48, silent_break, repeat 0: 1 M0 failure(s); visible; chose again: True; first subsequent source decision: M1 step 24 (zero-based).

Visibility is an observed result of reconstructing these histories, not a guarantee from FIFO trimming. The six failures need not be adjacent in the transcript. A qualifier with no later source decision remains in the H4 denominator but has no visibility check. The existing Wilson calculation (z=2.128) is retained, not a new dependence-adjusted analysis.

Reproduce with `python3 -B experiments/h4_trimming_check.py --grid GRID_DIRECTORY` (repeat `--grid` for each of the six named archives), `--out REPORT.md --coverage COVERAGE.csv`. The input archives remain outside Git.

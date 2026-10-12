# H4 trimming check

**Question.** The agent's history is trimmed when the transcript exceeds an estimated 12,000 tokens. Could the six consecutive failures that qualify a run for H4 have been trimmed away before the agent chose the link again?

**Method.** `experiments/h4_trimming_check.py` is applied to every task-only run of both confirmatory grids, in stochastic silent break and degradation, that reached six consecutive failures of the changed link in M1. At the first decision at the changed node after the sixth failure, it rebuilds the history the agent was sent, using `explore_agent.trim_history` with the run's own settings. It then checks whether the reports of all six failures were in it. The inputs are the confirmatory GRID zips of 11 October 2026, kept outside the repository in the team Drive.

**Result.** In every qualifying run, all six failures were in the agent's context at that decision. No run is affected, so H4 is unchanged.

| Grid | Model | Chose again / qualifying | All six failures in context | Some trimmed away | Wilson lower bound, visible only |
|---|---|---|---|---|---|
| GRID_anthropic-claude-haiku-5_5 (no preparation) | anthropic/claude-haiku-5.5 | 19/21 | 19/21 | 0/0 | 0.69 |
| GRID_deepseek-deepseek-v4_1-flash (no preparation) | deepseek/deepseek-v4.1-flash | 17/20 | 17/20 | 0/0 | 0.62 |
| GRID_openai-gpt-5_6-sol (no preparation) | openai/gpt-5.6-sol | 14/17 | 14/17 | 0/0 | 0.57 |
| GRID_anthropic-claude-haiku-5_5 (matched preparation) | anthropic/claude-haiku-5.5 | 15/20 | 15/20 | 0/0 | 0.51 |
| GRID_deepseek-deepseek-v4_1-flash (matched preparation) | deepseek/deepseek-v4.1-flash | 27/31 | 27/31 | 0/0 | 0.69 |
| GRID_openai-gpt-5_6-sol (matched preparation) | openai/gpt-5.6-sol | 8/14 | 8/14 | 0/0 | 0.31 |

**Why no run is affected.** Trimming drops the oldest turns first and always keeps the most recent turns. The six failures come immediately before the decision, so they are always among the turns kept.

**The DeepSeek count.** The no-preparation DeepSeek run reads 17/20 here against 17/21 in the H4 table. The one extra qualifying run ends before the agent returns to the changed node, so there is no decision to check. It did not choose the link again, so H4 is the same either way.

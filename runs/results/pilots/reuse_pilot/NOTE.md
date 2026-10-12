# Reuse pilot: why do agents retry a link that failed six times in a row?

**Status: exploratory pilot.** It runs on decisions from runs already analyzed, with one sample per decision. It motivates the confirmatory design and tests no hypothesis.

## Method

The pilot needs no new agent runs. It takes every agent run of the confirmatory H4/H6 grids (stochastic silent break, task-only and model-first, both grids, reasoning off) and finds the first decision, in an M1 episode, at the changed node after the changed link failed six times in a row. It then resumes the agent at that exact decision. The system prompt, history (trimmed with `explore_agent.trim_history` and the run's own settings), model, temperature (0) and reasoning control are all taken from the run artifact. Exactly one thing changes per condition. The worlds and complete logs are rebuilt with `run_pilot.make_pair` and `run_pilot.build_record`.

| Condition | What changes |
|---|---|
| resume | nothing, the decision replayed |
| hint | the last observation names one route to the goal that avoids the failing link |
| hint_first_step | the last observation names only the first step of that route |
| nudge | the last observation adds "when an action keeps failing, consider trying actions or routes you have not tried yet" |
| budget | the last observation says 20 more steps remain |
| reader | a fresh model reads the agent's own observations as a log and advises the next action |
| reader_full | a fresh model reads a log covering every link before and after the change, built as in the ICL arm |
| reader_hint | the agent's own log plus the route |

Script: `experiments/reuse_pilot.py`. Version 1 (Haiku, 5 conditions) is in `v1/`. Version 2 (all three models, 8 conditions) is in `v2/`. Each folder has `summary.md`. `v2/` also has `calls.jsonl`, with every answer, and `decisions.json`, with every decision point and its run id. Inputs are the run folders inside the confirmatory GRID zips. Those zips are kept outside the repository, under `ecpm-conf-<model>/runs/` and in the team Drive.

## Results (version 2), share of decisions that retry the failing link

| Condition | Claude Haiku 5.5 (41) | DeepSeek V4.1 Flash (50) | GPT-5.6 Sol (46) |
|---|---|---|---|
| resume | 80% | 52% | 63% |
| original runs | 80% | 54% | 59% |
| nudge | 29% | 6% | 9% |
| hint | 27% | 8% | 15% |
| reader_full | 46% | 36% (39 valid) | 39% |
| reader | 73% | 58% (48 valid) | 70% |
| hint_first_step | 78% | 32% | 80% |
| budget | 71% | 84% | 39% |

Paired against resume, the nudge moved 22, 23 and 25 decisions from retrying to switching, and 1, 0 and 0 the other way. The hint moved 22, 24 and 23 the first way and 0, 2 and 1 the other. Version 1 (Haiku) agrees: resume 73%, hint 29%, budget 61%, reader 73%, reader_hint 29%.

## Reading

- **Resume reproduces the original choices** within a few points for every model, so the resumed state matches what the agents saw.
- **One instruction removes most of the failure.** The nudge cuts it to 6 to 29%, about as much as naming a complete route. The models can explore. By default, when the only known route fails, they retry it.
- **Being in the loop is not the cause.** A fresh model reading the agent's own log chooses the same way.
- **Complete evidence about halves the failure,** which partly explains the better results of the log-reading arm, but 36 to 46% still retry.
- **Naming only the first step does not help,** and that step was often already known. A larger step budget has no consistent effect: it helps Sol, barely changes Haiku, and makes DeepSeek retry more.

## Limits

- **Single decisions, not whole episodes.** The nudge was added at the critical moment. In a full agent it would sit in the system prompt, where it may cause over-exploration when nothing changed. That trade-off needs full-episode runs.
- **Small sample.** One sample per decision at temperature 0, on 137 decisions drawn from runs already analyzed.
- **Format failures.** reader_full for DeepSeek had 11 answers with no valid action.

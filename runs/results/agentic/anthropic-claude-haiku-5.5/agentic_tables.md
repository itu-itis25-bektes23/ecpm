## anthropic/claude-haiku-5.5: 330 runs

**Table 1. Behaviour and probes by arm (scenarios with a change)**

| Reasoning | Arm | Runs | Exposed | Detection | Localization | Goal success M1 | Route regret M0 |
|---|---|---|---|---|---|---|---|
| off | task_only | 45 | 62% | 62% | 67% | 0.97 | 1.50 |
| off | model_first | 45 | 53% | 60% | 64% | 0.98 | 1.33 |
| off | graph_given | 45 | 62% | 100% | 100% | 1.00 | 0.11 |
| on | task_only | 45 | 40% | 64% | 53% | 1.00 | 2.16 |
| on | model_first | 45 | 58% | 69% | 62% | 0.98 | 2.00 |
| on | graph_given | 45 | 76% | 100% | 100% | 1.00 | 0.01 |

**Table 2. Exposure decides what the probes can show (all arms and reasoning settings)**

| Runs | n | Detection | Localization |
|---|---|---|---|
| Exposed | 158 | 96% (152/158) | 100% (158/158) |
| Not exposed | 112 | 47% (53/112) | 38% (43/112) |

**Table 3. Exposure / detection by scenario (reasoning settings pooled)**

| Scenario | Runs per arm | task_only exposed / detection | model_first exposed / detection | graph_given exposed / detection |
|---|---|---|---|---|
| silent_break | 20 | 60% / 65% | 80% / 80% | 80% / 100% |
| hard_removal | 20 | 65% / 85% | 65% / 85% | 90% / 100% |
| redirect | 20 | 75% / 80% | 65% / 75% | 90% / 100% |
| degradation | 10 | 50% / 70% | 70% / 50% | 100% / 100% |
| irrelevant | 20 | 5% / 20% | 5% / 25% | 0% / 100% |

**Table 4. No-change control: correctly reports no change**

| Reasoning | Runs per arm | task_only | model_first | graph_given |
|---|---|---|---|---|
| off | 10 | 90% | 90% | 90% |
| on | 10 | 80% | 100% | 90% |

**Cost and run quality.** Billed $6.97 in total, about $0.021 per run (off $3.41, on $3.57). Per run: task_only $0.019, model_first $0.033, graph_given $0.011. Reasoning tokens with reasoning on: mean 2,344, max 9,633 per run. Reasoning violations 0, cut-off calls 0, retried replies 0.

**H4 (six consecutive failures of the broken link).** Reached in 15 of 270 runs with a change; the agent chose the broken link again in 13 of those.


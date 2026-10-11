## openai/gpt-5.6-sol: 306 runs

**Table 1. Behaviour and probes by arm (scenarios with a change)**

| Reasoning | Arm | Runs | Exposed | Detection | Localization | Goal success M1 | Route regret M0 |
|---|---|---|---|---|---|---|---|
| off | task_only | 102 | 56% | 63% | 44% | 0.96 | 2.17 |
| off | model_first | 102 | 58% | 54% | 50% | 0.99 | 2.14 |
| off | graph_given | 102 | 83% | 100% | 99% | 1.00 | 0.22 |

**Table 2. Exposure decides what the probes can show (all arms and reasoning settings)**

| Runs | n | Detection | Localization |
|---|---|---|---|
| Exposed | 201 | 88% (177/201) | 89% (179/201) |
| Not exposed | 105 | 42% (44/105) | 17% (18/105) |

**Table 3. Exposure / detection by scenario (reasoning settings pooled)**

| Scenario | Runs per arm | task_only exposed / detection | model_first exposed / detection | graph_given exposed / detection |
|---|---|---|---|---|
| silent_break | 51 | 53% / 71% | 57% / 63% | 80% / 100% |
| degradation | 51 | 59% / 55% | 59% / 45% | 86% / 100% |

**Cost and run quality.** Billed $20.96 in total, about $0.069 per run (off $20.96). Per run: task_only $0.065, model_first $0.098, graph_given $0.043. Reasoning violations 0, cut-off calls 1, retried replies 0.

**H4 (six consecutive failures of the broken link).** Reached in 33 of 306 runs with a change; the agent chose the broken link again in 24 of those.


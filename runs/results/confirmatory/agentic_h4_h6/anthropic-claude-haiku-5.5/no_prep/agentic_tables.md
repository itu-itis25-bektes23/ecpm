## anthropic/claude-haiku-5.5: 306 runs

**Table 1. Behaviour and probes by arm (scenarios with a change)**

| Reasoning | Arm | Runs | Exposed | Detection | Localization | Goal success M1 | Route regret M0 |
|---|---|---|---|---|---|---|---|
| off | task_only | 102 | 55% | 65% | 43% | 0.93 | 2.03 |
| off | model_first | 102 | 48% | 45% | 38% | 0.96 | 1.97 |
| off | graph_given | 102 | 94% | 100% | 100% | 1.00 | 0.05 |

**Table 2. Exposure decides what the probes can show (all arms and reasoning settings)**

| Runs | n | Detection | Localization |
|---|---|---|---|
| Exposed | 201 | 88% (176/201) | 89% (178/201) |
| Not exposed | 105 | 36% (38/105) | 7% (7/105) |

**Table 3. Exposure / detection by scenario (reasoning settings pooled)**

| Scenario | Runs per arm | task_only exposed / detection | model_first exposed / detection | graph_given exposed / detection |
|---|---|---|---|---|
| silent_break | 51 | 55% / 82% | 51% / 57% | 92% / 100% |
| degradation | 51 | 55% / 47% | 45% / 33% | 96% / 100% |

**Cost and run quality.** Billed $9.32 in total, about $0.030 per run (off $9.32). Per run: task_only $0.030, model_first $0.046, graph_given $0.016. Reasoning violations 0, cut-off calls 0, retried replies 0.

**H4 (six consecutive failures of the broken link).** Reached in 36 of 306 runs with a change; the agent chose the broken link again in 29 of those.


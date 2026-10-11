## anthropic/claude-haiku-5.5: 306 runs

**Table 1. Behaviour and probes by arm (scenarios with a change)**

| Reasoning | Arm | Runs | Exposed | Detection | Localization | Goal success M1 | Route regret M0 |
|---|---|---|---|---|---|---|---|
| off | task_only | 102 | 63% | 57% | 45% | 0.94 | 1.82 |
| off | model_first | 102 | 50% | 46% | 37% | 0.96 | 2.16 |
| off | graph_given | 102 | 82% | 100% | 100% | 1.00 | 0.15 |

**Table 2. Exposure decides what the probes can show (all arms and reasoning settings)**

| Runs | n | Detection | Localization |
|---|---|---|---|
| Exposed | 199 | 84% (167/199) | 84% (167/199) |
| Not exposed | 107 | 37% (40/107) | 18% (19/107) |

**Table 3. Exposure / detection by scenario (reasoning settings pooled)**

| Scenario | Runs per arm | task_only exposed / detection | model_first exposed / detection | graph_given exposed / detection |
|---|---|---|---|---|
| silent_break | 51 | 65% / 67% | 49% / 57% | 78% / 100% |
| degradation | 51 | 61% / 47% | 51% / 35% | 86% / 100% |

**Cost and run quality.** Billed $12.44 in total, about $0.041 per run (off $12.44). Per run: task_only $0.045, model_first $0.046, graph_given $0.030. Reasoning violations 0, cut-off calls 0, retried replies 0.

**H4 (six consecutive failures of the broken link).** Reached in 32 of 306 runs with a change; the agent chose the broken link again in 25 of those.


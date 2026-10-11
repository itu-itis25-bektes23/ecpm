## deepseek/deepseek-v4.1-flash: 306 runs

**Table 1. Behaviour and probes by arm (scenarios with a change)**

| Reasoning | Arm | Runs | Exposed | Detection | Localization | Goal success M1 | Route regret M0 |
|---|---|---|---|---|---|---|---|
| off | task_only | 102 | 46% | 4% | 33% | 0.87 | 2.83 |
| off | model_first | 102 | 60% | 25% | 50% | 0.90 | 2.35 |
| off | graph_given | 102 | 82% | 99% | 100% | 0.99 | 0.21 |

**Table 2. Exposure decides what the probes can show (all arms and reasoning settings)**

| Runs | n | Detection | Localization |
|---|---|---|---|
| Exposed | 192 | 57% (109/192) | 88% (168/192) |
| Not exposed | 114 | 18% (21/114) | 17% (19/114) |

**Table 3. Exposure / detection by scenario (reasoning settings pooled)**

| Scenario | Runs per arm | task_only exposed / detection | model_first exposed / detection | graph_given exposed / detection |
|---|---|---|---|---|
| silent_break | 51 | 47% / 4% | 61% / 35% | 80% / 100% |
| degradation | 51 | 45% / 4% | 59% / 14% | 84% / 98% |

**Cost and run quality.** Billed $3.80 in total, about $0.012 per run (off $3.80). Per run: task_only $0.012, model_first $0.019, graph_given $0.007. Reasoning violations 0, cut-off calls 0, retried replies 0.

**H4 (six consecutive failures of the broken link).** Reached in 51 of 306 runs with a change; the agent chose the broken link again in 45 of those.


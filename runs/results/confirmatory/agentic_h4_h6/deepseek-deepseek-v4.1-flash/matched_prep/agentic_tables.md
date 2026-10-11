## deepseek/deepseek-v4.1-flash: 306 runs

**Table 1. Behaviour and probes by arm (scenarios with a change)**

| Reasoning | Arm | Runs | Exposed | Detection | Localization | Goal success M1 | Route regret M0 |
|---|---|---|---|---|---|---|---|
| off | task_only | 102 | 66% | 24% | 51% | 0.90 | 2.37 |
| off | model_first | 102 | 61% | 23% | 48% | 0.91 | 2.15 |
| off | graph_given | 102 | 85% | 100% | 99% | 1.00 | 0.22 |

**Table 2. Exposure decides what the probes can show (all arms and reasoning settings)**

| Runs | n | Detection | Localization |
|---|---|---|---|
| Exposed | 216 | 61% (131/216) | 85% (184/216) |
| Not exposed | 90 | 20% (18/90) | 20% (18/90) |

**Table 3. Exposure / detection by scenario (reasoning settings pooled)**

| Scenario | Runs per arm | task_only exposed / detection | model_first exposed / detection | graph_given exposed / detection |
|---|---|---|---|---|
| silent_break | 51 | 73% / 33% | 65% / 35% | 84% / 100% |
| degradation | 51 | 59% / 14% | 57% / 10% | 86% / 100% |

**Cost and run quality.** Billed $4.59 in total, about $0.015 per run (off $4.59). Per run: task_only $0.015, model_first $0.020, graph_given $0.011. Reasoning violations 0, cut-off calls 0, retried replies 0.

**H4 (six consecutive failures of the broken link).** Reached in 57 of 306 runs with a change; the agent chose the broken link again in 48 of those.


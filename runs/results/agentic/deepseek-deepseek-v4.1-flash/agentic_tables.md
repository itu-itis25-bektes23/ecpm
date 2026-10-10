## deepseek/deepseek-v4.1-flash: 330 runs

**Table 1. Behaviour and probes by arm (scenarios with a change)**

| Reasoning | Arm | Runs | Exposed | Detection | Localization | Goal success M1 | Route regret M0 |
|---|---|---|---|---|---|---|---|
| off | task_only | 45 | 62% | 27% | 60% | 0.95 | 2.83 |
| off | model_first | 45 | 44% | 38% | 53% | 0.96 | 2.57 |
| off | graph_given | 45 | 67% | 93% | 100% | 1.00 | 0.22 |
| on | task_only | 45 | 47% | 47% | 53% | 0.96 | 3.29 |
| on | model_first | 45 | 42% | 58% | 51% | 0.97 | 2.37 |
| on | graph_given | 45 | 71% | 98% | 100% | 1.00 | 0.02 |

**Table 2. Exposure decides what the probes can show (all arms and reasoning settings)**

| Runs | n | Detection | Localization |
|---|---|---|---|
| Exposed | 150 | 80% (120/150) | 92% (138/150) |
| Not exposed | 120 | 35% (42/120) | 42% (50/120) |

**Table 3. Exposure / detection by scenario (reasoning settings pooled)**

| Scenario | Runs per arm | task_only exposed / detection | model_first exposed / detection | graph_given exposed / detection |
|---|---|---|---|---|
| silent_break | 20 | 55% / 35% | 55% / 45% | 90% / 100% |
| hard_removal | 20 | 65% / 70% | 50% / 60% | 85% / 95% |
| redirect | 20 | 70% / 50% | 55% / 60% | 85% / 95% |
| degradation | 10 | 80% / 0% | 40% / 50% | 90% / 100% |
| irrelevant | 20 | 15% / 10% | 15% / 25% | 5% / 90% |

**Table 4. No-change control: correctly reports no change**

| Reasoning | Runs per arm | task_only | model_first | graph_given |
|---|---|---|---|---|
| off | 10 | 90% | 100% | 100% |
| on | 10 | 100% | 70% | 100% |

**Cost and run quality.** Billed $6.86 in total, about $0.021 per run (off $1.28, on $5.59). Per run: task_only $0.036, model_first $0.021, graph_given $0.005. Reasoning tokens with reasoning on: mean 37,918, max 378,563 per run. Reasoning violations 0, cut-off calls 62, retried replies 93.

**H4 (six consecutive failures of the broken link).** Reached in 5 of 75 runs with a change; the agent chose the broken link again in 5 of those. H4 is recorded for 75 of 270 runs with a change; regenerate the CSV from the run folders to include the rest.


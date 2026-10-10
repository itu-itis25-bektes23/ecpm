## openai/gpt-5.6-sol: 330 runs

**Table 1. Behaviour and probes by arm (scenarios with a change)**

| Reasoning | Arm | Runs | Exposed | Detection | Localization | Goal success M1 | Route regret M0 |
|---|---|---|---|---|---|---|---|
| off | task_only | 45 | 18% | 38% | 38% | 0.99 | 2.54 |
| off | model_first | 45 | 49% | 47% | 58% | 0.98 | 2.27 |
| off | graph_given | 45 | 62% | 91% | 98% | 1.00 | 0.11 |
| on | task_only | 45 | 31% | 47% | 51% | 0.99 | 2.35 |
| on | model_first | 45 | 31% | 60% | 56% | 1.00 | 2.47 |
| on | graph_given | 45 | 78% | 100% | 100% | 1.00 | 0.00 |

**Table 2. Exposure decides what the probes can show (all arms and reasoning settings)**

| Runs | n | Detection | Localization |
|---|---|---|---|
| Exposed | 121 | 91% (110/121) | 96% (116/121) |
| Not exposed | 149 | 42% (62/149) | 43% (64/149) |

**Table 3. Exposure / detection by scenario (reasoning settings pooled)**

| Scenario | Runs per arm | task_only exposed / detection | model_first exposed / detection | graph_given exposed / detection |
|---|---|---|---|---|
| silent_break | 20 | 40% / 45% | 45% / 65% | 85% / 100% |
| hard_removal | 20 | 30% / 75% | 65% / 80% | 95% / 85% |
| redirect | 20 | 20% / 30% | 40% / 60% | 95% / 95% |
| degradation | 10 | 20% / 40% | 60% / 40% | 80% / 100% |
| irrelevant | 20 | 10% / 20% | 0% / 15% | 0% / 100% |

**Table 4. No-change control: correctly reports no change**

| Reasoning | Runs per arm | task_only | model_first | graph_given |
|---|---|---|---|---|
| off | 10 | 80% | 90% | 90% |
| on | 10 | 90% | 70% | 90% |

**Cost and run quality.** Billed $21.49 in total, about $0.065 per run (off $9.69, on $11.80). Per run: task_only $0.054, model_first $0.100, graph_given $0.042. Reasoning tokens with reasoning on: mean 1,812, max 7,460 per run. Reasoning violations 0, cut-off calls 2, retried replies 0.

**H4 (six consecutive failures of the broken link).** Not in this CSV (recorded in each run's artifact; regenerate the CSV to include it).


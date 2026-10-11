## openai/gpt-5.6-sol: 306 runs

**Table 1. Behaviour and probes by arm (scenarios with a change)**

| Reasoning | Arm | Runs | Exposed | Detection | Localization | Goal success M1 | Route regret M0 |
|---|---|---|---|---|---|---|---|
| off | task_only | 102 | 63% | 58% | 51% | 0.97 | 1.96 |
| off | model_first | 102 | 59% | 59% | 51% | 0.96 | 2.06 |
| off | graph_given | 102 | 80% | 100% | 100% | 1.00 | 0.21 |

**Table 2. Exposure decides what the probes can show (all arms and reasoning settings)**

| Runs | n | Detection | Localization |
|---|---|---|---|
| Exposed | 206 | 85% (176/206) | 90% (185/206) |
| Not exposed | 100 | 45% (45/100) | 21% (21/100) |

**Table 3. Exposure / detection by scenario (reasoning settings pooled)**

| Scenario | Runs per arm | task_only exposed / detection | model_first exposed / detection | graph_given exposed / detection |
|---|---|---|---|---|
| silent_break | 51 | 65% / 75% | 59% / 69% | 82% / 100% |
| degradation | 51 | 61% / 41% | 59% / 49% | 78% / 100% |

**Cost and run quality.** Billed $27.16 in total, about $0.089 per run (off $27.16). Per run: task_only $0.096, model_first $0.108, graph_given $0.062. Reasoning violations 0, cut-off calls 3, retried replies 0.

**H4 (six consecutive failures of the broken link).** Reached in 30 of 306 runs with a change; the agent chose the broken link again in 20 of those.


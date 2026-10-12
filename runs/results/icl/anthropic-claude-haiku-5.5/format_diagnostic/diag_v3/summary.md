| Condition | Turns | Calls | Errors | Pure JSON | Strict parses | Routes optimal, strict | Routes optimal, content | Localization (B), content | Mean output tokens | Mean reasoning tokens | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|
| orig | ALL | 24 | 0 | 38% | 38% | 12% | 62% | 82% | – | – | $0.0000 |
| orig | graph_given B_task | 6 | 0 | 0% | 0% | 0% | 83% | 100% | – | – | $0.0000 |
| orig | model_first A_task | 6 | 0 | 100% | 100% | 42% | 42% | – | – | – | $0.0000 |
| orig | task_only A_task | 6 | 0 | 17% | 17% | 0% | 75% | – | – | – | $0.0000 |
| orig | task_only B_task | 6 | 0 | 33% | 33% | 8% | 50% | 60% | – | – | $0.0000 |
| off | ALL | 24 | 0 | 33% | 33% | 11% | 57% | 80% | 471 | 0 | $0.0181 |
| off | graph_given B_task | 6 | 0 | 0% | 0% | 0% | 79% | 100% | 615 | 0 | $0.0062 |
| off | model_first A_task | 6 | 0 | 100% | 100% | 33% | 33% | – | 294 | 0 | $0.0028 |
| off | task_only A_task | 6 | 0 | 17% | 17% | 8% | 80% | – | 541 | 0 | $0.0034 |
| off | task_only B_task | 6 | 0 | 17% | 17% | 4% | 31% | 50% | 435 | 0 | $0.0058 |
| schema_scratch | ALL | 24 | 0 | 100% | 100% | 71% | 71% | 83% | 480 | 0 | $0.0195 |
| schema_scratch | graph_given B_task | 6 | 0 | 100% | 100% | 83% | 83% | 100% | 514 | 0 | $0.0062 |
| schema_scratch | model_first A_task | 6 | 0 | 100% | 100% | 67% | 67% | – | 440 | 0 | $0.0035 |
| schema_scratch | task_only A_task | 6 | 0 | 100% | 100% | 88% | 88% | – | 505 | 0 | $0.0036 |
| schema_scratch | task_only B_task | 6 | 0 | 100% | 100% | 46% | 46% | 67% | 461 | 0 | $0.0062 |
| prompt_scratch | ALL | 24 | 0 | 75% | 75% | 60% | 77% | 92% | 715 | 0 | $0.0213 |
| prompt_scratch | graph_given B_task | 6 | 0 | 67% | 67% | 67% | 92% | 100% | 703 | 0 | $0.0065 |
| prompt_scratch | model_first A_task | 6 | 0 | 100% | 100% | 96% | 96% | – | 685 | 0 | $0.0040 |
| prompt_scratch | task_only A_task | 6 | 0 | 100% | 100% | 75% | 75% | – | 729 | 0 | $0.0041 |
| prompt_scratch | task_only B_task | 6 | 0 | 33% | 33% | 4% | 46% | 83% | 744 | 0 | $0.0068 |
| on_low | ALL | 24 | 0 | 92% | 92% | 84% | 92% | 100% | 1217 | 970 | $0.0271 |
| on_low | graph_given B_task | 6 | 0 | 83% | 83% | 75% | 92% | 100% | 1204 | 924 | $0.0079 |
| on_low | model_first A_task | 6 | 0 | 100% | 100% | 96% | 96% | – | 1153 | 936 | $0.0053 |
| on_low | task_only A_task | 6 | 0 | 100% | 100% | 100% | 100% | – | 1396 | 1170 | $0.0060 |
| on_low | task_only B_task | 6 | 0 | 83% | 83% | 67% | 79% | 100% | 1115 | 850 | $0.0078 |
| on_1k | ALL | 24 | 0 | 100% | 100% | 94% | 94% | 100% | 1653 | 1408 | $0.0323 |
| on_1k | graph_given B_task | 6 | 0 | 100% | 100% | 92% | 92% | 100% | 1694 | 1416 | $0.0094 |
| on_1k | model_first A_task | 6 | 0 | 100% | 100% | 96% | 96% | – | 1633 | 1415 | $0.0068 |
| on_1k | task_only A_task | 6 | 0 | 100% | 100% | 100% | 100% | – | 1669 | 1448 | $0.0068 |
| on_1k | task_only B_task | 6 | 0 | 100% | 100% | 88% | 88% | 100% | 1614 | 1355 | $0.0093 |

Routes optimal is the share of the four route queries answered with a valid, zero-regret route. Strict counts an answer that is not pure JSON as 0. Content reads the last JSON object carrying the routes. Groups: arm and turn of the sampled turns (the original answers of task-only and graph-given were malformed, those of model-first well-formed).

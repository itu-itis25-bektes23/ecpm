| Condition | Turns | Calls | Errors | Pure JSON | Strict parses | Routes optimal, strict | Routes optimal, content | Localization (B), content | Mean output tokens | Cost |
|---|---|---|---|---|---|---|---|---|---|---|
| orig | ALL | 12 | 0 | 25% | 25% | 8% | 75% | 100% | – | $0.0000 |
| orig | graph_given B_task | 3 | 0 | 0% | 0% | 0% | 92% | 100% | – | $0.0000 |
| orig | model_first A_task | 3 | 0 | 100% | 100% | 33% | 33% | – | – | $0.0000 |
| orig | task_only A_task | 3 | 0 | 0% | 0% | 0% | 92% | – | – | $0.0000 |
| orig | task_only B_task | 3 | 0 | 0% | 0% | 0% | 83% | 100% | – | $0.0000 |
| off | ALL | 24 | 0 | 25% | 25% | 9% | 75% | 100% | 598 | $0.0196 |
| off | graph_given B_task | 6 | 0 | 0% | 0% | 0% | 79% | 100% | 711 | $0.0067 |
| off | model_first A_task | 6 | 0 | 100% | 100% | 38% | 38% | – | 316 | $0.0028 |
| off | task_only A_task | 6 | 0 | 0% | 0% | 0% | 100% | – | 609 | $0.0036 |
| off | task_only B_task | 6 | 0 | 0% | 0% | 0% | 92% | 100% | 755 | $0.0065 |
| prefill | ALL | 12 | 12 | – | – | – | – | – | – | $0.0000 |
| prefill | graph_given B_task | 3 | 3 | – | – | – | – | – | – | $0.0000 |
| prefill | model_first A_task | 3 | 3 | – | – | – | – | – | – | $0.0000 |
| prefill | task_only A_task | 3 | 3 | – | – | – | – | – | – | $0.0000 |
| prefill | task_only B_task | 3 | 3 | – | – | – | – | – | – | $0.0000 |
| silent | ALL | 12 | 0 | 33% | 33% | 15% | 71% | 100% | 557 | $0.0096 |
| silent | graph_given B_task | 3 | 0 | 0% | 0% | 0% | 83% | 100% | 703 | $0.0033 |
| silent | model_first A_task | 3 | 0 | 100% | 100% | 33% | 33% | – | 259 | $0.0013 |
| silent | task_only A_task | 3 | 0 | 33% | 33% | 25% | 75% | – | 563 | $0.0018 |
| silent | task_only B_task | 3 | 0 | 0% | 0% | 0% | 92% | 100% | 704 | $0.0032 |
| on | ALL | 12 | 0 | 100% | 100% | 98% | 98% | 100% | 1560 | $0.0156 |
| on | graph_given B_task | 3 | 0 | 100% | 100% | 100% | 100% | 100% | 1650 | $0.0047 |
| on | model_first A_task | 3 | 0 | 100% | 100% | 100% | 100% | – | 1061 | $0.0025 |
| on | task_only A_task | 3 | 0 | 100% | 100% | 100% | 100% | – | 2333 | $0.0044 |
| on | task_only B_task | 3 | 0 | 100% | 100% | 92% | 92% | 100% | 1194 | $0.0039 |

Routes optimal is the share of the four route queries answered with a valid, zero-regret route. Strict counts an answer that is not pure JSON as 0. Content reads the last JSON object carrying the routes. Groups: arm and turn of the sampled turns (the original answers of task-only and graph-given were malformed, those of model-first well-formed).

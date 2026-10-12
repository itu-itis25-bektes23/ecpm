| Condition | Turns | Calls | Errors | Pure JSON | Strict parses | Routes optimal, strict | Routes optimal, content | Localization (B), content | Mean output tokens | Mean reasoning tokens | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|
| orig | ALL | 660 | 0 | 59% | 59% | 23% | 54% | 84% | – | – | $0.0000 |
| orig | graph_given A_task malformed | 57 | 0 | 72% | 72% | 23% | 49% | – | – | – | $0.0000 |
| orig | graph_given A_task well-formed | 53 | 0 | 100% | 100% | 45% | 45% | – | – | – | $0.0000 |
| orig | graph_given B_task malformed | 90 | 0 | 9% | 9% | 3% | 69% | 100% | – | – | $0.0000 |
| orig | graph_given B_task well-formed | 20 | 0 | 100% | 100% | 55% | 55% | 100% | – | – | $0.0000 |
| orig | model_first A_task malformed | 36 | 0 | 100% | 97% | 31% | 31% | – | – | – | $0.0000 |
| orig | model_first A_task well-formed | 74 | 0 | 100% | 100% | 43% | 43% | – | – | – | $0.0000 |
| orig | model_first B_task malformed | 40 | 0 | 52% | 52% | 16% | 51% | 92% | – | – | $0.0000 |
| orig | model_first B_task well-formed | 70 | 0 | 100% | 100% | 44% | 44% | 80% | – | – | $0.0000 |
| orig | task_only A_task malformed | 106 | 0 | 10% | 10% | 3% | 75% | – | – | – | $0.0000 |
| orig | task_only A_task well-formed | 4 | 0 | 100% | 100% | 50% | 50% | – | – | – | $0.0000 |
| orig | task_only B_task malformed | 66 | 0 | 14% | 14% | 3% | 67% | 83% | – | – | $0.0000 |
| orig | task_only B_task well-formed | 44 | 0 | 100% | 100% | 35% | 35% | 43% | – | – | $0.0000 |
| off | ALL | 660 | 0 | 58% | 58% | 22% | 53% | 86% | 441 | 0 | $0.4858 |
| off | graph_given A_task malformed | 57 | 0 | 86% | 86% | 33% | 47% | – | 356 | 0 | $0.0289 |
| off | graph_given A_task well-formed | 53 | 0 | 92% | 92% | 39% | 46% | – | 282 | 0 | $0.0249 |
| off | graph_given B_task malformed | 90 | 0 | 12% | 12% | 7% | 73% | 100% | 640 | 0 | $0.0947 |
| off | graph_given B_task well-formed | 20 | 0 | 75% | 75% | 41% | 59% | 100% | 362 | 0 | $0.0182 |
| off | model_first A_task malformed | 36 | 0 | 100% | 100% | 33% | 33% | – | 280 | 0 | $0.0164 |
| off | model_first A_task well-formed | 74 | 0 | 99% | 99% | 39% | 41% | – | 307 | 0 | $0.0347 |
| off | model_first B_task malformed | 40 | 0 | 58% | 58% | 14% | 49% | 95% | 448 | 0 | $0.0365 |
| off | model_first B_task well-formed | 70 | 0 | 93% | 93% | 37% | 42% | 81% | 326 | 0 | $0.0607 |
| off | task_only A_task malformed | 106 | 0 | 13% | 13% | 4% | 74% | – | 617 | 0 | $0.0650 |
| off | task_only A_task well-formed | 4 | 0 | 50% | 50% | 19% | 50% | – | 349 | 0 | $0.0019 |
| off | task_only B_task malformed | 66 | 0 | 27% | 27% | 8% | 61% | 86% | 539 | 0 | $0.0656 |
| off | task_only B_task well-formed | 44 | 0 | 68% | 68% | 20% | 39% | 48% | 338 | 0 | $0.0384 |
| json_schema | ALL | 660 | 0 | 100% | 100% | 41% | 41% | 82% | 264 | 0 | $0.4598 |
| json_schema | graph_given A_task malformed | 57 | 0 | 100% | 100% | 45% | 45% | – | 236 | 0 | $0.0278 |
| json_schema | graph_given A_task well-formed | 53 | 0 | 100% | 100% | 46% | 46% | – | 244 | 0 | $0.0261 |
| json_schema | graph_given B_task malformed | 90 | 0 | 100% | 100% | 39% | 39% | 100% | 308 | 0 | $0.0850 |
| json_schema | graph_given B_task well-formed | 20 | 0 | 100% | 100% | 54% | 54% | 100% | 271 | 0 | $0.0184 |
| json_schema | model_first A_task malformed | 36 | 0 | 100% | 100% | 41% | 41% | – | 246 | 0 | $0.0172 |
| json_schema | model_first A_task well-formed | 74 | 0 | 100% | 100% | 42% | 42% | – | 263 | 0 | $0.0361 |
| json_schema | model_first B_task malformed | 40 | 0 | 100% | 100% | 35% | 35% | 92% | 347 | 0 | $0.0367 |
| json_schema | model_first B_task well-formed | 70 | 0 | 100% | 100% | 40% | 40% | 77% | 316 | 0 | $0.0643 |
| json_schema | task_only A_task malformed | 106 | 0 | 100% | 100% | 37% | 37% | – | 225 | 0 | $0.0486 |
| json_schema | task_only A_task well-formed | 4 | 0 | 100% | 100% | 38% | 38% | – | 209 | 0 | $0.0018 |
| json_schema | task_only B_task malformed | 66 | 0 | 100% | 100% | 48% | 48% | 76% | 247 | 0 | $0.0597 |
| json_schema | task_only B_task well-formed | 44 | 0 | 100% | 100% | 35% | 35% | 45% | 204 | 0 | $0.0379 |
| schema_scratch | ALL | 660 | 0 | 100% | 100% | 71% | 71% | 86% | 525 | 0 | $0.5479 |
| schema_scratch | graph_given A_task malformed | 57 | 0 | 100% | 100% | 84% | 84% | – | 591 | 0 | $0.0381 |
| schema_scratch | graph_given A_task well-formed | 53 | 0 | 100% | 100% | 85% | 85% | – | 581 | 0 | $0.0352 |
| schema_scratch | graph_given B_task malformed | 90 | 0 | 100% | 100% | 68% | 68% | 100% | 551 | 0 | $0.0961 |
| schema_scratch | graph_given B_task well-formed | 20 | 0 | 100% | 100% | 76% | 76% | 100% | 554 | 0 | $0.0213 |
| schema_scratch | model_first A_task malformed | 36 | 0 | 100% | 100% | 74% | 74% | – | 453 | 0 | $0.0211 |
| schema_scratch | model_first A_task well-formed | 74 | 0 | 100% | 100% | 74% | 74% | – | 475 | 0 | $0.0442 |
| schema_scratch | model_first B_task malformed | 40 | 0 | 100% | 100% | 72% | 72% | 95% | 527 | 0 | $0.0404 |
| schema_scratch | model_first B_task well-formed | 70 | 0 | 100% | 100% | 67% | 67% | 83% | 495 | 0 | $0.0708 |
| schema_scratch | task_only A_task malformed | 106 | 0 | 100% | 100% | 75% | 75% | – | 561 | 0 | $0.0667 |
| schema_scratch | task_only A_task well-formed | 4 | 0 | 100% | 100% | 69% | 69% | – | 556 | 0 | $0.0025 |
| schema_scratch | task_only B_task malformed | 66 | 0 | 100% | 100% | 65% | 65% | 79% | 507 | 0 | $0.0685 |
| schema_scratch | task_only B_task well-formed | 44 | 0 | 100% | 100% | 44% | 44% | 59% | 432 | 0 | $0.0431 |
| prompt_scratch | ALL | 660 | 0 | 84% | 84% | 70% | 81% | 87% | 748 | 0 | $0.5922 |
| prompt_scratch | graph_given A_task malformed | 57 | 0 | 98% | 96% | 93% | 96% | – | 850 | 0 | $0.0434 |
| prompt_scratch | graph_given A_task well-formed | 53 | 0 | 96% | 96% | 93% | 97% | – | 925 | 0 | $0.0424 |
| prompt_scratch | graph_given B_task malformed | 90 | 0 | 50% | 50% | 40% | 82% | 100% | 812 | 0 | $0.1032 |
| prompt_scratch | graph_given B_task well-formed | 20 | 0 | 75% | 75% | 68% | 90% | 100% | 800 | 0 | $0.0227 |
| prompt_scratch | model_first A_task malformed | 36 | 0 | 100% | 100% | 91% | 91% | – | 663 | 0 | $0.0235 |
| prompt_scratch | model_first A_task well-formed | 74 | 0 | 100% | 100% | 86% | 86% | – | 665 | 0 | $0.0485 |
| prompt_scratch | model_first B_task malformed | 40 | 0 | 90% | 90% | 69% | 78% | 95% | 691 | 0 | $0.0416 |
| prompt_scratch | model_first B_task well-formed | 70 | 0 | 93% | 93% | 70% | 75% | 80% | 663 | 0 | $0.0730 |
| prompt_scratch | task_only A_task malformed | 106 | 0 | 100% | 100% | 83% | 85% | – | 792 | 0 | $0.0751 |
| prompt_scratch | task_only A_task well-formed | 4 | 0 | 100% | 100% | 81% | 81% | – | 716 | 0 | $0.0027 |
| prompt_scratch | task_only B_task malformed | 66 | 0 | 64% | 64% | 46% | 67% | 82% | 680 | 0 | $0.0707 |
| prompt_scratch | task_only B_task well-formed | 44 | 0 | 57% | 57% | 28% | 51% | 64% | 639 | 0 | $0.0453 |

Routes optimal is the share of the four route queries answered with a valid, zero-regret route. Strict counts an answer that is not pure JSON as 0. Content reads the last JSON object carrying the routes. Groups: arm and turn of the sampled turns (the original answers of task-only and graph-given were malformed, those of model-first well-formed).

## Paired comparisons

| Condition | Against | Measure | Turns | Condition mean | Baseline mean | Difference | 95% interval |
|---|---|---|---|---|---|---|---|
| json_schema | off | pure_json | 660 | 1.00 | 0.58 | +0.42 | [+0.38, +0.45] |
| json_schema | off | routes_strict | 660 | 0.41 | 0.22 | +0.19 | [+0.17, +0.21] |
| json_schema | off | routes_content | 660 | 0.41 | 0.50 | -0.09 | [-0.12, -0.07] |
| json_schema | off | detection | 318 | 0.88 | 0.89 | -0.00 | [-0.03, +0.02] |
| json_schema | off | localization | 318 | 0.84 | 0.86 | -0.02 | [-0.04, +0.01] |
| prompt_scratch | off | pure_json | 660 | 0.84 | 0.58 | +0.26 | [+0.22, +0.30] |
| prompt_scratch | off | routes_strict | 660 | 0.70 | 0.22 | +0.48 | [+0.45, +0.51] |
| prompt_scratch | off | routes_content | 660 | 0.81 | 0.50 | +0.31 | [+0.28, +0.33] |
| prompt_scratch | off | detection | 318 | 0.89 | 0.89 | +0.01 | [-0.02, +0.03] |
| prompt_scratch | off | localization | 318 | 0.88 | 0.86 | +0.03 | [-0.00, +0.05] |
| schema_scratch | off | pure_json | 660 | 1.00 | 0.58 | +0.42 | [+0.38, +0.45] |
| schema_scratch | off | routes_strict | 660 | 0.71 | 0.22 | +0.49 | [+0.47, +0.52] |
| schema_scratch | off | routes_content | 660 | 0.71 | 0.50 | +0.21 | [+0.19, +0.24] |
| schema_scratch | off | detection | 318 | 0.89 | 0.89 | +0.01 | [-0.02, +0.03] |
| schema_scratch | off | localization | 318 | 0.88 | 0.86 | +0.02 | [-0.01, +0.04] |
| json_schema | orig | pure_json | 660 | 1.00 | 0.59 | +0.41 | [+0.37, +0.45] |
| json_schema | orig | routes_strict | 660 | 0.41 | 0.23 | +0.18 | [+0.16, +0.20] |
| json_schema | orig | routes_content | 660 | 0.41 | 0.51 | -0.10 | [-0.12, -0.07] |
| json_schema | orig | detection | 316 | 0.87 | 0.87 | +0.00 | [-0.02, +0.03] |
| json_schema | orig | localization | 316 | 0.83 | 0.84 | -0.01 | [-0.03, +0.02] |
| prompt_scratch | orig | pure_json | 660 | 0.84 | 0.59 | +0.25 | [+0.21, +0.29] |
| prompt_scratch | orig | routes_strict | 660 | 0.70 | 0.23 | +0.47 | [+0.43, +0.50] |
| prompt_scratch | orig | routes_content | 660 | 0.81 | 0.51 | +0.30 | [+0.28, +0.33] |
| prompt_scratch | orig | detection | 316 | 0.89 | 0.87 | +0.02 | [-0.01, +0.05] |
| prompt_scratch | orig | localization | 316 | 0.88 | 0.84 | +0.04 | [+0.01, +0.07] |
| schema_scratch | orig | pure_json | 660 | 1.00 | 0.59 | +0.41 | [+0.37, +0.45] |
| schema_scratch | orig | routes_strict | 660 | 0.71 | 0.23 | +0.48 | [+0.46, +0.51] |
| schema_scratch | orig | routes_content | 660 | 0.71 | 0.51 | +0.21 | [+0.18, +0.23] |
| schema_scratch | orig | detection | 316 | 0.89 | 0.87 | +0.02 | [-0.01, +0.05] |
| schema_scratch | orig | localization | 316 | 0.87 | 0.84 | +0.03 | [+0.01, +0.06] |

Paired over the same turns. routes_strict counts an answer that is not pure JSON as 0 (the paper's primary scoring), routes_content reads the last JSON object carrying the routes. Detection and localization exist for Period B turns only. 95% interval: normal approximation of the paired mean.

Serving providers: Anthropic. Finish reasons: {'stop': 2640}.

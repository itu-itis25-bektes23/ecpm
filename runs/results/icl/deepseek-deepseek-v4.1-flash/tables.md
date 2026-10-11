# Audited DeepSeek ICL results

Generated from saved metric rows, without reparsing or rescoring.

| Arm | Completed / planned | Incomplete |
|---|---:|---:|
| model_first | 220/220 | 0/220 |
| task_only | 216/220 | 4/220 |
| graph_given | 219/220 | 1/220 |

## Scientific results by cohort

Each cell shows numerator/denominator, not an independent-sample confidence interval. Invalid scientific answers remain in applicable denominators. Incomplete conversations are not scored. Modes, histories and nominal cap/source cohorts stay separate; 32K cohorts can contain recorded 64K recovery attempts.

| Cap cohort | Arm | History | Reasoning | Mode | Complete n | A belief exact | B belief exact | A routes optimal or correct no-route | B routes optimal or correct no-route | Detection | Localization | Self Preservation mean | Truth Preservation mean | Truth all-four |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 32768 | graph_given | retained | off | det | 25 | 400/400 | 400/400 | 52/100 | 47/100 | 25/25 | 25/25 | 100/100 | 100/100 | 25/25 |
| 32768 | graph_given | retained | off | sto | 30 | 480/480 | 480/480 | 58/120 | 56/120 | 30/30 | 30/30 | 120/120 | 120/120 | 30/30 |
| 32768 | graph_given | retained | on | det | 25 | 400/400 | 400/400 | 100/100 | 100/100 | 25/25 | 25/25 | 100/100 | 100/100 | 25/25 |
| 32768 | graph_given | retained | on | sto | 30 | 480/480 | 480/480 | 120/120 | 120/120 | 30/30 | 30/30 | 120/120 | 120/120 | 30/30 |
| 32768 | graph_given | separate | off | det | 25 | 400/400 | 400/400 | 55/100 | 53/100 | 25/25 | 25/25 | 100/100 | 100/100 | 25/25 |
| 32768 | graph_given | separate | off | sto | 30 | 480/480 | 480/480 | 63/120 | 54/120 | 30/30 | 30/30 | 120/120 | 120/120 | 30/30 |
| 32768 | graph_given | separate | on | det | 25 | 400/400 | 400/400 | 100/100 | 100/100 | 25/25 | 25/25 | 100/100 | 100/100 | 25/25 |
| 32768 | graph_given | separate | on | sto | 29 | 464/464 | 464/464 | 116/116 | 116/116 | 29/29 | 29/29 | 116/116 | 116/116 | 29/29 |
| 32768 | model_first | retained | off | det | 25 | 400/400 | 391/400 | 62/100 | 53/100 | 25/25 | 25/25 | 100/100 | 100/100 | 25/25 |
| 32768 | model_first | retained | off | sto | 30 | 4/480 | 11/480 | 44/120 | 52/120 | 21/30 | 19/30 | 18/120 | 0/120 | 0/30 |
| 32768 | model_first | retained | on | det | 25 | 400/400 | 400/400 | 100/100 | 100/100 | 25/25 | 25/25 | 100/100 | 100/100 | 25/25 |
| 32768 | model_first | retained | on | sto | 30 | 18/480 | 29/480 | 114/120 | 115/120 | 22/30 | 21/30 | 28/120 | 3/120 | 0/30 |
| 32768 | model_first | separate | off | det | 24 | 384/384 | 375/384 | 55/96 | 49/96 | 23/24 | 23/24 | 96/96 | 96/96 | 24/24 |
| 32768 | model_first | separate | off | sto | 29 | 2/464 | 7/464 | 41/116 | 47/116 | 21/29 | 19/29 | 8/116 | 0/116 | 0/29 |
| 32768 | model_first | separate | on | det | 24 | 384/384 | 384/384 | 96/96 | 96/96 | 24/24 | 24/24 | 96/96 | 96/96 | 24/24 |
| 32768 | model_first | separate | on | sto | 30 | 18/480 | 29/480 | 114/120 | 113/120 | 26/30 | 25/30 | 28/120 | 3/120 | 0/30 |
| 32768 | task_only | retained | off | det | 25 | 368/400 | 374/400 | 49/100 | 45/100 | 22/25 | 22/25 | 92/100 | 96/100 | 24/25 |
| 32768 | task_only | retained | off | sto | 30 | 2/480 | 6/480 | 45/120 | 40/120 | 19/30 | 14/30 | 62/120 | 0/120 | 0/30 |
| 32768 | task_only | retained | on | det | 25 | 400/400 | 400/400 | 100/100 | 100/100 | 25/25 | 25/25 | 100/100 | 100/100 | 25/25 |
| 32768 | task_only | retained | on | sto | 28 | 18/448 | 28/448 | 108/112 | 106/112 | 21/28 | 21/28 | 31/112 | 3/112 | 0/28 |
| 32768 | task_only | separate | off | det | 25 | 400/400 | 390/400 | 46/100 | 35/100 | 25/25 | 24/25 | 100/100 | 100/100 | 25/25 |
| 32768 | task_only | separate | off | sto | 29 | 3/464 | 10/464 | 33/116 | 30/116 | 13/29 | 11/29 | 16/116 | 0/116 | 0/29 |
| 32768 | task_only | separate | on | det | 25 | 400/400 | 400/400 | 100/100 | 100/100 | 25/25 | 25/25 | 100/100 | 100/100 | 25/25 |
| 32768 | task_only | separate | on | sto | 29 | 18/464 | 29/464 | 111/116 | 112/116 | 26/29 | 25/29 | 28/116 | 3/116 | 0/29 |
| 16384 | model_first | separate | off | det | 1 | 16/16 | 15/16 | 3/4 | 2/4 | 1/1 | 1/1 | 4/4 | 4/4 | 1/1 |
| 16384 | model_first | separate | off | sto | 1 | 0/16 | 0/16 | 1/4 | 1/4 | 0/1 | 0/1 | 0/4 | 0/4 | 0/1 |
| 16384 | model_first | separate | on | det | 1 | 16/16 | 16/16 | 4/4 | 4/4 | 1/1 | 1/1 | 4/4 | 4/4 | 1/1 |

Full conditional destination/MAE/regret, parsing, self/truth exact and tolerance Preservation, and query-level metrics remain in metrics.csv.gz and aggregates.csv.gz. No failed case or malformed answer was rescued.

## Accounting

| Component | USD | Scope n |
|---|---:|---:|
| New reported charges | 12.14809357 | 3978 known requests |
| Unknown-charge reservations | 1.06659840 | 8 requests |
| Historical carry | 0.06029674 | completed/failed original batch attempts |
| Ledger exposure | 13.27498871 | cumulative batch |
| Remaining authorization | 6.72501129 | cumulative batch |
| Earlier pilots outside batch | 0.01826054 | 2 conversations |

Top-level provider charges are not invoice reconciliation. Upstream cost_details are not added again. Unknown charges retain reservations. Raw inconsistent reasoning subcounts are preserved, not normalized.

All three arms used prepare, task, readout in both periods: six stages per complete conversation. Model-first received no extra turn. Recovery attempts are not extra preparation treatment stages.

Five graph seeds, one repeat per configuration. These are descriptive results, not 655 independent graph samples or evidence of statistical significance.

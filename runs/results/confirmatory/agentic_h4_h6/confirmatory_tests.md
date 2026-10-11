# Confirmatory tests of H4 and H6 (agentic)

Design, fixed before these runs: 51 held-out seeds (SEEDS_51, disjoint from the five exploratory graphs), stochastic eight-node family, silent break and degradation, reasoning off, the three arms (306 runs per model). The pre-registered test uses the grid without a preparation turn; the same grid with matched preparation turns (--matched-prep) separates the extra turn. Code: results-freeze (10c93b5).

H4: share of task-only runs that chose the broken link again after six consecutive failures of it, among runs that reached six; prediction > 0.10, one-sided 95% Clopper-Pearson lower bound. H6: model-first minus task-only on the same share; prediction < 0, one-sided Fisher exact test. A comparison needs at least 10 qualifying runs per arm.

| Grid | Model | Runs | H4: task-only chose again | Lower bound | H6: model-first | Difference | One-sided p | Cost (USD, billed) |
|---|---|---|---|---|---|---|---|---|
| pre-registered (no preparation turn) | Claude Haiku 5.5 | 306 | 19 of 21 (90%) | 0.73 | 10 of 14 (71%) | -19% | 0.16 | 9.32 |
| pre-registered (no preparation turn) | DeepSeek V4.1 Flash | 306 | 17 of 21 (81%) | 0.62 | 26 of 28 (93%) | +12% | 0.96 | 3.80 |
| pre-registered (no preparation turn) | GPT-5.6 Sol | 306 | 14 of 17 (82%) | 0.60 | 10 of 15 (67%) | -16% | 0.27 | 20.96 |
| matched preparation turns | Claude Haiku 5.5 | 306 | 15 of 20 (75%) | 0.54 | 10 of 12 (83%) | +8% | 0.84 | 12.44 |
| matched preparation turns | DeepSeek V4.1 Flash | 306 | 27 of 31 (87%) | 0.73 | 20 of 25 (80%) | -7% | 0.36 | 4.59 |
| matched preparation turns | GPT-5.6 Sol | 306 | 8 of 14 (57%) | 0.33 | 12 of 16 (75%) | +18% | 0.92 | 27.16 |

Result: H4 is supported for all three models in the pre-registered grid (every lower bound above 0.10, at least 10 qualifying runs per arm), and again with matched preparation turns. H6 is not supported for any model in either grid.

# DeepSeek V4.1 Flash agentic grid: per-cell summaries

330 runs, cap 65,536, in two parts: 255 runs by Christian (reasoning off: all 165; reasoning on: deterministic and stochastic no_change) and the remaining 75 stochastic reasoning-on runs (irrelevant, silent_break, hard_removal, redirect, degradation) by Efe, with the same tool and settings. The combined per-run data is agentic_runs.csv; Tables 1-4 are in agentic_tables.md.

## Part 1: 255 runs (Christian)

#### scenario degradation · mode sto · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 6.05 ± 1.16 | 6.73 ± 1.40 | 3.90 ± 1.49 |
| Mean steps M1 | 7.90 ± 3.89 | 6.00 ± 2.85 | 5.75 ± 3.14 |
| Optimal action rate M0 | 0.70 ± 0.11 | 0.63 ± 0.17 | 0.81 ± 0.17 |
| Optimal action rate M1 | 0.61 ± 0.11 | 0.70 ± 0.17 | 0.75 ± 0.24 |
| Route regret M0 | 2.52 ± 0.28 | 3.42 ± 0.64 | 0.39 ± 0.37 |
| Exposed (share of runs) | 1.00 ± 0.00 | 0.40 ± 0.55 | 0.80 ± 0.45 |
| Detection correct | 0.00 ± 0.00 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Localization correct | 0.40 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Preservation accuracy | 0.75 ± 0.00 | 0.80 ± 0.21 | 1.00 ± 0.00 |
| Route probe optimal | 0.00 ± 0.00 | 0.40 ± 0.55 | 0.40 ± 0.55 |
| Input tokens | 182,684 ± 111,878 | 330,217 ± 150,978 | 126,206 ± 94,271 |
| Output tokens | 1,737 ± 640 | 5,823 ± 1,251 | 1,531 ± 657 |
| Cost per run (USD, billed where reported) | 0.01 ± 0.01 | 0.01 ± 0.00 | 0.00 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (11 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 5 | 2 | 4 |
| Detection correct | 0.00 ± 0.00 | 0.50 ± 0.71 | 1.00 ± 0.00 |
| Localization correct | 0.40 ± 0.55 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 0.75 ± 0.00 | 0.88 ± 0.18 | 1.00 ± 0.00 |

#### scenario hard_removal · mode det · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 5.25 ± 1.06 | 4.65 ± 1.23 | 2.80 ± 1.10 |
| Mean steps M1 | 3.80 ± 0.84 | 3.80 ± 0.84 | 3.40 ± 0.55 |
| Optimal action rate M0 | 0.67 ± 0.13 | 0.74 ± 0.18 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.91 ± 0.12 | 0.91 ± 0.12 | 1.00 ± 0.00 |
| Route regret M0 | 2.45 ± 0.27 | 1.85 ± 0.88 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.40 ± 0.55 | 0.40 ± 0.55 | 0.80 ± 0.45 |
| Detection correct | 0.40 ± 0.55 | 0.20 ± 0.45 | 1.00 ± 0.00 |
| Localization correct | 0.80 ± 0.45 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Preservation accuracy | 0.80 ± 0.11 | 0.85 ± 0.14 | 1.00 ± 0.00 |
| Route probe optimal | 0.60 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Input tokens | 78,896 ± 25,466 | 149,145 ± 36,784 | 51,607 ± 19,797 |
| Output tokens | 1,098 ± 162 | 3,548 ± 368 | 789 ± 211 |
| Cost per run (USD, billed where reported) | 0.00 ± 0.00 | 0.01 ± 0.00 | 0.00 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (8 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 2 | 2 | 4 |
| Detection correct | 1.00 ± 0.00 | 0.50 ± 0.71 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 0.88 ± 0.18 | 0.88 ± 0.18 | 1.00 ± 0.00 |

#### scenario hard_removal · mode det · reasoning on (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 6.60 ± 2.28 | 4.65 ± 1.23 | 2.80 ± 1.10 |
| Mean steps M1 | 5.65 ± 2.99 | 3.80 ± 0.84 | 3.40 ± 0.55 |
| Optimal action rate M0 | 0.64 ± 0.20 | 0.74 ± 0.18 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.89 ± 0.13 | 0.91 ± 0.12 | 1.00 ± 0.00 |
| Route regret M0 | 3.80 ± 2.26 | 1.85 ± 0.88 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.60 ± 0.55 | 0.40 ± 0.55 | 0.80 ± 0.45 |
| Detection correct | 1.00 ± 0.00 | 0.80 ± 0.45 | 0.80 ± 0.45 |
| Localization correct | 0.80 ± 0.45 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 0.90 ± 0.14 | 0.90 ± 0.14 | 1.00 ± 0.00 |
| Route probe optimal | 0.80 ± 0.45 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Input tokens | 118,046 ± 87,629 | 124,620 ± 36,703 | 43,887 ± 16,040 |
| Output tokens | 44,552 ± 80,849 | 21,796 ± 34,731 | 2,965 ± 1,362 |
| Cost per run (USD, billed where reported) | 0.04 ± 0.06 | 0.02 ± 0.02 | 0.01 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (9 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 3 | 2 | 4 |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 0.67 ± 0.58 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 0.92 ± 0.14 | 1.00 ± 0.00 | 1.00 ± 0.00 |

#### scenario hard_removal · mode sto · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 0.80 ± 0.45 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Mean steps M0 | 6.25 ± 1.31 | 6.13 ± 1.10 | 3.80 ± 1.44 |
| Mean steps M1 | 5.69 ± 2.11 | 5.19 ± 1.85 | 5.10 ± 2.18 |
| Optimal action rate M0 | 0.65 ± 0.20 | 0.66 ± 0.15 | 0.86 ± 0.19 |
| Optimal action rate M1 | 0.60 ± 0.25 | 0.80 ± 0.20 | 0.96 ± 0.08 |
| Route regret M0 | 2.77 ± 2.03 | 2.79 ± 0.98 | 0.29 ± 0.40 |
| Exposed (share of runs) | 1.00 ± 0.00 | 0.60 ± 0.55 | 0.80 ± 0.45 |
| Detection correct | 0.40 ± 0.55 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Preservation accuracy | 0.95 ± 0.11 | 0.85 ± 0.14 | 1.00 ± 0.00 |
| Route probe optimal | 0.20 ± 0.45 | 0.40 ± 0.55 | 0.80 ± 0.45 |
| Input tokens | 222,974 ± 201,235 | 385,713 ± 298,349 | 105,729 ± 65,190 |
| Output tokens | 2,017 ± 907 | 5,409 ± 1,431 | 1,410 ± 483 |
| Cost per run (USD, billed where reported) | 0.01 ± 0.01 | 0.02 ± 0.01 | 0.00 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (12 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 5 | 3 | 4 |
| Detection correct | 0.40 ± 0.55 | 0.67 ± 0.58 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 0.67 ± 0.58 | 1.00 ± 0.00 |
| Preservation accuracy | 0.95 ± 0.11 | 0.92 ± 0.14 | 1.00 ± 0.00 |

#### scenario irrelevant · mode det · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 5.25 ± 1.50 | 4.65 ± 1.23 | 2.80 ± 1.10 |
| Mean steps M1 | 4.75 ± 1.30 | 3.65 ± 1.22 | 2.80 ± 1.10 |
| Optimal action rate M0 | 0.69 ± 0.13 | 0.74 ± 0.18 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.73 ± 0.15 | 0.79 ± 0.22 | 1.00 ± 0.00 |
| Route regret M0 | 2.45 ± 1.10 | 1.85 ± 0.88 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.20 ± 0.45 | 0.20 ± 0.45 | 0.00 ± 0.00 |
| Detection correct | 0.20 ± 0.45 | 0.20 ± 0.45 | 0.80 ± 0.45 |
| Localization correct | 0.20 ± 0.45 | 0.20 ± 0.45 | 1.00 ± 0.00 |
| Preservation accuracy | 0.80 ± 0.11 | 0.80 ± 0.11 | 1.00 ± 0.00 |
| Route probe optimal | 0.20 ± 0.45 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Input tokens | 97,195 ± 40,965 | 146,832 ± 65,223 | 47,233 ± 27,028 |
| Output tokens | 1,252 ± 380 | 3,408 ± 995 | 746 ± 281 |
| Cost per run (USD, billed where reported) | 0.01 ± 0.00 | 0.01 ± 0.01 | 0.00 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (2 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 1 | 1 | 0 |
| Detection correct | 1.00 | 1.00 | n/a |
| Localization correct | 1.00 | 1.00 | n/a |
| Preservation accuracy | 1.00 | 1.00 | n/a |

#### scenario irrelevant · mode det · reasoning on (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 0.95 ± 0.11 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 6.00 ± 1.56 | 4.85 ± 1.28 | 2.80 ± 1.10 |
| Mean steps M1 | 6.00 ± 4.06 | 3.70 ± 1.30 | 2.80 ± 1.10 |
| Optimal action rate M0 | 0.62 ± 0.12 | 0.72 ± 0.16 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.66 ± 0.23 | 0.78 ± 0.22 | 1.00 ± 0.00 |
| Route regret M0 | 3.20 ± 0.62 | 2.05 ± 0.54 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.20 ± 0.45 | 0.20 ± 0.45 | 0.00 ± 0.00 |
| Detection correct | 0.20 ± 0.45 | 0.20 ± 0.45 | 1.00 ± 0.00 |
| Localization correct | 0.20 ± 0.45 | 0.20 ± 0.45 | 1.00 ± 0.00 |
| Preservation accuracy | 0.80 ± 0.11 | 0.80 ± 0.11 | 1.00 ± 0.00 |
| Route probe optimal | 0.20 ± 0.45 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Input tokens | 124,052 ± 93,737 | 125,095 ± 41,709 | 39,106 ± 20,661 |
| Output tokens | 86,813 ± 163,628 | 74,970 ± 47,389 | 2,326 ± 828 |
| Cost per run (USD, billed where reported) | 0.06 ± 0.11 | 0.05 ± 0.03 | 0.00 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (2 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 1 | 1 | 0 |
| Detection correct | 1.00 | 1.00 | n/a |
| Localization correct | 1.00 | 1.00 | n/a |
| Preservation accuracy | 1.00 | 1.00 | n/a |

#### scenario irrelevant · mode sto · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 6.45 ± 1.56 | 6.15 ± 1.58 | 4.05 ± 1.77 |
| Mean steps M1 | 6.45 ± 2.81 | 5.75 ± 3.41 | 4.70 ± 2.51 |
| Optimal action rate M0 | 0.65 ± 0.15 | 0.65 ± 0.25 | 0.83 ± 0.18 |
| Optimal action rate M1 | 0.70 ± 0.24 | 0.67 ± 0.33 | 0.86 ± 0.15 |
| Route regret M0 | 2.99 ± 0.89 | 2.64 ± 1.44 | 0.50 ± 0.47 |
| Exposed (share of runs) | 0.20 ± 0.45 | 0.20 ± 0.45 | 0.20 ± 0.45 |
| Detection correct | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.80 ± 0.45 |
| Localization correct | 0.20 ± 0.45 | 0.20 ± 0.45 | 1.00 ± 0.00 |
| Preservation accuracy | 0.75 ± 0.00 | 0.75 ± 0.00 | 1.00 ± 0.00 |
| Route probe optimal | 0.40 ± 0.55 | 0.40 ± 0.55 | 0.40 ± 0.55 |
| Input tokens | 160,978 ± 90,089 | 265,565 ± 157,926 | 105,938 ± 76,630 |
| Output tokens | 1,705 ± 607 | 4,810 ± 1,330 | 1,301 ± 556 |
| Cost per run (USD, billed where reported) | 0.01 ± 0.01 | 0.01 ± 0.01 | 0.00 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (3 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 1 | 1 | 1 |
| Detection correct | 0.00 | 0.00 | 1.00 |
| Localization correct | 1.00 | 1.00 | 1.00 |
| Preservation accuracy | 0.75 | 0.75 | 1.00 |

#### scenario no_change · mode det · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 5.10 ± 1.23 | 4.65 ± 1.23 | 2.80 ± 1.10 |
| Mean steps M1 | 4.20 ± 1.48 | 3.60 ± 1.14 | 2.80 ± 1.10 |
| Optimal action rate M0 | 0.75 ± 0.17 | 0.74 ± 0.18 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.81 ± 0.21 | 0.79 ± 0.22 | 1.00 ± 0.00 |
| Route regret M0 | 2.30 ± 1.29 | 1.85 ± 0.88 | 0.00 ± 0.00 |
| Exposed (share of runs) | n/a | n/a | n/a |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | n/a | n/a | n/a |
| Preservation accuracy | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Route probe optimal | 0.40 ± 0.55 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Input tokens | 82,418 ± 34,227 | 135,600 ± 57,922 | 44,825 ± 26,532 |
| Output tokens | 1,176 ± 252 | 3,143 ± 824 | 762 ± 312 |
| Cost per run (USD, billed where reported) | 0.01 ± 0.00 | 0.01 ± 0.01 | 0.00 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (0 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 0 | 0 | 0 |
| Detection correct | n/a | n/a | n/a |
| Localization correct | n/a | n/a | n/a |
| Preservation accuracy | n/a | n/a | n/a |

#### scenario no_change · mode det · reasoning on (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 6.70 ± 2.39 | 4.70 ± 1.19 | 2.80 ± 1.10 |
| Mean steps M1 | 5.60 ± 2.93 | 3.60 ± 1.14 | 2.80 ± 1.10 |
| Optimal action rate M0 | 0.66 ± 0.12 | 0.72 ± 0.17 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.76 ± 0.14 | 0.79 ± 0.22 | 1.00 ± 0.00 |
| Route regret M0 | 3.90 ± 1.67 | 1.90 ± 0.88 | 0.00 ± 0.00 |
| Exposed (share of runs) | n/a | n/a | n/a |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | n/a | n/a | n/a |
| Preservation accuracy | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Route probe optimal | 0.60 ± 0.55 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Input tokens | 111,409 ± 70,397 | 113,044 ± 39,048 | 36,939 ± 20,091 |
| Output tokens | 12,975 ± 8,875 | 6,019 ± 3,050 | 2,057 ± 1,045 |
| Cost per run (USD, billed where reported) | 0.01 ± 0.01 | 0.01 ± 0.00 | 0.00 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (0 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 0 | 0 | 0 |
| Detection correct | n/a | n/a | n/a |
| Localization correct | n/a | n/a | n/a |
| Preservation accuracy | n/a | n/a | n/a |

#### scenario no_change · mode sto · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 6.05 ± 0.74 | 6.65 ± 0.86 | 3.80 ± 1.44 |
| Mean steps M1 | 5.65 ± 2.86 | 5.20 ± 1.93 | 4.50 ± 2.33 |
| Optimal action rate M0 | 0.76 ± 0.10 | 0.62 ± 0.17 | 0.86 ± 0.19 |
| Optimal action rate M1 | 0.80 ± 0.15 | 0.71 ± 0.18 | 0.86 ± 0.19 |
| Route regret M0 | 2.56 ± 0.67 | 3.28 ± 0.68 | 0.29 ± 0.40 |
| Exposed (share of runs) | n/a | n/a | n/a |
| Detection correct | 0.80 ± 0.45 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | n/a | n/a | n/a |
| Preservation accuracy | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Route probe optimal | 0.40 ± 0.55 | 0.20 ± 0.45 | 0.60 ± 0.55 |
| Input tokens | 128,490 ± 68,776 | 295,438 ± 126,449 | 88,857 ± 58,825 |
| Output tokens | 1,534 ± 495 | 5,502 ± 1,544 | 1,128 ± 356 |
| Cost per run (USD, billed where reported) | 0.01 ± 0.01 | 0.02 ± 0.00 | 0.00 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (0 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 0 | 0 | 0 |
| Detection correct | n/a | n/a | n/a |
| Localization correct | n/a | n/a | n/a |
| Preservation accuracy | n/a | n/a | n/a |

#### scenario no_change · mode sto · reasoning on (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 6.75 ± 1.67 | 6.20 ± 1.54 | 3.60 ± 1.51 |
| Mean steps M1 | 5.95 ± 2.37 | 5.35 ± 2.90 | 4.35 ± 2.30 |
| Optimal action rate M0 | 0.66 ± 0.19 | 0.68 ± 0.16 | 0.96 ± 0.09 |
| Optimal action rate M1 | 0.67 ± 0.21 | 0.77 ± 0.23 | 0.97 ± 0.07 |
| Route regret M0 | 3.28 ± 2.53 | 2.58 ± 0.97 | 0.11 ± 0.24 |
| Exposed (share of runs) | n/a | n/a | n/a |
| Detection correct | 1.00 ± 0.00 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Localization correct | n/a | n/a | n/a |
| Preservation accuracy | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Route probe optimal | 0.20 ± 0.45 | 0.40 ± 0.55 | 0.80 ± 0.45 |
| Input tokens | 115,243 ± 50,429 | 205,270 ± 101,312 | 66,982 ± 45,783 |
| Output tokens | 37,346 ± 36,769 | 16,080 ± 6,184 | 5,814 ± 2,336 |
| Cost per run (USD, billed where reported) | 0.03 ± 0.03 | 0.02 ± 0.01 | 0.01 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (0 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 0 | 0 | 0 |
| Detection correct | n/a | n/a | n/a |
| Localization correct | n/a | n/a | n/a |
| Preservation accuracy | n/a | n/a | n/a |

#### scenario redirect · mode det · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 6.00 ± 3.52 | 4.65 ± 1.23 | 2.80 ± 1.10 |
| Mean steps M1 | 5.20 ± 4.60 | 3.20 ± 1.48 | 2.60 ± 1.82 |
| Optimal action rate M0 | 0.73 ± 0.12 | 0.74 ± 0.18 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.75 ± 0.17 | 0.79 ± 0.22 | 0.91 ± 0.12 |
| Route regret M0 | 3.20 ± 2.75 | 1.85 ± 0.88 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.80 ± 0.45 | 0.40 ± 0.55 | 0.80 ± 0.45 |
| Detection correct | 0.60 ± 0.55 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Localization correct | 0.60 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Preservation accuracy | 0.90 ± 0.14 | 0.85 ± 0.14 | 1.00 ± 0.00 |
| Route probe optimal | 0.20 ± 0.45 | 0.40 ± 0.55 | 0.60 ± 0.55 |
| Input tokens | 140,384 ± 173,601 | 143,195 ± 57,685 | 46,560 ± 36,020 |
| Output tokens | 1,229 ± 637 | 3,743 ± 464 | 679 ± 400 |
| Cost per run (USD, billed where reported) | 0.01 ± 0.01 | 0.01 ± 0.01 | 0.00 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (10 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 4 | 2 | 4 |
| Detection correct | 0.75 ± 0.50 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 0.75 ± 0.50 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 0.94 ± 0.12 | 1.00 ± 0.00 | 1.00 ± 0.00 |

#### scenario redirect · mode det · reasoning on (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 5.60 ± 1.44 | 4.65 ± 1.23 | 2.80 ± 1.10 |
| Mean steps M1 | 5.00 ± 2.38 | 3.20 ± 1.48 | 2.20 ± 1.30 |
| Optimal action rate M0 | 0.66 ± 0.19 | 0.74 ± 0.18 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.67 ± 0.20 | 0.79 ± 0.22 | 1.00 ± 0.00 |
| Route regret M0 | 2.80 ± 1.41 | 1.85 ± 0.88 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.40 ± 0.55 | 0.40 ± 0.55 | 0.80 ± 0.45 |
| Detection correct | 0.20 ± 0.45 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Localization correct | 0.60 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Preservation accuracy | 0.80 ± 0.11 | 0.85 ± 0.14 | 1.00 ± 0.00 |
| Route probe optimal | 0.20 ± 0.45 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Input tokens | 92,420 ± 51,941 | 118,576 ± 42,949 | 33,894 ± 20,727 |
| Output tokens | 105,583 ± 100,409 | 73,182 ± 113,405 | 2,370 ± 1,522 |
| Cost per run (USD, billed where reported) | 0.11 ± 0.10 | 0.05 ± 0.07 | 0.00 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (8 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 2 | 2 | 4 |
| Detection correct | 0.50 ± 0.71 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 0.88 ± 0.18 | 1.00 ± 0.00 | 1.00 ± 0.00 |

#### scenario redirect · mode sto · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 0.95 ± 0.11 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 6.70 ± 1.80 | 6.82 ± 0.90 | 3.80 ± 1.44 |
| Mean steps M1 | 5.07 ± 3.44 | 6.10 ± 3.72 | 3.70 ± 3.16 |
| Optimal action rate M0 | 0.67 ± 0.15 | 0.61 ± 0.18 | 0.86 ± 0.19 |
| Optimal action rate M1 | 0.77 ± 0.14 | 0.69 ± 0.19 | 0.92 ± 0.17 |
| Route regret M0 | 3.33 ± 1.87 | 3.50 ± 0.96 | 0.29 ± 0.40 |
| Exposed (share of runs) | 0.80 ± 0.45 | 0.60 ± 0.55 | 0.80 ± 0.45 |
| Detection correct | 0.20 ± 0.45 | 0.80 ± 0.45 | 0.80 ± 0.45 |
| Localization correct | 1.00 ± 0.00 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Preservation accuracy | 0.85 ± 0.14 | 0.90 ± 0.14 | 0.95 ± 0.11 |
| Route probe optimal | 0.60 ± 0.55 | 0.40 ± 0.55 | 0.80 ± 0.45 |
| Input tokens | 182,491 ± 110,724 | 316,202 ± 134,320 | 82,424 ± 72,466 |
| Output tokens | 1,874 ± 772 | 5,683 ± 941 | 1,041 ± 380 |
| Cost per run (USD, billed where reported) | 0.01 ± 0.01 | 0.01 ± 0.00 | 0.00 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (11 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 4 | 3 | 4 |
| Detection correct | 0.25 ± 0.50 | 1.00 ± 0.00 | 0.75 ± 0.50 |
| Localization correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 0.88 ± 0.14 | 1.00 ± 0.00 | 0.94 ± 0.12 |

#### scenario silent_break · mode det · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 5.55 ± 1.01 | 4.70 ± 1.19 | 2.80 ± 1.10 |
| Mean steps M1 | 4.10 ± 0.95 | 4.00 ± 0.77 | 3.40 ± 0.55 |
| Optimal action rate M0 | 0.67 ± 0.13 | 0.76 ± 0.18 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.86 ± 0.16 | 0.86 ± 0.09 | 1.00 ± 0.00 |
| Route regret M0 | 2.75 ± 0.75 | 1.90 ± 1.13 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.60 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Detection correct | 0.60 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Localization correct | 0.60 ± 0.55 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Preservation accuracy | 0.90 ± 0.14 | 0.90 ± 0.14 | 1.00 ± 0.00 |
| Route probe optimal | 0.60 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Input tokens | 89,703 ± 29,392 | 152,494 ± 43,112 | 53,445 ± 20,122 |
| Output tokens | 1,220 ± 271 | 3,467 ± 485 | 879 ± 238 |
| Cost per run (USD, billed where reported) | 0.01 ± 0.00 | 0.01 ± 0.00 | 0.00 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (11 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 3 | 3 | 5 |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |

#### scenario silent_break · mode det · reasoning on (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 7.10 ± 3.50 | 4.65 ± 1.23 | 2.80 ± 1.10 |
| Mean steps M1 | 5.65 ± 3.36 | 4.00 ± 0.79 | 3.40 ± 0.55 |
| Optimal action rate M0 | 0.61 ± 0.09 | 0.74 ± 0.18 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.79 ± 0.22 | 0.86 ± 0.10 | 1.00 ± 0.00 |
| Route regret M0 | 4.30 ± 2.48 | 1.85 ± 0.88 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.40 ± 0.55 | 0.40 ± 0.55 | 0.80 ± 0.45 |
| Detection correct | 0.40 ± 0.55 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Localization correct | 0.60 ± 0.55 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Preservation accuracy | 0.85 ± 0.14 | 0.85 ± 0.14 | 1.00 ± 0.00 |
| Route probe optimal | 0.80 ± 0.45 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Input tokens | 138,074 ± 131,321 | 123,151 ± 38,584 | 44,092 ± 16,111 |
| Output tokens | 99,223 ± 115,334 | 8,373 ± 1,722 | 2,810 ± 1,008 |
| Cost per run (USD, billed where reported) | 0.09 ± 0.11 | 0.01 ± 0.00 | 0.00 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (8 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 2 | 2 | 4 |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |

#### scenario silent_break · mode sto · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 0.80 ± 0.45 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Mean steps M0 | 6.45 ± 1.41 | 6.75 ± 1.38 | 4.05 ± 1.77 |
| Mean steps M1 | 7.00 ± 4.31 | 5.19 ± 2.12 | 5.60 ± 2.70 |
| Optimal action rate M0 | 0.62 ± 0.21 | 0.65 ± 0.16 | 0.83 ± 0.18 |
| Optimal action rate M1 | 0.64 ± 0.19 | 0.71 ± 0.23 | 0.88 ± 0.20 |
| Route regret M0 | 3.04 ± 1.53 | 3.30 ± 1.57 | 0.50 ± 0.47 |
| Exposed (share of runs) | 0.60 ± 0.55 | 0.60 ± 0.55 | 0.80 ± 0.45 |
| Detection correct | 0.00 ± 0.00 | 0.20 ± 0.45 | 1.00 ± 0.00 |
| Localization correct | 0.60 ± 0.55 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Preservation accuracy | 0.75 ± 0.00 | 0.75 ± 0.18 | 1.00 ± 0.00 |
| Route probe optimal | 0.20 ± 0.45 | 0.40 ± 0.55 | 0.60 ± 0.55 |
| Input tokens | 253,534 ± 211,638 | 401,909 ± 341,040 | 125,058 ± 92,766 |
| Output tokens | 2,122 ± 860 | 5,689 ± 2,148 | 1,528 ± 835 |
| Cost per run (USD, billed where reported) | 0.01 ± 0.01 | 0.02 ± 0.03 | 0.00 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (10 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 3 | 3 | 4 |
| Detection correct | 0.00 ± 0.00 | 0.33 ± 0.58 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 0.67 ± 0.58 | 1.00 ± 0.00 |
| Preservation accuracy | 0.75 ± 0.00 | 0.83 ± 0.14 | 1.00 ± 0.00 |


## Part 2: 75 runs, stochastic, reasoning on (Efe)

#### scenario degradation (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 6.70 ± 1.59 | 6.20 ± 1.11 | 3.50 ± 1.27 |
| Mean steps M1 | 7.80 ± 4.50 | 6.65 ± 3.26 | 4.75 ± 1.75 |
| Optimal action rate M0 | 0.68 ± 0.18 | 0.61 ± 0.22 | 0.98 ± 0.04 |
| Optimal action rate M1 | 0.70 ± 0.08 | 0.59 ± 0.11 | 0.97 ± 0.04 |
| Route regret M0 | 3.01 ± 1.86 | 2.54 ± 1.17 | 0.03 ± 0.08 |
| Exposed (share of runs) | 0.60 ± 0.55 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Detection correct | 0.00 ± 0.00 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Localization correct | 0.40 ± 0.55 | 0.20 ± 0.45 | 1.00 ± 0.00 |
| Preservation accuracy | 0.80 ± 0.21 | 0.85 ± 0.14 | 1.00 ± 0.00 |
| Route probe optimal | 0.20 ± 0.45 | 0.00 ± 0.00 | 0.80 ± 0.45 |
| Input tokens | 157,906 ± 102,355 | 247,622 ± 106,169 | 71,934 ± 36,236 |
| Output tokens | 89,367 ± 87,583 | 59,543 ± 58,318 | 8,743 ± 3,983 |
| Cost per run (USD, billed where reported) | 0.07 ± 0.06 | 0.05 ± 0.04 | 0.01 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (10 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 3 | 2 | 5 |
| Detection correct | 0.00 ± 0.00 | 0.50 ± 0.71 | 1.00 ± 0.00 |
| Localization correct | 0.67 ± 0.58 | 0.50 ± 0.71 | 1.00 ± 0.00 |
| Preservation accuracy | 0.83 ± 0.29 | 1.00 ± 0.00 | 1.00 ± 0.00 |

#### scenario hard_removal (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 0.90 ± 0.22 | 0.95 ± 0.11 | 1.00 ± 0.00 |
| Mean steps M0 | 6.75 ± 1.61 | 6.60 ± 1.15 | 3.45 ± 1.33 |
| Mean steps M1 | 7.60 ± 5.39 | 5.95 ± 2.76 | 5.00 ± 1.99 |
| Optimal action rate M0 | 0.69 ± 0.17 | 0.65 ± 0.15 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.82 ± 0.17 | 0.82 ± 0.17 | 0.98 ± 0.05 |
| Route regret M0 | 3.22 ± 2.18 | 3.09 ± 0.81 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.60 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 0.80 ± 0.45 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Preservation accuracy | 0.95 ± 0.11 | 0.90 ± 0.14 | 1.00 ± 0.00 |
| Route probe optimal | 0.60 ± 0.55 | 0.40 ± 0.55 | 0.80 ± 0.45 |
| Input tokens | 165,397 ± 144,092 | 244,718 ± 122,430 | 74,286 ± 41,362 |
| Output tokens | 67,772 ± 83,300 | 21,532 ± 8,932 | 8,393 ± 4,878 |
| Cost per run (USD, billed where reported) | 0.05 ± 0.06 | 0.02 ± 0.01 | 0.01 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (11 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 3 | 3 | 5 |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 0.67 ± 0.58 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |

#### scenario irrelevant (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 0.95 ± 0.11 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 7.85 ± 3.45 | 6.10 ± 1.39 | 3.45 ± 1.33 |
| Mean steps M1 | 5.37 ± 2.11 | 5.65 ± 3.10 | 4.20 ± 2.06 |
| Optimal action rate M0 | 0.65 ± 0.14 | 0.70 ± 0.20 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.70 ± 0.11 | 0.72 ± 0.29 | 1.00 ± 0.00 |
| Route regret M0 | 4.20 ± 3.58 | 2.56 ± 1.91 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 |
| Detection correct | 0.00 ± 0.00 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Localization correct | 0.00 ± 0.00 | 0.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 0.70 ± 0.11 | 0.75 ± 0.00 | 1.00 ± 0.00 |
| Route probe optimal | 0.20 ± 0.45 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Input tokens | 151,293 ± 91,303 | 205,243 ± 79,372 | 65,752 ± 40,134 |
| Output tokens | 115,905 ± 89,423 | 21,965 ± 13,038 | 6,354 ± 3,159 |
| Cost per run (USD, billed where reported) | 0.10 ± 0.07 | 0.02 ± 0.01 | 0.01 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (0 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 0 | 0 | 0 |
| Detection correct | n/a | n/a | n/a |
| Localization correct | n/a | n/a | n/a |
| Preservation accuracy | n/a | n/a | n/a |

#### scenario redirect (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 0.95 ± 0.11 | 1.00 ± 0.00 |
| Mean steps M0 | 5.95 ± 1.27 | 5.70 ± 1.52 | 3.60 ± 1.51 |
| Mean steps M1 | 5.15 ± 2.95 | 4.75 ± 2.35 | 3.60 ± 2.95 |
| Optimal action rate M0 | 0.72 ± 0.17 | 0.75 ± 0.19 | 0.95 ± 0.11 |
| Optimal action rate M1 | 0.75 ± 0.23 | 0.76 ± 0.21 | 0.95 ± 0.10 |
| Route regret M0 | 2.42 ± 1.24 | 2.16 ± 1.19 | 0.12 ± 0.27 |
| Exposed (share of runs) | 0.80 ± 0.45 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Detection correct | 1.00 ± 0.00 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Localization correct | 0.80 ± 0.45 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Preservation accuracy | 0.90 ± 0.14 | 0.90 ± 0.14 | 1.00 ± 0.00 |
| Route probe optimal | 0.40 ± 0.55 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Input tokens | 98,648 ± 57,931 | 207,466 ± 124,086 | 62,688 ± 54,249 |
| Output tokens | 80,296 ± 67,601 | 19,005 ± 8,549 | 8,660 ± 9,381 |
| Cost per run (USD, billed where reported) | 0.07 ± 0.05 | 0.02 ± 0.01 | 0.01 ± 0.01 |

Values are mean ± standard deviation across runs. Exposed runs only (13 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 4 | 4 | 5 |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 0.94 ± 0.12 | 0.94 ± 0.12 | 1.00 ± 0.00 |

#### scenario silent_break (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 0.80 ± 0.45 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Mean steps M0 | 6.55 ± 1.08 | 6.75 ± 0.94 | 3.45 ± 1.33 |
| Mean steps M1 | 7.38 ± 2.43 | 5.50 ± 1.67 | 4.80 ± 1.63 |
| Optimal action rate M0 | 0.69 ± 0.15 | 0.61 ± 0.15 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.62 ± 0.32 | 0.66 ± 0.26 | 0.99 ± 0.02 |
| Route regret M0 | 2.65 ± 0.90 | 3.39 ± 1.21 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.60 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Detection correct | 0.40 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Localization correct | 0.60 ± 0.55 | 0.20 ± 0.45 | 1.00 ± 0.00 |
| Preservation accuracy | 0.90 ± 0.14 | 0.75 ± 0.18 | 1.00 ± 0.00 |
| Route probe optimal | 0.40 ± 0.55 | 0.20 ± 0.45 | 1.00 ± 0.00 |
| Input tokens | 202,271 ± 147,691 | 339,882 ± 261,629 | 71,303 ± 35,134 |
| Output tokens | 121,611 ± 60,099 | 49,867 ± 60,108 | 8,834 ± 7,910 |
| Cost per run (USD, billed where reported) | 0.09 ± 0.04 | 0.04 ± 0.04 | 0.01 ± 0.01 |

Values are mean ± standard deviation across runs. Exposed runs only (11 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 3 | 3 | 5 |
| Detection correct | 0.67 ± 0.58 | 0.67 ± 0.58 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 0.33 ± 0.58 | 1.00 ± 0.00 |
| Preservation accuracy | 1.00 ± 0.00 | 0.83 ± 0.14 | 1.00 ± 0.00 |


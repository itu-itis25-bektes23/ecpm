### scenario degradation · mode sto · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 5.55 ± 3.18 | 5.10 ± 3.37 | 3.70 ± 1.58 |
| Mean steps M1 | 6.30 ± 2.70 | 5.80 ± 2.68 | 5.00 ± 2.23 |
| Optimal action rate M0 | 0.75 ± 0.26 | 0.81 ± 0.18 | 0.92 ± 0.16 |
| Optimal action rate M1 | 0.65 ± 0.29 | 0.71 ± 0.26 | 0.87 ± 0.22 |
| Route regret M0 | 1.99 ± 1.85 | 1.72 ± 2.12 | 0.19 ± 0.34 |
| Exposed (share of runs) | 0.60 ± 0.55 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Detection correct | 0.60 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Localization correct | 0.60 ± 0.55 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Preservation accuracy | 0.95 ± 0.11 | 0.90 ± 0.22 | 1.00 ± 0.00 |
| Route probe optimal | 0.20 ± 0.45 | 0.40 ± 0.55 | 0.60 ± 0.55 |
| Input tokens | 237,815 ± 152,578 | 357,671 ± 259,207 | 154,402 ± 93,498 |
| Output tokens | 3,062 ± 1,348 | 6,088 ± 2,133 | 2,373 ± 867 |
| Cost per run (USD, billed where reported) | 0.03 ± 0.02 | 0.04 ± 0.03 | 0.02 ± 0.01 |

Values are mean ± standard deviation across runs. Exposed runs only (12 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 3 | 4 | 5 |
| Detection correct | 0.67 ± 0.58 | 0.50 ± 0.58 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |

### scenario degradation · mode sto · reasoning on (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 5.85 ± 2.45 | 5.40 ± 2.26 | 3.50 ± 1.33 |
| Mean steps M1 | 5.85 ± 1.70 | 5.20 ± 1.97 | 4.80 ± 1.92 |
| Optimal action rate M0 | 0.74 ± 0.24 | 0.80 ± 0.18 | 0.99 ± 0.02 |
| Optimal action rate M1 | 0.63 ± 0.22 | 0.69 ± 0.32 | 0.95 ± 0.09 |
| Route regret M0 | 2.50 ± 2.06 | 2.14 ± 1.41 | 0.03 ± 0.07 |
| Exposed (share of runs) | 0.40 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Detection correct | 0.80 ± 0.45 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Localization correct | 0.40 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Preservation accuracy | 0.85 ± 0.14 | 0.85 ± 0.14 | 1.00 ± 0.00 |
| Route probe optimal | 0.20 ± 0.45 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Input tokens | 210,575 ± 106,179 | 349,977 ± 151,111 | 143,055 ± 76,575 |
| Output tokens | 6,532 ± 1,625 | 10,096 ± 1,959 | 7,418 ± 4,109 |
| Cost per run (USD, billed where reported) | 0.02 ± 0.01 | 0.04 ± 0.02 | 0.02 ± 0.01 |

Values are mean ± standard deviation across runs. Exposed runs only (10 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 2 | 3 | 5 |
| Detection correct | 1.00 ± 0.00 | 0.33 ± 0.58 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 1.00 ± 0.00 | 0.92 ± 0.14 | 1.00 ± 0.00 |

### scenario hard_removal · mode det · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 3.60 ± 2.43 | 4.00 ± 2.26 | 2.80 ± 1.10 |
| Mean steps M1 | 3.80 ± 0.27 | 3.70 ± 0.45 | 3.40 ± 0.55 |
| Optimal action rate M0 | 0.97 ± 0.04 | 0.89 ± 0.17 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.92 ± 0.10 | 0.94 ± 0.11 | 1.00 ± 0.00 |
| Route regret M0 | 0.80 ± 1.52 | 1.20 ± 1.52 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.80 ± 0.45 | 0.60 ± 0.55 | 0.60 ± 0.55 |
| Detection correct | 0.80 ± 0.45 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Localization correct | 0.80 ± 0.45 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Preservation accuracy | 0.95 ± 0.11 | 0.95 ± 0.11 | 1.00 ± 0.00 |
| Route probe optimal | 0.80 ± 0.45 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Input tokens | 95,671 ± 62,106 | 192,561 ± 74,138 | 71,039 ± 27,449 |
| Output tokens | 1,723 ± 694 | 4,583 ± 642 | 990 ± 205 |
| Cost per run (USD, billed where reported) | 0.01 ± 0.01 | 0.02 ± 0.01 | 0.01 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (10 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 4 | 3 | 3 |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |

### scenario hard_removal · mode det · reasoning on (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 4.80 ± 0.82 | 4.90 ± 1.27 | 2.80 ± 1.10 |
| Mean steps M1 | 3.45 ± 0.62 | 3.60 ± 0.89 | 3.40 ± 0.55 |
| Optimal action rate M0 | 0.70 ± 0.16 | 0.82 ± 0.13 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.99 ± 0.02 | 0.99 ± 0.03 | 1.00 ± 0.00 |
| Route regret M0 | 2.00 ± 0.85 | 2.10 ± 0.34 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.20 ± 0.45 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Detection correct | 0.80 ± 0.45 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 0.80 ± 0.45 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 0.95 ± 0.11 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Route probe optimal | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Input tokens | 106,089 ± 22,514 | 228,247 ± 70,112 | 72,430 ± 29,134 |
| Output tokens | 3,767 ± 945 | 8,135 ± 2,273 | 2,074 ± 409 |
| Cost per run (USD, billed where reported) | 0.01 ± 0.00 | 0.03 ± 0.01 | 0.01 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (10 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 1 | 4 | 5 |
| Detection correct | 1.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 1.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 1.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |

### scenario hard_removal · mode sto · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 5.25 ± 3.36 | 4.43 ± 2.26 | 3.65 ± 1.51 |
| Mean steps M1 | 5.25 ± 2.01 | 5.30 ± 2.29 | 5.15 ± 1.95 |
| Optimal action rate M0 | 0.76 ± 0.24 | 0.84 ± 0.18 | 0.95 ± 0.08 |
| Optimal action rate M1 | 0.90 ± 0.09 | 0.91 ± 0.09 | 0.91 ± 0.09 |
| Route regret M0 | 1.82 ± 2.01 | 1.24 ± 1.54 | 0.14 ± 0.23 |
| Exposed (share of runs) | 0.80 ± 0.45 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Detection correct | 0.80 ± 0.45 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Localization correct | 0.80 ± 0.45 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 0.95 ± 0.11 | 0.90 ± 0.14 | 1.00 ± 0.00 |
| Route probe optimal | 0.60 ± 0.55 | 0.80 ± 0.45 | 0.40 ± 0.55 |
| Input tokens | 255,892 ± 194,126 | 377,177 ± 239,684 | 152,009 ± 86,631 |
| Output tokens | 3,284 ± 1,607 | 6,882 ± 2,138 | 2,225 ± 745 |
| Cost per run (USD, billed where reported) | 0.03 ± 0.02 | 0.04 ± 0.03 | 0.02 ± 0.01 |

Values are mean ± standard deviation across runs. Exposed runs only (12 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 4 | 3 | 5 |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |

### scenario hard_removal · mode sto · reasoning on (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 5.15 ± 3.03 | 5.92 ± 1.90 | 3.50 ± 1.27 |
| Mean steps M1 | 5.40 ± 2.14 | 5.30 ± 2.58 | 4.75 ± 1.55 |
| Optimal action rate M0 | 0.78 ± 0.29 | 0.74 ± 0.13 | 0.97 ± 0.04 |
| Optimal action rate M1 | 0.85 ± 0.10 | 0.90 ± 0.14 | 0.98 ± 0.05 |
| Route regret M0 | 1.68 ± 2.03 | 2.71 ± 1.00 | 0.06 ± 0.09 |
| Exposed (share of runs) | 0.80 ± 0.45 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Detection correct | 1.00 ± 0.00 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Preservation accuracy | 1.00 ± 0.00 | 0.95 ± 0.11 | 1.00 ± 0.00 |
| Route probe optimal | 0.40 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Input tokens | 192,639 ± 156,601 | 401,248 ± 199,339 | 132,195 ± 69,982 |
| Output tokens | 4,822 ± 2,726 | 11,609 ± 2,713 | 4,993 ± 2,129 |
| Cost per run (USD, billed where reported) | 0.02 ± 0.02 | 0.05 ± 0.02 | 0.02 ± 0.01 |

Values are mean ± standard deviation across runs. Exposed runs only (12 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 4 | 3 | 5 |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |

### scenario irrelevant · mode det · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 3.70 ± 2.33 | 3.70 ± 2.33 | 3.00 ± 1.00 |
| Mean steps M1 | 2.80 ± 1.10 | 2.80 ± 1.10 | 3.00 ± 1.00 |
| Optimal action rate M0 | 0.96 ± 0.06 | 0.96 ± 0.06 | 0.93 ± 0.15 |
| Optimal action rate M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 0.93 ± 0.15 |
| Route regret M0 | 0.90 ± 1.23 | 0.90 ± 1.23 | 0.20 ± 0.45 |
| Exposed (share of runs) | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 |
| Detection correct | 0.00 ± 0.00 | 0.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 0.00 ± 0.00 | 0.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 0.75 ± 0.00 | 0.75 ± 0.00 | 1.00 ± 0.00 |
| Route probe optimal | 1.00 ± 0.00 | 1.00 ± 0.00 | 0.80 ± 0.45 |
| Input tokens | 83,719 ± 68,938 | 166,288 ± 106,728 | 69,950 ± 33,914 |
| Output tokens | 1,467 ± 794 | 4,095 ± 1,192 | 1,032 ± 352 |
| Cost per run (USD, billed where reported) | 0.01 ± 0.01 | 0.02 ± 0.01 | 0.01 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (0 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 0 | 0 | 0 |
| Detection correct | n/a | n/a | n/a |
| Localization correct | n/a | n/a | n/a |
| Preservation accuracy | n/a | n/a | n/a |

### scenario irrelevant · mode det · reasoning on (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 5.15 ± 1.14 | 4.15 ± 1.64 | 2.80 ± 1.10 |
| Mean steps M1 | 3.20 ± 1.10 | 3.30 ± 1.48 | 2.80 ± 1.10 |
| Optimal action rate M0 | 0.79 ± 0.19 | 0.84 ± 0.16 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.90 ± 0.22 | 0.88 ± 0.16 | 1.00 ± 0.00 |
| Route regret M0 | 2.35 ± 1.02 | 1.35 ± 1.08 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.00 ± 0.00 | 0.20 ± 0.45 | 0.00 ± 0.00 |
| Detection correct | 0.00 ± 0.00 | 0.20 ± 0.45 | 1.00 ± 0.00 |
| Localization correct | 0.00 ± 0.00 | 0.20 ± 0.45 | 1.00 ± 0.00 |
| Preservation accuracy | 0.75 ± 0.00 | 0.80 ± 0.11 | 1.00 ± 0.00 |
| Route probe optimal | 0.80 ± 0.45 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Input tokens | 113,175 ± 46,172 | 190,549 ± 89,040 | 62,251 ± 34,086 |
| Output tokens | 4,153 ± 978 | 5,978 ± 1,327 | 1,637 ± 335 |
| Cost per run (USD, billed where reported) | 0.01 ± 0.01 | 0.02 ± 0.01 | 0.01 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (1 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 0 | 1 | 0 |
| Detection correct | n/a | 1.00 | n/a |
| Localization correct | n/a | 1.00 | n/a |
| Preservation accuracy | n/a | 1.00 | n/a |

### scenario irrelevant · mode sto · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 0.95 ± 0.11 | 1.00 ± 0.00 |
| Mean steps M0 | 5.55 ± 3.47 | 5.10 ± 1.49 | 3.55 ± 1.35 |
| Mean steps M1 | 4.85 ± 2.47 | 4.22 ± 1.87 | 4.35 ± 2.09 |
| Optimal action rate M0 | 0.77 ± 0.28 | 0.81 ± 0.16 | 0.98 ± 0.05 |
| Optimal action rate M1 | 0.84 ± 0.24 | 0.85 ± 0.18 | 0.93 ± 0.12 |
| Route regret M0 | 2.02 ± 2.49 | 1.78 ± 1.04 | 0.06 ± 0.14 |
| Exposed (share of runs) | 0.20 ± 0.45 | 0.00 ± 0.00 | 0.00 ± 0.00 |
| Detection correct | 0.20 ± 0.45 | 0.20 ± 0.45 | 1.00 ± 0.00 |
| Localization correct | 0.20 ± 0.45 | 0.20 ± 0.45 | 1.00 ± 0.00 |
| Preservation accuracy | 0.75 ± 0.00 | 0.80 ± 0.11 | 1.00 ± 0.00 |
| Route probe optimal | 0.60 ± 0.55 | 0.60 ± 0.55 | 0.60 ± 0.55 |
| Input tokens | 237,266 ± 247,576 | 311,383 ± 201,674 | 131,536 ± 79,087 |
| Output tokens | 2,934 ± 2,045 | 6,241 ± 1,706 | 2,145 ± 899 |
| Cost per run (USD, billed where reported) | 0.03 ± 0.03 | 0.03 ± 0.02 | 0.01 ± 0.01 |

Values are mean ± standard deviation across runs. Exposed runs only (1 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 1 | 0 | 0 |
| Detection correct | 1.00 | n/a | n/a |
| Localization correct | 1.00 | n/a | n/a |
| Preservation accuracy | 0.75 | n/a | n/a |

### scenario irrelevant · mode sto · reasoning on (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 5.95 ± 1.11 | 5.50 ± 0.88 | 3.45 ± 1.33 |
| Mean steps M1 | 5.85 ± 1.88 | 5.20 ± 2.34 | 4.20 ± 2.06 |
| Optimal action rate M0 | 0.63 ± 0.20 | 0.71 ± 0.25 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.64 ± 0.24 | 0.77 ± 0.29 | 0.99 ± 0.01 |
| Route regret M0 | 2.61 ± 1.99 | 2.14 ± 1.46 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 |
| Detection correct | 0.60 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Localization correct | 0.20 ± 0.45 | 0.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 0.80 ± 0.11 | 0.70 ± 0.11 | 1.00 ± 0.00 |
| Route probe optimal | 0.20 ± 0.45 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Input tokens | 234,160 ± 101,211 | 343,867 ± 129,343 | 120,489 ± 75,696 |
| Output tokens | 6,738 ± 3,007 | 9,586 ± 1,675 | 4,687 ± 2,395 |
| Cost per run (USD, billed where reported) | 0.03 ± 0.01 | 0.04 ± 0.01 | 0.01 ± 0.01 |

Values are mean ± standard deviation across runs. Exposed runs only (0 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 0 | 0 | 0 |
| Detection correct | n/a | n/a | n/a |
| Localization correct | n/a | n/a | n/a |
| Preservation accuracy | n/a | n/a | n/a |

### scenario no_change · mode det · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 4.85 ± 1.52 | 4.65 ± 0.95 | 2.80 ± 1.10 |
| Mean steps M1 | 3.80 ± 0.84 | 3.20 ± 1.30 | 2.80 ± 1.10 |
| Optimal action rate M0 | 0.69 ± 0.18 | 0.79 ± 0.12 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.73 ± 0.19 | 0.89 ± 0.15 | 1.00 ± 0.00 |
| Route regret M0 | 2.05 ± 1.10 | 1.85 ± 0.38 | 0.00 ± 0.00 |
| Exposed (share of runs) | n/a | n/a | n/a |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | n/a | n/a | n/a |
| Preservation accuracy | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Route probe optimal | 0.20 ± 0.45 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Input tokens | 120,678 ± 62,179 | 178,989 ± 63,756 | 60,122 ± 35,505 |
| Output tokens | 2,061 ± 598 | 4,052 ± 641 | 907 ± 361 |
| Cost per run (USD, billed where reported) | 0.01 ± 0.01 | 0.02 ± 0.01 | 0.01 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (0 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 0 | 0 | 0 |
| Detection correct | n/a | n/a | n/a |
| Localization correct | n/a | n/a | n/a |
| Preservation accuracy | n/a | n/a | n/a |

### scenario no_change · mode det · reasoning on (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 4.65 ± 1.53 | 4.30 ± 1.24 | 2.80 ± 1.10 |
| Mean steps M1 | 3.50 ± 1.12 | 3.20 ± 0.84 | 2.80 ± 1.10 |
| Optimal action rate M0 | 0.76 ± 0.13 | 0.80 ± 0.16 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.81 ± 0.18 | 0.87 ± 0.18 | 1.00 ± 0.00 |
| Route regret M0 | 1.85 ± 0.58 | 1.50 ± 0.77 | 0.00 ± 0.00 |
| Exposed (share of runs) | n/a | n/a | n/a |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | n/a | n/a | n/a |
| Preservation accuracy | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Route probe optimal | 0.40 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Input tokens | 99,808 ± 48,849 | 176,653 ± 55,445 | 59,272 ± 33,745 |
| Output tokens | 3,242 ± 504 | 5,649 ± 947 | 1,400 ± 297 |
| Cost per run (USD, billed where reported) | 0.01 ± 0.01 | 0.02 ± 0.01 | 0.01 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (0 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 0 | 0 | 0 |
| Detection correct | n/a | n/a | n/a |
| Localization correct | n/a | n/a | n/a |
| Preservation accuracy | n/a | n/a | n/a |

### scenario no_change · mode sto · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 5.00 ± 1.94 | 5.70 ± 2.46 | 3.65 ± 1.51 |
| Mean steps M1 | 5.20 ± 2.46 | 4.70 ± 1.99 | 4.60 ± 2.52 |
| Optimal action rate M0 | 0.70 ± 0.21 | 0.72 ± 0.21 | 0.95 ± 0.08 |
| Optimal action rate M1 | 0.71 ± 0.23 | 0.76 ± 0.24 | 0.90 ± 0.14 |
| Route regret M0 | 1.80 ± 1.43 | 2.46 ± 1.68 | 0.14 ± 0.23 |
| Exposed (share of runs) | n/a | n/a | n/a |
| Detection correct | 0.80 ± 0.45 | 0.80 ± 0.45 | 0.80 ± 0.45 |
| Localization correct | n/a | n/a | n/a |
| Preservation accuracy | 0.95 ± 0.11 | 0.95 ± 0.11 | 0.95 ± 0.11 |
| Route probe optimal | 0.20 ± 0.45 | 0.40 ± 0.55 | 0.60 ± 0.55 |
| Input tokens | 165,774 ± 97,566 | 318,840 ± 169,694 | 133,499 ± 92,442 |
| Output tokens | 2,307 ± 1,035 | 6,310 ± 1,587 | 2,038 ± 878 |
| Cost per run (USD, billed where reported) | 0.02 ± 0.01 | 0.04 ± 0.02 | 0.01 ± 0.01 |

Values are mean ± standard deviation across runs. Exposed runs only (0 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 0 | 0 | 0 |
| Detection correct | n/a | n/a | n/a |
| Localization correct | n/a | n/a | n/a |
| Preservation accuracy | n/a | n/a | n/a |

### scenario no_change · mode sto · reasoning on (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 5.45 ± 2.35 | 4.40 ± 1.33 | 3.50 ± 1.33 |
| Mean steps M1 | 4.55 ± 2.00 | 4.60 ± 1.79 | 4.35 ± 2.09 |
| Optimal action rate M0 | 0.82 ± 0.18 | 0.79 ± 0.18 | 0.99 ± 0.02 |
| Optimal action rate M1 | 0.86 ± 0.24 | 0.82 ± 0.17 | 0.95 ± 0.08 |
| Route regret M0 | 2.10 ± 1.42 | 0.96 ± 1.27 | 0.03 ± 0.07 |
| Exposed (share of runs) | n/a | n/a | n/a |
| Detection correct | 0.60 ± 0.55 | 1.00 ± 0.00 | 0.80 ± 0.45 |
| Localization correct | n/a | n/a | n/a |
| Preservation accuracy | 0.95 ± 0.11 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Route probe optimal | 0.60 ± 0.55 | 0.40 ± 0.55 | 0.80 ± 0.45 |
| Input tokens | 159,510 ± 97,773 | 294,121 ± 154,420 | 119,442 ± 75,324 |
| Output tokens | 4,645 ± 2,466 | 8,986 ± 3,194 | 5,169 ± 3,111 |
| Cost per run (USD, billed where reported) | 0.02 ± 0.01 | 0.03 ± 0.02 | 0.01 ± 0.01 |

Values are mean ± standard deviation across runs. Exposed runs only (0 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 0 | 0 | 0 |
| Detection correct | n/a | n/a | n/a |
| Localization correct | n/a | n/a | n/a |
| Preservation accuracy | n/a | n/a | n/a |

### scenario redirect · mode det · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 4.50 ± 3.17 | 4.30 ± 1.44 | 2.80 ± 1.10 |
| Mean steps M1 | 3.35 ± 1.73 | 3.20 ± 1.30 | 2.20 ± 1.30 |
| Optimal action rate M0 | 0.85 ± 0.19 | 0.84 ± 0.20 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.84 ± 0.15 | 0.85 ± 0.22 | 1.00 ± 0.00 |
| Route regret M0 | 1.70 ± 2.45 | 1.50 ± 1.17 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.80 ± 0.45 | 0.60 ± 0.55 | 0.60 ± 0.55 |
| Detection correct | 0.80 ± 0.45 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Preservation accuracy | 0.95 ± 0.11 | 0.90 ± 0.14 | 1.00 ± 0.00 |
| Route probe optimal | 0.40 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Input tokens | 119,225 ± 121,145 | 183,536 ± 53,104 | 55,825 ± 35,551 |
| Output tokens | 1,836 ± 1,041 | 4,463 ± 343 | 926 ± 349 |
| Cost per run (USD, billed where reported) | 0.01 ± 0.01 | 0.02 ± 0.01 | 0.01 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (10 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 4 | 3 | 3 |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |

### scenario redirect · mode det · reasoning on (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 5.00 ± 0.73 | 5.00 ± 1.21 | 2.80 ± 1.10 |
| Mean steps M1 | 3.65 ± 1.80 | 3.10 ± 1.28 | 2.20 ± 1.30 |
| Optimal action rate M0 | 0.74 ± 0.18 | 0.80 ± 0.17 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.77 ± 0.20 | 0.83 ± 0.22 | 1.00 ± 0.00 |
| Route regret M0 | 2.20 ± 0.99 | 2.20 ± 0.41 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.80 ± 0.45 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Detection correct | 0.80 ± 0.45 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Preservation accuracy | 0.95 ± 0.11 | 0.95 ± 0.11 | 1.00 ± 0.00 |
| Route probe optimal | 0.40 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Input tokens | 119,031 ± 53,751 | 208,773 ± 65,067 | 54,440 ± 35,440 |
| Output tokens | 4,332 ± 1,166 | 7,867 ± 1,835 | 1,498 ± 628 |
| Cost per run (USD, billed where reported) | 0.01 ± 0.01 | 0.02 ± 0.01 | 0.01 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (13 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 4 | 4 | 5 |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |

### scenario redirect · mode sto · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 4.22 ± 2.25 | 4.80 ± 2.55 | 3.55 ± 1.35 |
| Mean steps M1 | 4.00 ± 2.81 | 4.30 ± 2.10 | 3.45 ± 2.64 |
| Optimal action rate M0 | 0.86 ± 0.17 | 0.84 ± 0.22 | 0.98 ± 0.05 |
| Optimal action rate M1 | 0.89 ± 0.15 | 0.85 ± 0.23 | 0.98 ± 0.03 |
| Route regret M0 | 0.81 ± 1.15 | 1.47 ± 1.77 | 0.06 ± 0.14 |
| Exposed (share of runs) | 1.00 ± 0.00 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Detection correct | 1.00 ± 0.00 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Preservation accuracy | 0.95 ± 0.11 | 0.95 ± 0.11 | 1.00 ± 0.00 |
| Route probe optimal | 0.40 ± 0.55 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Input tokens | 167,974 ± 205,602 | 275,842 ± 177,664 | 112,828 ± 90,259 |
| Output tokens | 2,478 ± 1,717 | 5,837 ± 1,875 | 1,898 ± 911 |
| Cost per run (USD, billed where reported) | 0.02 ± 0.02 | 0.03 ± 0.02 | 0.01 ± 0.01 |

Values are mean ± standard deviation across runs. Exposed runs only (13 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 5 | 3 | 5 |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 0.95 ± 0.11 | 1.00 ± 0.00 | 1.00 ± 0.00 |

### scenario redirect · mode sto · reasoning on (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 5.60 ± 1.81 | 4.85 ± 2.05 | 3.45 ± 1.33 |
| Mean steps M1 | 4.90 ± 1.63 | 4.35 ± 1.98 | 3.30 ± 2.34 |
| Optimal action rate M0 | 0.72 ± 0.21 | 0.81 ± 0.20 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.77 ± 0.27 | 0.84 ± 0.24 | 1.00 ± 0.01 |
| Route regret M0 | 2.43 ± 1.31 | 1.39 ± 1.65 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.40 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Detection correct | 0.60 ± 0.55 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Localization correct | 0.40 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Preservation accuracy | 0.85 ± 0.14 | 0.90 ± 0.14 | 1.00 ± 0.00 |
| Route probe optimal | 0.60 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Input tokens | 174,873 ± 100,315 | 322,164 ± 182,286 | 99,288 ± 75,974 |
| Output tokens | 5,554 ± 3,160 | 9,514 ± 3,532 | 3,598 ± 2,298 |
| Cost per run (USD, billed where reported) | 0.02 ± 0.01 | 0.04 ± 0.02 | 0.01 ± 0.01 |

Values are mean ± standard deviation across runs. Exposed runs only (10 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 2 | 3 | 5 |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |

### scenario silent_break · mode det · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 4.35 ± 1.55 | 3.55 ± 1.82 | 3.00 ± 1.00 |
| Mean steps M1 | 4.80 ± 1.34 | 4.45 ± 0.62 | 3.40 ± 0.55 |
| Optimal action rate M0 | 0.83 ± 0.14 | 0.91 ± 0.14 | 0.93 ± 0.15 |
| Optimal action rate M1 | 0.78 ± 0.17 | 0.81 ± 0.18 | 1.00 ± 0.00 |
| Route regret M0 | 1.55 ± 1.02 | 0.75 ± 0.94 | 0.20 ± 0.45 |
| Exposed (share of runs) | 0.60 ± 0.55 | 0.80 ± 0.45 | 0.40 ± 0.55 |
| Detection correct | 0.60 ± 0.55 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Localization correct | 0.80 ± 0.45 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Preservation accuracy | 0.90 ± 0.14 | 0.95 ± 0.11 | 1.00 ± 0.00 |
| Route probe optimal | 0.40 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Input tokens | 142,322 ± 54,254 | 199,636 ± 57,981 | 74,808 ± 24,905 |
| Output tokens | 2,461 ± 644 | 4,503 ± 680 | 1,086 ± 170 |
| Cost per run (USD, billed where reported) | 0.02 ± 0.01 | 0.02 ± 0.01 | 0.01 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (9 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 3 | 4 | 2 |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |

### scenario silent_break · mode det · reasoning on (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 4.65 ± 1.76 | 4.90 ± 1.38 | 2.80 ± 1.10 |
| Mean steps M1 | 3.75 ± 0.50 | 4.20 ± 1.49 | 3.40 ± 0.55 |
| Optimal action rate M0 | 0.84 ± 0.15 | 0.80 ± 0.12 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.94 ± 0.06 | 0.88 ± 0.11 | 1.00 ± 0.00 |
| Route regret M0 | 1.85 ± 1.04 | 2.10 ± 0.38 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.60 ± 0.55 | 0.80 ± 0.45 | 0.80 ± 0.45 |
| Detection correct | 0.60 ± 0.55 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Localization correct | 0.60 ± 0.55 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Preservation accuracy | 0.90 ± 0.14 | 0.95 ± 0.11 | 1.00 ± 0.00 |
| Route probe optimal | 1.00 ± 0.00 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Input tokens | 112,614 ± 40,417 | 249,631 ± 105,635 | 72,300 ± 28,401 |
| Output tokens | 4,458 ± 1,024 | 7,445 ± 1,928 | 2,061 ± 424 |
| Cost per run (USD, billed where reported) | 0.01 ± 0.00 | 0.03 ± 0.01 | 0.01 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (11 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 3 | 4 | 4 |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |

### scenario silent_break · mode sto · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 0.75 ± 0.43 | 0.90 ± 0.14 | 1.00 ± 0.00 |
| Mean steps M0 | 5.40 ± 3.39 | 4.60 ± 2.47 | 3.65 ± 1.51 |
| Mean steps M1 | 5.67 ± 2.31 | 7.38 ± 3.43 | 5.15 ± 1.95 |
| Optimal action rate M0 | 0.80 ± 0.25 | 0.84 ± 0.20 | 0.95 ± 0.08 |
| Optimal action rate M1 | 0.55 ± 0.25 | 0.62 ± 0.15 | 0.93 ± 0.10 |
| Route regret M0 | 1.93 ± 2.40 | 1.39 ± 1.42 | 0.14 ± 0.23 |
| Exposed (share of runs) | 0.80 ± 0.45 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Detection correct | 0.80 ± 0.45 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Localization correct | 0.80 ± 0.45 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Preservation accuracy | 0.90 ± 0.14 | 0.90 ± 0.14 | 1.00 ± 0.00 |
| Route probe optimal | 0.20 ± 0.45 | 0.20 ± 0.45 | 0.60 ± 0.55 |
| Input tokens | 446,059 ± 566,306 | 482,416 ± 359,043 | 151,109 ± 88,681 |
| Output tokens | 4,245 ± 2,742 | 7,449 ± 2,310 | 2,156 ± 752 |
| Cost per run (USD, billed where reported) | 0.05 ± 0.06 | 0.05 ± 0.04 | 0.02 ± 0.01 |

Values are mean ± standard deviation across runs. Exposed runs only (13 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 4 | 4 | 5 |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 0.94 ± 0.12 | 0.94 ± 0.12 | 1.00 ± 0.00 |

### scenario silent_break · mode sto · reasoning on (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 0.85 ± 0.34 | 1.00 ± 0.00 |
| Mean steps M0 | 5.10 ± 1.86 | 5.23 ± 1.49 | 3.45 ± 1.33 |
| Mean steps M1 | 6.05 ± 1.15 | 6.85 ± 0.98 | 4.80 ± 1.63 |
| Optimal action rate M0 | 0.73 ± 0.25 | 0.70 ± 0.21 | 0.99 ± 0.03 |
| Optimal action rate M1 | 0.79 ± 0.13 | 0.60 ± 0.15 | 1.00 ± 0.01 |
| Route regret M0 | 1.85 ± 2.07 | 1.88 ± 1.47 | 0.03 ± 0.07 |
| Exposed (share of runs) | 0.40 ± 0.55 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Detection correct | 0.60 ± 0.55 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Localization correct | 0.40 ± 0.55 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Preservation accuracy | 0.80 ± 0.21 | 0.95 ± 0.11 | 1.00 ± 0.00 |
| Route probe optimal | 0.40 ± 0.55 | 0.20 ± 0.45 | 1.00 ± 0.00 |
| Input tokens | 216,674 ± 89,879 | 590,779 ± 357,470 | 133,900 ± 72,580 |
| Output tokens | 7,095 ± 2,358 | 13,790 ± 4,754 | 5,433 ± 2,463 |
| Cost per run (USD, billed where reported) | 0.03 ± 0.01 | 0.07 ± 0.04 | 0.02 ± 0.01 |

Values are mean ± standard deviation across runs. Exposed runs only (11 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 2 | 4 | 5 |
| Detection correct | 1.00 ± 0.00 | 0.75 ± 0.50 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |


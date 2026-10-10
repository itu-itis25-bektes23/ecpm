### scenario degradation · mode sto · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 6.50 ± 1.36 | 6.35 ± 1.85 | 3.75 ± 1.25 |
| Mean steps M1 | 5.25 ± 2.22 | 6.20 ± 2.81 | 5.05 ± 1.77 |
| Optimal action rate M0 | 0.61 ± 0.12 | 0.79 ± 0.12 | 0.84 ± 0.15 |
| Optimal action rate M1 | 0.75 ± 0.17 | 0.73 ± 0.10 | 0.86 ± 0.17 |
| Route regret M0 | 2.80 ± 0.57 | 2.77 ± 1.45 | 0.33 ± 0.33 |
| Exposed (share of runs) | 0.00 ± 0.00 | 0.80 ± 0.45 | 0.60 ± 0.55 |
| Detection correct | 0.40 ± 0.55 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Localization correct | 0.20 ± 0.45 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Preservation accuracy | 0.80 ± 0.11 | 0.90 ± 0.14 | 1.00 ± 0.00 |
| Route probe optimal | 0.20 ± 0.45 | 0.20 ± 0.45 | 0.60 ± 0.55 |
| Input tokens | 111,318 ± 56,055 | 224,176 ± 111,771 | 89,146 ± 44,326 |
| Output tokens | 631 ± 161 | 2,861 ± 485 | 807 ± 289 |
| Cost per run (USD, billed where reported) | 0.05 ± 0.01 | 0.10 ± 0.03 | 0.04 ± 0.01 |

Values are mean ± standard deviation across runs. Exposed runs only (7 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 0 | 4 | 3 |
| Detection correct | n/a | 0.50 ± 0.58 | 1.00 ± 0.00 |
| Localization correct | n/a | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | n/a | 0.94 ± 0.12 | 1.00 ± 0.00 |

### scenario degradation · mode sto · reasoning on (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 6.05 ± 1.42 | 6.10 ± 1.62 | 3.45 ± 1.33 |
| Mean steps M1 | 5.85 ± 3.04 | 5.85 ± 3.29 | 4.65 ± 1.83 |
| Optimal action rate M0 | 0.71 ± 0.13 | 0.70 ± 0.15 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.75 ± 0.18 | 0.76 ± 0.17 | 1.00 ± 0.00 |
| Route regret M0 | 2.45 ± 1.10 | 2.41 ± 1.25 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.40 ± 0.55 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Detection correct | 0.40 ± 0.55 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Localization correct | 0.40 ± 0.55 | 0.20 ± 0.45 | 1.00 ± 0.00 |
| Preservation accuracy | 0.85 ± 0.14 | 0.75 ± 0.00 | 1.00 ± 0.00 |
| Route probe optimal | 0.20 ± 0.45 | 0.20 ± 0.45 | 1.00 ± 0.00 |
| Input tokens | 115,288 ± 68,311 | 200,749 ± 120,788 | 73,317 ± 39,094 |
| Output tokens | 3,230 ± 1,693 | 5,064 ± 2,197 | 3,803 ± 2,039 |
| Cost per run (USD, billed where reported) | 0.07 ± 0.03 | 0.12 ± 0.05 | 0.07 ± 0.03 |

Values are mean ± standard deviation across runs. Exposed runs only (9 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 2 | 2 | 5 |
| Detection correct | 1.00 ± 0.00 | 0.50 ± 0.71 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 0.50 ± 0.71 | 1.00 ± 0.00 |
| Preservation accuracy | 1.00 ± 0.00 | 0.75 ± 0.00 | 1.00 ± 0.00 |

### scenario hard_removal · mode det · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 5.15 ± 1.88 | 4.65 ± 1.63 | 2.80 ± 1.10 |
| Mean steps M1 | 3.60 ± 0.55 | 3.55 ± 0.80 | 3.40 ± 0.55 |
| Optimal action rate M0 | 0.71 ± 0.15 | 0.78 ± 0.14 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.95 ± 0.11 | 0.99 ± 0.02 | 1.00 ± 0.00 |
| Route regret M0 | 2.35 ± 1.13 | 1.85 ± 1.07 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.20 ± 0.45 | 0.80 ± 0.45 | 0.80 ± 0.45 |
| Detection correct | 0.00 ± 0.00 | 0.40 ± 0.55 | 0.60 ± 0.55 |
| Localization correct | 0.80 ± 0.45 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 0.95 ± 0.11 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Route probe optimal | 0.80 ± 0.45 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Input tokens | 67,683 ± 31,690 | 116,001 ± 42,360 | 47,440 ± 17,061 |
| Output tokens | 537 ± 181 | 2,165 ± 338 | 467 ± 70 |
| Cost per run (USD, billed where reported) | 0.04 ± 0.01 | 0.07 ± 0.01 | 0.03 ± 0.00 |

Values are mean ± standard deviation across runs. Exposed runs only (9 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 1 | 4 | 4 |
| Detection correct | 0.00 | 0.50 ± 0.58 | 0.75 ± 0.50 |
| Localization correct | 1.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 1.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |

### scenario hard_removal · mode det · reasoning on (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 4.65 ± 1.08 | 4.70 ± 1.88 | 2.80 ± 1.10 |
| Mean steps M1 | 3.80 ± 1.16 | 3.70 ± 0.74 | 3.40 ± 0.55 |
| Optimal action rate M0 | 0.74 ± 0.14 | 0.80 ± 0.12 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.97 ± 0.04 | 0.94 ± 0.09 | 1.00 ± 0.00 |
| Route regret M0 | 1.85 ± 0.42 | 1.90 ± 1.28 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.40 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Detection correct | 1.00 ± 0.00 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Preservation accuracy | 1.00 ± 0.00 | 0.95 ± 0.11 | 1.00 ± 0.00 |
| Route probe optimal | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Input tokens | 61,979 ± 26,786 | 110,602 ± 35,522 | 45,952 ± 17,255 |
| Output tokens | 1,813 ± 977 | 3,242 ± 643 | 769 ± 239 |
| Cost per run (USD, billed where reported) | 0.05 ± 0.02 | 0.08 ± 0.02 | 0.03 ± 0.01 |

Values are mean ± standard deviation across runs. Exposed runs only (10 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 2 | 3 | 5 |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |

### scenario hard_removal · mode sto · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 6.30 ± 1.29 | 6.20 ± 1.54 | 3.50 ± 1.33 |
| Mean steps M1 | 5.90 ± 2.55 | 5.25 ± 2.34 | 5.05 ± 1.77 |
| Optimal action rate M0 | 0.61 ± 0.10 | 0.75 ± 0.13 | 0.99 ± 0.02 |
| Optimal action rate M1 | 0.88 ± 0.15 | 0.90 ± 0.14 | 0.90 ± 0.11 |
| Route regret M0 | 2.65 ± 1.17 | 2.57 ± 1.15 | 0.03 ± 0.07 |
| Exposed (share of runs) | 0.20 ± 0.45 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 0.80 ± 0.45 |
| Localization correct | 1.00 ± 0.00 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Preservation accuracy | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Route probe optimal | 0.80 ± 0.45 | 0.80 ± 0.45 | 0.40 ± 0.55 |
| Input tokens | 117,556 ± 54,100 | 191,228 ± 94,829 | 83,333 ± 43,438 |
| Output tokens | 636 ± 157 | 2,721 ± 675 | 660 ± 268 |
| Cost per run (USD, billed where reported) | 0.05 ± 0.01 | 0.09 ± 0.03 | 0.04 ± 0.01 |

Values are mean ± standard deviation across runs. Exposed runs only (9 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 1 | 3 | 5 |
| Detection correct | 1.00 | 1.00 ± 0.00 | 0.80 ± 0.45 |
| Localization correct | 1.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 1.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |

### scenario hard_removal · mode sto · reasoning on (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 6.40 ± 1.26 | 6.70 ± 0.96 | 3.45 ± 1.33 |
| Mean steps M1 | 5.05 ± 2.09 | 5.65 ± 2.63 | 4.80 ± 1.63 |
| Optimal action rate M0 | 0.68 ± 0.08 | 0.67 ± 0.15 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.94 ± 0.09 | 0.94 ± 0.06 | 1.00 ± 0.01 |
| Route regret M0 | 2.79 ± 0.54 | 3.21 ± 1.50 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.40 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 1.00 ± 0.00 | 0.95 ± 0.11 | 1.00 ± 0.00 |
| Route probe optimal | 0.80 ± 0.45 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Input tokens | 104,857 ± 51,944 | 202,074 ± 72,837 | 73,893 ± 37,722 |
| Output tokens | 2,579 ± 1,606 | 5,072 ± 1,411 | 2,834 ± 1,326 |
| Cost per run (USD, billed where reported) | 0.07 ± 0.03 | 0.12 ± 0.03 | 0.06 ± 0.02 |

Values are mean ± standard deviation across runs. Exposed runs only (10 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 2 | 3 | 5 |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 1.00 ± 0.00 | 0.92 ± 0.14 | 1.00 ± 0.00 |

### scenario irrelevant · mode det · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 5.00 ± 1.45 | 4.70 ± 1.59 | 2.80 ± 1.10 |
| Mean steps M1 | 3.75 ± 0.75 | 3.20 ± 0.84 | 2.80 ± 1.10 |
| Optimal action rate M0 | 0.68 ± 0.16 | 0.77 ± 0.16 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.74 ± 0.19 | 0.87 ± 0.18 | 1.00 ± 0.00 |
| Route regret M0 | 2.20 ± 1.02 | 1.90 ± 1.07 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 |
| Detection correct | 0.00 ± 0.00 | 0.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 0.00 ± 0.00 | 0.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 0.75 ± 0.00 | 0.75 ± 0.00 | 1.00 ± 0.00 |
| Route probe optimal | 0.40 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Input tokens | 67,442 ± 25,468 | 183,950 ± 176,097 | 42,848 ± 23,373 |
| Output tokens | 558 ± 161 | 8,262 ± 14,552 | 446 ± 153 |
| Cost per run (USD, billed where reported) | 0.04 ± 0.01 | 0.22 ± 0.36 | 0.03 ± 0.01 |

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
| Mean steps M0 | 4.95 ± 1.43 | 4.60 ± 1.66 | 2.80 ± 1.10 |
| Mean steps M1 | 2.95 ± 1.10 | 3.20 ± 1.30 | 2.80 ± 1.10 |
| Optimal action rate M0 | 0.71 ± 0.14 | 0.80 ± 0.12 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.96 ± 0.07 | 0.90 ± 0.15 | 1.00 ± 0.00 |
| Route regret M0 | 2.15 ± 0.80 | 1.80 ± 1.08 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.20 ± 0.45 | 0.00 ± 0.00 | 0.00 ± 0.00 |
| Detection correct | 0.00 ± 0.00 | 0.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 0.00 ± 0.00 | 0.20 ± 0.45 | 1.00 ± 0.00 |
| Preservation accuracy | 0.75 ± 0.00 | 0.75 ± 0.00 | 1.00 ± 0.00 |
| Route probe optimal | 1.00 ± 0.00 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Input tokens | 56,262 ± 27,653 | 99,296 ± 43,404 | 40,948 ± 21,974 |
| Output tokens | 2,517 ± 759 | 2,654 ± 589 | 599 ± 137 |
| Cost per run (USD, billed where reported) | 0.06 ± 0.01 | 0.07 ± 0.02 | 0.03 ± 0.01 |

Values are mean ± standard deviation across runs. Exposed runs only (1 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 1 | 0 | 0 |
| Detection correct | 0.00 | n/a | n/a |
| Localization correct | 0.00 | n/a | n/a |
| Preservation accuracy | 0.75 | n/a | n/a |

### scenario irrelevant · mode sto · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 6.55 ± 1.25 | 6.00 ± 1.05 | 3.60 ± 1.19 |
| Mean steps M1 | 5.80 ± 2.12 | 5.00 ± 1.99 | 4.35 ± 2.07 |
| Optimal action rate M0 | 0.62 ± 0.17 | 0.72 ± 0.15 | 0.93 ± 0.15 |
| Optimal action rate M1 | 0.69 ± 0.24 | 0.76 ± 0.19 | 0.91 ± 0.15 |
| Route regret M0 | 3.03 ± 1.21 | 2.30 ± 1.05 | 0.14 ± 0.31 |
| Exposed (share of runs) | 0.20 ± 0.45 | 0.00 ± 0.00 | 0.00 ± 0.00 |
| Detection correct | 0.60 ± 0.55 | 0.20 ± 0.45 | 1.00 ± 0.00 |
| Localization correct | 0.20 ± 0.45 | 0.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 0.70 ± 0.21 | 0.75 ± 0.00 | 1.00 ± 0.00 |
| Route probe optimal | 0.40 ± 0.55 | 0.40 ± 0.55 | 0.80 ± 0.45 |
| Input tokens | 119,795 ± 47,270 | 183,347 ± 72,433 | 76,415 ± 45,440 |
| Output tokens | 677 ± 121 | 2,774 ± 652 | 660 ± 300 |
| Cost per run (USD, billed where reported) | 0.05 ± 0.01 | 0.09 ± 0.02 | 0.04 ± 0.01 |

Values are mean ± standard deviation across runs. Exposed runs only (1 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 1 | 0 | 0 |
| Detection correct | 1.00 | n/a | n/a |
| Localization correct | 1.00 | n/a | n/a |
| Preservation accuracy | 1.00 | n/a | n/a |

### scenario irrelevant · mode sto · reasoning on (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 5.95 ± 1.43 | 6.35 ± 1.56 | 3.45 ± 1.33 |
| Mean steps M1 | 4.50 ± 1.91 | 4.75 ± 1.55 | 4.20 ± 2.06 |
| Optimal action rate M0 | 0.73 ± 0.10 | 0.67 ± 0.08 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.79 ± 0.17 | 0.75 ± 0.18 | 1.00 ± 0.00 |
| Route regret M0 | 2.42 ± 0.78 | 2.58 ± 0.85 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.00 ± 0.00 | 0.00 ± 0.00 | 0.00 ± 0.00 |
| Detection correct | 0.20 ± 0.45 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Localization correct | 0.00 ± 0.00 | 0.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 0.75 ± 0.00 | 0.75 ± 0.00 | 1.00 ± 0.00 |
| Route probe optimal | 0.20 ± 0.45 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Input tokens | 90,045 ± 42,627 | 176,278 ± 71,876 | 67,834 ± 41,505 |
| Output tokens | 3,149 ± 1,401 | 5,267 ± 1,591 | 3,131 ± 1,611 |
| Cost per run (USD, billed where reported) | 0.07 ± 0.02 | 0.11 ± 0.03 | 0.06 ± 0.03 |

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
| Mean steps M0 | 4.80 ± 1.14 | 4.80 ± 1.56 | 2.80 ± 1.10 |
| Mean steps M1 | 3.60 ± 0.55 | 3.40 ± 0.89 | 2.80 ± 1.10 |
| Optimal action rate M0 | 0.69 ± 0.18 | 0.75 ± 0.18 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.77 ± 0.22 | 0.83 ± 0.24 | 1.00 ± 0.00 |
| Route regret M0 | 2.00 ± 0.92 | 2.00 ± 1.10 | 0.00 ± 0.00 |
| Exposed (share of runs) | n/a | n/a | n/a |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | n/a | n/a | n/a |
| Preservation accuracy | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Route probe optimal | 0.40 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Input tokens | 58,360 ± 18,215 | 106,600 ± 38,912 | 40,402 ± 22,735 |
| Output tokens | 477 ± 92 | 1,853 ± 344 | 418 ± 149 |
| Cost per run (USD, billed where reported) | 0.04 ± 0.01 | 0.06 ± 0.01 | 0.03 ± 0.01 |

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
| Mean steps M0 | 4.95 ± 1.45 | 4.65 ± 1.63 | 2.80 ± 1.10 |
| Mean steps M1 | 3.40 ± 1.10 | 3.10 ± 1.34 | 2.80 ± 1.10 |
| Optimal action rate M0 | 0.71 ± 0.12 | 0.78 ± 0.14 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.85 ± 0.17 | 0.94 ± 0.08 | 1.00 ± 0.00 |
| Route regret M0 | 2.15 ± 0.68 | 1.85 ± 1.07 | 0.00 ± 0.00 |
| Exposed (share of runs) | n/a | n/a | n/a |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | n/a | n/a | n/a |
| Preservation accuracy | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Route probe optimal | 0.60 ± 0.55 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Input tokens | 58,813 ± 29,543 | 114,981 ± 51,195 | 38,884 ± 21,751 |
| Output tokens | 1,711 ± 939 | 8,931 ± 14,478 | 590 ± 178 |
| Cost per run (USD, billed where reported) | 0.05 ± 0.02 | 0.18 ± 0.25 | 0.03 ± 0.01 |

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
| Mean steps M0 | 5.90 ± 0.91 | 6.20 ± 1.54 | 3.60 ± 1.19 |
| Mean steps M1 | 5.05 ± 1.98 | 4.90 ± 1.40 | 4.45 ± 2.24 |
| Optimal action rate M0 | 0.69 ± 0.15 | 0.75 ± 0.13 | 0.93 ± 0.15 |
| Optimal action rate M1 | 0.68 ± 0.12 | 0.79 ± 0.19 | 0.88 ± 0.17 |
| Route regret M0 | 2.25 ± 0.99 | 2.55 ± 1.13 | 0.14 ± 0.31 |
| Exposed (share of runs) | n/a | n/a | n/a |
| Detection correct | 0.60 ± 0.55 | 0.80 ± 0.45 | 0.80 ± 0.45 |
| Localization correct | n/a | n/a | n/a |
| Preservation accuracy | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Route probe optimal | 0.20 ± 0.45 | 0.40 ± 0.55 | 0.60 ± 0.55 |
| Input tokens | 93,238 ± 37,841 | 172,421 ± 64,650 | 75,552 ± 47,094 |
| Output tokens | 589 ± 124 | 2,579 ± 537 | 688 ± 302 |
| Cost per run (USD, billed where reported) | 0.05 ± 0.01 | 0.09 ± 0.02 | 0.04 ± 0.02 |

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
| Mean steps M0 | 6.30 ± 1.41 | 6.50 ± 1.51 | 3.50 ± 1.33 |
| Mean steps M1 | 4.95 ± 1.90 | 5.10 ± 2.00 | 4.40 ± 2.39 |
| Optimal action rate M0 | 0.69 ± 0.09 | 0.67 ± 0.06 | 0.99 ± 0.02 |
| Optimal action rate M1 | 0.74 ± 0.16 | 0.69 ± 0.11 | 0.98 ± 0.04 |
| Route regret M0 | 2.67 ± 0.55 | 2.93 ± 1.12 | 0.03 ± 0.07 |
| Exposed (share of runs) | n/a | n/a | n/a |
| Detection correct | 0.80 ± 0.45 | 0.40 ± 0.55 | 0.80 ± 0.45 |
| Localization correct | n/a | n/a | n/a |
| Preservation accuracy | 1.00 ± 0.00 | 0.90 ± 0.14 | 1.00 ± 0.00 |
| Route probe optimal | 0.40 ± 0.55 | 0.00 ± 0.00 | 1.00 ± 0.00 |
| Input tokens | 98,484 ± 48,553 | 182,618 ± 82,162 | 68,810 ± 45,463 |
| Output tokens | 2,507 ± 1,531 | 5,170 ± 1,749 | 3,842 ± 2,361 |
| Cost per run (USD, billed where reported) | 0.07 ± 0.03 | 0.11 ± 0.04 | 0.07 ± 0.03 |

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
| Mean steps M0 | 5.05 ± 1.44 | 4.80 ± 1.56 | 2.80 ± 1.10 |
| Mean steps M1 | 4.05 ± 1.33 | 3.00 ± 1.22 | 2.20 ± 1.30 |
| Optimal action rate M0 | 0.67 ± 0.15 | 0.75 ± 0.18 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.70 ± 0.18 | 0.83 ± 0.24 | 1.00 ± 0.00 |
| Route regret M0 | 2.25 ± 0.94 | 2.00 ± 1.10 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.00 ± 0.00 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Detection correct | 0.00 ± 0.00 | 0.40 ± 0.55 | 0.80 ± 0.45 |
| Localization correct | 0.00 ± 0.00 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Preservation accuracy | 0.75 ± 0.00 | 0.85 ± 0.14 | 1.00 ± 0.00 |
| Route probe optimal | 0.20 ± 0.45 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Input tokens | 72,524 ± 28,260 | 105,401 ± 45,325 | 36,975 ± 22,840 |
| Output tokens | 589 ± 110 | 1,913 ± 527 | 411 ± 142 |
| Cost per run (USD, billed where reported) | 0.04 ± 0.01 | 0.06 ± 0.02 | 0.03 ± 0.01 |

Values are mean ± standard deviation across runs. Exposed runs only (7 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 0 | 2 | 5 |
| Detection correct | n/a | 1.00 ± 0.00 | 0.80 ± 0.45 |
| Localization correct | n/a | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | n/a | 1.00 ± 0.00 | 1.00 ± 0.00 |

### scenario redirect · mode det · reasoning on (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 4.75 ± 1.16 | 5.45 ± 1.68 | 2.80 ± 1.10 |
| Mean steps M1 | 3.20 ± 0.45 | 3.00 ± 0.85 | 2.20 ± 1.30 |
| Optimal action rate M0 | 0.70 ± 0.12 | 0.67 ± 0.14 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.80 ± 0.18 | 0.84 ± 0.13 | 1.00 ± 0.00 |
| Route regret M0 | 1.95 ± 0.54 | 2.65 ± 0.65 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.00 ± 0.00 | 0.20 ± 0.45 | 1.00 ± 0.00 |
| Detection correct | 0.20 ± 0.45 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 0.80 ± 0.45 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 0.80 ± 0.11 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Route probe optimal | 0.40 ± 0.55 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Input tokens | 55,305 ± 18,197 | 109,639 ± 42,374 | 35,766 ± 22,195 |
| Output tokens | 1,820 ± 763 | 2,689 ± 675 | 617 ± 228 |
| Cost per run (USD, billed where reported) | 0.05 ± 0.01 | 0.07 ± 0.02 | 0.03 ± 0.01 |

Values are mean ± standard deviation across runs. Exposed runs only (6 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 0 | 1 | 5 |
| Detection correct | n/a | 1.00 | 1.00 ± 0.00 |
| Localization correct | n/a | 1.00 | 1.00 ± 0.00 |
| Preservation accuracy | n/a | 1.00 | 1.00 ± 0.00 |

### scenario redirect · mode sto · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 0.95 ± 0.11 | 1.00 ± 0.00 |
| Mean steps M0 | 6.45 ± 1.74 | 6.15 ± 1.02 | 3.60 ± 1.19 |
| Mean steps M1 | 5.05 ± 2.03 | 5.13 ± 2.55 | 3.45 ± 2.64 |
| Optimal action rate M0 | 0.61 ± 0.21 | 0.70 ± 0.15 | 0.93 ± 0.15 |
| Optimal action rate M1 | 0.70 ± 0.24 | 0.72 ± 0.17 | 0.97 ± 0.07 |
| Route regret M0 | 2.64 ± 1.52 | 2.56 ± 1.12 | 0.14 ± 0.31 |
| Exposed (share of runs) | 0.20 ± 0.45 | 0.60 ± 0.55 | 0.80 ± 0.45 |
| Detection correct | 0.40 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Localization correct | 0.20 ± 0.45 | 0.60 ± 0.55 | 0.80 ± 0.45 |
| Preservation accuracy | 0.80 ± 0.11 | 0.90 ± 0.14 | 1.00 ± 0.00 |
| Route probe optimal | 0.20 ± 0.45 | 0.20 ± 0.45 | 0.80 ± 0.45 |
| Input tokens | 107,412 ± 56,319 | 204,909 ± 131,353 | 65,378 ± 47,810 |
| Output tokens | 624 ± 145 | 2,780 ± 789 | 621 ± 218 |
| Cost per run (USD, billed where reported) | 0.05 ± 0.01 | 0.10 ± 0.04 | 0.04 ± 0.01 |

Values are mean ± standard deviation across runs. Exposed runs only (8 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 1 | 3 | 4 |
| Detection correct | 1.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 1.00 | 1.00 ± 0.00 | 0.75 ± 0.50 |
| Preservation accuracy | 1.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |

### scenario redirect · mode sto · reasoning on (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 6.25 ± 1.49 | 6.05 ± 1.54 | 3.45 ± 1.33 |
| Mean steps M1 | 4.65 ± 1.77 | 4.85 ± 2.05 | 3.30 ± 2.34 |
| Optimal action rate M0 | 0.70 ± 0.07 | 0.67 ± 0.18 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.76 ± 0.18 | 0.71 ± 0.21 | 1.00 ± 0.01 |
| Route regret M0 | 2.77 ± 0.86 | 2.65 ± 1.37 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.60 ± 0.55 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Detection correct | 0.60 ± 0.55 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Localization correct | 0.60 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Preservation accuracy | 0.85 ± 0.14 | 0.85 ± 0.14 | 1.00 ± 0.00 |
| Route probe optimal | 0.40 ± 0.55 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Input tokens | 96,010 ± 47,790 | 170,881 ± 94,896 | 57,836 ± 42,216 |
| Output tokens | 3,220 ± 1,757 | 4,372 ± 1,682 | 2,289 ± 1,621 |
| Cost per run (USD, billed where reported) | 0.07 ± 0.03 | 0.10 ± 0.04 | 0.05 ± 0.03 |

Values are mean ± standard deviation across runs. Exposed runs only (10 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 3 | 2 | 5 |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 0.92 ± 0.14 | 1.00 ± 0.00 | 1.00 ± 0.00 |

### scenario silent_break · mode det · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 5.10 ± 1.49 | 4.80 ± 1.56 | 2.80 ± 1.10 |
| Mean steps M1 | 3.90 ± 1.23 | 3.90 ± 0.80 | 3.40 ± 0.55 |
| Optimal action rate M0 | 0.66 ± 0.12 | 0.75 ± 0.18 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.94 ± 0.10 | 0.92 ± 0.10 | 1.00 ± 0.00 |
| Route regret M0 | 2.30 ± 0.78 | 2.00 ± 1.10 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.20 ± 0.45 | 0.60 ± 0.55 | 0.80 ± 0.45 |
| Detection correct | 0.40 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Localization correct | 0.40 ± 0.55 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 0.85 ± 0.14 | 0.90 ± 0.14 | 1.00 ± 0.00 |
| Route probe optimal | 0.80 ± 0.45 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Input tokens | 73,413 ± 40,035 | 121,128 ± 46,367 | 48,206 ± 18,073 |
| Output tokens | 614 ± 306 | 2,003 ± 398 | 485 ± 126 |
| Cost per run (USD, billed where reported) | 0.04 ± 0.01 | 0.07 ± 0.02 | 0.03 ± 0.01 |

Values are mean ± standard deviation across runs. Exposed runs only (8 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 1 | 3 | 4 |
| Detection correct | 1.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 1.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 1.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |

### scenario silent_break · mode det · reasoning on (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 4.75 ± 1.20 | 5.10 ± 1.97 | 2.80 ± 1.10 |
| Mean steps M1 | 3.80 ± 1.08 | 3.80 ± 0.65 | 3.40 ± 0.55 |
| Optimal action rate M0 | 0.73 ± 0.13 | 0.77 ± 0.09 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.96 ± 0.04 | 0.93 ± 0.10 | 1.00 ± 0.00 |
| Route regret M0 | 1.95 ± 0.37 | 2.30 ± 0.89 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.40 ± 0.55 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Detection correct | 0.40 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Localization correct | 0.60 ± 0.55 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Preservation accuracy | 0.85 ± 0.14 | 0.90 ± 0.14 | 1.00 ± 0.00 |
| Route probe optimal | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Input tokens | 63,517 ± 28,509 | 119,647 ± 39,750 | 46,688 ± 17,485 |
| Output tokens | 2,145 ± 986 | 3,029 ± 677 | 693 ± 170 |
| Cost per run (USD, billed where reported) | 0.05 ± 0.02 | 0.08 ± 0.02 | 0.03 ± 0.01 |

Values are mean ± standard deviation across runs. Exposed runs only (9 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 2 | 2 | 5 |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Preservation accuracy | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |

### scenario silent_break · mode sto · reasoning off (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (1, 0, 13, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 0.90 ± 0.22 | 0.90 ± 0.22 | 1.00 ± 0.00 |
| Mean steps M0 | 6.20 ± 1.24 | 6.10 ± 0.95 | 3.75 ± 1.25 |
| Mean steps M1 | 6.25 ± 2.63 | 5.80 ± 2.85 | 5.15 ± 1.95 |
| Optimal action rate M0 | 0.68 ± 0.18 | 0.74 ± 0.14 | 0.84 ± 0.15 |
| Optimal action rate M1 | 0.75 ± 0.19 | 0.83 ± 0.20 | 0.95 ± 0.09 |
| Route regret M0 | 2.66 ± 1.49 | 2.49 ± 1.18 | 0.33 ± 0.33 |
| Exposed (share of runs) | 0.60 ± 0.55 | 0.60 ± 0.55 | 0.60 ± 0.55 |
| Detection correct | 0.60 ± 0.55 | 0.60 ± 0.55 | 1.00 ± 0.00 |
| Localization correct | 0.60 ± 0.55 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Preservation accuracy | 0.80 ± 0.11 | 0.90 ± 0.14 | 1.00 ± 0.00 |
| Route probe optimal | 0.60 ± 0.55 | 1.00 ± 0.00 | 0.80 ± 0.45 |
| Input tokens | 146,473 ± 94,561 | 243,164 ± 144,097 | 89,907 ± 45,951 |
| Output tokens | 694 ± 205 | 2,952 ± 695 | 755 ± 251 |
| Cost per run (USD, billed where reported) | 0.06 ± 0.02 | 0.10 ± 0.04 | 0.04 ± 0.01 |

Values are mean ± standard deviation across runs. Exposed runs only (9 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 3 | 3 | 3 |
| Detection correct | 1.00 ± 0.00 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Localization correct | 1.00 ± 0.00 | 0.67 ± 0.58 | 1.00 ± 0.00 |
| Preservation accuracy | 0.83 ± 0.14 | 1.00 ± 0.00 | 1.00 ± 0.00 |

### scenario silent_break · mode sto · reasoning on (15 runs)

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs (seeds) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) | 5 (0, 13, 1, 25, 8) |
| Goal success M1 | 0.95 ± 0.11 | 1.00 ± 0.00 | 1.00 ± 0.00 |
| Mean steps M0 | 6.55 ± 1.75 | 6.25 ± 1.09 | 3.45 ± 1.33 |
| Mean steps M1 | 5.17 ± 2.19 | 6.20 ± 3.10 | 4.75 ± 1.55 |
| Optimal action rate M0 | 0.66 ± 0.07 | 0.68 ± 0.18 | 1.00 ± 0.00 |
| Optimal action rate M1 | 0.89 ± 0.16 | 0.86 ± 0.14 | 1.00 ± 0.00 |
| Route regret M0 | 2.83 ± 0.93 | 2.77 ± 1.26 | 0.00 ± 0.00 |
| Exposed (share of runs) | 0.40 ± 0.55 | 0.20 ± 0.45 | 1.00 ± 0.00 |
| Detection correct | 0.40 ± 0.55 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Localization correct | 0.20 ± 0.45 | 0.40 ± 0.55 | 1.00 ± 0.00 |
| Preservation accuracy | 0.85 ± 0.14 | 0.80 ± 0.21 | 1.00 ± 0.00 |
| Route probe optimal | 0.80 ± 0.45 | 0.80 ± 0.45 | 1.00 ± 0.00 |
| Input tokens | 124,703 ± 90,984 | 210,851 ± 91,793 | 73,422 ± 36,526 |
| Output tokens | 4,372 ± 2,599 | 5,747 ± 1,767 | 2,741 ± 1,335 |
| Cost per run (USD, billed where reported) | 0.09 ± 0.05 | 0.12 ± 0.04 | 0.06 ± 0.02 |

Values are mean ± standard deviation across runs. Exposed runs only (8 of 15):

| Metric | task_only | model_first | graph_given |
|---|---|---|---|
| Runs | 2 | 1 | 5 |
| Detection correct | 0.50 ± 0.71 | 1.00 | 1.00 ± 0.00 |
| Localization correct | 0.50 ± 0.71 | 1.00 | 1.00 ± 0.00 |
| Preservation accuracy | 1.00 ± 0.00 | 1.00 | 1.00 ± 0.00 |


# H4 and H6 under the registered analysis rules

Script: experiments/h4_h6_uncertainty.py. Inputs: agentic_runs.csv per model and grid in this folder.

## Grid: no_prep

| Model | H4 chose again / qualifying | Share | Wilson lower bound (Bonferroni) | H4 | H6 pairs | H6 mean difference (model-first minus task-only) | 95% interval | p (Holm) | H6 |
|---|---|---|---|---|---|---|---|---|---|
| anthropic-claude-haiku-5.5 | 19/21 | 0.90 | 0.69 | supported | 9 | -0.22 | [-0.56, +0.00] | 0.208 | not shown |
| deepseek-deepseek-v4.1-flash | 17/21 | 0.81 | 0.58 | supported | 17 | +0.12 | [+0.00, +0.29] | 1.000 | not shown |
| openai-gpt-5.6-sol | 14/17 | 0.82 | 0.57 | supported | 10 | -0.30 | [-0.60, +0.00] | 0.089 | not shown |

## Grid: matched_prep

| Model | H4 chose again / qualifying | Share | Wilson lower bound (Bonferroni) | H4 | H6 pairs | H6 mean difference (model-first minus task-only) | 95% interval | p (Holm) | H6 |
|---|---|---|---|---|---|---|---|---|---|
| anthropic-claude-haiku-5.5 | 15/20 | 0.75 | 0.51 | supported | 9 | +0.11 | [-0.22, +0.44] | 1.000 | not shown |
| deepseek-deepseek-v4.1-flash | 27/31 | 0.87 | 0.69 | supported | 22 | -0.09 | [-0.32, +0.14] | 0.791 | not shown |
| openai-gpt-5.6-sol | 8/14 | 0.57 | 0.31 | supported | 8 | +0.12 | [+0.00, +0.38] | 1.000 | not shown |

H6 pairs are seed and scenario combinations in which both arms reached six consecutive failures. With 8 to 22 pairs the paired test has little power, so "not shown" does not mean "no effect".

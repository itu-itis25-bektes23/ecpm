# Confirmatory tests of H2, H3 and H5 (two-turn ICL)

Stochastic silent break, eight-node family, held-out seeds, reasoning off, one answer per instance; an unparsed answer counts as incorrect. Paired differences over seeds with both runs, 95% percentile bootstrap (10,000 resamples, seed 0), one-sided bootstrap p, Holm across models. Script: experiments/stage2_tests.py.

## Primary: unparsed answers count as incorrect

| Hyp. | Quantity | Model | Seeds | Treatment | Comparison | Difference | 95% interval | p (Holm) | Reading |
|---|---|---|---|---|---|---|---|---|---|
| H2 | Localization, counts given minus core (K=10) | GPT-5.6 Sol | 84 | 0.99 | 0.98 | +0.01 | [-0.02, +0.06] | 0.391 | not shown |
| H2 | Localization, counts given minus core (K=10) | Claude Haiku 5.5 | 84 | 0.99 | 0.83 | +0.15 | [+0.08, +0.24] | 0.000 | supported |
| H2 | Localization, counts given minus core (K=10) | DeepSeek V4.1 Flash | 84 | 1.00 | 0.67 | +0.33 | [+0.24, +0.44] | 0.000 | supported |
| H3 | Optimal route, single-turn minus two-turn (K=10) | GPT-5.6 Sol | 84 | 0.62 | 0.71 | -0.10 | [-0.18, -0.01] | 1.000 | not shown |
| H3 | Optimal route, single-turn minus two-turn (K=10) | Claude Haiku 5.5 | 84 | 0.61 | 0.65 | -0.05 | [-0.17, +0.07] | 1.000 | not shown |
| H3 | Optimal route, single-turn minus two-turn (K=10) | DeepSeek V4.1 Flash | 84 | 0.46 | 0.45 | +0.01 | [-0.11, +0.13] | 1.000 | not shown |
| H5 | Localization, K=20 minus K=5 | GPT-5.6 Sol | 81 | 1.00 | 0.78 | +0.22 | [+0.14, +0.32] | 0.000 | supported |
| H5 | Localization, K=20 minus K=5 | Claude Haiku 5.5 | 81 | 0.79 | 0.67 | +0.12 | [+0.02, +0.22] | 0.013 | supported |
| H5 | Localization, K=20 minus K=5 | DeepSeek V4.1 Flash | 81 | 0.73 | 0.44 | +0.28 | [+0.16, +0.41] | 0.000 | supported |

## Secondary: seeds where both answers parsed

| Hyp. | Quantity | Model | Seeds | Treatment | Comparison | Difference | 95% interval | p (Holm) | Reading |
|---|---|---|---|---|---|---|---|---|---|
| H2 | Localization, counts given minus core (K=10) | GPT-5.6 Sol | 84 | 0.99 | 0.98 | +0.01 | [-0.02, +0.06] | 0.390 | not shown |
| H2 | Localization, counts given minus core (K=10) | Claude Haiku 5.5 | 84 | 0.99 | 0.83 | +0.15 | [+0.08, +0.24] | 0.000 | supported |
| H2 | Localization, counts given minus core (K=10) | DeepSeek V4.1 Flash | 84 | 1.00 | 0.67 | +0.33 | [+0.24, +0.44] | 0.000 | supported |
| H3 | Optimal route, single-turn minus two-turn (K=10) | GPT-5.6 Sol | 84 | 0.62 | 0.71 | -0.10 | [-0.18, -0.01] | 1.000 | not shown |
| H3 | Optimal route, single-turn minus two-turn (K=10) | Claude Haiku 5.5 | 84 | 0.61 | 0.65 | -0.05 | [-0.17, +0.07] | 1.000 | not shown |
| H3 | Optimal route, single-turn minus two-turn (K=10) | DeepSeek V4.1 Flash | 84 | 0.46 | 0.45 | +0.01 | [-0.11, +0.13] | 1.000 | not shown |
| H5 | Localization, K=20 minus K=5 | GPT-5.6 Sol | 81 | 1.00 | 0.78 | +0.22 | [+0.14, +0.31] | 0.000 | supported |
| H5 | Localization, K=20 minus K=5 | Claude Haiku 5.5 | 67 | 0.94 | 0.76 | +0.18 | [+0.07, +0.28] | 0.001 | supported |
| H5 | Localization, K=20 minus K=5 | DeepSeek V4.1 Flash | 81 | 0.73 | 0.44 | +0.28 | [+0.16, +0.41] | 0.000 | supported |

## Runs per model and condition

| Model | Condition | Runs | Reports a change | Localization | Localization unparsed | Optimal route | Route through broken link | Route unparsed | Reasoning off violated |
|---|---|---|---|---|---|---|---|---|---|
| GPT-5.6 Sol | core2 | 84 | 1.00 | 0.98 | 0 | 0.71 | 0 | 0 | 0 |
| GPT-5.6 Sol | counts2 | 84 | 1.00 | 0.99 | 0 | 0.00 | 0 | 0 | 0 |
| GPT-5.6 Sol | core1 | 84 | 0.93 | 0.86 | 0 | 0.62 | 0 | 0 | 0 |
| GPT-5.6 Sol | k5 | 84 | 1.00 | 0.79 | 0 | 0.67 | 1 | 0 | 0 |
| GPT-5.6 Sol | k20 | 81 | 1.00 | 1.00 | 0 | 0.68 | 0 | 0 | 0 |
| Claude Haiku 5.5 | core2 | 84 | 0.93 | 0.83 | 0 | 0.65 | 2 | 0 | 0 |
| Claude Haiku 5.5 | counts2 | 84 | 1.00 | 0.99 | 0 | 0.00 | 0 | 15 | 0 |
| Claude Haiku 5.5 | core1 | 84 | 0.85 | 0.15 | 0 | 0.61 | 0 | 0 | 0 |
| Claude Haiku 5.5 | k5 | 84 | 0.99 | 0.67 | 1 | 0.56 | 0 | 0 | 0 |
| Claude Haiku 5.5 | k20 | 81 | 0.85 | 0.79 | 13 | 0.49 | 2 | 0 | 0 |
| DeepSeek V4.1 Flash | core2 | 84 | 0.51 | 0.67 | 0 | 0.45 | 3 | 0 | 0 |
| DeepSeek V4.1 Flash | counts2 | 84 | 1.00 | 1.00 | 0 | 0.00 | 0 | 0 | 0 |
| DeepSeek V4.1 Flash | core1 | 84 | 0.13 | 0.23 | 1 | 0.46 | 13 | 0 | 0 |
| DeepSeek V4.1 Flash | k5 | 84 | 0.81 | 0.44 | 0 | 0.42 | 7 | 0 | 0 |
| DeepSeek V4.1 Flash | k20 | 81 | 0.23 | 0.73 | 0 | 0.44 | 9 | 0 | 0 |

Runs: 1251. Runs without a recorded reasoning control (made before the fix): 0. Commits: 09fc3a8.

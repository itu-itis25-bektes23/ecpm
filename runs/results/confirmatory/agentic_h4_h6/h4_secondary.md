# H4 secondary analyses

Script: `experiments/h4_secondary.py`. It covers task-only runs in stochastic silent break and degradation, in both confirmatory grids, as for the registered H4. The inputs are the GRID zips of 11 October 2026, kept outside the repository.

**Localization-conditioned H4.** This is the H4 measure among qualifying runs whose localization probe named the changed link correctly, as the paper reports secondarily.

**Seed-clustered sensitivity.** A seed can contribute one qualifying run per scenario, so runs are not fully independent. The clustered bound resamples seeds instead of runs: 10,000 resamples, one-sided at 0.05/3. The registered analysis stays the Wilson bound. Few seeds repeat (0 to 3 per model and grid), the bounds move little, and every bound stays far above 0.10.

| Grid | Model | H4: chose again / qualifying | Wilson bound | Seeds (repeated) | Seed-clustered bound | Localized and chose again / localized | Wilson bound, localized |
|---|---|---|---|---|---|---|---|
| GRID_anthropic-claude-haiku-5_5 (no preparation) | anthropic/claude-haiku-5.5 | 19/21 | 0.69 | 18 (3) | 0.74 | 18/20 | 0.68 |
| GRID_deepseek-deepseek-v4_1-flash (no preparation) | deepseek/deepseek-v4.1-flash | 17/21 | 0.58 | 19 (2) | 0.60 | 17/19 | 0.66 |
| GRID_openai-gpt-5_6-sol (no preparation) | openai/gpt-5.6-sol | 14/17 | 0.57 | 16 (1) | 0.59 | 13/15 | 0.60 |
| GRID_anthropic-claude-haiku-5_5 (matched preparation) | anthropic/claude-haiku-5.5 | 15/20 | 0.51 | 20 (0) | 0.55 | 13/17 | 0.51 |
| GRID_deepseek-deepseek-v4_1-flash (matched preparation) | deepseek/deepseek-v4.1-flash | 27/31 | 0.69 | 30 (1) | 0.73 | 25/28 | 0.71 |
| GRID_openai-gpt-5_6-sol (matched preparation) | openai/gpt-5.6-sol | 8/14 | 0.31 | 14 (0) | 0.29 | 7/13 | 0.27 |

# H4 threshold sensitivity

**Question.** H4 counts runs that choose the broken link again after six consecutive failures. How much does the result depend on the threshold of six?

**Method.** `experiments/h4_threshold_sensitivity.py` recomputes the H4 measure with `explore_metrics.choices_after_consecutive_failures` for thresholds 2 to 10. That is the function behind the published H4: the streak carries across M0 and M1, must reach the threshold in M1, and resets on a success of the link. It covers task-only runs, stochastic silent break and degradation, in both confirmatory grids. At six failures it reproduces the published counts. Inputs are the confirmatory GRID zips of 11 October 2026, kept outside the repository.

**Result.** Entries are runs choosing the link again over qualifying runs.

| Grid | Model | 2 failures | 3 failures | 4 failures | 5 failures | 6 failures | 7 failures | 8 failures | 10 failures |
|---|---|---|---|---|---|---|---|---|---|
| no_prep | claude-haiku-5.5 | 49/51 (96%) | 37/45 (82%) | 28/32 (88%) | 21/23 (91%) | 19/21 (90%) | 13/17 (76%) | 13/13 (100%) | 11/11 (100%) |
| no_prep | deepseek-v4.1-flash | 36/40 (90%) | 29/32 (91%) | 22/24 (92%) | 21/21 (100%) | 17/21 (81%) | 17/17 (100%) | 17/17 (100%) | 15/15 (100%) |
| no_prep | gpt-5.6-sol | 51/52 (98%) | 37/45 (82%) | 28/34 (82%) | 19/22 (86%) | 14/17 (82%) | 9/13 (69%) | 9/9 (100%) | 7/8 (88%) |
| matched_prep | claude-haiku-5.5 | 52/57 (91%) | 39/48 (81%) | 29/31 (94%) | 21/26 (81%) | 15/20 (75%) | 12/15 (80%) | 12/12 (100%) | 11/11 (100%) |
| matched_prep | deepseek-v4.1-flash | 58/59 (98%) | 48/49 (98%) | 37/45 (82%) | 33/35 (94%) | 27/31 (87%) | 25/26 (96%) | 22/25 (88%) | 14/17 (82%) |
| matched_prep | gpt-5.6-sol | 52/58 (90%) | 35/45 (78%) | 22/30 (73%) | 17/19 (89%) | 8/14 (57%) | 8/8 (100%) | 7/8 (88%) | 7/7 (100%) |

**Reading.** At every threshold from 2 to 10, most qualifying runs choose the link again. Without preparation the share lies between 69% (Sol, 7 failures, 9/13) and 100%. With matched preparation it lies between 57% (Sol, 6 failures, 8/14, the published value) and 100%. The direction does not depend on the choice of six. The size varies by a few qualifying runs at high thresholds, where counts are small. Fewer failures admit more runs, including retries that are still reasonable. More failures leave fewer runs, which tend to persist.

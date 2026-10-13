# Study v1, exploratory round

Commit 3bb584b65d0f0286f036cb3e6e4f900486aa2a55. Seeds [8, 13, 25, 0, 1, 4, 5, 7, 9, 10].
OpenRouter spend during the round: $0.63.

# Study v1, exploratory round

Seeds: 10 (8, 13, 25, 0, 1, 4, 5, 7, 9, 10). Claims and tests as in docs/STUDY_PLAN_v1.md. **Exploratory round: these numbers guide the design and test nothing.**

Acting runs: 1980. Billed cost: $49.89.

## C1. Choosing the link again after six consecutive failures

| Model | Chose again / qualifying | Share | Lower bound (Wilson, Bonferroni) | Verdict |
|---|---|---|---|---|
| claude-haiku-5.5 | 8/8 | 1.00 | 0.64 | too few |
| deepseek-v4.1-flash | 7/7 | 1.00 | 0.61 | too few |
| gpt-5.6-sol | 2/2 | 1.00 | 0.31 | too few |

## C2. The nudge: runs reaching six consecutive failures, nudge on against off

| Model | Seed-cell pairs | Reached, off | Reached, on | Off only | On only | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| claude-haiku-5.5 | 20 | 8 | 8 | 2 | 2 | 1.0000 | not shown |
| deepseek-v4.1-flash | 20 | 7 | 7 | 1 | 1 | 1.0000 | not shown |
| gpt-5.6-sol | 20 | 2 | 2 | 1 | 1 | 1.0000 | not shown |

## Nudge cost (no change and irrelevant), nudge on minus off

| Model | Scenario | Measure | Pairs | Difference | 95% interval | Cost flag |
|---|---|---|---|---|---|---|
| claude-haiku-5.5 | no_change | goal_success_m1 | 60 | +0.000 | [+0.000, +0.000] |  |
| claude-haiku-5.5 | no_change | steps_m1 | 60 | +0.067 | [-0.199, +0.332] |  |
| claude-haiku-5.5 | no_change | regret_m1 | 60 | +0.048 | [-0.220, +0.317] |  |
| claude-haiku-5.5 | irrelevant | goal_success_m1 | 60 | -0.004 | [-0.012, +0.004] |  |
| claude-haiku-5.5 | irrelevant | steps_m1 | 60 | -0.035 | [-0.272, +0.202] |  |
| claude-haiku-5.5 | irrelevant | regret_m1 | 60 | +0.026 | [-0.143, +0.195] |  |
| deepseek-v4.1-flash | no_change | goal_success_m1 | 60 | -0.021 | [-0.054, +0.013] |  |
| deepseek-v4.1-flash | no_change | steps_m1 | 59 | +0.484 | [+0.126, +0.843] |  |
| deepseek-v4.1-flash | no_change | regret_m1 | 59 | +0.496 | [+0.143, +0.850] |  |
| deepseek-v4.1-flash | irrelevant | goal_success_m1 | 60 | +0.000 | [+0.000, +0.000] |  |
| deepseek-v4.1-flash | irrelevant | steps_m1 | 60 | -0.233 | [-0.585, +0.118] |  |
| deepseek-v4.1-flash | irrelevant | regret_m1 | 60 | -0.147 | [-0.425, +0.131] |  |
| gpt-5.6-sol | no_change | goal_success_m1 | 60 | +0.000 | [+0.000, +0.000] |  |
| gpt-5.6-sol | no_change | steps_m1 | 60 | +0.129 | [-0.114, +0.373] |  |
| gpt-5.6-sol | no_change | regret_m1 | 60 | +0.104 | [-0.128, +0.336] |  |
| gpt-5.6-sol | irrelevant | goal_success_m1 | 60 | -0.004 | [-0.012, +0.004] |  |
| gpt-5.6-sol | irrelevant | steps_m1 | 60 | +0.093 | [-0.161, +0.347] |  |
| gpt-5.6-sol | irrelevant | regret_m1 | 60 | +0.125 | [-0.050, +0.299] |  |

## Acting: detection and localization by cell and prompt (nudge off)

| Model | Mode | Scenario | Prompt | Detection | Localization |
|---|---|---|---|---|---|
| claude-haiku-5.5 | det | hard_removal | graph_given | 100% (10/10) | 100% (10/10) |
| claude-haiku-5.5 | det | hard_removal | model_first | 90% (9/10) | 90% (9/10) |
| claude-haiku-5.5 | det | hard_removal | task_only | 90% (9/10) | 90% (9/10) |
| claude-haiku-5.5 | det | irrelevant | graph_given | 100% (10/10) | 100% (10/10) |
| claude-haiku-5.5 | det | irrelevant | model_first | 0% (0/10) | 0% (0/10) |
| claude-haiku-5.5 | det | irrelevant | task_only | 30% (3/10) | 20% (2/10) |
| claude-haiku-5.5 | det | no_change | graph_given | 100% (10/10) | – |
| claude-haiku-5.5 | det | no_change | model_first | 100% (10/10) | – |
| claude-haiku-5.5 | det | no_change | task_only | 100% (10/10) | – |
| claude-haiku-5.5 | det | redirect | graph_given | 100% (10/10) | 100% (10/10) |
| claude-haiku-5.5 | det | redirect | model_first | 70% (7/10) | 70% (7/10) |
| claude-haiku-5.5 | det | redirect | task_only | 70% (7/10) | 70% (7/10) |
| claude-haiku-5.5 | det | silent_break | graph_given | 100% (10/10) | 100% (10/10) |
| claude-haiku-5.5 | det | silent_break | model_first | 60% (6/10) | 60% (6/10) |
| claude-haiku-5.5 | det | silent_break | task_only | 60% (6/10) | 60% (6/10) |
| claude-haiku-5.5 | sto | degradation | graph_given | 100% (10/10) | 100% (10/10) |
| claude-haiku-5.5 | sto | degradation | model_first | 50% (5/10) | 50% (5/10) |
| claude-haiku-5.5 | sto | degradation | task_only | 50% (5/10) | 70% (7/10) |
| claude-haiku-5.5 | sto | hard_removal | graph_given | 100% (10/10) | 100% (10/10) |
| claude-haiku-5.5 | sto | hard_removal | model_first | 100% (10/10) | 100% (10/10) |
| claude-haiku-5.5 | sto | hard_removal | task_only | 70% (7/10) | 70% (7/10) |
| claude-haiku-5.5 | sto | irrelevant | graph_given | 100% (10/10) | 100% (10/10) |
| claude-haiku-5.5 | sto | irrelevant | model_first | 20% (2/10) | 0% (0/10) |
| claude-haiku-5.5 | sto | irrelevant | task_only | 40% (4/10) | 0% (0/10) |
| claude-haiku-5.5 | sto | no_change | graph_given | 100% (10/10) | – |
| claude-haiku-5.5 | sto | no_change | model_first | 90% (9/10) | – |
| claude-haiku-5.5 | sto | no_change | task_only | 90% (9/10) | – |
| claude-haiku-5.5 | sto | redirect | graph_given | 100% (10/10) | 100% (10/10) |
| claude-haiku-5.5 | sto | redirect | model_first | 60% (6/10) | 50% (5/10) |
| claude-haiku-5.5 | sto | redirect | task_only | 50% (5/10) | 30% (3/10) |
| claude-haiku-5.5 | sto | silent_break | graph_given | 100% (10/10) | 100% (10/10) |
| claude-haiku-5.5 | sto | silent_break | model_first | 70% (7/10) | 60% (6/10) |
| claude-haiku-5.5 | sto | silent_break | task_only | 90% (9/10) | 70% (7/10) |
| deepseek-v4.1-flash | det | hard_removal | graph_given | 100% (10/10) | 100% (10/10) |
| deepseek-v4.1-flash | det | hard_removal | model_first | 40% (4/10) | 70% (7/10) |
| deepseek-v4.1-flash | det | hard_removal | task_only | 60% (6/10) | 70% (7/10) |
| deepseek-v4.1-flash | det | irrelevant | graph_given | 90% (9/10) | 100% (10/10) |
| deepseek-v4.1-flash | det | irrelevant | model_first | 20% (2/10) | 20% (2/10) |
| deepseek-v4.1-flash | det | irrelevant | task_only | 30% (3/10) | 30% (3/10) |
| deepseek-v4.1-flash | det | no_change | graph_given | 100% (10/10) | – |
| deepseek-v4.1-flash | det | no_change | model_first | 100% (10/10) | – |
| deepseek-v4.1-flash | det | no_change | task_only | 100% (10/10) | – |
| deepseek-v4.1-flash | det | redirect | graph_given | 100% (10/10) | 100% (10/10) |
| deepseek-v4.1-flash | det | redirect | model_first | 50% (5/10) | 60% (6/10) |
| deepseek-v4.1-flash | det | redirect | task_only | 60% (6/10) | 70% (7/10) |
| deepseek-v4.1-flash | det | silent_break | graph_given | 100% (10/10) | 100% (10/10) |
| deepseek-v4.1-flash | det | silent_break | model_first | 40% (4/10) | 40% (4/10) |
| deepseek-v4.1-flash | det | silent_break | task_only | 60% (6/10) | 70% (7/10) |
| deepseek-v4.1-flash | sto | degradation | graph_given | 100% (10/10) | 100% (10/10) |
| deepseek-v4.1-flash | sto | degradation | model_first | 0% (0/10) | 40% (4/10) |
| deepseek-v4.1-flash | sto | degradation | task_only | 0% (0/10) | 60% (6/10) |
| deepseek-v4.1-flash | sto | hard_removal | graph_given | 90% (9/10) | 100% (10/10) |
| deepseek-v4.1-flash | sto | hard_removal | model_first | 20% (2/10) | 30% (3/10) |
| deepseek-v4.1-flash | sto | hard_removal | task_only | 30% (3/10) | 50% (5/10) |
| deepseek-v4.1-flash | sto | irrelevant | graph_given | 90% (9/10) | 100% (10/10) |
| deepseek-v4.1-flash | sto | irrelevant | model_first | 0% (0/10) | 10% (1/10) |
| deepseek-v4.1-flash | sto | irrelevant | task_only | 10% (1/10) | 10% (1/10) |
| deepseek-v4.1-flash | sto | no_change | graph_given | 100% (10/10) | – |
| deepseek-v4.1-flash | sto | no_change | model_first | 100% (10/10) | – |
| deepseek-v4.1-flash | sto | no_change | task_only | 90% (9/10) | – |
| deepseek-v4.1-flash | sto | redirect | graph_given | 100% (10/10) | 100% (10/10) |
| deepseek-v4.1-flash | sto | redirect | model_first | 50% (5/10) | 50% (5/10) |
| deepseek-v4.1-flash | sto | redirect | task_only | 40% (4/10) | 80% (8/10) |
| deepseek-v4.1-flash | sto | silent_break | graph_given | 100% (10/10) | 100% (10/10) |
| deepseek-v4.1-flash | sto | silent_break | model_first | 40% (4/10) | 40% (4/10) |
| deepseek-v4.1-flash | sto | silent_break | task_only | 0% (0/10) | 50% (5/10) |
| gpt-5.6-sol | det | hard_removal | graph_given | 90% (9/10) | 100% (10/10) |
| gpt-5.6-sol | det | hard_removal | model_first | 60% (6/10) | 80% (8/10) |
| gpt-5.6-sol | det | hard_removal | task_only | 40% (4/10) | 70% (7/10) |
| gpt-5.6-sol | det | irrelevant | graph_given | 100% (10/10) | 100% (10/10) |
| gpt-5.6-sol | det | irrelevant | model_first | 10% (1/10) | 10% (1/10) |
| gpt-5.6-sol | det | irrelevant | task_only | 10% (1/10) | 10% (1/10) |
| gpt-5.6-sol | det | no_change | graph_given | 100% (10/10) | – |
| gpt-5.6-sol | det | no_change | model_first | 100% (10/10) | – |
| gpt-5.6-sol | det | no_change | task_only | 100% (10/10) | – |
| gpt-5.6-sol | det | redirect | graph_given | 90% (9/10) | 100% (10/10) |
| gpt-5.6-sol | det | redirect | model_first | 60% (6/10) | 80% (8/10) |
| gpt-5.6-sol | det | redirect | task_only | 30% (3/10) | 30% (3/10) |
| gpt-5.6-sol | det | silent_break | graph_given | 100% (10/10) | 100% (10/10) |
| gpt-5.6-sol | det | silent_break | model_first | 70% (7/10) | 90% (9/10) |
| gpt-5.6-sol | det | silent_break | task_only | 30% (3/10) | 40% (4/10) |
| gpt-5.6-sol | sto | degradation | graph_given | 100% (10/10) | 100% (10/10) |
| gpt-5.6-sol | sto | degradation | model_first | 30% (3/10) | 30% (3/10) |
| gpt-5.6-sol | sto | degradation | task_only | 50% (5/10) | 30% (3/10) |
| gpt-5.6-sol | sto | hard_removal | graph_given | 90% (9/10) | 90% (9/10) |
| gpt-5.6-sol | sto | hard_removal | model_first | 80% (8/10) | 60% (6/10) |
| gpt-5.6-sol | sto | hard_removal | task_only | 80% (8/10) | 50% (5/10) |
| gpt-5.6-sol | sto | irrelevant | graph_given | 100% (10/10) | 100% (10/10) |
| gpt-5.6-sol | sto | irrelevant | model_first | 30% (3/10) | 0% (0/10) |
| gpt-5.6-sol | sto | irrelevant | task_only | 40% (4/10) | 10% (1/10) |
| gpt-5.6-sol | sto | no_change | graph_given | 90% (9/10) | – |
| gpt-5.6-sol | sto | no_change | model_first | 70% (7/10) | – |
| gpt-5.6-sol | sto | no_change | task_only | 60% (6/10) | – |
| gpt-5.6-sol | sto | redirect | graph_given | 100% (10/10) | 90% (9/10) |
| gpt-5.6-sol | sto | redirect | model_first | 40% (4/10) | 30% (3/10) |
| gpt-5.6-sol | sto | redirect | task_only | 60% (6/10) | 40% (4/10) |
| gpt-5.6-sol | sto | silent_break | graph_given | 100% (10/10) | 100% (10/10) |
| gpt-5.6-sol | sto | silent_break | model_first | 50% (5/10) | 30% (3/10) |
| gpt-5.6-sol | sto | silent_break | task_only | 50% (5/10) | 30% (3/10) |

## Acting: exposure (nudge off, changed scenarios)

| Model | Runs | Detection | Localization |
|---|---|---|---|
| claude-haiku-5.5 | exposed | 97% (148/153) | 95% (146/153) |
| claude-haiku-5.5 | not exposed | 42% (49/117) | 34% (40/117) |
| deepseek-v4.1-flash | exposed | 74% (115/155) | 93% (144/155) |
| deepseek-v4.1-flash | not exposed | 23% (27/115) | 27% (31/115) |
| gpt-5.6-sol | exposed | 96% (119/124) | 94% (117/124) |
| gpt-5.6-sol | not exposed | 34% (50/146) | 29% (43/146) |

## C3. The bridge: retrying with the complete log against the agent's own log

| Model | Decisions | Retry, own log | Retry, complete log | Own only | Complete only | p | Verdict |
|---|---|---|---|---|---|---|---|
| claude-haiku-5.5 | 154 | 102 | 68 | 51 | 17 | 0.0000 | descriptive |
| gpt-5.6-sol | 9 | 9 | 9 | 0 | 0 | 1.0000 | descriptive |
| pooled | 163 | 111 | 77 | 51 | 17 | 0.0000 | holds |

Decisions without a valid action in either probe: 68.

## Reading: detection, localization, routes and necessary updates (histories pooled)

| Model | Mode | Scenario | Arm | Detection | Localization | Optimal routes | Necessary updates |
|---|---|---|---|---|---|---|---|

## Evidence-only references: localization on the same views (K = 10)

| Mode | Scenario | Rate counter | Transition counter | Bayesian | Generator-aware |
|---|---|---|---|---|---|
| det | hard_removal | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) |
| det | irrelevant | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) |
| det | redirect | 0% (0/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) |
| det | silent_break | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) |
| sto | degradation | 60% (6/10) | 60% (6/10) | 60% (6/10) | 70% (7/10) |
| sto | hard_removal | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) |
| sto | irrelevant | 100% (10/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) |
| sto | redirect | 0% (0/10) | 100% (10/10) | 100% (10/10) | 100% (10/10) |
| sto | silent_break | 80% (8/10) | 80% (8/10) | 80% (8/10) | 100% (10/10) |


# Evidence-only reference agent

Seeds: [8, 13, 25, 0, 1, 4, 5, 7, 9, 10]. Agent: reference_agent.py. Runner: experiments/reference_agent_runs.py. Same worlds, episodes, step budget and metric functions as the language-model agents.

| Mode | Scenario | Runs | M1 goal success | Mean steps M1 | H4: chose again / qualifying | Median decision lag | Exposed runs |
|---|---|---|---|---|---|---|---|
| det | no_change | 10 | 1.00 | 3.5 | 0/0 | – | 0 |
| det | irrelevant | 10 | 1.00 | 3.6 | 0/0 | 1.0 | 2 |
| det | silent_break | 10 | 1.00 | 4.3 | 0/0 | 1.0 | 6 |
| det | hard_removal | 10 | 1.00 | 4.2 | 0/0 | 1 | 6 |
| det | redirect | 10 | 1.00 | 4.0 | 0/0 | – | 0 |
| sto | no_change | 10 | 1.00 | 5.0 | 0/0 | – | 0 |
| sto | irrelevant | 10 | 1.00 | 5.0 | 0/0 | 1 | 1 |
| sto | silent_break | 10 | 1.00 | 6.5 | 0/6 | 6.0 | 6 |
| sto | hard_removal | 10 | 1.00 | 5.3 | 0/0 | 1.0 | 6 |
| sto | redirect | 10 | 0.90 | 5.1 | 0/0 | – | 0 |
| sto | degradation | 10 | 1.00 | 5.9 | 0/2 | 12.0 | 6 |


Log:
```
19:08:54 round exploratory: 10 seeds [8, 13, 25, 0, 1, 4, 5, 7, 9, 10]
19:08:55 OpenRouter spend before the round: $183.10; budget for this round $250
19:08:55 commit e7f5bc2ae93439dec21da861cbf2ca6354865d5f
19:08:55 live gate on exploratory seed 8
19:08:55 started gate_haiku_off
19:08:55 started gate_haiku_nudge
19:08:55 started gate_sol_off
19:08:55 started gate_sol_nudge
19:08:55 started gate_deepseek_off
19:08:55 started gate_deepseek_nudge
19:09:15 running: gate_haiku_off, gate_haiku_nudge, gate_sol_off, gate_sol_nudge, gate_deepseek_off, gate_deepseek_nudge; spent $0.00
19:12:40 live gate passed for acting
19:12:43 STOPPED: reading preflight not accepted for sol; see ../ecpm-study-private/sol
22:25:34 round exploratory: 10 seeds [8, 13, 25, 0, 1, 4, 5, 7, 9, 10]
22:25:35 OpenRouter spend before the round: $183.49; budget for this round $250
22:25:35 commit 704dd9a2fd3d95a4346903e26fd0e0772033d024
22:25:35 live gate on exploratory seed 8
22:25:35 started gate_haiku_off
22:25:35 started gate_haiku_nudge
22:25:35 started gate_sol_off
22:25:35 started gate_sol_nudge
22:25:35 started gate_deepseek_off
22:25:35 started gate_deepseek_nudge
22:25:55 running: ; spent $0.00
22:25:56 live gate passed for acting
22:25:57 STOPPED: reading preflight not accepted for sol; see ../ecpm-study-private/sol
22:29:40 round exploratory: 10 seeds [8, 13, 25, 0, 1, 4, 5, 7, 9, 10]
22:29:40 OpenRouter spend before the round: $183.49; budget for this round $250
22:29:40 commit 4d7ff90d8e47ad18e8460a537c9af975008df981
22:29:40 live gate on exploratory seed 8
22:29:42 started gate_haiku_off
22:29:44 started gate_haiku_nudge
22:29:45 started gate_sol_off
22:29:45 started gate_sol_nudge
22:29:47 started gate_deepseek_off
22:29:48 started gate_deepseek_nudge
22:30:08 running: ; spent $0.00
22:30:09 live gate passed for acting
22:30:16 STOPPED: reading preflight not accepted for deepseek; see ../ecpm-study-private/deepseek
22:45:45 round exploratory: 10 seeds [8, 13, 25, 0, 1, 4, 5, 7, 9, 10]
22:45:46 OpenRouter spend before the round: $183.49; budget for this round $250
22:45:46 commit 67a163a152c4aaeb10b12999c53d21a52cdfdc8b
22:45:46 live gate on exploratory seed 8
22:45:46 started gate_haiku_off
22:45:46 started gate_haiku_nudge
22:45:47 started gate_sol_off
22:45:47 started gate_sol_nudge
22:45:47 started gate_deepseek_off
22:45:47 started gate_deepseek_nudge
22:46:08 running: ; spent $0.00
22:46:09 live gate passed for acting
22:46:15 reading configs validated
22:46:16 started acting_haiku_off
22:46:16 started acting_haiku_nudge
22:46:16 started acting_sol_off
22:46:17 started acting_sol_nudge
22:46:17 started acting_deepseek_off
22:46:19 started acting_deepseek_nudge
22:46:21 started reading_haiku
22:46:22 started reading_sol
22:46:23 started reading_deepseek
22:47:23 running: acting_haiku_off, acting_haiku_nudge, acting_sol_off, acting_sol_nudge, acting_deepseek_off, acting_deepseek_nudge, reading_haiku, reading_sol, reading_deepseek; spent $0.93
22:58:00 running: acting_haiku_off, acting_haiku_nudge, acting_sol_off, acting_sol_nudge, acting_deepseek_off, acting_deepseek_nudge, reading_haiku, reading_sol, reading_deepseek; spent $19.23
23:08:24 running: acting_haiku_off, acting_haiku_nudge, acting_sol_off, acting_sol_nudge, acting_deepseek_off, acting_deepseek_nudge, reading_haiku, reading_sol, reading_deepseek; spent $39.73
23:18:39 running: acting_haiku_off, acting_haiku_nudge, acting_sol_off, acting_sol_nudge, acting_deepseek_off, acting_deepseek_nudge; spent $53.27
23:28:09 STOPPED: 170 acting batches gave up after five attempts (limit 20)
23:28:09   ending acting_haiku_off
23:28:09   ending acting_haiku_nudge
23:28:09   ending acting_sol_off
23:28:09   ending acting_sol_nudge
23:28:09   ending acting_deepseek_off
23:28:09   ending acting_deepseek_nudge
07:17:51 round exploratory: 10 seeds [8, 13, 25, 0, 1, 4, 5, 7, 9, 10]
07:17:54 OpenRouter spend before the round: $0.00; budget for this round $25
07:17:55 commit 1313289ea64e28d1966fb3a20202434697b488c5
07:17:55 live gate on exploratory seed 8
07:17:55 started gate_haiku_off
07:17:55 started gate_haiku_nudge
07:17:55 started gate_sol_off
07:17:55 started gate_sol_nudge
07:17:55 started gate_deepseek_off
07:17:56 started gate_deepseek_nudge
07:18:16 running: gate_haiku_off, gate_haiku_nudge, gate_sol_off, gate_sol_nudge, gate_deepseek_off, gate_deepseek_nudge; spent $0.00
07:18:23 STOPPED: 170 acting batches gave up after five attempts (limit 20)
07:18:23   ending gate_haiku_off
07:18:23   ending gate_haiku_nudge
07:18:23   ending gate_sol_off
07:18:23   ending gate_sol_nudge
07:18:23   ending gate_deepseek_off
07:18:23   ending gate_deepseek_nudge
07:31:01 round exploratory: 10 seeds [8, 13, 25, 0, 1, 4, 5, 7, 9, 10]
07:31:02 OpenRouter spend before the round: $0.32; budget for this round $25
07:31:02 commit 52375b498aae2c1e84697763aaf1eee5608692cb
07:31:02 170 batch failures from earlier attempts are in the logs; only new ones count
07:31:02 live gate on exploratory seed 8
07:31:02 started gate_haiku_off
07:31:02 started gate_haiku_nudge
07:31:02 started gate_sol_off
07:31:03 started gate_sol_nudge
07:31:03 started gate_deepseek_off
07:31:03 started gate_deepseek_nudge
07:31:23 running: gate_sol_nudge; spent $0.01
07:36:48 live gate passed for acting
07:36:49 reading configs validated
07:36:49 started acting_haiku_off
07:36:49 started acting_haiku_nudge
07:36:49 started acting_sol_off
07:36:49 started acting_sol_nudge
07:36:50 started acting_deepseek_off
07:36:51 started acting_deepseek_nudge
07:36:52 started reading_haiku
07:36:54 started reading_sol
07:36:54 started reading_deepseek
07:37:54 running: acting_haiku_off, acting_haiku_nudge, acting_sol_off, acting_sol_nudge, acting_deepseek_off, acting_deepseek_nudge, reading_haiku, reading_sol, reading_deepseek; spent $0.22
07:42:30 round exploratory: 10 seeds [8, 13, 25, 0, 1, 4, 5, 7, 9, 10]; runs dated from 2026-10-12 count as done
07:42:31 OpenRouter spend before the round: $1.46; budget for this round $25
07:42:31 commit df727cbf5b2e486b77d001ecdc6a5c5b79b68dc4
07:42:33 170 batch failures from earlier attempts are in the logs; only new ones count
07:42:33 live gate on exploratory seed 8
07:42:33 started gate_haiku_off
07:42:33 started gate_haiku_nudge
07:42:33 started gate_sol_off
07:42:33 started gate_sol_nudge
07:42:33 started gate_deepseek_off
07:42:33 started gate_deepseek_nudge
07:42:53 running: ; spent $0.00
07:42:57 STOPPED: live gate: gate_sol_off: a run cost $1.24 (limit $0.5); gate_sol_off: a run cost $1.29 (limit $0.5)
07:46:27 round exploratory: 10 seeds [8, 13, 25, 0, 1, 4, 5, 7, 9, 10]; runs dated from 2026-10-12 count as done
07:46:28 OpenRouter spend before the round: $1.46; budget for this round $25
07:46:28 commit df727cbf5b2e486b77d001ecdc6a5c5b79b68dc4
07:46:28 170 batch failures from earlier attempts are in the logs; only new ones count
07:46:28 live gate on exploratory seed 8
07:46:28 started gate_haiku_off
07:46:28 started gate_haiku_nudge
07:46:29 started gate_sol_off
07:46:29 started gate_sol_nudge
07:46:29 started gate_deepseek_off
07:46:29 started gate_deepseek_nudge
07:47:55 round exploratory: 10 seeds [8, 13, 25, 0, 1, 4, 5, 7, 9, 10]; runs dated from 2026-10-12 count as done
07:47:55 OpenRouter spend before the round: $1.46; budget for this round $25
07:47:55 commit df727cbf5b2e486b77d001ecdc6a5c5b79b68dc4
07:47:56 170 batch failures from earlier attempts are in the logs; only new ones count
07:47:56 live gate on exploratory seed 8
07:47:56 started gate_haiku_off
07:47:56 started gate_haiku_nudge
07:47:56 started gate_sol_off
07:47:56 started gate_sol_nudge
07:47:56 started gate_deepseek_off
07:47:56 started gate_deepseek_nudge
07:48:16 running: ; spent $0.00
07:48:20 live gate passed for acting
07:48:21 reading configs validated
07:48:21 started acting_haiku_off
07:48:21 started acting_haiku_nudge
07:48:21 started acting_sol_off
07:48:21 started acting_sol_nudge
07:48:21 started acting_deepseek_off
07:48:21 started acting_deepseek_nudge
07:48:22 started reading_haiku
07:48:22 started reading_sol
07:48:22 started reading_deepseek
07:49:22 running: acting_haiku_off, acting_haiku_nudge, acting_sol_off, acting_sol_nudge, acting_deepseek_off, acting_deepseek_nudge, reading_haiku, reading_sol, reading_deepseek; spent $0.10
07:59:47 running: acting_haiku_off, acting_haiku_nudge, acting_sol_off, acting_sol_nudge, acting_deepseek_off, acting_deepseek_nudge; spent $5.95
08:03:53 STOPPED: 29 acting batches gave up after five attempts during this round (limit 20)
08:03:53   ending acting_sol_off
08:03:53   ending acting_sol_nudge
08:15:43 round exploratory: 10 seeds [8, 13, 25, 0, 1, 4, 5, 7, 9, 10]; runs dated from 2026-10-12 count as done
08:15:44 OpenRouter spend before the round: $7.68; budget for this round $25
08:15:44 commit ecd5e36f46b2a5fe32d2753f32edcbe9eb8609a8
08:15:44 199 batch failures from earlier attempts are in the logs; only new ones count
08:15:47 one live request per model succeeded
08:15:47 live gate on exploratory seed 8
08:15:47 started gate_haiku_off
08:15:47 started gate_haiku_nudge
08:15:47 started gate_sol_off
08:15:47 started gate_sol_nudge
08:15:47 started gate_deepseek_off
08:15:48 started gate_deepseek_nudge
08:16:08 running: ; spent $0.00
08:16:13 live gate passed for acting
08:16:13 reading configs validated
08:16:13 started acting_haiku_off
08:16:13 started acting_haiku_nudge
08:16:14 started acting_sol_off
08:16:14 started acting_sol_nudge
08:16:14 started acting_deepseek_off
08:16:14 started acting_deepseek_nudge
08:16:14 started reading_haiku
08:16:14 started reading_sol
08:16:15 started reading_deepseek
08:17:15 running: acting_haiku_off, acting_haiku_nudge, acting_sol_off, acting_sol_nudge, acting_deepseek_off, acting_deepseek_nudge, reading_haiku, reading_sol, reading_deepseek; spent $0.03
08:27:22 running: acting_sol_off, acting_sol_nudge; spent $0.22
08:37:27 running: acting_sol_off, acting_sol_nudge; spent $0.45
08:47:32 running: acting_sol_off, acting_sol_nudge; spent $0.68
08:57:38 running: acting_sol_off, acting_sol_nudge; spent $0.89
09:00:39 STOPPED: 21 acting batches gave up after five attempts during this round (limit 20). Last error: acting_sol_nudge: urllib.error.HTTPError: HTTP Error 429: Too Many Requests
09:00:39   ending acting_sol_off
09:00:39   ending acting_sol_nudge
10:39:57 round exploratory: 10 seeds [8, 13, 25, 0, 1, 4, 5, 7, 9, 10]; runs dated from 2026-10-12 count as done
10:39:57 OpenRouter spend before the round: $8.85; budget for this round $25
10:39:58 commit 3bb584b65d0f0286f036cb3e6e4f900486aa2a55
10:39:58 220 batch failures from earlier attempts are in the logs; only new ones count
10:40:01 one live request per model succeeded
10:40:01 live gate on exploratory seed 8
10:40:01 started gate_haiku_off
10:40:01 started gate_haiku_nudge
10:40:01 started gate_sol_off
10:40:01 started gate_sol_nudge
10:40:01 started gate_deepseek_off
10:40:01 started gate_deepseek_nudge
10:40:22 running: ; spent $0.00
10:40:25 live gate passed for acting
10:40:26 reading configs validated
10:40:26 started acting_haiku_off
10:40:26 started acting_haiku_nudge
10:40:26 started acting_sol_off
10:40:26 started acting_sol_nudge
10:40:26 started acting_deepseek_off
10:40:27 started acting_deepseek_nudge
10:40:27 started reading_haiku
10:40:27 started reading_sol
10:40:27 started reading_deepseek
10:41:28 running: acting_haiku_off, acting_haiku_nudge, acting_sol_off, acting_sol_nudge, acting_deepseek_off, acting_deepseek_nudge, reading_haiku, reading_sol, reading_deepseek; spent $0.00
10:48:59 round exploratory: 10 seeds [8, 13, 25, 0, 1, 4, 5, 7, 9, 10]; runs dated from 2026-10-12 count as done
10:49:00 OpenRouter spend before the round: $8.87; budget for this round $25
10:49:00 commit 3bb584b65d0f0286f036cb3e6e4f900486aa2a55
10:49:00 220 batch failures from earlier attempts are in the logs; only new ones count
10:49:04 one live request per model succeeded
10:49:04 live gate on exploratory seed 8
10:49:04 started gate_haiku_off
10:49:04 started gate_haiku_nudge
10:49:04 started gate_sol_off
10:49:04 started gate_sol_nudge
10:49:04 started gate_deepseek_off
10:49:04 started gate_deepseek_nudge
10:49:25 running: ; spent $0.00
10:49:28 live gate passed for acting
10:49:29 reading configs validated
10:49:29 started acting_haiku_off
10:49:29 started acting_haiku_nudge
10:49:30 started acting_sol_off
10:49:30 started acting_sol_nudge
10:49:30 started acting_deepseek_off
10:49:30 started acting_deepseek_nudge
10:49:30 started reading_haiku
10:49:31 started reading_sol
10:49:31 started reading_deepseek
10:50:31 running: acting_haiku_off, acting_haiku_nudge, acting_sol_off, acting_sol_nudge, acting_deepseek_off, acting_deepseek_nudge, reading_haiku, reading_sol, reading_deepseek; spent $0.00
11:00:34 running: acting_sol_off, acting_sol_nudge; spent $0.03
11:10:36 running: acting_sol_off, acting_sol_nudge; spent $0.08
11:20:40 running: acting_sol_off, acting_sol_nudge; spent $0.17
11:30:43 running: acting_sol_off, acting_sol_nudge; spent $0.18
11:37:45 processes that ended with errors: ['reading_haiku', 'reading_sol', 'reading_deepseek'] (their failures are in the logs and the report)
11:38:00 bridge probes
11:40:57 reference agent
11:40:59 analysis

```
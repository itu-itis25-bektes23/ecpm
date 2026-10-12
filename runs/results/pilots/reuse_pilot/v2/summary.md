## anthropic/claude-haiku-5.5

| Condition | Decisions | Reuse the failing link | Switch | No valid action | Errors |
|---|---|---|---|---|---|
| resume | 41 | 33/41 (80%) | 8 | 0 | 0 |
| hint | 41 | 11/41 (27%) | 30 | 0 | 0 |
| hint_first_step | 41 | 32/41 (78%) | 9 | 0 | 0 |
| nudge | 41 | 12/41 (29%) | 29 | 0 | 0 |
| budget | 41 | 29/41 (71%) | 12 | 0 | 0 |
| reader | 41 | 30/41 (73%) | 11 | 0 | 0 |
| reader_full | 41 | 19/41 (46%) | 22 | 0 | 0 |
| reader_hint | 41 | 15/41 (37%) | 26 | 0 | 0 |

Original runs: 33/41 of these decisions reused the failing link. Decisions with a route around it: 41/41.

| Condition | Paired decisions | Reuse, resume | Reuse, condition | Resume reused, condition switched | Resume switched, condition reused |
|---|---|---|---|---|---|
| hint | 41 | 33 | 11 | 22 | 0 |
| hint_first_step | 41 | 33 | 32 | 4 | 3 |
| nudge | 41 | 33 | 12 | 22 | 1 |
| budget | 41 | 33 | 29 | 11 | 7 |
| reader | 41 | 33 | 30 | 7 | 4 |
| reader_full | 41 | 33 | 19 | 17 | 3 |
| reader_hint | 41 | 33 | 15 | 20 | 2 |

| Condition | Route around fits the steps left | Reuse | Route does not fit | Reuse |
|---|---|---|---|---|
| resume | 35 | 27/35 | 6 | 6/6 |
| hint | 35 | 5/35 | 6 | 6/6 |
| hint_first_step | 35 | 26/35 | 6 | 6/6 |
| nudge | 35 | 9/35 | 6 | 3/6 |
| budget | 35 | 24/35 | 6 | 5/6 |
| reader | 35 | 24/35 | 6 | 6/6 |
| reader_full | 35 | 13/35 | 6 | 6/6 |
| reader_hint | 35 | 9/35 | 6 | 6/6 |

Resume by arm: model_first 12/16, task_only 21/25
Cost: $0.3790

## deepseek/deepseek-v4.1-flash

| Condition | Decisions | Reuse the failing link | Switch | No valid action | Errors |
|---|---|---|---|---|---|
| resume | 50 | 26/50 (52%) | 24 | 0 | 0 |
| hint | 50 | 4/50 (8%) | 46 | 0 | 0 |
| hint_first_step | 50 | 16/50 (32%) | 34 | 0 | 0 |
| nudge | 50 | 3/50 (6%) | 47 | 0 | 0 |
| budget | 50 | 42/50 (84%) | 8 | 0 | 0 |
| reader | 50 | 28/48 (58%) | 20 | 2 | 0 |
| reader_full | 50 | 14/39 (36%) | 25 | 11 | 0 |
| reader_hint | 50 | 6/49 (12%) | 43 | 1 | 0 |

Original runs: 27/50 of these decisions reused the failing link. Decisions with a route around it: 50/50.

| Condition | Paired decisions | Reuse, resume | Reuse, condition | Resume reused, condition switched | Resume switched, condition reused |
|---|---|---|---|---|---|
| hint | 50 | 26 | 4 | 24 | 2 |
| hint_first_step | 50 | 26 | 16 | 13 | 3 |
| nudge | 50 | 26 | 3 | 23 | 0 |
| budget | 50 | 26 | 42 | 3 | 19 |
| reader | 48 | 25 | 28 | 10 | 13 |
| reader_full | 39 | 19 | 14 | 9 | 4 |
| reader_hint | 49 | 26 | 6 | 21 | 1 |

| Condition | Route around fits the steps left | Reuse | Route does not fit | Reuse |
|---|---|---|---|---|
| resume | 37 | 16/37 | 13 | 10/13 |
| hint | 37 | 0/37 | 13 | 4/13 |
| hint_first_step | 37 | 8/37 | 13 | 8/13 |
| nudge | 37 | 2/37 | 13 | 1/13 |
| budget | 37 | 31/37 | 13 | 11/13 |
| reader | 36 | 21/36 | 12 | 7/12 |
| reader_full | 28 | 5/28 | 11 | 9/11 |
| reader_hint | 36 | 0/36 | 13 | 6/13 |

Resume by arm: model_first 13/25, task_only 13/25
Cost: $0.4562

## openai/gpt-5.6-sol

| Condition | Decisions | Reuse the failing link | Switch | No valid action | Errors |
|---|---|---|---|---|---|
| resume | 46 | 29/46 (63%) | 17 | 0 | 0 |
| hint | 46 | 7/46 (15%) | 39 | 0 | 0 |
| hint_first_step | 46 | 37/46 (80%) | 9 | 0 | 0 |
| nudge | 46 | 4/46 (9%) | 42 | 0 | 0 |
| budget | 46 | 18/46 (39%) | 28 | 0 | 0 |
| reader | 46 | 32/46 (70%) | 14 | 0 | 0 |
| reader_full | 46 | 18/46 (39%) | 28 | 0 | 0 |
| reader_hint | 46 | 9/46 (20%) | 37 | 0 | 0 |

Original runs: 27/46 of these decisions reused the failing link. Decisions with a route around it: 46/46.

| Condition | Paired decisions | Reuse, resume | Reuse, condition | Resume reused, condition switched | Resume switched, condition reused |
|---|---|---|---|---|---|
| hint | 46 | 29 | 7 | 23 | 1 |
| hint_first_step | 46 | 29 | 37 | 2 | 10 |
| nudge | 46 | 29 | 4 | 25 | 0 |
| budget | 46 | 29 | 18 | 12 | 1 |
| reader | 46 | 29 | 32 | 7 | 10 |
| reader_full | 46 | 29 | 18 | 14 | 3 |
| reader_hint | 46 | 29 | 9 | 22 | 2 |

| Condition | Route around fits the steps left | Reuse | Route does not fit | Reuse |
|---|---|---|---|---|
| resume | 39 | 23/39 | 7 | 6/7 |
| hint | 39 | 0/39 | 7 | 7/7 |
| hint_first_step | 39 | 30/39 | 7 | 7/7 |
| nudge | 39 | 0/39 | 7 | 4/7 |
| budget | 39 | 13/39 | 7 | 5/7 |
| reader | 39 | 25/39 | 7 | 7/7 |
| reader_full | 39 | 11/39 | 7 | 7/7 |
| reader_hint | 39 | 2/39 | 7 | 7/7 |

Resume by arm: model_first 14/22, task_only 15/24
Cost: $3.1300


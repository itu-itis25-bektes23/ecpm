| Condition | Decisions | Reuse the failing link | Switch | No valid action | Errors |
|---|---|---|---|---|---|
| resume | 41 | 30/41 (73%) | 11 | 0 | 0 |
| hint | 41 | 12/41 (29%) | 29 | 0 | 0 |
| budget | 41 | 25/41 (61%) | 16 | 0 | 0 |
| reader | 41 | 30/41 (73%) | 11 | 0 | 0 |
| reader_hint | 41 | 12/41 (29%) | 29 | 0 | 0 |

Original runs: 33/41 of these decisions reused the failing link. Decisions with a route around it: 41/41.

| Condition | Paired decisions | Reuse, resume | Reuse, condition | Resume reused, condition switched | Resume switched, condition reused |
|---|---|---|---|---|---|
| hint | 41 | 30 | 12 | 18 | 0 |
| budget | 41 | 30 | 25 | 8 | 3 |
| reader | 41 | 30 | 30 | 6 | 6 |
| reader_hint | 41 | 30 | 12 | 19 | 1 |

| Condition | Route around fits the steps left | Reuse | Route does not fit | Reuse |
|---|---|---|---|---|
| resume | 35 | 24/35 | 6 | 6/6 |
| hint | 35 | 6/35 | 6 | 6/6 |
| budget | 35 | 19/35 | 6 | 6/6 |
| reader | 35 | 25/35 | 6 | 5/6 |
| reader_hint | 35 | 7/35 | 6 | 5/6 |

Resume by arm: model_first 11/16, task_only 19/25
Cost: $0.1247

# Stochastic transfer, replicated and paired, 15 September 2026

Two anchor conditions by three draws, six trainings. Each adapter is
evaluated on both the deterministic and the stochastic instances built from
the same 32 seeds, so the drop is paired within adapter rather than
compared across runs.

- `raw_storeplicate.jsonl` one row per reply, n = 384
- `results_storeplicate.jsonl`, `summary_storeplicate.json` one row per run

Produced by `experiments/notebooks/e1_stochastic_replicate.ipynb`. Training
settings match `runs/2026-09-14_qwen2.5-1.5b_e1_phase1_replicate/`.

| condition | deterministic | stochastic | stochastic, node level | mean drop |
| --- | --- | --- | --- | --- |
| A bespoke | 26, 28, 31 | 4, 5, 6 | 7, 7, 9 | 23.3 |
| C off-route mix | 24, 25, 26 | 3, 3, 5 | 6, 7, 6 | 21.3 |

All six runs dropped, by 20 to 25 points, n = 32 per cell.

Reference on the stochastic instances: the evidence-only rule "the pair
that never succeeds in period B" localizes 32/32, and the untrained model
with the evidence in its prompt 3/32.

## Why the task is unchanged

Under noise a healthy link self-loops whenever an attempt misses, so a
median of twelve pairs per period self-loop at least once. The target
remains the uniquely never-succeeding pair in 32 of 32 instances. So the
surface form of the rule, "the pair that self-loops in period B", is false
here, while the robust form still identifies the target and the ceiling is
unchanged.

## What it establishes

Both trained conditions fall to the untrained level. Removing the route
confound makes the deterministic result reliable, see the replication run,
but does not make what is learned any more robust. The improvement phase 1
buys is a surface regularity that is worth nothing once self-loops stop
being diagnostic.

The deterministic figures reproduce those in
`runs/2026-09-14_qwen2.5-1.5b_e1_phase1_replicate/` across two independent sessions.

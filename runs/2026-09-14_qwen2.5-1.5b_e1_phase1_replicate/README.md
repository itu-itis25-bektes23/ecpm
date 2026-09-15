# Phase 1 replication, Qwen2.5-1.5B-Instruct, 14 September 2026

Three anchor conditions by three anchor draws, nine trainings, evaluated on
localization over 32 deterministic `silent_break` instances.

- `raw_replicate.jsonl` one row per reply, n = 288
- `results_replicate.jsonl`, `summary_replicate.json` one row per run

Produced by `experiments/notebooks/e1_phase1_replicate.ipynb`. Anchor draws
are `first_seed` 1000, 2000 and 3000, with the trainer seed varied
alongside, so the anchor draw and the optimization noise move together.
Everything else is held: 40 worlds, 140 examples, deterministic,
`PRES_REPEAT = 1`, `GRAD_ACCUM = 4`, 105 optimizer steps.

| condition | anchors | targets on the optimal route | localization by draw | mean | n per draw |
| --- | --- | --- | --- | --- | --- |
| A | bespoke, `archive/superseded-finetuning-notebooks` | 4/20, 3/20, 2/20 | 26, 28, 31 | 28.3 | 32 |
| B | `anchors_v22.py`, `silent_break` only | 20/20 | 9, 14, 24 | 15.7 | 32 |
| C | `anchors_v22.py`, four `irrelevant` per `silent_break` | 4/20 | 24, 25, 26 | 25.0 | 32 |

Final training loss 0.041 to 0.057 across all nine.

Reference on the same instances: the evidence-only rule localizes 32/32,
and the untrained model with the evidence in its prompt 4/32.

## What it establishes

**Route position accounts for most of the difference between the two
generators.** Condition C uses the frozen generator with the bespoke one's
off-route rate. Under v2.1 `irrelevant` sets its target to p = 0 exactly as
`silent_break` does, so the period-B signature is identical in B and C and
only route position moves. An exact permutation test gives p = 0.050 for A
against B, the smallest value attainable at three draws per condition, and
0.100 for C against B.

**The on-route condition is unstable.** It spans 15 points across draws
where the two off-route conditions span 5 and 2. The confound does not only
lower the mean, it makes training unreliable.

## Supersedes

Two figures reported earlier in September, 32/32 and 7/32, are single draws
from these distributions rather than point estimates. 32/32 is the top of
26 to 31; 7/32 sits below 9 to 24, and the same configuration at the same
draw reran here at 24. Do not cite either alone.

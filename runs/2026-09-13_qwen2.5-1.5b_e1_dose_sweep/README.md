# Phase 2 dose sweep, 13 September 2026

Evidence recall and probe accuracy against phase-2 dose, on one seed, for
both phase-1 adapters. Dose 0 is the phase-1 adapter untouched.

- `raw_dose.jsonl` one row per reply, n = 112

Produced by `experiments/notebooks/e1_phase2_dose_sweep.ipynb`. Two adapters
by seven doses by two arms.

| dose | 0 | 5 | 15 | 25 | 50 | 100 | 200 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| recall, bespoke anchors | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 | 1.00 |
| recall, frozen-generator anchors | 0.00 | 0.00 | 0.06 | 0.38 | 1.00 | 1.00 | 1.00 |

## What it establishes

**The recall gap at 25 steps is a threshold effect, not a difference in
kind.** Both adapters memorise the log completely by 50 steps. That removes
the caveat on `runs/2026-09-13_qwen2.5-1.5b_e1_phase2/`, where recall was
near zero at 25 steps.

**At verbatim memorisation the weights-only arm is still wrong**, in all six
cells at doses 50, 100 and 200 across both adapters. So the failure is not
absorption. At high dose its replies revert to emitting the task header,
which is the collapse seen without any phase-1 adapter, so phase 1 delays
that collapse rather than preventing it.

**Interference in the combined arm is dose-dependent and appears exactly
where memorisation does.** Correct at doses 0 and 5, then locked on a single
wrong answer from 15 onward, with the output format intact throughout.

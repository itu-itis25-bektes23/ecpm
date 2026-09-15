# Finetuning arm bisect, 13 September 2026

A series rather than a single run, kept together because the sequence is
what establishes the result. Provenance for the reproduction failure the
replication runs later settled, not a source of current numbers.

A rebuilt phase 1 scored 5/32 on localization where the August adapter
scored 31/32. Four runs restored one difference at a time.

| step | what was restored | localization |
| --- | --- | --- |
| first rebuild, four conditions and both modes | nothing | 5/32 |
| condition mix | deterministic `silent_break` only | 4/32 |
| optimizer | 140 examples, `GRAD_ACCUM = 4`, 105 steps | 7/32 |
| anchor generator | the bespoke `anchors.py` | 32/32 |

The optimizer step also restored two of the August adapter's three
signatures exactly, detection false on all 64 and preservation at the
all-unchanged constant on all 64. Only localization did not return, which
is what isolated the anchor worlds.

Two follow-ups in the same series tested what that meant. Rebuilding the
anchors from the frozen generator with the bespoke one's off-route rate
recovered most of the gap, which isolates route position as the mechanism.
Running the working adapter on stochastic instances collapsed it to 7/32
while the evidence-only rule stayed at 32/32, which says the learned
regularity is the surface form.

## Files

- `table_single.json`, `table_singlecond.json`, `table_augustopt.json` the
  three superseded graded evaluations, n = 32 seeds each. Their raw replies
  are not kept: 1.6 MB each and superseded by the replication runs.
- `raw_origanchors_arm_c.jsonl` the bisect itself, localization only, n = 32
- `raw_offroute_arm_c.jsonl`, `anchor_mix_offroute.json` the first confound
  test, 24/32 at 4/20 on-route
- `raw_sto_arm_c.jsonl`, `raw_sto_icl.jsonl` the first stochastic transfer,
  7/32 against 32/32 deterministic, n = 32 each

Produced by the notebooks listed as superseded in
`experiments/notebooks/README.md`.

## Do not cite these figures

The replication run showed that single phase-1 numbers are not point
estimates. 32/32 is the top of a 26 to 31 distribution and 7/32 sits below
a 9 to 24 one, with the same configuration at the same anchor draw later
scoring 24. Use `runs/2026-09-14_qwen2.5-1.5b_e1_phase1_replicate/` and
`runs/2026-09-15_qwen2.5-1.5b_e1_stochastic_replicate/` instead.
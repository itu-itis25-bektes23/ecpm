# Phase 2, the `ft` and `combined` arms, 13 September 2026

Qwen2.5-1.5B-Instruct on 8 seeds, each paired with its `no_change` twin, so
16 phase-2 trainings. Evidence in the prompt, in the weights, and in both.

- `raw_phase2_origanchors_arm_c.jsonl` the `arm_c` pass, all four probes
- `raw_phase2_origanchors.jsonl` the `ft` and `combined` arms
- `recall_phase2_origanchors.json` evidence recall per payload
- `table_phase2_origanchors.json` the scored table
- `raw_phase2_highdose_325steps.jsonl` five payloads trained 325 steps
  rather than 25, kept because recall reaches 1.00 there

Total n = 168 replies. Produced by
`experiments/notebooks/e1_phase2_rerun_origanchors.ipynb`, on the phase-1
adapter from the bespoke anchor generator. Phase 2 is 25 steps on one
instance's own evidence, with the adapter rebuilt from phase 1 for each
payload so no instance contaminates another.

| arm | phase-1 | instance evidence in the weights | in the prompt | localization | legal action label | routes valid |
| --- | --- | --- | --- | --- | --- | --- |
| `arm_c` | yes | no | yes | 8/8 | 8/8 | 6/16 |
| `ft` | yes | yes | no | 0/8 | 0/8 | 0/16 |
| `combined` | yes | yes | yes | 4/8 | 8/8 | 3/16 |

Detection and preservation do not move in any arm: sensitivity 0/8 to 1/8,
and preservation within 0.07 of the all-unchanged constant of 0.875 with
the changed pair never identified.

## What it establishes

**Weight-delivered evidence does not establish the task's vocabulary.**
With an empty prompt the model names the right node on all eight seeds and
never a legal action label, answering `A north` on seven of eight. One
memorised wrong answer rather than noise. Every route attempt fails on a
node the world does not contain. Returning the log to the prompt restores
legal labels immediately, 8 of 8.

**Both routes is worse than the prompt alone**, 4/8 against 8/8. Both
contrasts are four-to-zero discordant, p = 0.125, the smallest attainable at
n = 8.

Evidence recall at 25 steps on this adapter is 0.00 to 0.35, median 0.00,
so the `ft` result here cannot be attributed to a usability failure from
these rows alone. `runs/2026-09-13_qwen2.5-1.5b_e1_dose_sweep/` settles that, and the
high-dose file above carries five payloads at recall 1.00 where `ft` is
still wrong.

Localization is n = 8 here where the replication runs are n = 32. The
categorical vocabulary counts do not depend on sample size; the
localization rates do.

# notebooks

Kaggle notebooks for the finetuning arm. Each writes an artifact under
`runs/`. Not runnable in CI: they need a GPU, transformers and peft.

Phase 1 trains a LoRA adapter on throwaway anchor worlds at seeds 1000 and
above, never graded. Phase 2 trains further on one graded instance's own
evidence. The arms are defined in `docs/FINETUNING_ARM.md`.

Everything shared lives in `experiments/`: `gen_payloads.py` builds the
instances, `ecpm_eval.py` runs and scores through `ecpm_parser`,
`anchors_v22.py` builds the anchor worlds, `ft_ceiling.py` computes the
information ceiling, and `test_ft_arm.py` covers all of it.

## Current

| notebook | what it produces | artifact |
| --- | --- | --- |
| `e1_phase1_replicate.ipynb` | three anchor conditions by three draws | `runs/2026-09-14_qwen2.5-1.5b_e1_phase1_replicate/` |
| `e1_stochastic_replicate.ipynb` | the same adapters on deterministic and stochastic instances, paired | `runs/2026-09-15_qwen2.5-1.5b_e1_stochastic_replicate/` |
| `e1_phase2_rerun_origanchors.ipynb` | the `arm_c`, `ft` and `combined` arms | `runs/2026-09-13_qwen2.5-1.5b_e1_phase2/` |
| `e1_phase2_dose_sweep.ipynb` | evidence recall against phase-2 dose, both adapters | `runs/2026-09-13_qwen2.5-1.5b_e1_dose_sweep/` |
| `armc_eval_v22.ipynb` | the graded evaluation, parameterised by `ADAPTER_MATCH` | reused by the above |

## Superseded

The bisect that established why a rebuilt phase 1 did not reproduce the
August result. Artifacts in `runs/2026-09-13_qwen2.5-1.5b_e1_bisect/`.

Their headline figures are single training runs. The replication later
showed 32/32 is the top of a 26 to 31 distribution and 7/32 sits below a
9 to 24 one. Do not cite either as a point estimate.

| notebook | what it established |
| --- | --- |
| `e1_phase1_anchors.ipynb` | first rebuild, four conditions and both modes, 5/32 |
| `e1_phase1_singlecond.ipynb` | condition mix restored, 4/32, so the mix was not the cause |
| `e1_phase1_augustopt.ipynb` | optimizer restored, 7/32, but detection and preservation reproduced exactly |
| `e1_bisect_origanchors.ipynb` | the bespoke anchor generator, 32/32, cause found |
| `e1_confound_offroute.ipynb` | route position isolated as the mechanism, 24/32 |
| `e1_stochastic_transfer.ipynb` | the learned rule does not survive noise, 7/32 |
| `e1_phase2_ft_combined.ipynb` | first `ft` and `combined`, on the adapter later shown broken |
| `armc_eval_v22_2.ipynb`, `armc_eval_v22_3.ipynb` | the graded evaluations for two of the above |

## Adapters

Not committed: about 74 MB each. They are rebuilt by rerunning a phase-1
notebook at the recorded anchor draw. Each carries a
`phase1_provenance.json` naming the run, the anchor source, the optimizer
settings and the final loss, which is the authoritative record of which
adapter produced which result.

# Finetuning Arm - Documentation

**Maciej Zwierzynski**

## Purpose

The passive and active pilots both deliver evidence through the prompt.
This arm asks whether the delivery route matters: does the same observation log support the same answers when it is written into the weights rather than read from the context?

Five arms, differing only in where the evidence sits. Everything else (instances, probes, scoring) is shared with the other pilots.

| arm | phase-1 adapter | this instance's log in the weights | log in the prompt |
| --- | --- | --- | --- |
| `none` | no | no | no |
| `icl` | no | no | yes |
| `arm_c` | yes | no | yes |
| `ft` | yes | yes | no |
| `combined` | yes | yes | yes |

`none` is the floor and `icl` is the untrained reference. `arm_c` isolates what format training alone buys. `ft` asks whether an absorbed log is usable at all, and `combined` whether the two routes add or interfere.

The model is Qwen2.5-1.5B-Instruct in 4-bit with LoRA r16 alpha32 on all seven projections, the largest configuration that finetunes on a free Kaggle T4. That single model is a limitation of the arm, not a choice: nothing here distinguishes a capability threshold from a property of this setup.

## Two phases

**Phase 1** trains on throwaway anchor worlds drawn from the frozen generator at seeds 1000 and above, well outside the graded range of 0 to 79. Its stated job is to teach that a probe question is answered with a JSON object of the right shape. Forty worlds give 140 examples at `GRAD_ACCUM = 4` and 105 optimizer steps. Loss is masked to the gold answer tokens, so the model never learns to recite an evidence log.

**Phase 2** continues from a phase-1 adapter on one graded instance's own evidence, cued with a recall prompt, for a small number of steps. The adapter is rebuilt from phase 1 for each instance, so no instance contaminates another. Evidence recall is measured before the probes, by cueing the model to reproduce the log and counting the observation triples that come back. That separates "did not absorb the evidence" from "absorbed it and cannot use it", which is the distinction the whole arm turns on.

## Quickstart

No GPU needed for anything in this section.

```bash
# instances, regenerated rather than committed
python3 experiments/gen_payloads.py payloads_det --seeds 0-79
python3 experiments/gen_payloads.py payloads_nc --seeds 0-79 --condition no_change

# the archived prompts still reproduce
python3 experiments/gen_payloads.py --validate

# the information ceiling for a condition
python3 experiments/ft_ceiling.py payloads_det

# the arm's own suite
python3 experiments/test_ft_arm.py
```

The notebooks in `experiments/notebooks/` need a GPU and are run on Kaggle. `experiments/notebooks/README.md` maps each to the run directory it produces.

## Modules

- `experiments/gen_payloads.py` builds instances from the frozen
  generator. Every payload carries the full record, so a reply can be
  scored later without regenerating anything.
- `experiments/anchors_v22.py` builds anchor worlds from the same
  generator, with the prompt text taken from `prompts.py` rather than
  copied, so training and evaluation cannot drift apart.
- `experiments/ecpm_eval.py` runs an arm and scores it through
  `ecpm_parser`. Resumable, stamps provenance into every row.
- `experiments/ft_ceiling.py` the arm's own information ceiling. See
  "Two ceilings" below.
- `experiments/test_ft_arm.py` scripted answerers and injected defects.

## Scoring

Everything goes through `ecpm_parser`, the same scorer the other pilots use, so the columns mean the same thing across arms.

Two reporting rules this arm learned the hard way.

**Preservation accuracy is not reportable without its constant-answer baseline.** The queried set holds one changed pair of four, so answering "nothing changed" everywhere scores 0.875. An arm that does exactly that looks strong until the baseline is printed beside it. `ecpm_eval.table` emits `pres_acc`, `pres_const` and `target_recall` together for this reason.

**`bare_json` is a diagnostic, not a score.** The frozen contract (`docs/INTERFACE.md` section 7) takes the first balanced parseable object and ignores prose around it. An earlier local scorer required the whole reply to be one object, and the two disagreed on 16 of 64 preservation replies, all of them valid JSON followed by one stray quote character. The strict rule is kept as a column so a model that needs the leniency is visible, but it does not decide correctness.

## Two ceilings

`ecpm_baseline.py` is the project's null model and answers all four probes by arithmetic over the prompt view. `ft_ceiling.py` was written independently for this arm, covers localization only, and adds an exact posterior under the true generative process, which bounds any method reading only the counts.

They are deliberately not merged. The two agree that deterministic `silent_break` is solved by counting and that the stochastic conditions differ in how much room a model has, and a number reached twice by different routes is worth more than either alone. See the "independent check on the ceiling" section of the top-level README.

Neither covers `redirect`, and cannot: it preserves every success rate, so both are blind to it by construction. That is the point of that condition, and it is the one this arm has not yet run.

## Anchor worlds, and a confound

The anchor generator matters more than it looks. Two versions were compared at matched example count, optimizer settings and condition, and they differ in where the break falls.

| generator | targets on the optimal route | localization, three draws | spread |
| --- | --- | --- | --- |
| bespoke, archived | 2 to 4 of 20 | 26, 28, 31 | 5 |
| `anchors_v22.py`, `silent_break` only | 20 of 20 | 9, 14, 24 | 15 |
| `anchors_v22.py`, mixed cycle | 4 of 20 | 24, 25, 26 | 2 |

The frozen generator places every `silent_break` target on the optimal route, as do all graded instances. Training where route position is uninformative leaves the period-B self-loop as the only usable cue and the model learns it. Training where route position correlates perfectly offers a second cue that requires inferring the route, and both the mean and the reliability suffer.

Cycling four `irrelevant` worlds per `silent_break` world reproduces the off-route rate. Under the current schema `irrelevant` sets its target to p = 0 exactly as `silent_break` does, so the period-B signature is identical and only route position moves.

**Use `anchors_v22.py` with a mixed condition cycle.** It matches the bespoke generator, has a third of the variance, and is built from the frozen environment. The bespoke one is kept only because condition A of the replication uses it.

## What the arm found

Numbers and their `n` live in the run directories; this is the shape.

Phase 1 takes localization from 4/32 untrained to about 28/32, on a task the evidence-only rule solves 32/32. So the gain reaches a ceiling rather than exceeding it.

What is learned is one surface regularity: the broken pair is the one that self-loops in period B. Evaluated on stochastic instances, where a healthy link self-loops whenever an attempt misses and the rule is therefore false, every adapter falls to the untrained level while the evidence-only rule stays at 32/32.

Evidence delivered through the weights does not establish the task's vocabulary. With an empty prompt the model names the right node and never a legal action label, and every route attempt references a node the world does not contain. This is not an absorption failure: at doses where the log is reproduced verbatim it still fails. Returning the log to the prompt restores legal labels immediately.

Having the evidence both ways is worse than the prompt alone, and the interference appears at exactly the dose where memorisation begins.

Detection and preservation do not move in any arm.

## Limits

- One model at one size.
- The arm uses 32 deterministic seeds enumerated in its notebooks rather
  than the 23 matched stochastic seeds in `runs/seed_eligibility.json`.
  Reconciling the two is open.
- Detection and preservation are at n = 8 where localization is at n = 32.
- `redirect` has not been run.
- The localization probe opens by asserting that the dynamics changed,
  which is what detection cannot determine. A premise-free variant has
  never been run, in any arm.

## Reproducing a phase-1 adapter

Adapters are not committed: about 74 MB each. Each carries a `phase1_provenance.json` recording the run name, anchor source, anchor draw, optimizer settings and final loss. Rerunning the notebook named in `experiments/notebooks/README.md` at the recorded draw rebuilds it.

A phase-1 figure from a single training run is not a point estimate. The worst condition spans 15 points across anchor draws, and two figures reported in early September, 32/32 and 7/32, were later shown to be the extremes of distributions. Report a mean and a range over at least three draws.
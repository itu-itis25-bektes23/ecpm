# ECPM: proposed paper spine

Draft for group discussion, not a decision. The aim is to name one claim
the whole project is evidence for, so that each arm has a defined job and
we can tell what is in scope before the write-up starts.

**Revision note.** An earlier draft made the knowing/doing dissociation
the claim. Building the evidence-only baseline showed that a
non-reasoning counter reproduces the dissociation, which makes it a fact
about the task rather than about models. The claim below is the
replacement; the dissociation is retained as motivation.

## The claim

**Measured against an evidence-only null model, LLMs mostly match what
counting alone achieves, sometimes fall below it, and exceed it only
where counting cannot work in principle.**

The dissociation between knowing and doing is the *motivation*, not the
claim. The distinction matters and is the main change from the previous
draft.

### Why the dissociation cannot be the claim

It is real, and we have four independent lines of evidence for it (table
below). But it is largely a property of the task rather than of models,
and our own Gist explains why: planning needs only the period B rates in
the right order, while localization needs a *difference* between periods.
Those are different computations over different inputs, so nothing forces
them to co-occur -- in a model, in a counter, in anything.

The evidence-only baseline demonstrates this constructively. It routes
around the break (zero observed successes means infinite cost) while
naming the wrong pair, holding no representation whatsoever. A finding
that a linear scan over the logs reproduces is a finding about the
evidence.

The decisive objection is that "knowing and doing dissociate" is not
falsifiable as stated. Both cells populated confirms it; an empty cell
reads as sample size. A claim no result can refute is not a claim.

### Why the null-model framing works

It admits a null, so it can be wrong. Three outcomes are distinguishable
in advance and mean different things:

| region | reading |
| --- | --- |
| **above baseline** | the model extracted something counting could not -- the only positive world-model evidence available here |
| **at baseline** | the model is a counter; not a failure, but not a world model |
| **below baseline** | the model had the information and failed to use it |

This turns the project's liabilities into structure. "Deterministic mode
is solved by counting" stops being an embarrassment and becomes a
measured ceiling. Thin evidence stops being fatal, because the claim
needs a comparison against a computable reference rather than a precise
rate.

It also answers the PI's standing objection -- *is this test just
counting?* -- with a measurement instead of a defence: yes, in these
conditions, by this much, and here is the one condition where it is not.

And it earns redirect its place. Redirect is the only condition whose
baseline floor is zero, so it is the only condition where above-baseline
performance is unambiguous. Under the old framing redirect was one more
intervention; under this one it is the experimental heart.

### What this costs

A quieter headline, and a weaker parallel to Vafa et al., whose claim is
closer to the dissociation framing. Vafa becomes motivation and related
work rather than the frame we extend. Both costs are accepted
deliberately.

### Open sub-decision: floor or competitor

As a **floor**, the baseline defines interpretable regions and models are
scored against it; every condition stays informative. As a
**competitor**, it is reported as a system and the finding is that
frontier models do not beat a counter -- sharper, but it invites "your
task is too easy," which only the redirect result answers. This draft
assumes floor. Changing it changes the abstract.

## The dissociation, as motivation

| Source | Evidence |
| --- | --- |
| ICL sweep (Efe) | Gemma 4 E4B, 14 stochastic seeds, k=5: 4 named the link but routed badly, 4 routed well but blamed a healthy link. 8 of 14 off-diagonal. Deterministic 9/5/1/0. |
| Direct interface (Pavlos) | Two frontier models returned the optimal post-change route while failing to localize the break. Planning without updating. |
| Agentic arm (Christian) | Seed 7 silent break, GPT-5.6-sol: all four probes correct, yet broken-link usage after first failure 0.78 and adaptation lag 8 steps. Knowing without acting. |
| Evidence-only baseline | A non-reasoning counter reproduces the same pattern. This is the line that forces the reframing above. |

**The below-baseline case deserves promotion.** GPT-4o named the
deterministic break and then routed straight through it. That is a
failure to use information it demonstrably had, and unlike the
off-diagonal cells it is not explained by task structure. It is currently
one cell in a table and should be a result.

**The baseline reproduces the Gist's hand analysis exactly.** On the
seed-7 stochastic instance the Gist reports that a rate-copying planner
returns the optimal post-break route at cost 7.4594 (regret 0), while the
same visible rates put the largest change on a tie between (B, a1) and
(E, a1), both healthy. Run mechanically, `ecpm_baseline.py` returns that
tie at 0.60 and the route E→A→G→H→B→F, matching
`oracle.post.optimal_route` and `optimal_cost = 7.4594`. The argument in
the Gist was correct and is now executable on any instance.

**Caveat that must travel with the 2x2.** In the Gemma sweep the probes
were asked in separate fresh chats, so the route column measures
post-change planning rather than adaptation relative to a committed
route. This is precisely the gap the two-turn protocol closes, and the
figure should not be presented without it.

## Construct note

The four probes do not measure one thing. Detection, localization and
preservation are *verbal reports*; adaptation is *behaviour*. So the 2x2
measures report-action agreement, not the internal coherence of a
recovered map. Vafa et al. measure the latter. We should commit to the
former and say so, which keeps Christian's coherence branch as the
natural follow-up rather than an unscoped obligation inside this paper.

## What each arm contributes

The three arms are not three versions of the same experiment. Each varies
a different axis over one environment and one probe set, which is what
makes them comparable at all.

- **ICL (Efe)** — varies *delivery within the prompt*: single-turn versus
  two-turn. This arm is what licenses the word "updating"; see scope note
  below.
- **Agentic exploration (Christian)** — varies *the source of evidence*:
  a fixed log collected by an external policy versus the model choosing
  its own actions. Same probes, same scorer.
- **Finetuning (Maciej)** — varies *where the evidence lives*: prompt
  versus weights, plus a combined arm. Also contributes the scripted
  control answerers and the information-ceiling computation.

Read together, they ask whether the departure from the baseline survives
when the model gathers its own evidence, when the evidence is in the
weights, and when the framing gets harder.

Stated honestly, these are not three levels of one factor. The agentic
arm gives the model *causal control* over which evidence exists at all --
an intervention-versus-observation distinction, deeper than "where the
evidence comes from." The finetuning arm asks a memory question:
in-context versus in-weights. They share an environment, a probe set and
a scorer; they do not share a research question. The paper should say
that rather than imply a clean factorial.

## The null model

Under the claim above the baseline is not a control, it is the reference
every result is measured against. It sees exactly what the model sees --
a `prompt_view` at the same rendering and budget -- and answers the same
four probes by arithmetic. `assert_prompt_safe()` enforces that at
runtime.

Localization accuracy of a pure counter, seeds 1-30, collected logs.
`n` is the number of seeds that construct under matched mode for that
condition; ineligible seeds are excluded rather than scored.

| mode | condition | n | K=5 | K=10 | K=20 |
| --- | --- | --- | --- | --- | --- |
| sto | silent_break | 23 | 0.74 | 0.96 | 1.00 |
| sto | degradation | 23 | 0.30 | 0.65 | 0.91 |
| sto | irrelevant | 30 | 0.83 | 1.00 | 1.00 |
| sto | hard_removal | 23 | 1.00 | 1.00 | 1.00 |
| det | all conditions | 23-30 | 1.00 | 1.00 | 1.00 |

Deterministic mode has no headroom: a counter solves it. Stochastic
silent break is solved by K=10. Among the original five conditions the
only cell with room is stochastic degradation at K=5 and K=10 -- and
redirect (see Scope) is the only one with a floor of zero.

This is the central result, not an obstacle. It says precisely where a
model result is interpretable, and it makes the project's own rule -- no
claim that a model "cannot localize" unless the baseline can --
enforceable rather than aspirational.

**K is not a nuisance parameter.** The table shows K setting how much of
the answer is present in the logs, which makes it an independent
variable. Any result at a single K is one point on a curve and should be
reported as such.

## Figures

1. **Baseline ceiling by condition and K**. The reference frame. Leads,
   because every later figure is read against it.
2. **Model performance relative to the null**, per condition: above, at,
   or below. The finding.
3. **Knowing crossed with doing** (exists). Now the motivation, shown
   with the baseline's own 2x2 beside it to make the deflationary reading
   explicit and then answered.
4. **Updating versus planning**. Turn-1 route against turn-2 route,
   single-turn arm against two-turn arm on matched instances.
5. **Belief versus action**. Turn-2 stated beliefs against turn-2 route.
   The agentic arm supplies the sharpest version: correct probes, 0.78
   broken-link usage.

## Hypotheses, reframed

At n=14 the Wilson interval runs roughly 0.21 to 0.67, which cannot
support a point threshold. Stated as contrasts instead:

- **H1 (above).** On redirect, model localization exceeds the baseline by
  a margin. This is the only condition where the baseline floor is zero,
  so it is the cleanest test of the claim.
- **H2 (at).** On silent_break at K>=10, model localization does not
  differ from the baseline by more than a margin -- i.e. the model is
  behaving as a counter.
- **H3 (below).** There exist conditions where model localization is
  correct and the route still uses the changed link, at a rate above
  zero. Failure to use information demonstrably held.
- **H4 (delivery).** The two-turn arm differs from the single-turn arm on
  matched instances, in the direction of lower apparent adaptation --
  i.e. part of single-turn "adaptation" was planning.
- **H5 (specificity).** False-alarm rate on `no_change` is below the
  detection rate on `silent_break` by a margin, for both model and
  baseline.

Each is a contrast against a computable reference, so each can fail.

**Both-modes rule: proposed for retirement.** The old rule accepted a
verdict only if it held in deterministic and stochastic mode. With
deterministic at ceiling on five of six conditions, that rule now
discards findings rather than protecting them -- and the two modes are
not two settings of one task: deterministic is logical inference (one
failure proves a break), stochastic is statistical inference from a
sample. Proposal: report mode as a condition and let the reader see where
each result holds. Retained unchanged: no model rankings from three
seeds.

**Preservation needs splitting or cutting.** Over-reporting and
under-reporting land in the same score band -- Gemma scored 0.50 with a
right diagnosis plus collateral damage, GPT-4o scored 0.75 by marking
nothing changed and missing the break. One number is collapsing
sensitivity and specificity. Report the pair, or drop the probe.

## Delivery is a measured contrast, not a choice

Single-turn is retained as a **comparison condition** on the same seeds
and the same K, not as a legacy arm.

Run alone, two-turn shows whether a model updates. Run as a matched pair,
the difference between the arms measures how much of any apparent
updating was really planning from period B. A model shown both periods at
once can route around a break it never noticed; the Gemma sweep and
Pavlos's direct-interface runs both did exactly that. Without the paired
arm, "single-turn measures planning" is an argument. With it, it is a
number.

At ~$18 for 23 seeds at K=10 this is the cheapest claim in the budget.

## Budget

Anchored on measured usage: the archived Azure run used 5413 prompt and
220 completion tokens for one four-probe single-turn conversation at
K=5. Priced at $2.50/$10 per 1M (gpt-4o). See
`experiments/azure_budget.py`.

| plan | instances | cost |
| --- | --- | --- |
| ICL single-turn, 23 seeds, K=10 | 759 | $17.63 |
| ICL two-turn, 23 seeds, K=10 | 759 | $42.07 |
| ICL two-turn, 3 seeds, K=20 | 99 | $9.05 |
| Agentic, 1 seed, 3 conditions | 9 | $28.37 |
| **total** | | **$97.12** |

Against a $100 slice this leaves no rerun reserve, which is unwise: the
K=5 pilot lost 4 of 4 route answers to a prompt wording bug. Either drop
the K=20 slice (total $88) or draw on the full $199.97 credit, which
leaves $103 for a second model and the wider agentic sweep.

The agentic arm is ~100x an ICL conversation per instance (about 200 LLM
calls against a growing context), so it gets width only if the credit
allows.

## Readiness

What the spine needs, against what exists in the tree today. "Collection"
means it affects the artifacts and must be right before spending credit;
"analysis" means it is a pure function of stored artifacts and can be
added afterwards without rerunning anything.

| component | state | stage |
| --- | --- | --- |
| Environment, 6 conditions incl. redirect | 100% | collection |
| Frozen parser and probe scorers | 100% | collection |
| Two-turn elicitation (7 phases) | 100% | collection |
| Self-consistency preservation | 100% | collection |
| Evidence-only baseline + ceilings | 100% | analysis |
| Artifact completeness (paths, beliefs, usage) | 100% | collection |
| Adaptation prompt wording | **0%** | **collection — blocker** |
| Repeated sampling (`--samples`) | 0% | collection |
| Named scenario for redirect | 0% | collection (cosmetic) |
| Updating-vs-planning contrast | 0% | analysis |
| Belief-vs-action contrast | 0% | analysis |
| All-four-correct / 2x2 corners | 0% | analysis |
| Hypotheses as contrasts + Wilson | 0% | analysis |
| Cross-artifact aggregation | 0% | analysis |

Roughly: **collection is ~85% ready, analysis is ~15% ready.**

That asymmetry is the right shape to be in. The artifacts already store
`route_pre.scored.path`, `adaptation.scored.path`, per-pair beliefs, and
provider usage, so every missing metric is recoverable from runs done
today. Credit spent now is not wasted by the analysis layer arriving
later.

Two items break that rule and must land first:

- **The adaptation prompt wording bug.** It corrupts collection, not
  analysis. It cost Sonnet 4.6 and GPT-4o all four route answers in the
  pilot. Running at scale before fixing it buys format errors.
- **Repeated sampling.** Without it, model stochasticity is recorded as
  "the model failed," and no rerun recovers the missing samples.

## Where the evidence is thin

Not in coverage -- every arm has a job and the dissociation has four
independent lines of support. In depth:

- Almost every cell is n=1.
- The two-turn protocol, which is what licenses the word "updating," has
  produced exactly one comparison: seed 7, Gemma, single instance,
  deterministic only.
- The agentic arm has 3 of 6 conditions, one model, one mode, one sample.

So the claim is well-supported as a **phenomenon** and unsupported as a
**rate**. The paper should say so, and the budget above is shaped to
attack depth rather than breadth.

The null-model framing is deliberately tolerant of this. It needs each
model result compared against a computable reference on the same
instance, not a precise population rate -- which is why the ceiling table
and the below-baseline case are already publishable on data in hand,
while the Azure runs strengthen the claim rather than constitute it.

## Scope

**In.** The three arms. Six interventions. Both modes. Both delivery
modes as a matched pair. The baseline.

**Redirect is now implemented** (v2.3). Proposed by Sruthi and accepted
in the Gist as intervention 6. It joins the break family, so it edits the
same T* that silent_break and hard_removal do for a given seed, keeps
that link's success probability, and moves only its destination. The
action menu is byte-identical across periods. Eligible on the same 23 of
30 seeds as the break family, in both modes.

Its value is visible in the ceiling table: it is the one condition a
counter cannot solve, and unlike the low-K cases, more evidence does not
help.

| mode | condition | K=5 | K=10 | K=20 |
| --- | --- | --- | --- | --- |
| sto | redirect | 0.09 | 0.00 | 0.04 |
| sto | silent_break | 0.74 | 0.96 | 1.00 |
| det | redirect | 0.00 | 0.00 | 0.00 |
| det | silent_break | 1.00 | 1.00 | 1.00 |

In deterministic mode every rate stays 1.0, so every pair ties at zero
change and the baseline has no signal whatsoever. This makes redirect the
only condition where beating the baseline demonstrates something that
counting cannot do, and the only one that gives deterministic mode any
headroom at all.

**Out, and said so in the paper.** Vafa-style coherence metrics are a
different measurement philosophy and belong in an appendix or a
follow-up. The bandit / exploding-arm replication, plasticity and
catastrophic forgetting, and curriculum learning are future work.

Saying what is out of scope is normal and costs nothing. Trying to cover
all of it is what leaves the paper without a claim.

## Attribution

Environment, schema, parser, frozen harness, official pilot runs,
exploratory kit, sweep: Efe. Independent freeze and pilot review (five
corrections), exploratory direct-interface runs: Pavlos. Agentic
exploration arm: Christian. Finetuning arm, scripted control answerers,
information-ceiling computation, start/goal scoring fix: Maciej.
Redirect intervention and the reporting-versus-acting 2x2: proposed by
Sruthi.

## Decisions this draft assumes

Each of these changes the paper if reversed, so they should be agreed
rather than inherited:

1. **Claim = null-model framing**, dissociation demoted to motivation.
2. **Baseline is a floor**, not a competing system.
3. **Construct = report-action agreement**, not map coherence. Vafa is
   related work; the coherence branch is the follow-up.
4. **Both-modes rule retired**, mode reported as a condition.
5. **Preservation split into sensitivity/specificity**, or cut.
6. **Below-baseline promoted to a result** (GPT-4o naming the
   deterministic break and routing through it).

## Open items

- **Two scorer bugs were found while building redirect, and fixed.**
  Both were latent: harmless for the five conditions that reweight an
  edge in place, wrong as soon as one moves. (a) `invert_labels` was
  period-blind, so under redirect one action label mapped to two edges
  and the inversion kept whichever it saw last -- resolving a Period A
  route with the Period B destination. It now takes a world.
  (b) `score_adaptation` walked the Period B route on the Period A
  destination map; it now prefers Period B and falls back to Period A so
  hard_removal still reports `illegal_action` rather than
  `unknown_reference`. Existing artifacts are unaffected: the frozen
  example records still regenerate byte-identically, and `new_edge` is
  emitted only for redirect so no pre-existing record changes.
- **Redirect is not yet in the named scenario table** in `run_pilot.py`.
  It runs today via `--condition redirect`; a named scenario should be
  added when PR #5 lands, to avoid a conflict in the file that PR
  restructures.
- **The adaptation prompt has a known wording bug.** One sentence causes
  models to append a step at the goal node, which the grader rejects.
  It cost Sonnet 4.6 and GPT-4o all four of their route answers in the
  pilot. The corrected wording is drafted in the Gist and must land
  before any main run, or the Azure budget buys format errors.
- **The agentic metric definitions are unwritten.** The Metrics section
  of the agentic doc says "To be written," so "broken-link usage after
  first failure = 0.78" is being read as *used the broken link on 78% of
  opportunities after it first failed*. That reading carries a load-
  bearing claim in the table above and needs confirming before it goes in
  the paper.
- **Single-turn results measure planning, not updating.** A model shown
  both periods at once can route around a break it never noticed. This
  must be stated plainly or a reviewer will find it.
- **Route numbers predating Maciej's start/goal fix are void** (the old
  eval hard-coded start E and goal F; the graded seeds have 19 distinct
  pairs). The results sections of the methodology doc need regenerating.
- **Seed eligibility is unreconciled**: the doc says seeds 13 and 25 pass
  all three stochastic conditions; the runs use 1, 4, 10. Either rerun or
  document which criterion was relaxed.
- **One sample per instance.** Model stochasticity is currently scored as
  "the model failed." Needs three or more.
- **PRs #5 and #6 are unmerged**, and #5 restructures `run_pilot.py`,
  which blocks the remaining harness work.

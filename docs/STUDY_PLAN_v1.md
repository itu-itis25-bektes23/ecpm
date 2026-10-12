# Confirmatory study plan v1

This plan is fixed before the confirmatory round. It is tagged `study-plan-v1` on team main, and `study_round.py` refuses the confirmatory round without that tag. Exploratory rounds may run before the tag and may change anything below. The exploratory evidence that motivates the plan is on main: the five-graph grids, the earlier confirmatory grids (seeds 31–130), and the reuse pilot (`runs/results/pilots/reuse_pilot/`).

## 1. Question

Language models that act in a world that changes notice the change and can say so. Do they act on it? If not, why not, and what repairs it? The study answers this with one standardized grid grown from the existing setup.

## 2. Seeds

`runs/study_v1_seeds.json` holds the seed lists, with their provenance.

| Range | Role |
|---|---|
| 1–30 | **Exploratory.** Ten seeds: the five graphs of the earlier exploratory grids (8, 13, 25, 0, 1) plus the first five other seeds that pass `seed_eligibility.py` in the stochastic run set (4, 5, 7, 9, 10). The live gate also uses seed 8. |
| 31–130 | **Earlier tests.** The two-turn tests, the H4/H6 grids and the pilot used these seeds. The new claims came from them, so they are not used here. |
| 131+ | **Confirmatory.** The first 51 seeds that are eligible for every condition in both modes (145 to 499). No earlier run used them. |

**Why 51.** C1 repeats the earlier H4 test, so 51 seeds, the earlier power-based size, makes it a same-size replication on new graphs. The power of C2 and C3 at 51 seeds is given in Section 7.

## 3. Design

**Fixed throughout.**
- **World:** the eight-node family.
- **Models:** GPT-5.6 Sol, Claude Haiku 5.5 and DeepSeek V4.1 Flash, all through OpenRouter.
- **Reasoning:** off, with the control sent and recorded.

**Eleven cells.** There are six kinds of change: no change, irrelevant, silent break, hard removal, redirect, and degradation. Each runs in deterministic and stochastic mode, except degradation, which is undefined when every link works with probability 1. That gives 6 × 2 − 1 = 11 cells. The deterministic mode makes one failure proof of a break. The stochastic mode needs statistics.

**Acting family.**
- **The runner:** the agentic runner, 4 M0 and 4 M1 episodes, H = 20, the change not announced, output caps as in the earlier grids.
- **Factors:** the prompt (task-only, model-first or graph-given), the cell (11), and the nudge (off or on).
- **The nudge:** this exact sentence at the end of the system prompt: "When an action keeps failing, consider trying actions or routes you have not tried yet." It is recorded in every artifact.

**Reading family.** Expanded ICL at K = 10, with the arms task-only, model-first and graph-given, both history settings, and all 11 cells. Each model uses its OpenRouter profile with a validated config and one preflight (`experiments/study_icl.py`). Prompts are byte-identical to the earlier expanded-ICL runs.

**Bridge.** It uses every acting run with the nudge off, stochastic silent break, and prompt task-only or model-first. The decision is the first one at the changed node, in an M1 episode, after the changed link failed six times in a row. A fresh model of the same family reads (a) the agent's own observations and (b) a log covering every link before and after the change, built as in the ICL arm, and names the next action. The settings are those of `experiments/reuse_pilot.py`: temperature 0, one sample (`experiments/bridge_probes.py`).

**Data kept.**
- **Acting runs:** full transcripts, a snapshot of both worlds, and per step the reply, the reasoning text, the history trimming, the call time and latency.
- **Reading runs:** every request and response.
- **Archives:** every raw run is zipped per round.

## 4. Confirmatory claims

Each claim is one-sided and tested per model, except C3. Analysis: `experiments/study_analysis.py`.

| Claim | Measure | Test |
|---|---|---|
| **C1, the phenomenon.** After six consecutive observed failures of the changed link, agents choose it again. | Acting, task-only, nudge off, stochastic silent break and degradation. Among runs that reach six consecutive failures of the changed link in M1, the share that choose it again. This is the measure of the earlier H4. | Share > 0.10. One-sided Wilson lower bound, Bonferroni across models. Tested only with at least 10 qualifying runs. |
| **C2, the fix.** The nudge prevents runs from reaching six consecutive failures. | The same prompt and cells. Whether a run reaches six consecutive failures of the changed link, nudge on against off, paired by seed and cell. The measure is unconditional, because the nudge itself changes which runs reach six failures. | Exact one-sided McNemar test on the discordant pairs, Holm across models. |
| **C3, the bridge.** Complete evidence lowers retrying at the same decision. | Bridge decisions, all models pooled: choosing the failing link with the complete log against with the agent's own log. | Exact one-sided McNemar test. Per-model counts are reported descriptively. |

## 5. Secondary analyses, named in advance and reported descriptively

- **The cost of the nudge.** Under no change and irrelevant: M1 goal success, mean steps and regret, with the nudge on minus off, paired, with 95% intervals. A drop in goal success of more than 0.10 is reported as a cost.
- **What models notice.** Detection and localization by cell and prompt in the acting family, and by cell and arm in the reading family, read against the four evidence-only references on the same prompt views.
- **Exposure.** Detection and localization in runs that met the changed link against runs that did not.
- **C1's measure under model-first and graph-given,** and with the nudge on.

## 6. Rules

- **Before running.** The confirmatory round runs once, after the tag, with a live gate on an exploratory seed and a budget cap.
- **No early analysis.** No analysis of confirmatory runs before all families finish.
- **Failures.** A transport failure is rerun. A returned answer is never re-asked. Unparsable answers count as wrong in the reading family's strict score, which stays primary. The content re-score is secondary.
- **Deviations.** Any deviation from this plan is recorded with its reason.

## 7. Power at 51 seeds

The power figures come from simulation, with rates taken from the earlier grids and the pilot.
- **C1.** Earlier grids showed 57 to 90 percent on 14 to 31 qualifying runs per model, so the lower bound clears 0.10 with ample margin.
- **C2.** Assume a run reaches six failures with probability 0.40 with the nudge off and 0.15 with it on, over 102 seed-cell pairs per model. Power is 0.96.
- **C3.** Assume about 20 decisions per model and that 37 percent of decisions are discordant, of which 80 percent go towards switching, as in the pilot. Power is 0.87 pooled. Per model it is 0.18, which is why per-model results are descriptive.

## 8. Size and cost

**Exploratory round.**
- About 1,980 acting runs and 1,980 reading conversations.
- About 1 to 1.5 hours with the parallel launcher, and roughly $150 to $250.
- Budget cap: $250.

**Confirmatory round.** About 5.1 times the exploratory size. Its budget cap is set before it runs.

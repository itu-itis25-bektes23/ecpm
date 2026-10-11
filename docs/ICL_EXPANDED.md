# Expanded passive ICL

`icl_expanded_v2` compares explicit model construction with other ways of using
the same evidence. Earlier protocols and saved results remain separate. This is
an offline design, not a declaration of live deployment readiness.

## Five arms

All arms receive the same current action menu, shuffled single-step observations,
system rules and task format. Only graph given names the system as a graph and
supplies its true transitions: A before the A tasks and the updated B graph before
the B tasks, alongside the same observations.

| Arm | Before the task questions | Responses per two-period conversation |
| --- | --- | ---: |
| `model_first` | Construct a model, using any useful representation. | 6 |
| `task_only` | Restate rules and output format; do not interpret observations or solve questions. | 6 |
| `spontaneous` | Write useful notes, without an explicit model request. | 6 |
| `graph_given` | Receive the current graph and the same neutral instruction as `task_only`. | 6 |
| `baseline_task` | Answer tasks directly, without a preparation response. | 4 |

The four preparation arms share an approximate 250-word target and the same
16,384-token default response allowance, or an explicit matched 32,768-token
allowance for a separate cohort. Historical 4,096-token runs retain
their recorded allowance and separate identities. Rules and task format appear before preparation;
specific route queries appear in the task request. There is no step-by-step
counting procedure. A word target does not guarantee equal generated tokens or
reasoning effort, so actual words and usage are saved. Baseline intentionally has
one less response per period.

Preparation policy `five_arms_scoped_preparation_v3` labels the current turn as
preparation and scopes route-answer JSON requirements to later task-answer turns.
The open model representation, neutral preparation instruction and approximate
250-word target are unchanged. JSON representations are still allowed; task-answer
JSON is not the required preparation format. There is no added solution procedure.
Task/readout questions, history-retention rules and scorer `icl_expanded_rows_v3`
are unchanged. Rendered histories acquire the newly scoped preparation text.

Earlier `five_arms_length_target_v2` prompts remain reproducible at commit
`96cdd374b1d9acceb30096de4df929bb8cdabe34`. Keep their results separate from this
policy; use the corresponding historical checkout to audit them. New readiness
wrappers must name the new preparation policy and recheck context capacity.
Do not relabel historical records or retry preparation noncompliance.

For a read-only pilot format review, without rescoring, use an unused output path:

```sh
python3 -B experiments/preview_icl_expanded.py \
  --review-preparation /path/to/pilot.zip --out /tmp/preparation-review
```

This flags whole-response JSON containing only empty routes and optional change
fields during preparation. Missing responses remain visible; an unflagged answer
is not a compliance pass. It neither changes scores nor triggers retries.

## Sequence and history

Each period has preparation (except baseline), task questions, then a structured
transition report. Tasks ask for four routes. B also asks whether anything changed
and which pair changed. Reports cover every pair in the union of the A/B menus:
availability, destination and success probability, plus a changed label in B.

- `retained_reports_v2`: every question and exact final answer stays in the main
  conversation. B sees A's report, including malformed text.
- `separate_reports_post_task_v1`: the report uses a copy of current post-task
  history. Its exchange is never added to the main conversation. B sees A's
  preparation and tasks, but not A's report.

Both variants are evaluated separately. Copies replay supplied messages and final
answers, not private provider reasoning. Preservation compares A/B reports in
either case; separate history measures consistency between readouts rather than
retention of a report B was shown.

## Worlds and queries

Use seeds 8, 13, 25, 0 and 1 in the frozen eight-state environment. Deterministic
and stochastic modes have separate system prompts. Both support no change,
irrelevant change, silent break, hard removal and redirect. Degradation is
stochastic only. Sampling variation alone is not a true environment change.
The earlier unique-optimum gate is not used.

Main evidence budget: K=10 observed attempts per available action per period,
evidence seed 0. Removed actions have no B attempts. K is a sample size, not a
probability or the number of route trials. Higher budgets are deferred: K=20
does not reach coverage for seed 0 within the frozen collection limit. It is
rejected before planning or running this study, rather than silently dropping
that graph or changing the generator.

Four route queries use only A information and remain fixed in B and across arms,
histories, modes and scenarios for a seed. One is the anchor start/goal. Three
more use deterministic seeded selection, ensuring at least two canonical A
optimal routes use the planned intervention pair and at least one avoids it.
Selection covers relevant and irrelevant planned pairs, never B outcomes.
The generator's irrelevant-change label refers to its original start/goal;
other balanced queries can use that pair. Interpret relevance per query.
These are balanced queries, not unrestricted random route samples. Tied optimal
routes are accepted; alternate optima can avoid the pair. Actual submitted A
routes therefore determine updating eligibility.

## Scores

The final audit uses scorer `icl_expanded_rows_v3`. Replanning compares
reachability and state/action steps, so an extra JSON annotation cannot create
a route change. Extra fields still fail the separate format check. Older
scorer identities remain separate; do not rewrite their saved scores.

Routes use the true current system: validity, optimality, cost and regret, plus
correct no-route answers. Invalid routes have null cost/regret. Detection and
Localization use actual changes; no-change localization is null.
`route_solution_correct` means a feasible goal-reaching route or a correct
no-route answer. It does not require shortest cost. Use `route_optimal` for
the legacy per-query flag. For tables, `route_optimal_solution` combines
optimal routes with correct no-route answers over all queries;
`route_optimal_reachable` includes only truly reachable queries; and
`route_correct_no_route` includes only truly unreachable queries. The CSV also
exports `route_oracle_reachable`. Malformed answers remain failures within the
appropriate denominator. These columns consume saved route scores.

Structured reports retain row-level availability, destination, probability,
full-graph exactness and probability MAE. Stochastic probability tolerance is
0.15; deterministic tolerance is zero. Tolerance is a scoring convention, not a
change threshold. Errors against visible estimates and true probabilities remain
separate. Malformed values fail all-pair scores; conditional metrics retain their
scored denominators. A conditional metric with no scored values is null, not a pass.

Preservation uses four truly unchanged controls. Self Preservation requires B
values to match A and be labelled unchanged. Truth Preservation compares B with
the actual system separately. Exact and tolerant versions retain all-control and
conditional denominators. A preserved wrong belief is not correct knowledge.

Preparation extraction detects transition tables, grouped lists and JSON rows,
then scores explicitly stated destinations and probabilities. It does not infer
probabilities or grade prose quality. Unsupported, incomplete or conflicting
extraction is marked for review, with raw answers and truth rows in
`preparation_review.json`. It is not silently counted as absent or correct.
This secondary measurement never gates task scores. Report extraction coverage
and unreviewed counts. Also inspect neutral preparation for unwanted transitions.

Updating uses the model's own valid A route. A necessary update is eligible only
if that route used a truly changed pair and would be invalid or suboptimal in B.
Success requires a different, optimal B solution or correct no-route answer.
Malformed B stays a failure in this denominator. If A avoided the changed pair,
correct B routing alone is not evidence of updating. Degradation can leave the
old route optimal. For A-optimal routes still optimal in B, report unnecessary
route changes and harmful changes separately; another equally good route is not
harmful. Eligibility and unscored counts accompany rates.

## Offline use

From the repository root, use stdlib Python 3.11 or 3.12 and unused output paths:

```sh
python3 -B test_icl_expanded.py
python3 -B experiments/preview_icl_expanded.py --coverage --out /tmp/expanded-review
python3 -B run_pilot.py --protocol icl_expanded_v2 \
  --condition silent_break --seed 8 --mode det --k 10 --budget 10 \
  --model-first-condition model_first --history-policy retained_reports_v2 \
  --request-profile gemma_e4b --reasoning-mode off \
  --repeats 1 --sampling-seeds 0 --max-tokens 16384 \
  --provider dry-run --tag expanded_synthetic
python3 -B experiments/preview_icl_expanded.py \
  --summarize pilot_artifacts/expanded_synthetic --out /tmp/expanded-results
```

Exports use saved scientific scores after a fresh operational audit. Operational
failures are quarantined; model errors in valid runs stay in denominators.
Metrics and request-usage CSVs include arm, history, mode, scenario, model, graph,
K, reasoning and repeat. Identities prevent incompatible pooling and duplicate
repeats. Within-configuration sample standard deviations use scored repeat
values; one observation has null standard deviation. Repeats are not independent
graph samples.

Coverage supplies oracle references and prompt/history hashes. The unchanged
published rate/menu detector with empirical planning remains explicitly not
redirect-aware. This does not imply that all counting methods miss redirects.
Synthetic answers verify the pipeline, not model performance or live OFF/ON.

## Before live runs

Start with one repeat per admitted block; support five repeats for a planned
expansion. Sampling labels 0 through 4 are sent only with verified support.
Existing Gemma settings are not greedy and are not silently replaced. OFF/ON
require verified controls and distinct identities.
The current `sol` profile identifies `gpt-5.6-sol`, uses reasoning effort `none`
or `medium`, and omits temperature, top-p and seed in both modes. This does not
establish greedy sampling. A catalogue entry for another Sol version is not an
admitted deployment. `deepseek_openrouter` is a separate expanded-only profile;
see [OpenRouter deployment and pilot commands](ICL_OPENROUTER.md). Kimi has no
profile here. Do not substitute models through Sol or Gemma. Resolve the common sampling
policy from verified deployment capabilities before launching comparisons.

`--plan-profile PROFILE --config VERIFIED_CONFIG --k 10 --repeats 1 --out DIR`
prepares only combinations admitted by non-secret readiness wrappers. Wrappers
contain `deployment` and `expanded`, including protocol, preparation policy,
history, reasoning, schedule, allowances and system/context provenance.
Freeze the reviewed commit, verify actual context admission and mode controls,
and set a cost limit using verified prices. Save every raw request, final answer,
exposed reasoning, usage and available cost evidence. Estimates, cache counts and
provider billing remain separate; unknown values remain null.
New expanded CLI runs default to 16,384 per response, in both modes and all stages.
Explicit `--max-tokens 32768` supports a separate cohort, with the same allowance
in OFF and ON. Its readiness wrapper must record `output_allowances: [32768]`
and `control_preflight_output_tokens: 16384`. The retained control preflight
stays byte-for-byte 16K evidence, not a completed 32K test. Deployment output
capacity must admit 32K; every actual full conversation is checked with 32K
reserved for completion. Unknown hosted overhead remains unknown. The opt-in
OpenRouter estimate still uses UTF-8 bytes plus 4,096 units per message and a
25% context admission limit. No history is trimmed. A longer allowance does
not guarantee completion; length finishes, missing final answers and invalid
token accounting still stop the run without retrying.
Explicit `--max-tokens 4096` remains available for historical reproduction, not
the new pilot. Allowances are included in identities, audits, costs and exports;
do not pool different limits. Earlier protocols retain their original defaults.
The reviewed v3 4K source tree at `05df38907307ec290ede76998f50a6fb1318b4fd`
can be audited with this version only when recorded source hashes match that Git
tree exactly. The same pinned-source rule admits 16K artifacts from
`a2a0340eee721af5eb3152adfcb2262de7ef22fc` and
`a3e32493ad8a10e960a5b5abff3434053e020cb9` only at their original allowance.
Other historical versions still require their original checkout. A completed
16K run never counts as a completed 32K cell. Keep earlier failed responses and
budget reservations unchanged when planning a fresh matched pair.
Pricing calculations use the supplied uncached input and completion rates.
If a deployment has long-context or other tiered rates, use verified conservative
rates covering the entire planned input range for the ceiling. Treat the resulting
amount as an estimate; reconcile tier, cache and reasoning usage with provider
billing separately. The ceiling excludes deployment preflight calls.

This extension is passive ICL only. Larger graphs and agentic integration are
separate follow-ups.

### Optional bounded recovery

`icl_bounded_recovery_v1` is an exploratory amendment motivated by pilot
failures, not a preregistered rule. It starts every stage at 32K and permits
one identical-history repeat at 64K only after an explicit length finish.
Two transient retries are allowed, with at most four HTTP attempts per stage
and a 30-minute timeout per attempt. Wrong or malformed stop answers are not
retried. Truncated preparation is diagnostic only, never replayed as an answer.

ON denotes a supported reasoning-enabled request. Zero and missing reasoning
counts remain distinct observations, not exclusion criteria. OFF reasoning
channel contradictions still stop dispatch. Raw token-accounting anomalies
are flagged; invalid derived counts are null. Historical acceptance remains
unchanged. Reports distinguish policy, actual caps and recovery attempts.

[The serial recovery launcher](../experiments/run_icl_recovery.py) reserves
each request durably under one cumulative budget, preserves unknown charges,
and exports cell, conversation-attempt and HTTP-attempt records. Terminal
cells do not block independent cells or requeue on restart. Authentication,
identity/control, evidence, budget and repeated systemic failures pause new
dispatch. Uncertain interrupted requests remain reserved and are not replayed.
Four-worker execution is not implemented. Private configurations and ledgers
remain outside Git; use a pinned clean commit and the existing private manifest.
See [final run readiness](FINAL_RUN_READINESS.md) for the boundary between this
ICL lock and the existing agentic workflow.

Implementation: [adapter](../icl_expanded.py), [preparation extraction](../icl_preparation.py),
[runner](../icl_model_first_runner.py), [reporting](../experiments/preview_icl_expanded.py)
and [tests](../test_icl_expanded.py).

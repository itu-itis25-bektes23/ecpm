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
historical default 4096-token response allowance. New Sol ON runs can explicitly
select 16384 or 32768 tokens as described below. Rules and task format appear before preparation;
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

## Optional Sol request-defined ON acceptance and output allowance

For new expanded Sol ON runs only, set
`expanded.reasoning_acceptance_policy` to `sol_request_defined_on_v1` in a
copy of the verified deployment wrapper. Omit it for all other profiles/modes.
Existing exact-model support evidence for `reasoning_effort=medium` remains
required. No endpoint or sampling changes are implied.

For new Sol ON runs, use `--max-tokens 32768` and
`expanded.output_allowances=[32768]`. Explicit 16384 is also supported, with
the same value in the CLI and wrapper. Historical 4096 execution remains
supported. No automatic escalation, retry or response repair is added.
Set `expanded.control_preflight_output_allowance=8192` and provide
`expanded.experiment_allowance_source` explaining the saved deployment's
capacity evidence and reuse of the original 8192-token control preflight.
Do not edit that preflight request, response or usage. A short preflight
verifies controls, not long-output stability or future-history capacity.

The saved effective maximum output capacity must cover the selected allowance.
Each actual full conversation is checked with that output reserve before
generation; returned prompt usage plus the same reserve must fit the context.
History is never trimmed. Plans, costs, identities and exports record the
selected experiment allowance separately from the preflight allowance.

This policy accepts a supported medium-effort request even when the provider
reports zero reasoning tokens or omits the count. It does not claim observed
reasoning in those cases. Missing counts stay null, and the original
`control_check` stays unchanged. Each turn records a separate
`reasoning_acceptance` decision, checked against the original envelope and
request by the offline audit. Contradictory controls, invalid counts, blank
answers, length finishes, transport failures and context failures still fail.
Malformed nonblank answers remain scored format failures, not reasons to retry.

The policy is recorded in run identity and wrapper hashes, separating new runs
from the default positive-reasoning policy. Preserve and audit historical runs
with their original implementation; do not relabel interrupted conversations as
completed or invent their unsent stages. This change adds no recovery launcher,
retry, automatic token-limit increase or budget policy.

Offline regression against an original saved ON archive (no extraction or calls):

```sh
python3 -B test_sol_on_acceptance.py --on-archive /path/to/scoped_v3_pilot_on.zip
```

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
  --repeats 1 --sampling-seeds 0 --max-tokens 4096 \
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
admitted deployment. DeepSeek and Kimi do not yet have request profiles here;
do not run them through a Sol or Gemma profile. Resolve the common sampling
policy from verified deployment capabilities before launching comparisons.

`--plan-profile PROFILE --config VERIFIED_CONFIG --k 10 --repeats 1 --out DIR`
prepares only combinations admitted by non-secret readiness wrappers. Wrappers
contain `deployment` and `expanded`, including protocol, preparation policy,
history, reasoning, schedule, allowances and system/context provenance.
Freeze the reviewed commit, verify actual context admission and mode controls,
and set a cost limit using verified prices. Save every raw request, final answer,
exposed reasoning, usage and available cost evidence. Estimates, cache counts and
provider billing remain separate; unknown values remain null.
Pricing calculations use the supplied uncached input and completion rates.
If a deployment has long-context or other tiered rates, use verified conservative
rates covering the entire planned input range for the ceiling. Treat the resulting
amount as an estimate; reconcile tier, cache and reasoning usage with provider
billing separately. The ceiling excludes deployment preflight calls.

This extension is passive ICL only. Larger graphs and agentic integration are
separate follow-ups.
See [final run readiness](FINAL_RUN_READINESS.md) for the boundary between this
ICL lock and the existing agentic workflow.

Implementation: [adapter](../icl_expanded.py), [preparation extraction](../icl_preparation.py),
[runner](../icl_model_first_runner.py), [reporting](../experiments/preview_icl_expanded.py)
and [tests](../test_icl_expanded.py).

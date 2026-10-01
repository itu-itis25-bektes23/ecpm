# Model first, general preparation, or supplied graph

`icl_model_first_v1` with preparation policy `matched_preparation_v1` tests
whether explicitly asking for a system description helps beyond general
preparation. It is OFF-only, separate from the
[graph-availability experiment](ICL_GRAPH.md).

| Condition | Each period |
| --- | --- |
| `model_first` | Logs, freely written description, tasks |
| `task_only` | Logs, general preparation notes, tasks |
| `graph_given` | Logs and current graph, general preparation notes, tasks |

Every condition has three responses per period: preparation, task answers,
and a transition report. All stages allow 4096 output tokens. Only model-first
explicitly asks for a model; the other conditions use the same general
preparation instruction and may choose their own notes. This comparison tests
an explicit model request against general preparation, not against no preparation.

Only `graph_given` explicitly calls the system a graph. Model-first accepts any
representation. All conditions share deterministic silent-break worlds,
observations, ordering, mechanics and four route queries. The anchor query uses
the world's start/goal; three others use A reachability and a fixed hash ranking.
Explicit no-route answers are allowed. B receives the updated graph when supplied.
No B evidence enters A.

## History policies

Each period's structured report covers all 16 transition pairs after its tasks.
Select `--history-policy`:

- `retained_reports_v2` (default): every preceding question and exact final
  answer remains visible. All B stages, including model-first construction,
  see A's report question and answer.
- `separate_reports_post_task_v1`: collect each report in a copy of the post-task
  conversation, without appending the exchange to main history. No B stage,
  including its report copy, sees A's report. Earlier evidence, task answers
  and preparation answers remain visible.

Malformed final answers remain verbatim wherever retained. Provider-private
reasoning is never replayed. History and preparation policies have separate
recorded identities and results. Earlier runs without matched preparation remain a different design.
Use their original code version to audit them; do not pool them with this
version. Free-form preparation answers are saved and not scored.

## Offline commands

Use Python 3.11 or 3.12, standard library only, from the repository root.
Use unused output paths. No credentials or model access are needed.

```sh
python3 -B test_icl_model_first_contract.py
python3 -B test_icl_model_first.py
python3 -B experiments/preview_icl_model_first.py \
  --history-policy retained_reports_v2 --out /tmp/icl_retained_preview
python3 -B experiments/preview_icl_model_first.py \
  --history-policy separate_reports_post_task_v1 --out /tmp/icl_separate_preview
python3 -B run_pilot.py --protocol icl_model_first_v1 \
  --scenario icl_det_gate_seed8 --mode det \
  --model-first-condition model_first --history-policy retained_reports_v2 \
  --request-profile sol --provider dry-run --reasoning-mode off \
  --repeats 1 --sampling-seeds 0 --max-tokens 4096 \
  --out /tmp/icl_model_first_dry --tag model_first_retained
```

Select each condition and policy with a fresh tag. The generated preliminary
seed-8 plans contain six conversations and 36 responses across both policies:
six responses per conversation in every condition. These are
planned counts, not model results. `--repeats 3 --sampling-seeds 0 1 2` supports
later expansion; do not pool repeat 1 twice. The preview emits seed-8/13/25
prompts, complete synthetic histories, reference scores and hashes. For prompt
review, `review_prompts/` contains exactly three files: one complete initial
Period A prompt per condition. They contain no answers or Period B material.
Source reconciliation preserves both identities where supplied copies have an extra LF.

## Live configuration and limits

Use a clean implementation commit, an unused output directory and a private
`--deployment-config`. Its wrapper contains the [graph deployment schema](ICL_GRAPH.md)
under `deployment`, plus this `model_first` evidence:

```json
{
  "protocol": "icl_model_first_v1",
  "history_policy": "retained_reports_v2",
  "preparation_policy": "matched_preparation_v1",
  "output_allowances": [4096],
  "stage_limits_source": "<evidence the 4096 limit reaches the backend>",
  "system_message_source": "<evidence for the effective system-role path>",
  "context_source": "<verified policy-specific context handling>"
}
```

CLI and configuration policies must match. Placeholders and synthetic test
fixtures are not readiness evidence. Set `--model` and `--base-url` to verified
exact values. Confirm model-specific OFF controls, effective settings,
authentication and context handling. Azure and direct OpenAI are not interchangeable.

Preparation, tasks and reports each allow 4096 tokens in every condition.
Unused allowance does not transfer. The same number of turns and output
allowances does not imply equal actual token use or computation.
Each actual full conversation plus its stage allowance must fit before sending.
Never truncate or treat a previous answer as a future bound. Operational failures
stop; normally finished wrong/malformed answers remain results. There is no
automatic retry, repair, resume or ON fallback.

Sol uses `reasoning_effort=none`, stage-specific `max_completion_tokens`, and no
temperature/top_p/top_k/seed. Seed labels identify repeated outputs, not seeded
Sol samples. Gemma uses the existing OFF profiles; seeds require verified support.
Hosted authentication uses `OPENAI_API_KEY` or `TOGETHER_API_KEY`. Local generation
never reads those keys; optional frontend authentication uses `ECPM_LOCAL_API_KEY`.
`ECPM_LOCAL_BACKEND_API_KEY` is isolated to tokenizer/backend checks. Keep credentials
out of arguments, configuration evidence, logs and Git.

## Outputs and scores

`<out>/<tag>/` contains run JSONs and `summary.json`: original final answers,
complete raw provider envelopes saved before parsing, exact messages/hashes,
context/control evidence, parsed components, scores and per-request usage/cost.
Total usage equals main plus measurement branches. Model/task and report subtotals
are an alternative partition, not additional usage. Missing counts stay unknown.
Cost plans are admitted-context ceilings, not forecasts.

```sh
python3 -B experiments/preview_icl_model_first.py \
  --summarize /path/to/block_a /path/to/block_b --out /path/to/results.json
```

The reporter freshly audits operations and reads saved scores without reparsing.
Incomplete or failed-audit records are listed separately. Operationally valid
wrong/malformed answers stay in all-response denominators. Different model,
code, prompt, scorer, history and deployment identities separate groups;
duplicate repeat identities are rejected.

- Beliefs: strict single-object parsing, all-16 transition/joint denominators,
  conditional destination accuracy and probability MAE with scored counts.
  Unexpected fields fail format without erasing independently valid values.
- Route-finding: each query graded independently. No-route solutions are separate
  from finite routes; invalid/unreachable cost and regret are N/A.
- Detection and Localization: scored from B task answers.
- Preservation: the same four controls compare availability, destination and
  probability, requiring B's unchanged label. Self and truth scores retain
  all-control, conditional and all-four-correct measures. Separate-copy
  Preservation compares reports afterward even though B cannot see A's report.

Route/report consistency is diagnostic: the later report has seen the task answer,
so it is not a pre-task model and cannot establish which beliefs caused a route.
Turn counts and stage output allowances are matched, not actual computation,
input or latency. Repeats
within a graph are not independent worlds. Performance does not establish an
internal world model. Do not retry malformed answers to improve results.

# ICL results

Start with the [two result tables](final/results.md) and [task overview](../../docs/ICL.md).
[results.json](final/results.json) contains the saved component scores for all
18 final runs and 36 answers, not just the examples. Both conditions used
experiment commit `25d9d49af16a07939cb49ad0ba6e4101cc994ef7`.

The final tags are `icl_gate_gemma4e4b_q6k_det_off_belief_mt8192_v1` and
`icl_gate_gemma4e4b_q6k_det_on_belief_mt8192_v1`. Both saved operational audits
passed. App Thinking and API reasoning were aligned manually; neither final
condition used a separate reasoning budget. The output allowance was 8192.
Effective Min P was about 0.05 in both conditions despite the unchecked setting.
Exact request settings, runtime provenance and source hashes are in the score file.

## Six examples

These are fixed extracts: repeat 1, sampling seed 0 in every case, not selected
for performance. Each JSON contains the exact task and final-answer strings
in order: A task, A answer, B task, B answer. Turn B retains A and its answer
in context. Malformed answers are unchanged. Reasoning traces and provider
envelopes remain in the archive, not these extracts.

| Assistance level | OFF | ON |
|---|---|---|
| empirical_table | [Example](examples/empirical_table_off_r1_s0.json) | [Example](examples/empirical_table_on_r1_s0.json) |
| explained_logs | [Example](examples/explained_logs_off_r1_s0.json) | [Example](examples/explained_logs_on_r1_s0.json) |
| minimal_logs | [Example](examples/minimal_logs_off_r1_s0.json) | [Example](examples/minimal_logs_on_r1_s0.json) |

## Reproduce the tables

```bash
python3 -B experiments/summarize_icl.py runs/icl/final/results.json --output runs/icl/final/results.md
python3 -B experiments/test_summarize_icl.py
```

The stdlib-only script reads saved scores, never raw answers or a model.
It does not reparse, rescue later JSON objects or rescore. Malformed components
remain failures in all-response denominators. Conditional destination, MAE
and preservation measures retain their scored counts. Use `--json` with a
separate output path for all derived per-level and pooled measures.
`route_unresolvable` remains diagnostic only.

## Archived evidence

The complete local archive is retained outside Git and temporary storage as
`ecpm-icl-archives/pr21-2b2949b/full-evidence.zip`. It is not hosted by this
repository; request a copy from the PR author. Its sibling `MANIFEST.json`
records each member's SHA-256, and `receipt.json` records ZIP integrity.

Archive SHA-256:
`6a3d9e47cec11a35640d7fa2a5525c7f27433f3d0110d68abcb1dff335a53a65`

Members retain `reviewed-pr/runs/icl/`, `original-pilot-artifacts/`, and
`original-audit-zips/`. Each compact run and example records its exact archive
member and source-artifact hash. The final ON audit's `comparison.json` and
`report.md` hold the original both-condition audit, exact responses and
interpretation. They are archived, not duplicated here.

## Development history

Earlier attempts are development evidence, not final-comparison samples.
For the abbreviated tags below, prepend `icl_gate_gemma4e4b_q6k_det_`.
Original tags, summaries and available supporting audits remain in the archive.

| Tags | What they record | Historical verdict |
|---|---|---|
| `off` | Original route wording | Runner PASS; route-output ambiguity |
| `off_v2`, `on` | Corrected terminal-route wording, earlier belief contract | Runner PASS; belief-contract ambiguity |
| `off_belief_v1` | Clarified beliefs, 4096-token OFF reference | Runner PASS |
| `on_belief_v1` | Uncapped 4096-token ON | Runner FAIL; truncation |
| `on_belief_rb3072_v1` | API-only reasoning budget | Runner FAIL; truncation and reported-budget exceedances |
| `on_belief_rb3072_app_v1` | Partial launch | Launch FAIL; wrong model ID and local PermissionError |
| `on_belief_rb3072_app_v2` | App and API budget | Runner PASS; original strict reported-token FAIL |

For app_v2, the later verified token-accounting explanation was developed
post hoc; its saved addendum labels the historical comparison provisional.
The explanation does not relabel the original strict FAIL.

The `icl_mt8192_pair` audit package records an OFF preflight control failure,
with no experiment suite launched. Synthetic checks are preserved under
`icl_gate_det_off_dry`, `prompt_contract`, and both `prompt_audit` source
directories. Standalone narrative audits for the earliest route-contract
runs and a separate JSON-selection audit report were not located; available
raw responses and saved parser results remain archived.

One graph seed and three repeated outputs per level support a descriptive
pilot, not significance, cross-world generality or full graph learning.

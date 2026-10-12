# DeepSeek expanded ICL

[Generated tables](tables.md) separate operational completion from scientific
correctness. [Full raw evidence on Drive](https://drive.google.com/drive/folders/1AfRR4Mi-ykLaiLb47z6ARB_4Mz7yUwij)
contains prompts, answers, provider envelopes, configurations, commands and ledgers.
The archive link was supplied by its owner; recipient permissions have not been
independently checked.

The audited recovery implementation is
[`3dbaafcc71de094b7336e3a82d6fc0034e39be74`](https://github.com/itu-itis25-bektes23/ecpm/commit/3dbaafcc71de094b7336e3a82d6fc0034e39be74).
It builds on [#46](https://github.com/itu-itis25-bektes23/ecpm/pull/46)
and [#50](https://github.com/itu-itis25-bektes23/ecpm/pull/50); the exact recovery
commit is published separately in [#58](https://github.com/itu-itis25-bektes23/ecpm/pull/58).
Neither earlier dependency alone contains the recovery implementation. Historical completions retain their
original commit and allowance, not the reporting commit.

## Files and reproduction

- `cells.csv`: every planned cell, including incomplete failures, source hashes,
  actual allowances and first-attempt/recovery flags.
- `audited_metrics.csv.gz`: lossless compressed audited scientific rows, including
  malformed-answer failures, conditional denominators and quarantine rows.
- `request_attempts.csv.gz`: all attempts, usage, costs, raw-envelope hashes, unknown
  counts and original token-accounting discrepancies. The superseded historical
  failure is explicitly labelled, not counted as another completed cell.
- `aggregates.csv.gz`: generated metric totals separated by source/cap cohort,
  arm, mode, reasoning and history.
- [Failures](failures.json), [cost reconciliation](cost_reconciliation.json),
  [usage totals](usage_totals.json), [provenance](provenance.json) and
  [validation](validation.json).
- `metrics.csv.gz`, `request_usage.csv.gz` and `costs.csv`: unchanged exports
  imported on main by PR #63. Their request coverage is narrower than the full
  attempt accounting. These files are not added to the audited exports as extra
  observations or extra costs.
- [Imported strict-score tables](icl_tables.md): regenerated from main's saved
  metric rows with each arm's own conversation and metric denominators.
- `metrics_content.csv.gz` and [secondary content-score tables](icl_tables_content.md):
  unchanged post hoc content scores from main, with tables regenerated to show
  arm-specific denominators. These use a different parser policy,
  not the original scientific scores. They are kept separate, not silently pooled.
- [Import provenance](main_import_provenance.json) and [reconciliation](reconciliation.json):
  preserved-file hashes and score agreement checks.

The main import quarantines historical fixed-cap conversations under its export
path; the audited handoff validates them against their original implementation.
The generated coverage table distinguishes new completions, historical completions
and incomplete cells. The main import's strict and secondary tables are narrower
views, not substitutes for that coverage. No historical result was rescored here.

From the repository root, without models or private data:

```sh
python3 -B experiments/publish_deepseek_icl.py --check
python3 -B experiments/test_publish_deepseek_icl.py
```

Omit `--check` to regenerate tables. To reproduce the curated input files from
the audited handoff, pass `--handoff /path/to/handoff --out /path/to/unused/output`.
The importer verifies every handoff-manifest hash. It does not parse answers or
rescore them. The existing general ICL table exporter is not used unchanged here:
this cohort needs explicit incomplete cells, mixed caps, recovery and null usage.

## Interpretation

The model was `deepseek/deepseek-v4.1-flash`, served through OpenRouter with
Ionstream pinned. A generic `provider=openai` field denotes API compatibility,
not an OpenAI model or backing provider. ON acceptance follows the recorded
request-defined policy, not a claim of positive exposed reasoning on every turn.

All arms have matched preparation, task and readout stages in both periods.
Model-first has no extra preparation turn. Separate-history Preservation compares
reports even though B cannot see A's report. Reports are post-task, not independent
pre-task models. Free-form preparation remains unscored.

Incomplete conversations are unscored, not successes. Operationally valid wrong
and malformed answers remain results. Historical fixed-cap and adaptive-cap
cohorts stay identifiable. Provider-reported charges differ from unresolved
reservations and invoice reconciliation. No recovery was performed for this
publication. These repeated configurations do not constitute independent graph
samples; no significance or generality claim is made.

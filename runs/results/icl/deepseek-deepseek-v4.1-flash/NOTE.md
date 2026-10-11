# DeepSeek V4.1 Flash, expanded ICL

See the [audited coverage and accounting](tables.md) for new and historical completions, incomplete cells, actual cap cohorts and failures. OpenRouter, profile deepseek_openrouter, pinned Ionstream provider. The run used a bounded recovery policy (icl_bounded_recovery_v1): a failed stage could be retried within the same conversation, and every attempt is kept in the raw evidence and request_attempts.csv.gz.

The allowance-exhaustion failure is **retained history, stochastic redirect, seed 0, task_only, ON**, at B_readout. It exhausted both 32K and 64K. The stochastic silent-break seed-13 task_only OFF cell instead ended on a provider error. All incomplete cells remain unscored; [failures.json](failures.json) retains their exact identities and original usage.

The original main imports metrics.csv.gz, request_usage.csv.gz and costs.csv are preserved byte-for-byte. Their exporter quarantined the historical completions; [icl_tables.md](icl_tables.md) describes that narrower strict-score view with arm-specific denominators. The audited handoff's original scores, including those historical completions, remain in audited_metrics.csv.gz. See [reconciliation.json](reconciliation.json) for their agreement, without rescoring.

costs.csv is a narrower completed-conversation reported-charge view, not an invoice or a full attempt ledger. The [generated accounting table](tables.md) separates provider-reported charges, unresolved reservations, earlier pilots outside the batch, total exposure and remaining authorization. Exposure is not reported spend; upstream cost details are not added twice.

Answer format with reasoning off: 1,097 of 1,316 OFF task and readout answers are well-formed (all 1,304 ON answers are); 31 OFF answers start with prose before the JSON.

The ICL arms are matched in turns: every arm has six stages, including two preparation turns.

**Content re-score (secondary):** metrics_content.csv.gz and icl_tables_content.md re-read every answer that fails the strict parse from its last complete JSON object carrying the answer field (the same idea as the agentic parser) and re-score it with the run's own scorer. The strict files stay the primary record. Haiku: 433 of 626 malformed answers recovered; with reasoning off, graph-given B detection rises from 7-24% to 100% and necessary updates from 3-10% to 70-81%. DeepSeek: 218 of 219 recovered; its low OFF update rate (about 25% in graph-given) is unchanged, so it is behavior, not format. Sol has almost no malformed answers (at most 3 of 108 per stage), so its strict scores already are its content scores.

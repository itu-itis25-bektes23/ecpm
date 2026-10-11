# Evidence review: Claude Haiku 5.5, expanded ICL

Checked on 11 October 2026 with experiments/audit_icl_evidence.py, over the full local run folder (660 run directories, one record and one summary each). Read-only.

**The repository results come from exactly these runs.** The 660 run ids in metrics.csv.gz are identical to the 660 run records checked.

**Every check passed, with no exception.**
- 660 of 660 conversations completed, with the operational gate passed and every audit flag true (complete, hashes, history, identity, no secrets, persistence, responses).
- Every run records model anthropic/claude-haiku-5.5, protocol icl_expanded_v2, profile haiku_openrouter, scorer icl_expanded_rows_v3 and commit 3be2c59 with a clean tree.
- Every run is pinned to the Anthropic provider with fallbacks off, and all 3,960 answers report Anthropic as the serving provider and anthropic/claude-haiku-5.5 as the model.
- 330 runs are reasoning off and send reasoning.enabled false. 330 are reasoning on and send reasoning effort medium.
- Every answer requested an output cap of 16,384 tokens, returned HTTP 200 and finished with end_turn, so no answer was cut off.
- No answer has a control violation. With reasoning off, 0 of 1,980 answers report reasoning tokens. With reasoning on, 1,945 of 1,980 do, as NOTE.md states.
- The 660 runs cover 660 distinct cells: 2 reasoning settings, 2 modes, 11 scenario-mode cells, 5 graphs, 3 arms and 2 history settings.

**One detail.** The readiness records of the reasoning-off runs are dated 10 October 2026 and those of the reasoning-on runs 11 October 2026.

This is a check of the run records. A team member should confirm it before the results are frozen.

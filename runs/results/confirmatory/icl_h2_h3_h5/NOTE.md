# Notes on the stage-2 results

**Protocol.** These runs use the legacy two-turn protocol (`run_pilot.py --protocol legacy`). It asks the period B probes as separate successive questions, which is the earlier protocol described in Appendix B.1. It does not use the single period B answer described in Section 4 and Appendix D. In two-turn and single-turn alike, the Localization question states that the dynamics changed, so Localization can exceed Detection.

**Counts given (counts2).** The F3_stats view lists attempts and deliveries per link but no destinations. No route can be planned from it, so the optimal-route rate is 0.00 by construction. H2 uses Localization only. Because the view removes destinations as well as the counting, a positive H2 shows that this view helps localization, not that the failures in the core view are counting failures.

**Unparsed answers.** 15 of 1,251 Localization answers did not parse. 14 are Claude Haiku 5.5 declining to name a pair, 13 at K=20 and 1 at K=5 (for example "I won't guess a specific node"). Several of these also retract an earlier "no change" answer. The 15th is a DeepSeek V4.1 Flash single-turn answer that reasons in prose without a parsable answer object. They count as incorrect in the primary analysis. In the secondary analysis, which excludes them, H5 for Haiku is unchanged in reading (+0.18 on 67 seeds instead of +0.12 on 81). In counts2, 15 Haiku route answers did not parse; this affects no hypothesis. Every Localization answer that parsed named a pair on the period B menu.

**Single-turn Localization** is low for Claude Haiku 5.5 (0.15) and DeepSeek V4.1 Flash (0.23), against 0.83 and 0.67 in two-turn. Every Haiku answer and all but one DeepSeek answer parsed, and every parsed answer named a pair on the menu, so this is behavior, not format. In single-turn the model sees both periods in one prompt and has not first reported its period A beliefs, as it does in two-turn. This is descriptive: no hypothesis covers it.

**DeepSeek Detection** falls as evidence grows: it reports a change in 81% of runs at K=5, 51% at K=10 and 23% at K=20, and in 13% single-turn. This is descriptive: no hypothesis covers it.

**Settings.** Every request used an output cap of 16,384 tokens, as recorded in the model.max_tokens field of all 1,251 run artifacts (stage2_runner.py v2). The runs were made on 11 October 2026, with artifact timestamps from 16:56 to 17:13 UTC.

**Reasoning.** Every run records reasoning off with zero violations, from commit 09fc3a8, after the fix that makes the legacy path send the control. first_attempt_reasoning_audit.txt records the earlier attempt, which did not send it and is not used.

**Runner and prompts.** experiments/stage2_runner.py is the runner that made these runs (v2, after the fix). Each run is one call of run_pilot.py --protocol legacy. A dry run of run_pilot.py at 09fc3a8 reproduces the prompts these runs sent exactly: for seed 33, every probe prompt of core2, core1 and counts2 is identical to the prompt recorded in the run artifacts of all three models.

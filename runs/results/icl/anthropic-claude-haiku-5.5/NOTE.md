# Claude Haiku 5.5, expanded ICL

660 conversations, run on 2026-10-11 from commit 3be2c5905e062999c7ba05eb405776f2a173b833 (main, PR #50 and the Haiku profile), output limit 16384 tokens, OpenRouter pinned to the Anthropic endpoint. costs.csv holds the cost OpenRouter billed per conversation (the Sol ICL costs are estimates from tokens and list prices). prep_words columns are left empty.

Reasoning: ON asks for effort medium and is request-defined (haiku_request_defined_on_v1, the same rule as sol_request_defined_on_v1). Reasoning tokens are recorded per answer, not required.

**Evidence review pending:** the deployment configs and preflight records have not yet been reviewed independently. Do not freeze these results before that review.

**Answer format with reasoning off:** many OFF answers reason in plain text before giving the JSON object, against the protocol's JSON-only instruction, so the strict parser marks them invalid (for example task-only A_task: 4 of 110 well-formed; ON: 105 of 110). Sampled answers are correct in content. The strict scores here are the protocol's primary scores and reflect format compliance for OFF; a secondary content score that reads the last complete JSON object (the agentic arm's rule) will be added for all three models.

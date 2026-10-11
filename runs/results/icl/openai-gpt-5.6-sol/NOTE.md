# GPT-5.6 Sol, expanded ICL

660 of 660 conversations, Azure OpenAI.
- OFF: 330 conversations, commit cd23576, output allowance 4,096.
- ON: 329 conversations, commit 4f9dd9a, output allowance 32,768, request-defined ON (sol_request_defined_on_v1: ON is the supported request condition; reasoning tokens are recorded, not required).
- ON: 1 conversation (seed 8, deterministic silent break, task-only, retained history) from the earlier ON check run, commit cd23576, output allowance 4,096. It completed under that commit's stricter rule (observed reasoning required on every answer), so it is kept; its rows carry output_allowance 4096 and reasoning_acceptance_policy observed_reasoning_required_cd23576.

metrics.csv.gz combines all 660; costs.csv (OFF) and costs_on.csv (ON, including the check conversation) hold estimated costs from tokens and list prices. Almost no answers are malformed (at most 3 of 108 per stage), so the strict scores are also the content scores.

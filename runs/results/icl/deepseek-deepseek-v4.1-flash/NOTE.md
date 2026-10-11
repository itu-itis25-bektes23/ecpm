# DeepSeek V4.1 Flash, expanded ICL

655 of 660 conversations completed: 652 run from commit 3dbaafc (output allowance 32,768, raised to 65,536 for the 32 conversations that needed it) and 3 earlier pilot conversations from commit a3e3249 (16,384). OpenRouter, profile deepseek_openrouter, pinned provider. The run used a bounded recovery policy (icl_bounded_recovery_v1): a failed stage could be retried within the same conversation, and every attempt is kept in the raw evidence.

Five conversations are incomplete and excluded: four ended on provider errors, and one (stochastic, silent break, seed 13, task-only, OFF) exhausted both the 32K and the 64K allowance.

metrics.csv.gz and request_usage.csv.gz were exported from the 655 completed conversations with the export tool of the run's own checkout. icl_tables.md covers the 652 conversations of the main run. costs.csv holds the cost OpenRouter billed for the final attempt of each completed conversation (10.73 USD); the total including failed and retried attempts was 13.27 USD.

Answer format with reasoning off: 1,097 of 1,316 OFF task and readout answers are well-formed (all 1,304 ON answers are); 31 OFF answers start with prose before the JSON.

The ICL arms are matched in turns: every arm has six stages, including two preparation turns.

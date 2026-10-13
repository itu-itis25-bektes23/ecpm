# H1, exploratory (expanded ICL, five graphs)

H1 asks whether a model plans through a link it calls broken. Measured on the expanded-ICL runs: stochastic and deterministic silent break, conversations whose period B report gives the broken link p_success <= 0.05 or marks it unavailable; numerator: period B routes that still use that link. Answers that fail the strict parse are read from their last complete JSON object. One-sided 95% Clopper-Pearson lower bounds. Script: experiments/h1_icl.py.

Cohort: all completed conversations marked `operational_status=valid` in the published metric export: 660 Sol, 660 Haiku and 652 DeepSeek. Sol includes the seven published check conversations. The three separately audited, quarantined historical DeepSeek records are excluded from this scored cohort, without changing their audit status. `h1_inputs_manifest.csv` records the source hashes and selection; each completed run ID is used once. The counts below concern the qualifying silent-break subset.

The bounds are unadjusted and descriptive. They do not account for shared graphs or, for the route-level bounds, dependence among routes in a conversation. This cohort correction leaves the parsing, eligibility and bound calculations unchanged. Sol OFF's conversation lower bound changes from 0.02 to 0.01; all rounded route bounds and the H1 conclusion remain unchanged.

| Model | Reasoning | Conversations stating the link broken | Routes through the link | Lower bound | Conversations with such a route | Lower bound |
|---|---|---|---|---|---|---|
| GPT-5.6 Sol | off | 59 | 3 of 236 (1%) | 0.00 | 3 (5%) | 0.01 |
| GPT-5.6 Sol | on | 58 | 6 of 232 (3%) | 0.01 | 3 (5%) | 0.01 |
| Claude Haiku 5.5 | off | 21 | 0 of 84 (0%) | 0.00 | 0 (0%) | 0.00 |
| Claude Haiku 5.5 | on | 32 | 2 of 128 (2%) | 0.00 | 1 (3%) | 0.00 |
| DeepSeek V4.1 Flash | off | 38 | 15 of 152 (10%) | 0.06 | 10 (26%) | 0.15 |
| DeepSeek V4.1 Flash | on | 59 | 3 of 236 (1%) | 0.00 | 1 (2%) | 0.00 |

H1 (> 0.10 on the route share) is not supported for any model. The expanded-ICL prompt does not state the keep-destination rule. It says instead that a failed attempt does not by itself mean that the action lost its destination (icl_expanded.py at cd23576). In expanded ICL the period B plan comes before the period B report, and the runs use the five exploratory graphs. The condition specified in the internal analysis plan (the single-answer protocol without the keep-destination rule, 84 held-out seeds) was not run. The two-turn protocol that ran on those seeds (legacy, see confirmatory/icl_h2_h3_h5) asks for no period B probability, so H1 cannot be computed from it.

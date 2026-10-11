# H1, exploratory (expanded ICL, five graphs)

H1 asks whether a model plans through a link it calls broken. Measured on the expanded-ICL runs: stochastic and deterministic silent break, conversations whose period B report gives the broken link p_success <= 0.05 or marks it unavailable; numerator: period B routes that still use that link. Answers that fail the strict parse are read from their last complete JSON object. One-sided 95% Clopper-Pearson lower bounds. Script: experiments/h1_icl.py.

| Model | Reasoning | Conversations stating the link broken | Routes through the link | Lower bound | Conversations with such a route | Lower bound |
|---|---|---|---|---|---|---|
| GPT-5.6 Sol | off | 53 | 3 of 212 (1%) | 0.00 | 3 (6%) | 0.02 |
| GPT-5.6 Sol | on | 57 | 6 of 228 (3%) | 0.01 | 3 (5%) | 0.01 |
| Claude Haiku 5.5 | off | 21 | 0 of 84 (0%) | 0.00 | 0 (0%) | 0.00 |
| Claude Haiku 5.5 | on | 32 | 2 of 128 (2%) | 0.00 | 1 (3%) | 0.00 |
| DeepSeek V4.1 Flash | off | 38 | 15 of 152 (10%) | 0.06 | 10 (26%) | 0.15 |
| DeepSeek V4.1 Flash | on | 60 | 3 of 240 (1%) | 0.00 | 1 (2%) | 0.00 |

H1 (> 0.10 on the route share) is not supported for any model. The expanded protocol states a keep-destination rule, which could pull the link into the plan, so these shares are if anything an upper estimate for the rule-free condition. In expanded ICL the period B plan comes before the period B report. The pre-registered condition (two-turn protocol, no keep-destination rule, 84 seeds) was not run: the protocol has no variant without the rule.

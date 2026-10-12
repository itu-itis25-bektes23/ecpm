# Format diagnostic: Claude Haiku 5.5, expanded ICL, reasoning off

**Why.** With reasoning off, many Haiku task answers carry prose before the JSON object, so the strict parser rejects them (NOTE.md). This diagnostic asks whether the prose is noise or reasoning that the answers depend on.

**Method.** experiments/haiku_format_diag.py replays saved task-turn requests exactly as sent, reasoning off, and changes only how the answer may be written. It scores each answer with a scorer that agrees with the harness on all 4,044 route judgments and every detection and localization of the run files. Version 2 used 24 turns, 6 per group: task-only A_task, task-only B_task and graph-given B_task, sampled from originally malformed answers, and model-first A_task, from originally well-formed answers, as a control. Each turn got one sample per condition. Run on 12 October 2026. Results are in diag_v2/, the earlier 12-turn version 1 in diag_v1/, and version 3, on the same 24 turns, in diag_v3/.

**Version 4: full scale, the main result.** Version 4 covers every reasoning-off task turn, 660 of them, under four conditions. That is 2,640 calls, run on 12 October 2026, with 0 errors, every call served by Anthropic and every one finishing normally. The results are in diag_v4/. Each condition is paired with today's exact replay of the same turn, with normal 95% intervals.

| Condition, reasoning off | Pure JSON | Routes optimal, strict | Routes optimal, content | Detection (B) | Localization (B) |
|---|---|---|---|---|---|
| Exact replay | 58% | 22% | 50% | 89% | 86% |
| JSON forced by the answer schema | 100% | 41% | 41% (−0.09, [−0.12, −0.07]) | 88% (−0.00, [−0.03, +0.02]) | 84% (−0.02, [−0.04, +0.01]) |
| Required "reasoning" field in the schema | 100% | 71% | 71% (+0.21, [+0.19, +0.24]) | 89% | 88% |
| "reasoning" field, instructed only | 84% | 70% | 81% (+0.31, [+0.28, +0.33]) | 89% | 88% |

- **The replay matches the original answers:** 58% pure JSON against 59%, and 53% optimal routes by content against 54%. The behavior is stable.
- **Forcing JSON costs route quality where Haiku had written reasoning, and nowhere else.** On originally malformed turns, optimal routes fall from 74% to 37% (task-only A_task), 73% to 39% (graph-given B_task) and 61% to 48% (task-only B_task). On originally well-formed turns they do not change, for example 46% to 46% (graph-given A_task) and 41% to 42% (model-first A_task). Detection and localization do not change.
- **Three numbers describe Haiku's routes with reasoning off.** The strict score is 22%, combining format compliance and quality. JSON-only quality is 41%, which is the like-for-like comparison with models that answer without visible reasoning. Quality with visible reasoning is 50 to 54% by content.
- **A required reasoning field fixes the format,** with pure JSON in every answer and 71% optimal routes. It also raises turns that were already well-formed, for example from 41% to 74% (model-first A_task), so it changes the condition and not only the output format. The instructed field reaches 81% but only 84% pure JSON.
- **The 24-turn versions overstate the cost of forcing JSON** (61% to 38%), because their turns were chosen from malformed answers. Use version 4.

**Results (version 2, all 24 turns).**

| Condition, reasoning off | Pure JSON | Routes optimal, content | Localization (B), content |
|---|---|---|---|
| Exact replay | 33% | 61% | 83% |
| Structured output with the answer schema (JSON forced) | 100% | 38% | 83% |
| "Output only the JSON object" appended to the last user message | 83% | 41% | 75% |
| API JSON mode (json_object) | 42% | 63% | 83% |

**Findings.**
- **Forcing JSON lowers route quality.** When Haiku cannot write reasoning before the JSON, optimal routes fall from 61% to 38%. The drop holds in every group of malformed turns: task-only A_task 75% to 38%, graph-given B_task 83% to 46%, task-only B_task 46% to 25%. The forced level matches the 39% of the runs' own pure-JSON answers.
- **Localization does not depend on the format.** It is 83% with prose and with forced JSON.
- **The end-of-message instruction raises format compliance** from 33% to 83%, with the same drop in route quality.
- **JSON mode has no effect here.**
- **Version 1 checked the rest.** Assistant prefill is not supported by the model (HTTP 400). Reasoning on gives 100% pure JSON and 98% optimal routes on the same turns.

**Version 3: a fix.** It ran on the same 24 turns.

| Condition | Pure JSON | Routes optimal, strict | Routes optimal, content | Localization (B), content | Hidden reasoning tokens |
|---|---|---|---|---|---|
| Exact replay, reasoning off | 33% | 11% | 57% | 80% | 0 |
| Structured output with a required "reasoning" string field before the answer fields | 100% | 71% | 71% | 83% | 0 |
| The same field, only instructed | 75% | 60% | 77% | 92% | 0 |
| Reasoning on, effort low | 92% | 84% | 92% | 100% | 970 |
| Reasoning on, capped at 1,024 reasoning tokens | 100% | 94% | 94% | 100% | 1,408 |

- **An enforced "reasoning" field fixes the format without losing quality.** Every answer is pure JSON, with no hidden reasoning, and optimal routes reach 71%, above the 57% of the prose answers.
- **The field helps beyond format.** The model-first control turns, already well-formed, rise from 33% to 67%. A reasoning field gives the model room to reason, so it changes the condition and not only the output format.
- **A fair use reruns every model.** Applying it to Haiku alone would give Haiku room to reason that the other models did not get. The fair use is a rerun of the reasoning-off grid for every model with the same field.
- **The 1,024-token cap was not exact:** the mean was 1,408 reasoning tokens.

**Reading.** With reasoning off, the prose is Haiku's visible reasoning. For routes, the strict score compares all three models without visible reasoning, so the content score would credit Haiku with reasoning the other models did not use. For detection and localization the strict score understates Haiku, since forced-JSON answers localize as well as prose answers. Versions 1 to 3 are diagnostics on selected turns. Version 4 covers every reasoning-off task turn, with one sample per condition. None of them is a confirmatory test.

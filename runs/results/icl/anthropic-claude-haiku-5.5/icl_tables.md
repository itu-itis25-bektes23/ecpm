## anthropic/claude-haiku-5.5: 660 conversations (expanded ICL)

**Table 1. Reading, reporting and acting by arm (scenarios with a change)**

| Reasoning | Arm | History | Convs | A transitions exact | A routes optimal | B detection | B localization | B necessary updates | B routes optimal |
|---|---|---|---|---|---|---|---|---|---|
| off | task_only | retained | 45 | 31% | 4% | 27% | 16% | 0% | 10% |
| off | task_only | separate | 45 | 24% | 5% | 29% | 24% | 0% | 17% |
| off | model_first | retained | 45 | 33% | 38% | 71% | 67% | 45% | 33% |
| off | model_first | separate | 45 | 38% | 39% | 64% | 62% | 41% | 32% |
| off | graph_given | retained | 45 | 100% | 36% | 7% | 7% | 3% | 2% |
| off | graph_given | separate | 45 | 100% | 28% | 24% | 24% | 10% | 14% |
| on | task_only | retained | 45 | 44% | 95% | 73% | 71% | 78% | 76% |
| on | task_only | separate | 45 | 46% | 91% | 73% | 73% | 79% | 67% |
| on | model_first | retained | 45 | 45% | 96% | 89% | 89% | 92% | 88% |
| on | model_first | separate | 45 | 46% | 91% | 89% | 89% | 97% | 87% |
| on | graph_given | retained | 45 | 100% | 100% | 84% | 84% | 85% | 77% |
| on | graph_given | separate | 45 | 100% | 99% | 96% | 96% | 94% | 89% |

**Table 2. Reporting a change vs acting on it (conversations where a route had to change)**

| Conversations | n | Necessary updates made |
|---|---|---|
| Reported the change (detection correct) | 264 | 93% |
| Did not report it | 90 | 1% |

**Table 3. Detection / necessary updates by scenario (history and reasoning pooled)**

| Scenario | Convs per arm | task_only detection / updates | model_first detection / updates | graph_given detection / updates |
|---|---|---|---|---|
| silent_break | 40 | 55% / 76% | 85% / 85% | 55% / 68% |
| hard_removal | 40 | 72% / 90% | 88% / 74% | 57% / 72% |
| redirect | 40 | 40% / 65% | 85% / 92% | 45% / 61% |
| degradation | 20 | 20% / 50% | 15% / 33% | 55% / 50% |
| irrelevant | 40 | 50% / 76% | 88% / 74% | 52% / 64% |

**Table 4. No-change control: reports no change / replans anyway**

| Reasoning | Convs per arm | task_only | model_first | graph_given |
|---|---|---|---|---|
| off | 20 | 30% / 0% | 80% / 0% | 70% / 0% |
| on | 20 | 85% / 1% | 70% / 1% | 100% / 0% |

Rates pool numerators over denominators across conversations. Preparation answers flagged for review: 484.


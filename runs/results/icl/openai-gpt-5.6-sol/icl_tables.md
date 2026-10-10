## gpt-5.6-sol: 330 conversations (expanded ICL)

**Table 1. Reading, reporting and acting by arm (scenarios with a change)**

| Reasoning | Arm | History | Convs | A transitions exact | A routes optimal | B detection | B localization | B necessary updates | B routes optimal |
|---|---|---|---|---|---|---|---|---|---|
| off | task_only | retained | 45 | 47% | 95% | 100% | 93% | 86% | 86% |
| off | task_only | separate | 45 | 47% | 93% | 98% | 96% | 87% | 86% |
| off | model_first | retained | 45 | 45% | 91% | 76% | 76% | 85% | 82% |
| off | model_first | separate | 45 | 45% | 92% | 80% | 80% | 91% | 85% |
| off | graph_given | retained | 45 | 100% | 97% | 100% | 100% | 92% | 85% |
| off | graph_given | separate | 45 | 100% | 98% | 100% | 100% | 91% | 87% |

**Table 2. Reporting a change vs acting on it (conversations where a route had to change)**

| Conversations | n | Necessary updates made |
|---|---|---|
| Reported the change (detection correct) | 235 | 89% |
| Did not report it | 13 | 73% |

**Table 3. Detection / necessary updates by scenario (history and reasoning pooled)**

| Scenario | Convs per arm | task_only detection / updates | model_first detection / updates | graph_given detection / updates |
|---|---|---|---|---|
| silent_break | 20 | 100% / 95% | 80% / 81% | 100% / 98% |
| hard_removal | 20 | 100% / 92% | 100% / 100% | 100% / 89% |
| redirect | 20 | 100% / 89% | 100% / 91% | 100% / 93% |
| degradation | 10 | 90% / 67% | 0% / 75% | 100% / 67% |
| irrelevant | 20 | 100% / 73% | 70% / 82% | 100% / 89% |

**Table 4. No-change control: reports no change / replans anyway**

| Reasoning | Convs per arm | task_only | model_first | graph_given |
|---|---|---|---|---|
| off | 20 | 65% / 0% | 95% / 4% | 100% / 0% |

Rates pool numerators over denominators across conversations. Preparation answers flagged for review: 180.


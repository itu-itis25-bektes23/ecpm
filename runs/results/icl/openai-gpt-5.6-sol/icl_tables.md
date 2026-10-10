## gpt-5.6-sol: 659 conversations (expanded ICL)

**Table 1. Reading, reporting and acting by arm (scenarios with a change)**

| Reasoning | Arm | History | Convs | A transitions exact | A routes optimal | B detection | B localization | B necessary updates | B routes optimal |
|---|---|---|---|---|---|---|---|---|---|
| off | task_only | retained | 45 | 47% | 95% | 100% | 93% | 86% | 86% |
| off | task_only | separate | 45 | 47% | 93% | 98% | 96% | 87% | 86% |
| off | model_first | retained | 45 | 45% | 91% | 76% | 76% | 85% | 82% |
| off | model_first | separate | 45 | 45% | 92% | 80% | 80% | 91% | 85% |
| off | graph_given | retained | 45 | 100% | 97% | 100% | 100% | 92% | 85% |
| off | graph_given | separate | 45 | 100% | 98% | 100% | 100% | 91% | 87% |
| on | task_only | retained | 44 | 45% | 97% | 75% | 75% | 92% | 89% |
| on | task_only | separate | 45 | 47% | 96% | 78% | 78% | 91% | 88% |
| on | model_first | retained | 45 | 47% | 97% | 67% | 67% | 92% | 88% |
| on | model_first | separate | 45 | 46% | 97% | 69% | 69% | 95% | 89% |
| on | graph_given | retained | 45 | 100% | 100% | 100% | 100% | 100% | 92% |
| on | graph_given | separate | 45 | 100% | 100% | 100% | 100% | 100% | 92% |

**Table 2. Reporting a change vs acting on it (conversations where a route had to change)**

| Conversations | n | Necessary updates made |
|---|---|---|
| Reported the change (detection correct) | 450 | 94% |
| Did not report it | 49 | 67% |

**Table 3. Detection / necessary updates by scenario (history and reasoning pooled)**

| Scenario | Convs per arm | task_only detection / updates | model_first detection / updates | graph_given detection / updates |
|---|---|---|---|---|
| silent_break | 39 | 79% / 85% | 65% / 88% | 100% / 99% |
| hard_removal | 40 | 100% / 96% | 100% / 100% | 100% / 94% |
| redirect | 40 | 100% / 95% | 100% / 96% | 100% / 96% |
| degradation | 20 | 55% / 80% | 0% / 88% | 100% / 83% |
| irrelevant | 40 | 88% / 81% | 62% / 81% | 100% / 95% |

**Table 4. No-change control: reports no change / replans anyway**

| Reasoning | Convs per arm | task_only | model_first | graph_given |
|---|---|---|---|---|
| off | 20 | 65% / 0% | 95% / 4% | 100% / 0% |
| on | 20 | 90% / 3% | 100% / 3% | 100% / 0% |

Rates pool numerators over denominators across conversations. Preparation answers flagged for review: 327.


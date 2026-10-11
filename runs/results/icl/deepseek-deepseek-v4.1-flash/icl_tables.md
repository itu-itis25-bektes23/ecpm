## deepseek/deepseek-v4.1-flash: 652 conversations (expanded ICL)

**Table 1. Reading, reporting and acting by arm (scenarios with a change)**

| Reasoning | Arm | History | Convs | A transitions exact | A routes optimal | B detection | B localization | B necessary updates | B routes optimal |
|---|---|---|---|---|---|---|---|---|---|
| off | task_only | retained | 45 | 42% | 44% | 78% | 67% | 18% | 38% |
| off | task_only | separate | 44 | 46% | 37% | 68% | 61% | 26% | 28% |
| off | model_first | retained | 45 | 45% | 49% | 87% | 82% | 26% | 46% |
| off | model_first | separate | 44 | 43% | 44% | 80% | 75% | 28% | 43% |
| off | graph_given | retained | 45 | 100% | 50% | 100% | 100% | 26% | 44% |
| off | graph_given | separate | 45 | 100% | 54% | 100% | 100% | 25% | 48% |
| on | task_only | retained | 44 | 48% | 98% | 89% | 89% | 96% | 90% |
| on | task_only | separate | 45 | 47% | 97% | 98% | 96% | 100% | 91% |
| on | model_first | retained | 45 | 47% | 97% | 87% | 84% | 100% | 91% |
| on | model_first | separate | 44 | 45% | 97% | 91% | 89% | 97% | 91% |
| on | graph_given | retained | 45 | 100% | 100% | 100% | 100% | 100% | 92% |
| on | graph_given | separate | 44 | 100% | 100% | 100% | 100% | 100% | 92% |

**Table 2. Reporting a change vs acting on it (conversations where a route had to change)**

| Conversations | n | Necessary updates made |
|---|---|---|
| Reported the change (detection correct) | 404 | 75% |
| Did not report it | 21 | 45% |

**Table 3. Detection / necessary updates by scenario (history and reasoning pooled)**

| Scenario | Convs per arm | task_only detection / updates | model_first detection / updates | graph_given detection / updates |
|---|---|---|---|---|
| silent_break | 39 | 87% / 69% | 79% / 68% | 100% / 70% |
| hard_removal | 40 | 98% / 78% | 100% / 81% | 100% / 80% |
| redirect | 39 | 92% / 81% | 92% / 81% | 100% / 74% |
| degradation | 20 | 35% / 80% | 50% / 100% | 100% / 67% |
| irrelevant | 40 | 80% / 76% | 90% / 67% | 100% / 66% |

**Table 4. No-change control: reports no change / replans anyway**

| Reasoning | Convs per arm | task_only | model_first | graph_given |
|---|---|---|---|---|
| off | 20 | 70% / 4% | 84% / 0% | 100% / 0% |
| on | 18 | 78% / 3% | 90% / 3% | 100% / 0% |

Rates pool numerators over denominators across conversations. Preparation answers flagged for review: 353.


## anthropic/claude-haiku-5.5: 660 conversations (expanded ICL)

**Table 1. Reading, reporting and acting by arm (scenarios with a change)**

| Reasoning | Arm | History | Convs | A transitions exact | A routes optimal | B detection | B localization | B necessary updates | B routes optimal |
|---|---|---|---|---|---|---|---|---|---|
| off | task_only | retained | 45 | 36% | 64% | 67% | 56% | 51% | 44% |
| off | task_only | separate | 45 | 29% | 52% | 58% | 53% | 49% | 38% |
| off | model_first | retained | 45 | 36% | 38% | 89% | 84% | 61% | 46% |
| off | model_first | separate | 45 | 38% | 39% | 84% | 82% | 69% | 47% |
| off | graph_given | retained | 45 | 100% | 44% | 100% | 100% | 81% | 72% |
| off | graph_given | separate | 45 | 100% | 48% | 100% | 100% | 70% | 67% |
| on | task_only | retained | 45 | 47% | 97% | 87% | 84% | 90% | 88% |
| on | task_only | separate | 45 | 47% | 97% | 93% | 93% | 96% | 87% |
| on | model_first | retained | 45 | 45% | 96% | 91% | 91% | 95% | 90% |
| on | model_first | separate | 45 | 46% | 95% | 91% | 91% | 97% | 88% |
| on | graph_given | retained | 45 | 100% | 100% | 100% | 100% | 100% | 92% |
| on | graph_given | separate | 45 | 100% | 99% | 100% | 100% | 100% | 92% |

**Table 2. Reporting a change vs acting on it (conversations where a route had to change)**

| Conversations | n | Necessary updates made |
|---|---|---|
| Reported the change (detection correct) | 405 | 88% |
| Did not report it | 18 | 4% |

**Table 3. Detection / necessary updates by scenario (history and reasoning pooled)**

| Scenario | Convs per arm | task_only detection / updates | model_first detection / updates | graph_given detection / updates |
|---|---|---|---|---|
| silent_break | 40 | 80% / 78% | 98% / 89% | 100% / 91% |
| hard_removal | 40 | 92% / 78% | 100% / 86% | 100% / 95% |
| redirect | 40 | 80% / 79% | 98% / 100% | 100% / 90% |
| degradation | 20 | 20% / 22% | 15% / 33% | 100% / 83% |
| irrelevant | 40 | 80% / 78% | 98% / 81% | 100% / 90% |

**Table 4. No-change control: reports no change / replans anyway**

| Reasoning | Convs per arm | task_only | model_first | graph_given |
|---|---|---|---|---|
| off | 20 | 70% / 0% | 85% / 0% | 100% / 0% |
| on | 20 | 95% / 1% | 70% / 1% | 100% / 0% |

Rates pool numerators over denominators across conversations. Preparation answers flagged for review: 484.


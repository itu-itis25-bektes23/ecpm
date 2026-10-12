# Evidence-only reference agent

Seeds: [33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 48, 49, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 66, 68, 69, 70, 71, 72, 73, 74, 76, 77, 78, 79, 81, 83, 84, 85, 86, 87, 88, 89, 90, 91]. Agent: reference_agent.py. Runner: experiments/reference_agent_runs.py. Same worlds, episodes, step budget and metric functions as the language-model agents.

| Mode | Scenario | Runs | M1 goal success | Mean steps M1 | H4: chose again / qualifying | Median decision lag | Exposed runs |
|---|---|---|---|---|---|---|---|
| sto | silent_break | 51 | 0.93 | 6.4 | 1/22 | 6.0 | 31 |
| sto | degradation | 51 | 1.00 | 5.0 | 0/1 | 6 | 31 |

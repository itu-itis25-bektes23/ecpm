# Evidence-only reference agent

Seeds: [8, 13, 25, 0, 1, 4, 5, 7, 9, 10]. Agent: reference_agent.py. Runner: experiments/reference_agent_runs.py. Same worlds, episodes, step budget and metric functions as the language-model agents.

| Mode | Scenario | Runs | M1 goal success | Mean steps M1 | H4: chose again / qualifying | Median decision lag | Exposed runs |
|---|---|---|---|---|---|---|---|
| det | no_change | 10 | 1.00 | 3.5 | 0/0 | – | 0 |
| det | irrelevant | 10 | 1.00 | 3.6 | 0/0 | 1.0 | 2 |
| det | silent_break | 10 | 1.00 | 4.3 | 0/0 | 1.0 | 6 |
| det | hard_removal | 10 | 1.00 | 4.2 | 0/0 | 1 | 6 |
| det | redirect | 10 | 1.00 | 4.0 | 0/0 | – | 0 |
| sto | no_change | 10 | 1.00 | 5.0 | 0/0 | – | 0 |
| sto | irrelevant | 10 | 1.00 | 5.0 | 0/0 | 1 | 1 |
| sto | silent_break | 10 | 1.00 | 6.5 | 0/6 | 6.0 | 6 |
| sto | hard_removal | 10 | 1.00 | 5.3 | 0/0 | 1.0 | 6 |
| sto | redirect | 10 | 0.90 | 5.1 | 0/0 | – | 0 |
| sto | degradation | 10 | 1.00 | 5.9 | 0/2 | 12.0 | 6 |

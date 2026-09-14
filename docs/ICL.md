# ICL: three assistance levels

The `icl_two_response_v1` task asks a model to estimate links in a small
graph from observations, then update those estimates and its route when
given a second period of evidence. It is passive: the model does not choose
which observations to collect.

The three levels change the help supplied with the same evidence.
`empirical_table` gives observation counts and next-state frequencies,
plus a mechanics explanation. `explained_logs` gives shuffled raw rows
with that explanation. `minimal_logs` gives the same rows in the same
order, with the common field definitions but without the broader
failure/retry explanation. The world, menus, queried links, response
contract and scorer stay matched.

Period A comes first. The model reports **Beliefs** and **Route-finding**.
Period B is then revealed in the same conversation, retaining the first
answer. The second response adds **Detection**, **Localization** and
**Preservation**, along with updated beliefs and a new route. The five
queried links are the changed target and four unchanged controls; these
roles are not labelled in the prompts.

The final comparison is the matched `off_belief_mt8192_v1` and
`on_belief_mt8192_v1` pair, with full tags in the results index. Both were
produced at `25d9d49af16a07939cb49ad0ba6e4101cc994ef7`, not this documentation
revision. Earlier attempts, including failures and partial launches,
remain development evidence.

This pilot uses one graph with three repeated outputs per level.
Assistance levels are implemented and tested, but a difficulty ordering
and full graph learning are not established.

- [Final tables and development history](../runs/icl/README.md)
- [Saved scores and archive index](../runs/icl/README.md)
- [Offline report script](../experiments/summarize_icl.py) and [report tests](../experiments/test_summarize_icl.py)
- [Harness and shared prompts](../run_pilot.py), [parser and scorer](../ecpm_parser.py), [environment](../resource_mdp.py)
- [Runner tests](../test_run_pilot.py), [parser tests](../test_ecpm_parser.py), [prompt-contract tests](../test_prompt_contract.py)
- [Response contract](INTERFACE.md)

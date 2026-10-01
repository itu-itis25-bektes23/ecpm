# In-context learning experiments

These experiments test how supplied information and conversation history affect
Beliefs, Route-finding, Detection, Localization and Preservation in small routing
environments. Their prompts, histories and scores are not interchangeable.

- [Model-first experiment](ICL_MODEL_FIRST.md): freely describe the system before
  tasks, prepare without an explicit model request, or prepare with a supplied
  graph. All conditions have the same stages. Transition reports either remain
  in history or use separate post-task copies.
- [Graph availability](ICL_GRAPH.md): receive a graph in both periods, only in A,
  or neither period. Each conversation has two answers.
- [Interface](INTERFACE.md): earlier contracts and the frozen schema.

Each experiment page includes offline commands, outputs and deployment
requirements. Dry runs test the implementation with synthetic answers, not model
performance or deployment readiness. Historical evidence remains under
[runs](../runs/README.md). Do not pool different protocol, prompt, history-policy,
scoring or deployment identities. Repeated outputs within a graph are not
independent graph samples; performance does not establish an internal world model.

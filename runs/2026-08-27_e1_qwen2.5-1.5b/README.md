# E1, Qwen2.5-1.5B-Instruct, 27 August 2026

In-context learning against finetuning on matched evidence.

- `e1_answers_Qwen2.5-1.5B-Instruct.json` raw model replies
- `e1_official_scores.json` scored through the frozen parser

Generation and scoring are deliberately separate: replies are persisted raw,
then scored by `experiments/rescore_e1.py`, so a scorer change can be
re-applied without re-running the model.

    python3 experiments/rescore_e1.py \
        runs/2026-08-27_e1_qwen2.5-1.5b/e1_answers_Qwen2.5-1.5B-Instruct.json .

Two reasons to re-run rather than cite these directly. They predate the
start/goal scoring fix described in the 7 September update, so route numbers
may be void. And the adaptation prompt used here carries the pre-fix route
wording, which three models read as an instruction to append a step at the
goal node.

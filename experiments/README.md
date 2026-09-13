# experiments

Analysis and run scripts. Nothing here is imported by the harness; each is
run directly and writes an artifact under `runs/`.

- `seed_eligibility.py` recomputes the three seed criteria from the code and
  writes `runs/seed_eligibility.json`. The run script reads its seed list
  from that file, so the two cannot drift.
- `baseline_k_sweep.py` evidence-only baseline accuracy per condition and K.
  Establishes which conditions carry headroom for a model at all.
- `summarize_run.py` turns a directory of run artifacts into the reported
  statistics, with n attached and Wilson intervals on the proportions that
  carry claims.
- `azure_budget.py` costs a run matrix from measured token usage rather than
  estimates.

The in-context versus finetuning comparison, grafted from a separate
repository:

- `gen_payloads.py` builds prompt payloads from the frozen generator.
  Output is regenerated rather than committed.
- `e1_batch.py` runs the three arms for one model on a GPU. Carries its
  author's note that this exact file has not executed on one.
- `rescore_e1.py` scores saved replies through the frozen parser, so a
  scorer change can be re-applied without re-running the model.
- `notebooks/` the Colab notebooks the batch script mirrors.
- `run_two_turn_azure.sh` the two-turn run, resumable, refusing to start
  without credentials.

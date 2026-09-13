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
- `run_two_turn_azure.sh` the two-turn run, resumable, refusing to start
  without credentials.

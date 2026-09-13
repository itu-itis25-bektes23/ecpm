# runs

One directory per run, named `YYYY-MM-DD_model_variant`. Artifacts record
`frozen_sha`, `git_head` and `pinned_to_freeze`, so a run can always be
traced to the environment tree that produced it.

Summarise a directory with:

    python3 experiments/summarize_run.py runs/<dir>

Two entries are kept deliberately and are not duplicates.

- `2026-08-23_sonnet46_mt1024/` is the truncation failure that motivated
  raising the `--max-tokens` default to 4096. It is the evidence for that
  change and should not be removed.
- `*_dryrun.json` files are oracle-derived pipeline demos rather than model
  runs. They exercise the parser and scorer without an API call.

Loose JSON files at this level are generated analyses rather than runs:
`baseline_k_sweep_seeds1-30.json`, `baseline_redirect_sweep.json` and
`seed_eligibility.json`. Each is reproducible from a script in
`experiments/`.

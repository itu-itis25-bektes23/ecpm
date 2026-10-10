# Results

Final result files, one folder per arm and model, so all results are in one place. They live under `runs/`, which the repository keeps tracked for curated results (see `.gitignore`).

```
runs/results/
  agentic/
    openai-gpt-5.6-sol/           agentic_runs.csv, agentic_summary.md, agentic_tables.md
    anthropic-claude-haiku-5.5/   (same three files)
    deepseek-deepseek-v4.1-flash/ (same three files)
  icl/
    <model>/                      the ICL results CSVs for that model
```

- **Folder names** are the OpenRouter model ID with `/` replaced by `-`, as in the run folders.
- **`agentic_runs.csv`**: one row per run, with the settings (seed, mode, scenario, arm, history, reasoning, model), behaviour, exposure, probe results, H4 (`h4_reached`, `h4_chose_again`), reasoning tokens, billed cost, output cap and cut-offs. This is the file to analyse. CSVs written before the H4 columns existed still work; regenerate them from the run folders (`python summarize_agentic_runs.py <run folder>`) to add H4.
- **`agentic_summary.md`**: mean and spread per arm, one table set per scenario, mode and reasoning setting.
- **`agentic_tables.md`**: the Results-tab Tables 1–4 (behaviour and probes by arm, exposed vs not exposed, by scenario, no-change control), the cost line and an H4 line.

## Adding a model's agentic results

After a grid finishes (`python run_agentic_cost_check.py --grid ...`), its combined folder `runs/GRID_<model>_<date_time>/` holds `agentic_runs.csv` and `agentic_summary.md`:

```
mkdir runs/results/agentic/<model>
cp runs/GRID_<model>_<date_time>/agentic_runs.csv runs/GRID_<model>_<date_time>/agentic_summary.md runs/results/agentic/<model>/
python summarize_agentic_runs.py --tables runs/results/agentic/<model>/agentic_runs.csv
```

The last command writes `agentic_tables.md` next to the CSV. It works from any shared `agentic_runs.csv`, so everyone gets the same tables.

## What these runs used

The Sol and Haiku agentic grids ran on 10 Oct 2026 from the `results-freeze` tag:
- 5 graphs (seeds 8, 13, 25, 0, 1), 3 arms, 5 deterministic + 6 stochastic scenarios, reasoning off and on: 330 runs per model;
- history none;
- output cap 32,768 (DeepSeek: 65,536, set by its runner).

Each run's artifact records its commit, cap and per-call `finish_reason`.

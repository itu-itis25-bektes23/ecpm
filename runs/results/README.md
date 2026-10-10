# Results

Final result files, one folder per arm and model, so all results are in one place. They live under `runs/`, which the repository keeps tracked for curated results (see `.gitignore`).

```
runs/results/
  agentic/
    openai-gpt-5.6-sol/           agentic_runs.csv, agentic_summary.md, agentic_tables.md
    anthropic-claude-haiku-5.5/   (same three files)
    deepseek-deepseek-v4.1-flash/ (same three files)
  icl/
    openai-gpt-5.6-sol/           metrics.csv.gz, request_usage.csv.gz, costs.csv, icl_tables.md
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

## Adding a model's ICL results

The expanded-ICL export writes `metrics.csv` (one row per metric), `request_usage.csv` and a cost CSV. `metrics.csv` is large (Sol OFF: 153 MB), so keep it gzipped (1.4 MB):

```
mkdir runs/results/icl/<model>
gzip -c <results dir>/metrics.csv > runs/results/icl/<model>/metrics.csv.gz
gzip -c <results dir>/request_usage.csv > runs/results/icl/<model>/request_usage.csv.gz
python summarize_icl_run.py --tables runs/results/icl/<model>/metrics.csv.gz
```

The last command writes `icl_tables.md`:
- Table 1: reading (A transitions), answering (A and B routes), reporting (B detection, localization) and acting (B necessary updates), by arm, history and reasoning;
- Table 2: necessary updates for conversations that reported the change vs those that did not;
- Table 3: by scenario;
- Table 4: the no-change control (reports no change / replans anyway).

Rates pool numerators over denominators across valid conversations.

## What these runs used

ICL: the GPT-5.6 Sol OFF grid (Maciej, commit `cd23576`, preparation v3, Azure, 4,096 cap with no truncation): 3 arms × 2 histories × 55 configurations = 330 conversations.

The Sol and Haiku agentic grids ran on 10 Oct 2026 from the `results-freeze` tag:
- 5 graphs (seeds 8, 13, 25, 0, 1), 3 arms, 5 deterministic + 6 stochastic scenarios, reasoning off and on: 330 runs per model;
- history none;
- output cap 32,768 (DeepSeek: 65,536, set by its runner).

Each run's artifact records its commit, cap and per-call `finish_reason`.

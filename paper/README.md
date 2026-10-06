# Paper tools

Tools that produce or check the paper's figures, numbers and build. The
research code in the repository root stays stdlib only. `figures.py` is the
one exception: it needs the packages in `requirements-figures.txt`, and
nothing in the root imports it.

| Task | Command | Produces or checks |
|---|---|---|
| All tests | `python3 paper/tasks.py test` | every suite, plus `agentic_conditions.py test` |
| Figures | `python3 paper/tasks.py figures` | world atlas, evidence networks, `figure_summary.json` |
| Numbers | `python3 paper/tasks.py numbers PATH/ECPM_main.tex` | `derived_numbers.tex`: Wilson intervals, exploratory-run numbers, figure shares |
| Build gate | `python3 paper/tasks.py build PAPER_DIR [draft\|final]` | fails on LaTeX errors, undefined references, `??`, Type 3 or unembedded fonts; `final` also fails on placeholders |
| Anonymity | `python3 paper/tasks.py anon DIR` | names, handles, emails, home paths and PDF metadata in a supplement folder |
| Agentic conditions | `python3 paper/tasks.py agentic-test`, `agentic-estimate`, `agentic-dry model_first 33` | tests, offline cost estimate, one dry run |
| Everything offline | `python3 paper/tasks.py offline` | test, figures and the cost estimate |

Seeds are fixed: worlds use seeds 31 to 130, evidence seed 0, t-SNE
`random_state=0`, force layouts seed 7. Each check was tested against a
deliberately broken input and fails on it.

Figures: `pip install -r paper/requirements-figures.txt`, then run the figures task.

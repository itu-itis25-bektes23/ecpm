"""Study seeds for expanded ICL, without touching icl_expanded.py (whose source is pinned by its tests).

icl_expanded.SEEDS lists the five exploratory graphs. A study round adds its seeds through the environment
variable ECPM_ICL_SEEDS (comma list). Entry points call apply() right after importing icl_expanded, so the
default grid, its tests and its prompts are unchanged when the variable is unset.
"""
import os


def extra():
    return tuple(int(x) for x in os.environ.get("ECPM_ICL_SEEDS", "").replace(" ", "").split(",") if x)


def apply(module):
    add = tuple(s for s in extra() if s not in module.SEEDS)
    if add:
        module.SEEDS = tuple(module.SEEDS) + add
    return module.SEEDS

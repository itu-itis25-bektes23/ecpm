#!/usr/bin/env python3
"""Render Appendix D (Prompt templates) from what the harness actually sends.

Stdlib only. Runs the dry-run provider (no API calls) for the confirmatory
example instance (stochastic silent break, K = 10, seed 33), reads the prompts
recorded in the artifacts, and writes LaTeX in the style of the current
appendix: {\\scriptsize \\begin{verbatim} ... \\end{verbatim}}, lines wrapped at
48 columns, evidence records shortened to the first 6 rows plus
"[... N further records ...]".

Each verbatim block is preceded by a "% prompt-source: <key>" comment so that
paper/check_prompts.py can re-derive it from the artifacts.

Usage (from the repository root, /home/user/ecpm/work):
  python3.12 -B paper/gen_prompt_appendix.py [--dry-dir DIR] [--out TEX]
If --dry-dir is missing or empty the dry runs are created there (default: a
fresh temporary directory).
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import tempfile
import textwrap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(ROOT, "paper", "tex", "prompt_appendix_new.tex")
WIDTH = 48
KEEP_ROWS = 6
SEED = "33"
GOAL_PLACEHOLDER = "<goal>"

COMMON = ["--scenario", "seed7_silent_break", "--condition", "silent_break",
          "--seed", SEED, "--mode", "sto", "--provider", "dry-run", "--tag", "p"]
RUNS = {
    # key: (argv prefix, extra run_pilot args)
    "icl": (["run_pilot.py"], ["--protocol", "icl_two_response_v1",
                               "--turn-mode", "two_turn", "--k", "10",
                               "--budget", "10",
                               # confirmatory Period B schema: a belief
                               # about every listed pair
                               "--period-b-every-pair"]),
    "agent": (["run_pilot.py"], ["--pilot-type", "active"]),
    "agent_announce": (["run_pilot.py"], ["--pilot-type", "active",
                                          "--announce-change"]),
    "agent_model_first": (["agentic_conditions.py", "run", "model_first", "--"],
                          ["--pilot-type", "active"]),
}


# ------------------------------------------------------------------ dry runs
def make_dry_runs(dry_dir):
    for key, (prefix, extra) in RUNS.items():
        out = os.path.join(dry_dir, key)
        if glob.glob(os.path.join(out, "p", "*.json")):
            continue
        cmd = [sys.executable, "-B"] + prefix + COMMON + extra + ["--out", out]
        subprocess.run(cmd, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _icl_artifact(dry_dir):
    hits = sorted(glob.glob(os.path.join(
        dry_dir, "icl", "p", "icl_two_response_v1_seed*_sto_r1_explained_logs_*.json")))
    if not hits:
        raise FileNotFoundError("no explained_logs r1 artifact in " + dry_dir)
    return _load(hits[0])


def _agent_transcript(dry_dir, key):
    hits = sorted(glob.glob(os.path.join(dry_dir, key, "p", "*active*.json")))
    if not hits:
        raise FileNotFoundError(f"no active artifact for {key} in {dry_dir}")
    return [m["content"] for m in _load(hits[0])["explore"]["transcript"]
            if m["role"] == "user"]


def _note_before_position(msg):
    """The transition note is everything before the 'You are at' line."""
    head, _, _ = msg.partition("\nYou are at ")
    return head


def sources(dry_dir):
    """Return {key: exact text sent} for every block the appendix shows.

    agent_system is not stored in the artifacts; it comes from the function
    the harness calls, explore_agent.build_system_prompt (and, for the
    model_first condition, agentic_conditions.system_prompt).
    """
    sys.path.insert(0, ROOT)
    import explore_agent
    import agentic_conditions
    icl = _icl_artifact(dry_dir)
    out = {"turn_A": icl["turns"]["A"]["prompt"],
           "turn_B": icl["turns"]["B"]["prompt"]}
    out["agent_system"] = explore_agent.build_system_prompt(GOAL_PLACEHOLDER)
    mf_sys = agentic_conditions.system_prompt(GOAL_PLACEHOLDER, "model_first")
    out["agent_system_model_first_suffix"] = mf_sys[len(out["agent_system"]):].lstrip()
    user = _agent_transcript(dry_dir, "agent")
    step = next(m for m in user if m.startswith("Your last action")
                and "failed (you stayed)" in m)
    out["agent_step"] = step
    plain = next(m for m in user if m.startswith("You are placed back"))
    ann = next(m for m in _agent_transcript(dry_dir, "agent_announce")
               if m.startswith("You are placed back"))
    out["agent_transition"] = (_note_before_position(plain) + "\n\n"
                               + _note_before_position(ann))
    mf = _agent_transcript(dry_dir, "agent_model_first")
    asks = []
    for m in mf:
        i = m.find("Before the next episode")
        if i >= 0:
            ask = m[i:]
            if ask not in asks:
                asks.append(ask)
    out["agent_model_first_requests"] = "\n\n".join(asks)
    return out


# ------------------------------------------------------------------ rendering
def shorten(text):
    """Keep the first KEEP_ROWS evidence rows of each observation list."""
    lines = text.split("\n")
    res, i = [], 0
    while i < len(lines):
        res.append(lines[i])
        if lines[i].startswith("Raw shuffled observations, Period"):
            j = i + 1
            while j < len(lines) and lines[j].startswith("["):
                j += 1
            rows = lines[i + 1:j]
            res.extend(rows[:KEEP_ROWS])
            if len(rows) > KEEP_ROWS:
                res.append(f"[... {len(rows) - KEEP_ROWS} further records ...]")
            i = j
            continue
        i += 1
    return "\n".join(res)


def wrap(text):
    out = []
    for line in text.rstrip("\n").split("\n"):
        out.extend(textwrap.wrap(line, WIDTH, break_on_hyphens=False,
                                 break_long_words=False) or [""])
    return "\n".join(out)


def render_block(text):
    return wrap(shorten(text))


def verbatim(key, text):
    body = render_block(text)
    if "\\end{verbatim}" in body:
        raise ValueError("verbatim terminator inside prompt text")
    return (f"% prompt-source: {key}\n{{\\scriptsize\n\\begin{{verbatim}}\n"
            f"{body}\n\\end{{verbatim}}}}\n")


def render_tex(src):
    return "\n".join([
        "\\section{Prompt templates}\\label{app:prompts}",
        "",
        "The text sent to the model in the two-turn protocol, for stochastic "
        "silent break at $K = 10$ on the first confirmatory seed (seed 33), is "
        "reproduced below with the evidence records shortened. Every other part "
        "is verbatim. The full prompts of every run are stored with its "
        "artifact~\\cite{ecpm2026}. Turn 2 shows the confirmatory Period B "
        "schema, which asks for a belief about every listed pair.",
        "",
        "\\paragraph{Turn 1 (Period A).}",
        verbatim("turn_A", src["turn_A"]),
        "\\paragraph{Turn 2 (Period B added).}",
        verbatim("turn_B", src["turn_B"]),
        "\\paragraph{Agentic arm.}",
        "The system prompt, an example step observation and the transition "
        "message to $M_1$, as sent by the harness. \\texttt{<goal>}, the node, "
        "the menu and the step count are filled in per step.",
        verbatim("agent_system", src["agent_system"]),
        "\\noindent Step observation:",
        verbatim("agent_step", src["agent_step"]),
        "\\noindent Transition to $M_1$, main runs, and announced variant:",
        verbatim("agent_transition", src["agent_transition"]),
        "\\noindent In the model\\_first condition the system prompt ends with "
        "the sentence below, and before every episode after the first the "
        "model receives the first request below (later episodes: the second).",
        verbatim("agent_system_model_first_suffix",
                 src["agent_system_model_first_suffix"]),
        verbatim("agent_model_first_requests",
                 src["agent_model_first_requests"]),
    ])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-dir", default=None)
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()
    dry_dir = args.dry_dir or tempfile.mkdtemp(prefix="ecpm_promptdry_")
    os.makedirs(dry_dir, exist_ok=True)
    make_dry_runs(dry_dir)
    tex = render_tex(sources(dry_dir))
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(tex)
    print(f"wrote {args.out} (dry runs in {dry_dir})")


if __name__ == "__main__":
    main()

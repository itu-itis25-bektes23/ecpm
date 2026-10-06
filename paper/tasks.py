"""Task runner for ECPM. Stdlib only. Run from anywhere:

    python3 paper/tasks.py test                         # every test suite, offline
    python3 paper/tasks.py figures [OUTDIR]             # paper figures (needs requirements-figures.txt)
    python3 paper/tasks.py numbers PAPER_TEX [OUT_TEX]  # derived numbers macros from run artifacts
    python3 paper/tasks.py build PAPER_DIR [draft|final]  # LaTeX build gate
    python3 paper/tasks.py baselines [TEX]                  # reference sweep, offline numbers, write them into the paper
    python3 paper/tasks.py anon DIR                     # anonymity check of a supplement folder
    python3 paper/tasks.py agentic-test | agentic-estimate
    python3 paper/tasks.py agentic-dry CONDITION SEED   # one dry agentic run, no API calls
    python3 paper/tasks.py offline                      # test + figures + agentic-estimate
"""
import os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.join(ROOT, "paper")
PY = [sys.executable, "-B"]
TESTS = ["test_resource_mdp.py", "test_ecpm_parser.py", "test_explore_agent.py", "test_ecpm_baseline.py",
         "test_prompt_contract.py", "test_run_pilot.py", "test_icl_graph.py",
         "test_icl_model_first_contract.py", "test_icl_model_first.py",
         "test_api_setup.py", "test_every_pair.py", "test_run_matrix.py"]

def sh(cmd, cwd=ROOT, stop=True):
    print("$", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=cwd)
    if r.returncode != 0 and stop:
        sys.exit(f"FAILED ({r.returncode}): {' '.join(cmd)}")
    return r.returncode == 0

def main(a):
    task = a[0] if a else ""
    if task == "test":
        failed = [t for t in TESTS + ["agentic_conditions.py"]
                  if not sh(PY + ([t, "test"] if t == "agentic_conditions.py" else [t]), stop=False)]
        print(f"{len(TESTS) + 1 - len(failed)} of {len(TESTS) + 1} suites passed" + (f". Failed: {', '.join(failed)}" if failed else ""))
        if failed: sys.exit(1)
    elif task == "figures":
        sh(PY + [os.path.join(HERE, "figures.py"), a[1] if len(a) > 1 else os.path.join(HERE, "figures")])
    elif task == "numbers":
        out = os.path.join(HERE, "figures")
        sh(PY + [os.path.join(HERE, "derived_numbers.py"), a[1], "runs/2026-09-12_gpt4o_twoturn_k10/summary.json",
                 os.path.join(out, "figure_summary.json"), a[2] if len(a) > 2 else os.path.join(out, "derived_numbers.tex")])
    elif task == "build":
        sh(["bash", os.path.join(HERE, "check_build.sh"), a[2] if len(a) > 2 else "draft"], cwd=a[1])
    elif task == "baselines":
        out = os.path.join(ROOT, "runs", "references")
        for mode in ("sto", "det"):
            for k in ("5", "10", "20"):
                sh(PY + ["experiments/reference_sweep.py", "--seeds", "31-130", "--modes", mode, "--k", k, "--json", os.path.join(out, f"part_{mode}_{k}.json")])
        sh(PY + ["experiments/offline_numbers.py"]); sh(PY + ["experiments/queried_restricted.py"])
        tex = a[1] if len(a) > 1 else os.path.join(HERE, "tex", "ECPM_main.tex")
        sh(PY + ["experiments/check_references.py", out, tex, "--out", os.path.join(out, "summary.json")], stop=False)
        for s in ("fill_references.py", "fill_offline.py", "make_fig_refs.py"):
            sh(PY + [os.path.join(HERE, s), tex], stop=False)
    elif task == "anon":
        sh(PY + [os.path.join(HERE, "check_anon.py"), a[1]])
    elif task == "agentic-test":
        sh(PY + ["agentic_conditions.py", "test"])
    elif task == "agentic-estimate":
        sh(PY + ["agentic_conditions.py", "estimate"])
    elif task == "agentic-dry":
        sh(PY + ["agentic_conditions.py", "run", a[1], "--", "--pilot-type", "active", "--mode", "sto",
                 "--provider", "dry-run", "--scenario", "seed7_silent_break", "--seed", a[2], "--tag", f"dry_{a[1]}_s{a[2]}"])
    elif task == "offline":
        for t in (["test"], ["figures"], ["agentic-estimate"]): main(t)
    else:
        print(__doc__); sys.exit(2)

if __name__ == "__main__":
    main(sys.argv[1:])

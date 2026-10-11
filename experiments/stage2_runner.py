"""Two-turn ICL runs for H2, H3 and H5 (and the bridge to the original protocol), three models, reasoning off.

Paired over the 84 eligible held-out seeds (stochastic silent break, seeds 33-129), as in the analysis plan:
  core2   two-turn, core prompt, K=10        (the reference condition)
  counts2 two-turn, counts table, K=10       (H2: counts minus core, Localization)
  core1   single-turn, core prompt, K=10     (H3: single minus two-turn, optimal routes)
  k5      two-turn, core prompt, K=5         (H5: K=20 minus K=5, Localization)
  k20     two-turn, core prompt, K=20
Each run is one run_pilot.py call on the legacy path. Finished runs are skipped on restart.

v2 (after the fix-legacy-reasoning-control PR): the first stage-2 attempt did not send the reasoning
control, because the legacy path dropped it, so those runs used each provider's default. This version
writes to a new folder (ecpm-stage2-runs-v2), refuses to start on a checkout without the fix, and uses an
output cap of 16,384 for all three models (the cap only matters if an answer reaches it). Every artifact
now records reasoning_control with a violation flag for an "off" run that still reasons.
"""
import concurrent.futures as cf, ctypes, os, subprocess, sys, time
from pathlib import Path

REPO = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\Users\efebe\ecpm")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else REPO.parent / "ecpm-stage2-runs-v2"
WORKERS = int(os.environ.get("STAGE2_WORKERS", "24"))
DRY = os.environ.get("STAGE2_DRY") == "1"
SEEDS = [33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 48, 49, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61,
         62, 63, 64, 66, 68, 69, 70, 71, 72, 73, 74, 76, 77, 78, 79, 81, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93,
         94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 108, 110, 111, 112, 113, 114, 115, 116, 117,
         118, 119, 120, 121, 122, 123, 125, 126, 129]
MODELS = {"sol": "openai/gpt-5.6-sol", "haiku": "anthropic/claude-haiku-5.5", "deepseek": "deepseek/deepseek-v4.1-flash"}
CONDS = {"core2": ["--turn-mode", "two_turn", "--k", "10", "--budget", "10"],
         "counts2": ["--turn-mode", "two_turn", "--k", "10", "--budget", "10", "--rendering", "F3_stats"],
         "core1": ["--turn-mode", "single", "--k", "10", "--budget", "10"],
         "k5": ["--turn-mode", "two_turn", "--k", "5", "--budget", "5"],
         "k20": ["--turn-mode", "two_turn", "--k", "20", "--budget", "20"]}
# At K=20 the evidence generator cannot reach coverage on these seeds (deterministic, no model call involved),
# so H5 is paired over the other 81 seeds.
K20_NOT_BUILT = {60, 81, 122}
CONTROL = '{"reasoning": {"enabled": false}}'
SOURCE = "OpenRouter reasoning.enabled=false, the request field used for reasoning off in the agentic arm"

def jobs():
    for m, mid in MODELS.items():
        for c, extra in CONDS.items():
            for s in SEEDS:
                if c == "k20" and s in K20_NOT_BUILT: continue
                tag = f"{m}_{c}_s{s}"
                cmd = [sys.executable, "-B", "run_pilot.py", "--protocol", "legacy", "--condition", "silent_break",
                       "--seed", str(s), "--mode", "sto", *extra, "--out", str(OUT), "--tag", tag]
                cmd += (["--provider", "dry-run"] if DRY else
                        ["--provider", "openai", "--model", mid, "--base-url", "https://openrouter.ai/api/v1",
                         "--reasoning-mode", "off", "--reasoning-control-json", CONTROL,
                         "--reasoning-control-source", SOURCE, "--max-tokens", "16384", "--timeout", "300"])
                yield tag, cmd

def done(tag):
    d = OUT / tag
    return d.is_dir() and any(d.glob("pilot_*.json"))

def run(tag, cmd):
    if done(tag): return tag, "skipped"
    (OUT / "_logs").mkdir(parents=True, exist_ok=True)
    for attempt in (1, 2):                      # one retry for transport failures; never on a finished run
        with open(OUT / "_logs" / f"{tag}.log", "a", encoding="utf-8") as log:
            rc = subprocess.run(cmd, cwd=REPO, stdout=log, stderr=subprocess.STDOUT).returncode
        if rc == 0 and done(tag): return tag, "ok"
        time.sleep(10)
    return tag, "failed"

FIX_MARK = 'extra=reasoning_provenance(args)["request_fields"]'

def main():
    if FIX_MARK not in (REPO / "run_pilot.py").read_text(encoding="utf-8"):
        sys.exit("this checkout lacks the reasoning-control fix: merge fix-legacy-reasoning-control into main first")
    if not DRY:
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key: sys.exit("set OPENROUTER_API_KEY first")
        os.environ["OPENAI_API_KEY"] = key       # the legacy client reads this name; the base URL is OpenRouter
    if os.name == "nt":
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)   # keep the machine awake
    todo = list(jobs()); OUT.mkdir(parents=True, exist_ok=True)
    print(f"{len(todo)} runs ({len(MODELS)} models x {len(CONDS)} conditions x {len(SEEDS)} seeds), {WORKERS} at a time, output {OUT}")
    counts = {"ok": 0, "skipped": 0, "failed": 0}; t0 = time.time(); failed = []
    with cf.ThreadPoolExecutor(WORKERS) as ex:
        for i, fut in enumerate(cf.as_completed([ex.submit(run, t, c) for t, c in todo]), 1):
            tag, st = fut.result(); counts[st] += 1
            if st == "failed": failed.append(tag)
            if i % 25 == 0 or i == len(todo):
                print(f"{time.strftime('%H:%M:%S')} {i}/{len(todo)} | ok {counts['ok']} skipped {counts['skipped']} failed {counts['failed']} | {int(time.time()-t0)}s", flush=True)
    (OUT / "failed.txt").write_text("\n".join(failed), encoding="utf-8")
    print("done" if not failed else f"{len(failed)} failed, listed in failed.txt; run again to retry them")

if __name__ == "__main__":
    main()

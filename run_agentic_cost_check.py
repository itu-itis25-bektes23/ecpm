"""Agentic cost check: real token use and cost of single runs, per arm. Stdlib only. Keeps everything local.

    python3 run_agentic_cost_check.py                  # all 5 seeds x 3 arms, silent break
    python3 run_agentic_cost_check.py --seeds 8        # quick check on one seed (3 runs)
    python3 run_agentic_cost_check.py --mode sto       # stochastic instead of deterministic
    python3 run_agentic_cost_check.py --dry            # same flow with no API calls
    python3 run_agentic_cost_check.py --condition redirect      # another scenario (default silent_break)
    python3 run_agentic_cost_check.py --openrouter MODEL_ID --price-in 0.3 --price-out 1.2   # via OpenRouter
    python3 run_agentic_cost_check.py --reasoning off   # or on; omitted = model default (not controlled)
    python3 run_agentic_cost_check.py --help            # this text
    python3 run_agentic_cost_check.py --grid --openrouter MODEL_ID --workers 24   # a model's whole grid, in parallel

All options (combine freely):
  --seeds 8,13        graphs (default 8,13,25,0,1)
  --mode det|sto      deterministic or stochastic world (default det)
  --condition NAME    no_change | irrelevant | silent_break | hard_removal | redirect | degradation (sto only)
  --history NAME      none | retained_reports_v2 | separate_reports_post_task_v1 (default none)
  --matched-prep      preparation turn for every arm, as in ICL
  --reasoning off|on  sends an explicit control: Azure reasoning_effort none/medium,
                      OpenRouter reasoning {enabled: false} / {effort: medium}
  --reasoning-control JSON   override that control, e.g. '{"reasoning_effort": "low"}'
  --openrouter MODEL_ID      run through OpenRouter instead of Azure
  --price-in X --price-out Y USD per million tokens, used only when the provider reports
                      no billed cost (OpenRouter reports it, cache discounts included)
  --max-tokens N      output cap per call, reasoning included (default 32768)
  --dry               no API calls
  --yes               skip the confirmation after the first run (for unattended loops)
  --grid              run a whole grid: every (mode, condition, reasoning, seed) as its own batch;
                      --mode, --condition and --reasoning then take lists (defaults det,sto / all / off,on)
  --workers N         with --grid: batches run at once (default 8)
  --since YYYY-MM-DD  with --grid: finished runs in batch folders from this date on count (default today)
  --commands FILE     run any command list (e.g. ICL run_pilot.py lines, one per line) --workers at a time
  --state DIR         with --commands: logs, lock and failed.txt (default output/_commands, ignored by git)
  --retries N         with --commands: reruns of a failed line in one session (default 0, as ICL answers are not retried)
  --cwd DIR           with --commands: run the lines in another checkout (e.g. a branch that has the ICL profile);
                      nothing is written there except the runs' own --out folders
Every option is recorded in the run folder name and in each run's artifact.

What it does:
  - runs every line of RUN_DIR/queue.txt ("condition seed repeat"), creating the default
    queue (3 arms x the chosen seeds, one run each) on first start
  - re-reads queue.txt after every run, so you can add lines while it is running
  - skips runs that already finished, so you can stop and restart at any time
  - stops cleanly after the current run if you create a file called STOP in RUN_DIR
  - after the first live run, shows its real token count and the projected total,
    and asks once whether to continue
  - after every run, rewrites RUN_DIR/exposure.csv (tokens, cost inputs, exposure)
    and prints progress; at the end zips RUN_DIR next to it
The API key is read from AZURE_OPENAI_API_KEY or asked once and stored in
~/.ecpm_azure.json (outside the repository, readable only by you).
"""
import datetime, getpass, json, os, shutil, subprocess, sys

# ---- settings (edit here) -------------------------------------------------------
SEEDS, REPEATS = [8, 13, 25, 0, 1], [0]          # the 5 graphs from the Results-tab matrix, one run each
CONDITIONS = ["task_only", "model_first", "graph_given"]
MODE = "det"                                      # the Results-tab plan starts with the deterministic case
SETUP = ["--pilot-type", "active", "--mode", MODE, "--scenario", "seed7_silent_break",
         "--m0-episodes", "4", "--m1-episodes", "4", "--max-steps-per-episode", "20"]
PRICE_IN, PRICE_OUT = 2.50, 10.00            # USD per million tokens (GPT-4o list price; check yours)
OPENROUTER_URL = "https://openrouter.ai/api/v1"
RUN_TIMEOUT = 10800                           # seconds per run (several long reasoning calls fit)
# ----------------------------------------------------------------------------------

ROOT = os.path.dirname(os.path.abspath(__file__))
DRY = "--dry" in sys.argv
YES = "--yes" in sys.argv          # skip the one confirmation after the first run (unattended batches)
if "--help" in sys.argv or "-h" in sys.argv:
    print(__doc__); sys.exit(0)
VALUE_FLAGS = {"--seeds", "--mode", "--condition", "--history", "--reasoning", "--reasoning-control", "--max-tokens",
               "--openrouter", "--price-in", "--price-out", "--workers", "--since", "--commands", "--state", "--retries", "--cwd"}
SWITCH_FLAGS = {"--dry", "--yes", "--matched-prep", "--help", "-h", "--grid"}
GRID = "--grid" in sys.argv
_rest = sys.argv[1:]
while _rest:   # a mistyped option would otherwise be ignored silently, e.g. a run without its reasoning control
    _flag = _rest.pop(0)
    if _flag in VALUE_FLAGS:
        if not _rest or _rest[0].startswith("--"):
            sys.exit(f"{_flag} needs a value (see --help)")
        _rest.pop(0)
    elif _flag not in SWITCH_FLAGS:
        sys.exit(f"unknown option {_flag!r} (see --help)")
def _arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default
SEEDS = [int(x) for x in _arg("--seeds", ",".join(map(str, SEEDS))).split(",")]
MODE = _arg("--mode", MODE); SETUP[SETUP.index("--mode") + 1] = MODE
SCENARIO = _arg("--condition", "silent_break")    # no_change | irrelevant | silent_break | hard_removal | redirect | degradation (sto only)
if SCENARIO != "silent_break":
    SETUP += ["--condition", SCENARIO]
if SCENARIO == "no_change":     # nothing changed, so there is nothing to localize
    SETUP += ["--probes", "detection", "preservation", "adaptation"]
OPENROUTER = _arg("--openrouter", "")             # e.g. --openrouter deepseek/deepseek-chat
_price = lambda v: float(str(v).replace(",", "."))   # accept 0,0173 as typed on comma-decimal systems
PRICE_IN = _price(_arg("--price-in", PRICE_IN)); PRICE_OUT = _price(_arg("--price-out", PRICE_OUT))
MAX_TOKENS = _arg("--max-tokens", "32768")          # output cap per call, reasoning included
SETUP += ["--max-tokens", MAX_TOKENS]
HISTORY = _arg("--history", "none")                 # ablation: retained_reports_v2 | separate_reports_post_task_v1
MATCHED_PREP = "--matched-prep" in sys.argv
REASONING = _arg("--reasoning", "")                 # off | on; empty = model default, not controlled
REASONING_CONTROL = _arg("--reasoning-control", "")  # JSON override of the default control
if REASONING not in ("", "off", "on") and not GRID:   # --grid takes a list, checked in grid()
    sys.exit("--reasoning must be off or on")          # ablation: preparation turn for every arm, as in ICL
SWITCHES = ["--mode-prompts", "--history", HISTORY] + (["--matched-prep"] if MATCHED_PREP else [])
def batch_name(mode, seeds, scenario, reasoning, date=None):
    """Batch folder name: every setting that defines the runs is in it."""
    return (("DRY_" if DRY else "") + (datetime.date.today().isoformat() if date is None else date)
            + f"_agentic_cost_check_{mode}_seeds{'-'.join(map(str, seeds))}"
            + ("" if HISTORY == "none" else f"_{HISTORY.split('_')[0]}") + ("_prep" if MATCHED_PREP else "")
            + ("" if scenario == "silent_break" else f"_{scenario}")
            + (f"_{OPENROUTER.replace('/', '-')}" if OPENROUTER else "")
            + (f"_reasoning-{reasoning}" if reasoning else ""))
RUN_DIR = os.path.join(ROOT, "runs", batch_name(MODE, SEEDS, SCENARIO, REASONING))
CRED = os.path.expanduser("~/.ecpm_azure.json")

def openrouter_creds():
    k = os.environ.get("OPENROUTER_API_KEY") or getpass.getpass("OpenRouter API key: ").strip()
    return {"key": k}

def drain_typeahead():
    """Discard keys already waiting in the console, so only a fresh answer counts."""
    try:
        import msvcrt                      # Windows console
        while msvcrt.kbhit():
            msvcrt.getwch()
    except ImportError:
        try:
            import termios                 # macOS / Linux terminal
            if sys.stdin.isatty():
                termios.tcflush(sys.stdin, termios.TCIFLUSH)
        except Exception:
            pass

def creds():
    c = json.load(open(CRED)) if os.path.exists(CRED) else {}
    c.setdefault("key", os.environ.get("AZURE_OPENAI_API_KEY") or getpass.getpass("Azure API key: ").strip())
    c.setdefault("endpoint", os.environ.get("AZURE_ENDPOINT") or input("Azure endpoint URL: ").strip())
    c.setdefault("deployment", os.environ.get("AZURE_DEPLOYMENT") or input("Deployment name [gpt-4o]: ").strip() or "gpt-4o")
    with open(CRED, "w") as fh: json.dump(c, fh)
    os.chmod(CRED, 0o600)
    return c

def queue():
    q = os.path.join(RUN_DIR, "queue.txt")
    if not os.path.exists(q):
        with open(q, "w") as fh:
            fh.write("# condition seed repeat  (add lines any time, even during the runs)\n")
            for c in CONDITIONS:
                for s in SEEDS:
                    for r in REPEATS: fh.write(f"{c} {s} {r}\n")
    items = []
    for ln in open(q):
        p = ln.split("#")[0].split()
        if len(p) == 3: items.append((p[0], int(p[1]), int(p[2])))
    return list(dict.fromkeys(items))   # a line added twice is one run, not two (progress and totals)

def tag(c, s, r): return f"s{s}_{c}_r{r}"
def _artifact(t):
    d = os.path.join(RUN_DIR, t)
    fs = [f for f in os.listdir(d) if f.startswith("pilot_") and f.endswith(".json")] if os.path.isdir(d) else []
    return os.path.join(d, fs[0]) if fs else None

def done(t): return os.path.exists(os.path.join(RUN_DIR, t, "condition.json")) and _artifact(t) is not None

def tokens(t):
    """From run_pilot's token_usage_total in the artifact (the project's one token log)."""
    u = json.load(open(_artifact(t))).get("token_usage_total") or {}
    return int(u.get("prompt_tokens") or 0), int(u.get("completion_tokens") or 0)

def run_cost(t):
    """(USD, source) for one run: the provider's billed cost when every call reports one
    (OpenRouter does, cache discounts included), else an estimate from the list prices."""
    a = json.load(open(_artifact(t)))
    calls = a.get("provider_usage_calls") or []
    if calls and all(isinstance((u or {}).get("cost"), (int, float)) for u in calls):
        return sum(u["cost"] for u in calls), "billed"
    i, o = tokens(t)
    return i / 1e6 * PRICE_IN + o / 1e6 * PRICE_OUT, "est."

def cut_off(t):
    """Calls in a run that stopped at the output cap (finish_reason "length")."""
    return sum(1 for u in json.load(open(_artifact(t))).get("provider_usage_calls") or []
               if (u or {}).get("finish_reason") == "length")

def usd(v):
    return f"${v:.4f}" if 0 < v < 0.01 else f"${v:.2f}"   # sub-cent runs (cheap models) stay visible

def log(msg):
    line = f"{datetime.datetime.now():%H:%M:%S} {msg}"
    print(line, flush=True)
    with open(os.path.join(RUN_DIR, "log.txt"), "a") as fh: fh.write(line + "\n")

def reasoning_args(cr):
    """run_pilot flags for an explicit reasoning control (validated again by run_pilot)."""
    if REASONING_CONTROL:
        control, source = json.loads(REASONING_CONTROL), "operator override via --reasoning-control"
    elif OPENROUTER:
        control = {"reasoning": {"enabled": False}} if REASONING == "off" else {"reasoning": {"effort": "medium"}}
        source = "OpenRouter unified reasoning parameter; check reasoning_tokens_total in the artifact"
    else:
        if not cr["deployment"].lower().startswith(("gpt-5", "o1", "o3", "o4")):
            sys.exit(f"{cr['deployment']} has no reasoning control; drop --reasoning or use a reasoning model")
        control = {"reasoning_effort": "none" if REASONING == "off" else "medium"}
        source = "Azure reasoning_effort; none gave 0 reasoning tokens on gpt-5.6-sol (ICL checks, 9 Oct)"
    return ["--reasoning-mode", REASONING, "--reasoning-control-json", json.dumps(control),
            "--reasoning-control-source", source]

def run_one(c, s, r, cr):
    t = tag(c, s, r)
    if DRY:
        prov = ["--provider", "dry-run"]
    elif OPENROUTER:   # OpenAI-compatible endpoint, model id like "deepseek/deepseek-chat"
        prov = ["--provider", "openai", "--base-url", OPENROUTER_URL, "--model", OPENROUTER]
    else:
        prov = ["--provider", "azure", "--model", cr["deployment"], "--azure-endpoint", cr["endpoint"]]
    if not DRY and not OPENROUTER and cr["deployment"].lower().startswith(("gpt-5", "o1", "o3", "o4")):
        prov.append("--azure-reasoning-model")   # reasoning deployments need different request fields
    if REASONING and not DRY:   # dry-run sends nothing, so no control is attached
        prov += reasoning_args(cr)
    # -u: unbuffered, so stdout.txt shows each call as it happens (progress is visible mid-run)
    cmd = [sys.executable, "-B", "-u", "agentic_conditions.py", "run", c, "--repeat", str(r)] + SWITCHES + ["--"] + SETUP + \
          ["--seed", str(s), "--tag", t, "--out", RUN_DIR] + prov
    env = dict(os.environ, AZURE_OPENAI_API_KEY=cr.get("key", ""))
    if OPENROUTER:
        env["OPENAI_API_KEY"] = cr.get("key", "")
    with open(os.path.join(RUN_DIR, "stdout.txt"), "a") as out:
        try:
            ok = subprocess.run(cmd, cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=out,
                                timeout=RUN_TIMEOUT).returncode == 0
        except subprocess.TimeoutExpired:
            ok = False
    return ok and done(t)

def summary():
    subprocess.run([sys.executable, "-B", "agentic_conditions.py", "exposure", RUN_DIR], cwd=ROOT, stdout=subprocess.DEVNULL)

def main():
    if not os.path.exists(os.path.join(ROOT, "agentic_conditions.py")):
        sys.exit("agentic_conditions.py is not in this folder. Run git pull (or use the latest main) first.")
    os.makedirs(RUN_DIR, exist_ok=True)
    cr = {} if DRY else (openrouter_creds() if OPENROUTER else creds())
    log(f"start {'DRY ' if DRY else ''}batch in {RUN_DIR}")
    asked = DRY or YES
    streak = 0   # consecutive failures: three in a row means a setup problem, not a bad run
    while True:
        if os.path.exists(os.path.join(RUN_DIR, "STOP")):
            log("STOP file found, stopping after the last finished run"); break
        todo = [x for x in queue() if not done(tag(*x))]
        if not todo: break
        c, s, r = todo[0]
        log(f"run {tag(c, s, r)} ({len(todo)} left)")
        if not run_one(c, s, r, cr):
            streak += 1
            if streak >= 3:
                tail = open(os.path.join(RUN_DIR, "stdout.txt"), errors="ignore").read().splitlines()[-12:]
                log("3 runs failed in a row, so this is a setup problem. Stopping. Last output:\n  " + "\n  ".join(tail))
                log("Fix it, delete this run folder, and start again.")
                return
            log(f"FAILED {tag(c, s, r)}, see stdout.txt. Moving it to the end of the queue")
            with open(os.path.join(RUN_DIR, "failures.txt"), "a") as fh: fh.write(f"{c} {s} {r}\n")
            q = os.path.join(RUN_DIR, "queue.txt"); lines = open(q).read().splitlines()
            lines = [l for l in lines if l.split("#")[0].split() != [c, str(s), str(r)]]
            if open(os.path.join(RUN_DIR, "failures.txt")).read().count(f"{c} {s} {r}\n") < 2:
                lines.append(f"{c} {s} {r}")
            open(q, "w").write("\n".join(lines) + "\n")
            continue
        streak = 0
        summary()
        fin = [x for x in queue() if done(tag(*x))]
        ti = sum(tokens(tag(*x))[0] for x in fin); to = sum(tokens(tag(*x))[1] for x in fin)
        costs = [run_cost(tag(*x)) for x in fin]
        cost = sum(v for v, _ in costs)
        kind = "billed" if all(k == "billed" for _, k in costs) else "est."
        ri, ro = tokens(tag(c, s, r))
        rc, rk = run_cost(tag(c, s, r))
        log(f"done {len(fin)}/{len(queue())}  this run: in {ri:,} out {ro:,} {usd(rc)} {rk}"
            f"  |  total: in {ti:,} out {to:,} {usd(cost)} {kind}"
            + (f"  |  CUT OFF at the output cap: {cut_off(tag(c, s, r))} call(s)" if cut_off(tag(c, s, r)) else ""))
        if not asked:
            per = cost / len(fin); total = per * len(queue())
            drain_typeahead()   # keys typed or pasted during the run must not answer this question
            ans = input(f"First run used {ti:,} input / {to:,} output tokens ({usd(per)} {kind}). "
                        f"Projected for all {len(queue())} runs: {usd(total)}. Continue? [y/N] ").strip().lower()
            asked = True
            if ans != "y": log("stopped after the first run, as asked"); break
    summary()
    shutil.make_archive(RUN_DIR, "zip", RUN_DIR)
    log(f"finished. Everything is in {RUN_DIR} and {RUN_DIR}.zip")

# ---- --grid: a whole grid, each (mode, condition, reasoning, seed) a batch run by this script --------
GRID_SCENARIOS = ("no_change", "irrelevant", "silent_break", "hard_removal", "redirect", "degradation")

def _alive(pid):
    if os.name == "nt":   # os.kill(pid, 0) would terminate the process on Windows
        import ctypes
        k = ctypes.windll.kernel32; h = k.OpenProcess(0x1000, False, pid)
        if not h: return False
        code = ctypes.c_ulong(); k.GetExitCodeProcess(h, ctypes.byref(code)); k.CloseHandle(h)
        return code.value == 259   # STILL_ACTIVE
    try: os.kill(pid, 0); return True
    except OSError: return False

def _stop(p):   # a batch and the run it started
    if p.poll() is None:
        if os.name == "nt": subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
        else:
            import signal; os.killpg(p.pid, signal.SIGTERM)

def _online():
    if DRY or not OPENROUTER: return True
    import urllib.request
    try: urllib.request.urlopen(urllib.request.Request(OPENROUTER_URL + "/models", method="HEAD"), timeout=20); return True
    except Exception: return False

def _done_arms(mode, scenario, reasoning, seed, since):
    """Arms already finished for this seed, in any batch folder from `since` on (one-seed or five-seed)."""
    head, tail = batch_name(mode, ["@"], scenario, reasoning, date="").split("@")   # "...seeds" / "_suffix"
    pre = "DRY_" if DRY else ""
    done = set()
    for d in os.listdir(os.path.join(ROOT, "runs")):
        if not d.startswith(pre) or d[len(pre):len(pre) + 10] < since: continue
        rest = d[len(pre) + 10:]
        if not (rest.startswith(head[len(pre):]) and rest.endswith(tail)): continue
        seeds = rest[len(head) - len(pre):len(rest) - len(tail)]
        if "_" in seeds or str(seed) not in seeds.split("-"): continue   # exact suffix: no other scenario
        done |= {a for a in CONDITIONS if any(f.startswith("pilot_") and f.endswith(".json") for f in
                 (os.listdir(os.path.join(ROOT, "runs", d, f"s{seed}_{a}_r0")) if os.path.isdir(os.path.join(ROOT, "runs", d, f"s{seed}_{a}_r0")) else []))}
    return done

GLOG_DIR = os.path.join(ROOT, "runs", "_grid_logs")

def glog(msg):   # the grid's own log (log() writes into a single batch folder)
    line = f"{datetime.datetime.now():%H:%M:%S} {msg}"; print(line, flush=True)
    with open(os.path.join(GLOG_DIR, "grid_log.txt"), "a") as fh: fh.write(line + "\n")

def grid():
    import time
    modes = _arg("--mode", "det,sto").split(","); reasonings = _arg("--reasoning", "off,on").split(",")
    scen = _arg("--condition", "all"); scenarios = list(GRID_SCENARIOS) if scen == "all" else scen.split(",")
    workers = int(_arg("--workers", "8")); since = _arg("--since", datetime.date.today().isoformat())
    if set(modes) - {"det", "sto"} or set(reasonings) - {"off", "on"} or set(scenarios) - set(GRID_SCENARIOS):
        sys.exit("--grid: --mode det,sto | --reasoning off,on | --condition all or names from: " + ", ".join(GRID_SCENARIOS))
    jobs = [(m, c, r, s) for r in reasonings for m in modes for c in scenarios for s in SEEDS
            if not (m == "det" and c == "degradation")]   # degradation is undefined in the deterministic world
    total = len(jobs) * len(CONDITIONS)
    logs = os.path.join(ROOT, "runs", "_grid_logs"); os.makedirs(logs, exist_ok=True)
    lock = os.path.join(logs, "grid.lock")
    if os.path.exists(lock) and _alive(int(open(lock).read() or 0)):
        sys.exit(f"another grid is running (PID {open(lock).read()}); stop it first (Ctrl+C in its window)")
    open(lock, "w").write(str(os.getpid()))
    if OPENROUTER and not DRY:   # asked once here, inherited by every batch
        os.environ.setdefault("OPENROUTER_API_KEY", openrouter_creds()["key"])
    elif not DRY: creds()
    if os.name == "nt":   # keep the computer awake while the grid runs (the screen may still turn off)
        import ctypes; ctypes.windll.kernel32.SetThreadExecutionState(ctypes.c_uint(0x80000001))   # unsigned flag
    elif shutil.which("caffeinate"): subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())])
    skip = {"--grid", "--workers", "--since", "--mode", "--condition", "--reasoning", "--seeds", "--yes"}
    passthrough, a = [], sys.argv[1:]
    while a:
        f = a.pop(0); v = [a.pop(0)] if f in VALUE_FLAGS else []
        if f not in skip: passthrough += [f] + v
    pending, running, tries = list(jobs), {}, {}
    count = lambda: sum(len(_done_arms(m, c, r, s, since)) for m, c, r, s in jobs)
    glog(f"grid: {len(jobs)} batches ({total} runs), up to {workers} at once")
    shown = 0
    try:
        while pending or running:
            for j, p in list(running.items()):
                if p.poll() is not None:
                    del running[j]
                    if len(_done_arms(*j, since)) < len(CONDITIONS):
                        if tries[j] < 5: pending.append(j)
                        else: glog(f"gave up on {j} after 5 attempts (see runs/_grid_logs)")
            while pending and len(running) < workers:
                while not _online():
                    glog("network down: no new batches; checking again in 3 minutes"); time.sleep(180)
                m, c, r, s = j = pending.pop(0)
                missing = [x for x in CONDITIONS if x not in _done_arms(m, c, r, s, since)]
                if not missing: continue
                d = os.path.join(ROOT, "runs", batch_name(m, [s], c, r)); os.makedirs(d, exist_ok=True)
                with open(os.path.join(d, "queue.txt"), "w") as fh:   # only the arms still missing
                    fh.write("# condition seed repeat\n" + "".join(f"{x} {s} 0\n" for x in missing))
                tries[j] = tries.get(j, 0) + 1
                running[j] = subprocess.Popen(
                    [sys.executable, "-B", "-u", __file__] + passthrough + ["--seeds", str(s), "--mode", m,
                     "--condition", c, "--reasoning", r, "--yes"], cwd=ROOT, stdin=subprocess.DEVNULL,
                    stdout=open(os.path.join(logs, f"{m}_{c}_{r}_s{s}.txt"), "a"), stderr=subprocess.STDOUT,
                    start_new_session=os.name != "nt")
            if time.time() - shown >= 30:
                glog(f"batches running {len(running)}/{workers} | runs done {count()}/{total} | batches waiting {len(pending)}")
                shown = time.time()
            time.sleep(1 if DRY else 5)
    except KeyboardInterrupt:
        glog("stopping: ending every running batch"); [_stop(p) for p in running.values()]; return 130
    finally:
        if os.path.exists(lock): os.remove(lock)
    out = os.path.join(ROOT, "runs", ("DRY_" if DRY else "") + "GRID_" + (OPENROUTER.replace("/", "-") or "azure")
                       + "_" + datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S"))
    _combine(jobs, since, out)   # one combined table of every batch folder the grid used
    glog(f"grid done: {count()}/{total} runs. Combined results: {out}.zip (agentic_runs.csv, agentic_summary.md)")
    return 0

def _combine(jobs, since, out):
    """Copy every batch folder the grid's runs live in into one folder, summarize it, zip it."""
    keep = set()
    for m, c, r, s in jobs:
        head, tail = batch_name(m, ["@"], c, r, date="").split("@")
        pre = "DRY_" if DRY else ""
        for d in os.listdir(os.path.join(ROOT, "runs")):
            rest = d[len(pre) + 10:]
            if d.startswith(pre) and d[len(pre):len(pre) + 10] >= since and rest.startswith(head[len(pre):]) \
                    and rest.endswith(tail) and "_" not in rest[len(head) - len(pre):len(rest) - len(tail)]:
                keep.add(d)
    os.makedirs(out, exist_ok=True)
    for d in sorted(keep):
        shutil.copytree(os.path.join(ROOT, "runs", d), os.path.join(out, d), dirs_exist_ok=True)
    subprocess.run([sys.executable, "-B", "summarize_agentic_runs.py", out], cwd=ROOT, stdout=subprocess.DEVNULL)
    shutil.make_archive(out, "zip", out)

# ---- --commands: any command list (ICL run_pilot.py lines), N at a time ----------------------------------
def _line_out(line, cwd=None):
    """(argv, output folder) for one command line; the folder is --out/--tag as run_pilot.py writes it."""
    import shlex
    a = [t.strip('"') for t in shlex.split(line, posix=os.name != "nt")]
    if a and os.path.basename(a[0]).lower().startswith("python"):
        a[0] = sys.executable   # the same interpreter as this script
    out = a[a.index("--out") + 1] if "--out" in a else "pilot_artifacts"
    tag = a[a.index("--tag") + 1] if "--tag" in a else None
    return a, (os.path.join(out if os.path.isabs(out) else os.path.join(cwd or ROOT, out), tag) if tag else None)

def _line_done(d):
    """An ICL line is done when its summary.json shows every expected conversation completed."""
    try:
        sm = json.load(open(os.path.join(d, "summary.json")))
        return sm.get("completed_conversations") == sm.get("expected_conversations")
    except (OSError, ValueError, TypeError):
        return False

def commands(path):
    import time
    global GLOG_DIR
    GLOG_DIR = _arg("--state", os.path.join(ROOT, "output", "_commands"))   # output/ is git-ignored: real ICL runs need a clean tree
    workers, retries = int(_arg("--workers", "8")), int(_arg("--retries", "0"))
    cwd = os.path.abspath(_arg("--cwd", ROOT))   # where the lines run; scheduler state stays here, out of that tree
    _out = lambda l: _line_out(l, cwd)
    os.makedirs(GLOG_DIR, exist_ok=True)
    lines = [l.strip() for l in open(path, encoding="utf-8") if l.strip() and not l.strip().startswith("#")]
    failed_txt = os.path.join(GLOG_DIR, "failed.txt")
    earlier = set(open(failed_txt, encoding="utf-8").read().splitlines()) if os.path.exists(failed_txt) else set()
    bad = [l for l in lines if _out(l)[1] is None]
    if bad:
        sys.exit("every line needs --tag (its output folder), e.g.: " + bad[0][:120])
    lock = os.path.join(GLOG_DIR, "commands.lock")
    if os.path.exists(lock) and _alive(int(open(lock).read() or 0)):
        sys.exit(f"another command run is active (PID {open(lock).read()}); stop it first (Ctrl+C in its window)")
    open(lock, "w").write(str(os.getpid()))
    if os.name == "nt":
        import ctypes; ctypes.windll.kernel32.SetThreadExecutionState(ctypes.c_uint(0x80000001))
    elif shutil.which("caffeinate"): subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())])
    def online():
        if not any("openrouter.ai" in l and "dry-run" not in l for l in lines): return True   # only real OpenRouter lines
        import urllib.request
        try: urllib.request.urlopen(urllib.request.Request(OPENROUTER_URL + "/models", method="HEAD"), timeout=20); return True
        except Exception: return False
    def set_aside(d):   # run_suite refuses an existing folder: keep a partial attempt, never overwrite it
        if os.path.exists(d) and not _line_done(d):
            base = os.path.join(os.path.dirname(d), "_failed_attempts"); os.makedirs(base, exist_ok=True)
            n = 1
            while os.path.exists(os.path.join(base, f"{os.path.basename(d)}_{n}")): n += 1
            shutil.move(d, os.path.join(base, f"{os.path.basename(d)}_{n}"))
    pending = [i for i, l in enumerate(lines) if not _line_done(_out(l)[1]) and l not in earlier]
    running, tries, failed = {}, {}, []
    glog(f"commands: {len(lines)} lines, {len(lines) - len(pending) - len(earlier & set(lines))} already done, "
         f"{len(earlier & set(lines))} failed earlier (skipped; remove them from {failed_txt} to retry), up to {workers} at once")
    shown = 0
    try:
        while pending or running:
            for i, p in list(running.items()):
                if p.poll() is not None:
                    del running[i]
                    if not _line_done(_out(lines[i])[1]):
                        if tries[i] <= retries: pending.append(i)
                        else:
                            failed.append(lines[i]); set_aside(_out(lines[i])[1])
                            open(failed_txt, "a", encoding="utf-8").write(lines[i] + "\n")
                            glog(f"FAILED (kept in _failed_attempts, listed in failed.txt): {lines[i][:120]}")
            while pending and len(running) < workers:
                while not online():
                    glog("network down: no new lines; checking again in 3 minutes"); time.sleep(180)
                i = pending.pop(0); a, d = _out(lines[i])
                set_aside(d); tries[i] = tries.get(i, 0) + 1
                running[i] = subprocess.Popen(a, cwd=cwd, stdin=subprocess.DEVNULL, start_new_session=os.name != "nt",
                                              stdout=open(os.path.join(GLOG_DIR, f"{os.path.basename(d)}.txt"), "a"),
                                              stderr=subprocess.STDOUT)
            if time.time() - shown >= 30:
                done_n = sum(_line_done(_out(l)[1]) for l in lines)
                glog(f"lines running {len(running)}/{workers} | done {done_n}/{len(lines)} | waiting {len(pending)} | failed {len(failed)}")
                shown = time.time()
            time.sleep(1)
    except KeyboardInterrupt:
        glog("stopping: ending every running line"); [_stop(p) for p in running.values()]; return 130
    finally:
        if os.path.exists(lock): os.remove(lock)
    glog(f"commands done: {sum(_line_done(_out(l)[1]) for l in lines)}/{len(lines)} lines complete, {len(failed)} failed this session")
    return 1 if failed else 0

if __name__ == "__main__":
    if "--commands" in sys.argv: sys.exit(commands(_arg("--commands", "")))
    if GRID: sys.exit(grid())
    main()

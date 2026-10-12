"""Run one round of study plan v1 unattended (docs/STUDY_PLAN_v1.md).

    python study_round.py --round exploratory [--budget 250] [--acting-workers 16] [--reading-workers 12]
    python study_round.py --round exploratory --dry          # the whole chain on one seed, no API calls

Steps, each a gate: a failure stops everything and is written to the report.
  1. Checks: on main and clean, OPENROUTER_API_KEY set, credit readable, seeds file present, dry run of every family.
  2. Live gate: one exploratory seed, stochastic silent break, every model, nudge off and on (acting), and one reading
     conversation per model (preflight first if a model's configs are not validated). It must show no failed runs, no
     reasoning used with reasoning off, readable answers, and a cost per run within bounds.
  3. The round: acting grids in 6 working copies at once (3 models x nudge off/on) and reading jobs in 3 more, all in
     parallel. A monitor stops everything if the OpenRouter spend since the start passes --budget, or if failures spike.
  4. Bridge probes on the finished acting runs, then the analysis, then one zip with every raw run and the report.
Working copies: ../ecpm-study-wt/<round>/<name>. Results: ../ecpm-study-runs/<round>/. Stdlib only.
"""
import argparse, datetime, glob, json, os, shutil, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODELS = {"haiku": "anthropic/claude-haiku-5.5", "sol": "openai/gpt-5.6-sol", "deepseek": "deepseek/deepseek-v4.1-flash"}
MAX_TOKENS = {"haiku": "32768", "sol": "32768", "deepseek": "65536"}    # as the existing agentic grids
SEEDS = json.load(open(ROOT / "runs" / "study_v1_seeds.json"))


def now():
    return datetime.datetime.now().strftime("%H:%M:%S")


class Round:
    def __init__(self, a):
        self.a, self.rnd = a, a.round
        self.seeds = SEEDS[self.rnd]
        # Dry runs write to their own tree, so their fake answers can never sit where a real round looks for work.
        self.base = ROOT.parent / "ecpm-study-runs" / ("_dry" if a.dry else "")
        self.out = self.base / self.rnd
        self.wt = ROOT.parent / "ecpm-study-wt" / self.rnd
        self.out.mkdir(parents=True, exist_ok=True)
        self.log_path = self.out / "round_log.txt"
        self.procs = {}
        self.start_usage = None
        self.since = datetime.date.today().isoformat()      # runs from the round's first day count as done
        self.env = dict(os.environ, STUDY_RUNS_DIR=str(self.base),
                        STUDY_PRIVATE_DIR=str(ROOT.parent / "ecpm-study-private"))

    # ---------------------------------------------------------------- helpers
    def log(self, msg):
        line = f"{now()} {msg}"
        print(line, flush=True)
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def stop(self, why):
        self.log(f"STOPPED: {why}")
        for name, p in self.procs.items():
            if p.poll() is None:
                self.log(f"  ending {name}")
                try:
                    p.terminate()
                except Exception:
                    pass
        self.report(stopped=why)
        sys.exit(1)

    def git(self, *args, cwd=ROOT):
        return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)

    def usage(self):
        """OpenRouter spend so far for this key, in USD."""
        key = os.environ.get("OPENROUTER_API_KEY", "")
        req = urllib.request.Request("https://openrouter.ai/api/v1/key", headers={"Authorization": "Bearer " + key})
        with urllib.request.urlopen(req, timeout=30) as r:
            return float(json.loads(r.read())["data"]["usage"])

    def spent(self):
        try:
            return self.usage() - self.start_usage
        except Exception:
            return None

    def worktree(self, name):
        """A working copy at exactly this round's commit. A copy left from an earlier attempt is moved to it, so no
        family ever runs older code than the round reports."""
        path = self.wt / name
        commit = self.git("rev-parse", "HEAD").stdout.strip()
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            r = self.git("worktree", "add", "--detach", str(path), commit)
            if r.returncode:
                self.stop(f"git worktree add failed for {name}: {r.stderr.strip()}")
        else:
            r = self.git("checkout", "--force", "--detach", commit, cwd=path)
            if r.returncode:
                self.stop(f"could not move working copy {name} to {commit[:7]}: {r.stderr.strip()}")
        here = self.git("rev-parse", "HEAD", cwd=path).stdout.strip()
        if here != commit:
            self.stop(f"working copy {name} is at {here[:7]}, not the round's commit {commit[:7]}")
        return path

    # ---------------------------------------------------------------- 1. checks
    def checks(self):
        self.log(f"round {self.rnd}: {len(self.seeds)} seeds {self.seeds}")
        if not self.a.dry:                                   # leftovers of an older dry run in the real folder
            for f in list((self.out / "icl").glob("*/icl_*.json"))[:200]:
                if '"dry-run"' in f.read_text(encoding="utf-8", errors="ignore")[:20000]:
                    self.stop(f"dry-run conversations found in {self.out / 'icl'}; move {self.out} away first")
        if self.git("status", "--porcelain", "--untracked-files=no").stdout.strip():
            self.stop("the checkout has uncommitted changes; commit or stash them first")
        branch = self.git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        self.commit = self.git("rev-parse", "HEAD").stdout.strip()
        if branch != "main" and not self.a.allow_branch:
            self.stop(f"on branch {branch!r}, not main (use --allow-branch only for testing)")
        if not self.a.dry:
            if not os.environ.get("OPENROUTER_API_KEY"):
                self.stop("OPENROUTER_API_KEY is not set")
            try:
                self.start_usage = self.usage()
            except Exception as e:
                self.stop(f"cannot read OpenRouter usage for the budget cap: {e}")
            self.log(f"OpenRouter spend before the round: ${self.start_usage:.2f}; budget for this round ${self.a.budget:.0f}")
        self.log(f"commit {self.commit}")

    # ---------------------------------------------------------------- acting
    def acting_cmd(self, model, seeds, modes, conditions, nudge, workers):
        cmd = [sys.executable, "-B", "run_agentic_cost_check.py", "--grid", "--openrouter", MODELS[model],
               "--reasoning", "off", "--mode", modes, "--condition", conditions, "--seeds", ",".join(map(str, seeds)),
               "--workers", str(workers), "--max-tokens", MAX_TOKENS[model], "--since", self.since, "--yes"]
        if nudge:
            cmd.append("--nudge")
        if self.a.dry:
            cmd.append("--dry")
        return cmd

    def launch(self, name, cmd, cwd, env=None):
        logf = open(self.out / f"{name}.log", "a", encoding="utf-8")
        self.procs[name] = subprocess.Popen(cmd, cwd=cwd, stdout=logf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                            env=env or self.env)
        self.log(f"started {name}")

    def wait(self, names, poll=60):
        last = 0
        while any(self.procs[n].poll() is None for n in names):
            time.sleep(5 if self.a.dry else poll)
            if not self.a.dry:
                s = self.spent()
                if s is not None and s > self.a.budget:
                    self.stop(f"budget cap reached: ${s:.2f} spent, cap ${self.a.budget:.0f}")
                if time.time() - last > 600:
                    running = [n for n in names if self.procs[n].poll() is None]
                    self.log(f"running: {', '.join(running)}; spent ${s if s is not None else float('nan'):.2f}")
                    last = time.time()
                self.failure_spike()
        bad = [n for n in names if self.procs[n].returncode not in (0, None)]
        return bad

    def failure_spike(self):
        gave_up = 0
        for f in glob.glob(str(self.wt / "*" / "runs" / "_grid_logs" / "*.txt")):
            try:
                gave_up += open(f, encoding="utf-8", errors="ignore").read().count("gave up on")
            except OSError:
                pass
        if gave_up > self.a.max_gave_up:
            self.stop(f"{gave_up} acting batches gave up after five attempts (limit {self.a.max_gave_up})")

    def grid_zips(self, name):
        pattern = ("DRY_GRID_*" if self.a.dry else "GRID_*") + ".zip"
        return sorted(glob.glob(str(self.wt / name / "runs" / pattern)))

    # ---------------------------------------------------------------- reading
    def reading_cmd(self, model, step="all", extra=()):
        cmd = [sys.executable, "-B", "experiments/study_icl.py", step, "--model", model, "--round", self.rnd,
               "--workers", str(self.a.reading_workers), "--yes", *extra]
        if self.a.dry:
            cmd.append("--dry")
        return cmd

    # ---------------------------------------------------------------- 2. live gate
    def gate(self):
        seed = SEEDS["exploratory"][0]
        self.log(f"live gate on exploratory seed {seed}")
        names = []
        for m in MODELS:
            for nudge in (False, True):
                n = f"gate_{m}_{'nudge' if nudge else 'off'}"
                wt = self.worktree(f"acting_{m}_{'nudge' if nudge else 'off'}")    # the gate's runs count for the round
                self.launch(n, self.acting_cmd(m, [seed], "sto", "silent_break", nudge, 3), wt)
                names.append(n)
        bad = self.wait(names, poll=20)
        if bad:
            self.stop(f"live gate: acting process failed: {bad}")
        problems = []
        for n in names:
            zips = self.grid_zips(n.replace("gate_", "acting_"))
            if not zips:
                problems.append(f"{n}: no grid zip"); continue
            d = self.out / "gate" / n
            shutil.unpack_archive(zips[-1], d)
            import summarize_agentic_runs as S
            rows = S.load(str(d))
            if len(rows) < 3:
                problems.append(f"{n}: {len(rows)} of 3 runs")
            for r in rows:
                if r.get("reasoning_violation"):
                    problems.append(f"{n}: reasoning used with reasoning off")
                if not self.a.dry and (r.get("billed_cost") or 0) > self.a.max_run_cost:
                    problems.append(f"{n}: a run cost ${r['billed_cost']:.2f} (limit ${self.a.max_run_cost})")
        if problems:
            self.stop("live gate: " + "; ".join(problems))
        self.log("live gate passed for acting")
        if not self.a.skip_reading:
            for m in MODELS:
                wt = self.worktree(f"reading_{m}")
                if not self.a.dry:
                    r = subprocess.run(self.reading_cmd(m, "ready"), cwd=wt, env=self.env)
                    if r.returncode:
                        self.stop(f"reading preflight not accepted for {m}; see ../ecpm-study-private/{m}")
            self.log("reading configs validated" if not self.a.dry else "reading gate skipped in a dry run")

    # ---------------------------------------------------------------- 3. the round
    def round(self):
        seeds = self.seeds if not self.a.dry else self.seeds[:1]
        names = []
        for m in MODELS:
            for nudge in (False, True):
                n = f"acting_{m}_{'nudge' if nudge else 'off'}"
                self.launch(n, self.acting_cmd(m, seeds, "det,sto", "all", nudge, self.a.acting_workers), self.worktree(n))
                names.append(n)
        rnames = []
        if not self.a.skip_reading:
            for m in MODELS:
                n = f"reading_{m}"
                env = dict(self.env)
                if self.a.dry:
                    env["STUDY_ICL_SEED_LIMIT"] = "1"
                self.launch(n, self.reading_cmd(m), self.worktree(n), env)
                rnames.append(n)
        bad = self.wait(names + rnames)
        if bad:
            self.log(f"processes that ended with errors: {bad} (their failures are in the logs and the report)")
        self.acting_dirs = []
        for n in names:
            for z in self.grid_zips(n):
                d = self.out / "acting" / Path(z).stem
                if not d.exists():
                    shutil.unpack_archive(z, d)
                self.acting_dirs.append(str(d))

    # ---------------------------------------------------------------- 4. bridge, analysis, archive
    def after(self):
        bridge_dir = self.out / "bridge"
        cmd = [sys.executable, "-B", "experiments/bridge_probes.py", "--out", str(bridge_dir)]
        for d in self.acting_dirs:
            cmd += ["--runs", d]
        if self.a.dry:
            cmd.append("--dry")
        if self.acting_dirs:
            self.log("bridge probes")
            subprocess.run(cmd, cwd=ROOT)
        self.log("reference agent")                      # free: no API calls, the same seeds and cells
        subprocess.run([sys.executable, "-B", "experiments/reference_agent_runs.py", "--round", self.rnd,
                        "--out", str(self.out / "reference")] + (["--modes", "sto", "--scenarios", "silent_break"]
                                                                 if self.a.dry else []), cwd=ROOT)
        self.log("analysis")
        cmd = [sys.executable, "-B", "experiments/study_analysis.py", "--round", self.rnd, "--out", str(self.out / "analysis")]
        for d in self.acting_dirs:
            cmd += ["--acting", d]
        if (bridge_dir / "bridge.csv").exists():
            cmd += ["--bridge", str(bridge_dir / "bridge.csv")]
        if (self.out / "icl_export").exists():
            cmd += ["--icl-export", str(self.out / "icl_export")]
        if self.a.dry:
            cmd += ["--seed-limit", "1"]
        subprocess.run(cmd, cwd=ROOT)
        self.report()
        self.log("archiving every raw run")
        shutil.make_archive(str(self.out.parent / f"study_{self.rnd}_{datetime.date.today().isoformat()}"), "zip", self.out)
        self.log(f"done. Report: {self.out / 'report.md'}")

    def report(self, stopped=None):
        lines = [f"# Study v1, {self.rnd} round", "", f"Commit {getattr(self, 'commit', '?')}. Seeds {self.seeds}."]
        if stopped:
            lines += ["", f"**Stopped:** {stopped}"]
        s = self.spent() if self.start_usage is not None else None
        if s is not None:
            lines.append(f"OpenRouter spend during the round: ${s:.2f}.")
        a = self.out / "analysis" / "report.md"
        if a.exists():
            lines += ["", a.read_text(encoding="utf-8")]
        ref = self.out / "reference" / "summary.md"
        if ref.exists():
            lines += ["", ref.read_text(encoding="utf-8")]
        lines += ["", "Log:", "```", self.log_path.read_text(encoding="utf-8") if self.log_path.exists() else "", "```"]
        (self.out / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", required=True, choices=[k for k in SEEDS if isinstance(SEEDS[k], list)])
    ap.add_argument("--budget", type=float, default=250.0, help="USD cap on OpenRouter spend during the round")
    ap.add_argument("--acting-workers", type=int, default=16)
    ap.add_argument("--reading-workers", type=int, default=12)
    ap.add_argument("--max-run-cost", type=float, default=0.50, help="live gate: largest acceptable cost of one run")
    ap.add_argument("--max-gave-up", type=int, default=20, help="stop if more acting batches give up than this")
    ap.add_argument("--skip-reading", action="store_true")
    ap.add_argument("--allow-branch", action="store_true", help="testing only")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    if a.round == "confirmatory" and not a.dry:
        if "study-plan-v1" not in subprocess.run(["git", "tag"], cwd=ROOT, capture_output=True, text=True).stdout:
            sys.exit("the confirmatory round needs the tag study-plan-v1 first (docs/STUDY_PLAN_v1.md)")
    r = Round(a)
    r.checks()
    if os.name == "nt":                                   # keep the computer awake during the round
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(ctypes.c_uint(0x80000001))
    r.gate()
    r.round()
    r.after()


if __name__ == "__main__":
    main()

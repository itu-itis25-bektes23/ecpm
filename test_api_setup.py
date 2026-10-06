#!/usr/bin/env python3
"""Tests for the additive API setup: key env override, named providers,
--omit-temperature, timeout pass-through, non-retryable missing key,
--telemetry, models.json and experiments/run_matrix.py.

No network: urllib.request.urlopen is replaced by a recorder.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import types
import urllib.request

import model_clients
import run_pilot

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "experiments"))
import run_matrix  # noqa: E402

PASSED = []


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"FAIL {name}: {detail}")
    PASSED.append(name)
    print(f"PASS {name}")


class _Resp:
    def __init__(self, payload):
        self._b = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self._b


SENT = []


def fake_urlopen(req, timeout=None):
    SENT.append({"url": req.full_url, "body": json.loads(req.data),
                 "headers": dict(req.header_items()), "timeout": timeout})
    return _Resp({"choices": [{"message": {"content": "ok"}}],
                  "usage": {"prompt_tokens": 10, "completion_tokens": 5,
                            "completion_tokens_details":
                                {"reasoning_tokens": 2}}})


def with_env(**kv):
    saved = {k: os.environ.get(k) for k in kv}
    for k, v in kv.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    return saved


def missing_key_guard():
    """Return (ok, detail): ok only if a missing OPENAI_API_KEY raises
    MissingAPIKeyError on the first attempt with no retry."""
    calls = []

    def f():
        calls.append(1)
        return model_clients.call_openai_chat("m", "s", [], 10,
                                              "http://x/v1")
    orig_sleep = run_pilot.time.sleep
    run_pilot.time.sleep = lambda s: None
    try:
        run_pilot.with_retry(f, base_delay=0)
        raised = None
    except Exception as ex:  # noqa: BLE001
        raised = ex
    finally:
        run_pilot.time.sleep = orig_sleep
    ok = (isinstance(raised, model_clients.MissingAPIKeyError)
          and len(calls) == 1)
    return ok, f"{type(raised).__name__} after {len(calls)} calls"


def test_clients():
    orig = urllib.request.urlopen
    urllib.request.urlopen = fake_urlopen
    saved = with_env(OPENAI_API_KEY=None, MY_KEY="sekret",
                     DEEPSEEK_API_KEY=None)
    try:
        SENT.clear()
        model_clients.call_openai("m", [], 10, "http://x/v1", 33)
        check("default openai keeps local placeholder and temperature",
              SENT[-1]["headers"]["Authorization"] == "Bearer local"
              and SENT[-1]["body"]["temperature"] == 0)
        model_clients.call_openai("m", [], 10, "http://x/v1", 33,
                                  api_key_env="MY_KEY",
                                  omit_temperature=True)
        check("api_key_env and omit_temperature",
              SENT[-1]["headers"]["Authorization"] == "Bearer sekret"
              and "temperature" not in SENT[-1]["body"])
        model_clients.call_openai_chat("m", "sys", [], 10, "http://x/v1",
                                       timeout=777, api_key_env="MY_KEY")
        check("chat timeout passed through", SENT[-1]["timeout"] == 777)

        # missing key: distinct, not a KeyError, and with_retry gives up
        # after exactly one attempt
        ok, detail = missing_key_guard()
        check("missing key not retried", ok, detail)

        # injected defect: revert require_key to the old os.environ[...]
        # lookup (raises KeyError); the guard must now fail and say why
        orig_rk = model_clients.require_key
        model_clients.require_key = lambda name: os.environ[name]
        try:
            ok, detail = missing_key_guard()
        finally:
            model_clients.require_key = orig_rk
        check("injected defect: KeyError missing key is caught by the "
              "missing-key guard", not ok and "KeyError" in detail
              and "6 calls" in detail, detail)

        # named provider routed through dispatch
        os.environ["DEEPSEEK_API_KEY"] = "dk"
        args = types.SimpleNamespace(
            provider="deepseek", model="deepseek-v4-flash", max_tokens=10,
            base_url="https://api.openai.com/v1", timeout=55,
            api_key_env=None, omit_temperature=False)
        run_pilot.dispatch(args, None, "detection", [], [])
        check("deepseek routed to its base_url and key",
              SENT[-1]["url"] == "https://api.deepseek.com/v1/chat/completions"
              and SENT[-1]["headers"]["Authorization"] == "Bearer dk"
              and SENT[-1]["timeout"] == 55)
    finally:
        urllib.request.urlopen = orig
        with_env(**saved)


def test_telemetry():
    art = {"probes": {"a": {"provider_usage": {"prompt_tokens": 1000,
                                               "completion_tokens": 100}},
                      "b": {"provider_usage": {}}}}
    t = run_pilot.build_telemetry(art, 1.5, 2.0, 8.0)
    check("telemetry sums and prices",
          t["calls"] == 2 and t["n_usage_reported"] == 1
          and t["reasoning_tokens"] is None
          and t["cost"]["status"] == "estimated"
          and abs(t["cost"]["amount"] - 0.0028) < 1e-9, t)
    t = run_pilot.build_telemetry(art, 1.5)
    check("telemetry unpriced without prices",
          t["cost"]["status"] == "unpriced" and t["cost"]["amount"] is None)
    # nothing reported must not read as zero tokens
    t = run_pilot.build_telemetry({"probes": {"a": {"provider_usage": {}}}},
                                  0.1, 1.0, 1.0)
    check("no usage reported gives null tokens and unpriced",
          t["prompt_tokens"] is None and t["cost"]["status"] == "unpriced")


def test_cli_byte_identical():
    with tempfile.TemporaryDirectory() as d:
        base = [sys.executable, "-B", os.path.join(HERE, "run_pilot.py"),
                "--condition", "redirect", "--seed", "7", "--mode", "sto",
                "--turn-mode", "two_turn", "--reelicit", "--tag", "t"]
        outs = []
        for extra, sub in (([], "a"), (["--telemetry"], "b")):
            subprocess.run(base + extra + ["--out", os.path.join(d, sub)],
                           check=True, capture_output=True, cwd=HERE)
            p = os.path.join(d, sub, "t",
                             "pilot_stochastic_two_turn_dryrun.json")
            with open(p) as fh:
                outs.append(json.load(fh))
        a, b = outs
        check("telemetry absent by default", "telemetry" not in a)
        tel = b.pop("telemetry")
        for x in (a, b):
            x.pop("created_utc")
            for pr in x["probes"].values():
                pr.pop("latency_s", None)
                pr.get("metrics", {}).pop("latency_s", None)
                pr.pop("metrics_cumulative", None)
            x.pop("metrics_by_phase")
        check("telemetry is the only difference", a == b)
        check("dry-run telemetry counts calls, unpriced",
              tel["calls"] == 7 and tel["n_usage_reported"] == 0
              and tel["cost"]["status"] == "unpriced", tel)


def test_models_and_matrix():
    with open(os.path.join(HERE, "experiments", "models.json")) as fh:
        models = json.load(fh)
    names = {"gemma4_e4b", "gpt4o", "gpt56_sol", "deepseek_v4_flash",
             "kimi_k27_code"}
    check("models.json has the five profiles", names <= set(models))
    check("kimi omits temperature", models["kimi_k27_code"]
          ["omit_temperature"] is True)
    cells = run_matrix.matrix_cells()
    check("matrix has 12 cells", len(cells) == 12 and ("redirect", 10)
          in cells and ("no_change", 20) in cells)
    cmd = run_matrix.pilot_command(models["kimi_k27_code"], "no_change", 5,
                                   1, "/tmp/x")
    check("matrix command flags",
          "--omit-temperature" in cmd
          and cmd[cmd.index("--protocol") + 1] == "icl_two_response_v1"
          and "--period-b-every-pair" in cmd and "--reelicit" not in cmd
          and cmd[cmd.index("--provider") + 1] == "moonshot"
          and "localization" not in cmd and "--telemetry" in cmd)
    rows = run_matrix.plan_rows("gpt4o", models["gpt4o"], 23, 3000, 600)
    check("plan has no cost when price null",
          all(r["cost_estimate_usd"] == "" for r in rows)
          and rows[0]["calls_estimate"] == 2 * 23)

    # stop after 5 consecutive failures
    calls = []

    def failing(cmd, **kw):
        calls.append(cmd)
        return types.SimpleNamespace(returncode=1)
    with tempfile.TemporaryDirectory() as d:
        ns = run_matrix.build_parser().parse_args(
            ["--model", "gpt4o", "--seeds-file",
             os.path.join(HERE, "runs", "seed_eligibility.json"),
             "--out", d, "--dry-run"])
        rc = run_matrix.run(ns, runner=failing)
    check("matrix stops after 5 consecutive failures",
          rc == 1 and len(calls) == 5, f"rc={rc} calls={len(calls)}")


if __name__ == "__main__":
    test_clients()
    test_telemetry()
    test_cli_byte_identical()
    test_models_and_matrix()
    print(f"\n{len(PASSED)} passed, 0 failed")

"""Tests for the finetuning arm: the scorer, the anchor generator.

Run from the repository root:

    python3 experiments/test_ft_arm.py

Stdlib only. Two kinds of check.

**Scripted answerers.** Five stand-ins sit in the model seat and the table
must separate them: an oracle scores 1.00, a constant answerer reaches the
majority class on preservation and never names the changed pair, a prose
answerer scores identically under the frozen parser while the bare-JSON
diagnostic drops to zero, a stale planner that never replans walks the dead
link.

**Injected defects.** AGENTS.md: a check that has only ever passed has been
run, not tested. Each guard here is handed a damaged input and must fail and
say which guard caught it. Adding a guard without its defect case is the
thing this file exists to prevent.
"""

import os
import sys
import json
import re
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# ROOT first so the environment modules resolve, then HERE in front of it so
# experiments/ wins for this arm's own modules
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import ecpm_eval as E                                     # noqa: E402
import anchors_v22                                        # noqa: E402
import gen_payloads as GP                                 # noqa: E402

K = 5
N_SEEDS = 8
TRIPLE = re.compile(r"\(([A-Z]), (a\d+), ([A-Z])\)")

failures = []


def check(name, condition, detail=""):
    if condition:
        print(f"PASS {name}")
    else:
        print(f"FAIL {name}" + (f": {detail}" if detail else ""))
        failures.append(name)


def expect_raises(name, fn, want_in_message):
    """A guard that never fires has not been tested."""
    try:
        fn()
    except (AssertionError, SystemExit, ValueError, KeyError) as exc:
        msg = str(exc)
        if want_in_message.lower() in msg.lower():
            print(f"PASS {name} (guard fired: {msg[:70]})")
            return
        print(f"FAIL {name}: raised but did not mention "
              f"{want_in_message!r}: {msg[:90]}")
        failures.append(name)
        return
    print(f"FAIL {name}: damaged input was accepted")
    failures.append(name)


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------

rp, _ = GP.load_env(ROOT)
E.attach(ROOT)


def build(condition, deterministic=True, n=N_SEEDS):
    out = []
    for seed in range(80):
        if len(out) >= n:
            break
        try:
            out.append(GP.build_for_seed(rp, seed, deterministic, K, condition))
        except (ValueError, RuntimeError):
            pass
    return out


changed = build("silent_break")
nochange = build("no_change")
seeds = E.common_seeds(changed, nochange)
changed = [p for p in changed if p["seed"] in seeds]
nochange = [p for p in nochange if p["seed"] in seeds]
payloads = changed + nochange


def blocks(pay):
    ev = pay["single"][pay["probes"][0]]
    a = ev.split("Observations, period A:", 1)[1]
    return a.split("Observations, period B:", 1)


def rates(text):
    c = collections.defaultdict(lambda: [0, 0])
    for u, a, v in TRIPLE.findall(text):
        c[(u, a)][1] += 1
        if v != u:
            c[(u, a)][0] += 1
    return c


def make_asker(kind, pay):
    rec = pay["record"]
    ch = rec["change"]
    tgt = (ch["edge"]["from"], ch["action"]) if ch["edge"] else None
    queried = pay["queried_pairs"]

    def ask(messages, _max_new_tokens):
        user = messages[-1]["content"]
        if "did the network" in user:
            body = json.dumps({"changed": False if kind == "constant"
                               else pay["condition"] != "no_change"})
        elif "which single" in user:
            if kind in ("oracle", "stale"):
                pick = tgt
            elif kind == "constant":
                pick = ("A", "a1")
            else:
                ca, cb = rates(blocks(pay)[0]), rates(blocks(pay)[1])
                keys = sorted(set(ca) | set(cb))

                def r(c, p):
                    s, n = c.get(p, (0, 0)) if isinstance(c.get(p), tuple) \
                        else (c[p][0], c[p][1]) if p in c else (0, 0)
                    return s / n if n else 0.0
                pick = max(keys, key=lambda p: (r(ca, p) - r(cb, p), p))
            body = json.dumps({"node": pick[0], "action": pick[1]})
        elif "judge whether" in user:
            say = ((lambda q: False) if kind == "constant"
                   else (lambda q: (q["node"], q["action"]) == tgt))
            body = json.dumps({"pairs": [
                {"node": q["node"], "action": q["action"], "changed": say(q)}
                for q in queried]})
        elif "Plan a route" in user:
            # the stale planner never replans, so it answers with the
            # period-A optimum, which on a silent break walks the dead link
            o = rec["oracle"]["pre" if kind == "stale" else "post"]
            body = json.dumps({"route": [
                {"node": n, "action": a}
                for n, a in zip(o["optimal_route"], o["optimal_actions"])]})
        else:
            body = "{}"
        if kind == "prose":
            return ("Looking at the two periods carefully, here is my "
                    f"answer:\n```json\n{body}\n```\nHope that helps.")
        return body
    return ask


# --------------------------------------------------------------------------
# 1. the scorer separates the scripted answerers
# --------------------------------------------------------------------------

print(f"\n-- scripted answerers, {len(seeds)} matched seeds --")

rows = []
for kind in ("oracle", "constant", "rule", "prose", "stale"):
    for pay in payloads:
        rows += E.run_arm([pay], make_asker(kind, pay), arm=kind,
                          mode="single", verbose=False)

tab = {t["arm"]: t for t in
       E.table(rows, arms=["oracle", "constant", "rule", "prose", "stale"])}


def frac(cell):
    return float(cell.split("=")[-1]) if "=" in str(cell) else None


check("oracle localizes every instance",
      frac(tab["oracle"]["localize"]) == 1.0, tab["oracle"]["localize"])
check("oracle detection is perfect both ways",
      frac(tab["oracle"]["sens"]) == 1.0 and frac(tab["oracle"]["spec"]) == 1.0)
check("constant answerer reaches the majority class on preservation",
      abs(tab["constant"]["pres_acc"] - tab["constant"]["pres_const"]) < 1e-9,
      f"{tab['constant']['pres_acc']} vs {tab['constant']['pres_const']}")
check("constant answerer never names the changed pair",
      frac(tab["constant"]["target_recall"]) == 0.0,
      tab["constant"]["target_recall"])
check("prose scores the same as bare JSON under the frozen parser",
      tab["prose"]["localize"] == tab["rule"]["localize"],
      f"{tab['prose']['localize']} vs {tab['rule']['localize']}")
check("bare_json separates prose from bare JSON",
      frac(tab["prose"]["bare_json"]) == 0.0
      and frac(tab["rule"]["bare_json"]) == 1.0,
      f"prose {tab['prose']['bare_json']}, rule {tab['rule']['bare_json']}")
check("stale planner walks the dead link on every changed instance",
      tab["stale"]["route_status"].get("silent_broken_edge") == len(changed),
      str(tab["stale"]["route_status"]))
check("rows carry provenance",
      all("provenance" in r and r["provenance"]["frozen_sha"] for r in rows))


# --------------------------------------------------------------------------
# 2. anchor golds score correct through the frozen parser
# --------------------------------------------------------------------------

print("\n-- anchor generator --")

import ecpm_parser as ep                                  # noqa: E402

anchors_v22.CHANGED_CONDITIONS = ("silent_break",)
worlds = anchors_v22.build_anchor_set(rp, n_worlds=8, k=K,
                                      stochastic_share=0.0, first_seed=1000,
                                      preservation_changed_repeat=1)


def score_gold(world, item):
    rec = rp.build_record(
        anchors_v22._scenario(world["seed"], world["condition"], K), True)
    return ep.run_probe(rec, item["probe"], item["gold"],
                        queried_pairs=(world["queried_pairs"]
                                       if item["probe"] == "preservation"
                                       else None))["scored"]


def gold_ok(s):
    return (s.get("correct") is True or s.get("accuracy") == 1.0
            or s.get("is_optimal") is True)


bad = [(w["seed"], it["probe"]) for w in worlds for it in w["items"]
       if it["probe"] in ("detection", "localization", "preservation",
                          "adaptation") and not gold_ok(score_gold(w, it))]
check("every anchor gold scores correct", not bad, str(bad[:3]))
check("anchor seeds clear the graded range",
      min(w["seed"] for w in worlds) > anchors_v22.OFFICIAL_MAX_SEED)

a_intro = worlds[0]["items"][0]["prompt"].split("Nodes:")[0]
g_intro = changed[0]["single"]["detection"].split("Nodes:")[0]
check("anchor prompts use the same intro as the graded payloads",
      a_intro == g_intro)


# --------------------------------------------------------------------------
# 3. injected defects: every guard must fire on a damaged input
# --------------------------------------------------------------------------

print("\n-- injected defects --")

# 3.1 a corrupted anchor gold must not score correct
corrupt = dict(worlds[0]["items"][0])
corrupt["gold"] = json.dumps({"changed": "maybe"})
check("a corrupted anchor gold is rejected",
      not gold_ok(score_gold(worlds[0], corrupt)))

# 3.2 an illegal action label must not be counted correct
pay = changed[0]
tgt = pay["facts"]["target_pair"]
illegal = json.dumps({"node": tgt[0], "action": "north"})
check("an illegal action label is not scored correct",
      E.score(pay, "localization", illegal)["scored"].get("correct") is not True,
      illegal)

# 3.3 a preservation reply missing a queried pair must not score 1.00
short = json.dumps({"pairs": [{"node": q["node"], "action": q["action"],
                               "changed": False}
                              for q in pay["queried_pairs"][:-1]]})
s = E.score(pay, "preservation", short)["scored"]
check("an incomplete preservation cover does not score 1.00",
      s.get("accuracy") != 1.0 or s.get("status") != "ok",
      f"status={s.get('status')} accuracy={s.get('accuracy')}")

# 3.4 nothing examined must not score as a pass
empty = E.score(pay, "detection", "")["scored"]
check("an empty reply is not scored as a correct answer",
      empty.get("correct") is not True, str(empty)[:80])

# 3.5 the loader must refuse payloads from the superseded generator
old_style = {"seed": 7, "prompts": {}, "questions": {}}
tmp = os.path.join(HERE, "_defect_payloads")
os.makedirs(tmp, exist_ok=True)
json.dump(old_style, open(os.path.join(tmp, "payload_seed7_old.json"), "w"))
expect_raises("the loader refuses payloads from the old generator",
              lambda: E.load_payloads(tmp), "regenerate")
os.remove(os.path.join(tmp, "payload_seed7_old.json"))
os.rmdir(tmp)

# 3.6 an anchor set below the graded range must be refused
expect_raises("anchor seeds inside the graded range are refused",
              lambda: anchors_v22.build_anchor_set(
                  rp, n_worlds=2, k=K, stochastic_share=0.0, first_seed=7),
              "official")

# 3.7 degradation in deterministic mode must be refused by the environment
expect_raises("degradation is refused in deterministic mode",
              lambda: GP.build_for_seed(rp, 7, True, K, "degradation"),
              "deterministic")


print()
if failures:
    print(f"{len(failures)} FAILURES: {failures}")
    sys.exit(1)
print("ALL FINETUNING ARM TESTS PASSED")

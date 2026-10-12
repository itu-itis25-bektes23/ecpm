"""Offline trimming checks against the unchanged scientific scorer."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import explore_metrics as M
from experiments import h4_trimming_check as T


def fixture(m0=1, m1=5, later=True):
    def step(i, chosen="F", success=False, status="ok"):
        return dict(node="B", action_label="a2" if chosen == "F" else "a1",
                    chosen=chosen, success=success, parse_status=status,
                    raw_text=f"answer {i}")
    a = [step(i) for i in range(m0)]
    b = [step(m0 + i) for i in range(m1)]
    if later:
        b.append(step(m0 + m1, "C", True))
    ex = dict(m0_episodes=[dict(steps=a)], m1_episodes=[dict(steps=b)],
              metrics={"changed_action_usage": dict(node="B", action_label="a2")},
              config=dict(max_context_tokens_est=12000, keep_last_n_turns_min=2),
              transcript=[dict(role="user", content="initial observation")])
    for s in a + b:
        ex["transcript"].extend([dict(role="assistant", content=s["raw_text"]),
                                 dict(role="user", content="observed outcome")])
    data = dict(instance=dict(graph_seed=48, condition="silent_break", deterministic=False),
                model=dict(model="test/model"), explore=ex)
    rescore_fixture(data)
    return data


def rescore_fixture(data):
    ex = data["explore"]
    episodes = lambda phase: [NS(steps=[NS(**s) for s in e["steps"]]) for e in ex[phase]]
    ex["metrics"]["choices_after_consecutive_failures"] = M.choices_after_consecutive_failures(
        NS(change={"edge": ("B", "F")}), episodes("m0_episodes"), episodes("m1_episodes"))


def write_run(root, data, name="run", **meta):
    path = root / name
    path.mkdir()
    (path / "pilot_stochastic_active.json").write_text(json.dumps(data))
    condition = dict(condition="task_only", matched_prep=False, history="none", repeat=0)
    condition.update(meta)
    (path / "condition.json").write_text(json.dumps(condition))


class TrimmingTests(unittest.TestCase):
    def test_report_labels_repeat_choice_not_retention_counts(self):
        with tempfile.TemporaryDirectory() as d:
            write_run(Path(d), fixture())
            proc = subprocess.run([sys.executable, "-B", T.__file__, "--grid", d],
                                  capture_output=True, text=True, check=True)
            self.assertIn("Chose again / runs retaining all six reports", proc.stdout)
            self.assertIn("Chose again / runs missing at least one report", proc.stdout)
            self.assertIn("not counts of retained reports", proc.stdout)
            # One run retained all six reports, but did not choose the target again.
            self.assertIn("| test/model | 0/1 | 0/1 | 0/0 | 0.00 |", proc.stdout)

    def test_m0_carried_streak(self):
        # The old checker reports 0/0 instead of 0/1 for this saved-scorer qualifier.
        with tempfile.TemporaryDirectory() as d:
            write_run(Path(d), fixture())
            _, counts = T.check(d)
            self.assertEqual(counts["visible"], [0, 1])

    def test_success_resets_across_phases(self):
        data = fixture(m0=5, m1=5)
        data["explore"]["m1_episodes"][0]["steps"][0]["success"] = True
        rescore_fixture(data)
        self.assertEqual(T.check_run(data)["status"], "not_qualifying")

    def test_threshold_only_in_m1_and_abort_not_a_decision(self):
        data = fixture(m0=6, m1=0, later=False)
        self.assertEqual(T.check_run(data)["status"], "not_qualifying")
        data = fixture()
        s = data["explore"]["m1_episodes"][0]["steps"][-1]
        s.update(chosen="", parse_status="retries_exhausted")
        rescore_fixture(data)
        checked = T.check_run(data)
        self.assertTrue(checked["qualifying"])
        self.assertEqual(checked["status"], "no_later_source_decision")

    def test_visible_and_trimmed(self):
        data = fixture()
        self.assertEqual(T.check_run(data)["status"], "visible")
        data["explore"]["config"].update(max_context_tokens_est=1, keep_last_n_turns_min=0)
        self.assertEqual(T.check_run(data)["status"], "trimmed")

    def test_saved_scorer_and_transcript_damage(self):
        data = fixture()
        damaged = copy.deepcopy(data)
        damaged["explore"]["metrics"]["choices_after_consecutive_failures"]["chose_again"] = True
        with self.assertRaisesRegex(ValueError, "saved_scorer_mismatch"):
            T.check_run(damaged)
        damaged = copy.deepcopy(data)
        damaged["explore"]["transcript"][1]["content"] = "missing original answer"
        with self.assertRaisesRegex(ValueError, "transcript_step_alignment"):
            T.check_run(damaged)
        damaged = copy.deepcopy(data)
        damaged["explore"]["transcript"][2]["role"] = "assistant"
        with self.assertRaisesRegex(ValueError, "missing_failure_feedback"):
            T.check_run(damaged)

    def test_coverage_and_skipped_identities(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_run(root, fixture(), "qualifier")
            other = fixture(m0=0, m1=1)
            other["instance"]["graph_seed"] = 1
            write_run(root, other, "not_qualifying")
            write_run(root, fixture(), "other_arm", condition="model_first")
            report = T.check_grid(d)
            self.assertEqual(report["counts"], dict(visible=1, not_qualifying=1, out_of_scope=1))
            self.assertTrue(all(r["path"] and len(r["sha256"]) == 64 for r in report["records"]))
            self.assertFalse(any(Path(r["path"]).is_absolute() for r in report["records"]))
            write_run(root, fixture(), "duplicate_copy")
            report = T.check_grid(d)
            self.assertEqual(report["status"], "incomplete")
            self.assertIn("duplicate_identity", [r.get("reason") for r in report["records"]])

    def test_empty_missing_and_damaged_inputs_fail(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.assertEqual(T.check_grid(d)["status"], "could_not_run")
            proc = subprocess.run([sys.executable, "-B", T.__file__, "--grid", d],
                                  capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("could_not_run", proc.stdout)
            write_run(root, fixture())
            (root / "run/condition.json").unlink()
            self.assertEqual(T.check_grid(d)["records"][0]["reason"], "missing_condition")
            (root / "run/condition.json").write_text("not JSON")
            self.assertEqual(T.check_grid(d)["records"][0]["reason"], "invalid_input")


if __name__ == "__main__":
    unittest.main()

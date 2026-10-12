"""Tests for reference_agent.py: it uses only what a model sees, avoids a link its evidence says is broken, and
keeps its memory across the change. Offline."""
import os, re, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_pilot, explore_agent as E, explore_metrics as M, reference_agent as R


def run(seed, scen, det=False):
    inst = run_pilot.make_pair(seed, scen, deterministic=det, matched=True)
    cfg = E.ExploreConfig(max_episodes_m0=4, max_episodes_m1=4, max_steps_per_episode=20, seed=seed)
    ag = R.ReferenceAgent(inst.labels, inst.m0.goal, inst.start, 20, deterministic=det)
    res = E.run_explore_instance(inst, cfg, node_policy_fn=ag.factory)
    return inst, ag, res, M.compute_explore_metrics(inst, res["m0_episodes"], res["m1_episodes"])


class ReferenceAgent(unittest.TestCase):
    def test_never_reads_the_true_world(self):
        src = open(R.__file__, encoding="utf-8").read()
        code = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
        for forbidden in ("mdp.p", ".optimal(", "true_changes", "world_post", ".changes"):
            self.assertNotIn(forbidden, code)
        self.assertEqual(re.findall(r"mdp\.(\w+)", code), ["out_edges"])     # the menu, as a model sees it

    def test_stops_after_six_failures(self):
        _, _, _, m = run(33, "silent_break")
        h4 = m["choices_after_consecutive_failures"]
        self.assertTrue(h4["reached_in_m1"])
        self.assertFalse(h4["chose_again"])
        self.assertEqual(m["goal_success_rate_m1"], 1.0)

    def test_deterministic_one_failure_is_enough(self):
        _, _, _, m = run(33, "silent_break", det=True)
        self.assertEqual(m["changed_action_switch"]["decision_lag"], 1)

    def test_memory_survives_the_change(self):
        _, ag, res, _ = run(33, "no_change")
        m0 = sum(len(e.steps) for e in res["m0_episodes"])
        self.assertEqual(ag.decisions[m0][2], "route")      # first M1 step plans from what M0 taught it


if __name__ == "__main__":
    unittest.main()

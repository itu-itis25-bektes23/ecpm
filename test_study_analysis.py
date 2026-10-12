"""Tests for experiments/study_analysis.py: statistics and claims on inputs with known answers. Offline."""
import csv, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "experiments"))
import study_analysis as S


def run(model="m", seed=1, scen="silent_break", nudge=False, reached=False, again=False, arm="task_only", mode="sto", **kw):
    r = dict(model=model, seed=seed, scenario=scen, nudge=nudge, h4_reached=reached, h4_chose_again=again, arm=arm,
             mode=mode, repeat=0)
    r.update(kw)
    return r


class Stats(unittest.TestCase):
    def test_wilson_matches_reported_h4(self):           # the paper's H4 values, Bonferroni over three models
        self.assertAlmostEqual(S.wilson_lower(19, 21), 0.69, places=2)
        self.assertAlmostEqual(S.wilson_lower(17, 21), 0.58, places=2)
        self.assertAlmostEqual(S.wilson_lower(14, 17), 0.57, places=2)

    def test_mcnemar_exact(self):
        self.assertAlmostEqual(S.mcnemar_one_sided(10, 0), 1 / 1024)
        self.assertAlmostEqual(S.mcnemar_one_sided(0, 0), 1.0)
        self.assertAlmostEqual(S.mcnemar_one_sided(3, 3), 0.65625)

    def test_holm(self):
        self.assertEqual(S.holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])


class Claims(unittest.TestCase):
    def test_c1_counts_only_the_registered_cells(self):
        rows = [run(seed=s, reached=True, again=s % 4 != 0) for s in range(12)]          # 9 of 12 chose again
        rows += [run(seed=99, reached=True, again=True, arm="model_first"),               # not task-only
                 run(seed=98, reached=True, again=True, nudge=True),                      # nudge on
                 run(seed=97, reached=True, again=True, mode="det"),                      # deterministic
                 run(seed=96, reached=True, again=True, scen="redirect")]                 # other scenario
        (c1,) = S.claim_c1(rows)
        self.assertEqual((c1["chose_again"], c1["qualifying"]), (9, 12))
        self.assertEqual(c1["verdict"], "holds")

    def test_c1_needs_ten(self):
        (c1,) = S.claim_c1([run(seed=s, reached=True, again=True) for s in range(9)])
        self.assertEqual(c1["verdict"], "too few")

    def test_c2_pairs_by_seed_and_cell(self):
        rows = []
        for s in range(12):                                   # off reaches six failures, nudge does not
            rows += [run(seed=s, nudge=False, reached=True), run(seed=s, nudge=True, reached=False)]
        rows += [run(seed=50, nudge=False, reached=True)]     # unpaired: ignored
        (c2,) = S.claim_c2(rows)
        self.assertEqual((c2["pairs"], c2["off_only"], c2["on_only"]), (12, 12, 0))
        self.assertAlmostEqual(c2["p"], 1 / 4096)
        self.assertEqual(c2["verdict"], "holds")

    def test_c3_pooled_and_per_model(self):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="")
        w = csv.writer(tmp)
        w.writerow(["model", "id", "arm", "broken", "original", "own_choice", "own_reuse", "full_choice", "full_reuse",
                    "own_error", "full_error"])
        for i in range(8):
            w.writerow(["a", f"a{i}", "task_only", "a1", "a1", "a1", "True", "a2", "False", "", ""])
        for i in range(2):
            w.writerow(["b", f"b{i}", "task_only", "a1", "a1", "a2", "False", "a1", "True", "", ""])
        w.writerow(["b", "b9", "task_only", "a1", "a1", "", "None", "a1", "True", "", ""])      # no valid answer
        tmp.close()
        per, bad = S.claim_c3(tmp.name)
        pooled = [r for r in per if r["model"] == "pooled"][0]
        self.assertEqual((pooled["decisions"], pooled["own_only"], pooled["full_only"], bad), (10, 8, 2, 1))
        self.assertAlmostEqual(pooled["p"], S.mcnemar_one_sided(8, 2))
        os.unlink(tmp.name)


if __name__ == "__main__":
    unittest.main()

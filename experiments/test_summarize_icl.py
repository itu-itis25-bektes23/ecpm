"""Offline checks for compact saved scores and fixed example extracts."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import summarize_icl as report

ROOT = Path(__file__).resolve().parents[1] / 'runs/icl'
INPUT = ROOT / 'final/results.json'


class ReportingTests(unittest.TestCase):
    def test_complete_matrix_and_saved_table_agreement(self):
        data = report.load(INPUT)
        self.assertEqual(len(data['runs']), 18)
        self.assertEqual(sum(len(r['turns']) for r in data['runs']), 36)
        self.assertEqual(sum(t['scored']['beliefs']['n_queried'] for r in data['runs'] for t in r['turns'].values()), 180)
        result = report.report(INPUT)
        self.assertEqual(report.markdown(result), (ROOT / 'final/results.md').read_text())
        self.assertEqual(result, report.report(INPUT))
        self.assertEqual(report.markdown(result).count('|---|'), 2)

    def test_all_six_examples_and_injected_text_defect(self):
        data = report.load(INPUT)
        report.check_examples(data, ROOT / 'examples')
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'examples'
            shutil.copytree(ROOT / 'examples', target)
            p = next(target.glob('*.json'))
            example = json.loads(p.read_text())
            example['messages'][1]['content'] += 'changed'
            p.write_text(json.dumps(example))
            with self.assertRaisesRegex(ValueError, 'example-text hash guard'):
                report.check_examples(data, target)

    def test_invalid_beliefs_keep_failures_and_valid_routes(self):
        bad = next(r for r in report.load(INPUT)['runs'] if r['condition'] == 'on' and r['turns']['B']['parsed']['beliefs']['status'] != 'ok')
        result = report.summarize([bad])
        b = result['turns']['B']
        self.assertEqual(b['belief_exact_all_queried'], report.fraction(0, 5))
        self.assertEqual(b['destination_scored'], report.fraction(0, 0))
        self.assertEqual(b['p_mae_visible'], {'value': None, 'n': 0})
        self.assertEqual(b['valid_route_all_runs'], report.fraction(1, 1))
        self.assertEqual(result['preservation']['mean_control_preservation_all_runs']['value'], 0)
        self.assertEqual(result['preservation']['mean_control_preservation_conditional'], {'value': None, 'n': 0})

    def test_unresolvable_remains_diagnostic(self):
        runs = report.load(INPUT)['runs']
        before = report.summarize(runs)
        for r in runs:
            for t in r['turns'].values():
                t['scored']['route_belief_diagnostic']['status'] = 'route_unresolvable'
        after = report.summarize(runs)
        self.assertEqual(before['well_formed_all_responses'], after['well_formed_all_responses'])
        for turn in ('A', 'B'):
            self.assertEqual(before['turns'][turn]['valid_route_all_runs'], after['turns'][turn]['valid_route_all_runs'])

    def test_empty_missing_and_damaged_input(self):
        original = report.load(INPUT)
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'scores.json'
            with self.assertRaises(FileNotFoundError):
                report.load(p)
            for defect, guard in [('empty', 'input guard'), ('matrix', 'matrix guard'),
                                  ('score', 'saved-score hash guard'), ('aggregate', 'saved-aggregate agreement guard')]:
                data = copy.deepcopy(original)
                if defect == 'empty': data['runs'] = []
                elif defect == 'matrix': data['runs'].pop()
                else:
                    t = data['runs'][0]['turns']['A']
                    pair = t['scored']['beliefs']['per_pair'][0]
                    pair['correct'] = not pair['correct']
                    if defect == 'aggregate': t['source_scores_sha256'] = report.score_hash(t['scored'])
                p.write_text(json.dumps(data))
                with self.subTest(defect=defect), self.assertRaisesRegex(ValueError, guard):
                    report.report(p)
            p.write_text('{damaged')
            with self.assertRaises(json.JSONDecodeError): report.load(p)


if __name__ == '__main__':
    unittest.main()

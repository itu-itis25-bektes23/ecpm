"""Regression checks for H1 cohort selection; no model requests."""
import csv
import gzip
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('h1_selection_under_test', Path(__file__).with_name('h1_icl.py'))
h1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h1)


class H1CohortSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def raw(self, subdir, run_id, state='completed', extra=None):
        path = self.root / subdir / (run_id + '.json')
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {'run_id': run_id, 'state': state}
        data.update(extra or {})
        path.write_text(json.dumps(data, sort_keys=True))
        return str(path)

    def export(self, rows, fields=('run_id', 'operational_status')):
        path = self.root / 'runs/results/icl' / h1.RESULTS['Sol'] / 'metrics.csv.gz'
        path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(path, 'wt') as fh:
            writer = csv.DictWriter(fh, fields)
            writer.writeheader()
            writer.writerows(rows)

    def test_published_ids_exclude_quarantined_records(self):
        self.export([{'run_id': 'valid', 'operational_status': 'valid'},
                     {'run_id': 'valid', 'operational_status': 'valid'},
                     {'run_id': 'historical', 'operational_status': 'quarantined'}])
        with patch.object(h1, 'ROOT', str(self.root)):
            self.assertEqual(h1.published_ids('Sol'), {'valid'})

    def test_missing_status_column_fails_closed(self):
        self.export([{'run_id': 'valid'}], ('run_id',))
        with patch.object(h1, 'ROOT', str(self.root)):
            with self.assertRaisesRegex(ValueError, 'operational_status'):
                h1.published_ids('Sol')

    def test_conflicting_export_statuses_fail_closed(self):
        self.export([{'run_id': 'same', 'operational_status': 'valid'},
                     {'run_id': 'same', 'operational_status': 'quarantined'}])
        with patch.object(h1, 'ROOT', str(self.root)):
            with self.assertRaisesRegex(ValueError, 'conflicting export statuses'):
                h1.published_ids('Sol')

    def test_completed_recovery_selected_over_incomplete_attempt(self):
        run_id = 'icl_expanded_case'
        self.raw('first', run_id, state='failed')
        complete = self.raw('recovery', run_id)
        self.raw('quarantined', 'icl_expanded_old')
        rows, selected = h1.select_inputs(str(self.root), {run_id}, 'Sol')
        self.assertEqual(selected, [complete])
        self.assertEqual(sum(r[-1] for r in rows), 1)
        self.assertEqual(len(rows), 3)

    def test_identical_completed_copies_count_once(self):
        run_id = 'icl_expanded_same'
        first = self.raw('a', run_id)
        self.raw('b', run_id)
        rows, selected = h1.select_inputs(str(self.root), {run_id}, 'Sol')
        self.assertEqual(selected, [first])
        self.assertEqual([r[-1] for r in rows], [True, False])

    def test_conflicting_completed_copies_rejected(self):
        run_id = 'icl_expanded_conflict'
        self.raw('a', run_id)
        self.raw('b', run_id, extra={'different_response': True})
        with self.assertRaisesRegex(ValueError, 'conflicting completed sources'):
            h1.select_inputs(str(self.root), {run_id}, 'Sol')

    def test_incomplete_source_does_not_satisfy_coverage(self):
        run_id = 'icl_expanded_incomplete'
        self.raw('a', run_id, state='failed')
        with self.assertRaisesRegex(ValueError, 'completed sources missing'):
            h1.select_inputs(str(self.root), {run_id}, 'Sol')

    def test_filename_and_artifact_identity_must_match(self):
        run_id = 'icl_expanded_expected'
        self.raw('a', run_id, extra={'run_id': 'icl_expanded_wrong'})
        with self.assertRaisesRegex(ValueError, 'filename/artifact run ID mismatch'):
            h1.select_inputs(str(self.root), {run_id}, 'Sol')


if __name__ == '__main__':
    unittest.main()

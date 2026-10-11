"""Offline publication guards, including damaged and empty saved exports."""
import copy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import publish_deepseek_icl as report


class Publication(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cells = list(report.rows(report.DEFAULT/'cells.csv'))

    def test_full_saved_exports_and_generated_tables(self):
        tables, aggregate, check = report.generate(report.DEFAULT)
        self.assertEqual(check['completed'], 655)
        self.assertEqual(check['incomplete'], 5)
        self.assertEqual(check['metric_rows'], 201090)
        self.assertEqual(check['requests'], 4009)
        self.assertEqual(check, report.read(report.DEFAULT/'validation.json'))
        self.assertEqual(tables, (report.DEFAULT/'tables.md').read_text())
        self.assertIn('preservation_self_conditional', aggregate)
        self.assertIn('preservation_truth_conditional', aggregate)
        self.assertIn('null', aggregate)

    def test_empty_and_duplicate_cells_fail(self):
        with self.assertRaisesRegex(ValueError, 'coverage'):
            report.validate_cells([])
        bad = copy.deepcopy(self.cells)
        bad[1]['cell_id'] = bad[0]['cell_id']
        with self.assertRaisesRegex(ValueError, 'duplicate cell'):
            report.validate_cells(bad)

    def test_wrong_world_and_scored_failure_fail(self):
        bad = copy.deepcopy(self.cells)
        bad[0]['graph_seed'] = '999'
        with self.assertRaisesRegex(ValueError, 'grid'):
            report.validate_cells(bad)
        bad = copy.deepcopy(self.cells)
        next(c for c in bad if c['status']=='failed_terminal')['operational_valid'] = 'true'
        with self.assertRaisesRegex(ValueError, 'operational status'):
            report.validate_cells(bad)

    def test_empty_metrics_not_clean_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ('cells.csv','provenance.json'):
                (root/name).write_bytes((report.DEFAULT/name).read_bytes())
            report.gz_write(root/'metrics.csv.gz', b'cell_id\n')
            with self.assertRaisesRegex(ValueError, 'metric export hash'):
                report.generate(root)
            provenance = report.read(root/'provenance.json')
            provenance['source_export_sha256']['scientific_metrics.csv'] = hashlib.sha256(b'cell_id\n').hexdigest()
            report.dump(root/'provenance.json', provenance)
            with self.assertRaisesRegex(ValueError, 'metric row count'):
                report.generate(root)

    def test_nulls_and_boolean_numerators(self):
        self.assertIsNone(report.number('null'))
        self.assertEqual(report.number('0'), Decimal(0))
        self.assertEqual(report.number('True'), Decimal(1))
        self.assertEqual(report.number('False'), Decimal(0))
        self.assertIn('null', report.csv_text([{'missing': None, 'zero': 0}]))

    def test_public_scan_rejects_private_path_and_fake_credential(self):
        for text, guard in [('/Users/example/config.json','private path'), ('sk-'+'FAKE'*8,'credential pattern')]:
            with self.assertRaisesRegex(ValueError, guard): report.scan(text)
        report.scan('OPENROUTER_API_KEY is an environment-variable name, not its value.')


if __name__ == '__main__': unittest.main(verbosity=2)

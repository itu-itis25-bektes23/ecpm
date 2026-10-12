"""Tests for the study's ICL additions: the seed switch and experiments/study_icl.py. Offline, stdlib only."""
import importlib, json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'experiments'))


class SeedSwitch(unittest.TestCase):
    def test_default_grid_unchanged(self):
        env = dict(os.environ); env.pop('ECPM_ICL_SEEDS', None)
        out = subprocess.run([sys.executable, '-B', '-c', 'import icl_expanded as x, icl_study_seeds as s; s.apply(x); '
                              'print(len(x.configurations()), x.SEEDS)'], cwd=ROOT, env=env, capture_output=True, text=True)
        self.assertEqual(out.stdout.strip(), '55 (8, 13, 25, 0, 1)')

    def test_switch_adds_seeds_once(self):
        env = dict(os.environ, ECPM_ICL_SEEDS='145, 162,8')
        out = subprocess.run([sys.executable, '-B', '-c', 'import icl_expanded as x, icl_study_seeds as s; s.apply(x); s.apply(x); '
                              'print(len(x.configurations()), x.SEEDS)'], cwd=ROOT, env=env, capture_output=True, text=True)
        self.assertEqual(out.stdout.strip(), '77 (8, 13, 25, 0, 1, 145, 162)')

    def test_seeds_file(self):
        s = json.loads((ROOT / 'runs' / 'study_v1_seeds.json').read_text())
        self.assertEqual(len(s['exploratory']), 10); self.assertEqual(len(s['confirmatory']), 51)
        self.assertTrue(set(s['exploratory']) <= set(range(0, 31)))
        self.assertTrue(min(s['confirmatory']) >= 131)
        self.assertFalse(set(s['exploratory']) & set(s['confirmatory']))


class StudyIcl(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ['STUDY_PRIVATE_DIR'] = os.path.join(self.tmp.name, 'priv')
        os.environ['STUDY_RUNS_DIR'] = os.path.join(self.tmp.name, 'runs')
        import study_icl
        self.m = importlib.reload(study_icl)

    def tearDown(self):
        os.environ.pop('STUDY_PRIVATE_DIR'); os.environ.pop('STUDY_RUNS_DIR'); os.environ.pop('STUDY_ICL_ENDPOINTS_JSON', None)
        self.tmp.cleanup()

    def endpoints(self, tags):
        p = os.path.join(self.tmp.name, 'ep.json')
        json.dump({'data': {'endpoints': [{'tag': t, 'provider_name': t.title(), 'supported_parameters': ['max_tokens', 'reasoning'],
                   'max_completion_tokens': 65536, 'context_length': 200000,
                   'pricing': {'prompt': '0.000001', 'completion': '0.000002'}} for t in tags]}}, open(p, 'w'))
        os.environ['STUDY_ICL_ENDPOINTS_JSON'] = p

    def test_jobs_cover_the_round(self):
        rows = self.m.grid('exploratory')
        self.assertEqual(len(rows), 10 * 11 * 3 * 2)
        self.assertEqual(len(set(self.m.tag('haiku', *g) for g in rows)), len(rows))

    def test_config_pins_the_maker_endpoint(self):
        for key, tags, want in (('sol', ['azure', 'openai'], 'openai'), ('haiku', ['anthropic', 'google-vertex'], 'anthropic'),
                                ('deepseek', ['deepseek', 'ionstream', 'deepinfra', 'novita'], 'ionstream'),
                                # the endpoints OpenRouter listed for Sol on 12 October 2026
                                ('sol', ['openai/flex', 'openai', 'openai/fast', 'azure', 'azure/us',
                                         'amazon-bedrock/us-east-1', 'azure/eu'], 'openai')):
            self.endpoints(tags)
            self.m.config(key)
            w = json.load(open(self.m.priv(key) / f'{key}_off_candidate.json'))
            e = w['deployment']['effective']
            self.assertEqual(e['provider_slug'], want)
            self.assertEqual(e['hosted_evidence']['request_fields'], {'reasoning': {'enabled': False, 'exclude': False}})
            self.assertEqual(w['deployment']['model'], self.m.MODELS[key]['model'])

    def test_single_tier_only(self):
        self.endpoints(['openai/flex', 'azure'])
        self.m.config('sol')
        w = json.load(open(self.m.priv('sol') / 'sol_off_candidate.json'))
        self.assertEqual(w['deployment']['effective']['provider_slug'], 'openai/flex')

    def test_pinned_provider_missing_stops(self):
        self.endpoints(['deepseek', 'deepinfra', 'novita'])
        with self.assertRaises(SystemExit):
            self.m.config('deepseek')

    def test_ambiguous_endpoints_stop(self):
        self.endpoints(['azure', 'amazon-bedrock'])
        with self.assertRaises(SystemExit):
            self.m.config('sol')


if __name__ == '__main__':
    unittest.main()

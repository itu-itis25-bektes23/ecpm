"""Offline expanded contract and injected-defect tests. No live connections."""

import copy
import ast
import csv
import itertools
import json
import sys
import subprocess
import tempfile
import unittest
import types
import zipfile
from pathlib import Path
from unittest.mock import patch

import icl_expanded as x
import icl_model_first as old
import icl_model_first_runner as runner
from experiments import preview_icl_expanded as report
from experiments.preview_icl_model_first import compatible_identity
from test_icl_graph import config, envelope


def turns(answers):
    return {k: {'raw_response': v} for k, v in answers.items()}


def wrapper(mode='off', profile='gemma_31b_together', policy=old.HISTORY_POLICY):
    c = config(profile, mode)
    c['pricing'] = {'input_per_million': 1, 'output_per_million': 2, 'source': 'SYNTHETIC TEST ONLY'}
    return {'deployment': c, 'expanded': {'protocol': x.PROTOCOL,
        'preparation_policy': x.PREPARATION_POLICY, 'history_policy': policy,
        'reasoning_mode': mode, 'schedule': x.SCHEDULE, 'output_allowances': [4096],
        'stage_limits_source': 'SYNTHETIC TEST ONLY', 'system_message_source': 'SYNTHETIC TEST ONLY',
        'context_source': 'SYNTHETIC TEST ONLY'}}


class Expanded(unittest.TestCase):
    def setUp(self):
        self.world = x.build_world(8, 'det', 'silent_break')

    def run_synthetic(self, folder, w=None, mode='off', arm='model_first', policy=old.HISTORY_POLICY):
        return runner.run_once(w or self.world, arm, 1, report.arguments(arm, mode, policy), None, folder, x)

    def test_all_55_worlds_oracles_controls_and_shared_prompts(self):
        seen_a, seen_questions = {}, {}
        unreachable = noise = 0
        for seed, mode, scenario in x.configurations():
            w = x.build_world(seed, mode, scenario)
            q = x.queries(w)
            self.assertEqual(len(q), 4)
            self.assertEqual(seen_questions.setdefault(seed, q), q)
            self.assertEqual(seen_a.setdefault((seed, mode), w['A']), w['A'])
            self.assertEqual(len(w['true_changes']), int(scenario != 'no_change'))
            a, b = {tuple((r['node'], r['action'])): r for r in w['A']['graph']}, {tuple((r['node'], r['action'])): r for r in w['B']['graph']}
            self.assertEqual(len(w['controls']), 4)
            for c in w['controls']:
                key = c['node'], c['action']; self.assertEqual(a[key], b[key])
            answers = x.oracle_answers(w)
            scored = x.score_conversation(w, 'model_first', turns(answers))
            self.assertTrue(scored['periods']['B']['detection_correct'])
            self.assertTrue(scored['periods']['B']['localization_correct'])
            for period in ('A', 'B'):
                s = scored['periods'][period]
                self.assertEqual(s['beliefs']['joint_exact']['value'], 1)
                self.assertEqual(s['beliefs']['joint_exact']['denominator'], len(w[period]['required_pairs']))
                for r in s['routes'].values():
                    self.assertTrue(r['solution_correct'])
                    unreachable += not r['oracle_reachable']
                    self.assertEqual(r['regret'], 0 if r['oracle_reachable'] else None)
                texts = [x.prompts(w, period, arm) for arm in x.ARMS]
                for stage in ('task', 'readout'):
                    self.assertEqual(len({p[stage] for p in texts if stage != 'task' or 'prepare' in p}), 1)
                evidence = [(p.get('prepare', p['task'])).split('\n\n', 1)[0].replace(x.graph_text(w[period]) + '\n', '') for p in texts]
                self.assertEqual(len(set(evidence)), 1)
                for arm, p in zip(x.ARMS, texts):
                    self.assertEqual('graph' in p.get('prepare', p['task']).lower(), arm == 'graph_given')
                    self.assertFalse(any(word in p.get('prepare', p['task']).lower() for word in ('target', 'oracle', 'evaluator', 'intervention', 'control pair')))
                    if period == 'A': self.assertNotIn('Period B', p.get('prepare', p['task']))
            if mode == 'sto' and scenario == 'no_change':
                estimates = x.estimates(w['A']); updated = x.estimates(w['B'], estimates)
                noise += sum(a != b for a, b in zip(estimates, updated))
                self.assertIsNone(json.loads(answers['B_task'])['changed_pair'])
                self.assertFalse(any(r['changed'] for r in json.loads(answers['B_readout'])['pairs']))
                self.assertEqual(scored['periods']['B']['specificity']['value'], 1)
                self.assertIsNone(scored['periods']['B']['localization_changed_case'])
        self.assertEqual(len(x.configurations()), 55)
        self.assertGreater(unreachable, 0)
        self.assertGreater(noise, 0)

    def test_no_gate_and_old_queries_fixtures_hashes(self):
        for seed in x.SEEDS:
            x.build_world(seed, 'det', 'silent_break')
        for seed in (8, 13, 25):
            prior = old.verify_world(seed)
            new = x.build_world(seed, 'det', 'silent_break')
            self.assertEqual(x.queries(new)[0], old.queries(prior)[0])
            for p in ('A', 'B'):
                core = {k: v for k, v in new[p].items() if k != 'required_pairs'}
                self.assertEqual({k: prior[p][k] for k in core}, core)
            self.assertEqual(new['controls'], prior['controls'])
            old.verify_prompts(prior)
            for history in x.HISTORY_POLICIES: old.verify_histories(prior, history)
        for invalid in ((8, 'det', 'degradation'), (2, 'det', 'no_change'), (True, 'det', 'redirect')):
            with self.assertRaises(ValueError): x.build_world(*invalid)

    def test_actual_history_both_modes_malformed_final_preserved(self):
        raw = x.oracle_answers(self.world)
        raw['A_readout'] = 'MALFORMED REPORT\n\t retained verbatim'
        raw['A_task'] = '{broken task'
        for arm, policy in itertools.product(x.ARMS, x.HISTORY_POLICIES):
            calls = x.schedule(self.world, arm, raw, policy)
            self.assertEqual([c['id'] for c in calls], [p + '_' + s for p in ('A', 'B') for s in x.stages(arm)])
            self.assertTrue(all(c['max_output_tokens'] == 4096 for c in calls))
            b = next(c for c in calls if c['id'] == ('B_task' if arm == 'baseline_task' else 'B_prepare'))['messages']
            self.assertIn({'role': 'assistant', 'content': raw['A_task']}, b)
            report_message = {'role': 'assistant', 'content': raw['A_readout']}
            self.assertEqual(report_message in b, policy == old.HISTORY_POLICY)
            question = {'role': 'user', 'content': x.prompts(self.world, 'A', arm)['readout']}
            self.assertEqual(question in b, policy == old.HISTORY_POLICY)
            for c in calls[:len(x.stages(arm))]:
                self.assertFalse(any(raw['B_prepare'] in m['content'] for m in c['messages']))

    def test_removal_localization_route_and_denominator(self):
        w = x.build_world(8, 'det', 'hard_removal')
        answers = x.oracle_answers(w)
        task = x.parse_task(answers['B_task'], w, 'B')
        self.assertTrue(task['localization']['valid'])
        target = tuple(w['true_changes'][0])
        row = next(r for r in json.loads(answers['B_readout'])['pairs'] if (r['state'], r['action']) == target)
        self.assertEqual((row['available'], row['destination'], row['p_success']), (False, None, None))
        bad = json.loads(answers['B_task'])
        bad['routes'][0] = {'query_id': 'q0', 'reachable': True, 'steps': [{'state': target[0], 'action': target[1]}]}
        self.assertFalse(x.parse_task(json.dumps(bad), w, 'B')['routes']['q0']['valid'])
        # The additive explicit pair set, not a fixed sixteen, drives denominators.
        small = copy.deepcopy(w)
        for p in ('A', 'B'):
            small[p]['graph'] = small[p]['graph'][:5]
            small[p]['required_pairs'] = small[p]['required_pairs'][:5]
        parsed = x.parse_readout(answers['B_readout'], small['B'])
        self.assertEqual(old.score_readout(parsed, small, 'B')['joint_exact']['denominator'], 5)

    def test_sample_error_tolerance_is_not_change_threshold(self):
        w = x.build_world(8, 'sto', 'no_change')
        answers = x.oracle_answers(w)
        obj = json.loads(answers['B_readout'])
        obj['pairs'][0]['p_success'] = max(0, obj['pairs'][0]['p_success'] - .1)
        answers['B_readout'] = json.dumps(obj)
        score = x.score_conversation(w, 'model_first', turns(answers))
        self.assertEqual(score['periods']['B']['beliefs']['transition_exact']['numerator'], 15)
        self.assertEqual(score['periods']['B']['beliefs']['transition_tolerance']['numerator'], 16)
        self.assertTrue(score['periods']['B']['detection_correct'])
        self.assertEqual(score['periods']['B']['beliefs']['p_mae_truth_conditional']['n'], 16)
        self.assertEqual(score['periods']['B']['beliefs']['p_mae_visible_conditional']['n'], 16)
        self.assertNotEqual(score['periods']['B']['beliefs']['p_mae_truth_conditional']['value'],
                            score['periods']['B']['beliefs']['p_mae_visible_conditional']['value'])
        changed = x.build_world(8, 'sto', 'degradation')
        self.assertTrue(changed['true_changes'])
        self.assertEqual(x.oracle_answers(changed)['B_task'].count('"changed": true'), 1)
        tiny_change = copy.deepcopy(w)
        row = tiny_change['B']['graph'][0]
        row['p_success'] -= .01
        tiny_change['true_changes'] = [[row['node'],row['action']]]
        self.assertTrue(json.loads(x.oracle_answers(tiny_change)['B_task'])['changed'])
        before = dict(available=True,destination='B',p_success=1)
        after = dict(before,p_success=.85)
        self.assertTrue(x.close_transition(before,after,x.parser.BELIEF_P_TOL_STOCHASTIC))
        after['p_success'] = .849
        self.assertFalse(x.close_transition(before,after,x.parser.BELIEF_P_TOL_STOCHASTIC))

    def test_evidence_reference_unextended_and_not_truth_leaking(self):
        w = x.build_world(8, 'det', 'redirect')
        result = x.evidence_reference(w['visible'], x.queries(w))
        self.assertFalse(result['baseline']['detection'])
        self.assertFalse(json.loads(result['answers']['B_task'])['changed'])
        self.assertFalse(any(r['changed'] for r in json.loads(result['answers']['B_readout'])['pairs']))
        self.assertIn('published_ecpm_baseline', result['identity'])
        view = {k: self.world['A'][k] for k in ('rows', 'menu', 'required_pairs')}
        a = x.estimates(view)
        s, action = view['required_pairs'][0]
        view['rows'] = [f'[{s}, {action}, {s}]' if r.startswith(f'[{s}, {action},') else r for r in view['rows']]
        b = x.estimates(view, a)
        self.assertEqual(b[0]['p_success'], 0)
        self.assertEqual(b[0]['destination'], a[0]['destination'])
        # Same visible data/questions is the complete input, irrespective of hidden world changes.
        self.assertEqual(result, x.evidence_reference(copy.deepcopy(w['visible']), copy.deepcopy(x.queries(w))))

    def test_tied_routes_and_unreachable_remain_truth_graded(self):
        rows = [dict(node=s, action=a, available=True, destination=t, p_success=1) for s,a,t in
                [('A','a1','B'), ('A','a2','C'), ('B','a1','D'), ('C','a1','D')]]
        q = {'start': 'A', 'goal': 'D'}
        for a, t in (('a1','B'), ('a2','C')):
            parsed = {'valid': True, 'value': {'reachable': True, 'steps': [{'state':'A','action':a}, {'state':t,'action':'a1'}]}}
            r = old.grade_route(parsed, rows, q)
            self.assertTrue(r['optimal']); self.assertEqual(r['regret'], 0)
        r = old.grade_route({'valid':True, 'value':{'reachable':False,'steps':[]}}, [], q)
        self.assertTrue(r['solution_correct']); self.assertIsNone(r['regret'])

    def test_malformed_rows_independent_values_and_preservation(self):
        a = x.oracle_answers(self.world)
        obj = json.loads(a['B_readout'])
        obj['pairs'][0]['extra'] = True
        obj['pairs'][1]['p_success'] = 'null'
        a['B_readout'] = json.dumps(obj)
        score = x.score_conversation(self.world, 'model_first', turns(a))
        b = score['periods']['B']
        self.assertFalse(b['readout_parsed']['well_formed'])
        self.assertEqual(b['beliefs']['transition_exact']['numerator'], 15)
        self.assertTrue(all(r['solution_correct'] for r in b['routes'].values()))
        # Dropping a control is a failure in all-controls, not in its conditional denominator.
        control = self.world['controls'][0]
        obj['pairs'] = [r for r in obj['pairs'] if (r['state'], r['action']) != (control['node'], control['action'])]
        a['B_readout'] = json.dumps(obj)
        p = x.score_conversation(self.world, 'model_first', turns(a))['preservation_tolerance']['self']
        self.assertEqual(p['all_controls']['denominator'], 4)
        self.assertLess(p['conditional']['denominator'], 4)
        self.assertFalse(p['all_four_correct'])

    def test_plans_and_mode_validation_no_fake_readiness(self):
        p = report.plan('gemma_e4b')
        self.assertEqual((p['conversations'], p['responses']), (1100, 6160))
        self.assertIsNone(p['estimated_cost'])
        self.assertTrue(all('--deployment-config' not in r['argv'] for r in p['rows']))
        for mode in ('off', 'on'):
            w = wrapper(mode)
            x.validate_config(w, 'gemma_31b_together', mode, old.HISTORY_POLICY)
            supported = report.plan('gemma_31b_together', [w])
            self.assertEqual(supported['conversations'], 275)
            self.assertTrue(all(r['reasoning_mode'] == mode for r in supported['rows']))
            with self.assertRaises(ValueError): x.validate_config(w, 'gemma_31b_together', 'off' if mode == 'on' else 'on', old.HISTORY_POLICY)
            bad = copy.deepcopy(w); bad['deployment']['supported_request_fields'].remove('reasoning')
            with self.assertRaises(ValueError): x.validate_config(bad, 'gemma_31b_together', mode, old.HISTORY_POLICY)
        for profile in x.controls.MODELS:
            for mode in ('off','on'):
                s = runner.settings(profile, 0, profile != 'sol', 4096, mode)
                self.assertEqual(s.get('max_tokens', s.get('max_completion_tokens')), 4096)
                self.assertEqual(s.get('reasoning_effort') if profile == 'sol' else s['reasoning'],
                    ('none' if mode == 'off' else 'medium') if profile == 'sol' else {'enabled':mode=='on'} if profile == 'gemma_31b_together' else mode)

    def test_every_world_command_reaches_expanded_entry(self):
        # The older resolver rejects a no-change localization probe. The new
        # protocol asks for null localization and must not inherit that guard.
        for seed, mode, scenario in x.configurations():
            argv = report.command(seed,mode,scenario,'model_first','off',old.HISTORY_POLICY,'gemma_e4b','offline-test')
            with patch.object(sys, 'argv', argv[2:]), patch.object(x, 'run_suite') as run:
                x.pilot.main()
            sc, args, unused = run.call_args.args
            self.assertEqual((sc['seed'], args.mode, sc['condition']), (seed,mode,scenario))
            self.assertEqual((sc['k'], sc['budget'], sc['evidence_seed'], sc['rendering']), (10,10,0,'F2_shuffled'))
            self.assertEqual((args.repeats,args.sampling_seeds,args.max_tokens), (1,[0],4096))

    def test_raw_reconciliation_quarantine_and_unknown_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = self.run_synthetic(tmp)
            path = Path(tmp) / (a['run_id'] + '.json')
            good = report.summarize([path])
            self.assertEqual(good['runs'][0]['operational_status'], 'valid')
            self.assertTrue(all(r['reasoning_tokens'] is None and r['billing_reconciliation'] is None for r in good['request_usage']))
            for name, mutate in (
                ('usage', lambda t: t.update(provider_usage={'completion_tokens':1})),
                ('raw', lambda t: t.update(provider_response_raw=t['provider_response_raw'].replace('synthetic', 'length', 1))),
                ('mode', lambda t: t['request_body'].update(reasoning='on'))):
                bad = json.loads(json.dumps(a)); mutate(bad['turns']['B_task'])
                path.write_text(json.dumps(bad))
                result = report.summarize([path])
                self.assertEqual(result['runs'][0]['operational_status'], 'quarantined', name)
                self.assertEqual(len(result['metrics']), 1)
                self.assertEqual(result['metrics'][0]['denominator'], 0)
            # Rehashing a changed raw envelope must not hide copied stop/usage facts.
            for field in ('finish', 'usage'):
                bad = json.loads(json.dumps(a)); t = bad['turns']['B_task']
                if field == 'finish': t['provider_response']['choices'][0]['finish_reason'] = 'length'
                else: t['provider_response']['usage'] = {'completion_tokens':800}
                t['provider_response_raw'] = json.dumps(t['provider_response'])
                t['provider_response_raw_sha256'] = old.digest(t['provider_response_raw'])
                t['provider_response_sha256'] = runner.canonical(t['provider_response'])
                path.write_text(json.dumps(bad))
                self.assertEqual(report.summarize([path])['runs'][0]['operational_status'], 'quarantined')

    def test_wrong_answers_remain_scored_and_duplicate_repeat_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            answers = x.oracle_answers(self.world); answers['A_readout'] = 'not JSON'
            with patch.object(x, 'oracle_answers', return_value=answers):
                a = self.run_synthetic(tmp)
            path = Path(tmp) / (a['run_id'] + '.json')
            r = report.summarize([path])
            metric = next(v for v in r['metrics'] if v['metric']=='transition_exact' and v['period']=='A')
            self.assertEqual((metric['numerator'],metric['denominator']), (0,16))
            duplicate = copy.deepcopy(a); duplicate['run_id'] += '_different'
            second = Path(tmp) / 'duplicate.json'; second.write_text(json.dumps(duplicate))
            with self.assertRaisesRegex(ValueError, 'duplicate'): report.summarize([path,second])
            base = runner.canonical(compatible_identity(a))
            for key, value in [('model','another'), ('scorer','future'), ('scenario','redirect'),
                               ('implementation_commit','other'), ('deployment_sha256','other'), ('reasoning_mode','on')]:
                different = copy.deepcopy(a); different['identity'][key] = value
                self.assertNotEqual(base, runner.canonical(compatible_identity(different)))
            different = copy.deepcopy(a); different['synthetic'] = False
            self.assertNotEqual(base, runner.canonical(compatible_identity(different)))
        with tempfile.TemporaryDirectory() as empty:
            with self.assertRaisesRegex(ValueError,'empty'): report.summarize([empty])
            Path(empty,'damaged.json').write_text('{}')
            with self.assertRaises(KeyError): report.summarize([empty])

    def test_on_operational_checks_require_positive_evidence(self):
        c = wrapper('on')['deployment']
        good = envelope('not JSON', 'gemma_31b_together', 'on')
        self.assertTrue(x.controls.reasoning_check(good,'on',c['effective'],'gemma_31b_together',c)['mode_verified'])
        good['usage']['completion_tokens_details']['reasoning_tokens'] = 0
        good['choices'][0]['message']['reasoning_content'] = ''
        self.assertFalse(x.controls.reasoning_check(good,'on',c['effective'],'gemma_31b_together',c)['mode_verified'])

    def test_mocked_live_on_uses_shared_controls_and_stops_on_contradiction(self):
        profile = 'gemma_31b_together'
        w = wrapper('on', profile)
        args = report.arguments('model_first', 'on', old.HISTORY_POLICY, profile)
        args.provider, args.model = 'openai', w['deployment']['model']
        answers = list(x.oracle_answers(self.world).values())
        for contradiction in (False, True):
            calls = []
            def reply(body, config, timeout):
                calls.append(body)
                self.assertEqual(body['reasoning'], {'enabled':True})
                self.assertEqual(body['max_tokens'],4096)
                data = envelope(answers[len(calls)-1],profile,'off' if contradiction else 'on')
                data['usage']['prompt_tokens_details'] = None
                return 200,json.dumps(data)
            with tempfile.TemporaryDirectory() as tmp, patch.object(x.pilot,'_git_dirty',return_value=False), patch.object(runner,'call_provider',side_effect=reply):
                if contradiction:
                    with self.assertRaisesRegex(RuntimeError,'operational failure saved'):
                        runner.run_once(self.world,'model_first',1,args,w,tmp,x)
                    a = json.loads(next(Path(tmp).glob('*.json')).read_text())
                    self.assertEqual(a['state'],'incomplete')
                    self.assertEqual(len(calls),1)
                else:
                    a = runner.run_once(self.world,'model_first',1,args,w,tmp,x)
                    self.assertEqual(len(calls),6)
                    self.assertTrue(all(runner.audit_artifact(a,x).values()))
                    self.assertTrue(all(t['cached_tokens'] is None for t in report.summarize([tmp])['request_usage']))

    def test_1100_shared_runner_synthetic_paths(self):
        with tempfile.TemporaryDirectory() as root, patch.object(runner, 'call_provider', side_effect=AssertionError('network forbidden')):
            result = report.coverage(Path(root) / 'coverage')
            self.assertEqual((result['worlds'], result['synthetic_conversations'], result['synthetic_responses']), (55,1100,6160))
            self.assertEqual(len(result['history_hashes']),1100)
            self.assertEqual(len(result['prompt_hashes']),1540)

    def test_graph_probability_text_is_short_and_round_trips(self):
        for seed, mode, scenario in x.configurations():
            world = x.build_world(seed, mode, scenario)
            for period in ('A', 'B'):
                for row, line in zip(world[period]['graph'], x.graph_text(world[period]).splitlines()[2:]):
                    text = line.rsplit(' | ', 1)[1]
                    if row['p_success'] is None:
                        self.assertEqual(text, 'null')
                    else:
                        self.assertEqual(float(text).hex(), float(row['p_success']).hex())
        view = {'graph': [dict(node='A', action='a1', available=True, destination='B', p_success=p)
                          for p in (0.0, 1.0, .1, .3, .12345678901234567, 1e-7)]}
        texts = [line.rsplit(' | ', 1)[1] for line in x.graph_text(view).splitlines()[2:]]
        self.assertEqual(texts[:4], ['0', '1', '0.1', '0.3'])
        self.assertEqual(float(texts[4]), .12345678901234567)
        self.assertNotEqual(float(format(.12345678901234567, '.6g')), .12345678901234567)

    def test_added_csv_metrics_keep_false_and_unscored_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'source'; source.mkdir()
            a = self.run_synthetic(source)
            # Reporting consumes saved scores, not reparsed answers. Exercise
            # all three possible diagnostic values in the saved-score fixture.
            p = a['scores']['periods']['A']
            p['beliefs']['complete_graph_exact'] = False
            for q, value in zip(('q0','q1','q2'), (True,False,None)):
                for name in ('own_report_optimal','own_report_no_route_correct'):
                    p['routes'][q][name] = value
            (source / (a['run_id'] + '.json')).write_text(json.dumps(a))
            target = Path(tmp) / 'export'
            with patch.object(sys, 'argv', ['preview_icl_expanded.py', '--summarize', str(source), '--out', str(target)]):
                report.main()
            with (target / 'metrics.csv').open() as stream:
                rows = list(csv.DictReader(stream))
            def row(metric, query='null'):
                return next(r for r in rows if r['period']=='A' and r['metric']==metric and r['query_id']==query)
            self.assertEqual((row('complete_graph_exact')['numerator'],row('complete_graph_exact')['denominator']), ('0','1'))
            for name in ('own_report_optimal','own_report_no_route_correct'):
                for q, expected in [('q0',('1','1','1.0')),('q1',('0','1','0.0')),('q2',('null','0','null'))]:
                    r = row(name,q)
                    self.assertEqual(tuple(r[k] for k in ('numerator','denominator','value')),expected)

    def test_neutral_spontaneous_and_baseline_are_distinct(self):
        self.assertEqual(len(x.ARMS), 5)
        for period in ('A', 'B'):
            neutral = x.prompts(self.world, period, 'task_only')
            spontaneous = x.prompts(self.world, period, 'spontaneous')
            graph = x.prompts(self.world, period, 'graph_given')
            baseline = x.prompts(self.world, period, 'baseline_task')
            self.assertTrue(neutral['prepare'].endswith(x.NEUTRAL_PREP))
            self.assertTrue(graph['prepare'].endswith(x.NEUTRAL_PREP))
            self.assertTrue(spontaneous['prepare'].endswith(x.SPONTANEOUS_PREP))
            self.assertIn('Task rules and output format:', neutral['prepare'])
            self.assertNotIn('prepare', baseline)
            self.assertIn('Shuffled single-step observations', baseline['task'])
            for arm in x.ARMS:
                text = x.prompts(self.world, period, arm).get('prepare', baseline['task'])
                self.assertNotIn('successes divided', text)
                self.assertNotIn('count every row', text)
                self.assertNotIn('retain the latest destination', text)

    def test_balanced_queries_use_a_only_and_allow_ties(self):
        for seed, mode, scenario in x.configurations():
            w = x.build_world(seed, mode, scenario)
            flags = w['query_design'].values()
            self.assertGreaterEqual(sum(r['canonical_A_optimum_uses_target'] for r in flags), 2)
            self.assertGreaterEqual(sum(not r['canonical_A_optimum_uses_target'] for r in flags), 1)
            changed_b = copy.deepcopy(w)
            changed_b['B']['graph'] = []
            changed_b['B']['rows'] = []
            self.assertEqual(x.queries(changed_b), x.queries(w))
        w = x.build_world(0, 'det', 'silent_break')
        self.assertTrue(any(r['canonical_A_optimum_uses_target'] and not r['all_A_optima_use_target']
                            for r in w['query_design'].values()))

    def test_updating_uses_own_a_route_and_malformed_b_is_failure(self):
        answers = x.oracle_answers(self.world)
        a = json.loads(answers['A_task'])
        a['routes'][0]['steps'] = [{'state':'G','action':'a2'}, {'state':'B','action':'a2'}, {'state':'H','action':'a1'}]
        answers['A_task'] = json.dumps(a)
        s = x.score_conversation(self.world, 'baseline_task', turns(answers))
        self.assertFalse(s['updating']['queries']['q0']['necessary_update_eligible'])
        self.assertTrue(s['periods']['B']['routes']['q0']['optimal'])
        self.assertEqual(s['updating']['necessary_update_rate']['denominator'], 2)
        # The other two necessary queries now fail syntactically, without
        # disappearing from the success-rate denominator.
        answers['B_task'] = 'bad answer'
        s = x.score_conversation(self.world, 'baseline_task', turns(answers))
        self.assertEqual(s['updating']['necessary_update_rate'], old.fraction(0, 2))
        self.assertEqual(s['updating']['unnecessary_replan_rate']['denominator'], 0)

    def test_degradation_does_not_always_require_replanning(self):
        w = x.build_world(8, 'sto', 'degradation')
        a = x.oracle_answers(w)
        s = x.score_conversation(w, 'model_first', turns(a))
        self.assertTrue(any(r['A_route_used_changed_pair'] and r['A_route_still_optimal_in_B']
                            and not r['necessary_update_eligible'] for r in s['updating']['queries'].values()))
        none = x.build_world(8, 'sto', 'no_change')
        a = x.oracle_answers(none)
        s = x.score_conversation(none, 'model_first', turns(a))
        self.assertEqual(s['updating']['necessary_update_rate'], old.fraction(0, 0))

    def test_equally_good_replan_is_not_harmful(self):
        rows = [dict(node=s,action=a,available=True,destination=t,p_success=1)
                for s,a,t in [('A','a1','B'),('A','a2','C'),('B','a1','D'),('C','a1','D')]]
        q = dict(query_id='q0',start='A',goal='D')
        def parsed(action, middle):
            return {'valid':True, 'value':dict(query_id='q0',reachable=True,
                steps=[dict(state='A',action=action),dict(state=middle,action='a1')])}
        a,b = parsed('a1','B'),parsed('a2','C')
        periods = {p:{'task_parsed':{'routes':{'q0':r}},'routes':{'q0':old.grade_route(r,rows,q)}}
                   for p,r in [('A',a),('B',b)]}
        s = x.updating(periods,dict(route_queries=[q],true_changes=[],B=dict(graph=rows)))
        self.assertEqual(s['unnecessary_replan_rate'],old.fraction(1,1))
        self.assertEqual(s['harmful_unnecessary_replan_rate'],old.fraction(0,1))

    def test_preparation_extraction_does_not_guess_unsupported_prose(self):
        v = self.world['A']
        rows = json.loads(x.oracle_answers(self.world)['A_readout'])
        exact = x.preparation.score(json.dumps(rows),v)
        self.assertEqual(exact['pair_exact'],dict(numerator=16,denominator=16))
        rows['pairs'][0]['p_success'] = .2
        wrong = x.preparation.score(json.dumps(rows),v)
        self.assertEqual(wrong['pair_exact'],dict(numerator=15,denominator=16))
        unknown = x.preparation.score('At G the a1 action leads toward E with certainty.',v)
        self.assertEqual(unknown['status'],'needs_review')
        self.assertIsNone(unknown['pair_exact']['numerator'])
        self.assertEqual(unknown['pair_exact']['denominator'],0)
        neutral = x.preparation.score('Each attempt costs one. Output JSON with reachable and steps.',v)
        self.assertFalse(neutral['transition_content'])
        self.assertEqual(neutral['pair_exact'],dict(numerator=0,denominator=16))
        table = ['| State | Action | Destination | p_success |','|---|---|---|---|']
        table += [f"| {r['node']} | {r['action']} | {r['destination']} | {r['p_success']} |" for r in v['graph']]
        good = x.preparation.score('\n'.join(table),v)
        self.assertTrue(good['table_present']); self.assertEqual(good['pair_exact']['numerator'],16)
        conflict = x.preparation.score('\n'.join(table + ['| G | a1 | B | 1 |']),v)
        self.assertEqual(conflict['status'],'needs_review')
        self.assertEqual(conflict['pair_exact']['denominator'],0)
        malformed = x.preparation.score('[{"state":{},"action":[],"destination":{}}]',v)
        self.assertEqual(malformed['status'],'needs_review')
        partial_table = x.preparation.score('| State | Action | Destination |\n| G | a1 | E |',v)
        self.assertTrue(partial_table['table_present'])
        self.assertEqual(partial_table['status'],'needs_review')
        bad_number = x.preparation.score('G: a1 -> E (p=1..0)',v)
        self.assertEqual(bad_number['status'],'needs_review')

    def test_preparation_probability_prose_preserves_decimals_and_conflicts(self):
        v = x.build_world(8, 'sto', 'silent_break')['A']
        table = ['| State | Action | Destination | p_success |', '|---|---|---|---|']
        table += [f"| {r['node']} | {r['action']} | {r['destination']} | {r['p_success']} |"
                  for r in v['graph']]
        row = v['graph'][0]
        for probability in (row['p_success'], 0.9, 0.01):
            text = '\n'.join(table + [f"{row['node']}:{row['action']} success probability is {probability}."])
            score = x.preparation.score(text, v)
            extracted = next(r for r in score['rows']
                             if (r['state'], r['action']) == (row['node'], row['action']))
            self.assertEqual(extracted['p_success'], row['p_success'])
            self.assertEqual(score['status'], 'explicit_extraction' if probability == row['p_success'] else 'needs_review')
        # A contradictory explicit zero cannot overwrite an explicit table row.
        text = '\n'.join(table + [f"{row['node']}:{row['action']} success probability is 0.0."])
        self.assertEqual(x.preparation.score(text, v)['status'], 'needs_review')
        # A stated exception may refine a global rule used by grouped lists.
        text = 'All actions have success probability of 1.0.\nG: a1 -> E\nG:a1 success probability is 0.0.'
        self.assertEqual(x.preparation.extract(text, v)['rows'][0]['p_success'], 0.0)
        text = 'All actions have success probability of 1.5.\nG: a1 -> E'
        self.assertIsNone(x.preparation.extract(text, v)['rows'][0]['p_success'])

    def test_k_limits_repeat_five_and_identity_separation(self):
        with self.assertRaisesRegex(ValueError,'K=10'):
            x.build_world(8,'sto','silent_break',20)
        with self.assertRaisesRegex(ValueError,'K=10'):
            report.plan('gemma_e4b',k=20)
        w = x.build_world(8,'sto','silent_break',10)
        counts = {}
        for line in w['A']['rows']:
            pair = tuple(line.strip('[]').split(', ')[:2])
            counts[pair] = counts.get(pair,0) + 1
        self.assertEqual(set(counts.values()),{10})
        self.assertEqual(x.queries(w),x.queries(self.world))
        args = report.arguments('baseline_task','off',old.HISTORY_POLICIES[1])
        one = x.identity(self.world,'baseline_task',1,args,None)
        fifth = x.identity(self.world,'baseline_task',5,args,None)
        self.assertEqual(fifth['repeat_seed_label'],4)
        self.assertNotEqual(one['world_sha256'],x.identity(w,'baseline_task',1,args,None)['world_sha256'])
        with tempfile.TemporaryDirectory() as tmp:
            records = [runner.run_once(self.world,'baseline_task',r,args,None,tmp,x) for r in range(1,6)]
            summary = runner.write_summary(tmp,expected=5,design_api=x)
            self.assertTrue(summary['operational_gate_pass'])
            exported = report.summarize([tmp])
            self.assertEqual(len(exported['runs']),5)
            self.assertEqual(len({r['group'] for r in exported['runs']}),1)
            self.assertEqual(len(exported['request_usage']),20)
            stat = next(s for s in exported['repeat_statistics']
                        if s['metric']=='complete_graph_exact' and s['period']=='A')
            self.assertEqual((stat['n'],stat['mean'],stat['sample_std']),(5,1,0))
            one_run = report.summarize([str(Path(tmp) / (records[0]['run_id'] + '.json'))])
            self.assertTrue(all(s['sample_std'] is None for s in one_run['repeat_statistics']))
        plan = report.plan('gemma_e4b',k=10,repeats=5)
        self.assertEqual((plan['conversations'],plan['responses']),(5500,30800))
        self.assertTrue(all(r['k']==10 for r in plan['rows']))
        self.assertEqual(runner.block_cost_plan(self.world,'baseline_task',None,repeats=5,design_api=x)['requests'],20)


class PreparationScope(unittest.TestCase):
    def assert_scoped(self, text, period):
        self.assertIn('For later task-answer turns only, not this preparation turn:', text)
        self.assertIn('On those later task-answer turns, return only a JSON object with a routes list.', text)
        self.assertIn('Current turn: preparation, not a task answer.', text)
        self.assertIn('Task-answer JSON is not required on this turn.', text)
        self.assertNotIn('Return only a JSON object with a routes list.', text)
        if period == 'B':
            self.assertIn('On the later task-answer turn, also report changed', text)

    def test_scope_all_arms_periods_histories_and_modes(self):
        for mode, arm, history in itertools.product(x.SYSTEM, x.ARMS, x.HISTORY_POLICIES):
            w = x.build_world(8, mode, 'silent_break')
            answers = x.oracle_answers(w)
            answers['A_prepare'] = '{malformed preparation retained exactly\n\t'
            answers['A_readout'] = 'MALFORMED A REPORT'
            calls = x.schedule(w, arm, answers, history)
            for call in calls:
                period, stage = call['id'].split('_')
                if stage == 'prepare':
                    text = call['messages'][-1]['content']
                    self.assert_scoped(text, period)
                    instruction = x.MODEL_PREP if arm == 'model_first' else x.SPONTANEOUS_PREP if arm == 'spontaneous' else x.NEUTRAL_PREP
                    self.assertTrue(text.endswith(instruction))
                    self.assertIn('approximately 250 words', text)
                    if period == 'B':
                        self.assertIn({'role':'assistant','content':answers['A_prepare']}, call['messages'])
                        self.assertEqual({'role':'assistant','content':answers['A_readout']} in call['messages'], history == 'retained_reports_v2')
                    else:
                        self.assertNotIn('Period B', text)
            if arm == 'baseline_task':
                self.assertEqual(len(calls), 4)
                self.assertNotIn('Current turn: preparation', calls[0]['messages'][-1]['content'])
            else:
                self.assertEqual(len(calls), 6)
        # Inject the original missing scope; the same guard must reject it.
        with patch.object(x, 'task_guide', side_effect=lambda period, preparation=False: 'Return only a JSON object with a routes list.'):
            with self.assertRaisesRegex(AssertionError, 'later task-answer'):
                self.assert_scoped(x.prompts(w, 'A', 'model_first')['prepare'], 'A')

    def test_only_preparation_text_and_policy_change_from_published_source(self):
        try:
            source = subprocess.check_output(['git', 'show',
                '96cdd374b1d9acceb30096de4df929bb8cdabe34:icl_expanded.py'],
                cwd=Path(x.__file__).parent, text=True, stderr=subprocess.DEVNULL)
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Zip downloads and shallow clones lack this commit; CI checks out full history.
            self.skipTest('needs git history containing 96cdd374b1d9 (published v2 source)')
        prior = types.ModuleType('published_expanded_scope_reference')
        exec(compile(source, '<published expanded source>', 'exec'), prior.__dict__)
        def unchanged_nodes(text):
            return [ast.dump(n) for n in ast.parse(text).body
                # Sol acceptance changes only admission/identity plumbing; its
                # default-equivalence and damaged-input guards have separate tests.
                if not (isinstance(n, ast.FunctionDef) and n.name in
                        ('task_guide', 'prompts', 'identity', 'validate_config', 'validate_output_allowance',
                         'schedule', 'run_suite', 'audit_identity'))
                and not (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'PREPARATION_POLICY' for t in n.targets))]
        self.assertEqual(unchanged_nodes(source), unchanged_nodes(Path(x.__file__).read_text()))
        self.assertEqual(prior.PREPARATION_POLICY, 'five_arms_length_target_v2')
        self.assertEqual(x.PREPARATION_POLICY, 'five_arms_scoped_preparation_v3')
        for seed, mode, scenario in x.configurations():
            w = x.build_world(seed, mode, scenario)
            self.assertEqual(w, prior.build_world(seed, mode, scenario))
            self.assertEqual(x.oracle_answers(w), prior.oracle_answers(w))
            for period, arm in itertools.product(('A','B'), x.ARMS):
                before, after = prior.prompts(w, period, arm), x.prompts(w, period, arm)
                self.assertEqual(before['task'], after['task'])
                self.assertEqual(before['readout'], after['readout'])
                if arm == 'baseline_task':
                    self.assertEqual(before, after)
                else:
                    self.assertEqual(before['prepare'].split('\n\n')[0], after['prepare'].split('\n\n')[0])
                    self.assert_scoped(after['prepare'], period)

    def test_policy_separates_identity_and_rejects_old_readiness(self):
        w = x.build_world(8, 'det', 'silent_break')
        args = report.arguments('model_first', 'off', old.HISTORY_POLICY)
        current = x.identity(w, 'model_first', 1, args, None)
        with patch.object(x, 'PREPARATION_POLICY', 'five_arms_length_target_v2'):
            previous = x.identity(w, 'model_first', 1, args, None)
        self.assertNotEqual(runner.canonical(current), runner.canonical(previous))
        self.assertNotEqual(compatible_identity({'identity':current,'synthetic':True,'deployment':None}),
                            compatible_identity({'identity':previous,'synthetic':True,'deployment':None}))
        config_wrapper = wrapper()
        config_wrapper['expanded']['preparation_policy'] = 'five_arms_length_target_v2'
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            x.validate_config(config_wrapper, 'gemma_31b_together', 'off', old.HISTORY_POLICY)

    def test_review_exposes_empty_task_json_without_rescore_or_retry(self):
        w = x.build_world(8, 'det', 'silent_break')
        answers = x.oracle_answers(w)
        answers['A_prepare'] = ' \n{"routes":[]}\t'
        answers['B_prepare'] = '{"routes":[],"changed":true,"changed_pair":{"state":"G","action":"a1"}}'
        with tempfile.TemporaryDirectory() as folder, patch.object(x, 'oracle_answers', return_value=answers), \
             patch.object(runner, 'call_provider', side_effect=AssertionError('no live calls')):
            a = runner.run_once(w, 'model_first', 1, report.arguments('model_first','off',old.HISTORY_POLICY), None, folder, x)
            self.assertEqual(a['state'], 'completed')
            self.assertEqual(len(a['turns']), 6)
            self.assertTrue(all(runner.audit_artifact(a, x).values()))
            paths = list(Path(folder).glob('*.json'))
            original = paths[0].read_bytes()
            archive = Path(folder) / 'pilot.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('pilot/' + paths[0].name, original)
            with patch.object(x, 'score_conversation', side_effect=AssertionError('no rescoring')), \
                 patch.object(runner, 'audit_artifact', side_effect=AssertionError('historical audit uses its own version')):
                result = report.review_preparation([archive])
            self.assertEqual(result['groups'][0]['completed_both_empty_task_json'], 1)
            self.assertTrue(all(r['status'] == 'empty_task_answer_json' for r in result['responses']))
            self.assertEqual(paths[0].read_bytes(), original)
            self.assertEqual(a['turns']['A_prepare']['raw_response'], answers['A_prepare'])
            with self.assertRaisesRegex(ValueError, 'duplicate run'):
                report.review_preparation([archive, archive])

    def test_review_does_not_call_other_answers_compliant_or_empty_inputs_pass(self):
        for text in ('notes about {"routes":[]}', '{broken', '{"routes":[],"model":{}}',
                     '{"transitions":[]}', '{"routes":[{"query_id":"q0"}]}', '', None):
            self.assertFalse(report.empty_task_answer_json(text))
        self.assertTrue(report.empty_task_answer_json('{"routes":[],"changed":false,"changed_pair":null}'))
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, 'no preparation responses examined'):
                report.review_preparation([folder])
            path = Path(folder) / 'icl_expanded_v2_damaged.json'
            path.write_text('{damaged')
            with self.assertRaises(json.JSONDecodeError):
                report.review_preparation([folder])


if __name__ == '__main__':
    unittest.main(verbosity=2)

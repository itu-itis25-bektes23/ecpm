"""Offline integration and defect tests. All provider/tokenizer paths are mocked."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import icl_graph as controls
import icl_model_first as m
import icl_model_first_runner as runner
import run_pilot as pilot
from experiments.preview_icl_model_first import compatible_identity, generate, plan, summarize
from test_icl_graph import args as graph_args, config, envelope, local_config


def args(arm='model_first', provider='dry-run', profile='gemma_e4b', history_policy=m.HISTORY_POLICY):
    a = graph_args(profile=profile, provider=provider)
    a.protocol = m.PROTOCOL
    a.max_tokens = 4096
    a.graph_condition = None
    a.model_first_condition = arm
    a.off_reference = None
    a.history_policy = history_policy
    return a


def wrapper(local=True, profile='gemma_e4b', history_policy=m.HISTORY_POLICY):
    c = local_config() if local else config(profile)
    if profile in controls.HOSTED_PROFILES:
        c['pricing'] = {'input_per_million': 1, 'output_per_million': 2, 'source': 'SYNTHETIC TEST ONLY'}
    return {'deployment': c,
            'model_first': {'protocol': m.PROTOCOL, 'history_policy': history_policy,
                            'preparation_policy': m.PREPARATION_POLICY,
                            'output_allowances': [4096],
                            'stage_limits_source': 'SYNTHETIC TEST ONLY',
                            'system_message_source': 'SYNTHETIC TEST ONLY',
                            'context_source': 'SYNTHETIC TEST ONLY'}}


def reference(seed=8):
    world = m.load(seed)
    answers = runner.synthetic_answers(world)
    return world, answers


def mock_count(body, c, *, output_tokens, allow_system):
    assert allow_system
    return controls.local_count_record(body, c, 'SYNTHETIC TEMPLATE', [2] * 5000,
                                      c['context']['identity'], output_tokens=output_tokens)


class ContractIntegration(unittest.TestCase):
    def test_previous_preparation_configuration_is_rejected(self):
        good = wrapper()
        runner.validate_config(good, 'gemma_e4b')
        for value in (None, 'unmatched_turns'):
            bad = copy.deepcopy(good)
            if value is None:
                del bad['model_first']['preparation_policy']
            else:
                bad['model_first']['preparation_policy'] = value
            with self.assertRaises(ValueError):
                runner.validate_config(bad, 'gemma_e4b')
        bad = copy.deepcopy(good)
        bad['model_first']['output_allowances'] = [4096,8192]
        with self.assertRaises(ValueError):
            runner.validate_config(bad, 'gemma_e4b')

    def test_preparation_identity_cannot_be_relabelled(self):
        with tempfile.TemporaryDirectory() as t:
            a = runner.run_once(m.load(8), 'task_only', 1, args('task_only'), None, t)
            self.assertTrue(all(runner.audit_artifact(a).values()))
            before = compatible_identity(a)
            a['identity']['preparation_policy'] = 'unmatched_turns'
            a['identity_sha256'] = runner.canonical(a['identity'])
            self.assertNotEqual(before, compatible_identity(a))
            self.assertFalse(runner.audit_artifact(a)['identity'])

    def test_all_worlds_and_54_exact_prompts(self):
        count = 0
        for seed in (8, 13, 25):
            w = m.verify_world(seed)
            count += len(m.verify_prompts(w))
        self.assertEqual(count, 54)

    def test_defective_definition_and_fixture_fail(self):
        with patch.object(m, 'COMMON', m.COMMON + ' injected defect'):
            with self.assertRaisesRegex(ValueError, 'prompt drift'):
                m.verify_prompts(m.load(8))
        bad = m.load(8)
        bad['A']['rows'][0] = '[A, a1, A]'
        with patch.object(m, 'load', return_value=bad):
            with self.assertRaisesRegex(ValueError, 'fixture'):
                m.verify_world(8)

    def test_nine_locked_history_examples(self):
        self.assertEqual(sum(len(m.verify_histories(m.load(s))) for s in (8, 13, 25)), 9)

    def test_history_defect_and_policy_drift_caught(self):
        real = m.schedule
        def branched(world, arm, answers, policy=m.HISTORY_POLICY):
            calls = real(world, arm, answers, policy)
            for call in calls:
                if call['id'].startswith('B'):
                    call['messages'] = [x for x in call['messages'] if x['content'] != answers['A_readout']]
            return calls
        with patch.object(m, 'schedule', side_effect=branched):
            with self.assertRaisesRegex(ValueError, 'history example drift'):
                m.verify_histories(m.load(8))
        with patch.object(m, 'HISTORY_POLICIES', ('wrong policy', m.HISTORY_POLICY)):
            with self.assertRaisesRegex(ValueError, 'history policy drift'):
                m.verify_histories(m.load(8))

    def test_coroutine_matches_complete_contract_history(self):
        w, answers = reference()
        answers['A_task'] = '  malformed complete A text\n\t [not JSON] '
        answers['A_readout'] = ' \tmalformed A REPORT {\n '
        for arm in m.ARMS:
            flow = runner.requests(w, arm)
            actual = []
            call = next(flow)
            while True:
                actual.append(copy.deepcopy(call))
                try:
                    call = flow.send(answers[call['id']])
                except StopIteration:
                    break
            self.assertEqual(actual, m.schedule(w, arm, answers))
            for c in actual:
                if c['id'].startswith('B'):
                    self.assertIn(answers['A_task'], [x['content'] for x in c['messages']])
                    self.assertIn(answers['A_readout'], [x['content'] for x in c['messages']])
                    self.assertIn(m.prompts(w, 'A', arm)['readout'], [x['content'] for x in c['messages']])
                self.assertNotIn(answers['B_readout'], [x['content'] for x in c['messages']])
            saved = copy.deepcopy(actual[-1])
            actual[0]['messages'][0]['content'] = 'MUTATION'
            self.assertEqual(actual[-1], saved)

    def test_preview_counts_and_planning_unknowns(self):
        with tempfile.TemporaryDirectory() as t:
            r = generate(Path(t) / 'review')
            self.assertEqual(r['prompt_files_exact'], 54)
            self.assertEqual(len(list((Path(t) / 'review/prompts').rglob('*.txt'))), 54)
            for name, expected in r['locked_history_checks'].items():
                self.assertEqual(m.digest((Path(t) / 'review' / name).read_text()), expected)
            for arm in m.ARMS:
                text = (Path(t) / 'review/examples' / f'seed_8_{arm}.md').read_text()
                world, answers = reference()
                for call in m.schedule(world, arm, answers):
                    self.assertIn(call['messages'][-1]['content'], text)
                    self.assertIn(answers[call['id']], text)
                self.assertIn(m.HISTORY_POLICY, text)
            source = {s['file']: s for s in r['source_reconciliation']}
            for name in ('resource_mdp.py', 'ecpm_parser.py', 'ecpm_baseline.py'):
                self.assertTrue(source[name]['reconciled'])
                self.assertFalse(source[name]['match'])
                self.assertEqual(source[name]['relationship'], 'bundle_has_one_extra_trailing_LF')
                self.assertEqual(source[name]['bundle_bytes'], source[name]['published_bytes'] + 1)
        self.assertEqual(plan()['requests_per_model'], 18)
        self.assertEqual(plan()['conversations_per_model'], 3)
        self.assertEqual(plan()['maximum_completion_tokens_per_model'], 73728)
        self.assertEqual(plan(3)['requests_per_model'], 54)
        self.assertEqual(plan(3)['conversations_per_model'], 9)
        self.assertEqual(plan(3)['maximum_completion_tokens_per_model'], 221184)
        self.assertIsNone(plan()['cost_usd'])
        self.assertIsNone(plan()['input_tokens'])
        self.assertEqual(plan()['history_policy'], m.HISTORY_POLICY)
        for b in plan()['blocks']:
            self.assertEqual(b['main_output_allowance'], b['model_and_task_output_allowance'] + b['transition_report_output_allowance'])


class ParserScorer(unittest.TestCase):
    def setUp(self):
        self.w, self.answers = reference()
        self.a = json.loads(self.answers['A_readout'])
        self.b = json.loads(self.answers['B_readout'])

    def read(self, obj, p='A'):
        return m.parse_readout(json.dumps(obj), self.w[p])

    def test_reference_all_worlds_conditions_scores(self):
        for seed in (8, 13, 25):
            w, answers = reference(seed)
            for arm in m.ARMS:
                s = m.score_conversation(w, arm, {k: {'raw_response': v} for k, v in answers.items()})
                for p in ('A', 'B'):
                    self.assertEqual(s['periods'][p]['beliefs']['joint_exact']['numerator'], 16)
                    self.assertTrue(all(r['solution_correct'] for r in s['periods'][p]['routes'].values()))
                self.assertEqual(s['preservation']['self']['all_controls']['value'], 1)
                self.assertTrue(s['preservation']['truth']['all_four_correct'])
                self.assertTrue(s['periods']['B']['detection_correct'])
                self.assertTrue(s['periods']['B']['localization_correct'])
                self.assertEqual(s['explicit_model']['status'], 'not_scored_by_design' if arm == 'model_first' else 'not_applicable')

    def test_missing_available_only_one_pair_fails(self):
        del self.a['pairs'][0]['available']
        p = self.read(self.a)
        self.assertEqual(m.score_readout(p, self.w, 'A')['transition_exact']['numerator'], 15)
        self.assertEqual(m.score_readout(p, self.w, 'A')['p_mae_truth_conditional']['n'], 15)

    def test_null_and_bad_probability_not_repaired(self):
        for field, bad in [('destination', None), ('destination', 'null'), ('p_success', True),
                           ('p_success', -0.1), ('p_success', 1.1), ('p_success', '1')]:
            obj = copy.deepcopy(self.a)
            obj['pairs'][0][field] = bad
            s = m.score_readout(self.read(obj), self.w, 'A')
            self.assertEqual(s['transition_exact']['numerator'], 15)
            self.assertEqual(s['valid_rows']['numerator'], 15)

    def test_strict_document_and_duplicate_members(self):
        raw = self.answers['A_readout']
        for text in ('prose ' + raw, '```json\n' + raw + '\n```', raw + raw,
                     '{"pairs":[],"pairs":[]}', raw.replace('1.0', 'NaN', 1),
                     raw.replace('1.0', 'Infinity', 1), '{"pairs":[{"state":"A","state":"B"}]}'):
            p = m.parse_readout(text, self.w['A'])
            self.assertEqual(p['status'], 'invalid_json')
        p = m.parse_readout(raw.replace('1.0', '1e999', 1), self.w['A'])
        self.assertFalse(p['rows'][m.pair_id(m.pair_keys(self.w['A'])[0])]['transition_valid'])

    def test_missing_changed_keeps_transition(self):
        del self.b['pairs'][0]['changed']
        p = self.read(self.b, 'B')
        s = m.score_readout(p, self.w, 'B')
        self.assertEqual(s['transition_exact']['numerator'], 16)
        self.assertEqual(s['joint_exact']['numerator'], 15)
        self.assertEqual(s['p_mae_truth_conditional']['n'], 16)
        self.assertFalse(p['well_formed'])

    def test_duplicate_missing_unknown_extra_rows(self):
        obj = copy.deepcopy(self.a)
        obj['pairs'].append(copy.deepcopy(obj['pairs'][0]))
        self.assertEqual(m.score_readout(self.read(obj), self.w, 'A')['transition_exact']['numerator'], 15)
        obj = copy.deepcopy(self.a)
        obj['pairs'].pop()
        self.assertEqual(m.score_readout(self.read(obj), self.w, 'A')['transition_exact']['numerator'], 15)
        obj = copy.deepcopy(self.a)
        obj['pairs'].append({'state': 'UNKNOWN', 'action': 'a1'})
        p = self.read(obj)
        self.assertFalse(p['complete_model'])
        s = m.score_readout(p, self.w, 'A')
        self.assertEqual(s['transition_exact']['numerator'], 16)
        self.assertFalse(s['complete_graph_exact'])
        self.a['pairs'][0]['extra'] = 'bad format, retain required values'
        p = self.read(self.a)
        self.assertFalse(p['well_formed'])
        self.assertEqual(m.score_readout(p, self.w, 'A')['transition_exact']['numerator'], 16)

    def test_unavailable_null_semantics(self):
        self.a['pairs'][0].update(available=False, destination=None, p_success=None)
        s = m.score_readout(self.read(self.a), self.w, 'A')
        self.assertEqual(s['valid_rows']['numerator'], 16)
        self.assertEqual(s['transition_exact']['numerator'], 15)
        self.assertEqual(s['p_mae_truth_conditional']['n'], 15)
        self.a['pairs'][0]['destination'] = 'A'
        self.assertEqual(m.score_readout(self.read(self.a), self.w, 'A')['valid_rows']['numerator'], 15)

    def test_preservation_can_keep_wrong_beliefs(self):
        control = self.w['controls'][0]
        for obj in (self.a, self.b):
            row = next(r for r in obj['pairs'] if (r['state'], r['action']) == (control['node'], control['action']))
            row['p_success'] = .5
        s = m.preservation(self.read(self.a), self.read(self.b, 'B'), self.w)
        self.assertEqual(s['self']['all_controls']['value'], 1)
        self.assertEqual(s['truth']['all_controls']['value'], .75)
        del row['changed']
        s = m.preservation(self.read(self.a), self.read(self.b, 'B'), self.w)
        self.assertEqual(s['self']['conditional']['denominator'], 3)
        self.assertEqual(s['self']['all_controls']['value'], .75)

    def test_truth_preservation_does_not_require_valid_a(self):
        control = self.w['controls'][0]
        row = next(r for r in self.a['pairs'] if (r['state'], r['action']) == (control['node'], control['action']))
        del row['available']
        s = m.preservation(self.read(self.a), self.read(self.b, 'B'), self.w)
        self.assertEqual(s['self']['all_controls']['value'], .75)
        self.assertEqual(s['truth']['all_controls']['value'], 1)

    def test_route_components_independent(self):
        obj = json.loads(self.answers['B_task'])
        obj['routes'][0]['steps'] = None
        p = m.parse_task(json.dumps(obj), self.w, 'B')
        self.assertEqual(sum(r['valid'] for r in p['routes'].values()), 3)
        self.assertTrue(p['detection']['valid'])
        self.assertTrue(p['localization']['valid'])
        obj['changed'] = False
        self.assertFalse(m.parse_task(json.dumps(obj), self.w, 'B')['localization']['valid'])
        obj['changed_pair'] = None
        self.assertTrue(m.parse_task(json.dumps(obj), self.w, 'B')['localization']['valid'])
        obj['routes'].append(copy.deepcopy(obj['routes'][1]))
        self.assertFalse(m.parse_task(json.dumps(obj), self.w, 'B')['routes']['q1']['valid'])

    def test_unexpected_step_and_localization_fields_keep_scientific_values(self):
        answers = copy.deepcopy(self.answers)
        obj = json.loads(answers['B_task'])
        obj['routes'][0]['steps'][0]['note'] = 'extra field, not an extra action'
        obj['changed_pair']['note'] = 'extra field, retain exact state/action'
        answers['B_task'] = json.dumps(obj)
        parsed = m.parse_task(answers['B_task'], self.w, 'B')
        self.assertFalse(parsed['well_formed'])
        self.assertEqual(parsed['status'], 'partial')
        self.assertTrue(parsed['routes']['q0']['valid'])
        self.assertIn('unexpected route step fields at index 0', parsed['routes']['q0']['errors'])
        self.assertTrue(parsed['localization']['valid'])
        self.assertEqual(parsed['localization']['errors'], ['unexpected localization fields'])
        self.assertEqual(parsed['localization']['value'], obj['changed_pair'])
        scores = m.score_conversation(self.w, 'task_only', {k: {'raw_response': v} for k,v in answers.items()})
        self.assertTrue(scores['periods']['B']['routes']['q0']['optimal'])
        self.assertTrue(scores['periods']['B']['localization_correct'])
        for field, value in (('state', None), ('action', 'unknown')):
            bad = copy.deepcopy(obj)
            bad['routes'][0]['steps'][0][field] = value
            bad['changed_pair'][field] = value
            parsed = m.parse_task(json.dumps(bad), self.w, 'B')
            self.assertFalse(parsed['routes']['q0']['valid'])
            self.assertFalse(parsed['localization']['valid'])
        bad = copy.deepcopy(obj)
        del bad['routes'][0]['steps'][0]['action']
        del bad['changed_pair']['state']
        parsed = m.parse_task(json.dumps(bad), self.w, 'B')
        self.assertFalse(parsed['routes']['q0']['valid'])
        self.assertFalse(parsed['localization']['valid'])

    def test_extra_fields_do_not_rescue_extra_goal_or_wrong_route(self):
        obj = json.loads(self.answers['A_task'])
        obj['routes'][0]['steps'][0]['note'] = 'format error'
        obj['routes'][0]['steps'].append({'state': self.w['A']['goal'], 'action': None, 'note': 'still an invalid extra action'})
        parsed = m.parse_task(json.dumps(obj), self.w, 'A')
        self.assertFalse(parsed['routes']['q0']['valid'])
        self.assertFalse(m.grade_route(parsed['routes']['q0'], self.w['A']['graph'], m.queries(self.w)[0])['solution_correct'])
        obj = json.loads(self.answers['A_task'])
        obj['routes'][0]['steps'][0]['note'] = 'format error'
        obj['routes'][0]['steps'].pop()
        parsed = m.parse_task(json.dumps(obj), self.w, 'A')
        self.assertTrue(parsed['routes']['q0']['valid'])
        self.assertEqual(m.grade_route(parsed['routes']['q0'], self.w['A']['graph'], m.queries(self.w)[0])['status'], 'incomplete_route')

    def test_non_anchor_goal_and_extra_goal_remains_invalid(self):
        query = {'query_id': 'test', 'start': 'G', 'goal': 'E'}
        parsed = {'valid': True, 'value': {'reachable': True, 'steps': [{'state': 'G', 'action': 'a1'}]}}
        r = m.grade_route(parsed, self.w['A']['graph'], query)
        self.assertEqual(r['cost'], 1)
        self.assertTrue(r['optimal'])
        parsed['value']['steps'].append({'state': 'E', 'action': 'a1'})
        r = m.grade_route(parsed, self.w['A']['graph'], query)
        self.assertEqual(r['status'], 'extra_goal_item')
        self.assertIsNone(r['cost'])
        self.assertIsNone(r['regret'])

    def test_zero_probability_unreachable_regret_and_loops(self):
        rows = [{'node': 'X', 'action': 'a1', 'available': True, 'destination': 'Y', 'p_success': .5},
                {'node': 'X', 'action': 'a2', 'available': True, 'destination': 'Y', 'p_success': 1}]
        q = {'start': 'X', 'goal': 'Y'}
        p = {'valid': True, 'value': {'reachable': True, 'steps': [{'state': 'X', 'action': 'a1'}]}}
        r = m.grade_route(p, rows, q)
        self.assertEqual((r['cost'], r['regret']), (2, 1))
        for row in rows:
            row['p_success'] = 0
        p['value'] = {'reachable': False, 'steps': []}
        r = m.grade_route(p, rows, q)
        self.assertTrue(r['solution_correct'])
        self.assertFalse(r['valid'])
        self.assertIsNone(r['regret'])

    def test_route_length_missing_steps_and_incomplete(self):
        obj = json.loads(self.answers['A_task'])
        obj['routes'][0]['steps'] *= 17
        self.assertFalse(m.parse_task(json.dumps(obj), self.w, 'A')['routes']['q0']['valid'])
        obj = json.loads(self.answers['A_task'])
        obj['routes'][0]['steps'].pop()
        p = m.parse_task(json.dumps(obj), self.w, 'A')
        r = m.grade_route(p['routes']['q0'], self.w['A']['graph'], m.queries(self.w)[0])
        self.assertEqual(r['status'], 'incomplete_route')

    def test_known_contradiction_overrides_unlisted_pair(self):
        report = self.read(self.a)
        report['rows']['G:a1']['transition_valid'] = False
        report['complete_model'] = False
        p = {'valid': True, 'value': {'reachable': True, 'steps': [{'state': 'G', 'action': 'a1'}, {'state': 'E', 'action': 'a1'}]}}
        # E:a1 is known, deliberately demand the wrong final destination.
        dest = report['rows']['E:a1']['value']['destination']
        goal = next(n for n in self.w['A']['nodes'] if n not in (dest, 'E'))
        d = m.route_diagnostic(p, report, {'start': 'G', 'goal': goal})
        self.assertEqual(d['consistency'], 'route_inconsistent')
        self.assertIsNone(d['own_report_optimal'])
        p['value']['steps'].pop()
        self.assertEqual(m.route_diagnostic(p, report, {'start': 'G', 'goal': 'E'})['consistency'], 'route_unresolvable')


class RunnerTests(unittest.TestCase):
    def test_one_and_three_repeat_suites_and_expected_counts(self):
        sc = {**pilot.SCENARIO_DEFAULTS, **pilot.SCENARIOS['icl_det_gate_seed8']}
        for repeats, total in ((1, 18), (3, 54)):
            responses = conversations = 0
            with tempfile.TemporaryDirectory() as t:
                for arm in m.ARMS:
                    a = args(arm)
                    a.repeats, a.sampling_seeds = repeats, list(range(repeats))
                    out = Path(t) / arm
                    with patch('builtins.print'):
                        result = runner.run_suite(sc, a, out)
                    self.assertTrue(result['operational_gate_pass'])
                    self.assertEqual(result['expected_conversations'], repeats)
                    self.assertEqual(result['completed_conversations'], repeats)
                    expected_responses = repeats * 6
                    self.assertEqual(result['saved_responses'], expected_responses)
                    self.assertEqual(result['prelaunch_cost_plan']['requests'], expected_responses)
                    self.assertEqual(result['prelaunch_cost_plan']['maximum_completion_tokens'], repeats * 24576)
                    records = [json.loads(p.read_text()) for p in out.glob('icl*.json')]
                    self.assertEqual(sorted(r['identity']['repeat_seed_label'] for r in records), list(range(repeats)))
                    conversations += len(records)
                    responses += result['saved_responses']
                    # A mismatched expected count must fail, not appear complete.
                    self.assertFalse(runner.write_summary(out, expected=4 - repeats)['operational_gate_pass'])
            self.assertEqual(conversations, 3 * repeats)
            self.assertEqual(responses, total)

    def test_invalid_repeat_seed_combinations_stop_before_artifacts(self):
        sc = {**pilot.SCENARIO_DEFAULTS, **pilot.SCENARIOS['icl_det_gate_seed8']}
        for repeats, seeds in ((0, []), (2, [0, 1]), (4, [0, 1, 2, 3]),
                               (1, [1]), (1, [0, 1, 2]), (3, [0]), (3, [0, 0, 2])):
            a = args()
            a.repeats, a.sampling_seeds = repeats, seeds
            with tempfile.TemporaryDirectory() as t, patch.object(runner, 'call_provider') as provider:
                out = Path(t) / 'unused'
                with self.assertRaisesRegex(ValueError, 'one repeat 0 or three repeats'):
                    runner.run_suite(sc, a, out)
                self.assertFalse(out.exists())
                provider.assert_not_called()

    def test_one_repeat_cost_plan_scales_without_changing_allowances(self):
        for arm in m.ARMS:
            for config in (None, wrapper(), wrapper(False, 'sol')):
                one = runner.block_cost_plan(m.load(8), arm, config, repeats=1)
                three = runner.block_cost_plan(m.load(8), arm, config)
                for field in ('requests', 'maximum_completion_tokens', 'admitted_input_token_ceiling', 'usd_ceiling'):
                    if field in one:
                        self.assertAlmostEqual(three[field], 3 * one[field])
            for repeats in (0, 2, 4, True):
                with self.assertRaisesRegex(ValueError, 'one or three'):
                    runner.block_cost_plan(m.load(8), arm, None, repeats)
                with self.assertRaisesRegex(ValueError, 'one or three'):
                    plan(repeats)

    def run_mock(self, folder, arm='model_first', damage=None, count=mock_count, history_policy=m.HISTORY_POLICY):
        world, answers = reference()
        order = [c['id'] for c in m.schedule(world, arm, answers, history_policy)]
        requests = []
        def provider(body, c, timeout):
            name = order[len(requests)]
            requests.append(copy.deepcopy(body))
            env = envelope(answers[name])
            if damage:
                damage(name, env)
            return 200, json.dumps(env)
        with patch.object(runner, 'call_provider', side_effect=provider), \
             patch.object(controls, 'count_local_request', side_effect=count), \
             patch.object(pilot, '_git_dirty', return_value=False):
            a = runner.run_once(world, arm, 1, args(arm, 'openai', history_policy=history_policy),
                                wrapper(history_policy=history_policy), folder)
        return a, requests

    def test_fitting_all_stages_and_offline_audit_serialized(self):
        with tempfile.TemporaryDirectory() as t:
            a, requests = self.run_mock(t)
            self.assertEqual([b['max_tokens'] for b in requests], [4096] * 6)
            self.assertTrue(all(runner.audit_artifact(json.loads(json.dumps(a))).values()))
            self.assertIn('system', [x['role'] for x in requests[0]['messages']])
            self.assertEqual(a['scores']['explicit_model']['status'], 'not_scored_by_design')
        with tempfile.TemporaryDirectory() as t:
            a, requests = self.run_mock(t, arm='task_only')
            self.assertEqual([b['max_tokens'] for b in requests], [4096] * 6)

    def test_provider_raw_and_final_saved_before_answer_parsing(self):
        original = m.parse_task
        with tempfile.TemporaryDirectory() as t:
            def inspect(raw, world, period):
                saved = json.loads(next(Path(t).glob('*.json')).read_text())
                name = period + '_task'
                self.assertIn(name + ':provider_raw_saved', saved['persistence_events'])
                self.assertIn(name + ':raw_saved', saved['persistence_events'])
                self.assertEqual(saved['turns'][name]['raw_response'], raw)
                return original(raw, world, period)
            with patch.object(m, 'parse_task', side_effect=inspect):
                self.run_mock(t)

    def test_blank_failure_and_malformed_nonblank_continues(self):
        def blank(name, env):
            env['choices'][0]['message']['content'] = ' \n\t '
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(RuntimeError, 'operational failure'):
                self.run_mock(t, damage=blank)
            saved = json.loads(next(Path(t).glob('*.json')).read_text())
            self.assertEqual(len(saved['turns']), 1)
            self.assertEqual(saved['turns']['A_prepare']['raw_response'], ' \n\t ')
        malformed = ' \ncomplete malformed A text } {\t '
        def bad_task(name, env):
            if name == 'A_task':
                env['choices'][0]['message']['content'] = malformed
        with tempfile.TemporaryDirectory() as t:
            a, bodies = self.run_mock(t, damage=bad_task)
            self.assertEqual(a['scores']['periods']['A']['task_parsed']['status'], 'invalid_json')
            self.assertIn(malformed, [m['content'] for m in bodies[3]['messages']])
            self.assertTrue(all(runner.audit_artifact(a).values()))

    def test_raw_usage_finish_and_copied_fields_disagreement(self):
        with tempfile.TemporaryDirectory() as t:
            original, _ = self.run_mock(t)
        for field, value in [('provider_usage', {'prompt_tokens': 5000, 'completion_tokens': 1}),
                             ('provider_reasoning', 'wrong'), ('actual_response_model', 'wrong'),
                             ('raw_response', 'wrong')]:
            a = json.loads(json.dumps(original))
            a['turns']['A_prepare'][field] = value
            self.assertFalse(runner.audit_artifact(a)['responses'])
        a = json.loads(json.dumps(original))
        turn = a['turns']['A_prepare']
        turn['provider_response']['choices'][0]['finish_reason'] = 'length'
        turn['provider_response_raw'] = json.dumps(turn['provider_response'])
        turn['provider_response_sha256'] = runner.canonical(turn['provider_response'])
        turn['provider_response_raw_sha256'] = m.digest(turn['provider_response_raw'])
        self.assertFalse(runner.audit_artifact(a)['responses'])

    def test_identity_context_and_retained_report_tamper(self):
        with tempfile.TemporaryDirectory() as t:
            original, _ = self.run_mock(t)
        for key in ('B_prepare', 'B_task', 'B_readout'):
            # Even internally rehashed histories must retain both A report messages.
            for role in ('user', 'assistant'):
                a = json.loads(json.dumps(original))
                t = a['turns'][key]
                content = a['turns']['A_readout']['prompt' if role == 'user' else 'raw_response']
                t['request_body']['messages'].remove({'role': role, 'content': content})
                t['parent_history'] = copy.deepcopy(t['request_body']['messages'][:-1])
                t['parent_history_sha256'] = runner.canonical(t['parent_history'])
                t['parent_history_id'] = 'history_' + t['parent_history_sha256']
                t['messages_sha256'] = runner.canonical(t['request_body']['messages'])
                t['request_sha256'] = runner.canonical(t['request_body'])
                self.assertFalse(runner.audit_artifact(a)['history'])
        a = json.loads(json.dumps(original))
        a['turns']['A_prepare']['context_check']['identity']['build_info'] = 'changed'
        self.assertFalse(runner.audit_artifact(a)['responses'])

    def test_malformed_reports_retained_and_private_reasoning_excluded(self):
        malformed = ' \nA transition report: }{ invalid\t '
        def damage(name, env):
            if name == 'A_readout':
                env['choices'][0]['message']['content'] = malformed
        for arm in m.ARMS:
            with tempfile.TemporaryDirectory() as t:
                a, bodies = self.run_mock(t, arm=arm, damage=damage)
                self.assertTrue(all(runner.audit_artifact(a).values()))
                self.assertFalse(a['scores']['periods']['A']['readout_parsed']['well_formed'])
                for name, body in zip(a['run_order'], bodies):
                    if name.startswith('B'):
                        self.assertIn({'role': 'assistant', 'content': malformed}, body['messages'])
                    self.assertTrue(all(set(x) == {'role', 'content'} for x in body['messages']))
                # Provider-private text is never used by schedule or runner history.
                private = copy.deepcopy(a)
                for turn in private['turns'].values():
                    turn['provider_reasoning'] = 'PRIVATE REASONING SENTINEL'
                calls = m.schedule(a['world'], arm, {k: v['raw_response'] for k,v in private['turns'].items()})
                self.assertNotIn('PRIVATE REASONING SENTINEL', json.dumps(calls))

    def test_capacity_boundaries_and_old_default(self):
        c = local_config()
        body = c['preflight']['request']
        for cap in (4096, 8192):
            for n, fit in ((32768 - cap, True), (32769 - cap, False)):
                record = controls.local_count_record(body, c, 'template', [1] * n, c['context']['identity'], output_tokens=cap)
                self.assertEqual(record['fits'], fit)
        self.assertEqual(controls.local_count_record(body, c, 'template', [1], c['context']['identity'])['requested_output_tokens'], 8192)
        c = config('sol')
        self.assertEqual(controls.context_bound([{'role': 'system', 'content': 'x'}], c,
                                               output_tokens=4096, allow_system=True)['requested_output_tokens'], 4096)
        with self.assertRaises(ValueError):
            controls.context_bound([{'role': 'system', 'content': 'x'}], c)

    def test_oversized_b_stops_before_provider_and_preserves_a(self):
        count_calls = []
        def count(body, c, *, output_tokens, allow_system):
            count_calls.append(body)
            n = 32769 - output_tokens if len(count_calls) == 4 else 5000
            return controls.local_count_record(body, c, 'template', [2] * n, c['context']['identity'], output_tokens=output_tokens)
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(RuntimeError):
                self.run_mock(t, count=count)
            a = json.loads(next(Path(t).glob('*.json')).read_text())
            self.assertEqual(a['state'], 'incomplete')
            self.assertIn('raw_response', a['turns']['A_task'])
            self.assertIn('raw_response', a['turns']['A_readout'])
            messages = a['turns']['B_prepare']['request_body']['messages']
            self.assertIn({'role': 'assistant', 'content': a['turns']['A_readout']['raw_response']}, messages)
            self.assertNotIn('provider_response_raw', a['turns']['B_prepare'])
            self.assertNotIn('scores', a)

    def test_tokenizer_failure_and_deployment_mismatch_no_generation(self):
        for error in (TimeoutError('synthetic'), ValueError('deployment drift')):
            with tempfile.TemporaryDirectory() as t, patch.object(runner, 'call_provider') as provider, \
                    patch.object(controls, 'count_local_request', side_effect=error):
                with self.assertRaises(RuntimeError):
                    runner.run_once(m.load(8), 'model_first', 1, args(provider='openai'), wrapper(), t)
                provider.assert_not_called()
                self.assertEqual(json.loads(next(Path(t).glob('*.json')).read_text())['state'], 'incomplete')

    def test_length_positive_reasoning_excess_usage_stop_once(self):
        for damage in (lambda n,e: e['choices'][0].update(finish_reason='length'),
                       lambda n,e: e['choices'][0]['message'].update(reasoning_content='thought'),
                       lambda n,e: e['usage'].update(prompt_tokens=4999),
                       lambda n,e: e['usage'].update(completion_tokens=4097)):
            with tempfile.TemporaryDirectory() as t:
                with self.assertRaises(RuntimeError):
                    self.run_mock(t, damage=damage)
                a = json.loads(next(Path(t).glob('*.json')).read_text())
                self.assertEqual(len(a['turns']), 1)
                self.assertIn('provider_response_raw', a['turns']['A_prepare'])

    def test_network_failure_stops_without_retry(self):
        with tempfile.TemporaryDirectory() as t, \
                patch.object(runner, 'call_provider', side_effect=TimeoutError('synthetic')) as provider, \
                patch.object(controls, 'count_local_request', side_effect=mock_count):
            with self.assertRaises(RuntimeError):
                runner.run_once(m.load(8), 'model_first', 1, args(provider='openai'), wrapper(), t)
            self.assertEqual(provider.call_count, 1)
            saved = json.loads(next(Path(t).glob('*.json')).read_text())
            self.assertEqual(saved['state'], 'incomplete')
            self.assertEqual(saved['failure']['network_retries'], [])

    def test_profiles_and_missing_readiness(self):
        self.assertEqual(runner.settings('sol', 0, False, 4096),
                         {'max_completion_tokens': 4096, 'reasoning_effort': 'none'})
        c = wrapper(False, 'sol')
        runner.validate_config(c, 'sol')
        old_history = copy.deepcopy(c)
        del old_history['model_first']['history_policy']
        with self.assertRaisesRegex(ValueError, 'history policy'):
            runner.validate_config(old_history, 'sol')
        no_price = copy.deepcopy(c)
        no_price['deployment']['pricing']['input_per_million'] = None
        with self.assertRaisesRegex(ValueError, 'rates'):
            runner.validate_config(no_price, 'sol')
        del c['model_first']['system_message_source']
        with self.assertRaisesRegex(ValueError, 'stage-specific'):
            runner.validate_config(c, 'sol')
        self.assertEqual(controls.intended_settings('sol', 'off', 0)['max_completion_tokens'], 8192)

    def test_dry_matrix_summary_and_damaged_report(self):
        with tempfile.TemporaryDirectory() as t:
            paths = []
            for arm in m.ARMS:
                p = Path(t) / arm
                p.mkdir()
                for repeat in (1, 2, 3):
                    runner.run_once(m.load(8), arm, repeat, args(arm), None, p)
                s = runner.write_summary(p)
                self.assertTrue(s['operational_gate_pass'])
                self.assertNotIn('measurement', s['usage_by_workflow'])
                usage = s['usage_by_workflow']
                self.assertEqual(usage['main']['completion_tokens']['n_responses'],
                                 usage['model_and_task']['completion_tokens']['n_responses'] +
                                 usage['transition_report']['completion_tokens']['n_responses'])
                paths.append(p)
            report = summarize(paths)
            self.assertEqual(len(report['runs']), 9)
            self.assertEqual(sum(len(r['stages']) for r in report['runs']), 54)
            p = next(paths[0].glob('icl*.json'))
            bad = json.loads(p.read_text())
            del bad['scores']
            p.write_text(json.dumps(bad))
            with self.assertRaises(ValueError):
                summarize(paths)
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(ValueError, 'empty'):
                summarize([t])


class HistoryPolicies(unittest.TestCase):
    def test_preview_runner_and_locked_examples_for_both_policies(self):
        world, answers = reference()
        answers['A_task'] = ' \t malformed A task }{\n '
        answers['A_readout'] = ' \n malformed A report }{\t '
        for policy in m.HISTORY_POLICIES:
            self.assertEqual(sum(len(m.verify_histories(m.load(s), policy)) for s in (8, 13, 25)), 9)
            with tempfile.TemporaryDirectory() as t:
                r = generate(Path(t) / 'preview', policy)
                self.assertEqual(r['history_policy'], policy)
                self.assertEqual(r['plan']['history_policy'], policy)
                for name, expected in r['locked_history_checks'].items():
                    self.assertEqual(m.digest((Path(t) / 'preview' / name).read_text()), expected)
            for arm in m.ARMS:
                flow = runner.requests(world, arm, policy)
                call, calls = next(flow), []
                while True:
                    calls.append(copy.deepcopy(call))
                    try:
                        call = flow.send(answers[call['id']])
                    except StopIteration:
                        break
                self.assertEqual(calls, m.schedule(world, arm, answers, policy))

    def test_post_task_malformed_reports_and_audit_tamper(self):
        policy = m.HISTORY_POLICIES[1]
        malformed = ' \n A report complete but malformed }{\t '
        def damage(name, env):
            if name == 'A_readout':
                env['choices'][0]['message']['content'] = malformed
        for arm in m.ARMS:
            with tempfile.TemporaryDirectory() as t:
                a, bodies = RunnerTests().run_mock(t, arm, damage, history_policy=policy)
            a = json.loads(json.dumps(a))
            self.assertTrue(all(runner.audit_artifact(a).values()))
            self.assertEqual(a['turns']['A_readout']['raw_response'], malformed)
            self.assertFalse(a['scores']['periods']['A']['readout_parsed']['well_formed'])
            for name, body in zip(a['run_order'], bodies):
                if name.startswith('B'):
                    self.assertNotIn(malformed, [x['content'] for x in body['messages']])
                    self.assertIn(a['turns']['A_task']['raw_response'], [x['content'] for x in body['messages']])
                self.assertTrue(all(set(x) == {'role', 'content'} for x in body['messages']))
            for name in (n for n in a['turns'] if n.startswith('B')):
                bad = copy.deepcopy(a)
                turn = bad['turns'][name]
                for role, field in (('user', 'prompt'), ('assistant', 'raw_response')):
                    turn['request_body']['messages'].insert(-1, {'role': role, 'content': a['turns']['A_readout'][field]})
                turn['parent_history'] = copy.deepcopy(turn['request_body']['messages'][:-1])
                turn['parent_history_sha256'] = runner.canonical(turn['parent_history'])
                turn['parent_history_id'] = 'history_' + turn['parent_history_sha256']
                turn['request_sha256'] = runner.canonical(turn['request_body'])
                turn['messages_sha256'] = runner.canonical(turn['request_body']['messages'])
                self.assertFalse(runner.audit_artifact(bad)['history'])

    def test_policy_identity_config_reporting_and_no_resume(self):
        world, _ = reference()
        with tempfile.TemporaryDirectory() as t:
            paths, records = [], []
            for policy in m.HISTORY_POLICIES:
                p = Path(t) / policy
                p.mkdir()
                a = runner.run_once(world, 'model_first', 1, args(history_policy=policy), None, p)
                records.append(a)
                paths.append(p)
                with self.assertRaisesRegex(ValueError, 'no overwrite or resume'):
                    runner.run_once(world, 'model_first', 1, args(history_policy=policy), None, p)
                other = next(x for x in m.HISTORY_POLICIES if x != policy)
                with self.assertRaisesRegex(ValueError, 'output directory exists'):
                    runner.run_suite(pilot.SCENARIOS['icl_det_gate_seed8'], args(history_policy=other), p)
                c = wrapper(history_policy=policy)
                runner.validate_config(c, 'gemma_e4b', policy)
                with self.assertRaisesRegex(ValueError, 'stage-specific'):
                    runner.validate_config(c, 'gemma_e4b', other)
            self.assertNotEqual(records[0]['run_id'], records[1]['run_id'])
            self.assertEqual(records[0]['scores'], records[1]['scores'])
            self.assertEqual(records[0]['identity']['queries'], records[1]['identity']['queries'])
            report = summarize(paths)
            self.assertEqual(len(report['groups']), 2)
            self.assertEqual(sum(g['completed'] for g in report['groups'].values()), 2)
            for r in report['runs']:
                self.assertEqual(r['description_score'], 'not_scored_by_design')
                self.assertNotIn('manual_review', r)

    def test_usage_partitions_include_branches_exactly_once(self):
        for policy in m.HISTORY_POLICIES:
            for arm in m.ARMS:
                with tempfile.TemporaryDirectory() as t:
                    a, _ = RunnerTests().run_mock(t, arm, history_policy=policy)
                    s = runner.write_summary(t, expected=1)
                self.assertTrue(s['operational_gate_pass'])
                self.assertEqual(s['history_policies'], [policy])
                u = s['usage_by_workflow']
                n = 6
                branches = 0 if policy == m.HISTORY_POLICY else 2
                for field in ('prompt_tokens', 'completion_tokens'):
                    self.assertEqual(u['total'][field]['sum'], sum(x['provider_usage'][field] for x in a['turns'].values()))
                    self.assertEqual(u['total'][field]['sum'], (u['main'][field]['sum'] or 0) + (u['measurement_branch'][field]['sum'] or 0))
                    self.assertEqual(u['total'][field]['sum'], u['model_and_task'][field]['sum'] + u['transition_report'][field]['sum'])
                    self.assertEqual(u['total'][field]['n_responses'], n)
                    self.assertEqual(u['measurement_branch'][field]['n_responses'], branches)

    def test_both_policy_plans_and_stage_cost_ceilings(self):
        for repeats in (1, 3):
            plans = [plan(repeats, p) for p in m.HISTORY_POLICIES]
            self.assertEqual(sum(p['conversations_per_model'] for p in plans), 6 * repeats)
            self.assertEqual(sum(p['requests_per_model'] for p in plans), 36 * repeats)
            for p in plans:
                for b in p['blocks']:
                    self.assertEqual(b['main_output_allowance'] + b['measurement_branch_output_allowance'], 24576 * repeats)
                    c = wrapper(False, 'sol', p['history_policy'])
                    costs = runner.block_cost_plan(m.load(8), b['condition'], c, repeats, p['history_policy'])
                    self.assertEqual(costs['history_policy'], p['history_policy'])
                    self.assertEqual(costs['requests'], b['requests'])
                    self.assertEqual(costs['maximum_completion_tokens'], 24576 * repeats)
                    self.assertEqual(costs['admitted_input_token_ceiling'], b['requests'] * c['deployment']['context']['tokens'] - costs['maximum_completion_tokens'])
                    rates = c['deployment']['pricing']
                    self.assertAlmostEqual(costs['usd_ceiling'],
                        (costs['admitted_input_token_ceiling'] * rates['input_per_million'] +
                         costs['maximum_completion_tokens'] * rates['output_per_million']) / 1e6)


class ReportingAndCredentialReview(unittest.TestCase):
    def records(self, directory):
        a = runner.run_once(m.load(8), 'task_only', 1, args('task_only'), None, directory)
        path = Path(directory) / 'selected.json'
        path.write_text(json.dumps(a))
        return a, path

    def test_failed_fresh_audit_quarantined_without_changing_source(self):
        with tempfile.TemporaryDirectory() as t:
            a, path = self.records(t)
            a['turns']['A_task']['response_sha256'] = '0' * 64
            a['operational_audit'] = {k: True for k in a['operational_audit']}
            path.write_text(json.dumps(a))
            before = path.read_bytes()
            report = summarize([path])
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(report['runs'][0]['disposition'], 'quarantined_failed_operational_audit')
            self.assertIsNone(report['runs'][0]['scores'])
            group = next(iter(report['groups'].values()))
            self.assertEqual((group['declared_completed'], group['completed']), (1, 0))
            self.assertEqual(group['periods']['A']['transition_exact']['denominator'], 0)
            self.assertIsNone(group['periods']['A']['transition_exact']['value'])
            self.assertEqual(group['quarantined_run_ids'], [a['run_id']])

    def test_branched_identity_cannot_pool_with_retained_reports(self):
        with tempfile.TemporaryDirectory() as t:
            a, path = self.records(t)
            for policy in (None, 'branched_reports_v1'):
                old = copy.deepcopy(a)
                if policy is None:
                    del old['identity']['history_policy']
                else:
                    old['identity']['history_policy'] = policy
                old['identity_sha256'] = runner.canonical(old['identity'])
                old['run_id'] = old['run_id'].rsplit('_', 1)[0] + '_' + old['identity_sha256'][:16]
                self.assertNotEqual(old['run_id'], a['run_id'])
                self.assertFalse(runner.audit_artifact(old)['identity'])
                old_path = Path(t) / 'old_setup.json'
                old_path.write_text(json.dumps(old))
                report = summarize([path, old_path])
                self.assertEqual(len(report['groups']), 2)
                self.assertEqual(sum(g['completed'] for g in report['groups'].values()), 1)
                self.assertEqual(report['runs'][1]['disposition'], 'quarantined_failed_operational_audit')

    def test_valid_malformed_and_wrong_answers_remain_denominators(self):
        world, answers = reference()
        answers['A_readout'] = 'Nonblank malformed response.'
        b = json.loads(answers['B_task'])
        b.update(changed=False, changed_pair=None)
        answers['B_task'] = json.dumps(b)
        with tempfile.TemporaryDirectory() as t, patch.object(runner, 'synthetic_answers', return_value=answers):
            a, path = self.records(t)
            self.assertTrue(all(runner.audit_artifact(a).values()))
            group = next(iter(summarize([path])['groups'].values()))
            self.assertEqual(group['completed'], 1)
            self.assertEqual(group['periods']['A']['transition_exact'], m.fraction(0, 16))
            self.assertEqual(group['periods']['A']['readout_well_formed'], m.fraction(0, 1))
            self.assertEqual(group['periods']['B']['detection_correct'], m.fraction(0, 1))
            self.assertEqual(group['preservation']['self']['all_controls'], m.fraction(0, 4))

    def test_incomplete_attempt_visible_without_scientific_denominator(self):
        with tempfile.TemporaryDirectory() as t:
            a, path = self.records(t)
            a['state'] = 'incomplete'
            path.write_text(json.dumps(a))
            report = summarize([path])
            self.assertEqual(report['runs'][0]['disposition'], 'incomplete_operational_attempt')
            group = next(iter(report['groups'].values()))
            self.assertEqual(group['completed'], 0)
            self.assertEqual(group['incomplete_run_ids'], [a['run_id']])

    def test_different_exact_models_and_code_versions_are_not_pooled(self):
        with tempfile.TemporaryDirectory() as t:
            a, path = self.records(t)
            other_args = args('task_only')
            other_args.model = 'SYNTHETIC_DIFFERENT_MODEL'
            other = runner.run_once(m.load(8), 'task_only', 2, other_args, None, t)
            other_path = Path(t) / 'other.json'
            other_path.write_text(json.dumps(other))
            with patch.object(pilot, 'git_head', return_value='a' * 40):
                changed_code = runner.run_once(m.load(8), 'task_only', 3, args('task_only'), None, t)
            code_path = Path(t) / 'other_code.json'
            code_path.write_text(json.dumps(changed_code))
            for record in (a, other, changed_code):
                self.assertTrue(all(runner.audit_artifact(record).values()))
            report = summarize([path, other_path, code_path])
            self.assertEqual(len(report['groups']), 3)
            self.assertEqual([g['completed'] for g in report['groups'].values()], [1, 1, 1])

    def test_compatibility_includes_all_version_and_control_dimensions(self):
        with tempfile.TemporaryDirectory() as t:
            a, _ = self.records(t)
        original = compatible_identity(a)
        for field in ('protocol', 'history_policy', 'scorer', 'model', 'profile', 'provider', 'reasoning_mode',
                      'implementation_commit', 'implementation_dirty', 'lock_sha256',
                      'prompt_hashes', 'world_sha256', 'queries', 'deployment_sha256', 'sampling_seed_status'):
            b = copy.deepcopy(a)
            b['identity'][field] = 'different'
            self.assertNotEqual(compatible_identity(b), original, field)
        for field in ('synthetic', 'deployment'):
            b = copy.deepcopy(a)
            b[field] = 'different'
            self.assertNotEqual(compatible_identity(b), original, field)
        b = copy.deepcopy(a)
        b['identity']['stage_settings']['4096']['temperature'] = .5
        self.assertNotEqual(compatible_identity(b), original)
        b = copy.deepcopy(a)
        b['identity'].update(repeat=2, repeat_seed_label=1)
        self.assertEqual(compatible_identity(b), original)
        for x in (a, b):
            for values in x['identity']['stage_settings'].values():
                values['seed'] = x['identity']['repeat_seed_label']
        self.assertEqual(compatible_identity(a), compatible_identity(b))

    def test_audited_live_synthetic_and_deployment_variants_separate(self):
        with tempfile.TemporaryDirectory() as t:
            live, _ = RunnerTests().run_mock(t)
            dry = runner.run_once(m.load(8), 'model_first', 1, args(), None, t)
            other = copy.deepcopy(live)
            other['deployment']['model_first']['stage_limits_source'] = 'DIFFERENT SYNTHETIC EVIDENCE'
            other['identity']['deployment_sha256'] = runner.canonical(other['deployment'])
            other['identity_sha256'] = runner.canonical(other['identity'])
            other['run_id'] = other['run_id'].rsplit('_', 1)[0] + '_' + other['identity_sha256'][:16]
            paths = []
            for i, record in enumerate((live, dry, other)):
                self.assertTrue(all(runner.audit_artifact(record).values()))
                path = Path(t) / f'selected_{i}.json'
                path.write_text(json.dumps(record))
                paths.append(path)
            report = summarize(paths)
            self.assertEqual(len(report['groups']), 3)
            self.assertEqual([g['completed'] for g in report['groups'].values()], [1, 1, 1])

    def test_duplicate_repeat_different_run_id_and_out_of_range_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            a, path = self.records(t)
            b = copy.deepcopy(a)
            b['run_id'] += '_another_attempt'
            duplicate = Path(t) / 'duplicate.json'
            duplicate.write_text(json.dumps(b))
            with self.assertRaisesRegex(ValueError, 'duplicate repeat identity'):
                summarize([path, duplicate])
            b['identity'].update(repeat=4, repeat_seed_label=3)
            duplicate.write_text(json.dumps(b))
            with self.assertRaisesRegex(ValueError, 'invalid repeat identity'):
                summarize([duplicate])

    def test_profile_credential_routing_reads_only_the_selected_fake_key(self):
        class FakeEnvironment(dict):
            def get(self, key, default=None):
                reads.append(key)
                return super().get(key, default)
        class Response:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *unused):
                pass
            def read(self):
                return b'{}'
        class Opener:
            def open(self, request, timeout):
                captured.append(request)
                return Response()
        keys = {'OPENAI_API_KEY': 'FAKE_OPENAI', 'TOGETHER_API_KEY': 'FAKE_TOGETHER',
                'ECPM_LOCAL_API_KEY': 'FAKE_LOCAL_FRONTEND', 'ECPM_LOCAL_BACKEND_API_KEY': 'FAKE_BACKEND_ONLY'}
        cases = [('gemma_e4b', 'http://localhost:1234/v1', 'ECPM_LOCAL_API_KEY'),
                 ('gemma_31b_together', 'https://api.together.ai/v1', 'TOGETHER_API_KEY'),
                 ('gemma_31b', 'https://synthetic.invalid/v1', 'OPENAI_API_KEY'),
                 ('sol', 'https://synthetic.invalid/v1', 'OPENAI_API_KEY')]
        for profile, endpoint, selected in cases:
            reads, captured = [], []
            # Replace the mapping object, never copy or read the real environment.
            with patch.object(runner.os, 'environ', FakeEnvironment(keys)), \
                    patch.object(runner.urllib.request, 'build_opener', return_value=Opener()):
                runner.call_provider({'messages': []}, {'profile': profile, 'endpoint': endpoint}, 1)
            self.assertEqual(reads, [selected])
            self.assertEqual(captured[0].get_header('Authorization'), 'Bearer ' + keys[selected])
        reads, captured = [], []
        fake = FakeEnvironment({k: v for k, v in keys.items() if k != 'ECPM_LOCAL_API_KEY'})
        with patch.object(runner.os, 'environ', fake), \
                patch.object(runner.urllib.request, 'build_opener', return_value=Opener()):
            runner.call_provider({'messages': []}, {'profile': 'gemma_e4b', 'endpoint': 'http://127.0.0.1:1234/v1'}, 1)
        self.assertEqual(reads, ['ECPM_LOCAL_API_KEY'])
        self.assertIsNone(captured[0].get_header('Authorization'))
        reads = []
        with patch.object(runner.os, 'environ', fake), patch.object(runner.urllib.request, 'build_opener') as http:
            with self.assertRaisesRegex(ValueError, 'loopback'):
                runner.call_provider({}, {'profile': 'gemma_e4b', 'endpoint': 'https://synthetic.invalid/v1'}, 1)
            http.assert_not_called()
        self.assertEqual(reads, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)

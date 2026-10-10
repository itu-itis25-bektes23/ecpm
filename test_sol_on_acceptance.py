"""Sol request-defined acceptance, offline mocks and optional original ZIP checks."""

import ast
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import types
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import icl_graph as controls
import icl_expanded as expanded
import icl_model_first_runner as runner
import test_icl_expanded as fixtures
from experiments import preview_icl_expanded as report
from experiments.preview_icl_model_first import compatible_identity
from test_icl_graph import envelope

BASE = 'cd23576ac98d085119aa4f81a0782300ff10ef91'
POLICY = controls.SOL_REQUEST_DEFINED_ON


def zero_response(content='nonblank malformed answer'):
    return envelope(content, 'sol', 'off')


def opted_wrapper(history=expanded.HISTORY_POLICIES[0]):
    wrapper = fixtures.wrapper('on', 'sol', history)
    wrapper['expanded']['reasoning_acceptance_policy'] = POLICY
    return wrapper


def large_wrapper(cap, history=expanded.HISTORY_POLICIES[0]):
    w = opted_wrapper(history)
    w['expanded'].update(output_allowances=[cap], control_preflight_output_allowance=8192,
                         experiment_allowance_source='SYNTHETIC capacity evidence, not a live attestation')
    w['deployment']['effective']['max_output_tokens'] = 128000
    w['deployment']['context']['tokens'] = 1050000
    return w


def saved_turn(data, config, body):
    raw = json.dumps(data)
    turn = dict(provider_response_raw=raw, provider_response_raw_sha256=expanded.pilot.sha256_text(raw),
        provider_response=data, provider_response_sha256=runner.canonical(data),
        http_status=200, network_retries=[], context_check=runner.context_check(body, config, 4096),
        **runner.copied_fields(data, config, 'sol', False, 'on'))
    turn['response_sha256'] = expanded.pilot.sha256_text(turn['raw_response'])
    turn['reasoning_acceptance'] = controls.reasoning_acceptance(data, body, config, 'sol', 'on', POLICY)
    return json.loads(json.dumps(turn))


class SolAcceptance(unittest.TestCase):
    def setUp(self):
        self.wrapper = opted_wrapper()
        self.config = self.wrapper['deployment']
        self.body = {'model': self.config['model'], 'messages': [{'role': 'user', 'content': 'mock'}],
                     **runner.settings('sol', 0, False, 4096, 'on')}

    def accept(self, data, body=None, policy=POLICY):
        return controls.reasoning_acceptance(data, body or self.body, self.config, 'sol', 'on', policy)

    def test_zero_positive_missing_distinct_without_rewriting_observations(self):
        for count in (0, 15, None):
            data = zero_response()
            data['usage']['completion_tokens_details']['reasoning_tokens'] = count
            before = copy.deepcopy(data)
            observed = controls.reasoning_check(data, 'on', self.config['effective'], 'sol', self.config)
            result = self.accept(data)
            self.assertTrue(result['accepted'])
            self.assertEqual(result['observed_reasoning_tokens'], count)
            self.assertEqual(result['observed_reasoning_evidence'], observed['evidence'])
            self.assertEqual(self.accept(data, policy=None)['accepted'], count == 15)
            self.assertEqual(data, before)

    def test_unsupported_requests_counts_and_echoes_rejected(self):
        for field, value in (('reasoning_effort', 'none'), ('seed', 0), ('temperature', 0),
                             ('model', 'another-model'), ('max_completion_tokens', 65536)):
            self.assertFalse(self.accept(zero_response(), self.body | {field: value})['accepted'], field)
        for count in (-1, True, '0'):
            data = zero_response(); data['usage']['completion_tokens_details']['reasoning_tokens'] = count
            self.assertFalse(self.accept(data)['accepted'])
        for extra in ({'reasoning_effort': 'none'}, {'metadata': {'reasoning_enabled': False}}, {'model': 'other'}):
            self.assertFalse(self.accept(zero_response() | extra)['accepted'])
        self.config['supported_request_fields'].remove('reasoning_effort')
        self.assertFalse(self.accept(zero_response())['accepted'])
        del self.config['effective']['hosted_evidence']['source']
        with self.assertRaisesRegex(ValueError, 'exact-model'):
            self.accept(zero_response())

    def test_policy_is_opt_in_sol_on_only(self):
        for profile, mode, policy in (('sol', 'off', POLICY), ('gemma_e4b', 'on', POLICY),
                                      ('gemma_31b_together', 'on', POLICY), ('sol', 'on', 'typo')):
            with self.assertRaisesRegex(ValueError, 'versioned Sol ON'):
                controls.validate_reasoning_acceptance_policy(policy, profile, mode)
        config = fixtures.wrapper('off', 'sol')['deployment']
        data = zero_response()
        self.assertTrue(controls.reasoning_acceptance(data, {}, config, 'sol', 'off', None)['accepted'])
        data['usage']['completion_tokens_details']['reasoning_tokens'] = 1
        self.assertFalse(controls.reasoning_acceptance(data, {}, config, 'sol', 'off', None)['accepted'])

    def test_preflight_uses_same_policy_all_other_guards_retained(self):
        self.config['preflight']['response'] = zero_response('301')
        with self.assertRaisesRegex(ValueError, 'preflight control'):
            controls.validate_deployment(self.config, 'sol', 'on')
        expanded.validate_config(self.wrapper, 'sol', 'on', self.wrapper['expanded']['history_policy'])
        self.config['preflight']['response']['choices'][0]['finish_reason'] = 'length'
        with self.assertRaisesRegex(ValueError, 'preflight control'):
            expanded.validate_config(self.wrapper, 'sol', 'on', self.wrapper['expanded']['history_policy'])

    def test_explicit_caps_capacity_preflight_reuse_and_configuration_mismatches(self):
        for cap in (16384, 32768):
            w = large_wrapper(cap)
            pre = copy.deepcopy(w['deployment']['preflight'])
            expanded.validate_config(w, 'sol', 'on', w['expanded']['history_policy'], cap)
            self.assertEqual(w['deployment']['preflight'], pre)
            self.assertEqual(pre['request']['max_completion_tokens'], 8192)
            with self.assertRaisesRegex(ValueError, 'stage identity'):
                expanded.validate_config(w, 'sol', 'on', w['expanded']['history_policy'], 4096)
            for key, value in (('control_preflight_output_allowance', cap),
                               ('experiment_allowance_source', ''), ('reasoning_acceptance_policy', None)):
                bad = copy.deepcopy(w); bad['expanded'][key] = value
                with self.assertRaisesRegex(ValueError, 'capacity provenance'):
                    expanded.validate_config(bad, 'sol', 'on', w['expanded']['history_policy'])
            bad = copy.deepcopy(w); bad['deployment']['effective']['max_output_tokens'] = 8192
            with self.assertRaisesRegex(ValueError, 'capacity provenance'):
                expanded.validate_config(bad, 'sol', 'on', w['expanded']['history_policy'])
            bad = copy.deepcopy(w); bad['deployment']['preflight']['request']['max_completion_tokens'] = cap
            with self.assertRaisesRegex(ValueError, 'fixed preflight'):
                expanded.validate_config(bad, 'sol', 'on', w['expanded']['history_policy'])
            for profile, mode in (('sol', 'off'), ('gemma_e4b', 'on'), ('gemma_31b_together', 'on')):
                with self.assertRaises(ValueError): expanded.validate_output_allowance(cap, profile, mode)
        for cap in (8192, 65536, '32768', True):
            with self.assertRaises(ValueError): expanded.validate_output_allowance(cap, 'sol', 'on')

    def test_both_histories_large_caps_requests_costs_audits_exports_and_unchanged_scores(self):
        world = expanded.build_world(8, 'det', 'silent_break')
        answers = expanded.oracle_answers(world)
        identities = set()
        for cap in (4096, 16384, 32768):
            for history in expanded.HISTORY_POLICIES:
                w = opted_wrapper(history) if cap == 4096 else large_wrapper(cap, history)
                args = report.arguments('model_first', 'on', history, 'sol')
                args.provider, args.model, args.max_tokens = 'openai', w['deployment']['model'], cap
                calls = expanded.schedule(world, 'model_first', answers, history, cap)
                sent = []
                def reply(body, config, timeout):
                    sent.append(body)
                    self.assertEqual(body['messages'], calls[len(sent)-1]['messages'])
                    self.assertEqual(body['max_completion_tokens'], cap)
                    self.assertEqual(body['reasoning_effort'], 'medium')
                    data = zero_response(answers[calls[len(sent)-1]['id']])
                    return 200, json.dumps(data)
                with tempfile.TemporaryDirectory() as folder, patch.object(expanded.pilot, '_git_dirty', return_value=False), \
                        patch.object(runner, 'call_provider', side_effect=reply):
                    a = runner.run_once(world, 'model_first', 1, args, w, folder, expanded)
                    self.assertEqual(len(sent), 6)
                    self.assertTrue(all(runner.audit_artifact(json.loads(json.dumps(a)), expanded).values()))
                    self.assertEqual(a['scores'], expanded.score_conversation(world, 'model_first', fixtures.turns(answers)))
                    identities.add(a['run_id'])
                    for t in a['turns'].values():
                        self.assertEqual(t['max_output_tokens'], cap)
                        self.assertEqual(t['context_check']['requested_output_tokens'], cap)
                    rows = report.summarize([folder])
                    self.assertTrue(all(r['output_allowance'] == cap for r in rows['metrics']))
                    self.assertTrue(all(r['requested_output_tokens'] == cap for r in rows['request_usage']))
                    damaged = json.loads(json.dumps(a))
                    damaged['turns']['B_task']['max_output_tokens'] = cap + 1
                    self.assertFalse(runner.audit_artifact(damaged, expanded)['history'])
                    damaged = json.loads(json.dumps(a))
                    damaged['identity']['stage_settings'][str(cap)]['max_completion_tokens'] = cap + 1
                    self.assertFalse(runner.audit_artifact(damaged, expanded)['identity'])
                costs = runner.block_cost_plan(world, 'model_first', w, 1, history, expanded)
                self.assertEqual(costs['maximum_completion_tokens'], 6 * cap)
                self.assertEqual(costs['admitted_input_token_ceiling'], 6 * (w['deployment']['context']['tokens'] - cap))
                self.assertEqual(costs['usd_ceiling'], (costs['admitted_input_token_ceiling'] + 2 * 6 * cap) / 1e6)
                plan = report.plan('sol', [w])
                self.assertTrue(all(r['settings']['max_completion_tokens'] == cap for r in plan['rows']))
                self.assertTrue(all(r['argv'][r['argv'].index('--max-tokens')+1] == str(cap) for r in plan['rows']))
                self.assertEqual(plan['maximum_output_tokens'], sum(r['requests'] * cap for r in plan['rows']))
        self.assertEqual(len(identities), 6)

    def test_large_context_reserves_exact_capacity_usage_and_stop_before_send(self):
        for cap in (16384, 32768):
            w = large_wrapper(cap); c = w['deployment']
            body = self.body | {'max_completion_tokens': cap}
            count = runner.context_check(body, c, cap)
            c['context']['tokens'] = count['total_upper_bound']
            self.assertTrue(runner.context_check(body, c, cap)['fits'])
            c['context']['tokens'] -= 1
            self.assertFalse(runner.context_check(body, c, cap)['fits'])
            world = expanded.build_world(8, 'det', 'silent_break')
            args = report.arguments('model_first', 'on', w['expanded']['history_policy'], 'sol')
            args.provider, args.model, args.max_tokens = 'openai', c['model'], cap
            with tempfile.TemporaryDirectory() as folder, patch.object(runner, 'call_provider') as call:
                with self.assertRaisesRegex(RuntimeError, 'operational failure saved'):
                    runner.run_once(world, 'model_first', 1, args, w, folder, expanded)
                call.assert_not_called()
                a = json.loads(next(Path(folder).glob('*.json')).read_text())
                self.assertFalse(a['turns']['A_prepare']['context_check']['fits'])
            c['context']['tokens'] = 1050000
            data = zero_response()
            t = saved_turn(data, c, body)
            t['context_check'] = runner.context_check(body, c, cap)
            check = lambda t: runner.response_checks(t, body, c, 'sol', cap, False, 'on', POLICY)
            self.assertTrue(all(check(t).values()))
            for field, value, guard in (('completion_tokens', cap+1, 'transport'),
                                        ('prompt_tokens', c['context']['tokens']-cap+1, 'context')):
                bad = copy.deepcopy(data); bad['usage'][field] = value
                t = saved_turn(bad, c, body); t['context_check'] = runner.context_check(body,c,cap)
                self.assertFalse(check(t)[guard])

    def test_cli_synthetic_both_histories_both_caps(self):
        for cap in (16384, 32768):
            for history in expanded.HISTORY_POLICIES:
                with tempfile.TemporaryDirectory() as root:
                    argv = report.command(8, 'det', 'silent_break', 'model_first', 'on', history,
                                          'sol', 'offline_only', output_tokens=cap)
                    argv[0] = sys.executable
                    subprocess.run(argv + ['--out', root], check=True, capture_output=True, text=True)
                    summary = json.loads((Path(root)/'offline_only'/'summary.json').read_text())
                    self.assertEqual(summary['completed_conversations'], 1)
                    self.assertEqual(summary['saved_responses'], 6)
                    self.assertEqual(summary['prelaunch_cost_plan']['maximum_completion_tokens'], 6*cap)
                    self.assertTrue(summary['operational_gate_pass'])
                    a = json.loads(next((Path(root)/'offline_only').glob('icl_expanded*.json')).read_text())
                    self.assertTrue(a['synthetic'])
                    self.assertEqual(a['identity']['output_allowance'], cap)
                    self.assertTrue(all(t['request_body']['max_completion_tokens'] == cap for t in a['turns'].values()))

    def test_raw_reconciliation_transport_context_and_malformed_text(self):
        turn = saved_turn(zero_response(), self.config, self.body)
        def check(t, body=None):
            return runner.response_checks(t, body or self.body, self.config, 'sol', 4096, False, 'on', POLICY)
        self.assertTrue(all(check(turn).values()))
        self.assertFalse(runner.response_checks(turn, self.body, self.config, 'sol', 4096, False, 'on')['controls'])
        for field, value, guard in (('http_status', 500, 'transport'), ('network_retries', ['retry'], 'transport'),
                ('provider_usage', {}, 'copied_fields'), ('provider_response_raw', '{}', 'raw_envelope'),
                ('reasoning_acceptance', {}, 'copied_fields'), ('context_check', {}, 'context')):
            damaged = copy.deepcopy(turn); damaged[field] = value
            self.assertFalse(check(damaged)[guard], field)
        for content, finish in ((' \n\t', 'stop'), ('answer', 'length')):
            data = zero_response(content); data['choices'][0]['finish_reason'] = finish
            self.assertFalse(check(saved_turn(data, self.config, self.body))['transport'])
        self.assertFalse(check(turn, self.body | {'reasoning_effort': 'none'})['controls'])

    def test_runner_stops_after_one_length_response_and_preserves_raw(self):
        world = expanded.build_world(8, 'det', 'silent_break')
        args = report.arguments('model_first', 'on', self.wrapper['expanded']['history_policy'], 'sol')
        args.provider, args.model = 'openai', self.config['model']
        data = zero_response('partial answer'); data['choices'][0]['finish_reason'] = 'length'
        raw = json.dumps(data)
        with tempfile.TemporaryDirectory() as folder, patch.object(expanded.pilot, '_git_dirty', return_value=False), \
                patch.object(runner, 'call_provider', return_value=(200, raw)) as call:
            with self.assertRaisesRegex(RuntimeError, 'operational failure saved; no retry'):
                runner.run_once(world, 'model_first', 1, args, self.wrapper, folder, expanded)
            self.assertEqual(call.call_count, 1)
            a = json.loads(next(Path(folder).glob('*.json')).read_text())
            self.assertEqual(a['state'], 'incomplete')
            self.assertEqual(a['turns']['A_prepare']['provider_response_raw'], raw)
            self.assertFalse(a['turns']['A_prepare']['operational_checks']['transport'])
            self.assertNotIn('scores', a)

    def test_runner_audit_identity_and_malformed_denominators_both_histories(self):
        world = expanded.build_world(8, 'det', 'silent_break')
        for history in expanded.HISTORY_POLICIES:
            wrapper = opted_wrapper(history)
            args = report.arguments('model_first', 'on', history, 'sol')
            args.provider, args.model = 'openai', wrapper['deployment']['model']
            plain = copy.deepcopy(wrapper); del plain['expanded']['reasoning_acceptance_policy']
            old_id = expanded.identity(world, 'model_first', 1, args, plain)
            new_id = expanded.identity(world, 'model_first', 1, args, wrapper)
            self.assertNotEqual(runner.canonical(old_id), runner.canonical(new_id))
            self.assertNotEqual(compatible_identity({'identity': old_id, 'synthetic': False, 'deployment': plain}, 5),
                                compatible_identity({'identity': new_id, 'synthetic': False, 'deployment': wrapper}, 5))
            with tempfile.TemporaryDirectory() as folder, patch.object(expanded.pilot, '_git_dirty', return_value=False), \
                    patch.object(runner, 'call_provider', return_value=(200, json.dumps(zero_response()))) as call:
                a = runner.run_once(world, 'model_first', 1, args, wrapper, folder, expanded)
                self.assertEqual(call.call_count, 6)
                self.assertEqual(a['state'], 'completed')
                self.assertTrue(all(runner.audit_artifact(json.loads(json.dumps(a)), expanded).values()))
                for t in a['turns'].values():
                    self.assertFalse(t['control_check']['mode_verified'])
                    self.assertTrue(t['reasoning_acceptance']['accepted'])
                self.assertEqual(a['turns']['A_task']['parsed']['status'], 'invalid_json')
                summary = report.summarize([folder])
                self.assertTrue(summary)
                damaged = json.loads(json.dumps(a))
                damaged['turns']['A_prepare']['reasoning_acceptance']['observed_reasoning_tokens'] = 100
                self.assertFalse(runner.audit_artifact(damaged, expanded)['responses'])
                damaged = json.loads(json.dumps(a))
                del damaged['identity']['reasoning_acceptance_policy']
                self.assertFalse(runner.audit_artifact(damaged, expanded)['identity'])

    def test_base_science_prompts_histories_scores_and_default_identity_unchanged(self):
        source = subprocess.check_output(['git', 'show', BASE + ':icl_expanded.py'], text=True)
        prior = types.ModuleType('sol_backport_base')
        sys.modules[prior.__name__] = prior
        self.addCleanup(sys.modules.pop, prior.__name__)
        exec(compile(source, '<base>', 'exec'), prior.__dict__)
        def scientific_nodes(text):
            return [ast.dump(n) for n in ast.parse(text).body if not (
                isinstance(n, ast.FunctionDef) and n.name in ('identity', 'validate_config',
                    'validate_output_allowance', 'schedule', 'run_suite', 'audit_identity'))]
        self.assertEqual(scientific_nodes(source), scientific_nodes(Path(expanded.__file__).read_text()))
        # Validate unchanged defaults without attempting provider calls.
        for mode in ('off', 'on'):
            wrapper = fixtures.wrapper(mode, 'sol')
            self.assertEqual(prior.validate_config(wrapper, 'sol', mode, expanded.HISTORY_POLICIES[0]),
                             expanded.validate_config(wrapper, 'sol', mode, expanded.HISTORY_POLICIES[0]))
        with patch.object(expanded, 'source_hashes', return_value={}), patch.object(prior, 'source_hashes', return_value={}):
            world = expanded.build_world(8, 'det', 'silent_break')
            args = report.arguments('model_first', 'on', expanded.HISTORY_POLICIES[0], 'sol')
            wrapper = fixtures.wrapper('on', 'sol')
            self.assertEqual(prior.identity(world, 'model_first', 1, args, wrapper),
                             expanded.identity(world, 'model_first', 1, args, wrapper))
        for seed, mode, scenario in expanded.configurations():
            world = expanded.build_world(seed, mode, scenario)
            self.assertEqual(world, prior.build_world(seed, mode, scenario))
            answers = expanded.oracle_answers(world)
            for arm in expanded.ARMS:
                for period in ('A', 'B'):
                    self.assertEqual(expanded.prompts(world, period, arm), prior.prompts(world, period, arm))
                for history in expanded.HISTORY_POLICIES:
                    self.assertEqual(expanded.schedule(world, arm, answers, history), prior.schedule(world, arm, answers, history))
                self.assertEqual(expanded.score_conversation(world, arm, fixtures.turns(answers)),
                                 prior.score_conversation(world, arm, fixtures.turns(answers)))


def audit_saved_archive(path):
    """Compare guards on copies; never complete, rescore or rewrite old records."""
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    rows, states = [], []
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if not Path(name).name.startswith('icl_expanded_v2_') or not name.endswith('.json'):
                continue
            raw_artifact = archive.read(name)
            a = json.loads(raw_artifact)
            i = a['identity']
            assert (i['implementation_commit'], i['profile'], i['reasoning_mode']) == (BASE, 'sol', 'on')
            states.append(a['state'])
            config = a['deployment']['deployment']
            expanded.validate_config(a['deployment'], 'sol', 'on', i['history_policy'])
            for cap in (16384, 32768):
                derived = copy.deepcopy(a['deployment'])
                preflight = runner.canonical(derived['deployment']['preflight'])
                derived['expanded'].update(reasoning_acceptance_policy=POLICY,
                    output_allowances=[cap], control_preflight_output_allowance=8192,
                    experiment_allowance_source='Offline check of saved effective capacity; unchanged 8K preflight.')
                expanded.validate_config(derived, 'sol', 'on', i['history_policy'], cap)
                assert runner.canonical(derived['deployment']['preflight']) == preflight
                for t in a['turns'].values():
                    count = runner.context_check(t['request_body'], derived['deployment'], cap)
                    assert count['fits']
                    assert t['provider_usage']['prompt_tokens'] + cap <= derived['deployment']['context']['tokens']
            for stage in a['run_order']:
                t = a['turns'][stage]
                body = t['request_body']; data = json.loads(t['provider_response_raw'])
                before_turn = runner.canonical(t)
                old = runner.response_checks(t, body, config, 'sol', t['max_output_tokens'], False, 'on')
                copied = copy.deepcopy(t)
                copied['reasoning_acceptance'] = controls.reasoning_acceptance(data, body, config, 'sol', 'on', POLICY)
                new = runner.response_checks(copied, body, config, 'sol', t['max_output_tokens'], False, 'on', POLICY)
                assert all(new.values()), (name, stage, new)
                count = t['control_check']['reasoning_tokens']
                assert all(v for k, v in old.items() if k != 'controls')
                assert old['controls'] == (count > 0)
                assert before_turn == runner.canonical(t)
                rows.append({'source_artifact': name, 'source_sha256': hashlib.sha256(raw_artifact).hexdigest(),
                    'stage': stage, 'reasoning_tokens': count, 'old_controls': old['controls'],
                    'new_checks': new, 'raw_response_sha256': t['provider_response_raw_sha256']})
    assert len(states) == 6 and states.count('completed') == 1 and states.count('incomplete') == 5, states
    assert len(rows) == 22 and sum(r['reasoning_tokens'] == 0 for r in rows) == 5
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    print(json.dumps({'archive_sha256': before, 'original_states': states, 'responses': rows,
                     'note': 'Counterfactual guard comparison only. Original incomplete runs remain incomplete.'}, indent=2))


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--on-archive':
        audit_saved_archive(Path(sys.argv[2]))
    else:
        unittest.main()

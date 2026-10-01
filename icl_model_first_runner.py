"""OFF-only model-first orchestration with explicit report policies. No retries or repair."""

import copy
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import icl_graph as controls
import icl_model_first as design
import run_pilot as pilot

canonical = pilot._canonical_sha256


def settings(profile, seed, supported, allowance):
    if type(allowance) is not int or allowance not in (4096, 8192):
        raise ValueError('locked stage allowance required')
    result = controls.intended_settings(profile, 'off', seed, supported)
    result['max_completion_tokens' if profile == 'sol' else 'max_tokens'] = allowance
    return result


def requests(world, arm, history_policy=design.HISTORY_POLICY):
    """A coroutine: each send receives only the exact visible final answer."""
    design.check_history_policy(history_policy)
    history = [{'role': 'system', 'content': design.SYSTEM}]
    for period in ('A', 'B'):
        texts = design.prompts(world, period, arm)
        msg = {'role': 'user', 'content': texts['prepare']}
        answer = yield {'id': period + '_prepare', 'max_output_tokens': 4096,
                        'history_policy': history_policy, 'conversation': 'main',
                        'messages': copy.deepcopy(history + [msg])}
        history += [msg, {'role': 'assistant', 'content': answer}]
        msg = {'role': 'user', 'content': texts['task']}
        answer = yield {'id': period + '_task',
                        'history_policy': history_policy, 'conversation': 'main',
                        'max_output_tokens': 4096,
                        'messages': copy.deepcopy(history + [msg])}
        history += [msg, {'role': 'assistant', 'content': answer}]
        msg = {'role': 'user', 'content': texts['readout']}
        answer = yield {'id': period + '_readout', 'max_output_tokens': 4096,
                        'history_policy': history_policy,
                        'conversation': design.conversation_kind('readout', history_policy),
                        'messages': copy.deepcopy(history + [msg])}
        if history_policy == design.HISTORY_POLICY:
            history += [msg, {'role': 'assistant', 'content': answer}]


def validate_config(wrapper, profile, history_policy=design.HISTORY_POLICY):
    design.check_history_policy(history_policy)
    if set(wrapper) != {'deployment', 'model_first'}:
        raise ValueError('needs deployment plus model_first stage/path evidence')
    config = wrapper['deployment']
    controls.validate_deployment(config, profile, 'off')
    evidence = wrapper['model_first']
    if (evidence.get('protocol') != design.PROTOCOL
            or evidence.get('history_policy') != history_policy
            or evidence.get('preparation_policy') != design.PREPARATION_POLICY
            or evidence.get('output_allowances') != [4096]
            or any(not isinstance(evidence.get(k), str) or not evidence[k].strip()
                   for k in ('stage_limits_source', 'system_message_source', 'context_source'))):
        raise ValueError('history policy, stage-specific output and system-message/context evidence required')
    if profile == 'gemma_e4b' and not controls.local_context(config):
        raise ValueError('local actual-request tokenizer counting required')
    if profile in controls.HOSTED_PROFILES:
        pricing = config['pricing']
        if (any(pricing.get(k) is None for k in ('input_per_million', 'output_per_million'))
                or not isinstance(pricing.get('source'), str) or not pricing['source'].strip()):
            raise ValueError('verified hosted input/output rates and source required before launch')
    controls.no_secrets(wrapper)
    return config


def context_check(body, config, allowance):
    if controls.local_context(config):
        return controls.count_local_request(body, config, output_tokens=allowance, allow_system=True)
    return controls.context_bound(body['messages'], config, output_tokens=allowance, allow_system=True)


def copied_fields(data, config, profile, dry=False):
    choice = data['choices'][0]
    message = choice['message']
    check = ({'mode_verified': False, 'evidence': 'unknown', 'reasoning_tokens': None,
              'control_violation': False, 'status': 'not_applied_synthetic'} if dry else
             controls.reasoning_check(data, 'off', config['effective'], profile, config))
    return {'raw_response': message.get('content'), 'provider_finish_reason': choice.get('finish_reason'),
            'provider_usage': copy.deepcopy(data.get('usage', {})),
            'provider_reasoning': controls.provider_reasoning(data, profile),
            'actual_response_model': data.get('model'), 'system_fingerprint': data.get('system_fingerprint'),
            'truncated': choice.get('finish_reason') == 'length', 'control_check': check}


def response_checks(turn, body, config, profile, allowance, dry=False):
    """Operational facts come from the original envelope, never copied scores."""
    checks = {'raw_envelope': False, 'copied_fields': False, 'transport': False,
              'controls': False, 'context': False}
    try:
        raw = turn['provider_response_raw']
        data = json.loads(raw)
        copied = copied_fields(data, config, profile, dry)
        checks['raw_envelope'] = (design.digest(raw) == turn['provider_response_raw_sha256']
            and data == turn['provider_response'] and canonical(data) == turn['provider_response_sha256'])
        checks['copied_fields'] = all(k in turn and turn[k] == v for k, v in copied.items())
        usage = copied['provider_usage']
        content = copied['raw_response']
        checks['transport'] = (controls.has_final_content(content)
            and design.digest(content) == turn.get('response_sha256')
            and turn.get('network_retries') == [] and turn.get('http_status') == (None if dry else 200)
            and copied['provider_finish_reason'] == ('synthetic' if dry else 'stop')
            and not copied['truncated'] and 'I have to answer now.' not in (copied['provider_reasoning'] or ''))
        if dry:
            checks['controls'] = (data.get('synthetic') is True and usage == {}
                                  and copied['provider_reasoning'] is None)
            checks['context'] = turn['context_check'] == {'status': 'not_measured_synthetic'}
        else:
            checks['transport'] &= (len(data['choices']) == 1 and type(usage.get('completion_tokens')) is int
                and 0 <= usage['completion_tokens'] <= allowance
                and type(usage.get('prompt_tokens')) is int and usage['prompt_tokens'] >= 0)
            checks['controls'] = (copied['actual_response_model'] == config['response_model']
                and copied['control_check']['mode_verified'] and not copied['control_check']['control_violation'])
            count = turn['context_check']
            if controls.local_context(config):
                match = controls.prompt_usage_check(count, usage)
                checks['context'] = (controls.audit_local_count(count, body, config, output_tokens=allowance)
                    and turn.get('prompt_usage_check') == match and match['matches'])
            else:
                checks['context'] = count == controls.context_bound(body['messages'], config,
                    output_tokens=allowance, allow_system=True) and count['fits']
            checks['context'] &= (type(usage.get('prompt_tokens')) is int
                and 0 <= usage['prompt_tokens'] <= config['context']['tokens'] - allowance)
    except (KeyError, TypeError, ValueError, IndexError, AttributeError):
        pass
    return checks


def cost(usage, config, profile):
    if config is None:
        return {'status': 'unavailable', 'reason': 'synthetic run; no usage or price'}
    if profile == 'gemma_e4b':
        return {'status': 'local_unpriced'}
    prices = config['pricing']
    if all(prices.get(k) is not None for k in ('input_per_million', 'output_per_million')):
        return {'status': 'estimated', 'currency': 'USD', 'source': prices.get('source'),
                'amount': (usage['prompt_tokens'] * prices['input_per_million']
                           + usage['completion_tokens'] * prices['output_per_million']) / 1e6,
                'assumption': 'uncached input; all completion tokens at supplied rate'}
    return {'status': 'unavailable', 'reason': 'verified token prices not supplied'}


def synthetic_answers(world):
    answers, previous = {}, None
    for period in ('A', 'B'):
        estimates = design.from_logs(world[period], previous)
        ref = design.reference(world, period, estimates, previous)
        answers[period + '_prepare'] = 'SYNTHETIC OFFLINE REFERENCE, NOT A MODEL RESULT\n' + json.dumps(estimates)
        for stage in ('task', 'readout'):
            answers[period + '_' + stage] = json.dumps(ref[stage], separators=(',', ':'))
        previous = estimates
    return answers


def persist(path, artifact, event=None):
    if event:
        artifact['persistence_events'].append(event)
    pilot._write_json_atomic(str(path), artifact)


def call_provider(body, config, timeout):
    """Exactly one HTTP attempt; no redirects, retries or provider fallback."""
    endpoint = config['endpoint'].rstrip('/') + '/chat/completions'
    local = config['profile'] == 'gemma_e4b'
    if local:
        if urllib.parse.urlsplit(endpoint).hostname not in ('localhost', '127.0.0.1', '::1'):
            raise ValueError('local Gemma credential cannot leave loopback')
        # This is the optional FRONTEND credential, never the tokenizer key.
        # Do not even read either hosted credential on this path.
        key_name = 'ECPM_LOCAL_API_KEY'
    else:
        key_name = 'TOGETHER_API_KEY' if config['profile'] == 'gemma_31b_together' else 'OPENAI_API_KEY'
    key = os.environ.get(key_name)
    if not key and not local:
        raise ValueError('provider credential not configured')
    headers = {'Content-Type': 'application/json'}
    if key:
        headers['Authorization'] = 'Bearer ' + key
    req = urllib.request.Request(endpoint, json.dumps(body).encode(), headers)
    with urllib.request.build_opener(controls.NoRedirect()).open(req, timeout=timeout) as response:
        return response.status, response.read().decode('utf-8')


def identity(world, arm, repeat, profile, model, config_wrapper, provider, history_policy=design.HISTORY_POLICY):
    design.check_history_policy(history_policy)
    config = config_wrapper['deployment'] if config_wrapper else None
    return {'protocol': design.PROTOCOL, 'preparation_policy': design.PREPARATION_POLICY,
            'history_policy': history_policy, 'scorer': design.SCORER,
            'implementation_commit': pilot.git_head(), 'implementation_dirty': pilot._git_dirty(),
            'graph_seed': world['seed'], 'world_sha256': canonical(world), 'condition': arm,
            'queries': design.queries(world), 'repeat': repeat, 'repeat_seed_label': repeat - 1,
            'sampling_seed_status': 'supported' if config and config['seed_supported'] else 'unsupported' if config else 'not_applied_synthetic',
            'provider': provider, 'profile': profile, 'model': model, 'reasoning_mode': 'off',
            'lock_sha256': canonical(design.lock()), 'prompt_hashes': design.verify_prompts(world),
            'deployment_sha256': canonical(config_wrapper),
            'stage_settings': {str(cap): settings(profile, repeat - 1, bool(config and config['seed_supported']), cap)
                               for cap in (4096,)}}


def run_once(world, arm, repeat, args, wrapper, outdir):
    config = wrapper['deployment'] if wrapper else None
    policy = design.check_history_policy(args.history_policy)
    ident = identity(world, arm, repeat, args.request_profile, args.model, wrapper, args.provider, policy)
    run_id = f'{design.PROTOCOL}_seed{world["seed"]}_{arm}_r{repeat}_{canonical(ident)[:16]}'
    path = Path(outdir) / (run_id + '.json')
    if path.exists():
        raise ValueError('run exists; no overwrite or resume')
    artifact = {'run_id': run_id, 'identity': ident, 'identity_sha256': canonical(ident),
                'synthetic': config is None, 'deployment': wrapper, 'world': world,
                'state': 'initialized', 'turns': {}, 'persistence_events': [], 'run_order': []}
    persist(path, artifact, 'initialized')
    plan = requests(world, arm, policy)
    call = next(plan)
    dry_answers = synthetic_answers(world) if config is None else None
    started = time.monotonic()
    try:
        while True:
            name, cap = call['id'], call['max_output_tokens']
            body = {'model': args.model, 'messages': call['messages'], **ident['stage_settings'][str(cap)]}
            parent = copy.deepcopy(call['messages'][:-1])
            turn = {'history_policy': policy, 'conversation': call['conversation'],
                    'request_body': body, 'request_sha256': canonical(body),
                    'prompt': call['messages'][-1]['content'],
                    'prompt_sha256': design.digest(call['messages'][-1]['content']),
                    'messages_sha256': canonical(call['messages']), 'parent_history': parent,
                    'parent_history_id': 'history_' + canonical(parent), 'parent_history_sha256': canonical(parent),
                    'max_output_tokens': cap, 'network_retries': []}
            artifact['turns'][name] = turn
            artifact['run_order'].append(name)
            persist(path, artifact, name + ':request_saved')
            turn['context_check'] = context_check(body, config, cap) if config else {'status': 'not_measured_synthetic'}
            persist(path, artifact, name + ':context_saved')
            if config and not turn['context_check']['fits']:
                raise RuntimeError('actual conversation cannot fit; no generation')
            began = time.monotonic()
            if config:
                status, raw = call_provider(body, config, args.timeout)
            else:
                status, raw = None, json.dumps({'synthetic': True, 'model': args.model,
                    'choices': [{'finish_reason': 'synthetic', 'message': {'content': dry_answers[name]}}], 'usage': {}})
            # Persist complete provider bytes before decoding/answer parsing.
            controls.no_secrets(raw)
            turn.update(http_status=status, provider_response_raw=raw,
                        provider_response_raw_sha256=design.digest(raw), elapsed_s=time.monotonic() - began)
            persist(path, artifact, name + ':provider_raw_saved')
            envelope = json.loads(raw)
            turn.update(provider_response=envelope, provider_response_sha256=canonical(envelope),
                        **copied_fields(envelope, config, args.request_profile, config is None))
            if isinstance(turn['raw_response'], str):
                turn['response_sha256'] = design.digest(turn['raw_response'])
            if config and controls.local_context(config):
                turn['prompt_usage_check'] = controls.prompt_usage_check(turn['context_check'], turn['provider_usage'])
            persist(path, artifact, name + ':raw_saved')
            turn['operational_checks'] = response_checks(turn, body, config, args.request_profile, cap, config is None)
            if not all(turn['operational_checks'].values()):
                raise RuntimeError('returned answer failed operational checks')
            turn['cost'] = cost(turn['provider_usage'], config, args.request_profile)
            stage = name.split('_', 1)[1]
            turn['parsed'] = (design.parse_task(turn['raw_response'], world, name[0]) if stage == 'task' else
                              design.parse_readout(turn['raw_response'], world[name[0]]) if stage == 'readout' else
                              {'status': 'free_form', 'description_score': 'not_scored_by_design'})
            persist(path, artifact, name + ':parsed_saved')
            try:
                call = plan.send(turn['raw_response'])
            except StopIteration:
                break
        artifact['scores'] = design.score_conversation(world, arm, artifact['turns'])
        artifact['state'] = 'completed'
        artifact['elapsed_s'] = time.monotonic() - started
        persist(path, artifact, 'completed')
        artifact['operational_audit'] = audit_artifact(artifact)
        if not all(artifact['operational_audit'].values()):
            raise RuntimeError('independent audit failed')
        persist(path, artifact)
    except Exception as exc:
        artifact['state'] = 'incomplete'
        artifact['failure'] = {'type': type(exc).__name__, 'stage': call['id'], 'network_retries': []}
        if isinstance(exc, urllib.error.HTTPError):
            raw = exc.read().decode('utf-8', errors='replace')
            try:
                controls.no_secrets(raw)
                artifact['turns'][call['id']].update(http_status=exc.code, provider_response_raw=raw,
                                                    provider_response_raw_sha256=design.digest(raw))
            except ValueError:
                artifact['failure']['sensitive_response_withheld'] = True
        artifact['elapsed_s'] = time.monotonic() - started
        persist(path, artifact, 'operational_failure')
        raise RuntimeError('operational failure saved; no retry or automatic recovery: ' + type(exc).__name__) from None
    return artifact


def audit_artifact(a):
    """Offline audit of raw envelopes, policy-specific history and controls."""
    checks = {'complete': False, 'identity': False, 'history': False,
              'hashes': False, 'persistence': False, 'responses': False, 'no_secrets': False}
    try:
        i, world, turns = a['identity'], a['world'], a['turns']
        wrapper = a['deployment']
        policy = design.check_history_policy(i.get('history_policy'))
        config = validate_config(wrapper, i['profile'], policy) if wrapper else None
        dry = i['provider'] == 'dry-run'
        checks['identity'] = (i['protocol'] == design.PROTOCOL and i['scorer'] == design.SCORER
            and i.get('history_policy') == policy
            and i.get('preparation_policy') == design.PREPARATION_POLICY
            and i['reasoning_mode'] == 'off' and i['condition'] in design.ARMS
            and i['repeat'] in (1, 2, 3) and i['repeat_seed_label'] == i['repeat'] - 1
            and i['world_sha256'] == canonical(world) and world == design.load(i['graph_seed'])
            and i['queries'] == design.queries(world) and i['lock_sha256'] == canonical(design.lock())
            and i['prompt_hashes'] == design.verify_prompts(world)
            and i['deployment_sha256'] == canonical(wrapper) and a['identity_sha256'] == canonical(i)
            and a['synthetic'] == dry == (wrapper is None)
            and (dry or (i['implementation_dirty'] is False and i['model'] == config['model'])))
        expected_id = f'{design.PROTOCOL}_seed{world["seed"]}_{i["condition"]}_r{i["repeat"]}_{canonical(i)[:16]}'
        checks['identity'] &= a['run_id'] == expected_id
        plan = design.schedule(world, i['condition'], {k: t['raw_response'] for k, t in turns.items()}, policy)
        checks['complete'] = (a['state'] == 'completed' and not a.get('failure')
                              and set(turns) == {c['id'] for c in plan} and a['run_order'] == [c['id'] for c in plan])
        checks.update(history=True, hashes=True, persistence=True, responses=True)
        for c in plan:
            name, cap = c['id'], c['max_output_tokens']
            t = turns[name]
            request_settings = settings(i['profile'], i['repeat_seed_label'], bool(config and config['seed_supported']), cap)
            body = {'model': i['model'], 'messages': c['messages'], **request_settings}
            parent = c['messages'][:-1]
            checks['identity'] &= i['stage_settings'][str(cap)] == request_settings
            checks['history'] &= (t['history_policy'] == policy and t['conversation'] == c['conversation']
                and t['request_body'] == body and t['parent_history'] == parent
                and t['parent_history_id'] == 'history_' + canonical(parent)
                and t['parent_history_sha256'] == canonical(parent) and t['max_output_tokens'] == cap)
            checks['hashes'] &= (t['request_sha256'] == canonical(body)
                and t['messages_sha256'] == canonical(c['messages'])
                and t['prompt'] == c['messages'][-1]['content'] and t['prompt_sha256'] == design.digest(t['prompt']))
            events = a['persistence_events']
            required = [name + ':' + e for e in ('request_saved', 'context_saved', 'provider_raw_saved', 'raw_saved', 'parsed_saved')]
            checks['persistence'] &= all(events.count(e) == 1 for e in required)
            checks['persistence'] &= [events.index(e) for e in required] == sorted(events.index(e) for e in required)
            checks['persistence'] &= events.index(required[-1]) < events.index('completed')
            checks['responses'] &= all(response_checks(t, body, config, i['profile'], cap, dry).values())
        controls.no_secrets(a)
        checks['no_secrets'] = True
    except (ValueError, KeyError, TypeError, IndexError, AttributeError):
        pass
    return checks


def write_summary(outdir, expected=3):
    files = sorted(p for p in Path(outdir).glob('*.json') if p.name != 'summary.json')
    records = [json.loads(p.read_text()) for p in files]
    rows = [{'file': p.name, 'run_id': a['run_id'], 'state': a['state'], 'audit': audit_artifact(a)}
            for p, a in zip(files, records)]
    policies = sorted({a['identity']['history_policy'] for a in records})
    summary = {'protocol': design.PROTOCOL, 'preparation_policy': design.PREPARATION_POLICY, 'history_policies': policies,
               'history_policy': policies[0] if len(policies) == 1 else None,
               'expected_conversations': expected,
               'completed_conversations': sum(a['state'] == 'completed' for a in records),
               'saved_responses': sum('provider_response_raw' in t for a in records for t in a['turns'].values()),
               'runs': rows, 'operational_gate_pass': len(policies) == 1 and len(rows) == expected and all(all(r['audit'].values()) for r in rows)}
    summary['usage_by_workflow'] = {}
    # total = main + measurement_branch. Stage subtotals also partition total.
    for group in ('total', 'main', 'measurement_branch', 'model_and_task', 'transition_report'):
        turns = [t for a in records for name, t in a['turns'].items()
                 if (group == 'total' or
                     (group in ('main', 'measurement_branch') and t.get('conversation') == group) or
                     (group in ('model_and_task', 'transition_report') and
                      name.endswith('_readout') == (group == 'transition_report')))
                 and 'provider_usage' in t]
        usage = {}
        for field in ('prompt_tokens', 'completion_tokens'):
            values = [t['provider_usage'].get(field) for t in turns]
            known = [v for v in values if type(v) is int]
            usage[field] = {'sum': sum(known) if known else None, 'n_reported': len(known), 'n_responses': len(values)}
        prices = [t.get('cost', {}) for t in turns]
        amounts = [c['amount'] for c in prices if c.get('status') == 'estimated']
        usage['estimated_usd'] = {'sum': sum(amounts) if amounts else None, 'n_priced': len(amounts), 'n_responses': len(turns)}
        summary['usage_by_workflow'][group] = usage
    pilot._write_json_atomic(str(Path(outdir) / 'summary.json'), summary)
    return summary


def block_cost_plan(world, arm, wrapper, repeats=3, history_policy=design.HISTORY_POLICY):
    """Conservative ceiling from the admitted context, not a token-use forecast."""
    if type(repeats) is not int or repeats not in (1, 3):
        raise ValueError('one or three repeats required')
    calls = design.schedule(world, arm, synthetic_answers(world), history_policy)
    completion = repeats * sum(c['max_output_tokens'] for c in calls)
    if wrapper is None:
        return {'status': 'unavailable', 'reason': 'no verified deployment/rates',
                'history_policy': history_policy,
                'repeats': repeats, 'requests': len(calls) * repeats, 'maximum_completion_tokens': completion}
    config = wrapper['deployment']
    ceiling = repeats * sum(config['context']['tokens'] - c['max_output_tokens'] for c in calls)
    prices = config['pricing']
    result = {'status': 'local_unpriced' if config['profile'] == 'gemma_e4b' else 'estimated',
              'history_policy': history_policy,
              'repeats': repeats, 'requests': len(calls) * repeats, 'maximum_completion_tokens': completion,
              'admitted_input_token_ceiling': ceiling,
              'assumption': 'every actual policy-specific request fills its admitted context and completion allowance; uncached prices; preflight excluded'}
    if config['profile'] in controls.HOSTED_PROFILES:
        result.update(usd_ceiling=(ceiling * prices['input_per_million'] + completion * prices['output_per_million']) / 1e6,
                      rate_source=prices['source'])
    return result


def run_suite(sc, args, outdir):
    policy = design.check_history_policy(args.history_policy)
    if args.model_first_condition not in design.ARMS or args.request_profile not in controls.MODELS:
        raise ValueError('explicit model-first condition and request profile required')
    if (args.mode != 'det' or args.pilot_type != 'passive' or type(args.repeats) is not int
            or args.repeats not in (1, 3) or args.sampling_seeds != list(range(args.repeats))
            or args.max_tokens != 4096 or args.reasoning_mode != 'off'):
        raise ValueError('locked pilot: passive det, OFF, one repeat 0 or three repeats 0/1/2, 4096 per-stage allowance')
    if (args.graph_condition or args.off_reference or args.reasoning_control_json or args.reasoning_control_source
            or args.temperature != 0 or args.top_p is not None or args.top_k is not None
            or args.sampling_seed_support != 'auto' or args.provider not in ('dry-run', 'openai')):
        raise ValueError('use only locked profile controls; no ON fallback or legacy overrides')
    if Path(outdir).exists():
        raise ValueError('output directory exists; no overwrite or resume')
    # This validates evidence settings and refuses redirect, stochastic or changed budgets.
    controls.prepare(sc)
    world = design.verify_world(sc['seed'])
    design.verify_prompts(world)
    wrapper = None
    if args.provider != 'dry-run':
        if pilot._git_dirty():
            raise ValueError('real runs require a clean implementation commit')
        if not args.deployment_config:
            raise ValueError('verified deployment and model-first stage/path evidence required')
        wrapper = json.loads(Path(args.deployment_config).read_text())
        config = validate_config(wrapper, args.request_profile, policy)
        if args.model != config['model'] or args.base_url.rstrip('/') != config['endpoint'].rstrip('/'):
            raise ValueError('exact deployment model/endpoint mismatch')
    elif args.deployment_config:
        raise ValueError('dry runs must not use private readiness configurations')
    planned_cost = block_cost_plan(world, args.model_first_condition, wrapper, args.repeats, policy)
    print(json.dumps({'prelaunch_cost_plan': planned_cost}, sort_keys=True))
    Path(outdir).mkdir(parents=True, exist_ok=False)
    try:
        for repeat in range(1, args.repeats + 1):
            a = run_once(world, args.model_first_condition, repeat, args, wrapper, outdir)
            print(a['run_id'] + ': completed' + (' SYNTHETIC' if a['synthetic'] else ''))
    finally:
        summary = write_summary(outdir, expected=args.repeats)
        summary['prelaunch_cost_plan'] = planned_cost
        pilot._write_json_atomic(str(Path(outdir) / 'summary.json'), summary)
    print('operational gate: ' + ('PASS' if summary['operational_gate_pass'] else 'FAIL'))
    return summary

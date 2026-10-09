"""Offline expanded coverage, exact plans and saved-score exports. Stdlib only."""

import argparse
import csv
import hashlib
import itertools
import json
import math
import statistics
import sys
import tempfile
import zipfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import icl_expanded as design
import icl_model_first as pilot
import icl_model_first_runner as runner
from experiments.preview_icl_model_first import compatible_identity, save


def arguments(arm, mode, policy, profile='gemma_e4b', output_tokens=design.CAP):
    return SimpleNamespace(provider='dry-run', request_profile=profile, model=None,
        reasoning_mode=mode, history_policy=policy, model_first_condition=arm, timeout=900,
        max_tokens=design.output_allowance(output_tokens))


def command(seed, mode, scenario, arm, reasoning, policy, profile, tag, config=None, k=10, repeats=1, output_tokens=design.NEW_CAP):
    args = ['python3', '-B', 'run_pilot.py', '--protocol', design.PROTOCOL,
        '--seed', str(seed), '--mode', mode, '--condition', scenario,
        '--k', str(k), '--budget', str(k), '--evidence-seed', '0',
        '--model-first-condition', arm, '--history-policy', policy,
        '--request-profile', profile, '--reasoning-mode', reasoning,
        '--repeats', str(repeats), '--sampling-seeds', *map(str, range(repeats)), '--max-tokens', str(design.output_allowance(output_tokens)),
        '--provider', 'openai' if config else 'dry-run', '--tag', tag]
    if config:
        args += ['--model', config['model'], '--base-url', config['endpoint'],
                 '--deployment-config', '<verified-expanded-config.json>']
    return args


def plan(profile, wrappers=(), k=10, repeats=1):
    """An illustration is not a provider plan. Only validated wrappers admit live rows."""
    if profile not in design.controls.EXPANDED_MODELS:
        raise ValueError('unknown request profile')
    if k not in design.SUPPORTED_K or repeats not in (1, 5):
        raise ValueError('K=10 and one/five repeats required')
    approved, excluded = {}, []
    for wrapper in wrappers:
        mode, policy = wrapper['expanded']['reasoning_mode'], wrapper['expanded']['history_policy']
        cap = design.output_allowance(wrapper['expanded']['output_allowances'][0])
        config = design.validate_config(wrapper, profile, mode, policy, cap)
        key = (mode, policy)
        if key in approved:
            raise ValueError('duplicate readiness mode/history')
        approved[key] = (config, cap)
    rows = []
    for (seed, mode, scenario), arm, history, reasoning in itertools.product(
            design.configurations(), design.ARMS, design.HISTORY_POLICIES, ('off', 'on')):
        config, cap = approved.get((reasoning, history), (None, design.NEW_CAP))
        if wrappers and config is None:
            excluded.append(dict(seed=seed, mode=mode, scenario=scenario, arm=arm,
                                 history=history, reasoning=reasoning, reason='no validated configuration'))
            continue
        tag = f'expanded_{seed}_{mode}_{scenario}_{arm}_{history}_{reasoning}'
        settings = runner.settings(profile, 0, bool(config and config['seed_supported']), cap, reasoning, config)
        stage_ids = [p + '_' + s for p in ('A', 'B') for s in design.stages(arm)]
        rows.append(dict(graph_seed=seed, mode=mode, scenario=scenario, arm=arm,
            history_policy=history, reasoning_mode=reasoning, sampling_seed_label=0,
            sampling_seed_status='unverified_not_applied' if not config else 'supported' if config['seed_supported'] else 'unsupported',
            settings=settings, requests=len(stage_ids) * repeats, repeats=repeats, k=k,
            sampling_seed_labels=list(range(repeats)), output_allowance_per_request=cap,
            stages=stage_ids,
            cost_plan={'status': 'unavailable', 'reason': 'no verified deployment/rates'} if not config else
                runner.block_cost_plan(design.build_world(seed, mode, scenario, k), arm,
                    {'deployment': config}, repeats=repeats, history_policy=history, design_api=design, output_tokens=cap),
            argv=command(seed, mode, scenario, arm, reasoning, history, profile, tag, config, k, repeats, cap),
            deployment_sha256=runner.canonical(config) if config else None))
    return {'protocol': design.PROTOCOL, 'schedule': design.SCHEDULE, 'profile': profile,
        'status': 'validated_configuration_plan_not_live_verification' if wrappers else 'synthetic_illustration_not_provider_plan',
        'conversations': repeats * len(rows), 'responses': sum(r['requests'] for r in rows),
        'maximum_output_tokens': sum(r['output_allowance_per_request'] * r['requests'] for r in rows), 'input_tokens': None,
        'estimated_cost': None, 'billing_cost': None,
        'cost_note': 'Unknown until admitted inputs and verified rates are supplied; ceilings are not forecasts.',
        'rows': rows, 'excluded': excluded}


def dimensions(a):
    i = a['identity']
    return {k: i[k] for k in ('protocol', 'preparation_policy', 'scorer', 'schedule', 'graph_seed', 'mode', 'scenario',
        'condition', 'history_policy', 'reasoning_mode', 'profile', 'model', 'provider', 'repeat',
        'repeat_seed_label', 'implementation_commit', 'world_sha256', 'deployment_sha256')} | {
        'run_id': a['run_id'], 'synthetic': a['synthetic'], 'source_sha256': i['source_sha256'],
        'output_allowance_per_response': design.artifact_allowance(i),
        'k': i['evidence_settings']['k'], 'evidence_seed': i['evidence_settings']['evidence_seed'],
        'query_policy': i['query_policy'], 'preparation_word_target': i['preparation_word_target']}


def metric_rows(a, status):
    """Saved numerators only. No reparsing, rescoring or dropping malformed rows."""
    dims = dimensions(a) | {'operational_status': status}
    rows = []
    def emit(metric, numerator=None, denominator=0, period=None, query=None, value=None):
        rows.append(dims | dict(period=period, query_id=query, metric=metric,
            numerator=numerator, denominator=denominator,
            value=(numerator / denominator if denominator else None) if value is None else value))
    if status != 'valid':
        emit('operationally_quarantined')
        return rows
    s = a['scores']
    for period in ('A', 'B'):
        p = s['periods'][period]
        prep = s['preparation'][period]
        emit('preparation_status', period=period, value=prep['status'])
        if prep['status'] != 'not_applicable':
            emit('preparation_needs_review', int(not prep['scored']), 1, period)
            emit('preparation_word_count', prep['word_count'], 1, period)
            emit('preparation_length_target_met', int(prep['length_target_met']), 1, period)
            emit('preparation_table_present', int(prep['table_present']), 1, period)
            v = prep['transition_content']
            emit('preparation_transition_content', int(v) if v is not None else None, int(v is not None), period)
            emit('preparation_reported_pairs', prep['reported_pairs'], prep['required_pairs'], period)
            for name in ('pair_exact', 'pair_tolerance', 'destination_correct'):
                v = prep[name]
                emit('preparation_' + name, v['numerator'], v['denominator'], period)
            v = prep['p_mae_truth']
            emit('preparation_p_mae_truth_conditional', v['sum'], v['n'], period)
        for name in ('task', 'readout'):
            emit(name + '_well_formed', int(p[name + '_parsed']['well_formed']), 1, period)
        emit('complete_graph_exact', int(p['beliefs']['complete_graph_exact']), 1, period)
        for name, v in p['beliefs'].items():
            if isinstance(v, dict) and 'numerator' in v:
                emit(name, v['numerator'], v['denominator'], period)
            elif isinstance(v, dict) and 'sum' in v:
                emit(name, v['sum'], v['n'], period)
        if period == 'B':
            for name in ('detection_correct', 'localization_correct', 'localization_changed_case', 'no_change_null_correct'):
                v = p[name]
                emit(name, int(v) if v is not None else None, int(v is not None), period)
            for name in ('sensitivity', 'specificity'):
                v = p[name]; emit(name, v['numerator'], v['denominator'], period)
        for q, r in p['routes'].items():
            for name in ('valid', 'optimal', 'solution_correct', 'reachability_correct'):
                emit('route_' + name, int(r[name]), 1, period, q)
            # Keep legacy fields, while giving all-query correctness and
            # reachable-only optimality explicit, non-overlapping meanings.
            reachable = r['oracle_reachable']
            emit('route_oracle_reachable', int(reachable), 1, period, q)
            emit('route_optimal_solution', int(r['optimal'] or r['status'] == 'correct_no_route'), 1, period, q)
            emit('route_optimal_reachable', int(r['optimal']) if reachable else None,
                 int(reachable), period, q)
            emit('route_correct_no_route', int(r['status'] == 'correct_no_route') if not reachable else None,
                 int(not reachable), period, q)
            for name in ('cost', 'regret'):
                emit('route_' + name + '_conditional', r[name], int(r[name] is not None), period, q)
            for name in ('own_report_optimal', 'own_report_no_route_correct'):
                v = r[name]
                emit(name, int(v) if v is not None else None, int(v is not None), period, q)
            emit('route_status', period=period, query=q, value=r['status'])
            emit('route_report_diagnostic', period=period, query=q, value=r['consistency'])
        for pair, r in p['beliefs']['rows'].items():
            for name, v in r.items():
                if v is not None:
                    emit('pair_' + name, int(v), 1, period, pair)
    for kind in ('preservation', 'preservation_tolerance'):
        for basis in ('self', 'truth'):
            p = s[kind][basis]
            for scope in ('all_controls', 'conditional'):
                v = p[scope]; emit(f'{kind}_{basis}_{scope}', v['numerator'], v['denominator'], 'B')
            emit(f'{kind}_{basis}_all_four_correct', int(p['all_four_correct']), 1, 'B')
    for metric, value in s['updating'].items():
        if metric == 'queries':
            for q, detail in value.items():
                for name, flag in detail.items():
                    emit('updating_' + name, int(flag) if flag is not None else None, int(flag is not None), 'B', q)
        else:
            emit(metric, value['numerator'], value['denominator'], 'B')
    return rows


def repeat_statistics(metrics):
    """Within-configuration dispersion, never an independent-world estimate."""
    groups = {}
    for row in metrics:
        key = (row['group'], row['metric'], row['period'], row['query_id'])
        value = row['value']
        if type(value) not in (int, float) or not math.isfinite(value):
            continue
        groups.setdefault(key, []).append(row)
    result = []
    for (group, metric, period, query), rows in sorted(groups.items(), key=lambda item: str(item[0])):
        values = [r['value'] for r in rows]
        result.append(dict(group=group, metric=metric, period=period, query_id=query,
            n=len(values), repeat_labels=[r['repeat_seed_label'] for r in rows],
            mean=statistics.mean(values), sample_std=statistics.stdev(values) if len(values) > 1 else None,
            note='within one configuration and graph; conditional metrics include scored repeats only'))
    return result


def summarize(paths):
    files = [f for p in paths for f in (sorted(Path(p).glob('*.json')) if Path(p).is_dir() else [Path(p)])
             if f.name != 'summary.json']
    if not files:
        raise ValueError('empty input is not a result')
    metrics, usage, runs, review, seen, repeats = [], [], [], [], set(), set()
    for path in files:
        a = json.loads(path.read_text())
        if a['identity']['protocol'] != design.PROTOCOL:
            raise ValueError('wrong protocol input')
        group = runner.canonical(compatible_identity(a, max_repeat=5))
        repeat = (group, a['identity']['repeat'])
        if a['run_id'] in seen or repeat in repeats:
            raise ValueError('duplicate run/repeat identity')
        seen.add(a['run_id']); repeats.add(repeat)
        audit = runner.audit_artifact(a, design)
        status = 'valid' if all(audit.values()) else 'quarantined'
        if status == 'valid' and a.get('scores', {}).get('scorer') != design.SCORER:
            raise ValueError('missing or incompatible saved scores')
        runs.append(dimensions(a) | {'group': group, 'operational_status': status, 'audit': audit})
        metrics += [r | {'group': group} for r in metric_rows(a, status)]
        if status == 'valid':
            for period, score in a['scores']['preparation'].items():
                if score['status'] == 'needs_review':
                    review.append(dimensions(a) | dict(period=period,
                        raw_response=a['turns'][period + '_prepare']['raw_response'],
                        extraction=score,
                        truth=design.build_world(a['identity']['graph_seed'], a['identity']['mode'],
                            a['identity']['scenario'], a['identity']['evidence_settings']['k'])[period]['graph']))
        for stage, t in a['turns'].items():
            u = t.get('provider_usage', {})
            details = u.get('prompt_tokens_details')
            usage.append(dimensions(a) | dict(group=group, operational_status=status, stage=stage,
                prompt_tokens=u.get('prompt_tokens'), completion_tokens=u.get('completion_tokens'),
                reasoning_tokens=t.get('control_check', {}).get('reasoning_tokens'),
                cached_tokens=details.get('cached_tokens') if isinstance(details, dict) else None,
                exposed_reasoning=t.get('provider_reasoning'),
                reasoning_details=t.get('provider_reasoning_details'),
                returned_model=t.get('actual_response_model'),
                returned_provider=t.get('actual_response_provider'),
                finish_reason=t.get('provider_finish_reason'), truncated=t.get('truncated'),
                provider_usage=u,
                estimated_cost=t.get('cost'), billing_reconciliation=None))
    return {'runs': runs, 'metrics': metrics, 'request_usage': usage,
            'repeat_statistics': repeat_statistics(metrics), 'preparation_review': review,
            'policy': 'fresh operational audit; incompatible groups separate; saved scores unchanged; no historical rescoring'}


def empty_task_answer_json(text):
    """Narrow format diagnostic, not preparation scoring or a parser fallback."""
    if not isinstance(text, str):
        return False
    try:
        value = json.loads(text)
    except ValueError:
        return False
    return (isinstance(value, dict) and value.get('routes') == []
            and set(value) <= {'routes', 'changed', 'changed_pair'})


def review_preparation(paths):
    """Read saved preparation text, including historical ZIPs, without rescoring."""
    def inputs():
        for source in map(Path, paths):
            if source.suffix.lower() == '.zip':
                with zipfile.ZipFile(source) as archive:
                    for name in sorted(archive.namelist()):
                        if Path(name).name.startswith('icl_expanded_v2_') and name.endswith('.json'):
                            yield str(source) + ':' + name, archive.read(name)
            else:
                files = sorted(source.rglob('icl_expanded_v2_*.json')) if source.is_dir() else [source]
                for path in files:
                    yield str(path), path.read_bytes()

    runs, rows, groups, seen = 0, [], {}, set()
    for source, raw in inputs():
        a = json.loads(raw)
        i = a['identity']
        if i['protocol'] != design.PROTOCOL:
            raise ValueError('wrong protocol input')
        if a['run_id'] in seen:
            raise ValueError('duplicate run in preparation review')
        seen.add(a['run_id']); runs += 1
        key = (i['condition'], i['preparation_policy'], i['implementation_commit'])
        group = groups.setdefault(key, dict(condition=key[0], preparation_policy=key[1],
            implementation_commit=key[2], runs=0, completed_runs=0,
            completed_both_empty_task_json=0, periods={p: dict(completed_responses=0,
                completed_missing_responses=0, empty_task_json=0) for p in ('A', 'B')}))
        completed = a['state'] == 'completed'
        group['runs'] += 1; group['completed_runs'] += int(completed)
        if 'prepare' not in i['stages']:
            continue
        flags = []
        for period in ('A', 'B'):
            text = a['turns'].get(period + '_prepare', {}).get('raw_response')
            flag = empty_task_answer_json(text)
            flags.append(flag)
            counts = group['periods'][period]
            if completed:
                counts['completed_responses'] += int(isinstance(text, str))
                counts['completed_missing_responses'] += int(not isinstance(text, str))
                counts['empty_task_json'] += int(flag)
            rows.append(dict(run_id=a['run_id'], condition=i['condition'],
                graph_seed=i['graph_seed'], mode=i['mode'], scenario=i['scenario'],
                history_policy=i['history_policy'], repeat=i['repeat'], period=period,
                state=a['state'], preparation_policy=i['preparation_policy'],
                status='missing' if not isinstance(text, str) else
                    'empty_task_answer_json' if flag else 'not_flagged_not_a_compliance_pass',
                source=source, source_sha256=hashlib.sha256(raw).hexdigest(),
                response_sha256=hashlib.sha256(text.encode()).hexdigest() if isinstance(text, str) else None))
        group['completed_both_empty_task_json'] += int(completed and all(flags))
    if not any(r['response_sha256'] is not None for r in rows):
        raise ValueError('no preparation responses examined')
    return dict(policy='diagnostic only: whole-response JSON with empty routes and optional change fields; '
                'not an operational audit, compliance pass, parser replacement or rescore; no retries',
                runs=runs, groups=list(groups.values()), responses=rows)


def coverage(out):
    out = Path(out)
    if out.exists():
        raise ValueError('output exists')
    out.mkdir(parents=True)
    records, prompt_hashes, history_hashes = [], {}, {}
    first_a, first_questions = {}, {}
    for seed, mode, scenario in design.configurations():
        w = design.build_world(seed, mode, scenario)
        qs = design.queries(w)
        key = (seed, mode)
        ah = runner.canonical(w['A'])
        first_a.setdefault(key, ah); first_questions.setdefault(seed, qs)
        assert first_a[key] == ah and first_questions[seed] == qs
        oracle = design.oracle_answers(w)
        scored = design.score_conversation(w, 'model_first', {k: {'raw_response': v} for k, v in oracle.items()})
        reference = design.evidence_reference(w['visible'], qs)
        ref_scores = design.score_conversation(w, 'model_first', {k: {'raw_response': v} for k, v in reference['answers'].items()})
        for period in ('A', 'B'):
            assert scored['periods'][period]['beliefs']['joint_exact']['value'] == 1
            assert all(r['solution_correct'] for r in scored['periods'][period]['routes'].values())
            common = []
            for arm in design.ARMS:
                p = design.prompts(w, period, arm)
                prepare = (p['prepare'] if 'prepare' in p else p['task']).split('\n\n', 1)[0]
                if arm == 'graph_given':
                    prepare = prepare.replace(design.graph_text(w[period]) + '\n', '', 1)
                common.append(prepare)
                for stage, text in p.items():
                    prompt_hashes[f'{seed}/{mode}/{scenario}/{arm}/{period}/{stage}'] = pilot.digest(text)
            assert len(set(common)) == 1
        identities = []
        # Temporary synthetic runs exercise the actual shared persistence/audit path.
        for arm, history, reasoning in itertools.product(design.ARMS, design.HISTORY_POLICIES, ('off', 'on')):
            with tempfile.TemporaryDirectory(prefix='expanded-synthetic-') as temporary:
                a = runner.run_once(w, arm, 1, arguments(arm, reasoning, history, output_tokens=design.NEW_CAP), None, temporary, design)
                assert all(runner.audit_artifact(a, design).values())
                assert len(a['turns']) == 2 * len(design.stages(arm))
                assert all(a['scores'][k] == scored[k] for k in ('periods', 'preservation', 'preservation_tolerance'))
                identities.append(a['run_id'])
                history_hashes[f'{seed}/{mode}/{scenario}/{arm}/{history}/{reasoning}'] = runner.canonical(
                    [t['request_body']['messages'] for t in a['turns'].values()])
        records.append({'seed': seed, 'mode': mode, 'scenario': scenario, 'world_sha256': runner.canonical(w),
            'A_sha256': ah, 'queries': qs, 'required_pairs': w['A']['required_pairs'],
            'true_changes': w['true_changes'], 'controls': w['controls'],
            'synthetic_run_ids': identities, 'oracle_reference': scored,
            'evidence_reference': {'identity': reference['identity'], 'baseline': reference['baseline'], 'scores': ref_scores}})
    for arm in design.ARMS:
        w = design.build_world(8, 'det', 'silent_break')
        sections = [f'Expanded ICL, seed 8, deterministic silent break, {arm}',
            'Complete fixed messages, in request order. Each response is supplied by the run.',
            'Retained history includes reports; separate post-task copies do not replay reports.',
            'Provider-private reasoning is never replayed.', '\nSYSTEM\n' + design.system(w)]
        for period in ('A', 'B'):
            for stage, text in design.prompts(w, period, arm).items():
                sections.append('\n' + period + '_' + stage + '\n' + text)
        save(out / 'prompts' / (arm + '.txt'), '\n\n'.join(sections) + '\n')
    report = {'worlds': len(records), 'synthetic_conversations': sum(len(r['synthetic_run_ids']) for r in records),
        'synthetic_responses': sum(2 * len(design.stages(arm)) for arm, history, reasoning in itertools.product(
            design.ARMS, design.HISTORY_POLICIES, ('off', 'on'))) * len(records), 'provider_calls': 0,
        'reasoning_labels': 'requested synthetic plan labels, not live verified OFF/ON evidence',
        'prompt_hashes': prompt_hashes, 'history_hashes': history_hashes, 'worlds_and_references': records}
    save(out / 'offline_coverage.json', report)
    save(out / 'illustrative_plan.json', plan('gemma_e4b'))
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--coverage', action='store_true')
    ap.add_argument('--summarize', nargs='+')
    ap.add_argument('--review-preparation', nargs='+', help='read-only empty task-JSON diagnostic for saved run directories or ZIPs')
    ap.add_argument('--plan-profile', choices=tuple(design.controls.EXPANDED_MODELS))
    ap.add_argument('--config', action='append', default=[], help='explicit non-secret expanded readiness file for a supported mode/history')
    ap.add_argument('--k', type=int, choices=design.SUPPORTED_K, default=10)
    ap.add_argument('--repeats', type=int, choices=(1, 5), default=1)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    if sum(map(bool, (args.coverage, args.summarize, args.plan_profile, args.review_preparation))) != 1:
        ap.error('choose coverage, summarize, plan-profile or review-preparation')
    if args.config and not args.plan_profile:
        ap.error('configs are used only for explicit provider planning')
    if args.review_preparation:
        result = review_preparation(args.review_preparation)
        save(Path(args.out) / 'preparation_diagnostic.json', result)
        print(json.dumps({'runs': result['runs'], 'groups': result['groups']}))
    elif args.coverage:
        r = coverage(args.out)
        print(json.dumps({k: r[k] for k in ('worlds', 'synthetic_conversations', 'synthetic_responses', 'provider_calls')}))
    elif args.plan_profile:
        wrappers = [json.loads(Path(p).read_text()) for p in args.config]
        result = plan(args.plan_profile, wrappers, args.k, args.repeats)
        paths = {(w['expanded']['reasoning_mode'], w['expanded']['history_policy']): p for w, p in zip(wrappers, args.config)}
        for row in result['rows']:
            if wrappers:
                row['argv'][-1] = paths[(row['reasoning_mode'], row['history_policy'])]
        save(Path(args.out) / 'plan.json', result)
    else:
        result = summarize(args.summarize)
        save(Path(args.out) / 'results.json', result)
        for name in ('metrics', 'request_usage'):
            with (Path(args.out) / (name + '.csv')).open('x', newline='') as stream:
                rows = result[name]
                if not rows:
                    raise ValueError('no export rows')
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                for row in rows:
                    writer.writerow({k: json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) or v is None else v for k, v in row.items()})
        save(Path(args.out) / 'preparation_review.json', result['preparation_review'])
        with (Path(args.out) / 'repeat_statistics.csv').open('x', newline='') as stream:
            rows = result['repeat_statistics']
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else
                ['group', 'metric', 'period', 'query_id', 'n', 'repeat_labels', 'mean', 'sample_std', 'note'])
            writer.writeheader()
            for row in rows:
                writer.writerow({k: json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) or v is None else v for k, v in row.items()})


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Offline previews and saved-score reports. No API calls."""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import icl_model_first as design
import icl_model_first_runner as runner


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(value if isinstance(value, str) else json.dumps(value, indent=2, sort_keys=True) + '\n')


def plan(repeats=1, history_policy=design.HISTORY_POLICY):
    design.check_history_policy(history_policy)
    if type(repeats) is not int or repeats not in (1, 3):
        raise ValueError('one or three repeats required')
    branched = history_policy != design.HISTORY_POLICY
    return {'protocol': design.PROTOCOL, 'preparation_policy': design.PREPARATION_POLICY, 'history_policy': history_policy,
            'status': 'offline only; deployment not ready',
            'first_graph_seed': 8, 'repeats_per_condition': repeats,
            'sampling_seed_labels': list(range(repeats)), 'reasoning': 'off',
            'blocks': [{'condition': arm, 'conversations': repeats,
                        'requests': repeats * 6,
                        'main_output_allowance': repeats * (16384 if branched else 24576),
                        'measurement_branch_output_allowance': repeats * (8192 if branched else 0),
                        'model_and_task_output_allowance': repeats * 16384,
                        'transition_report_output_allowance': repeats * 8192}
                       for arm in design.ARMS],
            'conversations_per_model': 3 * repeats, 'requests_per_model': 18 * repeats,
            'maximum_completion_tokens_per_model': 3 * repeats * 24576,
            'all_three_worlds_if_later_authorized': {'conversations': 9 * repeats, 'requests': 54 * repeats},
            'preflights': 'excluded; separately authorized only',
            'input_tokens': None, 'cost_usd': None, 'cost_status': 'unavailable',
            'assumptions': ['Completion counts are ceilings, not expected usage.',
                            'Count each policy-specific rendered request, including every retained actual answer and the current report question.',
                            'Retained reports enter B; post-task copies exclude previous reports, not earlier evidence or task/model answers.',
                            'No previous answer bounds every future answer; count each actual request.',
                            'Uncached USD = input_tokens * input_rate / 1e6 + completion_tokens * output_rate / 1e6.',
                            'Total usage equals main plus measurement branches; model/task and report subtotals are an alternative partition, not extra usage.'],
            'deployment': {'provider': None, 'endpoint': None, 'exact_model': None,
                           'tokenizer_template_verified': False, 'stage_limits_verified': False,
                           'input_usd_per_million': None, 'output_usd_per_million': None}}


def conversation_example(world, arm, answers, history_policy=design.HISTORY_POLICY):
    """Complete inputs and answers per request, including independent copies."""
    calls = design.schedule(world, arm, answers, history_policy)
    lines = [f'# Seed {world["seed"]}: {arm}', '',
             f'History policy: `{history_policy}`. SYNTHETIC REFERENCE, NOT MODEL OUTPUT.', '',
             'Each section shows the complete request in order, then its synthetic final answer.',
             'Repeated text below represents retained input, not extra generation calls.',
             'No provider-private reasoning is replayed.', '',
             '| Request | Conversation | Input messages | Input text characters | Output allowance |',
             '| --- | --- | --- | --- | --- |']
    for call in calls:
        lines.append(f'| {call["id"]} | {call["conversation"]} | {len(call["messages"])} | '
                     f'{sum(len(m["content"]) for m in call["messages"])} | {call["max_output_tokens"]} |')
    lines += ['', 'Character counts are not tokenizer counts or future-answer bounds. Actual request',
              'admission needs verified template/tokenizer or hosted context evidence.', '']
    for call in calls:
        lines += [f'## {call["id"]}: {call["conversation"]}', '']
        for index, message in enumerate(call['messages'], 1):
            lines += [f'### Input {index}: {message["role"]}', '', '```text', message['content'], '```', '']
        lines += ['### Synthetic final answer', '', '```text', answers[call['id']], '```', '']
    return '\n'.join(lines)


def generate(out, history_policy=design.HISTORY_POLICY):
    design.check_history_policy(history_policy)
    out = Path(out)
    if out.exists():
        raise ValueError('review output exists; use an unused directory')
    out.mkdir(parents=True)
    manifest, history_checks, checks, references = {}, {}, [], {}
    for seed in (8, 13, 25):
        world = design.verify_world(seed)
        manifest.update(design.verify_prompts(world))
        history_checks.update(design.verify_histories(world, history_policy))
        answers = runner.synthetic_answers(world)
        locked_answers = {p + '_' + s: f'SYNTHETIC {p}_{s}; NOT A MODEL RESULT'
                          for p in ('A', 'B') for s in ('prepare', 'task', 'readout')}
        for arm in design.ARMS:
            if seed == 8:
                # Reviewer export: one complete initial prompt per condition.
                save(out / 'review_prompts' / f'{arm}.txt',
                     design.prompts(world, 'A', arm)['prepare'] + '\n')
            for period in ('A', 'B'):
                for stage, text in design.prompts(world, period, arm).items():
                    save(out / 'prompts' / f'seed_{seed}' / arm / f'{period}_{stage}.txt', text + '\n')
            raw_example = json.dumps(design.schedule(world, arm, locked_answers, history_policy), indent=2) + '\n'
            save(out / 'prompts' / f'seed_{seed}' / arm / 'request_history_example.json', raw_example)
            history = design.schedule(world, arm, answers, history_policy)
            save(out / 'histories' / f'seed_{seed}_{arm}.json', {
                'synthetic': True, 'history_policy': history_policy, 'requests': history})
            if seed == 8:
                save(out / 'examples' / f'seed_8_{arm}.md', conversation_example(world, arm, answers, history_policy))
            turns = {key: {'raw_response': value} for key, value in answers.items()}
            scored = design.score_conversation(world, arm, turns)
            for p in ('A', 'B'):
                s = scored['periods'][p]
                if (s['beliefs']['joint_exact']['numerator'] != 16
                        or not all(r['solution_correct'] for r in s['routes'].values())):
                    raise ValueError('offline reference failed: ' + str((seed, arm, p)))
            references[f'{seed}/{arm}'] = {'synthetic': True, 'answers': answers, 'scores': scored}
        estimates = design.from_logs(world['A'])
        for p in ('A', 'B'):
            if p == 'B':
                estimates = design.from_logs(world['B'], estimates)
            if estimates != world[p]['graph']:
                raise ValueError('evidence reference does not match truth')
            base = design.evidence(world, p, 'task_only')
            if (base != design.evidence(world, p, 'model_first')
                    or base != design.evidence(world, p, 'graph_given').replace(design.graph_text(world[p]) + '\n', '', 1)):
                raise ValueError('non-graph evidence difference')
            checks.append({'seed': seed, 'period': p, 'observations': len(world[p]['rows']),
                           'pairs': len(estimates), 'reference_exact': True, 'common_evidence_identical': True})
    source = []
    for name, expected in design.lock()['source_hashes'].items():
        if not name.endswith('.py'):
            source.append({'file': name, 'status': 'source not supplied; not independently verified'})
            continue
        raw = subprocess.check_output(['git', 'show', design.lock()['source_commit'] + ':' + name])
        actual = hashlib.sha256(raw).hexdigest()
        extra_lf_match = hashlib.sha256(raw + b'\n').hexdigest() == expected
        source.append({'file': name, 'bundle_sha256': expected, 'published_sha256': actual,
                       'match': expected == actual,
                       'reconciled': expected == actual or extra_lf_match,
                       'relationship': 'byte_identical' if expected == actual else
                           'bundle_has_one_extra_trailing_LF' if extra_lf_match else 'unresolved',
                       'published_bytes': len(raw),
                       'bundle_bytes': len(raw) + 1 if extra_lf_match else len(raw) if expected == actual else None})
    report = {'protocol': design.PROTOCOL, 'preparation_policy': design.PREPARATION_POLICY, 'history_policy': history_policy,
              'model_calls': 0, 'deployment_ready': False,
              'base_commit': design.lock()['source_commit'], 'prompt_files_exact': len(manifest),
              'prompt_checks': manifest, 'reference_checks': checks,
              'locked_history_checks': history_checks,
              'source_reconciliation': source, 'plan': plan(1, history_policy), 'later_expansion_plan': plan(3, history_policy)}
    save(out / 'offline_report.json', report)
    save(out / 'references.json', references)
    save(out / 'run_plan.json', plan(1, history_policy))
    save(out / 'later_expansion_plan.json', plan(3, history_policy))
    return report


def compatible_identity(artifact):
    """Conservative grouping: no deployment/provenance differences are pooled.

    Only the repeat number and its expected sampling seed vary within a group.
    Unknown identity additions also separate groups, rather than silently
    assuming that a future control/version field is scientifically irrelevant.
    """
    identity = dict(artifact['identity'])
    repeat = identity.pop('repeat')
    seed = identity.pop('repeat_seed_label')
    if type(repeat) is not int or repeat not in (1, 2, 3) or type(seed) is not int or seed != repeat - 1:
        raise ValueError('invalid repeat identity; allowed repeat labels are 0/1/2')
    stage_settings = {cap: dict(values) for cap, values in identity['stage_settings'].items()}
    for values in stage_settings.values():
        if 'seed' in values:
            if type(values['seed']) is not int or values['seed'] != seed:
                raise ValueError('request seed disagrees with repeat identity')
            del values['seed']
    identity['stage_settings'] = stage_settings
    return {'identity': identity, 'synthetic': artifact['synthetic'],
            'actual_deployment_sha256': runner.canonical(artifact['deployment'])}


def summarize(paths):
    """Read saved scores, never rescue, reparse or rescore model answers."""
    artifacts = []
    for path in paths:
        candidates = sorted(Path(path).glob('*.json')) if Path(path).is_dir() else [Path(path)]
        artifacts.extend(json.loads(p.read_text()) for p in candidates if p.name != 'summary.json')
    if not artifacts:
        raise ValueError('empty input is not a result')
    if len({a['run_id'] for a in artifacts}) != len(artifacts):
        raise ValueError('duplicate run input')
    groups, identities, repeats, details = {}, {}, {}, []
    for a in artifacts:
        if a['identity']['protocol'] != design.PROTOCOL:
            raise ValueError('wrong protocol')
        compatibility = compatible_identity(a)
        key = (f"{a['identity']['graph_seed']}/{a['identity']['condition']}/{a['identity']['profile']}/"
               + runner.canonical(compatibility))
        repeat = a['identity']['repeat']
        if repeat in repeats.setdefault(key, set()):
            raise ValueError('duplicate repeat identity in compatible group, regardless of run ID')
        repeats[key].add(repeat)
        identities[key] = compatibility
        audit = runner.audit_artifact(a)
        included = a['state'] == 'completed' and bool(audit) and all(audit.values())
        disposition = ('included' if included else 'quarantined_failed_operational_audit'
                       if a['state'] == 'completed' else 'incomplete_operational_attempt')
        groups.setdefault(key, []).append((a, included))
        details.append({'run_id': a['run_id'], 'state': a['state'], 'group': key,
                        'operational_audit': audit, 'disposition': disposition,
                        'included_in_scientific_scores': included,
                        'scores': a.get('scores') if included else None,
                        'description_score': 'not_scored_by_design' if a['identity']['condition'] == 'model_first' else 'not_applicable',
                        'stages': {k: {f: t.get(f) for f in ('history_policy', 'conversation', 'provider_usage', 'provider_finish_reason', 'cost', 'elapsed_s')}
                                   for k, t in a['turns'].items()}})
    summary = {}
    for key, rows in groups.items():
        completed = [a for a, included in rows if included]
        if any('scores' not in a or a['scores'].get('scorer') != design.SCORER for a in completed):
            raise ValueError('missing or incompatible saved scores')
        group = {'compatibility': identities[key], 'attempted': len(rows), 'completed': len(completed),
                 'declared_completed': sum(a['state'] == 'completed' for a, _ in rows),
                 'quarantined_run_ids': [a['run_id'] for a, included in rows if a['state'] == 'completed' and not included],
                 'incomplete_run_ids': [a['run_id'] for a, _ in rows if a['state'] != 'completed'],
                 'periods': {}, 'preservation': {}}
        for p in ('A', 'B'):
            scores = [a['scores']['periods'][p] for a in completed]
            n = len(scores)
            # Incomplete operational runs are explicit, not model-scoring results.
            entry = {'n_completed_conversations': n,
                     'task_well_formed': design.fraction(sum(s['task_parsed']['well_formed'] for s in scores), n),
                     'readout_well_formed': design.fraction(sum(s['readout_parsed']['well_formed'] for s in scores), n)}
            for metric in ('transition_exact', 'joint_exact', 'valid_rows', 'destination_accuracy_conditional'):
                entry[metric] = design.fraction(sum(s['beliefs'][metric]['numerator'] for s in scores),
                                                sum(s['beliefs'][metric]['denominator'] for s in scores))
            errors = [s['beliefs']['p_mae_truth_conditional'] for s in scores]
            count = sum(e['n'] for e in errors)
            entry['p_mae_truth_conditional'] = {'n': count, 'value': sum(e['sum'] for e in errors) / count if count else None}
            for kind in ('anchor', 'sampled'):
                routes = [r for s in scores for r in s['routes'].values() if r['query']['kind'] == kind]
                reachable = [r for r in routes if r['oracle_reachable']]
                valid = [r for r in reachable if r['valid']]
                entry[kind] = {'solution_correct': design.fraction(sum(r['solution_correct'] for r in routes), len(routes)),
                               'reachability_correct': design.fraction(sum(r['reachability_correct'] for r in routes), len(routes)),
                               'valid_finite_route': design.fraction(len(valid), len(reachable)),
                               'optimal_finite_route': design.fraction(sum(r['optimal'] for r in reachable), len(reachable)),
                               'regret_valid_only': {'n': len(valid), 'value': sum(r['regret'] for r in valid) / len(valid) if valid else None}}
            if p == 'B':
                for metric in ('detection_correct', 'localization_correct'):
                    entry[metric] = design.fraction(sum(s[metric] for s in scores), n)
            group['periods'][p] = entry
        for basis in ('self', 'truth'):
            ps = [a['scores']['preservation'][basis] for a in completed]
            group['preservation'][basis] = {
                'all_controls': design.fraction(sum(p['all_controls']['numerator'] for p in ps), len(ps) * 4),
                'conditional': design.fraction(sum(p['conditional']['numerator'] for p in ps),
                                               sum(p['conditional']['denominator'] for p in ps)),
                'all_four_correct': design.fraction(sum(p['all_four_correct'] for p in ps), len(ps))}
        summary[key] = group
    return {'protocol': design.PROTOCOL, 'groups': summary, 'runs': details,
            'interpretation': 'Repeated outputs within each graph; no independence or significance claim. Free-form descriptions are saved, not scored by design.'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', required=True)
    ap.add_argument('--history-policy', choices=design.HISTORY_POLICIES, default=design.HISTORY_POLICY,
                    help='policy for previews and plans; saved-score reports use recorded identities')
    ap.add_argument('--summarize', nargs='+')
    a = ap.parse_args()
    if a.summarize:
        save(a.out, summarize(a.summarize))
    else:
        report = generate(a.out, a.history_policy)
        print(json.dumps({'prompt_files_exact': report['prompt_files_exact'], 'model_calls': 0, 'deployment_ready': False}))


if __name__ == '__main__':
    main()

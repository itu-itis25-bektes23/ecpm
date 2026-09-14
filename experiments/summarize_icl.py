"""Offline summaries of compact, previously scored ICL records.

python3 experiments/summarize_icl.py runs/icl/final/results.json --output runs/icl/final/results.md

No model, parser or scorer imports. The saved component scores are inputs,
not recalculated results. Malformed components remain in failure denominators.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


LEVELS = ('empirical_table', 'explained_logs', 'minimal_logs')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def fraction(numerator, denominator):
    return {'numerator': numerator, 'denominator': denominator,
            'rate': numerator / denominator if denominator else None}


def mean(values):
    return {'value': sum(values) / len(values) if values else None,
            'n': len(values)}


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()



def score_hash(value):
    return digest(json.dumps(value, sort_keys=True, separators=(',', ':')))


def load(path):
    data = json.loads(path.read_text())
    require(data['format'] == 'icl_saved_scores_v1', 'format guard')
    runs = data['runs']
    require(runs, 'input guard: no saved runs')
    expected = {(mode, level, repeat, repeat - 1)
                for mode in ('off', 'on') for level in LEVELS for repeat in (1, 2, 3)}
    require(len(runs) == 18 and
            {(r['condition'], r['level'], r['repeat'], r['sampling_seed']) for r in runs} == expected,
            'matrix guard: need all 18 runs with matched seeds')
    require(len({r['run_id'] for r in runs}) == 18, 'run-id guard')
    for r in runs:
        require(set(r['turns']) == {'A', 'B'}, 'two-turn guard')
        require(len(r['source_artifact_sha256']) == 64, 'source hash guard')
        for name, t in r['turns'].items():
            require(score_hash(t['scored']) == t['source_scores_sha256'], 'saved-score hash guard')
            require(type(t['parsed']['well_formed']) is bool, 'well-formed field guard')
            b = t['scored']['beliefs']
            require(b['n_queried'] == 5 and b['n_scored'] == len(b.get('per_pair', [])), 'belief-count guard')
            if name == 'B':
                require(t['previous_response_sha256'] == r['turns']['A']['response_sha256'], 'turn-link guard')
                require(t['scored']['control_preservation']['n_controls'] == 4, 'control-count guard')
    return data


def check_examples(data, directory):
    paths = sorted(directory.glob('*.json'))
    require(len(paths) == 6, 'example-count guard')
    seen = set()
    by_id = {r['run_id']: r for r in data['runs']}
    for path in paths:
        e = json.loads(path.read_text())
        r = by_id[e['run_id']]
        require(e['repeat'] == r['repeat'] == 1 and e['sampling_seed'] == r['sampling_seed'] == 0,
                'example-selection guard')
        require(e['source_artifact_sha256'] == r['source_artifact_sha256'], 'example-source guard')
        require(e['archive_member'] == r['archive_member'], 'example archive guard')
        require(e['condition'] == r['condition'] and e['level'] == r['level'], 'example identity guard')
        require([(m['turn'], m['role']) for m in e['messages']] ==
                [('A', 'user'), ('A', 'assistant'), ('B', 'user'), ('B', 'assistant')], 'example-order guard')
        for m in e['messages']:
            field = 'prompt_sha256' if m['role'] == 'user' else 'response_sha256'
            require(digest(m['content']) == m['sha256'] == r['turns'][m['turn']][field], 'example-text hash guard')
        seen.add((e['condition'], e['level']))
    require(seen == {(m, l) for m in ('off', 'on') for l in LEVELS}, 'example coverage guard')


def summarize(runs):
    """Reuse the historical audit formulas, with observed denominators explicit."""
    n = len(runs)
    turns = [t for d in runs for t in d['turns'].values()]
    out = {
        'runs_observed': n, 'runs_expected': n,
        'well_formed_all_responses': fraction(sum(t['parsed']['well_formed'] for t in turns), 2 * n),
        'full_parse_status_counts': dict(Counter(t['parsed']['status'] for t in turns)),
        'component_parse_counts': {k: dict(Counter(t['parsed'].get(k, {}).get('status', 'N/A') for t in turns))
                                   for k in ('beliefs', 'route', 'detection', 'localization')},
        'turns': {},
    }
    for turn in ('A', 'B'):
        ts = [d['turns'][turn] for d in runs]
        beliefs = [t['scored']['beliefs'] for t in ts]
        routes = [t['scored']['route'] for t in ts]
        pairs = [p for b in beliefs for p in b.get('per_pair', [])]
        dest_n = sum(b['n_destination_scored'] for b in beliefs)
        dest_correct = sum(p.get('destination_ok') is True for p in pairs if p.get('true_available'))
        valid = [r for r in routes if r['status'] == 'valid_finite']
        s = {
            'belief_exact_all_queried': fraction(sum(p['correct'] is True for p in pairs), 5 * n),
            'belief_scored_n': sum(b['n_scored'] for b in beliefs),
            'destination_scored': fraction(dest_correct, dest_n),
            'destination_all_queried_success': fraction(dest_correct, 5 * n),
            'valid_route_all_runs': fraction(len(valid), n),
            'optimal_route_all_runs': fraction(sum(r['is_optimal'] is True for r in routes), n),
            'route_status_counts': dict(Counter(r['status'] for r in routes)),
            'route_belief_diagnostic_counts': dict(Counter(t['scored']['route_belief_diagnostic']['status'] for t in ts)),
            'mean_regret_valid': mean([r['regret'] for r in valid]),
            'mean_cost_valid': mean([r['expected_cost'] for r in valid]),
        }
        for kind in ('visible', 'truth'):
            count = sum(b['n_p_' + kind + '_scored'] for b in beliefs)
            total = sum((b['p_mae_' + kind] or 0) * b['n_p_' + kind + '_scored'] for b in beliefs)
            s['p_mae_' + kind] = {'value': total / count if count else None, 'n': count}
        out['turns'][turn] = s
    post = [d['turns']['B']['scored'] for d in runs]
    out['detection_all_runs'] = fraction(sum(s['detection_localization']['detection_correct'] is True for s in post), n)
    loc = [s['detection_localization'] for s in post if s['detection_localization']['localization_applicable']]
    out['localization_all_runs'] = fraction(sum(s['localization_correct'] is True for s in loc), len(loc))
    pres = [s['control_preservation'] for s in post]
    eligible = [p for p in pres if p['status'] == 'ok' and p.get('per_pair')]
    out['preservation'] = {'scored_runs_n': len(eligible), 'all_runs_n': n,
                           'all_four_correct_all_runs': fraction(sum(p['all_four_controls_correct'] for p in pres), n)}
    for key in ('mean_control_preservation', 'truth_mean_control_preservation'):
        out['preservation'][key + '_all_runs'] = dict(mean([p[key] for p in pres]), unscored_counted_as_zero=True)
        out['preservation'][key + '_conditional'] = mean([p[key] for p in eligible])
    out['completion_tokens'] = sum(t['provider_usage']['completion_tokens'] for t in turns)
    out['reasoning_tokens'] = sum(t['provider_usage']['completion_tokens_details']['reasoning_tokens'] for t in turns)
    out['unique_response_hashes'] = len({t['response_sha256'] for t in turns})
    return out



def report(path):
    data = load(path)
    result = {'experiment_commit': data['experiment_commit'], 'scope': data['scope'], 'conditions': {}}
    for mode in ('off', 'on'):
        runs = sorted((r for r in data['runs'] if r['condition'] == mode),
                      key=lambda r: (LEVELS.index(r['level']), r['repeat']))
        result['conditions'][mode] = {
            'per_level': {level: summarize([r for r in runs if r['level'] == level]) for level in LEVELS},
            'pooled': summarize(runs)}
    require(score_hash(result['conditions']) == data['expected_aggregates_sha256'],
            'saved-aggregate agreement guard')
    return result


def markdown(result):
    f = lambda x: f"{x['numerator']}/{x['denominator']}" if x['denominator'] else 'N/A (n=0)'
    m = lambda x: f"{x['value']:.4f} (n={x['n']})" if x['n'] else 'N/A (n=0)'

    def cells(s):
        return [f(s['well_formed_all_responses']),
                *(f(s['turns'][t]['belief_exact_all_queried']) for t in ('A', 'B')),
                *(f(s['turns'][t]['optimal_route_all_runs']) for t in ('A', 'B')),
                f(s['detection_all_runs']), f(s['localization_all_runs']),
                m(s['preservation']['mean_control_preservation_all_runs']),
                f(s['preservation']['all_four_correct_all_runs'])]

    headers = ['Well formed', 'Beliefs A', 'Beliefs B', 'Route-finding A',
               'Route-finding B', 'Detection', 'Localization',
               'Preservation mean', 'All-four-correct']
    divider = '|---|' + '---:|' * len(headers)
    lines = ['# Final ICL results', '', 'Generated by `experiments/summarize_icl.py` from saved scores.', '',
             'Experiment commit: `' + result['experiment_commit'] + '`.', '', result['scope'], '',
             'Fractions show successes / all relevant responses or queried pairs, including malformed components as failures. Beliefs are exact pair scores. Route-finding reports optimal routes / all runs. Preservation mean measures unchanged-control self-consistency across all runs (unscored = 0); all-four-correct is runs preserving all four controls / all runs. `route_unresolvable` is diagnostic only.', '',
             '## Assistance levels: OFF → ON', '',
             '| Assistance level | ' + ' | '.join(headers) + ' |', divider]
    for level in LEVELS:
        off, on = (cells(result['conditions'][mode]['per_level'][level]) for mode in ('off', 'on'))
        lines += ['| ' + level + ' | ' + ' | '.join(a + ' → ' + b for a, b in zip(off, on)) + ' |']
    lines += ['', '## Pooled OFF/ON', '', '| Condition | ' + ' | '.join(headers) + ' |', divider]
    for mode in ('off', 'on'):
        lines += ['| ' + mode.upper() + ' | ' + ' | '.join(cells(result['conditions'][mode]['pooled'])) + ' |']
    lines += ['', 'See [results.json](results.json) for all machine-readable fields, including conditional destination accuracy, visible/truth MAE, preservation with scored counts, route validity, costs and regret. The [archive index](../README.md#archived-evidence) identifies the saved detailed report with exact beliefs/routes, parsing errors and operational checks; [six fixed examples](../examples/) show both turns.', '',
              'Earlier runs remain development evidence. The original strict 3072-token FAIL is not relabeled by this separate 8192-token comparison.']
    return '\n'.join(lines).rstrip() + '\n'



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, help='Write Markdown tables; default: stdout')
    parser.add_argument('--json', type=Path, help='Optional derived aggregates, separate from input')
    args = parser.parse_args()
    try:
        for path in (args.output, args.json):
            require(path is None or path.resolve() != args.input.resolve(), 'input overwrite guard')
        result = report(args.input)
        if args.output:
            args.output.write_text(markdown(result))
        else:
            print(markdown(result), end='')
        if args.json:
            args.json.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f'ICL report failed: {exc}\n')


if __name__ == '__main__':
    main()

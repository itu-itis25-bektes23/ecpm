"""Five-arm passive ICL design with explicit histories and audited scores."""

import copy
import hashlib
import itertools
import json
import math
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

import ecpm_baseline as baseline
import ecpm_parser as parser
import icl_graph as controls
import icl_model_first as pilot_design
import icl_model_first_runner as runner
import resource_mdp as environment
import run_pilot as pilot
import icl_preparation as preparation

PROTOCOL = 'icl_expanded_v2'
SCORER = 'icl_expanded_rows_v3'
PREPARATION_POLICY = 'five_arms_scoped_preparation_v3'
SCHEDULE = 'prepare_task_post_task_report_v2'
STAGES = ('prepare', 'task', 'readout')
CAP = 4096
NEW_CAP = 16384
HISTORICAL_4K_BASE = '05df38907307ec290ede76998f50a6fb1318b4fd'


def output_allowance(value):
    if type(value) is not int or value not in (CAP, NEW_CAP):
        raise ValueError('expanded output allowance must be 4096 (historical) or 16384')
    return value


def artifact_allowance(identity):
    caps = list(identity['stage_settings'])
    if len(caps) != 1 or caps[0] not in ('4096', '16384'):
        raise ValueError('one explicit expanded output allowance required')
    return output_allowance(int(caps[0]))
PREP_WORDS = 250
SUPPORTED_K = (10,)
QUERY_POLICY = 'a_only_balanced_queries_v2'
SEEDS = (8, 13, 25, 0, 1)
SCENARIOS = ('no_change', 'irrelevant', 'silent_break', 'hard_removal', 'redirect', 'degradation')
ARMS = ('model_first', 'task_only', 'spontaneous', 'graph_given', 'baseline_task')
HISTORY_POLICIES = pilot_design.HISTORY_POLICIES
SOURCE_BASE = '75a0c73569e3f4c7003c4d29d4e4d0e343e4e017'
canonical = runner.canonical
parse_task = pilot_design.parse_task
parse_readout = pilot_design.parse_readout
queries = pilot_design.queries
fraction = pilot_design.fraction

SYSTEM = {
    'det': '''You will answer questions about a system with states and actions in Period A
and then Period B. The system is deterministic within each period. Every
available action has one destination and succeeds either always or never.
A successful attempt moves to its destination; an unsuccessful attempt stays
at the current state. Each attempt costs 1, and a failed action can be retried.
The current action menu determines availability; availability does not mean
success. An action with success probability 0 can remain available and still
have a destination. Period B may or may not differ from Period A.
Use only the supplied information and follow each message's instructions.''',
    'sto': '''You will answer questions about a system with states and actions in Period A
and then Period B. Within each period, every available action has one
destination and a fixed success probability. A successful attempt moves to
that destination; an unsuccessful attempt stays at the current state.
Attempts are sampled independently. Each attempt costs 1, and a failed action
can be retried. The current action menu determines availability; availability
does not mean success. An action with success probability 0 can remain
available and still have a destination. Period B may or may not differ from A.
Observed success fractions estimate the probabilities; different fractions
alone do not establish a change, and no observed successes do not prove that
the underlying probability is zero. Use only the supplied information and
follow each message's instructions.'''}
OBSERVATIONS = '''Each observation is [current_state, action, observed_next_state].
Observations belong to the named period. Available means listed in the current
action menu. Destination means the state an action reaches when it succeeds.
A failed attempt leaves the current state unchanged; it does not by itself
mean that the action lost its destination or now leads to the current state.
An action can remain available even when it never succeeds.
If the current-period specification is supplied, its stated transitions apply.
For unavailable actions, report destination=null and p_success=null.'''

NEUTRAL_PREP = '''Restate the task rules and output format in your own words.
Do not interpret the observations, describe specific transitions, or solve
the task questions. Aim for approximately 250 words.'''
MODEL_PREP = '''Construct a model of how this system behaves from the supplied
evidence. Use whatever representation you find useful. Describe the current
system so that your model can be used to answer questions about it later.
Aim for approximately 250 words.'''
SPONTANEOUS_PREP = '''Write any notes you find useful for answering the task
questions later. Aim for approximately 250 words.'''


def stages(arm):
    if arm not in ARMS:
        raise ValueError('unknown arm')
    return ('task', 'readout') if arm == 'baseline_task' else STAGES


def task_guide(period, preparation=False):
    text = '''Task rules and output format:
Find the route with the smallest expected number of attempts for each requested
start and goal. Return only a JSON object with a routes list. Each entry has
query_id, reachable (a boolean), and steps (a list of state/action objects).
Stop at the goal: do not add a final goal item. For an unreachable goal, return
reachable=false and steps=[]. The specific queries will be supplied with the
task questions.'''
    if period == 'B':
        text += '''\nAlso report changed (a boolean) and changed_pair (null, or a state/action
object identifying the changed pair). Compare the underlying systems across
periods; different sampled fractions alone do not establish a change.'''
    if preparation:
        text = text.replace('Task rules and output format:',
            'Task rules and output format:\nFor later task-answer turns only, not this preparation turn:')
        text = text.replace('Return only a JSON object with a routes list.',
            'On those later task-answer turns, return only a JSON object with a routes list.')
        text = text.replace('Also report changed',
            'On the later task-answer turn, also report changed')
    return text


def system(world):
    return SYSTEM[world['mode']]


def configurations():
    return [(seed, mode, scenario) for seed in SEEDS for mode in SYSTEM
            for scenario in SCENARIOS if not (mode == 'det' and scenario == 'degradation')]


def _base_world(seed, mode, scenario, k=10):
    if type(seed) is not int or (seed, mode, scenario) not in configurations():
        raise ValueError('unsupported world; deterministic degradation is undefined')
    if type(k) is not int or k not in SUPPORTED_K:
        raise ValueError('the verified main visible budget is K=10')
    sc = dict(pilot.SCENARIO_DEFAULTS, seed=seed, condition=scenario, matched=True,
              k=k, budget=k, evidence_seed=0, rendering='F2_shuffled')
    record = pilot.build_record(sc, mode == 'det')
    visible = environment.prompt_view(record, budget_per_pair=k, budget_seed=0)
    keys = sorted({(s, a) for p in ('pre', 'post')
                   for s, actions in visible['legal_actions_' + p].items() for a in actions})
    world = {'seed': seed, 'mode': mode, 'scenario': scenario, 'k': k, 'budget': k,
             'evidence_seed': 0, 'rendering': 'F2_shuffled', 'visible': visible}
    for period, suffix in (('A', 'pre'), ('B', 'post')):
        truth = {(r['from'], r['action']): r for r in record['world_' + suffix]['edges']}
        world[period] = {'period': period, 'nodes': visible['nodes'], 'start': visible['start'],
            'goal': visible['goal'], 'menu': {s: visible['legal_actions_' + suffix].get(s, []) for s in visible['nodes']},
            'rows': pilot.raw_visible_rows(visible, suffix), 'required_pairs': [list(k) for k in keys],
            'graph': [dict(node=s, action=a, available=(s, a) in truth,
                           destination=truth[(s, a)]['to'] if (s, a) in truth else None,
                           p_success=truth[(s, a)]['p'] if (s, a) in truth else None) for s, a in keys]}
    target = pilot.protocol_target_pair(record, sc)
    world['target'] = list(target)  # Evaluator only, including no-change counterfactual.
    world['controls'] = [q for q in pilot.queried_pairs_for_icl(record, sc)
                         if (q['node'], q['action']) != target]
    world['true_changes'] = [list(k) for k, a, b in zip(keys, world['A']['graph'], world['B']['graph']) if a != b]
    assert len(world['controls']) == 4
    assert all([c['node'], c['action']] not in world['true_changes'] for c in world['controls'])
    return world


@lru_cache(maxsize=5)
def query_design(seed):
    """Fixed across modes/scenarios/K. Uses only A worlds and planned pair IDs."""
    views = []
    for mode, scenario in itertools.product(SYSTEM, ('silent_break', 'irrelevant')):
        w = _base_world(seed, mode, scenario)
        a, target = w['A'], tuple(w['target'])
        without = copy.deepcopy(a['graph'])
        for row in without:
            if (row['node'], row['action']) == target:
                row['p_success'] = 0
        flags = {}
        for s, g in itertools.permutations(a['nodes'], 2):
            route = pilot_design.shortest(a['graph'], s, g)
            if not route['reachable']:
                continue
            alternate = pilot_design.shortest(without, s, g)
            flags[(s, g)] = (
                any((step['state'], step['action']) == target for step in route['steps']),
                not alternate['reachable'] or alternate['cost'] > route['cost'] + 1e-9)
        views.append(flags)
    anchor = a['start'], a['goal']
    candidates = sorted((p for p in views[0] if p != anchor), key=lambda p:
        pilot_design.digest(f'{QUERY_POLICY}|{seed}|{p}'))
    best, score = None, -1
    for sampled in itertools.combinations(candidates, 3):
        chosen = (anchor,) + sampled
        # At least two canonical A optima use each planned changed pair;
        # at least one avoids it. Alternate tied optima remain valid answers.
        if not all(2 <= sum(v[p][0] for p in chosen) <= 3 for v in views):
            continue
        needed = sum(sum(v[p][1] for p in chosen) for v in views)
        if needed > score:
            best, score = chosen, needed
    if best is None:
        raise ValueError('cannot satisfy the A-only route-query design')
    return tuple(best)


def build_world(seed, mode, scenario, k=10):
    world = _base_world(seed, mode, scenario, k)
    world['route_queries'] = [dict(query_id=f'q{i}', start=s, goal=g,
        kind='anchor' if i == 0 else 'sampled') for i, (s, g) in enumerate(query_design(seed))]
    world['query_policy'] = QUERY_POLICY
    target = tuple(world['target'])
    world['query_design'] = {}
    without = copy.deepcopy(world['A']['graph'])
    for row in without:
        if (row['node'], row['action']) == target:
            row['p_success'] = 0
    for q in world['route_queries']:
        optimum = pilot_design.shortest(world['A']['graph'], q['start'], q['goal'])
        alternate = pilot_design.shortest(without, q['start'], q['goal'])
        world['query_design'][q['query_id']] = dict(
            canonical_A_optimum_uses_target=any((s['state'], s['action']) == target for s in optimum['steps']),
            all_A_optima_use_target=not alternate['reachable'] or alternate['cost'] > optimum['cost'] + 1e-9)
    return world


def graph_text(view):
    lines = ['Current-period graph:', 'state | action | available | destination | p_success']
    for r in view['graph']:
        lines.append(f"{r['node']} | {r['action']} | {str(r['available']).lower()} | "
                     f"{r['destination'] if r['destination'] is not None else 'null'} | "
                     + (repr(r['p_success']).removesuffix('.0') if r['p_success'] is not None else 'null'))
    return '\n'.join(lines)


def prompts(world, period, arm):
    if arm not in ARMS or period not in ('A', 'B'):
        raise ValueError('unknown arm/period')
    v = world[period]
    lines = [OBSERVATIONS, 'Period ' + period, 'States: ' + ', '.join(v['nodes']), 'Current action menu:']
    lines += [s + ': ' + (', '.join(v['menu'][s]) or '(no actions)') for s in sorted(v['menu'])]
    if arm == 'graph_given':
        lines.append(graph_text(v))
    lines += [f'Shuffled single-step observations, Period {period}:', *v['rows']]
    instruction = MODEL_PREP if arm == 'model_first' else SPONTANEOUS_PREP if arm == 'spontaneous' else NEUTRAL_PREP
    # Supply only the required identifiers here, never their evaluator roles.
    report_view = copy.deepcopy(world)
    report_view[period]['menu'] = {s: [a for n, a in v['required_pairs'] if n == s] for s in v['nodes']}
    report = pilot_design.readout(report_view, period)
    if period == 'B':
        report = report.replace('or probability differs from Period A; otherwise false.',
            'or underlying success probability differs from Period A; otherwise false.\n'
            'Different sampled estimates alone do not establish an underlying change.')
    evidence = '\n'.join(lines) + '\n\n' + task_guide(period, preparation=arm != 'baseline_task')
    task = pilot_design.task(world, period)
    if arm == 'baseline_task':
        return {'task': evidence + '\n\n' + task, 'readout': report}
    return {'prepare': evidence + '\n\nCurrent turn: preparation, not a task answer.\n'
            'Task-answer JSON is not required on this turn.\n' + instruction,
            'task': task, 'readout': report}


def schedule(world, arm, answers, history_policy=pilot_design.HISTORY_POLICY, output_tokens=CAP):
    flow = runner.requests(world, arm, history_policy, sys.modules[__name__], output_allowance(output_tokens))
    calls, call = [], next(flow)
    while True:
        calls.append(call)
        try:
            call = flow.send(answers[call['id']])
        except StopIteration:
            return calls


def estimates(view, earlier=None):
    """Only visible rows/menu/identifiers, not graph probabilities or target."""
    visible = {k: view[k] for k in ('menu', 'rows', 'required_pairs')}
    old = {(r['node'], r['action']): r for r in earlier or []}
    stats = pilot.visible_transition_stats(visible['rows'], visible['menu'],
        {s: [a for n, a in visible['required_pairs'] if n == s] for s in visible['menu']})
    rows = []
    for s, a in visible['required_pairs']:
        observed = stats[(s, a)]
        destinations = sorted(n for n in observed['next_state_counts'] if n != s)
        if len(destinations) > 1:
            raise ValueError('visible action has multiple successful destinations')
        rows.append(dict(node=s, action=a, available=observed['available'],
            destination=(destinations[0] if destinations else old.get((s, a), {}).get('destination')) if observed['available'] else None,
            p_success=observed['p_success']))
    return rows


def answers_from_rows(questions, periods, changes, label):
    result = {}
    for period in ('A', 'B'):
        rows = periods[period]
        task = {'routes': [{'query_id': q['query_id'], **{k: v for k, v in pilot_design.shortest(
                rows, q['start'], q['goal']).items() if k != 'cost'}} for q in questions]}
        pairs = [{'state': r['node'], **{k: v for k, v in r.items() if k != 'node'}} for r in rows]
        if period == 'B':
            change = changes[0] if changes else None
            task.update(changed=bool(changes), changed_pair=None if change is None else {'state': change[0], 'action': change[1]})
            for r in pairs:
                r['changed'] = (r['state'], r['action']) in set(map(tuple, changes))
        result[period + '_prepare'] = label + '\n' + json.dumps(rows)
        result[period + '_task'] = json.dumps(task)
        result[period + '_readout'] = json.dumps({'pairs': pairs})
    return result


def oracle_answers(world):
    return answers_from_rows(queries(world), {p: world[p]['graph'] for p in ('A', 'B')}, world['true_changes'],
                             'SYNTHETIC ORACLE REFERENCE; USES EVALUATOR TRUTH; NOT MODEL OUTPUT')


def evidence_reference(visible, questions):
    """Only prompt-visible data/questions. Published detector is not redirect-aware."""
    result = baseline.run_baseline(copy.deepcopy(visible))
    if result['status'] != 'ok':
        raise ValueError('evidence baseline could not run')
    keys = sorted({(s, a) for p in ('pre', 'post') for s, actions in visible['legal_actions_' + p].items() for a in actions})
    views = {p: {'menu': visible['legal_actions_' + suffix], 'rows': pilot.raw_visible_rows(visible, suffix),
                 'required_pairs': keys} for p, suffix in (('A', 'pre'), ('B', 'post'))}
    a = estimates(views['A'])
    b = estimates(views['B'], a)
    changes = [result['localization']] if result['detection'] and result['localization'] is not None else []
    return {'identity': 'published_ecpm_baseline_rates_v1_empirical_planning_v1',
            'baseline': result, 'answers': answers_from_rows(questions, {'A': a, 'B': b}, changes,
                'SYNTHETIC VISIBLE-EVIDENCE REFERENCE; NOT ORACLE OR MODEL OUTPUT')}


def close_transition(a, b, tolerance):
    return (a['available'] == b['available'] and a['destination'] == b['destination']
            and ((a['p_success'] is None and b['p_success'] is None) or
                 (a['p_success'] is not None and b['p_success'] is not None
                  and abs(a['p_success'] - b['p_success']) <= tolerance + parser.EPS)))


def preservation_tolerance(a, b, world, tolerance):
    result = {}
    truth = {pilot_design.pair_id((r['node'], r['action'])): r for r in world['B']['graph']}
    for name in ('self', 'truth'):
        values = []
        for c in world['controls']:
            key = pilot_design.pair_id((c['node'], c['action']))
            x, y = a['rows'][key], b['rows'][key]
            if y['transition_valid'] and y['changed_valid'] and (name == 'truth' or x['transition_valid']):
                values.append(not y['value']['changed'] and close_transition(
                    x['value'] if name == 'self' else truth[key], y['value'], tolerance))
        result[name] = {'all_controls': fraction(sum(values), len(world['controls'])),
                        'conditional': fraction(sum(values), len(values)),
                        'unscored': len(world['controls']) - len(values),
                        'all_four_correct': len(values) == 4 and all(values)}
    return result


def score_conversation(world, arm, turns):
    result = pilot_design.score_conversation(world, arm, turns)
    result['scorer'] = SCORER
    tolerance = parser.BELIEF_P_TOL_STOCHASTIC if world['mode'] == 'sto' else parser.BELIEF_P_TOL_DETERMINISTIC
    result['preparation'] = {p: preparation.score(turns[p + '_prepare']['raw_response'], world[p], tolerance)
        if arm != 'baseline_task' else {'status': 'not_applicable', 'scored': False} for p in ('A', 'B')}
    result['probability_tolerance'] = tolerance
    result['probability_comparison_epsilon'] = parser.EPS
    old_estimate = None
    for period in ('A', 'B'):
        s = result['periods'][period]
        truth = world[period]['graph']
        visible = estimates(world[period], old_estimate)
        old_estimate = visible
        n = len(world[period]['required_pairs'])
        available_ok, destination_ok, tolerant, joint, visible_errors = 0, 0, 0, 0, []
        for t, empirical in zip(truth, visible):
            key = pilot_design.pair_id((t['node'], t['action']))
            r = s['readout_parsed']['rows'][key]
            v = r['value'] or {}
            valid = r['transition_valid']
            available_ok += bool(valid and v['available'] == t['available'])
            destination_ok += bool(valid and t['available'] and v['destination'] == t['destination'])
            ok = bool(valid and close_transition(v, t, tolerance))
            tolerant += ok
            joint += ok and (period == 'A' or s['beliefs']['rows'][key]['changed_correct'])
            if valid and empirical['available'] and v['p_success'] is not None:
                visible_errors.append(abs(v['p_success'] - empirical['p_success']))
        s['beliefs'].update(availability_accuracy=fraction(available_ok, n),
            destination_accuracy_all=fraction(destination_ok, sum(t['available'] for t in truth)),
            transition_tolerance=fraction(tolerant, n), joint_tolerance=fraction(joint, n),
            p_mae_visible_conditional={'sum': sum(visible_errors), 'n': len(visible_errors),
                                      'value': sum(visible_errors) / len(visible_errors) if visible_errors else None})
    b = result['periods']['B']
    changed = bool(world['true_changes'])
    detection, loc = b['task_parsed']['detection'], b['task_parsed']['localization']
    b['detection_correct'] = detection['valid'] and detection['value'] == changed
    expected = world['true_changes'][0] if changed else None
    b['localization_correct'] = loc['valid'] and (loc['value'] is None if expected is None else
        loc['value'] is not None and [loc['value']['state'], loc['value']['action']] == expected)
    b['localization_changed_case'] = b['localization_correct'] if changed else None
    b['no_change_null_correct'] = b['localization_correct'] if not changed else None
    b['sensitivity'] = fraction(b['detection_correct'], 1) if changed else fraction(0, 0)
    b['specificity'] = fraction(b['detection_correct'], 1) if not changed else fraction(0, 0)
    result['preservation_tolerance'] = preservation_tolerance(result['periods']['A']['readout_parsed'],
        b['readout_parsed'], world, tolerance)
    result['updating'] = updating(result['periods'], world)
    return result


def updating(periods, world):
    """Task routes, not readout labels. Eligibility always comes from own A."""
    def route_value(parsed):
        value = parsed['value']
        return (value['reachable'], tuple((s['state'], s['action']) for s in value['steps']))

    records = {}
    changes = {tuple(p) for p in world['true_changes']}
    for q in queries(world):
        key = q['query_id']
        a = periods['A']['task_parsed']['routes'][key]
        b = periods['B']['task_parsed']['routes'][key]
        old = periods['A']['routes'][key]
        current = periods['B']['routes'][key]
        valid_a = old['valid']
        used = valid_a and any((s['state'], s['action']) in changes for s in a['value']['steps'])
        replay = pilot_design.grade_route(a, world['B']['graph'], q)
        replay_optimal = replay['optimal'] or replay['status'] == 'correct_no_route'
        necessary = bool(used and not replay_optimal)
        stable = bool(valid_a and old['optimal'] and replay_optimal)
        # Extra JSON fields remain format errors, but do not change the route.
        different = bool(a['valid'] and b['valid'] and route_value(a) != route_value(b))
        successful_b = current['optimal'] or current['status'] == 'correct_no_route'
        records[key] = dict(A_route_valid=valid_a, A_route_used_changed_pair=bool(used),
            A_route_still_optimal_in_B=bool(valid_a and replay_optimal),
            necessary_update_eligible=necessary, necessary_update_correct=necessary and different and successful_b,
            unnecessary_replan_eligible=stable, unnecessary_replan_scored=stable and b['valid'],
            route_changed=different if b['valid'] else None,
            unnecessary_replan=stable and different if b['valid'] else None,
            harmful_unnecessary_replan=stable and different and not successful_b if b['valid'] else None,
            B_solution_optimal=bool(successful_b))
    result = {'queries': records, 'eligible_A_routes': fraction(sum(r['A_route_valid'] for r in records.values()), len(records))}
    for metric, eligible, success in (
        ('necessary_update_rate', 'necessary_update_eligible', 'necessary_update_correct'),
        ('unnecessary_replan_rate', 'unnecessary_replan_scored', 'unnecessary_replan'),
        ('harmful_unnecessary_replan_rate', 'unnecessary_replan_scored', 'harmful_unnecessary_replan')):
        values = [r[success] for r in records.values() if r[eligible]]
        result[metric] = fraction(sum(values), len(values))
    return result


def source_hashes():
    root = Path(__file__).resolve().parent
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in
            ('icl_expanded.py', 'icl_model_first.py', 'icl_model_first_runner.py', 'icl_graph.py',
            'resource_mdp.py', 'ecpm_baseline.py', 'ecpm_parser.py', 'run_pilot.py', 'icl_preparation.py',
            'experiments/preview_icl_model_first.py')}


@lru_cache(maxsize=16)
def historical_source_hashes(commit):
    """Only Git-pinned source bytes, never a caller-supplied source attestation."""
    if not isinstance(commit, str) or len(commit) != 40 or any(c not in '0123456789abcdef' for c in commit):
        raise ValueError('full historical commit required')
    root = Path(__file__).resolve().parent
    return tuple((name, hashlib.sha256(subprocess.check_output(
        ['git', 'show', commit + ':' + name], cwd=root, stderr=subprocess.DEVNULL)).hexdigest()
        ) for name in source_hashes())


def identity(world, arm, repeat, args, wrapper):
    if arm not in ARMS or type(repeat) is not int or repeat not in range(1, 6) or args.reasoning_mode not in ('off', 'on'):
        raise ValueError('expanded: repeat 1 to 5 and explicit OFF/ON required')
    pilot_design.check_history_policy(args.history_policy)
    config = wrapper['deployment'] if wrapper else None
    cap = output_allowance(getattr(args, 'max_tokens', CAP))
    return {'protocol': PROTOCOL, 'preparation_policy': PREPARATION_POLICY, 'scorer': SCORER,
        'schedule': SCHEDULE, 'stages': list(stages(arm)), 'history_policy': args.history_policy,
        'preparation_word_target': None if arm == 'baseline_task' else PREP_WORDS,
        'query_policy': QUERY_POLICY,
        'source_base': SOURCE_BASE, 'source_sha256': source_hashes(),
        'implementation_commit': pilot.git_head(), 'implementation_dirty': pilot._git_dirty(),
        'graph_seed': world['seed'], 'mode': world['mode'], 'scenario': world['scenario'],
        'evidence_settings': {k: world[k] for k in ('k', 'budget', 'evidence_seed', 'rendering')},
        'world_sha256': canonical(world), 'queries': queries(world), 'condition': arm,
        'repeat': repeat, 'repeat_seed_label': repeat - 1, 'reasoning_mode': args.reasoning_mode,
        'provider': args.provider, 'profile': args.request_profile, 'model': args.model,
        'synthetic_reference': 'oracle_reference' if config is None else None,
        'sampling_seed_status': 'not_applied_synthetic' if config is None else 'supported' if config['seed_supported'] else 'unsupported',
        'deployment_sha256': canonical(wrapper),
        **({'context_admission': dict(config['context'])} if config and controls.estimated_context(config) else {}),
        'evidence_sha256': {p: canonical({k: world[p][k] for k in ('nodes', 'start', 'goal', 'menu', 'rows', 'required_pairs')}) for p in ('A', 'B')},
        'prompt_hashes': {'system': canonical(system(world)), **{p: canonical(prompts(world, p, arm)) for p in ('A', 'B')}},
        'stage_settings': {str(cap): runner.settings(args.request_profile, repeat - 1,
            bool(config and config['seed_supported']), cap, args.reasoning_mode, config)}}


def validate_config(wrapper, profile, mode, policy, output_tokens=CAP):
    cap = output_allowance(output_tokens)
    pilot_design.check_history_policy(policy)
    if set(wrapper) != {'deployment', 'expanded'}:
        raise ValueError('expanded deployment and stage/control evidence required')
    evidence = wrapper['expanded']
    required = {'protocol': PROTOCOL, 'preparation_policy': PREPARATION_POLICY,
                'history_policy': policy, 'reasoning_mode': mode, 'schedule': SCHEDULE,
                'output_allowances': [cap]}
    if any(evidence.get(k) != v for k, v in required.items()):
        raise ValueError('expanded mode/schedule/stage identity mismatch')
    # Reuse the strict deployment and fixed preflight validation, without claiming
    # that an operator evidence string itself proves effective semantics.
    controls.validate_deployment(wrapper['deployment'], profile, mode,
                                 preflight_output_tokens=NEW_CAP if cap == NEW_CAP else 8192)
    # Common non-mode checks also apply on ON, with no mutated evidence.
    if any(not isinstance(evidence.get(k), str) or not evidence[k].strip()
           for k in ('stage_limits_source', 'system_message_source', 'context_source')):
        raise ValueError('stage/system/context evidence required')
    config = wrapper['deployment']
    if profile == 'gemma_e4b' and not controls.local_context(config):
        raise ValueError('local actual-request tokenizer required')
    if profile in controls.EXPANDED_HOSTED_PROFILES and (any(config['pricing'].get(k) is None for k in
        ('input_per_million', 'output_per_million')) or not config['pricing'].get('source')):
        raise ValueError('verified hosted pricing required')
    controls.no_secrets(wrapper)
    return config


def audit_identity(a):
    i = a['identity']
    world = build_world(i['graph_seed'], i['mode'], i['scenario'], i['evidence_settings']['k'])
    args = SimpleNamespace(history_policy=i['history_policy'], reasoning_mode=i['reasoning_mode'],
        provider=i['provider'], request_profile=i['profile'], model=i['model'], max_tokens=artifact_allowance(i))
    expected = identity(world, i['condition'], i['repeat'], args, a['deployment'])
    if i['source_sha256'] != expected['source_sha256']:
        # Admit only the reviewed v3 4K implementation (including descendants
        # with byte-identical ICL sources), not arbitrary historical code.
        try:
            prior = dict(historical_source_hashes(i['implementation_commit']))
            if (artifact_allowance(i) != CAP or i['source_sha256'] != prior
                    or prior != dict(historical_source_hashes(HISTORICAL_4K_BASE))):
                return False
        except (ValueError, subprocess.CalledProcessError):
            return False
        expected['source_sha256'] = prior
    # Recorded commit/dirty state are provenance, not this auditing checkout.
    expected.update(implementation_commit=i['implementation_commit'], implementation_dirty=i['implementation_dirty'])
    dry = i['provider'] == 'dry-run'
    return (i == expected and world == a['world'] and a['identity_sha256'] == canonical(i)
            and a['synthetic'] == dry == (a['deployment'] is None)
            and (dry or (i['implementation_dirty'] is False and i['model'] == a['deployment']['deployment']['model'])))


def run_suite(sc, args, outdir):
    if (args.mode not in SYSTEM or args.pilot_type != 'passive' or args.repeats not in (1, 5)
            or args.sampling_seeds != list(range(args.repeats)) or args.max_tokens not in (CAP, NEW_CAP) or args.reasoning_mode not in ('off', 'on')
            or args.model_first_condition not in ARMS or args.request_profile not in controls.EXPANDED_MODELS
            or args.provider not in ('dry-run', 'openai')):
        raise ValueError('expanded: passive det/sto, one or five repeats, sequential seed labels, 4096/16384, explicit arm/profile/OFF or ON')
    if (args.graph_condition or args.off_reference or args.reasoning_control_json or args.reasoning_control_source
            or args.temperature != 0 or args.top_p is not None or args.top_k is not None
            or args.sampling_seed_support != 'auto' or sc['k'] not in SUPPORTED_K or sc['budget'] != sc['k']
            or sc['evidence_seed'] != 0 or sc['rendering'] != 'F2_shuffled' or not sc['matched']):
        raise ValueError('no expanded evidence or provider overrides')
    if Path(outdir).exists():
        raise ValueError('output exists; no overwrite/resume')
    world = build_world(sc['seed'], args.mode, sc['condition'], sc['k'])
    wrapper = None
    if args.provider == 'dry-run':
        if args.deployment_config:
            raise ValueError('synthetic runs cannot read private configs')
    else:
        if pilot._git_dirty() or not args.deployment_config:
            raise ValueError('clean commit and verified deployment required')
        wrapper = json.loads(Path(args.deployment_config).read_text())
        config = validate_config(wrapper, args.request_profile, args.reasoning_mode, args.history_policy, args.max_tokens)
        if args.model != config['model'] or args.base_url.rstrip('/') != config['endpoint'].rstrip('/'):
            raise ValueError('exact model/endpoint mismatch')
    cost_plan = runner.block_cost_plan(world, args.model_first_condition, wrapper, repeats=args.repeats,
                                      history_policy=args.history_policy, design_api=sys.modules[__name__], output_tokens=args.max_tokens)
    print(json.dumps({'prelaunch_cost_plan': cost_plan}))
    Path(outdir).mkdir(parents=True, exist_ok=False)
    try:
        for repeat in range(1, args.repeats + 1):
            runner.run_once(world, args.model_first_condition, repeat, args, wrapper, outdir, sys.modules[__name__])
    finally:
        summary = runner.write_summary(outdir, expected=args.repeats, design_api=sys.modules[__name__])
        summary['prelaunch_cost_plan'] = cost_plan
        pilot._write_json_atomic(str(Path(outdir) / 'summary.json'), summary)
    print(json.dumps(summary))
    return summary

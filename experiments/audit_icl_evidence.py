"""Evidence review of the Haiku 5.5 expanded-ICL runs: checks every run record against the claims of its NOTE.md.

    python experiments/audit_icl_evidence.py   (run from the folder that holds ecpm-haiku-runs/)

Read-only. Checks per run: completed, operational gate and audit flags, model, commit (clean), protocol,
profile, scorer, provider pinned to Anthropic with fallbacks off, the reasoning request of each mode, and per
answer: response model and provider, output cap 16,384, HTTP 200, finish reason, control violations and
reasoning tokens.
"""
import json, glob, collections, re
C = collections.Counter(); bad = collections.defaultdict(list); dates = collections.Counter()
cells = set(); reasoning_on = [0, 0]; off_nonzero = 0; ts = []
for d in sorted(glob.glob('ecpm-haiku-runs/*/')):
    s = json.load(open(d + 'summary.json', encoding='utf-8-sig'))
    files = glob.glob(d + 'icl_*.json')
    C['dirs'] += 1
    if len(files) != 1: bad['file_count'].append(d)
    a = json.load(open(files[0], encoding='utf-8-sig'))
    idn = a['identity']; eff = a['deployment']['deployment']['effective']
    C['completed' if s.get('completed_conversations') == s.get('expected_conversations') == 1 else 'incomplete'] += 1
    if not s.get('operational_gate_pass'): bad['gate'].append(d)
    if not all(a['operational_audit'].values()): bad['audit'].append(d)
    if a['state'] != 'completed': bad['state'].append(d)
    for k, v in [('model', 'anthropic/claude-haiku-5.5'), ('implementation_commit', '3be2c5905e062999c7ba05eb405776f2a173b833'),
                 ('implementation_dirty', False), ('protocol', 'icl_expanded_v2'), ('profile', 'haiku_openrouter'), ('scorer', 'icl_expanded_rows_v3')]:
        if idn.get(k) != v: bad['identity_' + k].append((d, idn.get(k)))
    if eff.get('provider_slug') != 'anthropic' or 'allow_fallbacks false' not in eff.get('routing_source', ''): bad['routing'].append(d)
    mode = idn['reasoning_mode']; C['mode_' + mode] += 1
    want = {'off': {'enabled': False, 'exclude': False}, 'on': {'effort': 'medium', 'exclude': False}}[mode]
    if eff['hosted_evidence']['request_fields'].get('reasoning') != want: bad['request_fields'].append(d)
    cells.add((mode, idn['mode'], idn['scenario'], idn['graph_seed'], idn['condition'], idn['history_policy']))
    for ev in a.get('persistence_events') or []:
        for v in (ev.values() if isinstance(ev, dict) else []):
            if isinstance(v, str) and re.match(r'20\d\d-\d\d-\d\dT', v): ts.append(v)
    for name, t in a['turns'].items():
        C['turns'] += 1
        if t.get('actual_response_model') != 'anthropic/claude-haiku-5.5': bad['resp_model'].append((d, name))
        if t.get('actual_response_provider') != 'Anthropic': bad['resp_provider'].append((d, name, t.get('actual_response_provider')))
        if t.get('max_output_tokens') != 16384: bad['cap'].append((d, name, t.get('max_output_tokens')))
        if t.get('http_status') != 200: bad['http'].append((d, name))
        fr = t.get('native_finish_reason'); C['finish_' + str(fr)] += 1
        cc = t.get('control_check') or {}
        if cc.get('control_violation'): bad['control_violation'].append((d, name))
        rt = cc.get('reasoning_tokens') or 0
        if mode == 'on': reasoning_on[0] += 1; reasoning_on[1] += rt > 0
        elif rt > 0: off_nonzero += 1
print('dirs', C['dirs'], '| completed', C['completed'], '| incomplete', C['incomplete'])
print('modes', C['mode_off'], C['mode_on'], '| distinct cells', len(cells), '| turns', C['turns'])
print('finish reasons', {k: v for k, v in C.items() if k.startswith('finish_')})
print('ON answers with reasoning', reasoning_on[1], 'of', reasoning_on[0], '| OFF answers with reasoning tokens', off_nonzero)
print('run timestamps', min(ts) if ts else None, 'to', max(ts) if ts else None, '| n', len(ts))
for k, v in bad.items(): print('PROBLEM', k, len(v), v[:3])
if not bad: print('No problems found in any check.')

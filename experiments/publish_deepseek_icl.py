"""Curate audited saved exports, never parse model answers or recompute scores.

Import once with --handoff DIRECTORY. Regenerate tables with --out DIRECTORY;
--check verifies committed tables and compressed data without private evidence.
"""
import argparse
import collections
import csv
from decimal import Decimal
import gzip
import hashlib
import io
import itertools
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / 'runs/results/icl/deepseek-deepseek-v4.1-flash'
COMMIT = '3dbaafcc71de094b7336e3a82d6fc0034e39be74'
ARCHIVE = 'https://drive.google.com/drive/folders/1AfRR4Mi-ykLaiLb47z6ARB_4Mz7yUwij'
STATUS = {'completed': 652, 'historical_completed': 3, 'failed_terminal': 5}
SCENARIOS = ('silent_break', 'hard_removal', 'redirect', 'irrelevant', 'no_change')
ARMS = ('model_first', 'task_only', 'graph_given')
HISTORIES = ('retained_reports_v2', 'separate_reports_post_task_v1')
REQUEST_FIELDS = (
    'cell_id run_id graph_seed mode scenario arm history_policy reasoning_mode stage '
    'attempt_ordinal cohort_kind source_commit max_output_tokens selected_stage_attempt '
    'conversation_status request_sha256 raw_response_sha256 http_status finish_reason '
    'native_finish_reason exception_type outcome model provider final_content_nonblank '
    'prompt_tokens completion_tokens total_tokens reasoning_tokens_reported cached_tokens '
    'reported_cost_usd upstream_cost_details usage_raw reasoning_acceptance failed_checks '
    'reservation_id reservation_status reserved_usd charged_to_this_batch elapsed_s'
).split()


def require(ok, guard):
    if not ok:
        raise ValueError(guard)


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def scan(text):
    require(not re.search(r'/Users/|/private/|<LOCAL_HOME>|[A-Z]:\\Users\\', text), 'private path')
    require(not re.search(r'\b(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]{16,}|Bearer\s+[A-Za-z0-9_.-]{20,}', text), 'credential pattern')
    require('\u2014' not in text, 'em dash')


def csv_value(value):
    return json.dumps(value, sort_keys=True) if value is None or isinstance(value, (dict, list, bool)) else str(value)


def csv_text(rows, fields=None):
    require(bool(rows), 'empty rows')
    f = io.StringIO(newline='')
    writer = csv.DictWriter(f, fieldnames=fields or list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows({k: csv_value(r.get(k)) for k in writer.fieldnames} for r in rows)
    return f.getvalue()


def gz_write(path, data):
    # Stable gzip headers, no local source filename or current timestamp.
    with path.open('wb') as f, gzip.GzipFile(fileobj=f, mode='wb', filename='', mtime=0) as z:
        z.write(data)


def rows(path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt', encoding='utf-8', newline='') as f:
        yield from csv.DictReader(f)


def number(value):
    if value in ('True', 'true'): return Decimal(1)
    if value in ('False', 'false'): return Decimal(0)
    return None if value in (None, '', 'null') else Decimal(str(value))


def validate_cells(cells):
    require(len(cells) == 660, 'coverage: expected 660 cells')
    require(collections.Counter(c['status'] for c in cells) == STATUS, 'status counts')
    require(len({c['cell_id'] for c in cells}) == 660, 'duplicate cell')
    require(len({c['run_id'] for c in cells}) == 660, 'duplicate conversation')
    dims = ('graph_seed', 'mode', 'scenario', 'arm', 'history_policy', 'reasoning_mode')
    actual = {tuple(str(c[k]) for k in dims) for c in cells}
    expected = {(str(seed), mode, scenario, arm, history, reasoning)
                for seed, mode, arm, history, reasoning in itertools.product(
                    (8, 13, 25, 0, 1), ('det', 'sto'), ARMS, HISTORIES, ('off', 'on'))
                for scenario in SCENARIOS + (('degradation',) if mode == 'sto' else ())}
    require(actual == expected, 'world/arm/history/reasoning grid')
    for c in cells:
        valid = c['status'] != 'failed_terminal'
        require(str(c['operational_valid']).lower() == str(valid).lower(), 'operational status')
        require(not valid or int(c['completed_stages']) == 6, 'stage count')


def import_handoff(handoff, out):
    require(not out.exists(), 'output already exists')
    manifest = read(handoff / 'handoff_manifest.json')
    for name, expected in manifest.items():
        require(digest(handoff / name) == expected, 'handoff hash: ' + name)
    summary = read(handoff / 'AUDIT_SUMMARY.json')
    require(summary['commit'] == COMMIT and summary['completed_operationally_valid'] == 655, 'audit provenance')
    require(read(handoff/'preservation_verification.json')['all_original_hashes_unchanged'], 'preservation')
    exports = handoff / 'exports'
    cells = read(exports / 'cells.json')
    validate_cells(cells)
    by_cell = {c['cell_id']: c for c in cells}
    requests = read(exports / 'request_attempts.json')
    for r in requests:
        r['cohort_kind'] = 'current_cell'
    for q in read(exports / 'historical_failed_requests.json'):
        c = by_cell[q['cell_id']]
        u = q['usage_raw'] or {}
        requests.append({**{k: c[k] for k in ('cell_id','graph_seed','mode','scenario','arm','history_policy','reasoning_mode')},
            **q, 'cohort_kind': 'superseded_historical_failure', 'attempt_ordinal': 1,
            'conversation_status': 'superseded_incomplete', 'charged_to_this_batch': True,
            **{k: u.get(k) for k in ('prompt_tokens','completion_tokens','total_tokens')},
            'reasoning_tokens_reported': (u.get('completion_tokens_details') or {}).get('reasoning_tokens'),
            'cached_tokens': (u.get('prompt_tokens_details') or {}).get('cached_tokens'),
            'upstream_cost_details': u.get('cost_details')})
    request_text = csv_text(requests, REQUEST_FIELDS)
    scan(request_text)
    failures = read(exports / 'failures.json')
    for f in failures:
        f['failing_stage_attempts'] = [{k: q.get(k) for k in REQUEST_FIELDS + ['provider_error']} for q in f['failing_stage_attempts']]
    out.mkdir(parents=True)
    (out/'cells.csv').write_text(csv_text(cells))
    gz_write(out/'request_usage.csv.gz', request_text.encode())
    # Lossless compression of the complete audited scientific export.
    with (exports/'scientific_metrics.csv').open('rb') as src, (out/'metrics.csv.gz').open('wb') as dst:
        with gzip.GzipFile(fileobj=dst, mode='wb', filename='', mtime=0) as z:
            while block := src.read(1024 * 1024):
                z.write(block)
    dump(out/'failures.json', failures)
    dump(out/'cost_reconciliation.json', read(exports/'cost_reconciliation.json'))
    dump(out/'usage_totals.json', read(exports/'usage_totals.json'))
    names = ('cells.json','request_attempts.json','historical_failed_requests.json','scientific_metrics.csv',
             'failures.json','cost_reconciliation.json','usage_totals.json')
    dump(out/'provenance.json', {
        'schema': 'deepseek_icl_curated_v1', 'audited_source_commit': COMMIT, 'raw_archive': ARCHIVE,
        'handoff_manifest_sha256': digest(handoff/'handoff_manifest.json'),
        'source_export_sha256': {n: digest(exports/n) for n in names},
        'metric_rows_verified_against_saved_scores': read(handoff/'sharing_verification.json')['finalized_metric_rows_verified_against_saved_scores'],
        'transformations': ['metrics.csv.gz decompresses byte-for-byte to the audited scientific CSV',
            'cells.csv retains every audited cell field',
            'request_usage includes current attempts plus the superseded failed 16K conversation; no requests are silently deduplicated',
            'public request/failure records omit configuration paths and large context/control objects; original envelopes remain in the raw archive'],
        'historical_commit': 'a3e32493ad8a10e960a5b5abff3434053e020cb9',
        'code_dependencies': ['PR #46: OpenRouter/16K', 'PR #50: context estimate', 'PR #58 / 3dbaafcc: 32K/64K bounded recovery and request-defined ON acceptance'],
        'drive_permissions': 'Archive link supplied by the owner; recipient access not verified by this offline export.'})


def generate(out):
    cells = list(rows(out/'cells.csv'))
    validate_cells(cells)
    by_cell = {c['cell_id']: c for c in cells}
    groups, seen, coverage, sentinels = {}, set(), collections.Counter(), collections.Counter()
    raw_hash = hashlib.sha256()
    with gzip.open(out/'metrics.csv.gz','rb') as f:
        while block := f.read(1024 * 1024): raw_hash.update(block)
    p = read(out/'provenance.json')
    require(raw_hash.hexdigest() == p['source_export_sha256']['scientific_metrics.csv'], 'metric export hash')
    for r in rows(out/'metrics.csv.gz'):
        require(r['cell_id'] in by_cell, 'unknown metric cell')
        c = by_cell[r['cell_id']]
        require(r['run_id'] == c['run_id'] and r['implementation_commit'] == c['source_commit'], 'metric identity')
        require(r['protocol'] == 'icl_expanded_v2' and r['model'] == 'deepseek/deepseek-v4.1-flash' and r['synthetic'] == 'False', 'metric schema/model')
        for a,b in (('condition','arm'),('graph_seed','graph_seed'),('mode','mode'),('scenario','scenario'),('history_policy','history_policy'),('reasoning_mode','reasoning_mode')):
            require(r[a] == c[b], 'metric dimensions')
        key = (r['cell_id'],r['period'],r['query_id'],r['metric'])
        require(key not in seen, 'duplicate metric'); seen.add(key)
        coverage[r['cell_id']] += 1
        valid = c['status'] != 'failed_terminal'
        require(r['operational_status'] == ('valid' if valid else 'quarantined'), 'quarantine status')
        if not valid:
            require(r['metric'] == 'operationally_quarantined' and number(r['numerator']) is None, 'failed cell scored')
            continue
        if r['metric'] == 'task_well_formed': sentinels[r['cell_id']] += 1
        group = tuple(c[k] for k in ('source_commit','initial_output_allowance','arm','history_policy','reasoning_mode','mode')) + (r['period'],r['metric'])
        g = groups.setdefault(group, {'numerator': Decimal(0), 'denominator': Decimal(0), 'scored_rows': 0, 'null_rows': 0, 'cells': set()})
        g['cells'].add(r['cell_id'])
        n, d = number(r['numerator']), number(r['denominator'])
        if n is None or not d:
            g['null_rows'] += 1
        else:
            g['numerator'] += n; g['denominator'] += d; g['scored_rows'] += 1
    require(len(seen) == p['metric_rows_verified_against_saved_scores'], 'metric row count')
    require(set(coverage) == set(by_cell), 'metric coverage')
    require(all(sentinels[c['cell_id']] == 2 for c in cells if c['status'] != 'failed_terminal'), 'period denominators')
    requests = list(rows(out/'request_usage.csv.gz'))
    require(len(requests) == 4009, 'request coverage')
    ids = {(r['cohort_kind'],r['cell_id'],r['stage'],r['attempt_ordinal']) for r in requests}
    require(len(ids) == len(requests), 'duplicate request')
    actual_caps = collections.Counter(int(r['max_output_tokens']) for r in requests if r['cohort_kind'] == 'current_cell')
    require(actual_caps == {16384:18,32768:3946,65536:40}, 'actual allowances')
    cost = read(out/'cost_reconciliation.json')
    reported = sum((number(r['reported_cost_usd']) or Decimal(0) for r in requests), Decimal(0))
    totals = read(out/'usage_totals.json')['all_preserved_attempts']
    require(reported == Decimal(totals['reported_cost_usd']), 'reported costs')
    require(sum(number(r['reported_cost_usd']) is None for r in requests) == 8, 'unknown charges')
    for field in ('prompt_tokens','completion_tokens','total_tokens','reasoning_tokens_reported','cached_tokens'):
        values = [number(r[field]) for r in requests if number(r[field]) is not None]
        require(sum(values) == totals[field]['reported_sum'] and len(values) == totals[field]['reported_n'], 'usage totals: '+field)
    require(sum(Decimal(cost[k]) for k in ('new_provider_reported_cost_usd','carried_exposure_after_evidence_reconciliation_usd','unresolved_new_reservations_usd')) == Decimal(cost['ledger_exposure_usd']), 'exposure equation')
    aggregate=[]
    dims=('source_commit','initial_output_allowance','arm','history_policy','reasoning_mode','mode','period','metric')
    for key,g in sorted(groups.items()):
        aggregate.append(dict(zip(dims,key), numerator=str(g['numerator']) if g['scored_rows'] else None,
            denominator=str(g['denominator']), scored_rows=g['scored_rows'], null_rows=g['null_rows'],
            conversations=len(g['cells']), value=str(g['numerator']/g['denominator']) if g['denominator'] else None))
    lines=['# Audited DeepSeek ICL results', '', 'Generated from saved metric rows, without reparsing or rescoring.', '',
        '| Arm | Completed / planned | Incomplete |', '|---|---:|---:|']
    for arm in ARMS:
        sub=[c for c in cells if c['arm']==arm]; n=sum(c['status']!='failed_terminal' for c in sub)
        lines.append(f'| {arm} | {n}/{len(sub)} | {len(sub)-n}/{len(sub)} |')
    metrics=[('A','transition_exact'),('B','transition_exact'),('A','route_optimal_solution'),('B','route_optimal_solution'),
             ('B','detection_correct'),('B','localization_correct'),('B','preservation_self_all_controls'),('B','preservation_truth_all_controls'),
             ('B','preservation_truth_all_four_correct')]
    lines += ['', '## Scientific results by cohort', '',
        'Each cell shows numerator/denominator, not an independent-sample confidence interval. Invalid scientific answers remain in applicable denominators. Incomplete conversations are not scored. Modes, histories and nominal cap/source cohorts stay separate; 32K cohorts can contain recorded 64K recovery attempts.', '',
        '| Cap cohort | Arm | History | Reasoning | Mode | Complete n | A belief exact | B belief exact | A routes optimal or correct no-route | B routes optimal or correct no-route | Detection | Localization | Self Preservation mean | Truth Preservation mean | Truth all-four |',
        '|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    cohorts=sorted({k[:6] for k in groups})
    for key in cohorts:
        commit,cap,arm,hist,reasoning,mode=key
        n=sum(c['status']!='failed_terminal' and tuple(c[k] for k in dims[:6])==key for c in cells)
        values=[]
        for period,metric in metrics:
            g=groups.get(key+(period,metric))
            values.append(f"{g['numerator']}/{g['denominator']}" if g and g['denominator'] else 'N/A (n=0)')
        lines.append('| '+' | '.join([cap,arm,'retained' if hist.startswith('retained') else 'separate',reasoning,mode,str(n)]+values)+' |')
    lines += ['', 'Full conditional destination/MAE/regret, parsing, self/truth exact and tolerance Preservation, and query-level metrics remain in metrics.csv.gz and aggregates.csv.gz. No failed case or malformed answer was rescued.', '',
        '## Accounting', '', '| Component | USD | Scope n |', '|---|---:|---:|',
        f"| New reported charges | {cost['new_provider_reported_cost_usd']} | 3978 known requests |",
        f"| Unknown-charge reservations | {cost['unresolved_new_reservations_usd']} | 8 requests |",
        f"| Historical carry | {cost['carried_exposure_after_evidence_reconciliation_usd']} | completed/failed original batch attempts |",
        f"| Ledger exposure | {cost['ledger_exposure_usd']} | cumulative batch |",
        f"| Remaining authorization | {cost['remaining_authorization_usd']} | cumulative batch |",
        f"| Earlier pilots outside batch | {cost['included_historical_pilots_outside_batch_reported_cost_usd']} | 2 conversations |", '',
        'Top-level provider charges are not invoice reconciliation. Upstream cost_details are not added again. Unknown charges retain reservations. Raw inconsistent reasoning subcounts are preserved, not normalized.', '',
        'All three arms used prepare, task, readout in both periods: six stages per complete conversation. Model-first received no extra turn. Recovery attempts are not extra preparation treatment stages.', '',
        'Five graph seeds, one repeat per configuration. These are descriptive results, not 655 independent graph samples or evidence of statistical significance.', '']
    validation={'cells':len(cells),'completed':655,'incomplete':5,'metric_rows':len(seen),'requests':len(requests),
        'actual_cap_request_counts_current_cells':{str(k):v for k,v in actual_caps.items()},'schema_unique_coverage':'PASS','audited_export_hash':'PASS',
        'reported_cost_total_including_historical_pilots_usd':str(reported),
        'raw_archive_access':'Owner-supplied link, access not independently verified'}
    for path in out.iterdir():
        if path.is_file():
            text=gzip.open(path,'rt').read() if path.suffix=='.gz' else path.read_text()
            scan(text)
    return '\n'.join(lines), csv_text(aggregate), validation


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--handoff',type=Path)
    ap.add_argument('--out',type=Path,default=DEFAULT)
    ap.add_argument('--check',action='store_true')
    ap.add_argument('--verify-handoff',type=Path,help='Also compare tables with the immutable audited aggregate export')
    args=ap.parse_args()
    if args.handoff:
        require(not args.check,'import is separate from check')
        import_handoff(args.handoff,args.out)
    tables,aggregate,validation=generate(args.out)
    if args.verify_handoff:
        provenance=read(args.out/'provenance.json')
        require(digest(args.verify_handoff/'handoff_manifest.json')==provenance['handoff_manifest_sha256'],'handoff manifest identity')
        manifest=read(args.verify_handoff/'handoff_manifest.json')
        name='exports/scientific_aggregates.json'
        require(digest(args.verify_handoff/name)==manifest[name],'audited aggregate hash')
        keys=('source_commit','initial_output_allowance','arm','history_policy','reasoning_mode','mode','period','metric')
        current={tuple(r[k] for k in keys):r for r in csv.DictReader(io.StringIO(aggregate))}
        original=read(args.verify_handoff/name)
        require(bool(original),'empty audited aggregates')
        for old in original:
            new=current[tuple(str(old[k]) for k in keys)]
            for field in ('numerator','denominator'):
                # Original audit sums binary floats; compare numeric values, not formatting.
                require(abs((number(new[field]) or Decimal(0))-Decimal(str(old[field])))<Decimal('1e-9'),'audited aggregate disagreement')
        print('Audited aggregate rows matched:',len(original))
    if args.check:
        require((args.out/'tables.md').read_text()==tables,'generated tables differ')
        with gzip.open(args.out/'aggregates.csv.gz','rt') as f: require(f.read()==aggregate,'generated aggregates differ')
        require(read(args.out/'validation.json')==validation,'validation differs')
    else:
        (args.out/'tables.md').write_text(tables)
        gz_write(args.out/'aggregates.csv.gz',aggregate.encode())
        dump(args.out/'validation.json',validation)
    print(json.dumps(validation,indent=2))


if __name__=='__main__': main()

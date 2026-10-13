"""H1 on expanded-ICL runs: among silent-break conversations whose period B report gives the changed link
p_success <= 0.05 or unavailable, the share of period B routes (and of conversations) that still go through it.
Usage: python experiments/h1_icl.py --sol DIR --haiku DIR --deepseek DIR [--manifest FILE.csv]
Each DIR holds that model's raw expanded-ICL run folders (from the team Drive). Only completed conversations marked operational_status=valid in the published
runs/results/icl/<model>/metrics.csv.gz are used. Each run ID is selected once; the manifest records every source
file, its SHA-256 and membership. Missing or conflicting completed sources fail before analysis."""
import argparse, csv, gzip, hashlib, json, glob, os, sys, collections
from scipy.stats import beta
lb = lambda k, n: 0.0 if k == 0 else beta.ppf(0.05, k, n - k + 1)

def rows_lenient(turn, key):
    p = turn.get('parsed') or {}
    if p.get('well_formed'):
        return p, 'strict'
    text = str(turn.get('raw_response') or ''); dec = json.JSONDecoder(); best = None
    for i, ch in enumerate(text):
        if ch != '{': continue
        try: obj, _ = dec.raw_decode(text[i:])
        except ValueError: continue
        if isinstance(obj, dict) and key in obj: best = obj      # last complete object carrying the answer field
    return ({'_obj': best} if best is not None else None), 'lenient'

def stated_broken(turn, pair):
    p, how = rows_lenient(turn, 'pairs')
    if p is None: return None, how
    if '_obj' in p:
        for r in p['_obj'].get('pairs') or []:
            if isinstance(r, dict) and (r.get('state'), r.get('action')) == pair:
                ps = r.get('p_success')
                return (r.get('available') is False or (isinstance(ps, (int, float)) and ps <= 0.05)), how
        return None, how
    v = (p.get('rows') or {}).get(f'{pair[0]}:{pair[1]}', {}).get('value') or {}
    if not v: return None, how
    ps = v.get('p_success')
    return (v.get('available') is False or (isinstance(ps, (int, float)) and ps <= 0.05)), how

def routes(turn):
    p, how = rows_lenient(turn, 'routes')
    if p is None: return None, how
    if '_obj' in p:
        rs = p['_obj'].get('routes') or []
        return [r.get('steps') or [] for r in rs if isinstance(r, dict)], how
    return [ (q.get('value') or {}).get('steps') or [] for q in (p.get('routes') or {}).values()], how

def run(files, label):
    agg = collections.defaultdict(lambda: [0, 0, 0, 0, 0])   # conv_qual, conv_through, routes, routes_through, lenient_used
    for f in files:
        a = json.load(open(f))
        if a.get('state') not in (None, 'completed'): continue
        w, i = a['world'], a['identity']
        if w.get('scenario') != 'silent_break': continue
        pair = tuple(w['true_changes'][0])
        sb, h1 = stated_broken(a['turns']['B_readout'], pair)
        if not sb: continue
        rt, h2 = routes(a['turns']['B_task'])
        if rt is None: continue
        through = [any((s.get('state'), s.get('action')) == pair for s in steps if isinstance(s, dict)) for steps in rt]
        k = (i['reasoning_mode'], i['condition'])
        g = agg[k]; g[0] += 1; g[1] += any(through); g[2] += len(through); g[3] += sum(through); g[4] += (h1 == 'lenient' or h2 == 'lenient')
    tot = collections.defaultdict(lambda: [0, 0, 0, 0, 0])
    for (rs, arm), g in sorted(agg.items()):
        for j in range(5): tot[rs][j] += g[j]
    for rs in ('off', 'on'):
        g = tot[rs]
        if not g[0]: print(f'{label:8} {rs:3}: no qualifying conversations'); continue
        print(f'{label:8} {rs:3}: {g[0]:3} conversations state the link broken | plan through it: {g[1]} ({g[1]/g[0]:.0%}, LB {lb(g[1],g[0]):.2f}) | routes through it: {g[3]} of {g[2]} ({(g[3]/g[2] if g[2] else 0):.0%}, LB {lb(g[3],g[2]) if g[2] else 0:.2f}) | lenient parse used in {g[4]}')
        for arm in ('task_only', 'model_first', 'graph_given'):
            x = agg.get((rs, arm))
            if x and x[0]: print(f'           {arm:11}: {x[1]}/{x[0]} conversations, {x[3]}/{x[2]} routes')


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = {'Sol': 'openai-gpt-5.6-sol', 'Haiku': 'anthropic-claude-haiku-5.5', 'DeepSeek': 'deepseek-deepseek-v4.1-flash'}


def published_ids(label):
    f = os.path.join(ROOT, 'runs', 'results', 'icl', RESULTS[label], 'metrics.csv.gz')
    statuses = collections.defaultdict(set)
    with gzip.open(f, 'rt', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        if not {'run_id', 'operational_status'} <= set(reader.fieldnames or []):
            raise ValueError(f'{label}: export requires run_id and operational_status')
        for row in reader:
            statuses[row['run_id']].add(row['operational_status'])
    conflicts = [rid for rid, values in statuses.items() if len(values) != 1]
    if conflicts:
        raise ValueError(f'{label}: conflicting export statuses: {sorted(conflicts)}')
    ids = {rid for rid, values in statuses.items() if values == {'valid'}}
    if not ids:
        raise ValueError(f'{label}: no operationally valid published IDs')
    return ids


def select_inputs(folder, ids, label):
    """Select one complete, hash-consistent source per valid published run ID."""
    files = sorted(glob.glob(os.path.join(folder, '**', 'icl_expanded*.json'), recursive=True))
    rows, selected, selected_hashes = [], [], {}
    for f in files:
        rid = os.path.basename(f)[:-5]
        with open(f, 'rb') as fh:
            data = fh.read()
        digest = hashlib.sha256(data).hexdigest()
        artifact = json.loads(data)
        if artifact.get('run_id') != rid:
            raise ValueError(f'{label}: filename/artifact run ID mismatch: {rid}')
        use = rid in ids and artifact.get('state') == 'completed'
        if use and rid in selected_hashes:
            if selected_hashes[rid] != digest:
                raise ValueError(f'{label}: conflicting completed sources for {rid}')
            use = False  # Identical copies are documented but never counted twice.
        if use:
            selected_hashes[rid] = digest
            selected.append(f)
        rows.append([label, os.path.relpath(f, folder), rid, digest, use])
    missing = ids - selected_hashes.keys()
    if missing:
        raise ValueError(f'{label}: completed sources missing for valid IDs: {sorted(missing)}')
    return rows, selected


def main():
    ap = argparse.ArgumentParser()
    for label in RESULTS:
        ap.add_argument('--' + label.lower(), required=True, help=f'{label} raw run folder')
    ap.add_argument('--manifest', default=os.path.join(ROOT, 'runs', 'results', 'hypotheses', 'h1_inputs_manifest.csv'))
    a = ap.parse_args()
    rows, selected = [], {}
    for label in RESULTS:
        model_rows, selected[label] = select_inputs(
            getattr(a, label.lower()), published_ids(label), label)
        rows.extend(model_rows)
    for label in RESULTS:
        count = sum(row[0] == label for row in rows)
        print(f'{label}: {count} files, {len(selected[label])} unique completed valid published runs, 0 missing')
        run(selected[label], label)
    with open(a.manifest, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['model', 'file', 'run_id', 'sha256', 'used'])
        w.writerows(rows)
    print('manifest:', a.manifest)


if __name__ == '__main__':
    main()

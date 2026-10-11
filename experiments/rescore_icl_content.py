# Usage: python experiments/rescore_icl_content.py <code checkout of the run> <json list of run folders> <output folder>
"""Content re-score: answers that fail the strict JSON parse are re-read from the last complete JSON object that
carries the answer field, then scored with the run's own scorer. Strict scores stay the primary record."""
import copy, json, os, sys, glob
code, dirs_file, out = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, code); os.chdir(code)
import icl_expanded as design
KEYS = {'task': 'routes', 'readout': 'pairs', 'prepare': None}
dec = json.JSONDecoder()
def last_obj(text, key):
    best = None
    for i, ch in enumerate(text):
        if ch != '{': continue
        try: obj, _ = dec.raw_decode(text[i:])
        except ValueError: continue
        if isinstance(obj, dict) and (key is None or key in obj): best = obj
    return best
changed_turns = total = 0
for d in json.load(open(dirs_file)):
    for f in glob.glob(d + '/icl_expanded*.json'):
        a = json.load(open(f)); turns = copy.deepcopy(a['turns'])
        for st, t in turns.items():
            kind = st.split('_', 1)[1]; key = KEYS.get(kind)
            if key is None or (t.get('parsed') or {}).get('well_formed'): continue
            raw = str(t.get('raw_response') or ''); total += 1
            obj = last_obj(raw, key)
            if obj is not None and raw.strip() != json.dumps(obj):
                t['raw_response'] = json.dumps(obj); changed_turns += 1
        a['scores'] = design.score_conversation(a['world'], a['identity']['condition'], turns)
        dst = os.path.join(out, os.path.basename(d)); os.makedirs(dst, exist_ok=True)
        json.dump(a, open(os.path.join(dst, os.path.basename(f)), 'w'))
        if os.path.exists(os.path.join(d, 'summary.json')):
            import shutil; shutil.copy(os.path.join(d, 'summary.json'), dst)
print(f'malformed answers: {total}; re-read from a complete JSON object: {changed_turns}')

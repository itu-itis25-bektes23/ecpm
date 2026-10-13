"""H4 threshold sensitivity: the share choosing the broken link again after n consecutive failures, n = 2 to 10.

    python experiments/h4_threshold_sensitivity.py --grid UNZIPPED_GRID [--grid ...] [--out table.md]

Uses explore_metrics.choices_after_consecutive_failures with n_failures = n, the function behind the published H4
(streak across M0 and M1, threshold reached in M1, reset on a success of the link). Task-only runs, stochastic silent
break and degradation, both confirmatory grids. At n = 6 it reproduces the published H4 counts. Inputs are the GRID
zips kept outside the repository.
"""
import glob, json, sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__))))
import explore_metrics as M, run_pilot
from types import SimpleNamespace as NS
N = (2, 3, 4, 5, 6, 7, 8, 10)
def steps(ep):
    return NS(steps=[NS(**s) for s in ep['steps']], **{k: v for k, v in ep.items() if k != 'steps'})
out = {}
import argparse
ap = argparse.ArgumentParser(); ap.add_argument('--grid', action='append', required=True, help='unzipped confirmatory GRID folder'); ap.add_argument('--out')
ARGS = ap.parse_args()
for root in sorted(ARGS.grid):
    grid = 'no_prep' if root.endswith(('130215', '130148', '130438')) else 'matched_prep'
    for f in glob.glob(root + '/**/pilot_stochastic_active.json', recursive=True):
        d = f.rsplit('/', 1)[0]
        meta = json.load(open(d + '/condition.json')); a = json.load(open(f)); ins = a['instance']
        if meta.get('condition') != 'task_only' or ins.get('deterministic') or ins.get('condition') not in ('silent_break', 'degradation'):
            continue
        inst = run_pilot.make_pair(ins['graph_seed'], ins['condition'], deterministic=False, matched=True)
        m0 = [steps(e) for e in a['explore']['m0_episodes']]; m1 = [steps(e) for e in a['explore']['m1_episodes']]
        model = a['model']['model'].split('/')[-1]
        for n in N:
            r = M.choices_after_consecutive_failures(inst, m0, m1, n_failures=n)
            if r.get('reached_in_m1'):
                k = out.setdefault((grid, model, n), [0, 0]); k[1] += 1; k[0] += bool(r.get('chose_again'))
pass
L = ['| Grid | Model | ' + ' | '.join(f'{n} failures' for n in N) + ' |', '|---|---|' + '---|' * len(N)]
for grid in ('no_prep', 'matched_prep'):
    pass
    for model in ('claude-haiku-5.5', 'deepseek-v4.1-flash', 'gpt-5.6-sol'):
        cells = []
        for n in N:
            k, q = out.get((grid, model, n), [0, 0])
            cells.append(f'{k}/{q} ({100 * k / q:.0f}%)' if q else '0/0')
        L.append(f'| {grid} | {model} | ' + ' | '.join(cells) + ' |')
print('\n'.join(L))
if ARGS.out:
    open(ARGS.out, 'w', encoding='utf-8').write('\n'.join(L) + '\n')

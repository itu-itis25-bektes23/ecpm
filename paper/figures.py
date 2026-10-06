"""Figures for the ECPM paper: world atlas and evidence networks.

Optional paper tooling. Needs numpy, scipy, networkx, matplotlib and
scikit-learn (paper/requirements-figures.txt); the research code stays stdlib only.
Everything is computed from the generator and the evidence-only prompt view,
with fixed seeds, so reruns give identical files. No model calls.

    python3 paper/tasks.py figures            # or: python3 paper/figures.py OUTDIR
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import resource_mdp as R, ecpm_baseline as B
FAM = {8: dict(n_nodes=8, extra_edges=6), 16: dict(n_nodes=16, extra_edges=20)}
SCEN = ['no_change', 'irrelevant', 'silent_break', 'hard_removal', 'redirect', 'degradation']

def build(seed, cond, n):
    return R.make_pair(seed, cond, matched=True, **FAM[n])

def status(seed, cond, n):
    try:
        inst = build(seed, cond, n)
    except Exception:
        return 'not_built', None
    pre, post = inst.oracle['pre'], inst.oracle['post']
    if not post['solvable'] or not (pre['route_unique'] and post['route_unique']):
        return 'excluded', inst
    moved = pre['optimal_route'] != post['optimal_route']
    if cond in ('no_change', 'irrelevant'):
        return ('excluded' if moved else 'eligible'), inst
    return ('eligible' if moved else 'restraint'), inst

def run_set(n, seeds=range(31, 131)):
    return [s for s in seeds if status(s, 'silent_break', n)[0] == 'eligible']

def features(inst, K, ev_seed=0):
    ev = R.paired_evidence(inst, k=K, evidence_seed=ev_seed, max_episodes=3000)
    pv = R.prompt_view(R.pair_to_json(inst, ev), budget_per_pair=K)
    pre, post, dpre, dpost = B.read_periods(pv)
    rate, tv, removed = [], [], 0.0
    for pair in pre:
        if pair not in post:
            removed = 1.0; continue
        a0, a1 = pre[pair], post[pair]
        r0, r1 = a0['delivered'] / a0['attempts'], a1['delivered'] / a1['attempts']
        rate.append(abs(r1 - r0))
        d0 = {k: v / a0['attempts'] for k, v in dpre.get(pair, {}).items()}
        d1 = {k: v / a1['attempts'] for k, v in dpost.get(pair, {}).items()}
        d0['_stay'] = 1 - r0; d1['_stay'] = 1 - r1
        keys = set(d0) | set(d1)
        tv.append(0.5 * sum(abs(d0.get(k, 0) - d1.get(k, 0)) for k in keys))
    top = lambda x: sorted(x, reverse=True)[:6] + [0.0] * max(0, 6 - len(x))
    return top(rate) + [0.5 * removed], top(tv) + [0.5 * removed]

import sys, math, os, json
import numpy as np, networkx as nx, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
plt.rcParams.update({'pdf.fonttype': 42, 'font.family': 'serif',
                     'font.serif': ['TeX Gyre Termes', 'Times New Roman', 'DejaVu Serif'], 'font.size': 7})
OUT = sys.argv[1] if len(sys.argv) > 1 else 'figures'
os.makedirs(OUT, exist_ok=True)
CMAP = plt.get_cmap('viridis')
TCOL, UCOL = '#D55E00', '#0072B2'          # target T*, off-route control U*
PAL = {'no_change': '#6E6E6E', 'irrelevant': '#56B4E9', 'silent_break': '#D55E00',
       'hard_removal': '#CC79A7', 'redirect': '#E69F00', 'degradation': '#009E73'}
MARK = {'no_change': 'o', 'irrelevant': 's', 'silent_break': '^', 'hard_removal': 'v',
        'redirect': 'D', 'degradation': 'P'}
NAME = {'no_change': 'no change', 'irrelevant': 'irrelevant', 'silent_break': 'silent break',
        'hard_removal': 'hard removal', 'redirect': 'redirect', 'degradation': 'degradation'}
summary = {}

def world(seed, n):
    sb = build(seed, 'silent_break', n); ir = build(seed, 'irrelevant', n)
    G = nx.DiGraph(); G.add_nodes_from(sb.m0.nodes)
    for (u, v), p in sb.m0.p.items(): G.add_edge(u, v, p=p)
    route = sb.oracle['pre']['optimal_route']
    return G, set(zip(route, route[1:])), sb.change.edge if hasattr(sb.change, 'edge') else sb.change['edge'], \
        (ir.change.edge if hasattr(ir.change, 'edge') else ir.change['edge']), sb, route

def draw_world(ax, seed, n, cx, cy, r, halo=False, lw=0.35):
    G, R_, T, U, sb, route = world(seed, n)
    pos = nx.kamada_kawai_layout(G.to_undirected())
    P = np.array(list(pos.values())); P -= P.mean(0); P /= (np.abs(P).max() + 1e-9)
    pos = {k: (cx + r * P[i, 0], cy + r * P[i, 1]) for i, k in enumerate(pos)}
    if halo:
        ax.add_patch(plt.Circle((cx, cy), r * 1.25, color='#BBBBBB', alpha=0.35, lw=0, zorder=0))
    for u, v, d in G.edges(data=True):
        (x0, y0), (x1, y1) = pos[u], pos[v]
        col, w, z = CMAP((d['p'] - 0.6) / 0.35), lw, 1
        if (u, v) in R_: w, z = lw * 2.4, 2
        if (u, v) == U: col, w, z = UCOL, lw * 2.6, 3
        if (u, v) == T: col, w, z = TCOL, lw * 3.2, 4
        ax.plot([x0, x1], [y0, y1], color=col, lw=w, alpha=0.9, zorder=z, solid_capstyle='round')
    xs, ys = zip(*pos.values()); ax.scatter(xs, ys, s=0.6, c='#222222', zorder=5, lw=0)
    return pos

def spiral(m, radius):
    g = math.pi * (3 - math.sqrt(5))
    return [(radius * math.sqrt((i + 0.5) / m) * math.cos(i * g), radius * math.sqrt((i + 0.5) / m) * math.sin(i * g)) for i in range(m)]

def atlas(fname, big=False):
    fig, ax = plt.subplots(figsize=(6.3, 2.35) if not big else (12, 4.6))
    ax.set_aspect('equal'); ax.axis('off')
    for n, cx, rr, wr in ((8, -6.4, 2.9, 0.27), (16, 6.4, 2.9, 0.29)):
        rs = run_set(n); restr = {s for s in rs if status(s, 'degradation', n)[0] == 'restraint'}
        order = sorted(rs, key=lambda s: (s in restr, s))
        summary[f'n{n}'] = dict(run_set=len(rs), restraint=len(restr))
        for (x, y), s in zip(spiral(len(order), rr), order):
            draw_world(ax, s, n, cx + x, y, wr, halo=s in restr, lw=0.3 if n == 16 else 0.38)
        ax.text(cx, -3.35, f'{len(rs)} {"eight" if n == 8 else "sixteen"}-node worlds, '
                f'{len(restr)} restraint cases (grey halo)', ha='center', va='top', fontsize=6.5)
    pos = draw_world(ax, 1, 8, 0, 0.15, 1.75, lw=1.0)
    _, R_, T, U, sb, route = world(1, 8)
    for k, (x, y) in pos.items():
        ax.text(x, y, k, fontsize=6.5, ha='center', va='center', zorder=7,
                bbox=dict(boxstyle='circle,pad=0.18', fc='white', ec='#222222', lw=0.5))
    rd = build(1, 'redirect', 8).change
    nu, nv = (rd.new_edge if hasattr(rd, 'new_edge') else rd['new_edge'])
    ax.annotate('', xy=pos[nv], xytext=pos[nu], zorder=6, arrowprops=dict(arrowstyle='->', color=TCOL, lw=0.9, ls='--',
                connectionstyle='arc3,rad=0.25', shrinkA=6, shrinkB=6))
    ax.text(0, -2.0, f'seed 1: start {sb.start}, goal {sb.m0.goal}, route ' + r'$\to$'.join(route),
            ha='center', fontsize=6.5)
    leg = [Line2D([0], [0], color=TCOL, lw=2.2, label=r'target $T^*$'), Line2D([0], [0], color=UCOL, lw=2.0, label=r'control $U^*$'),
           Line2D([0], [0], color=TCOL, lw=0.9, ls='--', label='redirect')]
    ax.legend(handles=leg, loc='upper center', bbox_to_anchor=(0.5, 0.9), ncol=3, fontsize=6, frameon=False,
              handlelength=1.6, columnspacing=1.0)
    sm = plt.cm.ScalarMappable(cmap=CMAP, norm=plt.Normalize(0.6, 0.95))
    cax = fig.add_axes([0.42, 0.93, 0.16, 0.025]); cb = fig.colorbar(sm, cax=cax, orientation='horizontal')
    cb.set_ticks([0.6, 0.95]); cb.ax.tick_params(labelsize=5.5, length=1.5, pad=1); cb.outline.set_linewidth(0.3)
    cax.set_title('success probability $p$', fontsize=5.5, pad=1.5)
    ax.set_xlim(-9.6, 9.6); ax.set_ylim(-3.7, 3.3)
    fig.savefig(os.path.join(OUT, fname), bbox_inches='tight', pad_inches=0.01, dpi=300); plt.close(fig)

def evidence(fname, K, seeds, panels=('rate', 'transition'), figsize=(3.1, 3.5)):
    X = {'rate': [], 'transition': []}; lab = []
    for s in seeds:
        for c in SCEN:
            inst = build(s, c, 8); f_rate, f_tv = features(inst, K)
            X['rate'].append(f_rate); X['transition'].append(f_tv); lab.append(c)
    lab = np.array(lab)
    fig, axes = plt.subplots(len(panels), 1, figsize=figsize)
    titles = {'rate': 'success rates only (rate counter)', 'transition': 'full outcome distributions (transition counter)'}
    summary[f'evidence_K{K}'] = {}
    for ax, key in zip(np.atleast_1d(axes), panels):
        A = np.array(X[key]); A = A + 2e-3 * np.random.default_rng(0).standard_normal(A.shape)
        from sklearn.neighbors import NearestNeighbors
        from sklearn.manifold import TSNE
        nn = NearestNeighbors(n_neighbors=9).fit(A); _, idx = nn.kneighbors(A)
        G = nx.Graph(); G.add_nodes_from(range(len(A)))
        for i, row in enumerate(idx):
            for j in row[1:]: G.add_edge(i, int(j))
        P = TSNE(n_components=2, perplexity=50, init='pca', random_state=0, early_exaggeration=6).fit_transform(A)
        hr = lab == 'hard_removal'; mn = ~hr
        sp = np.ptp(P[mn], 0)
        target = np.array([P[mn, 0].min() + 0.05 * sp[0], P[mn, 1].max() - 0.02 * sp[1]])
        P[hr] = (P[hr] - P[hr].mean(0)) * 0.6 + target   # t-SNE distances between clusters carry no meaning
        for i, j in G.edges():
            ax.plot(*zip(P[i], P[j]), color=PAL[lab[i]], lw=0.3, alpha=0.45, zorder=1)
        placed = []
        span = np.ptp(P, 0).max()
        for c in SCEN:
            m = lab == c
            ax.scatter(P[m, 0], P[m, 1], s=7, marker=MARK[c], c=PAL[c], lw=0.2, edgecolors='white', zorder=2)
        for c in SCEN:
            cx, cy = np.median(P[lab == c], 0)
            while any(abs(cx - px) < 0.22 * span and abs(cy - py) < 0.06 * span for px, py in placed):
                cy -= 0.065 * span
            placed.append((cx, cy))
            ax.text(cx, cy, NAME[c], fontsize=6, ha='center', va='center', zorder=4, color='black',
                    bbox=dict(boxstyle='round,pad=0.12', fc='white', ec=PAL[c], lw=0.7, alpha=0.9))
        red = np.where(lab == 'redirect')[0]
        summary.setdefault(f'redirect_neighbours_K{K}', {})[key] = {
            c: round(float(np.mean([np.mean(lab[idx[i, 1:]] == c) for i in red])), 3) for c in SCEN}
        # share of each scenario's nearest neighbours that carry its own label (cluster purity)
        pur = {c: float(np.mean([np.mean(lab[idx[i, 1:]] == c) for i in np.where(lab == c)[0]])) for c in SCEN}
        summary[f'evidence_K{K}'][key] = {c: round(v, 3) for c, v in pur.items()}
        ax.set_title(titles[key], fontsize=6.5, pad=2); ax.axis('off')
    fig.tight_layout(pad=0.2, h_pad=0.4)
    fig.savefig(os.path.join(OUT, fname), bbox_inches='tight', pad_inches=0.01, dpi=300); plt.close(fig)

if __name__ == '__main__':
    seeds8 = run_set(8)
    atlas('fig_atlas.pdf')
    evidence('fig_evidence_k10.pdf', 10, seeds8)
    atlas('fig_atlas_large.pdf', big=True)
    for K in (5, 20):
        evidence(f'fig_evidence_k{K}.pdf', K, seeds8, figsize=(6.3, 2.6))
    json.dump(summary, open(os.path.join(OUT, 'figure_summary.json'), 'w'), indent=1)
    print(json.dumps(summary))

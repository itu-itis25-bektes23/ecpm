"""Fill the reference cells of Table 3 and tab:det from runs/references (reference_sweep.py output).
Anchored: each row prefix must occur exactly once. Usage: python3 paper/fill_references.py TEX"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import resource_mdp as R
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tex_path = sys.argv[1]; tex = open(tex_path).read()
def rows(f): return json.load(open(os.path.join(ROOT, "runs/references", f)))["rows"]
def eligible(rs):
    by = {}
    for r in rs:
        if r["condition"] != "no_change": by.setdefault(r["seed"], set()).add(r["condition"])
    return {s for s, c in by.items() if len(c) == 5}
def share(rs, ref): return f'{sum(r[ref]["loc"] == r["truth"] for r in rs) / len(rs):.2f}'
sto = rows("part_sto_10.json"); el = eligible(sto); sto = [r for r in sto if r["seed"] in el]
det = rows("part_det_10.json")
cell = lambda rs, c: [r for r in rs if r["condition"] == c]
deg = cell(sto, "degradation")
moves = [r for r in deg if (lambda i: i.m0.optimal_route(i.start)[0] != i.m1.optimal_route(i.start)[0])(
    R.make_pair(r["seed"], "degradation", deterministic=False, matched=True))]
rest = [r for r in deg if r not in moves]
assert (len(el), len(moves), len(rest)) == (84, 60, 24), (len(el), len(moves), len(rest))
edits = []
for name, c in (("Irrelevant", "irrelevant"), ("Silent break", "silent_break"), ("Hard removal", "hard_removal"), ("Redirect", "redirect")):
    v = share(cell(sto, c), "rate"); g = share(cell(sto, c), "generator")
    edits.append((f"\n{name} & {v} & \\PH & {g} &", f"\n{name} & {v} & {share(cell(sto, c), 'bayes')} & {g} &"))
    dv = share(cell(det, c), "rate"); dg = share(cell(det, c), "generator")
    edits.append((f"Det. & {name} & {dv} & \\PH & {dg} &", f"Det. & {name} & {dv} & {share(cell(det, c), 'bayes')} & {dg} &"))
for label, rs in (("moves", moves), ("restraint", rest)):
    v = share(rs, "rate")
    edits.append((f"Degr.\\ ({label}) & {v} & \\PH & \\PH &", f"Degr.\\ ({label}) & {v} & {share(rs, 'bayes')} & {share(rs, 'generator')} &"))
n0 = tex.count("\\PH")
for old, new in edits:
    if tex.count(new) == 1 and old not in tex:
        continue  # already filled with the same value
    assert tex.count(old) == 1, f"anchor not unique or missing: {old!r} ({tex.count(old)})"
    tex = tex.replace(old, new)
open(tex_path, "w").write(tex)
print(f"{len(edits)} rows filled, \\PH {n0} -> {tex.count(chr(92) + 'PH')}")

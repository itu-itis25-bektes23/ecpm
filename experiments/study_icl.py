"""Expanded ICL for the study rounds: Sol, Haiku and DeepSeek through OpenRouter, one procedure for all three.

Generalizes haiku_icl.py. Run from the repository root, per model:

    python experiments/study_icl.py config    --model haiku      # OFF config from the OpenRouter endpoints API, with sources
    python experiments/study_icl.py preflight --model haiku      # ONE paid preflight for OFF, never repeated, then validated configs
    python experiments/study_icl.py jobs      --model haiku --round exploratory   # command lines for the round
    python experiments/study_icl.py run       --model haiku --round exploratory --workers 16
    python experiments/study_icl.py audit     --model haiku --round exploratory
    python experiments/study_icl.py export    --model haiku --round exploratory
    python experiments/study_icl.py all       --model haiku --round exploratory --workers 16 --yes   # every step, unattended

Rules kept from the ICL OpenRouter procedure: every config value comes from a machine-readable source recorded with
its address and date, or the script stops; one backing provider is pinned from evidence; each preflight runs once and
is never retried; reasoning is off (the study's condition). Configs and evidence go to ../ecpm-study-private/<model>/,
conversations to ../ecpm-study-runs/<round>/icl/. Seeds come from runs/study_v1_seeds.json.
"""
import argparse, copy, datetime, gzip, json, os, shutil, subprocess, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = 'https://openrouter.ai/api/v1'
DOCS = {'routing': 'https://openrouter.ai/docs/features/provider-routing',
        'reasoning': 'https://openrouter.ai/docs/use-cases/reasoning-tokens',
        'parameters': 'https://openrouter.ai/docs/api-reference/parameters'}
MODELS = {
    'sol': dict(model='openai/gpt-5.6-sol', profile='sol_openrouter', template='openrouter_sol.template.json', maker='openai'),
    'haiku': dict(model='anthropic/claude-haiku-5.5', profile='haiku_openrouter', template='openrouter_haiku.template.json',
                  maker='anthropic'),
    'deepseek': dict(model='deepseek/deepseek-v4.1-flash', profile='deepseek_openrouter',
                     template='openrouter_deepseek.template.json', maker='deepseek',
                     # The earlier DeepSeek ICL runs were pinned to Ionstream (runs/results/icl/deepseek-deepseek-v4.1-flash/
                     # README.md; every recorded answer reports Ionstream), and the maker's own endpoint is excluded by the
                     # account's allowed-providers setting (preflight 12 October 2026: HTTP 404, nothing generated).
                     pin='ionstream',
                     pin_reason='the provider the earlier DeepSeek ICL runs were pinned to (results README), allowed by the '
                                'account; the maker endpoint is excluded by the account\'s allowed-providers setting'),
}
HIST = {'separate': 'separate_reports_post_task_v1', 'kept': 'retained_reports_v2'}
SCEN = {'det': ('no_change', 'irrelevant', 'silent_break', 'hard_removal', 'redirect'),
        'sto': ('no_change', 'irrelevant', 'silent_break', 'hard_removal', 'redirect', 'degradation')}
ARMS = ('task_only', 'model_first', 'graph_given')
CAP = 16384
MODE = 'off'
TODAY = datetime.date.today().isoformat()


def sh(cmd, cwd=None, check=True, env=None):
    print('>', ' '.join(map(str, cmd)), flush=True)
    return subprocess.run([str(c) for c in cmd], cwd=cwd, check=check, env=env)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


# Shared across working copies and rounds (configs are validated once per model); the round launcher sets both.
PRIVATE = Path(os.environ.get('STUDY_PRIVATE_DIR') or ROOT.parent / 'ecpm-study-private')
RUNS = Path(os.environ.get('STUDY_RUNS_DIR') or ROOT.parent / 'ecpm-study-runs')


def priv(key):
    return PRIVATE / key


def out_dir(rnd):
    return RUNS / rnd / 'icl'


def seeds(rnd):
    s = load(ROOT / 'runs' / 'study_v1_seeds.json')
    if rnd not in s:
        sys.exit(f'round {rnd!r} not in runs/study_v1_seeds.json (has {[k for k in s if isinstance(s[k], list)]})')
    limit = int(os.environ.get('STUDY_ICL_SEED_LIMIT') or 0)      # testing only: the first N seeds
    return s[rnd][:limit] if limit else s[rnd]


def env_for(rnd):
    e = dict(os.environ)
    e['ECPM_ICL_SEEDS'] = ','.join(map(str, seeds(rnd)))
    return e


# ---------------------------------------------------------------------------------------------------- config
def fetch(url):
    if os.environ.get('STUDY_ICL_ENDPOINTS_JSON'):          # offline testing with a saved API answer
        return load(os.environ['STUDY_ICL_ENDPOINTS_JSON'])
    req = urllib.request.Request(url, headers={'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def pick_endpoint(key, data):
    """Pin one backing provider from evidence: the maker's standard endpoint (tag exactly the maker), else the
    single maker endpoint, else the only endpoint listed; otherwise stop. Tags like "openai/flex" or "openai/fast"
    are service tiers of the maker, so the standard tier is preferred over them."""
    eps = data['data']['endpoints']
    m = MODELS[key]
    tags = [str(e.get('tag', '')) for e in eps]
    if m.get('pin'):
        hit = [e for e in eps if str(e.get('tag', '')) == m['pin']] or \
              [e for e in eps if str(e.get('tag', '')).split('/')[0] == m['pin']]
        if len(hit) == 1:
            return hit[0], f'pinned to "{hit[0]["tag"]}": {m["pin_reason"]}'
        sys.exit(f'{m["model"]}: the pinned provider "{m["pin"]}" matches {len(hit)} endpoints ({tags}); stopping')
    exact = [e for e in eps if str(e.get('tag', '')) == m['maker']]
    if len(exact) == 1:
        tiers = [t for t in tags if t.split('/')[0] == m['maker'] and t != m['maker']]
        why = f'the maker\'s standard endpoint ("{m["maker"]}")'
        return exact[0], why + (f'; its service tiers {tiers} were not used' if tiers else '')
    maker = [e for e in eps if str(e.get('tag', '')).split('/')[0] == m['maker']]
    if len(maker) == 1:
        return maker[0], f'the maker\'s only endpoint ("{maker[0]["tag"]}")'
    if len(eps) == 1:
        return eps[0], 'the only endpoint listed'
    sys.exit(f'{m["model"]}: {len(eps)} endpoints and no standard maker endpoint ({tags}); choose one by evidence '
             'before running')


def config(key):
    m = MODELS[key]
    url = f'{API}/models/{m["model"]}/endpoints'
    data = fetch(url)
    save(priv(key) / 'sources' / f'openrouter_endpoints_{TODAY}.json', data)
    ep, why = pick_endpoint(key, data)
    need = {'max_tokens', 'reasoning'}
    if not need <= set(ep.get('supported_parameters', [])):
        sys.exit(f'{key}: endpoint does not list {need - set(ep.get("supported_parameters", []))}; stopping')
    if int(ep.get('max_completion_tokens') or 0) < CAP or int(ep.get('context_length') or 0) < CAP:
        sys.exit(f'{key}: endpoint output or context limit is below {CAP} tokens; stopping')
    src = f'OpenRouter endpoints API {url}, retrieved {TODAY}, saved as sources/openrouter_endpoints_{TODAY}.json'
    w = copy.deepcopy(load(ROOT / 'docs' / m['template']))
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    d, e = w['deployment'], w['deployment']['effective']
    d.update(response_model=m['model'], model_source=src, supported_request_fields=sorted(need | {'provider', 'plugins'}))
    e.update(reasoning_mode=MODE, max_output_tokens=int(ep['max_completion_tokens']), history_truncation=False, source=src,
             runtime=None, runtime_source=f'Unavailable: OpenRouter does not publish the serving runtime ({src})',
             template_sha256=None, template_source=f'Unavailable: the hosted chat template is not published ({src})',
             provider_slug=ep['tag'], response_provider=ep['provider_name'],
             routing_source=f'{DOCS["routing"]}, retrieved {TODAY}: pinned to provider "{ep["tag"]}" ({why}) with allow_fallbacks false',
             sampling_source=f'No sampling fields are sent, so provider defaults apply ({DOCS["parameters"]}, retrieved {TODAY})',
             output_context_source=f'{src}: context_length {ep["context_length"]}, max_completion_tokens {ep["max_completion_tokens"]}',
             no_reasoning_budget_source=f'{DOCS["reasoning"]}, retrieved {TODAY}: reasoning.enabled sets no explicit budget')
    e['hosted_evidence'].update(date=TODAY, source=f'{DOCS["reasoning"]}, retrieved {TODAY}',
                                effect='disables_reasoning_computation',
                                request_fields={'reasoning': {'enabled': False, 'exclude': False}},
                                reasoning_tokens_source=f'usage.completion_tokens_details.reasoning_tokens ({DOCS["reasoning"]})')
    d['context'] = {'method': 'openrouter_utf8_reserve_estimate_v1', 'tokens': int(ep['context_length']),
                    'overhead_tokens_per_message': None, 'engineering_reserve_per_message': 4096,
                    'admission_fraction': 0.25, 'source': src}
    p = ep['pricing']
    d['pricing'] = {'input_per_million': round(float(p['prompt']) * 1e6, 6),
                    'output_per_million': round(float(p['completion']) * 1e6, 6), 'source': src}
    w['expanded'].update(history_policy=HIST['separate'], reasoning_mode=MODE,
                         stage_limits_source=f'icl_expanded.py at commit {commit}',
                         system_message_source=f'icl_expanded.py SYSTEM at commit {commit}',
                         context_source=f'estimate-based OpenRouter context admission with {src}')
    save(priv(key) / f'{key}_{MODE}_candidate.json', w)
    print(f'{key}: config written. Pinned {ep["provider_name"]} ({ep["tag"]}), {why}; context {ep["context_length"]}, '
          f'max output {ep["max_completion_tokens"]}, price per million in/out {d["pricing"]["input_per_million"]}/'
          f'{d["pricing"]["output_per_million"]}')


# ---------------------------------------------------------------------------------------------------- preflight
def validated(key, hist):
    return priv(key) / f'{key}_{MODE}_{hist}_validated.json'


def preflight(key, yes=False):
    if all(validated(key, h).exists() for h in HIST):
        return print(f'{key}: already validated, no preflight sent')
    if not os.environ.get('OPENROUTER_API_KEY'):
        sys.exit('set OPENROUTER_API_KEY first')
    cand = priv(key) / f'{key}_{MODE}_candidate.json'
    if not cand.exists():
        sys.exit(f'{key}: no candidate config; run config first')
    out = priv(key) / f'{MODE}_preflight'
    if out.exists():
        sys.exit(f'{key}: {out} exists, a preflight already ran; it is never repeated. Inspect it, then remove the '
                 'folder only if the evidence shows nothing was sent')
    if not yes and input(f'{key}: send ONE paid OFF preflight (a few cents)? [yes/no] ').strip().lower() != 'yes':
        return print('nothing sent')
    r = sh([sys.executable, '-B', 'experiments/preflight_icl_expanded.py', '--config', cand, '--out', out, '--execute'],
           cwd=ROOT, check=False)
    if r.returncode or not (out / 'validated_wrapper.json').exists():
        sys.exit(f'{key}: preflight not accepted; stopping without retry. Evidence in {out}')
    accepted = load(out / 'validated_wrapper.json')
    for name, policy in HIST.items():                      # same evidence, each history setting
        w = copy.deepcopy(accepted); w['expanded']['history_policy'] = policy
        sys.path.insert(0, str(ROOT))
        import icl_expanded as x
        x.validate_config(w, MODELS[key]['profile'], MODE, policy, CAP)
        save(validated(key, name), w)
    print(f'{key}: preflight accepted, configs validated for both history settings')


# ---------------------------------------------------------------------------------------------------- jobs, run
def tag(key, seed, mode, cond, arm, hist):
    return f'{key}_{MODE}_{mode}_{cond}_s{seed}_{arm}_{hist}_mt{CAP}'


def line(key, rnd, seed, mode, cond, arm, hist, dry=False):
    m = MODELS[key]
    base = ['python', '-B', 'run_pilot.py', '--protocol', 'icl_expanded_v2', '--seed', seed, '--mode', mode,
            '--condition', cond, '--k', 10, '--budget', 10, '--evidence-seed', 0, '--model-first-condition', arm,
            '--history-policy', HIST[hist], '--request-profile', m['profile'], '--reasoning-mode', MODE,
            '--repeats', 1, '--sampling-seeds', 0, '--max-tokens', CAP]
    tail = (['--provider', 'dry-run'] if dry else
            ['--provider', 'openai', '--model', m['model'], '--base-url', API, '--timeout', 900,
             '--deployment-config', validated(key, hist)])
    return ' '.join(f'"{x}"' if ' ' in str(x) else str(x) for x in base + tail +
                    ['--out', out_dir(rnd), '--tag', tag(key, seed, mode, cond, arm, hist)])


def grid(rnd):
    return [(s, mo, c, a, h) for mo in ('det', 'sto') for c in SCEN[mo] for s in seeds(rnd) for a in ARMS for h in HIST]


def jobs_file(key, rnd, dry=False):
    return priv(key) / f'jobs_{rnd}{"_dry" if dry else ""}.txt'


def jobs(key, rnd, dry=False):
    rows = [line(key, rnd, *g, dry=dry) for g in grid(rnd)]
    f = jobs_file(key, rnd, dry)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text('\n'.join(rows) + '\n', encoding='utf-8')
    print(f'{key}: {len(rows)} command lines in {f}')
    return f


def run(key, rnd, workers, dry=False):
    f = jobs_file(key, rnd, dry)
    if not f.exists():
        f = jobs(key, rnd, dry)
    state = priv(key) / f'state_{rnd}{"_dry" if dry else ""}'
    return sh([sys.executable, '-B', 'run_agentic_cost_check.py', '--commands', f, '--workers', workers,
               '--cwd', ROOT, '--state', state], cwd=ROOT, check=False, env=env_for(rnd)).returncode


def audit(key, rnd, dry=False):
    bad, done = [], 0
    for g in grid(rnd):
        d = out_dir(rnd) / tag(key, *g)
        try:
            s = load(d / 'summary.json')
        except OSError:
            bad.append(f'{d.name}: no summary'); continue
        if not s.get('operational_gate_pass') or s.get('completed_conversations') != s.get('expected_conversations'):
            bad.append(f'{d.name}: operational gate not passed'); continue
        done += 1
        for f in d.glob('*.json'):
            if f.name == 'summary.json':
                continue
            turns = load(f).get('turns') or {}
            for t in (turns.values() if isinstance(turns, dict) else turns):
                if t.get('truncated'):
                    bad.append(f'{d.name}: a truncated answer')
                rt = ((t.get('provider_usage') or {}).get('completion_tokens_details') or {}).get('reasoning_tokens')
                if isinstance(rt, int) and rt > 0 and not dry:
                    bad.append(f'{d.name}: reasoning tokens in an OFF answer')
    report = {'model': key, 'round': rnd, 'expected': len(grid(rnd)), 'completed': done, 'problems': bad}
    save(priv(key) / f'audit_{rnd}.json', report)
    print(f'{key}: {done}/{len(grid(rnd))} conversations complete, {len(bad)} problems')
    return report


def export(key, rnd):
    dirs = [str(out_dir(rnd) / tag(key, *g)) for g in grid(rnd) if (out_dir(rnd) / tag(key, *g) / 'summary.json').exists()]
    tmp = priv(key) / f'export_{rnd}'
    if tmp.exists():
        shutil.rmtree(tmp)
    listing = priv(key) / f'export_dirs_{rnd}.json'
    save(listing, dirs)
    code = ("import json, runpy, sys; dirs = json.load(open(sys.argv[1], encoding='utf-8')); "
            "sys.argv = ['experiments/preview_icl_expanded.py', '--summarize', *dirs, '--out', sys.argv[2]]; "
            "runpy.run_path('experiments/preview_icl_expanded.py', run_name='__main__')")
    sh([sys.executable, '-B', '-c', code, listing, tmp], cwd=ROOT, env=env_for(rnd))
    dest = RUNS / rnd / 'icl_export' / key
    dest.mkdir(parents=True, exist_ok=True)
    for name in ('metrics', 'request_usage'):
        with open(tmp / f'{name}.csv', 'rb') as src, gzip.open(dest / f'{name}.csv.gz', 'wb') as gz:
            shutil.copyfileobj(src, gz)
    print(f'{key}: export in {dest}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('step', choices=['config', 'preflight', 'ready', 'jobs', 'run', 'audit', 'export', 'all'])
    ap.add_argument('--model', required=True, choices=sorted(MODELS))
    ap.add_argument('--round', default='exploratory')
    ap.add_argument('--workers', type=int, default=16)
    ap.add_argument('--yes', action='store_true')
    ap.add_argument('--dry', action='store_true', help='dry-run provider, no configs, no network')
    a = ap.parse_args()
    k = a.model
    if a.step == 'config': config(k)
    elif a.step == 'preflight': preflight(k, a.yes)
    elif a.step == 'ready':
        if not all(validated(k, h).exists() for h in HIST):
            config(k)                                    # always fresh until validated: no stale candidate is reused
            preflight(k, a.yes)
        print(f'{k}: ready')
    elif a.step == 'jobs': jobs(k, a.round, a.dry)
    elif a.step == 'run': sys.exit(run(k, a.round, a.workers, a.dry))
    elif a.step == 'audit': sys.exit(1 if audit(k, a.round, a.dry)['problems'] else 0)
    elif a.step == 'export': export(k, a.round)
    else:
        if not a.dry:
            if not all(validated(k, h).exists() for h in HIST):
                config(k)
                preflight(k, a.yes)
        jobs(k, a.round, a.dry)
        run(k, a.round, a.workers, a.dry)
        rep = audit(k, a.round, a.dry)
        export(k, a.round)
        sys.exit(1 if rep['problems'] else 0)


if __name__ == '__main__':
    main()

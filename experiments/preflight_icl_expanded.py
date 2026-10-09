"""Prepare one fixed 16K control request; generation requires explicit --execute."""

import argparse
import copy
import json
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import icl_expanded as design
import icl_model_first_runner as runner
from experiments.preview_icl_model_first import save


def prepare(wrapper):
    config, spec = wrapper['deployment'], wrapper['expanded']
    if (set(wrapper) != {'deployment', 'expanded'}
            or spec.get('protocol') != design.PROTOCOL
            or spec.get('preparation_policy') != design.PREPARATION_POLICY
            or spec.get('schedule') != design.SCHEDULE
            or spec.get('output_allowances') != [design.NEW_CAP]):
        raise ValueError('current expanded 16K wrapper required')
    design.pilot_design.check_history_policy(spec['history_policy'])
    for key in ('stage_limits_source', 'system_message_source', 'context_source'):
        if not isinstance(spec.get(key), str) or not spec[key].strip():
            raise ValueError('missing stage/system/context provenance')
    profile, mode = config['profile'], spec['reasoning_mode']
    if profile not in ('sol', 'deepseek_openrouter'):
        raise ValueError('this hosted preflight entry supports Sol and OpenRouter only')
    body = design.controls.deployment_preflight_request(config, profile, mode,
                                                        preflight_output_tokens=design.NEW_CAP)
    if profile in design.controls.EXPANDED_HOSTED_PROFILES and (
            any(config['pricing'].get(k) is None for k in ('input_per_million', 'output_per_million'))
            or not config['pricing'].get('source')):
        raise ValueError('verified prices required before a paid preflight')
    count = runner.context_check(body, config, design.NEW_CAP)
    if not count['fits']:
        raise ValueError('preflight context cannot fit')
    bound = count.get('input_tokens', count.get('input_tokens_upper_bound', count.get('input_token_units_estimate')))
    ceiling = runner.cost({'prompt_tokens': bound, 'completion_tokens': design.NEW_CAP}, config, profile)
    if design.controls.estimated_context(config):
        ceiling['assumption'] = 'conditional on the engineering input estimate; not a hard charge ceiling; returned usage can exceed it before the stop'
    return body, count, ceiling


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--config', required=True)
    ap.add_argument('--out', required=True, help='unused private evidence directory outside Git')
    ap.add_argument('--execute', action='store_true', help='one separately authorized generation; never retries')
    ap.add_argument('--timeout', type=int, default=900)
    args = ap.parse_args()
    wrapper = json.loads(Path(args.config).read_text())
    body, count, ceiling = prepare(wrapper)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    save(out / 'request.json', body)
    save(out / 'context.json', count)
    save(out / 'cost_ceiling.json', ceiling)
    if not args.execute:
        print('Prepared only. No generation; not deployment readiness.')
        return
    config, spec = wrapper['deployment'], wrapper['expanded']
    try:
        status, raw = runner.call_provider(body, config, args.timeout)
    except urllib.error.HTTPError as exc:
        status, raw = exc.code, exc.read().decode('utf-8', errors='replace')
    except Exception as exc:
        save(out / 'failure.json', {'type': type(exc).__name__, 'network_retries': []})
        raise RuntimeError('preflight transport failed; saved failure type; no retry') from None
    design.controls.no_secrets(raw)
    save(out / 'response_raw.txt', raw)
    save(out / 'transport.json', {'http_status': status, 'network_retries': []})
    response = json.loads(raw)
    completed = copy.deepcopy(wrapper)
    completed['deployment']['preflight'] = dict(request=body, response=response,
        http_status=status, network_retries=[], source='Saved request.json, response_raw.txt and transport.json',
        response_raw=raw, response_raw_sha256=design.pilot_design.digest(raw))
    design.validate_config(completed, config['profile'], spec['reasoning_mode'],
                           spec['history_policy'], design.NEW_CAP)
    save(out / 'validated_wrapper.json', completed)
    print('Preflight accepted, not a long-conversation or pilot validation. No experiment launched.')


if __name__ == '__main__':
    main()

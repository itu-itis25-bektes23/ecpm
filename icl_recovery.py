"""Opt-in exploratory execution amendment; historical acceptance is unchanged."""
import copy
import hashlib
import json
import signal
import time
import urllib.error
from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

POLICY = 'icl_bounded_recovery_v1'
TRANSIENT = (408, 429, 500, 502, 503, 504)


def specification():
    return dict(version=POLICY, initial_output_tokens=32768, truncation_output_tokens=65536,
        max_length_repeats=1, max_transient_retries=2, max_http_attempts_per_stage=4,
        timeout_seconds=1800, max_backoff_seconds=120,
        reasoning_acceptance='request_defined_observed_usage_separate',
        usage_quality='inconsistent_subcounts_flagged_not_normalized',
        disclosure='exploratory amendment motivated by pilot failures',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())


def enabled(wrapper):
    return bool(wrapper and wrapper.get('expanded', {}).get('operational_policy'))


class Stop(RuntimeError):
    def __init__(self, reason, pause=False):
        self.reason, self.pause = reason, pause
        super().__init__(reason)


@contextmanager
def deadline(seconds):
    """Serial POSIX launcher: bound the whole HTTP attempt, not each socket read."""
    if signal.getitimer(signal.ITIMER_REAL)[0]: raise Stop('existing_alarm_conflict',True)
    previous=signal.getsignal(signal.SIGALRM)
    def expired(*_): raise TimeoutError('HTTP wall-clock deadline')
    signal.signal(signal.SIGALRM,expired)
    signal.setitimer(signal.ITIMER_REAL,seconds)
    try: yield
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        signal.signal(signal.SIGALRM,previous)


def observations(data, config, profile, mode):
    import icl_graph as controls
    check = controls.reasoning_check(data, mode, config['effective'], profile, config)
    usage = data.get('usage', {})
    raw = check['reasoning_tokens']; total = usage.get('completion_tokens')
    valid = type(raw) is int and raw >= 0 and type(total) is int and 0 <= raw <= total
    # Raw values and historical mode_verified are retained independently.
    return {'requested_mode':mode, 'acceptance_policy':POLICY,
        'request_condition_accepted':bool(controls.hosted_semantics(config, mode)) and not check['control_violation'],
        'observed_reasoning_tokens':raw, 'observed_reasoning_evidence':check['evidence'],
        'derived_reasoning_tokens':raw if valid else None,
        'derived_final_tokens':total - raw if valid else None,
        'usage_quality':'unknown_reasoning_count' if raw is None else 'consistent' if valid else 'inconsistent_subcounts'}


def classify(t):
    """Classify independently of parsing or scientific score."""
    if t.get('exception_type'):
        kind=t.get('network_cause_type') if t['exception_type']=='URLError' else t['exception_type']
        return 'transient' if kind in ('TimeoutError','ConnectionError','RemoteDisconnected',
            'ConnectionResetError','ConnectionAbortedError','ConnectionRefusedError','BrokenPipeError','IncompleteRead') else 'exception'
    status = t.get('http_status')
    if status in (401,402,403): return 'authentication_payment'
    if status in TRANSIENT: return 'transient'
    if status != 200: return 'http_error'
    c = t.get('operational_checks', {})
    if not c.get('raw_envelope') or not c.get('copied_fields'): return 'evidence_corruption'
    if not c.get('controls'): return 'identity_control'
    if 'I have to answer now.' in (t.get('provider_reasoning') or ''): return 'identity_control'
    if not c.get('context'): return 'context'
    if t.get('provider_finish_reason') == 'length' or t.get('native_finish_reason') in ('length','max_tokens'):
        return 'length'
    if all(c.values()): return 'accepted'
    if not isinstance(t.get('raw_response'),str) or not t['raw_response'].strip() or t.get('provider_finish_reason')!='stop':
        return 'content_finish'
    return 'usage_failure'


def delay(attempt):
    value = attempt.get('retry_after')
    seconds = 2 ** attempt['ordinal']
    if value is not None:
        try: seconds = max(seconds, float(value))
        except ValueError:
            try: seconds = max(seconds, (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
            except (ValueError, TypeError): raise Stop('invalid_retry_after', True)
    if seconds > 120: raise Stop('retry_after_exceeds_bounded_wait', True)
    return max(0, seconds)


def fill_response(t, config, mode):
    import icl_model_first_runner as r
    data = json.loads(t['provider_response_raw'])
    t.update(provider_response=data, provider_response_sha256=r.canonical(data),
        **r.copied_fields(data, config, config['profile'], False, mode))
    if isinstance(t['raw_response'], str): t['response_sha256'] = r.design.digest(t['raw_response'])
    t['reasoning_acceptance'] = observations(data, config, config['profile'], mode)
    if r.controls.estimated_context(config):
        t['prompt_usage_check'] = r.controls.estimate_usage_check(t['context_check'], t['provider_usage'])
    t['operational_checks'] = r.response_checks(t, t['request_body'], config, config['profile'],
        t['max_output_tokens'], reasoning_mode=mode, operational_policy=POLICY)


def stage(turn, artifact, name, path, config, mode, coordinator, caller=None, sleeper=time.sleep):
    import icl_model_first_runner as r
    caller = caller or r.call_provider
    if coordinator is None: raise Stop('durable_budget_coordinator_required', True)
    attempts = turn['attempts'] = []
    body = copy.deepcopy(turn['request_body']); cap = 32768; transient = 0; increased = False
    for number in range(1, 5):
        key = 'max_completion_tokens' if config['profile'] == 'sol' else 'max_tokens'
        body[key] = cap
        count = r.context_check(body, config, cap)
        if not count['fits']: raise Stop('context')
        t = dict(ordinal=number, max_output_tokens=cap, timeout_seconds=1800,
            request_body=copy.deepcopy(body), request_sha256=r.canonical(body),
            context_check=count, network_retries=[], phase='prepared')
        attempts.append(t); r.persist(path, artifact, name + ':attempt_prepared')
        reservation = coordinator.reserve(name, number, t)
        t.update(reservation_id=reservation, phase='dispatched')
        r.persist(path, artifact, name + ':attempt_dispatched')
        began = time.monotonic()
        try:
            with deadline(1800):
                try:
                    status, raw = caller(body, config, 1800)
                except urllib.error.HTTPError as exc:
                    t.update(http_status=exc.code, retry_after=exc.headers.get('Retry-After') if exc.headers else None)
                    status, raw = exc.code, exc.read().decode('utf-8', errors='replace')
            t.update(http_status=status, provider_response_raw=raw,
                     provider_response_raw_sha256=r.design.digest(raw))
        except Exception as exc:
            # Exception messages can contain credentials/URLs, so retain type only.
            t['exception_type'] = type(exc).__name__
            if isinstance(exc,urllib.error.URLError): t['network_cause_type']=type(exc.reason).__name__
        t.update(elapsed_s=time.monotonic()-began, phase='returned')
        r.persist(path, artifact, name + ':attempt_raw_saved')
        coordinator.settle(reservation, t)
        if 'provider_response_raw' in t:
            r.controls.no_secrets(t['provider_response_raw'])
            if t.get('http_status') == 200:
                try: fill_response(t, config, mode)
                except (ValueError, TypeError, KeyError, IndexError, AttributeError):
                    t['operational_checks'] = {'raw_envelope':False}
        reason = classify(t); t['outcome'] = reason
        r.persist(path, artifact, name + ':attempt_classified')
        if reason == 'accepted':
            turn.update({k:copy.deepcopy(v) for k,v in t.items() if k not in ('ordinal','phase','outcome')})
            turn['selected_attempt'] = number
            return t['http_status'], t['provider_response_raw']
        if reason == 'length' and not increased and number < 4:
            increased = True; cap = 65536
            continue
        if reason == 'transient' and transient < 2 and number < 4:
            transient += 1
            wait = delay(t); t['backoff_seconds'] = wait
            r.persist(path, artifact, name + ':backoff_saved')
            sleeper(wait)
            continue
        raise Stop(reason, reason in ('authentication_payment','identity_control','evidence_corruption'))
    raise Stop('attempts_exhausted')


def audit_attempts(turn, config, mode, base_body):
    import icl_model_first_runner as r
    attempts = turn.get('attempts', []); cap = 32768; transient = 0; increased = False
    if not 1 <= len(attempts) <= 4 or turn.get('selected_attempt') != len(attempts): return False
    for number,t in enumerate(attempts,1):
        body = copy.deepcopy(base_body)
        body['max_completion_tokens' if config['profile']=='sol' else 'max_tokens'] = cap
        if (t.get('ordinal') != number or t.get('max_output_tokens') != cap
                or t.get('request_body') != body or t.get('request_sha256') != r.canonical(body)
                or t.get('timeout_seconds') != 1800 or t.get('phase') != 'returned'
                or not t.get('reservation_id') or t.get('network_retries') != []
                or t.get('context_check') != r.context_check(body,config,cap) or not t['context_check']['fits']): return False
        if 'provider_response_raw' in t:
            if t['provider_response_raw_sha256'] != r.design.digest(t['provider_response_raw']): return False
        if t.get('http_status') == 200:
            actual = r.response_checks(t,body,config,config['profile'],cap,reasoning_mode=mode,operational_policy=POLICY)
            if actual != t.get('operational_checks'): return False
        reason=classify(t)
        if reason != t.get('outcome'): return False
        if reason == 'accepted':
            return number == len(attempts) and all(turn.get(k)==t.get(k) for k in
                ('request_body','request_sha256','max_output_tokens','context_check','provider_response_raw',
                 'reasoning_acceptance','reservation_id'))
        if reason == 'length' and not increased:
            increased=True; cap=65536
        elif reason == 'transient' and transient < 2:
            transient+=1
            if not 0 <= t.get('backoff_seconds',-1) <= 120: return False
        else: return False
    return False

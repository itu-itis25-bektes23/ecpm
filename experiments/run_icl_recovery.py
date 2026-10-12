"""Serial, durable recovery of a verified private 660-cell ICL batch. Stdlib only."""
import argparse
import copy
import csv
from decimal import Decimal
import fcntl
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import icl_expanded as design
import icl_model_first_runner as runner
import icl_recovery as recovery
from experiments import preview_icl_expanded as report

BASE = 'a3e32493ad8a10e960a5b5abff3434053e020cb9'
MODEL = 'deepseek/deepseek-v4.1-flash'


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text())


def save(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    with tmp.open('w') as f:
        f.write(value if isinstance(value, str) else json.dumps(value, indent=2) + '\n')
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)


def money(v):
    if type(v) not in (str,int,float,Decimal): raise ValueError('unknown monetary value')
    d = Decimal(str(v))
    if not d.is_finite() or d < 0: raise ValueError('invalid monetary value')
    return d


def reported_charge(t):
    try:
        raw = t['provider_response_raw']
        if runner.design.digest(raw) != t['provider_response_raw_sha256']: raise ValueError('raw hash')
        value=json.loads(raw,parse_float=Decimal)['usage']['cost']
        return None if value is None else money(value)
    except (KeyError,TypeError,json.JSONDecodeError): return None


def exposure(ledger):
    return money(ledger['carried_exposure_usd']) + sum((money(r['reported_cost_usd'])
        if r.get('reported_cost_usd') is not None else money(r['reserved_usd'])
        for r in ledger['requests'].values()), Decimal(0))


class Coordinator:
    """One process and one conversation at a time; fsync before each dispatch."""
    def __init__(self, state, ledger, attempt_id, quote):
        self.state, self.ledger, self.attempt_id, self.quote = state, ledger, attempt_id, quote

    def reserve(self, stage, number, request):
        key = f'{self.attempt_id}/{stage}/{number}'
        if key in self.ledger['requests']: raise recovery.Stop('duplicate_request',True)
        cap = request['max_output_tokens']
        ceiling = ((1048576-cap)*money(self.quote['input_per_token_usd'])
                   + cap*money(self.quote['output_per_token_usd']))
        if exposure(self.ledger) + ceiling > money(self.ledger['budget_usd']):
            raise recovery.Stop('budget_exhausted',True)
        self.ledger['requests'][key] = dict(status='inflight', reserved_usd=str(ceiling),
            reported_cost_usd=None, stage=stage, ordinal=number, attempt_id=self.attempt_id,
            request_sha256=request['request_sha256'], max_output_tokens=cap,
            started_unix=time.time(), quote=self.quote)
        save(self.state/'ledger.json',self.ledger)
        return key

    def settle(self, key, request):
        entry = self.ledger['requests'][key]
        charge = reported_charge(request)
        entry.update(status='accounted' if charge is not None else 'unknown_charge',
            reported_cost_usd=str(charge) if charge is not None else None,
            response_raw_sha256=request.get('provider_response_raw_sha256'),
            http_status=request.get('http_status'), exception_type=request.get('exception_type'))
        save(self.state/'ledger.json',self.ledger)
        if charge is not None and charge > money(entry['reserved_usd']):
            raise recovery.Stop('charge_exceeded_reservation',True)


def snapshot(root):
    return {str(p.relative_to(root)):digest(p) for p in sorted(root.rglob('*'))
        if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith('.lock')}


def old_module(root):
    spec=importlib.util.spec_from_file_location('original_batch_readonly',root/'run_batch.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def match_cell(a, row):
    expected = dict(graph_seed=row['graph_seed'], mode=row['mode'], scenario=row['scenario'],
        condition=row['arm'], history_policy=row['history_policy'], reasoning_mode=row['reasoning_mode'],
        repeat=1, repeat_seed_label=0, model=MODEL, profile='deepseek_openrouter')
    if any(a['identity'].get(k)!=v for k,v in expected.items()): raise ValueError('cell identity mismatch')


def audit_old(path, row, wrapper, complete=True):
    a=read(path); match_cell(a,row)
    if (a['identity']['implementation_commit']!=BASE or a['deployment']!=wrapper
            or design.artifact_allowance(a['identity'])!=16384 or not design.audit_identity(a)):
        raise ValueError('historical source/config/cap mismatch')
    if complete and not all(runner.audit_artifact(a,design).values()): raise ValueError('historical audit failed')
    return a


def migrate(old, state, manifest, original):
    """Originals are read-only. Reconcile only a fully journalled known charge."""
    hashes=snapshot(old)
    ledger=read(old/'results/ledger.json'); rows={r['cell_id']:r for r in manifest['rows']}
    if money(ledger['budget_usd'])!=20: raise ValueError('expected cumulative $20 authorization')
    if original.exposure(ledger)!=Decimal('0.73168876'): raise ValueError('old exposure changed; inspect before migration')
    if len(ledger['cells'])!=2: raise ValueError('unexpected historical inventory')
    cells={}; prior_attempts=[]; carry=Decimal(0)
    for cell,row in rows.items():
        wrapper=read(old/row['configuration'])
        if row.get('pilot_artifact'):
            path=old/row['pilot_artifact']; a=audit_old(path,row,wrapper)
            cells[cell]=dict(status='historical_completed',artifact=str(path),sha256=digest(path),
                actual_cap=16384,policy='historical',charged_to_this_batch=False)
        elif cell in ledger['cells']:
            entry=ledger['cells'][cell]
            paths=list((old/'results/artifacts'/cell).glob('icl_expanded_v2_*.json'))
            if len(paths)!=1: raise ValueError('ambiguous old artifact')
            path=paths[0]; complete=entry['status']=='completed'; a=audit_old(path,row,wrapper,complete)
            charges=[reported_charge(t) for t in a['turns'].values() if 'provider_response_raw' in t]
            known=all(v is not None for v in charges)
            if complete:
                if len(charges)!=6 or not known or sum(charges)!=money(entry['reported_cost_usd']): raise ValueError('completed charge mismatch')
                carry+=sum(charges)
                cells[cell]=dict(status='historical_completed',artifact=str(path),sha256=digest(path),actual_cap=16384,
                    policy='historical',charged_to_this_batch=True)
            else:
                if cell!='deepseek_separate_sto_no_change_s8_model_first_on': raise ValueError('unexpected old failure')
                journal=old/'results/attempts'/cell
                events=a['persistence_events']
                names=['A_prepare','A_task','A_readout','B_prepare','B_task']
                proof=(entry['status']=='failed' and read(journal/'exit.json')['returncode']==1
                    and a['state']=='incomplete' and a['failure']['stage']=='B_task'
                    and a['run_order']==names and set(a['turns'])==set(names) and len(charges)==5 and known
                    and sum(charges)==Decimal('0.05605758')
                    and events.count('operational_failure')==1
                    and all(events.count(n+':provider_raw_saved')==1 and events.count(n+':request_saved')==1 for n in names)
                    and all(not t.get('network_retries') and t.get('http_status')==200 for t in a['turns'].values()))
                for name,t in a['turns'].items():
                    checks=runner.response_checks(t,t['request_body'],wrapper['deployment'],'deepseek_openrouter',16384,reasoning_mode='on')
                    proof &= all(v for k,v in checks.items() if name!='B_task' or k!='transport')
                argv=read(journal/'argv.json')
                for flag,value in {'--protocol':'icl_expanded_v2','--seed':'8','--mode':'sto',
                        '--condition':'no_change','--reasoning-mode':'on','--max-tokens':'16384',
                        '--tag':cell,'--repeats':'1','--sampling-seeds':'0'}.items():
                    proof &= argv.count(flag)==1 and argv[argv.index(flag)+1]==value
                flow=runner.requests(a['world'],row['arm'],row['history_policy'],design,16384)
                call=next(flow)
                for name in names:
                    t=a['turns'][name]
                    proof &= call['id']==name and call['messages']==t['request_body']['messages']
                    if name!='B_task': call=flow.send(t['raw_response'])
                carry+=sum(charges) if proof else money(entry['reserved_usd'])
                prior_attempts.append(dict(cell_id=cell,attempt_id='historical_attempt_0',artifact=str(path),sha256=digest(path),
                    journal=str(journal),actual_cap=16384,reported_cost_usd=str(sum(charges)) if known else None,
                    reservation_reconciled=bool(proof),exposure_usd=str(sum(charges) if proof else money(entry['reserved_usd']))))
                cells[cell]=dict(status='pending',historical_failure='historical_attempt_0')
        else: cells[cell]={'status':'pending'}
    if sum(c['status']=='historical_completed' for c in cells.values())!=3: raise ValueError('expected three historical completions')
    new=dict(version=recovery.POLICY,budget_usd='20',carried_exposure_usd=str(carry),cells=cells,requests={},attempts={},
        authorization='Existing cumulative $20 batch authorization, not a fresh budget',historical_attempts=prior_attempts,
        systemic_streak=0,last_systemic_reason=None)
    save(state/'original_ledger.json',ledger)
    save(state/'migration.json',dict(old_root=str(old),old_file_hashes=hashes,old_manifest_sha256=digest(old/'batch_manifest.json'),
        old_exposure_usd=str(original.exposure(ledger)),carried_exposure_usd=str(carry),
        basis='Raw provider reported charges plus retained unknown reservations, not invoice reconciliation',
        historical_completed=3,fresh_recovery_cells=1,untouched_cells=656,prior_attempts=prior_attempts))
    save(state/'ledger.json',new)
    return new


def wrapper_for(old, row):
    w=read(old/row['configuration']); w['expanded'].update(output_allowances=[32768],
        control_preflight_output_tokens=16384,operational_policy=recovery.specification())
    w['expanded']['stage_limits_source']='Exploratory bounded recovery: initial 32768, one same-stage length retry at 65536; original 16384 control preflight retained unchanged.'
    w['expanded']['context_source']='Same engineering estimate, complete actual history, reserve each actual attempt cap; unknown hosted overhead remains unknown.'
    w['deployment']['context']['source']=w['deployment']['context']['source'].replace('plus 16384 output','plus the actual requested output allowance')
    design.validate_config(w,'deepseek_openrouter',row['reasoning_mode'],row['history_policy'],32768)
    return w


def verify_repo(repo, commit):
    def git(*a): return subprocess.check_output(['git',*a],cwd=repo,text=True).strip()
    if len(commit)!=40 or git('rev-parse','HEAD')!=commit or git('status','--porcelain'):
        raise ValueError('clean exact recovery commit required')
    subprocess.run(['git','merge-base','--is-ancestor',BASE,commit],cwd=repo,check=True)


def csv_text(rows):
    stream=io.StringIO(); fields=list(dict.fromkeys(k for r in rows for k in r))
    writer=csv.DictWriter(stream,fieldnames=fields); writer.writeheader()
    writer.writerows({k:json.dumps(v) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows)
    return stream.getvalue()


def export(state, ledger, rows):
    coverage=[]; requests=[]; attempts=[]; scores=[]
    for row in rows:
        entry=ledger['cells'][row['cell_id']]
        coverage.append(dict(row,**{k:v for k,v in entry.items() if k not in row},
            planned_initial_cap=32768 if entry['status']!='historical_completed' else 16384,
            scientific_score_available=entry['status'] in ('completed','historical_completed')))
        coverage[-1]['output_tokens']=entry.get('actual_cap',32768)
        coverage[-1]['historical_manifest_output_tokens']=row['output_tokens']
        coverage[-1]['first_conversation_attempt_completed']=(entry['status']=='historical_completed' or
            (entry['status']=='completed' and not entry.get('historical_failure')))
        if entry['status'] in ('completed','historical_completed'):
            a=read(entry['artifact'])
            scores.append(dict(cell_id=row['cell_id'],run_id=a['run_id'],source_commit=a['identity']['implementation_commit'],
                policy=a['identity'].get('operational_policy','historical_fixed_16k'),artifact=entry['artifact'],
                artifact_sha256=digest(entry['artifact']),scores=a['scores']))
    historical=[dict(cell_id=cell,artifact=e['artifact'],attempt_id=cell+'__historical_0',status='completed')
        for cell,e in ledger['cells'].items() if e['status']=='historical_completed']
    historical += [dict(a,status='incomplete') for a in ledger['historical_attempts']]
    for entry in historical:
        a=read(entry['artifact'])
        attempts.append(dict(entry,policy='historical_fixed_16k',source_commit=a['identity']['implementation_commit']))
        for stage,t in a['turns'].items():
            if 'provider_response_raw' not in t: continue
            requests.append(dict(cell_id=entry['cell_id'],attempt_id=entry['attempt_id'],stage=stage,ordinal=1,
                policy='historical_fixed_16k',source_commit=a['identity']['implementation_commit'],max_tokens=t['max_output_tokens'],
                requested_controls=t['request_body'].get('reasoning'),historical_control_check=t.get('control_check'),
                usage_raw=t.get('provider_usage'),finish_reason=t.get('provider_finish_reason'),
                http_status=t.get('http_status'),raw_sha256=t.get('provider_response_raw_sha256'),
                artifact=entry['artifact'],charged_to_this_batch=ledger['cells'][entry['cell_id']].get('charged_to_this_batch',True)))
    for attempt_id,entry in ledger['attempts'].items():
        attempts.append(dict(attempt_id=attempt_id,**entry))
        paths=list((state/'artifacts'/attempt_id).glob('icl_expanded_v2_*.json'))
        if len(paths)!=1: continue
        a=read(paths[0])
        for stage,t in a['turns'].items():
            for q in t.get('attempts',[]):
                raw=q.get('provider_response',{}); usage=raw.get('usage',{})
                requests.append(dict(cell_id=entry['cell_id'],attempt_id=attempt_id,stage=stage,ordinal=q['ordinal'],
                    policy=recovery.POLICY,source_commit=a['identity']['implementation_commit'],max_tokens=q['max_output_tokens'],
                    requested_controls=q['request_body'].get('reasoning'),reasoning=q.get('reasoning_acceptance'),
                    usage_raw=usage,finish_reason=q.get('provider_finish_reason'),outcome=q.get('outcome'),
                    http_status=q.get('http_status'),exception_type=q.get('exception_type'),
                    request_sha256=q['request_sha256'],raw_sha256=q.get('provider_response_raw_sha256'),
                    ledger=ledger['requests'].get(q.get('reservation_id'))))
    for name,data in [('coverage',coverage),('attempts',attempts),('requests',requests)]:
        save(state/(name+'.json'),data); save(state/(name+'.csv'),csv_text(data))
    save(state/'saved_scientific_scores.json',dict(completed_records=scores,
        planned_cells=len(rows),unscored_cell_ids=[r['cell_id'] for r in coverage if not r['scientific_score_available']],
        note='Saved scores and their denominators only. No reparsing or rescoring. Historical and adaptive policy cohorts remain separate.'))
    save(state/'progress.json',dict(planned=len(rows),counts={s:sum(c['status']==s for c in ledger['cells'].values())
        for s in sorted({c['status'] for c in ledger['cells'].values()})},
        total_exposure_usd=str(exposure(ledger)),remaining_usd=str(money(ledger['budget_usd'])-exposure(ledger)),
        policy=recovery.POLICY,workers=1,paused_reason=ledger.get('paused_reason')))


def recover_crash(ledger):
    for c in ledger['cells'].values():
        if c['status']=='inflight': c['status']='uncertain'
    for a in ledger['attempts'].values():
        if a['status']=='inflight': a['status']='uncertain'
    for r in ledger['requests'].values():
        if r['status']=='inflight': r['status']='unknown_charge'


def validate_accounting(state, ledger):
    migration=read(state/'migration.json')
    if money(ledger['budget_usd'])!=20 or ledger['carried_exposure_usd']!=migration['carried_exposure_usd']:
        raise ValueError('cumulative authorization or migration exposure changed')
    found=set()
    for attempt_id,entry in ledger['attempts'].items():
        for path in (state/'artifacts'/attempt_id).glob('icl_expanded_v2_*.json'):
            a=read(path)
            for stage,t in a['turns'].items():
                for q in t.get('attempts',[]):
                    key=q.get('reservation_id')
                    if key is None: continue  # Crash before durable dispatch record.
                    if key in found or key not in ledger['requests']: raise ValueError('duplicate/missing reservation evidence')
                    found.add(key); r=ledger['requests'][key]
                    if (r['attempt_id']!=attempt_id or r['stage']!=stage or r['ordinal']!=q['ordinal']
                            or r['request_sha256']!=q['request_sha256'] or r['max_output_tokens']!=q['max_output_tokens']):
                        raise ValueError('request reservation identity mismatch')
                    quote=r['quote']; cap=r['max_output_tokens']
                    expected=(1048576-cap)*money(quote['input_per_token_usd'])+cap*money(quote['output_per_token_usd'])
                    if money(r['reserved_usd'])!=expected: raise ValueError('reservation ceiling changed')
                    if r.get('reported_cost_usd') is not None:
                        cost=reported_charge(q)
                        if cost is None or money(r['reported_cost_usd'])!=cost:
                            raise ValueError('ledger charge differs from raw response')
    for key,r in ledger['requests'].items():
        if key not in found and r.get('reported_cost_usd') is not None:
            raise ValueError('known charge without persisted response evidence')
    if exposure(ledger)>20: raise ValueError('cumulative exposure exceeds authorization')


def bind_ledger(registry, state, source):
    """Do not allow another state directory to restart the cumulative budget."""
    identity={'state':str(state),'source':str(source),'budget_usd':'20'}
    if registry.exists():
        if read(registry)!=identity or not (state/'ledger.json').exists():
            raise ValueError('budget already bound elsewhere or migration interrupted; investigate without resetting')
    else:
        save(registry,identity)


def finish_status(ledger, reason, pause):
    if reason in ('length','content_finish',None):
        ledger.update(systemic_streak=0,last_systemic_reason=None)
    else:
        ledger['systemic_streak']=ledger['systemic_streak']+1 if ledger['last_systemic_reason']==reason else 1
        ledger['last_systemic_reason']=reason
        pause |= ledger['systemic_streak']>=3
    if pause: ledger['paused_reason']=reason
    return pause


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--old-package',required=True,type=Path); ap.add_argument('--state',required=True,type=Path)
    ap.add_argument('--expected-commit',required=True); ap.add_argument('--execute',action='store_true')
    ap.add_argument('--max-new-cells',type=int); args=ap.parse_args()
    os.umask(0o077)
    repo=Path(__file__).resolve().parents[1]; os.chdir(repo)
    verify_repo(repo,args.expected_commit)
    old,state=args.old_package.resolve(),args.state.resolve()
    if state.is_relative_to(old) or state.is_relative_to(repo): raise ValueError('new state must be outside old package and Git')
    original=old_module(old); manifest=original.verify_package(old); rows=manifest['rows']
    state.mkdir(parents=True,exist_ok=True)
    with (state/'process.lock').open('a') as lock, (old/'results/process.lock').open('r') as old_lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB); fcntl.flock(old_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        bind_ledger(old.parent/(old.name+'.recovery-ledger.json'),state,old)
        marker=dict(commit=args.expected_commit,policy=recovery.specification(),old_package=str(old))
        if (state/'identity.json').exists():
            if read(state/'identity.json')!=marker: raise ValueError('recovery identity changed')
        else: save(state/'identity.json',marker)
        ledger=read(state/'ledger.json') if (state/'ledger.json').exists() else migrate(old,state,manifest,original)
        if read(state/'migration.json')['old_file_hashes']!=snapshot(old): raise ValueError('historical evidence changed')
        recover_crash(ledger); save(state/'ledger.json',ledger)
        validate_accounting(state,ledger)
        for row in rows:
            e=ledger['cells'][row['cell_id']]
            if e['status'] in ('completed','historical_completed'):
                if digest(e['artifact'])!=e['sha256'] or not all(runner.audit_artifact(read(e['artifact']),design).values()):
                    raise ValueError('completed artifact changed or audit failed')
                match_cell(read(e['artifact']),row)
        configs={row['configuration']:row for row in rows}
        for name,row in configs.items():
            path=state/'configurations'/Path(name).name; expected=wrapper_for(old,row)
            if path.exists() and read(path)!=expected: raise ValueError('derived configuration changed')
            if not path.exists(): save(path,expected)
        export(state,ledger,rows)
        print(json.dumps(read(state/'progress.json')),flush=True)
        if not args.execute:
            print('Prepared offline. No pricing, authentication or generation requests.'); return
        if not os.environ.get('OPENROUTER_API_KEY'): raise ValueError('export OPENROUTER_API_KEY privately first')
        if ledger.get('paused_reason') not in (None,'budget_exhausted'):
            raise ValueError('Paused for investigation: '+ledger['paused_reason'])
        count=0
        for row in rows:
            cell=row['cell_id']; entry=ledger['cells'][cell]
            if entry['status']!='pending': continue
            if (state/'STOP').exists() or (args.max_new_cells is not None and count>=args.max_new_cells): break
            verify_repo(repo,args.expected_commit)
            if read(state/'migration.json')['old_file_hashes']!=snapshot(old): raise ValueError('old evidence changed')
            # Public metadata only, with no credentials and no automatic retry.
            with urllib.request.urlopen(original.URL,timeout=30) as response: metadata=json.load(response)
            quote=original.price_quote(metadata)
            endpoint=next(e for e in metadata['data']['endpoints'] if e['tag']=='ionstream')
            if endpoint['max_completion_tokens']<65536: raise ValueError('64K capacity unavailable')
            w=wrapper_for(old,row)
            # Also check all published tier prices against the pinned readiness rates.
            if (money(quote['input_per_token_usd'])*1000000 > money(w['deployment']['pricing']['input_per_million'])
                    or money(quote['output_per_token_usd'])*1000000 > money(w['deployment']['pricing']['output_per_million'])):
                raise ValueError('prices exceed readiness rates')
            attempt_id=cell+'__recovery_1'
            output=state/'artifacts'/attempt_id
            if output.exists() or attempt_id in ledger['attempts']: raise ValueError('duplicate/unrecorded recovery attempt')
            output.mkdir(parents=True,exist_ok=False)
            journal=state/'attempts'/attempt_id
            save(journal/'public_endpoints.json',metadata); save(journal/'configuration.json',w)
            args_run=report.arguments(row['arm'],row['reasoning_mode'],row['history_policy'],'deepseek_openrouter',32768)
            args_run.provider='openai'; args_run.model=MODEL; args_run.timeout=1800
            args_run.recovery_coordinator=Coordinator(state,ledger,attempt_id,quote)
            save(journal/'launch.json',dict(cell=row,commit=args.expected_commit,policy=recovery.specification(),
                invocation='icl_model_first_runner.run_once',configuration_sha256=runner.canonical(w)))
            entry.update(status='inflight',attempt_id=attempt_id,policy=recovery.POLICY,actual_cap='adaptive_32768_65536')
            ledger['attempts'][attempt_id]=dict(cell_id=cell,status='inflight',source_commit=args.expected_commit,policy=recovery.POLICY)
            save(state/'ledger.json',ledger); reason=None; pause=False
            print('Running '+attempt_id,flush=True)
            try:
                world=design.build_world(row['graph_seed'],row['mode'],row['scenario'],10)
                a=runner.run_once(world,row['arm'],1,args_run,w,output,design)
                path=output/(a['run_id']+'.json')
                if not all(runner.audit_artifact(a,design).values()): raise ValueError('independent audit')
                entry.update(status='completed',artifact=str(path),sha256=digest(path),
                    first_stage_attempts_only=all(len(t['attempts'])==1 for t in a['turns'].values()))
                ledger['attempts'][attempt_id].update(status='completed',artifact=str(path),sha256=digest(path))
                save(journal/'scientific_results.json',report.summarize([path]))
            except Exception as exc:
                paths=list(output.glob('icl_expanded_v2_*.json'))
                failure=read(paths[0]).get('failure',{}) if len(paths)==1 else {}
                reason=failure.get('reason','implementation_error'); pause=failure.get('pause',True)
                entry.update(status='failed_terminal',reason=reason)
                ledger['attempts'][attempt_id].update(status='failed_terminal',reason=reason,exception_type=type(exc).__name__)
                save(journal/'failure.json',dict(reason=reason,pause=pause,exception_type=type(exc).__name__))
            # Crash-damaged requests remain reserved; a normal terminal cell is never requeued.
            pause=finish_status(ledger,reason,pause)
            save(state/'ledger.json',ledger); export(state,ledger,rows); count+=1
            print(json.dumps(read(state/'progress.json')),flush=True)
            if pause: break


if __name__=='__main__': main()

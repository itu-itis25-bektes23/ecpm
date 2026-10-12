"""Mocked bounded-recovery, raw-evidence and budget guards. No network."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

import icl_expanded as x
import icl_recovery as recovery
import icl_model_first_runner as runner
from experiments import run_icl_recovery as batch
from experiments import preview_icl_expanded as report
import test_icl_expanded as fixtures


class Recovery(unittest.TestCase):
    def run_case(self, mode='on', events=(), malformed=False):
        temp=tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup); folder=Path(temp.name)
        w=fixtures.Expanded32K().wrapper(mode); w['expanded']['operational_policy']=recovery.specification()
        c=w['deployment']; x.validate_config(w,c['profile'],mode,x.HISTORY_POLICIES[0],32768)
        world=x.build_world(8,'sto','no_change'); answers=x.oracle_answers(world)
        if malformed: answers['A_task']='wrong malformed JSON {'
        ledger=dict(budget_usd='20',carried_exposure_usd='0.06029674',requests={})
        coordinator=batch.Coordinator(folder,ledger,'cell/recovery1',
            dict(input_per_token_usd='0.0000001',output_per_token_usd='0.0000011'))
        args=report.arguments('model_first',mode,x.HISTORY_POLICIES[0],c['profile'],32768)
        args.provider='openai'; args.model=c['model']; args.timeout=1800; args.recovery_coordinator=coordinator
        calls=[]; events=list(events); accepted=0
        def respond(body,config,timeout):
            nonlocal accepted
            calls.append(copy.deepcopy(body)); self.assertEqual(timeout,1800)
            event=events.pop(0) if events else 'ok'
            if event=='timeout': raise TimeoutError()
            if event=='429':
                import io
                raise urllib.error.HTTPError('https://example.invalid',429,'rate limited',{'Retry-After':'0'},io.BytesIO(b'{"error":"rate"}'))
            d=fixtures.Expanded16K().response(c,mode,answers[list(answers)[accepted]])
            d['usage'].update(prompt_tokens=100,completion_tokens=800,cost=0.001)
            d['choices'][0]['message']['reasoning']=None
            d['usage']['completion_tokens_details']={'reasoning_tokens':0}
            if event=='missing': d['usage']['completion_tokens_details']={}
            if event=='anomaly': d['usage']['completion_tokens_details']['reasoning_tokens']=801
            if event=='positive':
                d['usage']['completion_tokens_details']['reasoning_tokens']=10
                d['choices'][0]['message']['reasoning']='private reasoning'
            if event=='mismatch': d['provider']='Wrong provider'
            if event=='length':
                d['choices'][0]['finish_reason']='length'; d['choices'][0]['message']['content']=None
            elif event=='empty': d['choices'][0]['message']['content']=' \n'
            else: accepted+=1
            return 200,json.dumps(d)
        error=None
        with patch.object(x.pilot,'_git_dirty',return_value=False),patch.object(runner,'call_provider',side_effect=respond), \
                patch.object(recovery,'delay',return_value=0):
            try: runner.run_once(world,'model_first',1,args,w,folder/'artifacts',x)
            except RuntimeError as exc: error=exc
        path=next((folder/'artifacts').glob('*.json')); a=json.loads(path.read_text())
        return a,calls,ledger,path,error

    def test_on_zero_and_missing_are_requested_condition_not_proof(self):
        for event in ('ok','missing','anomaly'):
            a,calls,ledger,path,error=self.run_case(events=[event])
            self.assertIsNone(error); self.assertEqual(len(calls),6)
            t=a['turns']['A_prepare']; obs=t['reasoning_acceptance']
            self.assertTrue(obs['request_condition_accepted'])
            self.assertEqual(obs['derived_reasoning_tokens'],0 if event=='ok' else None)
            if event!='anomaly': self.assertFalse(t['control_check']['mode_verified'])
            self.assertTrue(all(runner.audit_artifact(a,x).values()))
            exported=report.summarize([path])['request_usage'][0]
            self.assertEqual(exported['reasoning_tokens'],0 if event=='ok' else None)
            if event=='anomaly': self.assertEqual(exported['provider_usage']['completion_tokens_details']['reasoning_tokens'],801)
            bad=copy.deepcopy(a); bad['turns']['A_prepare']['reasoning_acceptance']['derived_reasoning_tokens']=123
            self.assertFalse(all(runner.audit_artifact(bad,x).values()))

    def test_off_positive_and_identity_pause(self):
        for event in ('positive','mismatch'):
            a,calls,_,_,error=self.run_case('off',[event])
            self.assertIsNotNone(error); self.assertEqual(len(calls),1)
            self.assertEqual(a['failure']['reason'],'identity_control'); self.assertTrue(a['failure']['pause'])

    def test_same_prefix_length_increase_and_first_accepted(self):
        a,calls,_,path,error=self.run_case(events=['length','ok'])
        self.assertIsNone(error); self.assertEqual(len(calls),7)
        self.assertEqual(calls[1],calls[0] | {'max_tokens':65536})
        self.assertEqual(calls[2]['max_tokens'],32768)
        self.assertEqual(a['turns']['A_prepare']['max_output_tokens'],65536)
        self.assertTrue(all(runner.audit_artifact(a,x).values()))
        self.assertEqual(len(report.summarize([path])['request_usage']),7)
        bad=copy.deepcopy(a); bad['turns']['A_prepare']['attempts'][0]['request_body']['messages'][0]['content']='tampered'
        self.assertFalse(all(runner.audit_artifact(bad,x).values()))

    def test_four_attempt_limit_transients_and_length(self):
        a,calls,ledger,_,error=self.run_case(events=['timeout','length','429','ok'])
        self.assertIsNone(error); self.assertEqual(len(calls),9)
        self.assertEqual([c['max_tokens'] for c in calls[:4]],[32768,32768,65536,65536])
        self.assertTrue(all(runner.audit_artifact(a,x).values()))
        self.assertEqual(sum(r['status']=='unknown_charge' for r in ledger['requests'].values()),2)
        a,calls,_,_,error=self.run_case(events=['timeout','timeout','timeout'])
        self.assertIsNotNone(error); self.assertEqual(len(calls),3)
        a,calls,_,_,error=self.run_case(events=['length','length'])
        self.assertIsNotNone(error); self.assertEqual(len(calls),2); self.assertFalse(a['failure']['pause'])

    def test_no_recovery_for_empty_or_malformed_stop(self):
        a,calls,_,_,error=self.run_case(events=['empty'])
        self.assertIsNotNone(error); self.assertEqual(len(calls),1)
        a,calls,_,_,error=self.run_case(malformed=True)
        self.assertIsNone(error); self.assertEqual(len(calls),6)
        self.assertNotEqual(a['turns']['A_task']['parsed']['status'],'ok')

    def test_budget_reservation_unknown_charge_and_duplicate(self):
        with tempfile.TemporaryDirectory() as folder:
            l=dict(budget_usd='20',carried_exposure_usd='19.9',requests={})
            c=batch.Coordinator(Path(folder),l,'a',dict(input_per_token_usd='0.0000001',output_per_token_usd='0.0000011'))
            request=dict(max_output_tokens=32768,request_sha256='hash')
            with self.assertRaisesRegex(recovery.Stop,'budget_exhausted'): c.reserve('A',1,request)
            self.assertFalse(l['requests'])
            l['carried_exposure_usd']='19.8'; key=c.reserve('A',1,request)
            with self.assertRaisesRegex(recovery.Stop,'duplicate'): c.reserve('A',1,request)
            with self.assertRaisesRegex(recovery.Stop,'budget'): c.reserve('B',1,request)
            c.settle(key,{'exception_type':'TimeoutError'})
            self.assertEqual(l['requests'][key]['status'],'unknown_charge')
            self.assertGreater(batch.exposure(l),batch.money('19.8'))

    def test_crash_never_requeues_or_releases_reservation(self):
        l=dict(cells={'c':{'status':'inflight'},'d':{'status':'failed_terminal'},'e':{'status':'pending'}},
            attempts={'a':{'status':'inflight'}},requests={'r':{'status':'inflight','reserved_usd':'1','reported_cost_usd':None}},
            carried_exposure_usd='0.06029674')
        before=batch.exposure(l); batch.recover_crash(l)
        self.assertEqual(l['cells']['c']['status'],'uncertain')
        self.assertEqual(l['cells']['d']['status'],'failed_terminal'); self.assertEqual(l['cells']['e']['status'],'pending')
        self.assertEqual(batch.exposure(l),before)

    def test_adaptive_cost_has_all_twenty_four_attempts(self):
        w=fixtures.Expanded32K().wrapper(); w['expanded']['operational_policy']=recovery.specification()
        plan=runner.block_cost_plan(x.build_world(8,'sto','no_change'),'model_first',w,1,design_api=x)
        self.assertEqual(plan['maximum_http_requests'],24)
        self.assertEqual(plan['maximum_completion_tokens'],6*(32768+3*65536))

    def test_independent_cells_continue_but_systemic_failures_pause(self):
        l=dict(systemic_streak=0,last_systemic_reason=None)
        for reason in ('length','content_finish',None): self.assertFalse(batch.finish_status(l,reason,False))
        self.assertFalse(batch.finish_status(l,'transient',False))
        self.assertFalse(batch.finish_status(l,'transient',False))
        self.assertTrue(batch.finish_status(l,'transient',False))
        self.assertEqual(l['paused_reason'],'transient')

    def test_retry_after_is_bounded_not_silently_shortened(self):
        self.assertEqual(recovery.delay({'ordinal':1,'retry_after':'60'}),60)
        with self.assertRaisesRegex(recovery.Stop,'bounded_wait'):
            recovery.delay({'ordinal':1,'retry_after':'121'})

    def test_preflight_acceptance_is_versioned_too(self):
        w=fixtures.Expanded32K().wrapper('on'); c=w['deployment']
        c['preflight']['response']['choices'][0]['message']['reasoning']=None
        c['preflight']['response']['usage']['completion_tokens_details']={'reasoning_tokens':0}
        fixtures.Expanded16K().reseal_preflight(c)
        with self.assertRaisesRegex(ValueError,'control not verified'):
            x.validate_config(w,c['profile'],'on',x.HISTORY_POLICIES[0],32768)
        w['expanded']['operational_policy']=recovery.specification()
        x.validate_config(w,c['profile'],'on',x.HISTORY_POLICIES[0],32768)
        self.assertFalse(x.controls.reasoning_check(c['preflight']['response'],'on',c['effective'],c['profile'],c)['mode_verified'])

    def test_budget_cannot_be_restarted_in_another_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder); state=p/'state'; state.mkdir()
            batch.bind_ledger(p/'registry.json',state,p/'original')
            with self.assertRaisesRegex(ValueError,'interrupted'):
                batch.bind_ledger(p/'registry.json',state,p/'original')
            batch.save(state/'ledger.json',{'budget_usd':'20'})
            batch.bind_ledger(p/'registry.json',state,p/'original')
            with self.assertRaisesRegex(ValueError,'elsewhere'):
                batch.bind_ledger(p/'registry.json',p/'other',p/'original')

    def test_second_serial_coordinator_cannot_hold_lock(self):
        import fcntl
        with tempfile.TemporaryDirectory() as folder:
            with (Path(folder)/'lock').open('a') as first, (Path(folder)/'lock').open('a') as second:
                fcntl.flock(first,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with self.assertRaises(BlockingIOError): fcntl.flock(second,fcntl.LOCK_EX|fcntl.LOCK_NB)

    def test_http_wall_clock_deadline_interrupts_not_just_socket_timeout(self):
        import time
        import signal
        with self.assertRaises(TimeoutError):
            with recovery.deadline(0.01): time.sleep(1)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL)[0],0)


if __name__=='__main__': unittest.main(verbosity=2)

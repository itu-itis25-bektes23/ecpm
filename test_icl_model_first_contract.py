import copy
import json
import unittest
import icl_model_first as d

class ContractTests(unittest.TestCase):
    def test_preparation_is_present_and_retained_in_every_condition(self):
        for seed in (8, 13, 25):
            world = d.load(seed)
            answers = {p+'_'+s: f'UNIQUE {p}_{s}' for p in ('A','B')
                       for s in ('prepare','task','readout')}
            for policy in d.HISTORY_POLICIES:
                for arm in d.ARMS:
                    calls = d.schedule(world, arm, answers, policy)
                    self.assertEqual([c['id'] for c in calls],
                                     [p+'_'+s for p in ('A','B')
                                      for s in ('prepare','task','readout')])
                    self.assertEqual([c['max_output_tokens'] for c in calls], [4096]*6)
                    for p in ('A','B'):
                        task_call = next(c for c in calls if c['id'] == p+'_task')
                        self.assertIn({'role':'assistant','content':answers[p+'_prepare']},
                                      task_call['messages'])

    def test_only_initial_message_supplies_evidence_and_only_model_first_requests_model(self):
        for seed in (8,13,25):
            world = d.load(seed)
            for period in ('A','B'):
                prompts = {arm:d.prompts(world,period,arm) for arm in d.ARMS}
                self.assertEqual(prompts['task_only']['prepare'],
                                 prompts['graph_given']['prepare'].replace(d.graph_text(world[period])+'\n','',1))
                for arm, parts in prompts.items():
                    self.assertIn('Shuffled single-step observations', parts['prepare'])
                    self.assertNotIn('Route queries:', parts['prepare'])
                    self.assertEqual(parts['task'], d.task(world,period))
                    self.assertEqual(parts['readout'], d.readout(world,period))
                    if arm != 'model_first':
                        instruction = parts['prepare'].split('\n\n')[-1].lower()
                        self.assertNotIn('model', instruction)
                        self.assertNotIn('representation', instruction)

    def test_fixture_coverage_and_changed_graph(self):
        for seed in (8,13,25):
            w=d.load(seed)
            for p in ('A','B'):
                self.assertEqual(len(w[p]['graph']),16)
                self.assertEqual(len(w[p]['rows']),160)
                self.assertEqual(len(w[p]['nodes']),8)
            changes=[(a,b) for a,b in zip(w['A']['graph'],w['B']['graph']) if a!=b]
            self.assertEqual(len(changes),1)
            a,b=changes[0]
            self.assertEqual(a['destination'],b['destination'])
            self.assertTrue(a['available'] and b['available'])
            self.assertEqual((a['p_success'],b['p_success']),(1,0))
            self.assertEqual(len(w['controls']),4)
            self.assertNotIn(w['target'],[[c['node'],c['action']] for c in w['controls']])

    def test_sequential_logs_reconstruct_full_world(self):
        for seed in (8,13,25):
            w=d.load(seed); previous=None
            for p in ('A','B'):
                previous=d.from_logs(w[p],previous)
                self.assertEqual(previous,w[p]['graph'])

    def test_evidence_shared_except_graph(self):
        for seed in (8,13,25):
            w=d.load(seed)
            for p in ('A','B'):
                common=d.evidence(w,p,'task_only')
                self.assertEqual(common,d.evidence(w,p,'model_first'))
                self.assertEqual(common,d.evidence(w,p,'graph_given').replace(d.graph_text(w[p])+'\n','',1))

    def test_b_graph_is_updated(self):
        w=d.load(8); p=d.prompts(w,'B','graph_given')['prepare']
        self.assertIn('G | a1 | true | E | 0',p)
        self.assertNotIn('G | a1 | true | E | 1',p)

    def test_no_future_information_in_a(self):
        w=d.load(8); changed=copy.deepcopy(w); changed['B']={'bad':'FUTURE SENTINEL'}; changed['target']=['X','bad']; changed['controls']=[]
        for arm in d.ARMS:
            self.assertEqual(d.prompts(w,'A',arm),d.prompts(changed,'A',arm))
        self.assertEqual(d.queries(w),d.queries(changed))

    def test_no_future_information_in_a_histories(self):
        w=d.load(8); changed=copy.deepcopy(w)
        changed['B']['rows']=['FUTURE EVIDENCE SENTINEL']
        answers={p+'_'+s:f'answer {p}_{s}' for p in ('A','B') for s in ('prepare','task','readout')}
        future=dict(answers)
        for key in future:
            if key.startswith('B'):
                future[key]='FUTURE ANSWER SENTINEL'
        for arm in d.ARMS:
            for policy in d.HISTORY_POLICIES:
                before=[c for c in d.schedule(w,arm,answers,policy) if c['id'].startswith('A')]
                after=[c for c in d.schedule(changed,arm,future,policy) if c['id'].startswith('A')]
                self.assertEqual(before,after)
                self.assertNotIn('FUTURE',json.dumps(after))

    def test_no_representation_or_route_queries_before_construction(self):
        w=d.load(8)
        p=d.prompts(w,'A','model_first')['prepare'].lower()
        for banned in ('graph','json','q0','q1','route queries','target','control'):
            self.assertNotIn(banned,p)
        self.assertIn('whatever representation',p)
        self.assertNotIn('construct a model',d.prompts(w,'A','task_only')['task'])

    def test_common_tasks_and_transition_report_text(self):
        for p in ('A','B'):
            w=d.load(8)
            for arm in d.ARMS:
                self.assertTrue(d.prompts(w,p,arm)['task'].endswith(d.task(w,p)))
                self.assertTrue(d.prompts(w,p,arm)['readout'].endswith(d.readout(w,p)))

    def test_complete_history_including_reports_no_branches(self):
        answers={p+'_'+s:f'UNIQUE_ANSWER_{p}_{s}' for p in ('A','B') for s in ('prepare','task','readout')}
        for seed in (8,13,25):
            w=d.load(seed)
            for arm in d.ARMS:
                calls=d.schedule(w,arm,answers)
                expected=[{'role':'system','content':d.SYSTEM}]
                for call in calls:
                    p,stage=call['id'].split('_',1)
                    expected.append({'role':'user','content':d.prompts(w,p,arm)[stage]})
                    self.assertEqual(call['messages'],expected)
                    texts=[x['content'] for x in call['messages']]
                    if p=='B':
                        self.assertIn(d.prompts(w,'A',arm)['readout'],texts)
                        self.assertIn(answers['A_readout'],texts)
                    else:
                        self.assertFalse(any(answers['B_'+s] in texts for s in ('prepare','task','readout')))
                    if stage=='readout':
                        self.assertIn(answers[p+'_task'],texts)
                    expected.append({'role':'assistant','content':answers[call['id']]})

    def test_history_identity_does_not_reselect_queries(self):
        expected={8:[('G','D'),('C','E'),('H','E'),('A','B')],
                  13:[('H','E'),('G','B'),('G','H'),('C','F')],
                  25:[('E','G'),('A','G'),('D','A'),('C','H')]}
        self.assertEqual(d.HISTORY_POLICY,'retained_reports_v2')
        for seed,pairs in expected.items():
            self.assertEqual([(q['start'],q['goal']) for q in d.queries(d.load(seed))],pairs)

    def test_both_policies_complete_expected_history(self):
        answers={p+'_'+s:f' \nMALFORMED EXACT {p}_{s} }}{{\t '
                 for p in ('A','B') for s in ('prepare','task','readout')}
        for seed in (8,13,25):
            w=d.load(seed)
            for arm in d.ARMS:
                for policy in d.HISTORY_POLICIES:
                    main=[{'role':'system','content':d.SYSTEM}]
                    for call in d.schedule(w,arm,answers,policy):
                        period,stage=call['id'].split('_',1)
                        expected=main+[{'role':'user','content':d.prompts(w,period,arm)[stage]}]
                        self.assertEqual(call['messages'],expected)
                        self.assertEqual(call['history_policy'],policy)
                        texts=[x['content'] for x in expected]
                        if stage=='readout':
                            self.assertIn(answers[period+'_task'],texts)
                        if period=='B':
                            self.assertIn(answers['A_task'],texts)
                            if arm=='model_first':
                                self.assertIn(answers['A_prepare'],texts)
                            for value in (answers['A_readout'],d.prompts(w,'A',arm)['readout']):
                                self.assertEqual(value in texts,policy==d.HISTORY_POLICY)
                        else:
                            self.assertFalse(any(answers['B_'+s] in texts for s in ('prepare','task','readout')))
                        branch=stage=='readout' and policy!=d.HISTORY_POLICY
                        self.assertEqual(call['conversation'],'measurement_branch' if branch else 'main')
                        if not branch:
                            main=expected+[{'role':'assistant','content':answers[call['id']]}]

    def test_graph_heading_only_in_graph_given(self):
        for seed in (8,13,25):
            for period in ('A','B'):
                for arm in d.ARMS:
                    for text in d.prompts(d.load(seed),period,arm).values():
                        self.assertEqual('Current-period graph:' in text,arm=='graph_given' and text == d.prompts(d.load(seed),period,arm)['prepare'])
                        self.assertNotIn('Current-period specification:',text)
                        if arm!='graph_given':
                            self.assertNotIn('graph',text.lower())

    def test_matched_allowances_and_request_count(self):
        w=d.load(8); answers={p+'_'+s:'visible answer' for p in ('A','B') for s in ('prepare','task','readout')}
        counts=[]
        for arm in d.ARMS:
            calls=d.schedule(w,arm,answers); counts.append(len(calls))
            self.assertEqual(sum(c['max_output_tokens'] for c in calls),24576)
            for p in ('A','B'):
                self.assertEqual(sum(c['max_output_tokens'] for c in calls if c['id'].startswith(p) and not c['id'].endswith('readout')),8192)
        self.assertEqual(counts,[6,6,6]); self.assertEqual(sum(counts)*3,54)

    def test_queries_unique_and_reproducible(self):
        for seed in (8,13,25):
            w=d.load(seed); q=d.queries(w)
            self.assertEqual(q,d.queries(w))
            self.assertTrue(all(d.shortest(w['A']['graph'],x['start'],x['goal'])['reachable'] for x in q))
            self.assertEqual(len({(x['start'],x['goal']) for x in q}),4)
            self.assertTrue(all(x['start']!=x['goal'] for x in q))
            self.assertEqual((q[0]['start'],q[0]['goal']),(w['A']['start'],w['A']['goal']))
            self.assertEqual([x['query_id'] for x in q],['q0','q1','q2','q3'])

    def test_goal_is_query_specific_and_unreachable_explicit(self):
        rows=d.load(8)['A']['graph']
        self.assertEqual(d.shortest(rows,'G','E'),{'reachable':True,'steps':[{'state':'G','action':'a1'}],'cost':1.0})
        self.assertEqual(d.shortest(rows,'D','G'),{'reachable':False,'steps':[],'cost':None})
        self.assertEqual(d.shortest(rows,'G','G'),{'reachable':True,'steps':[],'cost':0.0})

    def test_expected_attempt_cost_and_zero_probability(self):
        rows=[{'node':'X','action':'a1','available':True,'destination':'Y','p_success':0.5}]
        self.assertEqual(d.shortest(rows,'X','Y')['cost'],2)
        rows[0]['p_success']=0
        self.assertIsNone(d.shortest(rows,'X','Y')['cost'])

    def test_reference_routes_execute_and_match_anchor(self):
        for seed in (8,13,25):
            w=d.load(seed); previous=None
            for p in ('A','B'):
                estimates=d.from_logs(w[p],previous); ref=d.reference(w,p,estimates,previous)
                self.assertEqual(ref['costs']['q0'],2 if p=='A' else 3)
                lookup={(x['node'],x['action']):x for x in estimates}
                for q,route in zip(d.queries(w),ref['task']['routes']):
                    if not route['reachable']:
                        self.assertEqual(route['steps'],[]); continue
                    state=q['start']; cost=0
                    for step in route['steps']:
                        self.assertEqual(step['state'],state)
                        row=lookup[(state,step['action'])]; self.assertGreater(row['p_success'],0)
                        cost+=1/row['p_success']; state=row['destination']
                    self.assertEqual(state,q['goal'])
                    self.assertEqual(cost,ref['costs'][q['query_id']])
                if p=='B':
                    self.assertEqual(ref['task']['changed_pair'],{'state':w['target'][0],'action':w['target'][1]})
                    self.assertEqual(sum(x['changed'] for x in ref['readout']['pairs']),1)
                previous=estimates

    def test_reference_detection_does_not_read_target(self):
        w=d.load(8); a=d.from_logs(w['A']); b=d.from_logs(w['B'],a)
        expected=d.reference(w,'B',b,a)
        w['target']=['WRONG','WRONG']
        self.assertEqual(d.reference(w,'B',b,a),expected)
        unchanged=d.reference(w,'B',a,a)
        self.assertFalse(unchanged['task']['changed']); self.assertIsNone(unchanged['task']['changed_pair'])

    def test_unknown_destination_rejected_in_offline_fixture(self):
        w=d.load(8)
        with self.assertRaises(ValueError): d.from_logs(w['B'])

if __name__=='__main__': unittest.main(verbosity=2)

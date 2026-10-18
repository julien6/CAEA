import unittest
from copy import deepcopy
from dataclasses import asdict
from caea.core import Action
from caea.org_v2.model import make_case,posterior,AcquisitionCore,AgentKnowledge
from caea.org_v2.protocols import PROTOCOLS,PeerToPeer,Coalitions,Market
from caea.org_v2.engine import episode,Environment


class Organizations(unittest.TestCase):
    def test_sharing_oracle(self):
        for count in (2,3,4):
            rs=[{'eid':str(i),'kind':'share','pair':'x','slot':i,'parts':count,'h':0,'bit':int(i==0),'reliability':.85} for i in range(count)]
            self.assertEqual(posterior(rs[:-1],1),[.5]);self.assertAlmostEqual(posterior(rs,1)[0],.85)
            self.assertEqual(posterior(rs+rs,1),posterior(rs,1))
    def test_local_noninterference_and_snapshot(self):
        case=make_case(71);p=PeerToPeer(case['nodes']['root']['meta'],4,3,AcquisitionCore(),delay=2)
        initial=p.views[1].detached();event={'id':'e','action':{'op':'discover','node':'root'},'children':{'D0':case['nodes']['D0']['meta']}}
        before=p.propose(1);p.integrate(0,event)
        self.assertEqual(before,p.propose(1));self.assertEqual(initial.snapshot(),p.views[1].snapshot())
        p.start(2,0,{0,1,2});self.assertIn('D0',p.views[1].known)
        self.assertNotIn('D0',initial.known)
    def test_reference_cannot_teleport(self):
        s=AgentKnowledge(4,known={'root':{'type':'root','path':['root'],'size':0,'topic':None}})
        s.records=[{'eid':'x','kind':'share','h':0,'pair':'p','slot':0,'bit':1,'reliability':.85,'target_path':['root','D9','N9']}]
        self.assertEqual(s.actions(),[Action('discover','root')])
    def test_budget_replay_and_all_protocols(self):
        case=make_case(72)
        for org in PROTOCOLS:
            for delay in (0,2):
                cfg={'organization':org,'policy':'caea','budget':24,'delay':delay}
                first=episode(case,cfg);replay={r['event']:r['record'] for r in first['extractions']}
                second=episode(case,cfg,replay=replay)
                self.assertEqual(first['metrics'],second['metrics']);self.assertEqual(first['traces'],second['traces']);self.assertEqual(first['messages'],second['messages'])
                self.assertLessEqual(first['metrics']['cost'],24);self.assertGreater(first['metrics']['messages'],0)
    def test_metadata_not_fabricated(self):
        case=make_case(3);env=Environment(case);s=AgentKnowledge(4,known={'root':deepcopy(case['nodes']['root']['meta'])})
        s.known['root']['size']=100
        from caea.org_v2.model import Assignment
        with self.assertRaises(ValueError):env.execute([Assignment(0,Action('discover','root'),0)],[s],[3],0)
    def test_coalitions_and_market_have_real_events(self):
        case=make_case(73)
        coal=episode(case,{'organization':'COAL','budget':36});market=episode(case,{'organization':'MKT','budget':36})
        self.assertTrue(any(e['type']=='coalition_join' for e in coal['messages']))
        self.assertGreater(coal['metrics']['formations'],0);self.assertGreater(market['metrics']['bids'],0)
        self.assertTrue(any(e.get('kind')=='BID' for e in market['messages']))
    def test_depth_and_parts(self):
        for depth in (2,3,5):
            c=make_case(5,depth=depth,parts=4)
            for nid,node in c['nodes'].items():
                self.assertEqual(node['meta']['path'][-1],nid)
                self.assertTrue(all(p in c['nodes'] for p in node['meta']['path']))
            for org in PROTOCOLS:self.assertLessEqual(episode(c,{'organization':org,'budget':12})['metrics']['cost'],12)
    def test_no_reference_negative_control(self):
        case=make_case(4,reference_quality=0)
        for org in PROTOCOLS:
            a=episode(case,{'organization':org,'policy':'joint','budget':24})
            b=episode(case,{'organization':org,'policy':'caea','budget':24})
            self.assertEqual(a['traces'],b['traces']);self.assertEqual(a['metrics'],b['metrics'])
    def test_no_hidden_access(self):
        self.assertNotIn('Environment',AcquisitionCore.__dict__)
        case=make_case(83);a=case['nodes']['root']['meta']
        for cls in PROTOCOLS.values():
            p=cls(a,4,3,AcquisitionCore());self.assertFalse(hasattr(p,'_case'))
            self.assertEqual([set(s.known) for s in p.views],[{'root'}]*3)
    def test_pending_messages_and_unavailable_worker(self):
        for org in PROTOCOLS:
            result=episode(make_case(92),{'organization':org,'budget':24,'delay':3,'unavailable':True})
            self.assertLess(result['metrics']['rounds'],1000)
            for row in result['traces']:
                if 5<=row['round']<10:self.assertNotIn(2,[a['worker'] for a in row['assignments']])

    def test_conditional_path_propagation_counterexample(self):
        s=AgentKnowledge(1)
        s.known={'F':{'type':'folder','path':['root','D','F'],'topic':None,'size':0},'noise':{'type':'doc','path':['root','D','noise'],'topic':0,'size':1}}
        s.records=[{'eid':'source','kind':'share','pair':'p','slot':0,'h':0,'bit':0,'reliability':.85,'target_path':['root','D','F','target']}]
        myopic=AcquisitionCore('myopic');full=AcquisitionCore('caea')
        self.assertEqual(myopic.proposals(s.detached(),0,3,0,0,1)[0].action,Action('read','noise'))
        self.assertEqual(full.proposals(s.detached(),0,3,0,0,1)[0].action,Action('discover','F'))

    def test_message_loss_and_schema_validation(self):
        from caea.org_v2.model import EpisodeConfig
        with self.assertRaises(ValueError):EpisodeConfig.validate({'organization':'P2P','agents':3,'capacities':[1]})
        for org in PROTOCOLS:
            r=episode(make_case(555),{'organization':org,'budget':12,'drop_rate':.5,'delay':1})
            self.assertLess(r['metrics']['rounds'],1000)
            self.assertTrue(any(m['type']=='lost' for m in r['messages']))

    def test_ring_diffusion_requires_hops(self):
        case=make_case(71);p=PeerToPeer(case['nodes']['root']['meta'],4,8,AcquisitionCore(),delay=1)
        event={'id':'diffusion','action':{'op':'discover','node':'root'},'children':{'D0':case['nodes']['D0']['meta']}}
        p.integrate(0,event);p.start(1,0,set(range(8)))
        self.assertIn('D0',p.views[1].known);self.assertNotIn('D0',p.views[2].known)
        p.start(2,0,set(range(8)));self.assertIn('D0',p.views[2].known);self.assertNotIn('D0',p.views[3].known)

    def test_structural_coalition_goal_is_completed(self):
        row=episode(make_case(73),{'organization':'COAL','budget':36})
        self.assertTrue(any(m['type']=='coalition_dissolve' and m['reason']=='completed' for m in row['messages']))
        self.assertGreater(row['metrics']['formations'],1)

    def test_compressed_artifact_roundtrip(self):
        import tempfile
        from pathlib import Path
        from caea.org_v2.storage import write_episode,read_episode,episode_files
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'episodes').mkdir();p=root/'episodes'/'x.json.gz'
            value={'x':[1,2,{'y':'source'}]};write_episode(p,value);first=p.read_bytes();write_episode(p,value)
            self.assertEqual(p.read_bytes(),first);self.assertEqual(read_episode(p),value);self.assertEqual(episode_files(root),[p])

    def test_executor_overrides_extractor_source_identity(self):
        def forged(node,agent,version):return {'eid':'invented-source','kind':'noise'}
        r=episode(make_case(93),{'organization':'CENT','policy':'joint','budget':24},extractor=forged)
        reads=[e for t in r['traces'] for e in t['events'] if e['action']['op']=='read']
        self.assertTrue(reads)
        for e in reads:self.assertEqual(e['record']['eid'],e['action']['node'])

    def test_curve_json_roundtrip_preserves_values(self):
        import json
        r=episode(make_case(94),{'organization':'CENT','budget':12})
        saved=json.loads(json.dumps(r))
        self.assertEqual([list(point) for point in r['curve']],saved['curve'])
        self.assertEqual(r['traces'],saved['traces']);self.assertEqual(r['messages'],saved['messages'])

    def test_archived_episode_stream_does_not_need_extraction(self):
        import io,json,gzip,tarfile,tempfile
        from pathlib import Path
        from caea.org_v2.archive import rows,ancillary
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'test'/'outputs';folder.mkdir(parents=True)
            with tarfile.open(folder/'artifacts.tar.gz','w:gz') as tar:
                payloads={'./episodes/e.json.gz':gzip.compress(json.dumps({'id':'e','curve':[[0,0,0]]}).encode(),mtime=0),'./cases/c.json':b'{"k": 1}','./llm_calls.jsonl':b'{"episode":"e","eid":"x"}\n'}
                import hashlib
                payloads['./INNER_SHA256SUMS']=''.join(hashlib.sha256(data).hexdigest()+'  '+name+'\n' for name,data in payloads.items()).encode()
                for name,data in payloads.items():
                    member=tarfile.TarInfo(name);member.size=len(data);tar.addfile(member,io.BytesIO(data))
            self.assertEqual(list(rows(root,'test')),[{'id':'e','curve':[[0,0,0]]}])
            cases,calls=ancillary(root,'test');self.assertEqual(cases,{'c':{'k':1}});self.assertEqual(calls[0]['episode'],'e')
            self.assertFalse((folder/'episodes').exists())

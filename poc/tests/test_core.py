import copy
import unittest
from caea.core import Environment, Action, posterior, generate_case
from caea.policies import Policy


class Invariants(unittest.TestCase):
    def test_one_share_has_no_information(self):
        a={'eid':'a','kind':'share','pair':'p','slot':0,'bit':1,'h':0,'reliability':.85}
        b={**a,'eid':'b','slot':1,'bit':0}
        self.assertEqual(posterior([a],1),[.5])
        self.assertAlmostEqual(posterior([a,b],1)[0],.85)
        self.assertEqual(posterior([a,b,a,b],1),posterior([a,b],1))

    def test_discovery_is_local_and_no_teleport(self):
        e=Environment(generate_case(1))
        self.assertEqual(list(e.state.known),['root'])
        with self.assertRaises(ValueError):e.step([Action('read','D0/F0/N0')])
        e.step([Action('discover','root')])
        self.assertEqual(len(e.state.known),5)
        self.assertFalse(e.state.records)
        e.step([Action('load','D0')])
        self.assertEqual(len(e.state.known),5)
        e.step([Action('discover','D0')])
        self.assertEqual(len(e.state.known),9)
        self.assertFalse(e.state.records)

    def test_cost_collision_and_round_snapshot(self):
        e=Environment(generate_case(1),budget=2)
        e.step([Action('discover','root')]*2)
        self.assertEqual(e.state.spent,2)
        self.assertEqual(e.duplicate_cost,1)
        self.assertEqual(e.utility(),0)
        with self.assertRaises(ValueError):
            Environment(generate_case(1)).step([Action('discover','root'),Action('load','D0')])

    def test_snapshot_keeps_its_original_version(self):
        e=Environment(generate_case(1))
        before=e.state.snapshot()
        change=e.step([Action('discover','root')])
        self.assertEqual(list(before['known']),['root'])
        self.assertEqual(list(change['before']['known']),['root'])
        self.assertEqual(len(change['after']['known']),5)
        self.assertEqual(before['version'],0)
        self.assertEqual(change['after']['version'],1)
        self.assertIsNot(before['records'],e.state.records)
        self.assertIsNot(before['references'],e.state.references)

    def test_feedback_contains_only_public_fields(self):
        e=Environment(generate_case(1))
        change=e.step([Action('discover','root')])
        self.assertEqual(set(change),{'before','after','acquired','cost'})
        self.assertNotIn('truth',change['after'])
        self.assertNotIn('actual',change['after'])

    def test_policy_cannot_see_hidden_truth(self):
        case=generate_case(4)
        other=copy.deepcopy(case); other['truth']=[1-x for x in case['truth']]
        for n in other['nodes'].values():
            if n.get('record',{}).get('kind')=='direct':n['record']['bit']^=1
        a,b=Environment(case),Environment(other)
        p,q=Policy('caea',1),Policy('caea',1);p.budget=q.budget=64
        self.assertEqual(p.choose(a.state,3),q.choose(b.state,3))
        self.assertFalse(hasattr(a.state,'truth'))

    def test_reproducible_cases_and_budget(self):
        self.assertEqual(generate_case(7),generate_case(7))
        e=Environment(generate_case(7),budget=37)
        p=Policy('caea',2);p.budget=37
        while True:
            actions=p.choose(e.state,3)
            if not actions:break
            p.feedback(e.step(actions))
        self.assertLessEqual(e.state.spent,37)
        self.assertEqual(e.metrics()['mae'],0)
        self.assertGreaterEqual(e.metrics()['auc'],0)
        self.assertLessEqual(e.metrics()['auc'],1)

    def test_extractor_receives_no_evaluator_annotation(self):
        e=Environment(generate_case(2));p=Policy('random',5);p.budget=32
        seen=[]
        def extract(node,agent,version):
            self.assertEqual(set(node),{'text','meta'})
            self.assertNotIn('record',node)
            seen.append(node)
            return {'eid':node['meta']['path'][-1],'kind':'noise'}
        while True:
            actions=p.choose(e.state,3)
            if not actions:break
            e.step(actions,extract)
        self.assertTrue(seen)

    def test_identity_rendering_preserves_hidden_channels(self):
        import re
        numeric=generate_case(37)
        identity=generate_case(37,rendering='identity_join')
        self.assertEqual(numeric['truth'],identity['truth'])
        pairs={}
        for nid,node in identity['nodes'].items():
            record=node.get('record')
            if not record:continue
            self.assertEqual(record,numeric['nodes'][nid]['record'])
            if record['kind']=='share':pairs.setdefault(record['pair'],{})[record['slot']]=node
        for group in pairs.values():
            first,second=group[0],group[1]
            account=int(re.search(r'mapped to account U([01])',first['text'])[1])
            actor=int(re.search(r'recorded for account U([01])',second['text'])[1])
            self.assertEqual(int(account==actor),first['record']['bit'] ^ second['record']['bit'])

    def test_estimator_cannot_change_oracle_reward(self):
        case=generate_case(2)
        a,b=Environment(case),Environment(case)
        p=Policy('random',5);p.budget=64
        while True:
            actions=p.choose(a.state,3)
            if not actions:break
            a.step(actions)
            b.step(actions,lambda n,i,v:{'kind':'noise','eid':n['meta']['path'][-1]})
        self.assertEqual(a.utility(),b.utility())
        self.assertEqual(a.state.spent,b.state.spent)
        self.assertEqual(a.actual,b.actual)

if __name__=='__main__':unittest.main()

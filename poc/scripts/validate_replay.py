"""Regenerate and replay final episodes after interface hardening. No LLM inference."""
import argparse,json,math,time
from pathlib import Path
from caea.core import generate_case,Environment
from caea.policies import Policy
p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--output',required=True);p.add_argument('--runs',nargs='+');p.add_argument('--expected',type=int,default=11392);a=p.parse_args()
root=Path(a.root);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
started=time.time();counts={}
for run in (a.runs or ['numeric-v1','document-oracle','strict-oracle','llm15-final','llm7-final','strict15-final','strict7-final']):
    cfg=json.loads((root/run/'config.json').read_text())
    groups=[(root/run/'outputs'/item['name'],item['config']) for item in cfg['suite']] if 'suite' in cfg else [(root/run/'outputs',cfg)]
    for folder,config in groups:
        replay={}
        llm='llm' in config
        if llm:
            for line in (folder/'llm_calls.jsonl').read_text().splitlines():
                r=json.loads(line);key=(r['episode'],r['eid'])
                assert key not in replay
                replay[key]=r.get('parsed')
        total=0
        for setting in config['settings']:
            params={k:v for k,v in setting.items() if k not in ('name','budget','agents','organization')}
            for seed in config['case_seeds']:
                case=generate_case(seed,**params)
                for ps in config['policy_seeds']:
                    for method in config['methods']:
                        eid=f'{setting["name"]}-{seed}-{ps}-{method}'
                        expected=json.loads((folder/'episodes'/f'{eid}.json').read_text())
                        assert expected['case_sha256']==case['sha256']
                        env=Environment(case,setting['budget'],config['capacity'])
                        agents=1 if method in ('single','single_informed') else setting.get('agents',3)
                        name=('caea_informed' if method=='single_informed' else 'caea') if method in ('single','single_informed') else method
                        policy=Policy(name,ps+seed*10007,agents,setting.get('organization','central'),references=name!='caea_no_refs')
                        policy.budget=env.budget
                        def extractor(node,agent,version):
                            assert set(node)=={'text','meta'}
                            key=(eid,node['meta']['path'][-1])
                            if key not in replay:raise AssertionError('new unrecorded acquisition')
                            return replay[key]
                        while True:
                            actions=policy.choose(env.state,env.capacity)
                            if not actions:break
                            public=env.step(actions,extractor if llm else None)
                            assert set(public)=={'before','after','acquired','cost'}
                            policy.feedback(public)
                        actual=env.metrics()
                        for metric,value in expected['metrics'].items():
                            assert math.isclose(actual[metric],value,abs_tol=1e-12,rel_tol=1e-12),(run,eid,metric,actual[metric],value)
                        assert env.traces==expected['traces'],(run,eid,'trace mismatch')
                        assert env.curve==[tuple(row) for row in expected['curve']],(run,eid,'curve mismatch')
                        total+=1
        counts[str(folder.relative_to(root))]=total
        print(json.dumps({'group':str(folder),'identical_episodes':total}),flush=True)
assert sum(counts.values())==a.expected
(out/'replay_validation.json').write_text(json.dumps({'identical_episodes':sum(counts.values()),'groups':counts,
    'metrics_tolerance':1e-12,'traces_exact':True,'curves_exact':True,'regenerated_case_hashes_exact':True,
    'llm_calls_replayed_without_inference':True,'public_feedback_only':True,'wall_seconds':time.time()-started},indent=2))

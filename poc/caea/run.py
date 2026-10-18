"""CLI: generate hidden cases, run paired policies, save resumable episode files."""
import argparse
import json
import os
import platform
import time
from pathlib import Path
from .core import generate_case, Environment
from .policies import Policy


def run(config, output):
    out=Path(output); out.mkdir(parents=True,exist_ok=True)
    used=out/'used_config.json'
    if used.exists() and json.loads(used.read_text())!=config:
        raise ValueError('output directory belongs to a different configuration')
    if config.get('llm') and (out/'llm_calls.jsonl').exists():
        raise ValueError('LLM traces already exist; use a fresh run directory to preserve accounting')
    used.write_text(json.dumps(config,sort_keys=True,indent=2))
    (out/'cases').mkdir(exist_ok=True); (out/'episodes').mkdir(exist_ok=True)
    extractor=None
    if config.get('llm'):
        from .llm import Extractor
        extractor=Extractor(config['llm'],out)
    for setting in config['settings']:
        label=setting['name']
        for seed in config['case_seeds']:
            params={k:v for k,v in setting.items() if k not in ('name','budget','agents','organization')}
            case=generate_case(seed,**params)
            case_path=out/'cases'/f'{label}-{seed}.json'
            case_path.write_text(json.dumps(case,sort_keys=True))
            for repeat in config.get('policy_seeds',[0]):
                for method in config['methods']:
                    eid=f'{label}-{seed}-{repeat}-{method}'
                    target=out/'episodes'/f'{eid}.json'
                    if target.exists():
                        continue
                    env=Environment(case,setting['budget'],config.get('capacity',3))
                    agents=1 if method in ('single','single_informed') else setting.get('agents',3)
                    name=('caea_informed' if method=='single_informed' else 'caea') if method in ('single','single_informed') else method
                    pol=Policy(name,repeat+seed*10007,agents,setting.get('organization','central'),
                               references=name!='caea_no_refs')
                    pol.budget=env.budget
                    started=time.time()
                    if extractor: extractor.episode=eid
                    while env.state.spent<env.budget:
                        action=pol.choose(env.state,env.capacity)
                        if not action: break
                        change=env.step(action,extractor)
                        pol.feedback(change)
                    result={'episode':eid,'setting':label,'case_seed':seed,'policy_seed':repeat,
                            'method':method,'agents':agents,'case_sha256':case['sha256'],
                            'metrics':env.metrics(),'wall_seconds':time.time()-started,
                            'final_p':env.state.probabilities(),'truth':case['truth'],
                            'curve':env.curve,'traces':env.traces}
                    tmp=target.with_suffix('.tmp')
                    tmp.write_text(json.dumps(result,sort_keys=True)); tmp.replace(target)
                    print(json.dumps({'episode':eid,**result['metrics']}),flush=True)
    metadata={'python':platform.python_version(),'platform':platform.platform(),
              'slurm_job_id':os.getenv('SLURM_JOB_ID'),'node':platform.node(),
              'config':config,'finished_unix':time.time()}
    if extractor:
        metadata['llm']=extractor.summary()
        import urllib.request
        with urllib.request.urlopen('http://'+os.environ['OLLAMA_HOST']+'/api/ps') as response:
            metadata['runtime_models']=json.load(response)
    (out/'metadata.json').write_text(json.dumps(metadata,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',required=True); parser.add_argument('--output',required=True)
    args=parser.parse_args()
    config=json.loads(Path(args.config).read_text())
    if 'suite' in config:
        for item in config['suite']:
            run(item['config'],Path(args.output)/item['name'])
    else:
        run(config,args.output)

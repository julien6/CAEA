"""Versioned, paired organization experiments; immutable episode outputs."""
import argparse,json,os,time
from pathlib import Path
from itertools import product
from .model import make_case,digest
from .engine import episode
from .storage import write_episode


def run(cfg,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    used=out/'used_config.json'
    if used.exists() and json.loads(used.read_text())!=cfg:raise ValueError('configuration mismatch')
    if cfg.get('llm') and (out/'llm_calls.jsonl').exists():raise ValueError('fresh directory required for LLM runs')
    used.write_text(json.dumps(cfg,indent=2));(out/'episodes').mkdir(exist_ok=True);(out/'cases').mkdir(exist_ok=True)
    extractor=None
    if cfg.get('llm'):
        from caea.llm import Extractor
        extractor=Extractor(cfg['llm'],out)
    for setting in cfg['settings']:
      for seed in cfg['case_seeds']:
        case=make_case(seed,**setting.get('case',{}))
        (out/'cases'/f'{setting["name"]}-{seed}.json').write_text(json.dumps(case,sort_keys=True))
        for organization,policy,ps in product(cfg.get('organizations',['CENT','P2P','COAL','MKT']),cfg.get('policies',['joint','caea']),cfg.get('policy_seeds',[0,1])):
            label=f'{setting["name"]}-{seed}-{ps}-{organization}-{policy}'
            target=out/'episodes'/f'{label}.json.gz'
            if target.exists():continue
            ec={'organization':organization,'policy':policy,'policy_seed':seed*10007+ps,**setting.get('execution',{})}
            if extractor:extractor.episode=label
            result=episode(case,ec,extractor);result.update(id=label,setting=setting['name'],case_seed=seed,policy_seed=ps,organization=organization,policy=policy)
            write_episode(target,result)
            print(json.dumps({'id':label,**result['metrics']}),flush=True)
    meta={'slurm_job_id':os.getenv('SLURM_JOB_ID'),'finished':time.time(),'config_sha256':digest(cfg)}
    if extractor:meta['llm']=extractor.summary()
    (out/'metadata.json').write_text(json.dumps(meta,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    run(json.loads(Path(a.config).read_text()),a.output)

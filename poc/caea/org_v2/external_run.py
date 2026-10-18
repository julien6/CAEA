import argparse,json,time,os
from pathlib import Path
from itertools import product
from .engine import episode
from .storage import write_episode
from .extractor import ExternalExtractor,deterministic


def run(cfg,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);(out/'episodes').mkdir(exist_ok=True);(out/'cases').mkdir(exist_ok=True)
    if (out/'llm_calls.jsonl').exists():raise ValueError('fresh output required')
    (out/'used_config.json').write_text(json.dumps(cfg,indent=2));summaries=[]
    for name in cfg['tasks']:
        case=json.loads((Path(cfg['dataset'])/(name+'.json')).read_text());(out/'cases'/(name+'.json')).write_text(json.dumps(case,sort_keys=True))
        extractor=ExternalExtractor(cfg['llm'],out,case['question']) if cfg.get('llm') else None
        for org,policy in product(cfg.get('organizations',['CENT','P2P','COAL','MKT']),cfg.get('policies',['joint','caea'])):
            eid=f'{name}-{org}-{policy}';ec={'organization':org,'policy':policy,'budget':cfg.get('budget',30),'agents':3,'policy_seed':10007*case['seed']}
            if extractor:extractor.episode=eid
            result=episode(case,ec,extractor or deterministic)
            # Source-span witness recall is separate from acquired witness-set coverage.
            extracted={}
            for event in result['extractions']:
                r=event['record']
                if r:extracted.setdefault(r['eid'],[]).extend(r.get('quotes',[]))
            found=0
            for witness in case['witnesses']:
                nid=f'{witness["file"]}/page-{witness["page"]}'
                if any(witness['quote'].lower() in q.lower() for q in extracted.get(nid,[])):found+=1
            result['metrics']['witness_quote_recall']=found/len(case['witnesses'])
            result.update(id=eid,setting='external',case_seed=case['seed'],task_id=name,policy_seed=0,organization=org,policy=policy)
            write_episode(out/'episodes'/(eid+'.json.gz'),result);print(eid,result['metrics'],flush=True)
        if extractor:extractor.log.close();summaries.append(extractor.summary())
    (out/'metadata.json').write_text(json.dumps({'slurm_job_id':os.getenv('SLURM_JOB_ID'),'llm_summaries':summaries,'finished':time.time()},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args();run(json.loads(Path(a.config).read_text()),a.output)

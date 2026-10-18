"""Rebuild cases and replay recorded assertions without invoking any model."""
import argparse,json,math
from collections import defaultdict,deque
from pathlib import Path
from caea.org_v2.model import make_case,digest
from caea.org_v2.engine import episode
from caea.org_v2.storage import episode_files,read_episode
from caea.org_v2.archive import rows,ancillary

p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--runs',nargs='+',required=True);p.add_argument('--output',required=True);a=p.parse_args();root=Path(a.root);counts={};checked=0
for name in a.runs:
    folder=root/name;cfg=json.loads((folder/'config.json').read_text());total=0
    saved_cases,raw_calls=ancillary(root,name) if cfg.get('llm') or 'dataset' in cfg else ({},[])
    print('Starting',name,flush=True)
    calls=defaultdict(deque)
    if cfg.get('llm'):
        for row in raw_calls:calls[row['episode'],row['eid']].append(row.get('parsed'))
    for old in rows(root,name):
        setting=old['setting']
        if setting=='external':
            case=saved_cases[old['task_id']]
        else:
            params=next(s['case'] for s in cfg['settings'] if s['name']==setting)
            case=make_case(old['case_seed'],**params)
        assert case['sha256']==old['case_sha256'],(name,old['id'],'case hash')
        replay={r['event']:r['record'] for r in old['extractions']}
        if cfg.get('llm'):
            for event in old['extractions']:
                eid=event['event'].split(':read:',1)[1]
                recorded=calls[old['id'],eid].popleft()
                assert recorded==event['record'] or (recorded and {**recorded,'parts':2}==event['record']),(name,old['id'],'raw-call binding')
            new=episode(case,old['config'],replay=replay)
        elif case.get('external'):
            from caea.org_v2.extractor import deterministic
            new=episode(case,old['config'],extractor=deterministic)
        else:new=episode(case,old['config'])
        if case.get('external'):
            quotes=defaultdict(list)
            for event in new['extractions']:
                r=event['record']
                if r:quotes[r['eid']].extend(r.get('quotes',[]))
            found=sum(any(w['quote'].lower() in q.lower() for q in quotes[f'{w["file"]}/page-{w["page"]}']) for w in case['witnesses'])
            new['metrics']['witness_quote_recall']=found/len(case['witnesses'])
        for key in ('traces','messages','threshold_times','extractions'):assert new[key]==old[key],(name,old['id'],key)
        assert [list(point) for point in new['curve']]==old['curve'],(name,old['id'],'curve')
        for metric,value in new['metrics'].items():assert math.isclose(value,old['metrics'][metric],abs_tol=1e-12,rel_tol=1e-12),(name,old['id'],metric)
        total+=1
    if cfg.get('llm'):assert all(not q for q in calls.values()),'unused model calls'
    counts[name]=total;checked+=total
    print('Verified',name,total,flush=True)
out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
(out/'replay.json').write_text(json.dumps({'episodes':checked,'runs':counts,'traces_exact':True,'messages_exact':True,'case_hashes_exact':True,'metrics_tolerance':1e-12,'llm_inference':False},indent=2))
print('Replayed',checked,'episodes')

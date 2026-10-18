"""Paired fixed-horizon comparison on the matched worker-count robustness cohort."""
from collections import defaultdict
from caea.org_v2.staging import materialize
from caea.org_v2.storage import episode_files,read_episode
from caea.org_v2.analysis import uncertainty
import numpy as np


def contrasts(root):
    values=defaultdict(lambda:defaultdict(list))
    for shard in range(5):
        folder=materialize(root,f'org-final-robust-{shard}')
        for path in episode_files(folder):
            if not path.name.startswith('workers_') or '-caea.' not in path.name:continue
            r=read_episode(path);n=int(r['setting'].split('_')[1]);utility=0;reach=False
            for cost,t,u in r['curve']:
                if t<=48:utility=u;reach=reach or u>=.25
            values[r['organization'],n,r['case_seed']]['utility_at_48'].append(utility)
            values[r['organization'],n,r['case_seed']]['reach_025_at_48'].append(float(reach))
    rng=np.random.default_rng(20261018);result=[]
    for org in ('CENT','P2P','COAL','MKT'):
      for n in (2,4,8):
        seeds=sorted(k[2] for k in values if k[:2]==(org,n))
        assert len(seeds)==50
        for metric in ('utility_at_48','reach_025_at_48'):
            ds=np.array([np.mean(values[org,n,s][metric])-np.mean(values[org,1,s][metric]) for s in seeds])
            signs=rng.choice([-1,1],(10000,len(ds)))
            pv=(1+int(np.sum(np.abs((signs*ds).mean(axis=1))>=abs(ds.mean())-1e-15)))/10001
            result.append({'organization':org,'workers':n,'baseline_workers':1,'metric':metric,'delta':float(ds.mean()),'ci':uncertainty(ds,rng),'p':pv,'cases':50})
    for metric in ('utility_at_48','reach_025_at_48'):
        family=sorted([r for r in result if r['metric']==metric],key=lambda r:r['p']);running=0
        for i,r in enumerate(family):running=max(running,min(1,r['p']*(len(family)-i)));r['p_holm']=running
    return result

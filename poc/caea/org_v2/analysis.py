"""Remote case-clustered paired statistics and temporal diagnostics."""
import argparse,json
from pathlib import Path
from collections import defaultdict
import numpy as np
from .storage import episode_files,read_episode


def uncertainty(values,rng):
    v=np.asarray(values);n=len(v)
    means=v[rng.integers(0,n,(4000,n))].mean(axis=1)
    return np.quantile(means,[.025,.975]).tolist()


def analyze(folders,out,external=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);groups=defaultdict(lambda:defaultdict(list));count=0;negative={};timing=[]
    for folder in folders:
      for f in episode_files(folder):
        row=read_episode(f);count+=1
        groups[row['setting'],row['organization'],row['policy']][row['case_seed']].append(row['metrics'])
        if row['setting'] in ('direct','no_refs'):
            key=(row['setting'],row['organization'],row['case_seed'],row['policy_seed'])
            # Byte counts differ when payload scores change; compare execution and acquired utility.
            value=(row['metrics']['auc'],row['metrics']['cost'],[(r['assignments'],r['events']) for r in row['traces']])
            if key in negative and negative[key]!=value:raise AssertionError(('negative control diverged',key))
            negative[key]=value
        if row['policy']=='caea' and (row['setting']=='mixed' or row['setting'].startswith('workers_')):
            timing.append(row)
    rng=np.random.default_rng(20261018);summaries=[];lookup={}
    for (setting,org,policy),cases in sorted(groups.items()):
        r={'setting':setting,'organization':org,'policy':policy,'cases':len(cases),'episodes':sum(map(len,cases.values()))}
        metrics=next(iter(cases.values()))[0]
        for metric in metrics:
            values=[np.mean([v[metric] for v in cases[s]]) for s in sorted(cases)]
            r[metric]=float(np.mean(values))
            if metric in ('auc','utility','elapsed','brier') and not external:r[metric+'_ci']=uncertainty(values,rng)
        summaries.append(r);lookup[setting,org,policy]=r
    contrasts=[]
    for setting,org,policy in sorted(groups):
        if policy not in ('caea','costpath'):continue
        for baseline in (['joint','myopic'] if policy=='caea' else ['caea']):
            target=groups.get((setting,org,baseline))
            if not target:continue
            current=groups[setting,org,policy];common=sorted(set(current)&set(target))
            for metric in ('auc','utility','elapsed'):
                ds=np.array([np.mean([v[metric] for v in current[s]])-np.mean([v[metric] for v in target[s]]) for s in common])
                r={'setting':setting,'organization':org,'policy':policy,'baseline':baseline,'metric':metric,'delta':float(ds.mean())}
                if not external:
                    r['ci']=uncertainty(ds,rng);signs=rng.choice([-1,1],(10000,len(ds)))
                    r['p']=(1+int(np.sum(np.abs((signs*ds).mean(axis=1))>=abs(ds.mean())-1e-15)))/10001
                    r['family']='main' if policy=='caea' else 'costpath_exploratory'
                contrasts.append(r)
    if not external:
        for family in {r['family'] for r in contrasts}:
          for metric in ('auc','utility','elapsed'):
            seq=sorted([r for r in contrasts if r['family']==family and r['metric']==metric],key=lambda r:r['p']);running=0
            for i,r in enumerate(seq):running=max(running,min(1,r['p']*(len(seq)-i)));r['p_holm']=running
    temporal=[]
    for org in ('CENT','P2P','COAL','MKT'):
      for setting in sorted({r['setting'] for r in timing}):
        selected=[r for r in timing if r['organization']==org and r['setting']==setting]
        if not selected:continue
        for model in ('linear','slow','lognormal'):
          for sync in (0,.1,1):
            for horizon in (24,48,96):
                values=[];reached=[];censored=[]
                for r in selected:
                    now=0;u=0;hit=None
                    from .engine import duration
                    for step in r['traces']:
                        now+=max([duration(e,model,r['case_seed']) for e in step['events']] or [1])+sync
                        # Utility is released only at the atomic end of the original batch.
                        idx=step['round']+1;utility=r['curve'][idx][2]
                        if now<=horizon:u=utility
                        if hit is None and utility>=.25:hit=now
                    values.append(u);reached.append(hit is not None and hit<=horizon);censored.append(min(hit if hit is not None else horizon,horizon))
                temporal.append({'organization':org,'setting':setting,'duration_model':model,'sync':sync,'horizon':horizon,'utility_at_horizon':float(np.mean(values)),'reach_rate':float(np.mean(reached)),'restricted_time_to_025':float(np.mean(censored)),'episodes':len(selected)})
    result={'episodes':count,'external_descriptive':external,'negative_controls_exact':bool(negative),'summaries':summaries,'contrasts':contrasts,'temporal':temporal,'bootstrap':0 if external else 4000,'signflip':0 if external else 10000,'seed':20261018}
    (out/'analysis.json').write_text(json.dumps(result,indent=2));print(json.dumps({'episodes':count,'summaries':len(summaries),'contrasts':len(contrasts)}))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--folders',nargs='+',required=True);p.add_argument('--output',required=True);p.add_argument('--external',action='store_true');a=p.parse_args();analyze(a.folders,a.output,a.external)

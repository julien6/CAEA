"""Remote-only analysis; paired case bootstrap (policy seeds averaged first)."""
import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path


def mean(x):return sum(x)/len(x)
def quantile(x,p):
    x=sorted(x); q=(len(x)-1)*p; i=int(q)
    return x[i]+(q-i)*(x[min(i+1,len(x)-1)]-x[i])
def interval(values,rng,reps=4000):
    n=len(values)
    samples=[mean([values[rng.randrange(n)] for _ in range(n)]) for _ in range(reps)]
    return [quantile(samples,.025),quantile(samples,.975)]


def analyze(out,reps=4000):
    out=Path(out)
    rows=[json.loads(p.read_text()) for p in sorted((out/'episodes').glob('*.json'))]
    if not rows:raise ValueError('no episode files')
    g=defaultdict(lambda:defaultdict(list))
    for r in rows:g[r['setting'],r['method']][r['case_seed']].append(r['metrics'])
    rng=random.Random(20261018)
    summaries=[]
    for (setting,method),cases in sorted(g.items()):
        record={'setting':setting,'method':method,'n_cases':len(cases),'n_episodes':sum(map(len,cases.values()))}
        for metric in next(iter(cases.values()))[0]:
            values=[mean([r[metric] for r in values]) for seed,values in sorted(cases.items())]
            record[metric]=mean(values)
            if metric in ('auc','brier','utility','resolved','duplicates','mae'):
                record[metric+'_ci']=interval(values,rng,reps)
        summaries.append(record)
    comparisons=[]
    for setting in sorted({r['setting'] for r in rows}):
        caea=g.get((setting,'caea'))
        if not caea:continue
        for method in sorted({r['method'] for r in rows if r['setting']==setting}-{'caea'}):
            comparator=g[setting,method]
            common=sorted(set(caea)&set(comparator))
            for metric in ('auc','brier','resolved'):
                diffs=[mean([r[metric] for r in caea[s]])-mean([r[metric] for r in comparator[s]]) for s in common]
                ci=interval(diffs,rng,reps)
                # Paired sign-flip randomization, two-sided, Monte Carlo +1 correction.
                obs=abs(mean(diffs)); draws=10000
                p=(1+sum(abs(mean([v*(1 if rng.random()<.5 else -1) for v in diffs]))>=obs-1e-15 for _ in range(draws)))/(draws+1)
                comparisons.append({'setting':setting,'baseline':method,'metric':metric,
                                    'n_cases':len(common),'delta':mean(diffs),'ci':ci,'p':p})
    # Holm correction separately for each metric over all setting-baseline contrasts.
    for metric in ('auc','brier','resolved'):
        family=sorted([r for r in comparisons if r['metric']==metric],key=lambda r:r['p'])
        cumulative=0
        for rank,r in enumerate(family):
            cumulative=max(cumulative,min(1,r['p']*(len(family)-rank)))
            r['p_holm']=cumulative
    result={'summaries':summaries,'comparisons':comparisons,'bootstrap_replicates':reps,
            'analysis_seed':20261018,'aggregation':'mean across policy seeds per case, then equally weighted cases'}
    (out/'analysis.json').write_text(json.dumps(result,indent=2))
    with open(out/'summary.csv','w') as f:
        writer=csv.DictWriter(f,fieldnames=list(summaries[0]));writer.writeheader();writer.writerows(summaries)
    lines=['setting, method, AUC [95% case-bootstrap CI], Brier, duplicate fraction']
    for r in summaries:
        lines.append(f'{r["setting"]}, {r["method"]}, {r["auc"]:.4f} [{r["auc_ci"][0]:.4f}, {r["auc_ci"][1]:.4f}], {r["brier"]:.4f}, {r["duplicates"]:.4f}')
    (out/'summary.txt').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        settings=sorted({r['setting'] for r in rows})
        fig,axes=plt.subplots(1,len(settings),figsize=(4*len(settings),3),squeeze=False)
        colors={'caea':'#0072B2','joint':'#D55E00','independent':'#CC79A7','random':'#777777','single':'#009E73','ucb':'#E69F00'}
        for ax,setting in zip(axes[0],settings):
            for method in colors:
                subset=[r for r in rows if r['setting']==setting and r['method']==method]
                if not subset:continue
                budget=max(r['metrics']['cost'] for r in subset)
                xx=list(range(int(budget)+1)); yy=[]
                for x in xx:
                    vals=[]
                    for r in subset:
                        value=0
                        for c,u in r['curve']:
                            if c<=x:value=u
                        vals.append(value)
                    yy.append(mean(vals))
                ax.plot(xx,yy,label=method,color=colors[method])
            ax.set_title(setting);ax.set_xlabel('Acquisition cost');ax.set_ylim(0,1)
        axes[0,0].set_ylabel('Oracle entropy reduction')
        axes[0,-1].legend(fontsize=7)
        fig.tight_layout();fig.savefig(out/'curves.pdf');fig.savefig(out/'curves.png',dpi=160);plt.close(fig)
    except ImportError:
        (out/'plot-unavailable.txt').write_text('matplotlib missing; numeric analysis complete')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--reps',type=int,default=4000)
    a=p.parse_args();root=Path(a.output)
    if (root/'episodes').exists():analyze(root,a.reps)
    else:
        for child in sorted(root.iterdir()):
            if child.is_dir() and (child/'episodes').exists():analyze(child,a.reps)

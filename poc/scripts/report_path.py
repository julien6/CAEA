import argparse,json,random
from pathlib import Path
from caea.analyze import mean,interval
p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--output',required=True);a=p.parse_args()
root=Path(a.root);out=Path(a.output)
folder=root/'path-ablation'/'outputs';data=json.loads((folder/'analysis.json').read_text())
summaries={(r['setting'],r['method']):r for r in data['summaries']}
rows=[json.loads(f.read_text()) for f in (folder/'episodes').glob('*.json')];assert len(rows)==3200
lookup={(r['setting'],r['case_seed'],r['policy_seed'],r['method']):r for r in rows}
settings=['mixed','direct','pairs','no_refs','noisy_cues','sparse_refs','larger','coalition']
for setting in ['direct','no_refs']:
    for seed in range(6000,6100):
        for ps in (0,1):assert lookup[setting,seed,ps,'caea_informed']['metrics']==lookup[setting,seed,ps,'myopic_informed']['metrics']
rng=random.Random(20261018);comparisons=[]
for setting in settings:
    ds=[mean([lookup[setting,s,ps,'caea_informed']['metrics']['auc']-lookup[setting,s,ps,'myopic_informed']['metrics']['auc'] for ps in (0,1)]) for s in range(6000,6100)]
    ci=interval(ds,rng,4000);observed=abs(mean(ds))
    pv=(1+sum(abs(mean([d*(1 if rng.random()<.5 else -1) for d in ds]))>=observed-1e-15 for _ in range(10000)))/10001
    comparisons.append({'setting':setting,'delta':mean(ds),'ci':ci,'p':pv})
running=0
for rank,r in enumerate(sorted(comparisons,key=lambda r:r['p'])):
    running=max(running,min(1,r['p']*(8-rank)));r['p_holm']=running
lines=[r'\subsection{Separating Immediate Reference Use from Path Propagation}',
       'A comparator that ignores references entirely cannot isolate the value of planning access to an unexposed companion. '
       'We therefore add Myopic+, which uses the same public prior, reservations and companion-read bonus as CAEA+, but gives no reference bonus to opening or discovery actions. '
       'Only ancestor-path propagation differs. This comparator is an observed-reference heuristic, not an exact Bayesian information-gain planner. '
       'The protocol was fixed before fresh case seeds 6000--6099: 100 cases, two policy repetitions, eight conditions and two methods, totaling 3,200 episodes.',
       r'\begin{table}[t]\centering\small',
       r'\caption{CAEA+ versus immediate-reference Myopic+. Intervals are paired 95\% case-bootstrap intervals; Holm correction covers eight conditions.}',
       r'\begin{tabular}{lrrr}\toprule Condition & CAEA+ & Myopic+ & Difference [95\% CI]\\\midrule']
for setting,r in zip(settings,comparisons):
    c=summaries[setting,'caea_informed']['auc'];m=summaries[setting,'myopic_informed']['auc'];ci=r['ci']
    lines.append(f'{setting.replace("_",r"\_")} & {c:.3f} & {m:.3f} & {r["delta"]:.3f} [{ci[0]:.3f}, {ci[1]:.3f}]\\\\')
lines += [r'\bottomrule\end{tabular}\end{table}']
for setting in ['mixed','pairs','larger']:
    r=next(r for r in comparisons if r['setting']==setting)
    lines.append(f'For {setting}, the propagation contrast is {r["delta"]:.4f} '
                 f'(95\\% CI [{r["ci"][0]:.4f}, {r["ci"][1]:.4f}], Holm-adjusted $p={r["p_holm"]:.4f}$).')
lines.append('The two negative controls again match exactly. These results distinguish making an already exposed companion attractive from prioritizing the paid structural operations that expose it. '
             'They bound the empirical contribution of path propagation in this particular tree family; they do not establish superiority over optimal planning or a complete published informative-sensing solver.')
(out/'results_path.tex').write_text('\n\n'.join(lines)+'\n')
(out/'path_report.json').write_text(json.dumps({'comparisons':comparisons,'summaries':data['summaries'],'episodes':3200,'negative_control_identity':True},indent=2))
print(json.dumps(comparisons))

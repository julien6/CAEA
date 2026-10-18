import argparse,json,random
from pathlib import Path
from caea.analyze import mean,interval
p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--output',required=True);a=p.parse_args()
root=Path(a.root);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
folder=root/'prior-robustness'/'outputs'
analysis=json.loads((folder/'analysis.json').read_text())
summary={(r['setting'],r['method']):r for r in analysis['summaries']}
episodes=[json.loads(f.read_text()) for f in (folder/'episodes').glob('*.json')]
assert len(episodes)==8000
lookup={(r['setting'],r['case_seed'],r['policy_seed'],r['method']):r for r in episodes}
settings=['mixed','direct','pairs','no_refs','noisy_cues','sparse_refs','larger','coalition']
for setting in ['direct','no_refs']:
    for seed in range(5000,5100):
        for ps in (0,1):assert lookup[setting,seed,ps,'caea_informed']['metrics']==lookup[setting,seed,ps,'joint_informed']['metrics']
rng=random.Random(20261018);comparisons=[]
for setting in settings:
    diffs=[mean([lookup[setting,s,ps,'caea_informed']['metrics']['auc']-lookup[setting,s,ps,'joint_informed']['metrics']['auc'] for ps in (0,1)]) for s in range(5000,5100)]
    ci=interval(diffs,rng,4000);observed=abs(mean(diffs));draws=10000
    pv=(1+sum(abs(mean([v*(1 if rng.random()<.5 else -1) for v in diffs]))>=observed-1e-15 for _ in range(draws)))/(draws+1)
    comparisons.append({'setting':setting,'delta':mean(diffs),'ci':ci,'p':pv})
running=0
for i,r in enumerate(sorted(comparisons,key=lambda r:r['p'])):
    running=max(running,min(1,r['p']*(8-i)));r['p_holm']=running
lines=[r'\subsection{Stronger Public-Prior Controls on Fresh Cases}',
       'Review of the generator revealed an important prior: every diagnostic artifact has a non-null topic. An unlabeled artifact is therefore noise with probability one in this family. '
       'The generic proxy used above assigns it unresolvedness one, which is conservative for unknown real-world metadata but misspecified for this particular generator. '
       'We therefore add stronger controls rather than attributing all initial gains to a uniquely effective cooperative policy.',
       'Joint+ and CAEA+ set the read score of an unlabeled artifact to zero, leaving every other score and operation unchanged. '
       'The prior comes from the public generative model, not from a hidden artifact value or evaluator annotation. Single+ uses CAEA+ with one action slot. '
       'Outside this generator, missing metadata must not be assumed to establish irrelevance. This is a model-aware variant, not an operational rule for real evidence.',
       'The follow-up protocol was frozen before 100 fresh case seeds 5000--5099, with two policy repetitions and the same eight conditions: 8,000 additional episodes. '
       'No parameters were fitted to these cases. The paired CAEA+--Joint+ comparison uses the same bootstrap and sign-flip procedure, with Holm correction across eight conditions. '
       'It is a declared robustness follow-up prompted by review of the initial design; it does not rewrite the original protocol.',
       r'\begin{table*}[t]\centering\small',
       r'\caption{Stronger prior-aware controls: mean AUC on 100 fresh cases per condition. J=Joint, C=original CAEA, J+=Joint+, C+=CAEA+, S+=Single+. The difference and interval compare C+ with J+.}',
       r'\begin{tabular}{lrrrrrrr}\toprule Condition & J & C & J+ & C+ & S+ & $\Delta$(C+--J+) [95\% CI] & $p_{\rm Holm}$\\\midrule']
for condition,r in zip(settings,comparisons):
    vals=[summary[condition,m]['auc'] for m in ['joint','caea','joint_informed','caea_informed','single_informed']]
    lines.append(condition.replace('_',r'\_')+' & '+' & '.join(f'{v:.3f}' for v in vals)+f' & {r["delta"]:.3f} [{r["ci"][0]:.3f}, {r["ci"][1]:.3f}] & {r["p_holm"]:.4f}\\\\')
lines += [r'\bottomrule\end{tabular}\end{table*}']
for condition in ['mixed','pairs','direct']:
    c=summary[condition,'caea'];j=summary[condition,'joint_informed'];ci=summary[condition,'caea_informed'];ji=summary[condition,'joint_informed']
    lines.append(f'In {condition}, the original CAEA AUC is {c["auc"]:.4f}, compared with {j["auc"]:.4f} for the stronger Joint+ reference. '
                 f'CAEA+ and Joint+ Brier scores are {ci["brier"]:.4f} and {ji["brier"]:.4f}, respectively. '
                 'These values distinguish dependence exploitation from the benefit of using an obvious metadata prior.')
lines.append('The direct and no-reference conditions again give exact episode-wise equality between CAEA+ and Joint+. '
             'Any gain in those conditions would indicate an implementation or accounting discrepancy, since the added obligation mechanism has nothing to act upon. '
             'The results should be interpreted against the stronger references in this table, not only the initial generic proxy. '
             'The original Cl1 remains a statement about its predefined comparator; it is not a claim of superiority over every informed baseline.')
(out/'results_prior.tex').write_text('\n\n'.join(lines)+'\n')
(out/'prior_report.json').write_text(json.dumps({'summaries':analysis['summaries'],'comparisons':comparisons,'negative_control_identity':True,'episodes':8000},indent=2))
print(json.dumps(comparisons))

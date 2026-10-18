"""Generate manuscript tables and figures exclusively inside a Slurm report job."""
import json,argparse
from pathlib import Path
from collections import defaultdict
from caea.org_v2.analysis import analyze
from caea.org_v2.staging import materialize
from caea.org_v2.storage import episode_files,read_episode
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--output',required=True);p.add_argument('--numeric-only',action='store_true');a=p.parse_args();root=Path(a.root);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
main=json.loads((materialize(root,'org-final-report')/'main'/'analysis.json').read_text());robust=json.loads((materialize(root,'org-final-report')/'robust'/'analysis.json').read_text())
if a.numeric_only:
    external=external_control=synthetic=synthetic_control={'summaries':[]}
else:
    external=analyze([materialize(root,'org-final-external-llm')],out/'external',True)
    external_control=analyze([materialize(root,'org-final-external-control')],out/'external_control',True)
    synthetic=analyze([materialize(root,'org-final-synthetic-recovered-v2')],out/'synthetic')
    synthetic_control=analyze([materialize(root,'org-final-synthetic-oracle')],out/'synthetic_control')
orgs=['CENT','P2P','COAL','MKT'];pols=['joint','myopic','caea','costpath'];index=lambda d:{(r['setting'],r['organization'],r['policy']):r for r in d['summaries']}
m=index(main);r=index(robust);e=index(external);ec=index(external_control);sy=index(synthetic);sc=index(synthetic_control)
contr={(c['setting'],c['organization'],c['policy'],c['baseline'],c['metric']):c for c in main['contrasts']}
def plot_numeric(contr):
    fig,axes=plt.subplots(1,2,figsize=(7.2,3.0),sharey=True)
    for ax,condition in zip(axes,['mixed','pairs']):
        for offset,baseline,color in [(-.12,'joint','#0072B2'),(.12,'myopic','#D55E00')]:
            cs=[contr[condition,o,'caea',baseline,'auc'] for o in orgs]
            ax.errorbar([i+offset for i in range(4)],[c['delta'] for c in cs],yerr=[[c['delta']-c['ci'][0] for c in cs],[c['ci'][1]-c['delta'] for c in cs]],fmt='o',color=color,label='CAEA - '+baseline)
        maximum=max(contr[c,o,'caea',b,'auc']['ci'][1] for c in ('mixed','pairs') for o in orgs for b in ('joint','myopic'))
        minimum=min(0,min(contr[c,o,'caea',b,'auc']['ci'][0] for c in ('mixed','pairs') for o in orgs for b in ('joint','myopic')))
        ax.set_ylim(minimum,maximum*1.1)
        ax.axhline(0,color='gray',lw=.7);ax.set_xticks(range(4),orgs);ax.set_title(condition);ax.set_ylabel('Paired AUC difference');ax.legend(fontsize=8)
    fig.tight_layout();fig.savefig(out/'organization_effects.pdf');plt.close(fig)

lines=[r'\subsection{Organization-by-Acquisition Factorial Study}',f'The final corrected primary cohort contains {main["episodes"]:,} episodes. Direct and absent-reference controls give identical acquisitions and oracle utility across the four acquisition cores within each organization. This is a mechanism check, not four independent strong baselines.',r'\begin{table*}[t]\centering\small',r'\caption{Primary numerical AUC. The last column is CAEA--Joint with paired 95\% case-bootstrap interval. Holm correction is over the prespecified main contrasts.}',r'\begin{tabular}{llrrrrl}\toprule Condition & Org. & Joint & Myopic & CAEA & CostPath & CAEA--Joint [95\% CI]\\\midrule']
for setting in ['mixed','pairs','wrong_refs50','direct','no_refs','sparse_refs']:
    if setting in ('direct','no_refs','sparse_refs'):lines.append(r'\iflongversion')
    for org in orgs:
        c=contr[setting,org,'caea','joint','auc'];values=' & '.join(f'{m[setting,org,pol]["auc"]:.3f}' for pol in pols)
        lines.append(f'{setting.replace("_",r"\_")} & {org} & {values} & {c["delta"]:.3f} [{c["ci"][0]:.3f}, {c["ci"][1]:.3f}]\\\\')
    if setting in ('direct','no_refs','sparse_refs'):lines.append(r'\fi')
lines += [r'\bottomrule\end{tabular}\end{table*}']
lines.append('In mixed and pairs, CENT and COAL have identical mean acquisition AUC under three workers and immediate communication. A full three-member coalition can reproduce the centralized valuation and reservation process; this is a conditional collapse, not evidence that the protocols are universally equivalent or four independent confirmations. Their messages and organizational events differ. The robustness study exposes the limitation of coalition-local sharing when the team exceeds the maximum group size.')
lines.extend([r'\begin{table*}[t]\centering\small',r'\caption{Propagation-specific contrast and exploratory path-cost variant. Paired 95\% intervals are by case. Main Holm correction covers 48 CAEA contrasts; CostPath uses its separate 24-contrast family.}',r'\begin{tabular}{llrrrr}\toprule Condition & Org. & CAEA--Myopic [95\% CI] & $p_{\rm Holm}$ & CostPath--CAEA [95\% CI] & $p_{\rm Holm}$\\\midrule'])
for setting in ['mixed','pairs','wrong_refs50','direct','no_refs','sparse_refs']:
    if setting in ('direct','no_refs','sparse_refs'):lines.append(r'\iflongversion')
    for org in orgs:
        c=contr[setting,org,'caea','myopic','auc'];cp=contr[setting,org,'costpath','caea','auc']
        lines.append(f'{setting.replace("_",r"\_")} & {org} & {c["delta"]:.3f} [{c["ci"][0]:.3f}, {c["ci"][1]:.3f}] & {c["p_holm"]:.4f} & {cp["delta"]:.3f} [{cp["ci"][0]:.3f}, {cp["ci"][1]:.3f}] & {cp["p_holm"]:.4f}\\\\')
    if setting in ('direct','no_refs','sparse_refs'):lines.append(r'\fi')
lines.append(r'\bottomrule\end{tabular}\end{table*}')
lines.append('The propagation contrast isolates the value of prioritizing paid access operations rather than only attractive companion reads. CostPath is an exploratory change in score denominator, not a new default selected after seeing the final cases.')
lines += [r'\begin{figure*}[t]\centering\includegraphics[width=.95\textwidth]{organization_effects.pdf}',r'\caption{Within-organization acquisition contrasts. Error bars are paired case-bootstrap intervals; organization differences also include their different information flows.}\end{figure*}',r'\subsection{Robustness, Communication and Sequential Feedback}',f'The sensitivity cohort contains {robust["episodes"]:,} episodes on new case seeds. Each modification is compared within its own case family; this is not an exhaustive interaction study.',r'\begin{table*}[t]\centering\small',r'\caption{Robustness: CAEA--Joint AUC differences, paired by case. Full intervals and corrected tests are retained in the analysis artifact.}',r'\begin{tabular}{lrrrr}\toprule Condition & CENT & P2P & COAL & MKT\\\midrule']
for setting in sorted({v['setting'] for v in robust['summaries']}):
    vals=[r[setting,org,'caea']['auc']-r[setting,org,'joint']['auc'] for org in orgs]
    lines.append(setting.replace('_',r'\_')+' & '+' & '.join(f'{v:.3f}' for v in vals)+r'\\')
lines += [r'\bottomrule\end{tabular}\end{table*}',r'\begin{table*}[t]\centering\small',r'\caption{CAEA under explicit protocols in the primary mixed condition. Bytes include serialized observation and assignment payloads. Times are simulated, not measured hardware speedups.}',r'\begin{tabular}{lrrrrrrr}\toprule Org. & Paid cost & Terminal utility & Brier & Duplicate fraction & Messages & KiB & Simulated time\\\midrule']
for org in orgs:
    row=m['mixed',org,'caea'];lines.append(f'{org} & {row["cost"]:.2f} & {row["utility"]:.3f} & {row["brier"]:.3f} & {row["duplicates"]:.3f} & {row["messages"]:.1f} & {row["message_bytes"]/1024:.1f} & {row["elapsed"]:.1f}\\\\')
lines += [r'\bottomrule\end{tabular}\end{table*}',r'\begin{table*}[t]\centering\small',r'\caption{Matched robustness cases: CAEA utility at time 48 and attainment of utility .25, linear durations and synchronization .1. Non-attaining episodes are retained.}',r'\begin{tabular}{lrrrrrrrr}\toprule & \multicolumn{2}{c}{1 worker} & \multicolumn{2}{c}{2 workers} & \multicolumn{2}{c}{4 workers} & \multicolumn{2}{c}{8 workers}\\ Org. & Utility & Reach & Utility & Reach & Utility & Reach & Utility & Reach\\\midrule']
for org in orgs:
    vals=[]
    for n in (1,2,4,8):
        t=next(t for t in robust['temporal'] if t['organization']==org and t['setting']==f'workers_{n}' and t['duration_model']=='linear' and t['sync']==.1 and t['horizon']==48)
        vals.extend([t['utility_at_horizon'],t['reach_rate']])
    lines.append(org+' & '+' & '.join(f'{v:.3f}' for v in vals)+r'\\')
lines += [r'\bottomrule\end{tabular}\end{table*}', 'These endpoints answer a different question from information per paid acquisition. The archived temporal analysis also varies synchronization, duration distributions and horizons. Higher worker count may improve one endpoint while reducing cost efficiency; no universal parallel advantage follows.',r'\subsection{Documentary Acquisition and Interpretation}',r'\begin{table*}[t]\centering\small',r'\caption{Documentary studies: Qwen CAEA/Joint AUC, and corresponding deterministic or exact-control AUC. External columns measure required witness acquisition, synthetic columns oracle entropy reduction; their magnitudes are not interchangeable.}',r'\begin{tabular}{lrrrrrrrr}\toprule & \multicolumn{4}{c}{Synthetic} & \multicolumn{4}{c}{External M57 documentation}\\ Org. & Q-C & Q-J & Exact-C & Exact-J & Q-C & Q-J & Det-C & Det-J\\\midrule']
if a.numeric_only:
    lines=lines[:lines.index(r'\subsection{Documentary Acquisition and Interpretation}')]
    from org_temporal import contrasts as temporal_contrasts
    paired_time=temporal_contrasts(root)
    (out/'temporal_contrasts.json').write_text(json.dumps(paired_time,indent=2))
    lines.append(r'\subsection{Documentary Experiments in Progress}')
    lines.append('This is a numerical layout preview. Documentary inference and final recorded-response validation are still running; no documentary performance values are inserted in this preview.')
    (out/'results_org.tex').write_text('\n\n'.join(lines)+'\n')
    plot_numeric(contr)
    raise SystemExit(0)
for org in orgs:
    vals=[sy['mixed',org,p]['auc'] for p in ('caea','joint')]+[sc['mixed',org,p]['auc'] for p in ('caea','joint')]+[e['external',org,p]['auc'] for p in ('caea','joint')]+[ec['external',org,p]['auc'] for p in ('caea','joint')]
    lines.append(org+' & '+' & '.join(f'{v:.3f}' for v in vals)+r'\\')
lines += [r'\bottomrule\end{tabular}\end{table*}']
lines.insert(lines.index(r'\subsection{Documentary Acquisition and Interpretation}'),'With eight workers, the CAEA mean AUCs are '+', '.join(f'{org} {r["workers_8",org,"caea"]["auc"]:.3f}' for org in orgs)+'. This counterexample to universal coalition superiority is retained rather than selecting only favorable organizations.')
for stress in ('workers_8','delay_3','wrong_refs_0.75'):
    details=[]
    for org in orgs:
        c=next(c for c in robust['contrasts'] if c['setting']==stress and c['organization']==org and c['metric']=='auc')
        details.append(f"{org}: {c['delta']:.3f} [{c['ci'][0]:.3f}, {c['ci'][1]:.3f}], $p_{{\\rm Holm}}={c['p_holm']:.4f}$")
    lines.insert(lines.index(r'\subsection{Documentary Acquisition and Interpretation}'),f"For {stress.replace('_',r'\_')}, CAEA--Joint AUC contrasts are "+'; '.join(details)+'. These are sensitivity results, not evidence of universal robustness.')
from org_temporal import contrasts as temporal_contrasts
paired_time=temporal_contrasts(root)
(out/'temporal_contrasts.json').write_text(json.dumps(paired_time,indent=2))
time_rows=[r'\begin{table*}[t]\centering\small',r'\caption{Matched CAEA worker-count contrasts versus one worker at time 48 (linear duration, synchronization .1). Utility intervals are paired case-bootstrap; Holm correction is separate over twelve contrasts for each endpoint.}',r'\begin{tabular}{llrrrr}\toprule Org. & Workers & $\Delta$ utility [95\% CI] & $p_{\rm Holm}$ & $\Delta$ reach(.25) & $p_{\rm Holm}$\\\midrule']
for contrast in paired_time:
    if contrast['metric']=='utility_at_48':
        reach=next(c for c in paired_time if c['organization']==contrast['organization'] and c['workers']==contrast['workers'] and c['metric']!='utility_at_48')
        time_rows.append(f"{contrast['organization']} & {contrast['workers']} & {contrast['delta']:.3f} [{contrast['ci'][0]:.3f}, {contrast['ci'][1]:.3f}] & {contrast['p_holm']:.4f} & {reach['delta']:.3f} & {reach['p_holm']:.4f}"+r'\\')
time_rows.extend([r'\bottomrule\end{tabular}\end{table*}', 'Fixed-horizon utility improves in eleven worker-count contrasts and decreases for eight-member COAL. None of the twelve threshold-attainment contrasts passes its Holm-adjusted .05 level. These endpoints do not support a general claim of faster threshold attainment.'])
lines[lines.index(r'\subsection{Documentary Acquisition and Interpretation}'):lines.index(r'\subsection{Documentary Acquisition and Interpretation}')]=time_rows
for org in orgs:
    c=next(c for c in synthetic['contrasts'] if c['organization']==org and c['metric']=='auc' and c['baseline']=='joint')
    lines.append(f'Synthetic {org}: CAEA--Joint {c["delta"]:.3f} [{c["ci"][0]:.3f}, {c["ci"][1]:.3f}], $p_{{\\rm Holm}}={c["p_holm"]:.4f}$. External CAEA witness-quote recall is {e["external",org,"caea"]["witness_quote_recall"]:.3f}. External contrasts are descriptive within one scenario.')
# Audit all calls independently of successful episode metrics.
audit={};totalcalls=0;attempts=0;inputtokens=0;outputtokens=0
for name in ('org-final-synthetic-recovered-v2','org-final-external-llm'):
    folder=materialize(root,name);calls=errors=refs=quotes=0;maxprompt=0
    wall_seconds=eval_seconds=load_seconds=server_seconds=0.0
    diagnostic=diagnostic_exact=references=references_exact=noise=noise_exact=0
    episode_cases={};case_cache={}
    for path in episode_files(folder):
        ep=read_episode(path);key=ep.get('task_id') or f'{ep["setting"]}-{ep["case_seed"]}'
        if key not in case_cache:case_cache[key]=json.loads((folder/'cases'/(key+'.json')).read_text())
        episode_cases[ep['id']]=case_cache[key]
    for line in (folder/'llm_calls.jsonl').open():
        row=json.loads(line);attempts+=1
        if 'request' in row:calls+=1;totalcalls+=1
        errors+=bool(row.get('error'));refs+=row.get('rejected_mentions',0);quotes+=row.get('rejected_quotes',0)
        case=episode_cases[row['episode']]
        if not case.get('external'):
            real=case['nodes'][row['eid']]['record'];parsed=row.get('parsed')
            if parsed and parsed['kind']=='share':parsed={**parsed,'parts':2}
            if real['kind']=='noise':noise+=1;noise_exact+=int(parsed==real)
            else:diagnostic+=1;diagnostic_exact+=int(parsed==real)
            if real.get('target_path'):
                references+=1;references_exact+=int(bool(parsed) and parsed.get('target_path')==real['target_path'])
        response=row.get('response',{})
        wall_seconds+=row.get('wall_seconds',0);eval_seconds+=response.get('eval_duration',0)/1e9;load_seconds+=response.get('load_duration',0)/1e9;server_seconds+=response.get('total_duration',0)/1e9
        inputtokens+=response.get('prompt_eval_count',0);outputtokens+=response.get('eval_count',0);maxprompt=max(maxprompt,row.get('requested_input_tokens',row.get('input_tokens',0)))
    audit[name]={'calls':calls,'errors':errors,'rejected_quotes':quotes,'rejected_mentions':refs,'max_prompt':maxprompt,'wall_seconds':wall_seconds,'ollama_eval_seconds':eval_seconds,'ollama_load_seconds':load_seconds,'ollama_total_seconds':server_seconds,'diagnostic':diagnostic,'diagnostic_exact':diagnostic_exact,'references':references,'references_exact':references_exact,'noise':noise,'noise_exact':noise_exact}
    label={'org-final-synthetic-recovered-v2':'Synthetic study (complete recovered archives)','org-final-external-llm':'External study'}[name]
    lines.append(f'{label}: {calls:,} dispatched calls, {errors:,} failed or refused attempts, maximum counted input {maxprompt:,} tokens. Rejected external quote strings: {quotes}; rejected filename strings: {refs}. Measured request wall time totals {wall_seconds:.1f} seconds; server generation and loading total {eval_seconds:.1f} and {load_seconds:.1f} seconds, respectively. These request sums are distinct from allocated GPU-hours and simulated acquisition durations.')
    if diagnostic:
        lines.append(f'Diagnostic typed records are exact in {diagnostic_exact}/{diagnostic} attempts; references in {references_exact}/{references}; noise in {noise_exact}/{noise}. Noise-dominated aggregate accuracy is not used to conceal diagnostic errors.')
lines.append('Literal external filename references may be rare or absent. The external comparison therefore tests transfer and limitations, not a guaranteed replication of the deliberately complementary synthetic effect. Source acquisition coverage must not be mistaken for correct extracted answers.')
# Full research version includes the external audit rubric and actual system strings.
lines.append(r'\iflongversion')
def tex(v):
    return str(v).replace('\\',r'\textbackslash{}').replace('&',r'\&').replace('_',r'\_').replace('%',r'\%').replace('#',r'\#').replace('{',r'\{').replace('}',r'\}')
lines.extend([r'\subsection{External Witness Rubric and Recorded Instructions}',r'\begin{table*}[t]\centering\scriptsize',r'\caption{External question rubric. D=development, T=test. The raw task artifact contains the full question, all witnesses, offsets and hashes. Source names are original PDF basenames.}',r'\begin{tabular}{p{.06\textwidth}p{.43\textwidth}p{.42\textwidth}}\toprule ID & Question & Required source witnesses\\\midrule'])
from caea.org_v2.external import TASKS
for tid,question,witnesses in TASKS:
    desc='; '.join(f'{name}, p.{page+1}: {span}' for name,page,span in witnesses)
    lines.append(tex(tid)+' & '+tex(question)+' & '+tex(desc)+r'\\')
lines.append(r'\bottomrule\end{tabular}\end{table*}')
for name,title in [('org-final-synthetic-recovered-v2','Synthetic document extraction'),('org-final-external-llm','External source-span extraction')]:
    folder=materialize(root,name)
    for rawline in (folder/'llm_calls.jsonl').open():
        raw=json.loads(rawline)
        if 'request' in raw:
            prompt=raw['request']['prompt'];system=prompt.split('<|im_start|>system\n',1)[1].split('<|im_end|>',1)[0]
            lines.extend([tex(title)+'. The recorded system instruction is:',r'\begin{quote}\small '+tex(system)+r'\end{quote}']);break
lines.append(r'\fi')
(out/'results_org.tex').write_text('\n\n'.join(lines)+'\n')
(out/'documentary_audit.json').write_text(json.dumps({'runs':audit,'calls':totalcalls,'attempts':attempts,'input_tokens':inputtokens,'output_tokens':outputtokens},indent=2))
plot_numeric(contr)
(out/'study_summary.json').write_text(json.dumps({'main_episodes':main['episodes'],'robust_episodes':robust['episodes'],'synthetic_llm_episodes':synthetic['episodes'],'synthetic_exact_episodes':synthetic_control['episodes'],'external_llm_episodes':external['episodes'],'external_deterministic_episodes':external_control['episodes'],'main_negative_controls_exact':main['negative_controls_exact']},indent=2))

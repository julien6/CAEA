import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--output',required=True);a=p.parse_args()
root=Path(a.root);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
items=[]
for run,model in [('strict15-final','1.5B'),('strict7-final','7B')]:
    folder=root/run/'outputs'
    analysis=json.loads((folder/'analysis.json').read_text());audit=json.loads((folder/'audit.json').read_text())
    metadata=json.loads((folder/'metadata.json').read_text())
    assert len(list((folder/'episodes').glob('*.json')))==24
    r=next(r for r in analysis['comparisons'] if r['metric']=='auc' and r['baseline']=='joint')
    items.append({'run':run,'model':model,'analysis':analysis,'audit':audit,'metadata':metadata,'contrast':r})
running=0
for i,item in enumerate(sorted(items,key=lambda x:x['contrast']['p'])):
    running=max(running,min(1,item['contrast']['p']*(2-i)));item['contrast']['p_holm_global']=running
lines=[r'\subsection{Prospective Follow-Up: Required Evidence Fields}',
       'Inspection of the initial experiment identified valid JSON responses omitting essential evidence fields. '
       'This is a pipeline-contract failure: syntactic validity alone does not provide the values needed for inference. '
       'We therefore performed a declared follow-up on new case seeds 3000--3011, with the protocol frozen before those runs. '
       'This follow-up was motivated by observed initial errors and must not be interpreted as an independent pre-experiment prediction or substituted for the original Cl3 verdict.',
       'The follow-up keeps B=48, the 768-token window, 160 reserved output tokens, both model identities, policies and acquisition scores. '
       'All JSON properties become required. Instructions specify neutral values for fields irrelevant to noise; the validator still discards those values when kind is noise. '
       'No annotation fills a missing LLM value. A separate interface hardening passes only raw text and public metadata to the interpreter; the previous implementation already constructed its prompt from those fields alone. '
       'The frozen follow-up source commit is 6638c30.',
       r'\begin{table*}[t]\centering\small',
       r'\caption{Strict-schema follow-up on 12 fresh cases. Diagnostic extraction is audited separately below; the acquisition policy is unchanged.}',
       r'\begin{tabular}{llrrrr}\toprule Model & Method & AUC [95\% CI] & Brier & Posterior MAE & Typed accuracy\\\midrule']
for item in items:
    for r in item['analysis']['summaries']:
        ci=r['auc_ci']
        lines.append(f'{item["model"]} & {r["method"]} & {r["auc"]:.3f} [{ci[0]:.3f}, {ci[1]:.3f}] & {r["brier"]:.3f} & {r["mae"]:.3f} & {r["typed_accuracy"]:.3f}\\\\')
lines += [r'\bottomrule\end{tabular}\end{table*}']
for item in items:
    r=item['contrast'];ci=r['ci'];c=item['audit']['counts'];d=item['audit']['diagnostic']
    success=r['delta']>=.02 and ci[0]>0 and r['p_holm_global']<.05;item['followup_supported']=success
    lines.append(f'With {item["model"]}, CAEA--Joint AUC is {r["delta"]:.4f} '
       f'(95\\% CI [{ci[0]:.4f}, {ci[1]:.4f}], two-model Holm-adjusted $p={r["p_holm_global"]:.4f}$). '
       'The follow-up criterion is '+('met. ' if success else 'not met. ')+
       f'Diagnostic exact extraction is {d.get("exact",0)}/{d["attempts"]}; correct references are {d.get("correct_reference",0)}/{d.get("references",0)}. '
       f'There are {c.get("http_calls",0)} HTTP calls, {c.get("context_overflow",0)} preventive overflows, '
       f'{c.get("input_tokens",0):,} input tokens and {c.get("output_tokens",0):,} output tokens. '
       f'Mean HTTP latency is {item["audit"]["mean_http_seconds"]:.3f} s including load overhead.')
oracle=json.loads((root/'strict-oracle'/'outputs'/'analysis.json').read_text())
r={r['method']:r for r in oracle['summaries']}
lines.append(f'The exact-extraction control on the same fresh cases gives AUC {r["caea"]["auc"]:.4f} for CAEA and {r["joint"]["auc"]:.4f} for Joint. '
   'Different case sets prevent attributing every change from the first experiment to the schema alone. '
   'The follow-up tests usability of the stricter contract, rather than estimating a clean same-case causal effect of prompt design. '
   'A larger schema-by-model study would be needed for that stronger claim.')
# A deterministic qualitative trace: first completed pair in mixed, case 1000, policy seed 0.
casepath=root/'numeric-v1'/'outputs'/'episodes'/'mixed-1000-0-caea.json'
episode=json.loads(casepath.read_text());seen={};chosen=None
for idx,t in enumerate(episode['traces']):
    r=t.get('record') or {}
    if r.get('kind')=='share':
        if r['pair'] in seen:
            earlier=seen[r['pair']]
            if earlier[1]['record']['slot']!=r['slot']:
                chosen=(earlier[0],idx,earlier[1],t);break
        seen[r['pair']]=(idx,t)
lines += [r'\subsection{A Fixed-Case Acquisition Trace}']
if chosen:
    start,end,first,last=chosen
    lines.append(f'For qualitative inspection we use the fixed numerical case seed 1000 and policy seed 0, '
                 f'not the best-performing episode. Its first completed pair is \\texttt{{{first["record"]["pair"]}}} '
                 f'for hypothesis H{first["record"]["h"]}. The two source values are {first["record"]["bit"]} and {last["record"]["bit"]}; '
                 'neither fragment alone provides information under the specified channel model. '
                 'The following actual actions connect first acquisition to completion. The written path guides ordinary discovery rather than bypassing it.')
    lines += [r'\begin{table}[t]\centering\scriptsize',r'\caption{First completed pair in a fixed CAEA numerical episode; rounds are zero-indexed common-state versions.}',r'\begin{tabular}{rll}\toprule Round & Operation & Node\\\midrule']
    for t in episode['traces'][start:end+1]:
        act=t['action'];lines.append(f'{t["version"]} & {act["op"]} & \\texttt{{{act["node"]}}}\\\\')
    lines += [r'\bottomrule\end{tabular}\end{table}']
lines.append('The trace is illustrative and adds no independent statistical sample. '
             'It exposes the mechanism whose average effect is assessed in the paired tables, including the paid structural steps between related observations.')
(out/'results_strict.tex').write_text('\n\n'.join(lines)+'\n')
(out/'strict_report.json').write_text(json.dumps(items,indent=2))
print(json.dumps({'models_supported':sum(i['followup_supported'] for i in items),'http_calls':sum(i['audit']['counts'].get('http_calls',0) for i in items)}))

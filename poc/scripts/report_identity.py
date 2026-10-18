import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--output',required=True);a=p.parse_args()
root=Path(a.root);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
folder=root/'identity7-final'/'outputs'
analysis=json.loads((folder/'analysis.json').read_text());audit=json.loads((folder/'audit.json').read_text())
metadata=json.loads((folder/'metadata.json').read_text())
oracle=json.loads((root/'identity-oracle'/'outputs'/'analysis.json').read_text())
assert len(list((folder/'episodes').glob('*.json')))==24
contrast=next(r for r in analysis['comparisons'] if r['metric']=='auc' and r['baseline']=='joint')
lines=[r'\subsection{Exploratory Identity-Correlation Investigation Cases}',
       'To move beyond explicitly numbered bit fragments, we add 12 fresh synthetic investigation cases (seeds 4000--4011) with a fictional company and target employee. '
       'Four questions concern restricted-archive access, USB copying, external transmission and collaborator approval. '
       'Routine office email, invoices and maintenance notes provide distractors. Directory exports identify an employee account; audit exports identify the actor account for an event. '
       'Each correlation key defines its own local pair of account aliases. A pair of directory and audit exports can therefore identify whether the target was the actor, while either alone is uninformative under the model.',
       'This is a deterministic rendering of the same hidden-channel construction, not an expert-validated simulation of judicial practice. '
       'For an identity share $K$ the directory reports account U$_K$; for the second share $X_1$ the audit reports actor U$_{1-X_1}$. '
       'The accounts match exactly when $K\\oplus X_1=1$. A witness statement renders a direct channel, and the benchmark quality class S denotes reliability 0.85. '
       'The corpus truth is fixed before text rendering. This preserves an exact oracle while giving the interpreter an identity-join task rather than a literal binary-value phrase.',
       'The extension uses Qwen2.5 7B, the required-field schema, context 768, output reserve 160, temperature zero, model seed 42, policy seed zero and B=48. '
       'All acquisition scores, tree sizes and costs are unchanged. The prompt explains the account-to-record conversion and never receives hidden annotations. '
       'The configuration was frozen before the new cases were run. The larger model was chosen based on the preceding technical phase, so this is an exploratory domain rendering rather than a new independent confirmatory claim.',
       r'\begin{table}[t]\centering\small',
       r'\caption{Identity-correlation rendering: 12 new cases, Qwen2.5 7B. Exact controls share the same underlying cases.}',
       r'\begin{tabular}{llrr}\toprule Interpreter & Policy & AUC [95\% CI] & Brier\\\midrule']
for kind,result in [('Qwen',analysis),('Exact',oracle)]:
    for r in result['summaries']:
        ci=r['auc_ci'];lines.append(f'{kind} & {r["method"]} & {r["auc"]:.3f} [{ci[0]:.3f}, {ci[1]:.3f}] & {r["brier"]:.3f}\\\\')
lines += [r'\bottomrule\end{tabular}\end{table}']
c=audit['counts'];d=audit['diagnostic'];ci=contrast['ci']
lines.append(f'The exploratory CAEA--Joint AUC difference is {contrast["delta"]:.4f} '
       f'(paired 95\\% CI [{ci[0]:.4f}, {ci[1]:.4f}], unadjusted exploratory sign-flip $p={contrast["p"]:.4f}$). '
       'This p-value is not corrected over the entire sequence of studies and does not revise Cl3. '
       f'The diagnostic exact count is {d.get("exact",0)}/{d["attempts"]}, reference exact count {d.get("correct_reference",0)}/{d.get("references",0)}, '
       f'with {c.get("http_calls",0)} HTTP calls, {c.get("context_overflow",0)} context refusals, '
       f'{c.get("input_tokens",0):,} input tokens and {c.get("output_tokens",0):,} output tokens. '
       f'The maximum dispatched prompt is {audit["max_input_tokens"]} tokens and mean HTTP latency is {audit["mean_http_seconds"]:.3f} s.')
lines.append('Human-readable office documents increase interpretability of the prototype but do not establish forensic realism. '
       'The source types, two-account alias space, fixed reliability and exact path references remain controlled simplifications. '
       'Dates are export metadata rather than a validated causal timeline, and the four questions remain independent. '
       'No claim of representativeness, legal sufficiency or transfer to a public forensic corpus follows from this extension.')
(out/'results_identity.tex').write_text('\n\n'.join(lines)+'\n')
(out/'identity_report.json').write_text(json.dumps({'analysis':analysis,'audit':audit,'metadata':metadata,'oracle':oracle},indent=2))
print(json.dumps({'http_calls':c.get('http_calls',0),'auc_delta':contrast['delta'],'ci':ci}))

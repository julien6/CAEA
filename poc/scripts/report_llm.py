"""Held-out text report and joint Holm family; run only in a compute allocation."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--output',required=True);a=p.parse_args()
root=Path(a.root);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
items=[]
for run,model in [('llm15-final','1.5B'),('llm7-final','7B')]:
    for context in (384,768):
        folder=root/run/'outputs'/f'ctx{context}'
        analysis=json.loads((folder/'analysis.json').read_text())
        audit=json.loads((folder/'audit.json').read_text())
        metadata=json.loads((folder/'metadata.json').read_text())
        assert len(list((folder/'episodes').glob('*.json')))==24
        contrast=next(r for r in analysis['comparisons'] if r['baseline']=='joint' and r['metric']=='auc')
        items.append({'model':model,'context':context,'run':run,'analysis':analysis,'audit':audit,'metadata':metadata,'contrast':contrast})
family=sorted(items,key=lambda x:x['contrast']['p']);running=0
for i,item in enumerate(family):
    running=max(running,min(1,item['contrast']['p']*(len(family)-i)))
    item['contrast']['p_holm_global']=running
lines=[r'\subsection{Held-Out Configuration and Results}',
       r'We evaluate 12 held-out case seeds (2000--2011), Joint and CAEA, and windows of 384 and 768 tokens with a 160-token output reserve. The two Qwen models use GGUF Q4\_K\_M weights, temperature zero, seed 42, one parallel inference slot and no response memoization. Each model--window condition contains 24 episodes; the full text experiment contains 96. Both models were downloaded and their exact tokenizers pinned before the final runs. Within this initial experiment, the prompt and schema were frozen after pilots 900 and 901 and remained unchanged across all cases 2000--2011. The separately declared follow-up is reported next.',
       r'\begin{table*}[t]\centering\small',
       r'\caption{Held-out text extraction results, 12 cases per row. Typed accuracy includes noise; the diagnostic-only audit below is essential. AUC uses the original acquired records even when extraction fails.}',
       r'\begin{tabular}{lrlrrrr} \toprule Model & Window & Method & AUC [95\% CI] & Brier & Posterior MAE & Typed accuracy\\\midrule']
for item in items:
    for r in item['analysis']['summaries']:
        ci=r['auc_ci']
        lines.append(f'{item["model"]} & {item["context"]} & {r["method"]} & {r["auc"]:.3f} [{ci[0]:.3f}, {ci[1]:.3f}] & {r["brier"]:.3f} & {r["mae"]:.3f} & {r["typed_accuracy"]:.3f}\\\\')
lines += [r'\bottomrule\end{tabular}\end{table*}',
          r'\begin{table}[t]\centering\small',
          r'\caption{Paired CAEA--Joint text AUC contrasts. Holm correction jointly covers all four model--window contrasts.}',
          r'\begin{tabular}{lrrr}\toprule Model/window & Difference & 95\% CI & $p_{\rm Holm}$\\\midrule']
for item in items:
    r=item['contrast'];ci=r['ci']
    lines.append(f'{item["model"]}/{item["context"]} & {r["delta"]:.3f} & [{ci[0]:.3f}, {ci[1]:.3f}] & {r["p_holm_global"]:.4f}\\\\')
lines += [r'\bottomrule\end{tabular}\end{table}']
for item in items:
    r=item['contrast'];success=r['delta']>=.02 and r['ci'][0]>0 and r['p_holm_global']<.05
    item['claim_supported']=success
for item in [x for x in items if x['context']==768]:
    r=item['contrast'];ci=r['ci']
    lines.append(f'At 768 tokens with {item["model"]}, the paired AUC difference is {r["delta"]:.4f} '
       f'(95\\% CI [{ci[0]:.4f}, {ci[1]:.4f}], adjusted $p={r["p_holm_global"]:.4f}$). '
       'The predefined model-specific Cl3 criterion is '+('met.' if item['claim_supported'] else 'not met.'))
number=sum(i['claim_supported'] for i in items if i['context']==768)
lines.append('Overall Cl3 is '+('supported for both tested extractors.' if number==2 else 'partially supported across extractors.' if number==1 else 'not supported by the held-out extractor results.')+
             ' This verdict is conditional on the controlled text rendering and does not establish transfer to realistic judicial corpora.')
lines += [r'\subsection{Capacity Failures and Diagnostic Extraction Audit}',
          r'\begin{table*}[t]\centering\small',
          r'\caption{Invocation-level diagnostic audit across both policies. Repeated reads across methods are repeated workload, not independent statistical samples. Refusal counts include preventive context overflow. Diagnostic exact and reference exact are counts against evaluator annotations, not model self-assessments.}',
          r'\begin{tabular}{lrrrrrrr}\toprule Model/window & Attempts & HTTP calls & Overflow & Diagnostic exact & Reference exact & Input tokens & Output tokens\\\midrule']
for item in items:
    audit=item['audit'];c=audit['counts'];d=audit['diagnostic']
    lines.append(f'{item["model"]}/{item["context"]} & {c["attempts"]} & {c.get("http_calls",0)} & {c.get("context_overflow",0)} & {d.get("exact",0)}/{d["attempts"]} & {d.get("correct_reference",0)}/{d.get("references",0)} & {c.get("input_tokens",0):,} & {c.get("output_tokens",0):,}\\\\')
lines += [r'\bottomrule\end{tabular}\end{table*}']
for item in items:
    c=item['audit']['counts'];d=item['audit']['diagnostic']
    lines.append(f'{item["model"]}/{item["context"]}: {c.get("false_diagnostic",0)} noise artifacts were accepted as diagnostic; '
          f'{d.get("correct_bit",0)} of {d["attempts"]} acquired diagnostic artifacts had the correct accepted bit and hypothesis. '
          f'The maximum dispatched input length was {item["audit"]["max_input_tokens"]} tokens, '
          f'and mean dispatched HTTP latency was {item["audit"]["mean_http_seconds"]:.3f} s, including load overhead.')
lines += ['At 384 tokens, the fixed prompt plus output reserve can exclude diagnostic artifacts while allowing shorter noise records. '
          'A high aggregate typed accuracy in that condition is therefore misleading: it is dominated by correctly identifying noise. '
          'The oracle can still score information in acquired documents which the interpreter failed to ingest; the posterior MAE exposes this separation. '
          'At 768 tokens, the supplied documents fit without silent truncation; any remaining loss includes semantic extraction and reference-validation errors. '
          'Increasing the context cannot repair those errors by itself. We do not equate these threshold effects with general long-context reasoning quality.']
oracle=json.loads((root/'document-oracle'/'outputs'/'analysis.json').read_text())
r={x['method']:x for x in oracle['summaries']}
lines.append(f'On the same 12 cases with exact typed extraction and B=48, CAEA AUC is {r["caea"]["auc"]:.4f} and Joint AUC is {r["joint"]["auc"]:.4f}. '
             'This paired oracle control separates interpreter degradation from a change in case distribution or acquisition budget. The full numerical study uses B=72 and should not be compared to these text AUC values without this control.')
lines += [r'\subsection{Model Identity and Execution Accounting}',
          r'\begin{table*}[t]\centering\scriptsize',
          r'\caption{Exact model identities. Tokenizer revisions refer to the matching official Qwen instruction model repositories. Both evaluated base repositories advertise Apache-2.0 licenses. Digests identify the downloaded Ollama manifests.}',
          r'\begin{tabular}{lll}\toprule Model & Ollama SHA-256 digest & Hugging Face tokenizer revision\\\midrule']
for item in [x for x in items if x['context']==768]:
    c=item['metadata']['llm']['config']
    lines.append(f'{item["model"]} & \\texttt{{{c["digest"]}}} & \\texttt{{{c["hf_revision"]}}}\\\\')
lines += [r'\bottomrule\end{tabular}\end{table*}']
for item in [x for x in items if x['context']==768]:
    metadata=item['metadata'];runtime=metadata.get('runtime_models',{}).get('models',[])
    model=next((m for m in runtime if m.get('name')==metadata['llm']['config']['model']),{})
    lines.append(f'The {item["model"]} run used Slurm job {metadata["slurm_job_id"]} on \\texttt{{{metadata["node"]}}}, '
                 f'Python {metadata["python"]}, and the frozen source commit 5126533. '
                 f'The final runtime report records {model.get("size_vram",0):,} bytes in GPU memory '
                 f'out of {model.get("size",0):,} total loaded-model bytes.')
# Full relevant versions, no invented version guesses.
freeze=(root/'llm15-final'/'outputs'/'pip-freeze.txt').read_text().splitlines()
versions=[v for v in freeze if v.lower().startswith(('transformers==','huggingface-hub==','torch==','matplotlib=='))]
lines.append('Relevant container packages were '+', '.join(r'\texttt{'+v.replace('_',r'\_')+'}' for v in versions)+'. '
             'The Ollama server version is '+json.loads((root/'llm15-final'/'outputs'/'ollama-version.json').read_text())['version']+'. '
             'Full package listings, container SHA-256, driver/GPU information, raw calls, per-context loaded-model reports and Slurm accounting accompany the artifact. '
             'During measured inference, no response was replayed from an application cache. Reported tokens include all real requests, with failed extractions retained.')
# Actual elapsed times from sacct are inserted from the final accounting during packaging.
(out/'results_llm.tex').write_text('\n\n'.join(lines)+'\n')
(out/'llm_report.json').write_text(json.dumps(items,indent=2))
print(json.dumps({'cl3_models_supported':number,'http_calls':sum(i['audit']['counts'].get('http_calls',0) for i in items),
                  'attempts':sum(i['audit']['counts']['attempts'] for i in items)}))

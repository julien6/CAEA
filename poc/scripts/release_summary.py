"""Remote-only execution accounting for the final research artifact."""
import argparse,csv,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--output',required=True);p.add_argument('--extended',action='store_true');p.add_argument('--all-studies',action='store_true');a=p.parse_args()
root=Path(a.root);out=Path(a.output)
rows=[]
with open(out/'accounting.tsv') as f:
    for r in csv.DictReader(f,delimiter='|'):
        if r['JobID'].isdigit():
            assert r['State']=='COMPLETED' and r['ExitCode']=='0:0',r
            rows.append(r)
gpu_seconds=sum(int(r['ElapsedRaw']) for r in rows if 'gres/gpu=1' in r['AllocTRES'])
core_seconds=sum(int(r['ElapsedRaw'])*int(r['AllocCPUS']) for r in rows)
measured=['llm15-final','llm7-final','strict15-final','strict7-final','identity7-final']
llm_calls=0;tokens_in=0;tokens_out=0;attempts=0
for run in measured:
    folders=[root/run/'outputs']
    if not (folders[0]/'episodes').exists():folders=[p for p in folders[0].iterdir() if p.is_dir() and (p/'episodes').exists()]
    for folder in folders:
        audit=json.loads((folder/'audit.json').read_text())['counts']
        llm_calls+=audit.get('http_calls',0);attempts+=audit['attempts']
        tokens_in+=audit.get('input_tokens',0);tokens_out+=audit.get('output_tokens',0)
replay=json.loads((root/'final-validation'/'outputs'/'replay_validation.json').read_text())
identity=json.loads((root/'identity-check'/'outputs'/'replay_validation.json').read_text())
assert replay['identical_episodes']==11392 and identity['identical_episodes']==48
if a.extended:
    final=json.loads((root/'complete-validation'/'outputs'/'replay_validation.json').read_text())
    assert final['identical_episodes']==19440
if a.all_studies:
    final=json.loads((root/'all-studies-validation'/'outputs'/'replay_validation.json').read_text())
    assert final['identical_episodes']==22640
    unit=(root/'final-unit'/'outputs'/'tests.txt').read_text()
    assert 'Ran 15 tests' in unit and '\nOK\n' in unit
summary={'core_numeric_episodes':22400 if a.all_studies else 19200 if a.extended else 11200,'llm_episodes':168,'oracle_control_episodes':72,
 'final_episodes_replayed':22640 if a.all_studies else 19440 if a.extended else 11440,'measured_llm_calls':llm_calls,'llm_attempts':attempts,
 'measured_input_tokens':tokens_in,'measured_output_tokens':tokens_out,
 'completed_accounted_jobs':len(rows),'allocated_gpu_seconds':gpu_seconds,
 'allocated_cpu_core_seconds':core_seconds,
 'accounting_scope':'Includes model preparation, pilots, measured experiments and validation/report jobs listed in accounting.tsv; excludes this packaging job and local document typesetting.',
 'all_cases_regenerated_with_matching_hashes':True,'all_traces_and_curves_replayed_exactly':True}
(out/'project_summary.json').write_text(json.dumps(summary,indent=2))
(out/'execution_summary.tex').write_text(
 f'The measured documentary experiments contain 168 episodes, {llm_calls:,} real HTTP inference calls, '
 f'{tokens_in:,} input tokens and {tokens_out:,} output tokens. Preventive refusals are included in '
 f'{attempts:,} extraction attempts but are not counted as inference calls. '
 f'Regeneration and recorded-response replay recover all {summary["final_episodes_replayed"]:,} final episodes '
 'with matching case hashes, action traces and utility curves; metric agreement is checked to tolerance $10^{-12}$. '
 f'The recorded accounting for {len(rows)} completed jobs totals {gpu_seconds/3600:.3f} allocated GPU-hours '
 f'and {core_seconds/3600:.3f} allocated CPU-core-hours, including preparation, pilots and report/validation work. '
 'These are allocation durations, not estimates of hardware utilization, energy or monetary price. '
 'Document typesetting is local; experiments, tests, statistical analysis, data generation and plotting execute on OcciData.\n')
print(json.dumps(summary))

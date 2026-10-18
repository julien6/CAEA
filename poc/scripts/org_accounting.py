"""Slurm allocation accounting for all v2 attempts, including excluded/failed runs."""
import argparse,json,subprocess,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args();cfg=json.loads(Path(a.config).read_text());out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
ids=[str(v['job_id']) for v in cfg['jobs']]
if len(ids)!=len(set(ids)):raise ValueError('duplicate allocation IDs')
run_by_id={str(v['job_id']):v['run'] for v in cfg['jobs']}
cmd=['sacct','-j',','.join(ids),'--parsable2','--format=JobIDRaw,JobName,State,ExitCode,ElapsedRaw,AllocCPUS,AllocTRES','--noheader']
raw=subprocess.check_output(cmd,text=True);(out/'accounting.tsv').write_text(raw)
main={}
for line in raw.splitlines():
    parts=line.split('|')
    if parts[0] in ids:main[parts[0]]=parts
cpu=gpu=0;states={}
for jid in ids:
    if jid not in main:raise ValueError('missing accounting '+jid)
    r=main[jid]
    if r[2].split()[0] not in ('COMPLETED','FAILED','CANCELLED','TIMEOUT','OUT_OF_MEMORY','NODE_FAIL','BOOT_FAIL','PREEMPTED','REVOKED','SPECIAL_EXIT'):raise RuntimeError('nonterminal allocation '+jid+': '+r[2])
    seconds=int(r[4] or 0);cores=int(r[5] or 0);cpu+=seconds*cores
    match=re.search(r'(?:^|,)gres/gpu=(\d+)',r[6]);gpu_count=int(match.group(1)) if match else 0;gpu+=seconds*gpu_count
    states[jid]={'run':run_by_id[jid],'state':r[2],'exit':r[3],'allocated_seconds':seconds,'cpu_cores':cores,'gpu_count':gpu_count}
if gpu>24*3600 or cpu>200*3600:raise AssertionError('authorized resource envelope exceeded')
summary={'gpu_hours':gpu/3600,'cpu_core_hours':cpu/3600,'jobs':states,'limits':{'gpu_hours':24,'cpu_core_hours':200},'includes_excluded_attempts':True,'scope':'All recorded org-* job IDs supplied in config, excluding this accounting allocation; add its sacct on completion.'}
(out/'resource_summary.json').write_text(json.dumps(summary,indent=2))
(out/'execution_org.tex').write_text(f'The allocation ledger, including preparation, pilots and excluded attempts, accounts for {gpu/3600:.3f} GPU-hours and {cpu/3600:.3f} CPU-core-hours before its own final accounting allocation. These are allocated durations, not energy, monetary cost or hardware utilization. The authorized limits are 24 GPU-hours and 200 CPU-core-hours. Complete job-level states and exit codes are archived.\n')
print(json.dumps({k:v for k,v in summary.items() if k!='jobs'}))

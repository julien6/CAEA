"""Wait only inside an allocated report job; accounting handles expired controller IDs."""
import argparse,json,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--timeout',type=int,default=3600);a=p.parse_args();jobs=json.loads(Path(a.config).read_text())['jobs'];ids=[str(j['job_id']) for j in jobs];start=time.monotonic()
while True:
    raw=subprocess.check_output(['sacct','-j',','.join(ids),'-nP','--format=JobIDRaw,State,ExitCode'],text=True)
    states={r[0]:(r[1],r[2]) for line in raw.splitlines() if (r:=line.split('|'))[0] in ids}
    for jid,(state,code) in states.items():
        if state.startswith(('FAILED','CANCELLED','TIMEOUT','OUT_OF_MEMORY','NODE_FAIL')):raise RuntimeError((jid,state,code))
    if len(states)==len(ids) and all(v==('COMPLETED','0:0') for v in states.values()):break
    if time.monotonic()-start>a.timeout:raise TimeoutError(states)
    print('Waiting for final parents',states,flush=True);time.sleep(20)
print('All prerequisite allocations completed successfully',flush=True)

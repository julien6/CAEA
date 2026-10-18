"""Descriptive external-source evaluation; questions are not independent cases."""
import argparse,json
from pathlib import Path
from caea.org_v2.staging import materialize
from caea.org_v2.analysis import analyze
p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
for name,label in [('org-final-external-llm','qwen'),('org-final-external-control','deterministic')]:
    folder=materialize(a.root,name);analyze([folder],out/label,external=True)
    if label=='qwen':
        total=calls=errors=inp=generated=rejected=mentions=0
        for line in (folder/'llm_calls.jsonl').open():
            r=json.loads(line);total+=1;calls+=int('request' in r);errors+=bool(r.get('error'));inp+=r.get('response',{}).get('prompt_eval_count',0);generated+=r.get('response',{}).get('eval_count',0);rejected+=r.get('rejected_quotes',0);mentions+=len((r.get('parsed') or {}).get('mentions',[]))
        (out/'audit.json').write_text(json.dumps({'attempts':total,'dispatched':calls,'errors':errors,'input_tokens':inp,'output_tokens':generated,'rejected_quotes':rejected,'accepted_literal_pdf_mentions':mentions,'inference_reuse':False,'independent_scenarios':1},indent=2))

"""Audit text outputs against evaluator records, never inside policy execution."""
import argparse,json,collections
from pathlib import Path


def audit(out):
    out=Path(out); path=out/'llm_calls.jsonl'
    if not path.exists():return
    records={}
    for c in (out/'cases').glob('*.json'):
        case=json.loads(c.read_text())
        setting,seed=c.stem.rsplit('-',1)
        for nid,node in case['nodes'].items():
            if 'record' in node:records[(setting,seed,nid)]=node['record']
    counts=collections.Counter();tokens=[]; durations=[];relevant=collections.Counter()
    for line in path.read_text().splitlines():
        r=json.loads(line);episode=r['episode'].split('-');key=(episode[0],episode[1],r['eid'])
        truth=records.get(key)
        if truth is None:raise ValueError('missing evaluator artifact')
        diagnostic=truth['kind']!='noise'
        counts['attempts']+=1
        counts['diagnostic_attempts' if diagnostic else 'noise_attempts']+=1
        if r.get('error'):counts[r['error'].split(':')[0]]+=1
        if r.get('response'):
            counts['http_calls']+=1
            counts['input_tokens']+=r['response'].get('prompt_eval_count',0)
            counts['output_tokens']+=r['response'].get('eval_count',0)
            tokens.append(r.get('requested_input_tokens',0))
            durations.append(r['wall_seconds'])
        parsed=r.get('parsed')
        if diagnostic:
            relevant['attempts']+=1
            relevant['exact']+=parsed==truth
            relevant['correct_kind']+=parsed is not None and parsed.get('kind')==truth['kind']
            relevant['correct_bit']+=parsed is not None and parsed.get('bit')==truth.get('bit') and parsed.get('h')==truth.get('h')
            if truth.get('target_path'):
                relevant['references']+=1
                relevant['correct_reference']+=parsed is not None and parsed.get('target_path')==truth['target_path']
        else:
            counts['noise_exact']+=parsed==truth
            counts['false_diagnostic']+=parsed is not None and parsed.get('kind')!='noise'
    result={'counts':dict(counts),'diagnostic':dict(relevant),
            'max_input_tokens':max(tokens,default=0),'mean_http_seconds':sum(durations)/max(1,len(durations))}
    (out/'audit.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    root=Path(a.output)
    if (root/'episodes').exists():audit(root)
    else:
        for child in sorted(root.iterdir()):
            if child.is_dir() and (child/'episodes').exists():audit(child)

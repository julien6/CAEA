"""Check completion of the frozen study; never assert favorable performance."""
import argparse,json
from pathlib import Path
from caea.org_v2.staging import materialize

p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--output',required=True);a=p.parse_args()
root=Path(a.root);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
replays={}
for i in range(5):
    name=f'org-final-numeric-replay-{i}'
    folder=materialize(root,name);record=json.loads((folder/'replay.json').read_text())
    assert record['episodes']==7040
    assert record['runs']=={f'org-final-main-{i}':3840,f'org-final-robust-{i}':3200}
    assert 'Ran 33 tests' in (folder/'tests.txt').read_text() and '\nOK\n' in (folder/'tests.txt').read_text()
    replays[name]=record
name='org-final-documentary-validation-v4'
record=json.loads((materialize(root,name)/'replay.json').read_text())
assert record['runs']=={'org-final-synthetic-recovered-v2':192,'org-final-synthetic-oracle':192,'org-final-external-llm':128,'org-final-external-control':128}
assert record['episodes']==640;replays[name]=record
for record in replays.values():
    assert record['traces_exact'] and record['messages_exact'] and record['case_hashes_exact']
    assert record['metrics_tolerance']==1e-12 and record['llm_inference'] is False
report=materialize(root,'org-final-manuscript-v6')
study=json.loads((report/'study_summary.json').read_text())
expected={'main_episodes':19200,'robust_episodes':16000,'synthetic_llm_episodes':192,'synthetic_exact_episodes':192,'external_llm_episodes':128,'external_deterministic_episodes':128,'main_negative_controls_exact':True}
assert study==expected,(study,expected)
for name in ('results_org.tex','organization_effects.pdf','documentary_audit.json','temporal_contrasts.json'):
    assert (report/name).stat().st_size>0
corpus=materialize(root,'org-corpus-bundle')/'corpus'/'tasks'/'annotation_audit.json'
audit=json.loads(corpus.read_text())
assert audit['all_spans_verified'] and audit['human_validation'] is False
assert len(audit['tasks'])==20
assert sum(t['split']=='development' for t in audit['tasks'])==4
assert sum(t['split']=='test' for t in audit['tasks'])==16
result={'complete':True,'new_replayed_episodes':sum(r['episodes'] for r in replays.values()),'study':study,'replays':replays,'unit_tests':33,'external_tasks':20,'external_test_tasks':16,'independent_external_scenarios':1,'scope':'Computational completion and artifact integrity; no claim of favorable results, human annotation audit, publication or acceptance.'}
assert result['new_replayed_episodes']==35840
(out/'closure.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('replays','study')},indent=2))

import argparse,json
from pathlib import Path
from caea.org_v2.analysis import analyze
from caea.org_v2.staging import materialize
p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--output',required=True);p.add_argument('--prefix',default='org-final');a=p.parse_args()
root=Path(a.root);out=Path(a.output)
for study in ('main','robust'):
    folders=[materialize(root,f'{a.prefix}-{study}-{i}') for i in range(5)]
    result=analyze(folders,out/study)
    assert result['episodes']==(19200 if study=='main' else 16000)

import argparse,json,os,urllib.request
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--config');p.add_argument('--output');a=p.parse_args()
c=json.loads(Path(a.config).read_text())
with urllib.request.urlopen('http://'+os.environ['OLLAMA_HOST']+'/api/tags') as r:tags=json.load(r)
models={m['name']:m for m in tags['models']}
items=[i['config'] for i in c['suite']] if 'suite' in c else [c]
for item in items:
    if 'llm' in item:
        llm=item['llm'];actual=models[llm['model']]
        if llm.get('digest') and llm['digest']!=actual['digest']:raise ValueError('model digest mismatch')
Path(a.output,'models-before.json').write_text(json.dumps(tags,indent=2))

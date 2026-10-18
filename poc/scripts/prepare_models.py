import argparse,json,os,urllib.request
from pathlib import Path
from huggingface_hub import snapshot_download, HfApi
p=argparse.ArgumentParser();p.add_argument('--config');p.add_argument('--output');a=p.parse_args()
c=json.loads(Path(a.config).read_text()); out=Path(a.output)
meta=[]
for item in c['models']:
    req=urllib.request.Request('http://'+os.environ['OLLAMA_HOST']+'/api/pull',
        data=json.dumps({'model':item['ollama'],'stream':False}).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=1800) as r: response=json.load(r)
    sha=HfApi().model_info(item['hf']).sha
    path=snapshot_download(item['hf'],revision=sha,allow_patterns=['tokenizer*','vocab.json','merges.txt','config.json','special_tokens_map.json'])
    meta.append({'ollama':item['ollama'],'hf':item['hf'],'revision':sha,'tokenizer_path':path,'pull':response})
    print(json.dumps(meta[-1]),flush=True)
(out/'prepared.json').write_text(json.dumps(meta,indent=2))

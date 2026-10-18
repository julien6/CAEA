"""Fetch only public M57 scenario documentation, never protected answer keys."""
import hashlib,json,urllib.request,subprocess
from pathlib import Path
root=Path('/projects/caea/datasets/m57-public-docs');root.mkdir(parents=True,exist_ok=True)
base='https://downloads.digitalcorpora.org/corpora/scenarios/2009-m57-patents/docs/'
names=[f'detectivereport{i}.pdf' for i in range(1,5)]+['m57-affidavit-warrant-final.pdf','M57-Patents-Illegal.pdf','M57-Patents-Exfiltration.pdf','M57-Patents-Eavesdropping.pdf']
from pypdf import PdfReader
manifest=[]
for name in names:
 try:
  raw=urllib.request.urlopen(base+name,timeout=90).read()
  if len(raw)>20_000_000:raise ValueError('document exceeds bound')
  p=root/name;p.write_bytes(raw)
  pages=[page.extract_text() for page in PdfReader(p).pages]
  (root/(name+'.json')).write_text(json.dumps(pages))
  manifest.append({'name':name,'url':base+name,'sha256':hashlib.sha256(raw).hexdigest(),'pages':len(pages),'characters':sum(map(len,pages))})
  print(name, '\n'.join(pages),flush=True)
 except Exception as e:manifest.append({'name':name,'error':str(e)})
(root/'manifest.json').write_text(json.dumps(manifest,indent=2))
Path('outputs/corpus_manifest.json').write_text(json.dumps(manifest,indent=2))

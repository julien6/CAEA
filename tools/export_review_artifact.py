"""Package existing observations for review; no scientific execution or inference.

Keep immutable originals in experiments/. Publish chunked, metadata-anonymized
copies with new checksums; never reuse an original checksum for modified bytes.
"""
import argparse, gzip, hashlib, io, json, re, tarfile
from pathlib import Path

CHUNK = 40 * 1024 * 1024
REPLACEMENTS = {}

def redact(data):
    try: text = data.decode('utf-8')
    except UnicodeDecodeError: return data, False
    for old, new in REPLACEMENTS.items(): text = text.replace(old, new)
    return text.encode(), text.encode() != data

class Chunks:
    def __init__(self, folder):
        self.folder=folder; self.file=None; self.size=0; self.index=0; self.paths=[]
    def write(self, data):
        length=len(data)
        while data:
            if self.file is None:
                p=self.folder/f'data.tar.gz.part{self.index:03d}'
                self.file=p.open('wb'); self.paths.append(p); self.index+=1; self.size=0
            n=min(len(data),CHUNK-self.size); self.file.write(data[:n]); data=data[n:]; self.size+=n
            if self.size==CHUNK: self.file.close(); self.file=None
        return length
    def flush(self):
        if self.file: self.file.flush()
    def close(self):
        if self.file: self.file.close(); self.file=None


def main():
    global REPLACEMENTS
    ap=argparse.ArgumentParser();ap.add_argument('--redactions',default='review_redactions.local.json');ap.add_argument('--source',default='experiments/occidata');ap.add_argument('--output',default='results');a=ap.parse_args()
    REPLACEMENTS=json.loads(Path(a.redactions).read_text())
    source=Path(a.source);output=Path(a.output);output.mkdir(exist_ok=True)
    index={'schema':1,'purpose':'Reviewer transport of existing finalized and historical records; no new computation.',
      'anonymization':'Account/host/project identifiers replaced in text metadata; algorithmic parameters and source/response content retained. Export checksums replace original transport manifests.',
      'excluded':'Duplicate source/transport archives, source checkout copies, Slurm stdout/stderr, source commit/worktree records and original transport manifests. Scientific observations and analyses retained.', 'runs':{}}
    for run in sorted(p for p in source.iterdir() if p.is_dir()):
        folder=output/run.name;folder.mkdir(exist_ok=True)
        for p in folder.glob('data.tar.gz.part*'): p.unlink()
        inputs=[]
        if (run/'config.json').exists(): inputs.append((run/'config.json','config.json'))
        outputs=run/'outputs'
        if outputs.exists():
            for p in sorted(outputs.rglob('*')):
                if not p.is_file() or '__pycache__' in p.parts:continue
                if p.name in ('INNER_SHA256SUMS','SHA256SUMS') or p.name.startswith('slurm-'):continue
                if p.name.endswith(('.tar.gz','.out','.err')):continue
                inputs.append((p,'outputs/'+p.relative_to(outputs).as_posix()))
        members=[];writer=Chunks(folder)
        with gzip.GzipFile(fileobj=writer,mode='wb',mtime=0,filename='') as gz:
            with tarfile.open(fileobj=gz,mode='w|') as tar:
                for p,name in inputs:
                    original=p.read_bytes();data,changed=redact(original)
                    # Episodes are already compressed: inspect their text too without
                    # changing any unaffected compressed scientific record.
                    if p.suffix=='.gz':
                        unpacked=gzip.decompress(original); cleaned,changed=redact(unpacked)
                        if changed:data=gzip.compress(cleaned,mtime=0)
                    info=tarfile.TarInfo(name);info.size=len(data);info.mtime=0;info.mode=0o644
                    tar.addfile(info,io.BytesIO(data))
                    members.append({'path':name,'size':len(data),'sha256':hashlib.sha256(data).hexdigest(),
                                    'original_sha256':hashlib.sha256(original).hexdigest(),'metadata_redacted':changed})
        writer.close()
        manifest={'run':run.name,'files':members,'parts':[{'name':p.name,'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in writer.paths]}
        (folder/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        index['runs'][run.name]={'files':len(members),'bytes':sum(p.stat().st_size for p in writer.paths),'parts':len(writer.paths),'redacted_files':sum(m['metadata_redacted'] for m in members)}
        print(run.name,len(members),flush=True)
    (output/'index.json').write_text(json.dumps(index,indent=2)+'\n')

if __name__=='__main__':main()

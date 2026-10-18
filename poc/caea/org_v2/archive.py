"""Stream immutable run archives without extracting thousands of temporary files."""
import gzip,io,json,tarfile,hashlib
from pathlib import Path
from .storage import episode_files,read_episode


def iter_members(root,name,predicate,checksums=None):
    archive=Path(root)/name/'outputs'/'artifacts.tar.gz'
    with tarfile.open(archive,'r|gz') as stream:
        for member in stream:
            key=member.name.removeprefix('./')
            if member.isfile() and predicate(key):
                raw=stream.extractfile(member).read()
                if checksums is not None:
                    assert key in checksums and hashlib.sha256(raw).hexdigest()==checksums[key],('archive checksum',name,key)
                if key.endswith('.gz'):raw=gzip.decompress(raw)
                yield key,raw


def checksums(root,name):
    for _,raw in iter_members(root,name,lambda k:k=='INNER_SHA256SUMS'):
        return {path.removeprefix('./'):sha for line in raw.decode().splitlines() for sha,path in [line.split('  ',1)]}
    raise ValueError('archive has no inner manifest: '+name)


def rows(root,name):
    folder=Path(root)/name/'outputs'
    if (folder/'artifacts.tar.gz').exists():
        for key,raw in iter_members(root,name,lambda k:k.startswith('episodes/') and (k.endswith('.json') or k.endswith('.json.gz')),checksums(root,name)):yield json.loads(raw)
    else:
        for path in episode_files(folder):yield read_episode(path)


def ancillary(root,name):
    """Cases and original raw-call records; independent of episode-file order."""
    cases={};calls=[];folder=Path(root)/name/'outputs'
    if (folder/'artifacts.tar.gz').exists():
        for key,raw in iter_members(root,name,lambda k:k.startswith('cases/') and k.endswith('.json') or k=='llm_calls.jsonl',checksums(root,name)):
            if key=='llm_calls.jsonl':calls=[json.loads(line) for line in raw.splitlines()]
            else:cases[Path(key).stem]=json.loads(raw)
    else:
        cases={p.stem:json.loads(p.read_text()) for p in (folder/'cases').glob('*.json')}
        if (folder/'llm_calls.jsonl').exists():calls=[json.loads(line) for line in (folder/'llm_calls.jsonl').read_text().splitlines()]
    return cases,calls

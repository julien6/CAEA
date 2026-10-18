"""Deterministic compressed episode artifacts; readers also accept pilot JSON."""
import gzip,json
from pathlib import Path


def read_episode(path):
    raw=Path(path).read_bytes()
    if str(path).endswith('.gz'):raw=gzip.decompress(raw)
    return json.loads(raw)


def episode_files(folder):
    return sorted((Path(folder)/'episodes').glob('*.json*'))


def write_episode(path,result):
    path=Path(path);tmp=path.with_suffix('.tmp')
    tmp.write_bytes(gzip.compress(json.dumps(result,sort_keys=True).encode(),compresslevel=3,mtime=0));tmp.replace(path)

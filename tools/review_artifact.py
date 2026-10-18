"""Verify reviewer transport and optionally unpack selected runs (no simulation)."""
import argparse,gzip,hashlib,json,tarfile,tempfile
from pathlib import Path, PurePosixPath
import re

p=argparse.ArgumentParser();p.add_argument('--root',default='results');p.add_argument('--runs',nargs='*');p.add_argument('--unpack',action='store_true');p.add_argument('--destination',default='results/unpacked');a=p.parse_args()
root=Path(a.root);index=json.loads((root/'index.json').read_text());names=a.runs or sorted(index['runs'])
supplemental=root/'supplemental_manifest.json'
if supplemental.exists():
    for entry in json.loads(supplemental.read_text()):
        relative=PurePosixPath(entry['path'])
        assert relative.parts[0]=='results' and '..' not in relative.parts
        target=root.joinpath(*relative.parts[1:])
        assert hashlib.sha256(target.read_bytes()).hexdigest()==entry['sha256'],str(target)
    print('Verified supplemental summaries and final resource ledger',flush=True)

for name in names:
    if not re.fullmatch(r'[A-Za-z0-9_-]+',name):raise ValueError('Invalid run name')
    if name not in index['runs']:raise ValueError('Unknown run: '+name)
    folder=root/name;manifest=json.loads((folder/'manifest.json').read_text())
    with tempfile.TemporaryFile() as packed:
        for part in manifest['parts']:
            data=(folder/part['name']).read_bytes()
            assert len(data)==part['size'] and hashlib.sha256(data).hexdigest()==part['sha256'],(name,part['name'])
            packed.write(data)
        packed.seek(0)
        expected={m['path']:m for m in manifest['files']};seen=set()
        with tarfile.open(fileobj=packed,mode='r|gz') as tar:
            for member in tar:
                member_path=PurePosixPath(member.name)
                assert not member_path.is_absolute() and '..' not in member_path.parts
                assert member.isfile() and member.name in expected,(name,member.name)
                data=tar.extractfile(member).read();m=expected[member.name]
                assert len(data)==m['size'] and hashlib.sha256(data).hexdigest()==m['sha256'],(name,member.name)
                assert member.name not in seen;seen.add(member.name)
                if a.unpack:
                    target=Path(a.destination)/name/member.name
                    assert target.resolve().is_relative_to((Path(a.destination)/name).resolve())
                    target.parent.mkdir(parents=True,exist_ok=True)
                    assert not target.exists(),'Refusing to overwrite '+str(target)
                    target.write_bytes(data)
        assert seen==set(expected),name
    print('Verified',name,len(seen),'files',flush=True)

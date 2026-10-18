"""Read archived Slurm artifacts into report-job scratch, never onto the frontend."""
from pathlib import Path
import tarfile,subprocess


def materialize(root,name):
    original=Path(root)/name/'outputs';archive=original/'artifacts.tar.gz'
    if not archive.exists():return original
    target=Path.cwd()/'staged'/name
    if not target.exists():
        target.mkdir(parents=True)
        with tarfile.open(archive,'r:gz') as stream:stream.extractall(target,filter='data')
        subprocess.run(['sha256sum','--quiet','-c','INNER_SHA256SUMS'],cwd=target,check=True)
    return target

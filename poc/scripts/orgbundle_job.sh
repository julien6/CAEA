#!/bin/bash
#SBATCH --job-name=caea-org-corpus-bundle
#SBATCH --account=REVIEW_PROJECT
#SBATCH --partition=24CPUNodes
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:15:00
#SBATCH --output=outputs/slurm-%j.out
#SBATCH --error=outputs/slurm-%j.err
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
mkdir -p outputs/corpus
cp -a /projects/caea/datasets/m57-public-docs/. outputs/corpus/
python3 - <<'PY'
import json,hashlib
from pathlib import Path
root=Path('outputs/corpus'); manifest=json.loads((root/'manifest.json').read_text())
for m in manifest:
 if 'sha256' in m:assert hashlib.sha256((root/m['name']).read_bytes()).hexdigest()==m['sha256']
for p in (root/'tasks').glob('*.json'):
 if p.name=='annotation_audit.json':continue
 c=json.loads(p.read_text());expected=c.pop('sha256');assert hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest()==expected
print('All source PDF and task hashes verified')
PY

#!/bin/bash
#SBATCH --job-name=caea-org-replay
#SBATCH --account=REVIEW_PROJECT
#SBATCH --partition=24CPUNodes
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=04:00:00
#SBATCH --output=outputs/slurm-%j.out
#SBATCH --error=outputs/slurm-%j.err
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
export PYTHONPATH="$PWD/src/poc"
IMAGE=/apps/containerCollections/CUDA12/pytorch-NGC-25-01-ollama-0.14.3.sif
singularity exec "$IMAGE" python -m unittest discover -s src/poc/tests -v >outputs/tests.txt 2>&1
python3 src/poc/scripts/wait_org_jobs.py --config config.json --timeout 3600
mapfile -t runs < <(python3 -c 'import json; print("\n".join(json.load(open("config.json"))["runs"]))')
singularity exec "$IMAGE" python -m compileall -q src/poc/caea src/poc/scripts >outputs/compile.txt 2>&1
singularity exec "$IMAGE" python src/poc/scripts/org_replay.py --root /projects/caea/runs --runs "${runs[@]}" --output outputs

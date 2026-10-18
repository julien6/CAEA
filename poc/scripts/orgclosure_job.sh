#!/bin/bash
#SBATCH --job-name=caea-org-closeout
#SBATCH --account=REVIEW_PROJECT
#SBATCH --partition=24CPUNodes
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=01:00:00
#SBATCH --output=outputs/slurm-%j.out
#SBATCH --error=outputs/slurm-%j.err
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
export PYTHONPATH="$PWD/src/poc"
IMAGE=/apps/containerCollections/CUDA12/pytorch-NGC-25-01-ollama-0.14.3.sif
python3 src/poc/scripts/wait_org_jobs.py --config config.json --timeout 3000
singularity exec "$IMAGE" python src/poc/scripts/org_closeout.py --root /projects/caea/runs --output outputs

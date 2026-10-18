#!/bin/bash
#SBATCH --job-name=caea-org-pilot-report
#SBATCH --account=REVIEW_PROJECT
#SBATCH --partition=24CPUNodes
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=outputs/slurm-%j.out
#SBATCH --error=outputs/slurm-%j.err
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
export PYTHONPATH="$PWD/src/poc" OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
IMAGE=/apps/containerCollections/CUDA12/pytorch-NGC-25-01-ollama-0.14.3.sif
ROOT=/projects/caea/runs
singularity exec "$IMAGE" python -m caea.org_v2.analysis --folders "$ROOT/org-pilot-v1/outputs" --output outputs/numeric
singularity exec "$IMAGE" python -m caea.org_v2.analysis --folders "$ROOT/org-external-pilot/outputs" --output outputs/external --external
singularity exec "$IMAGE" python src/poc/scripts/org_replay.py --root "$ROOT" --runs org-pilot-v1 org-external-pilot --output outputs/replay

#!/bin/bash
#SBATCH --job-name=caea-org-paper-report
#SBATCH --account=REVIEW_PROJECT
#SBATCH --partition=24CPUNodes
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=outputs/slurm-%j.out
#SBATCH --error=outputs/slurm-%j.err
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
export PYTHONPATH="$PWD/src/poc" OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
IMAGE=/apps/containerCollections/CUDA12/pytorch-NGC-25-01-ollama-0.14.3.sif
singularity exec "$IMAGE" python src/poc/scripts/org_manuscript_results.py --root /projects/caea/runs --output outputs

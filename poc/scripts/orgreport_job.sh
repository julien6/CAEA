#!/bin/bash
#SBATCH --job-name=caea-org-report
#SBATCH --account=REVIEW_PROJECT
#SBATCH --partition=24CPUNodes
#SBATCH --cpus-per-task=2
#SBATCH --mem=24G
#SBATCH --time=02:00:00
#SBATCH --output=outputs/slurm-%j.out
#SBATCH --error=outputs/slurm-%j.err
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
export PYTHONPATH="$PWD/src/poc" OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
IMAGE=/apps/containerCollections/CUDA12/pytorch-NGC-25-01-ollama-0.14.3.sif
ROOT=/projects/caea/runs
python3 src/poc/scripts/wait_org_jobs.py --config config.json
singularity exec "$IMAGE" python src/poc/scripts/org_study_report.py --root "$ROOT" --output outputs

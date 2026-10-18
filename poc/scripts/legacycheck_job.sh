#!/bin/bash
#SBATCH --job-name=caea-v2-legacy
#SBATCH --account=REVIEW_PROJECT
#SBATCH --partition=24CPUNodes
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=outputs/slurm-%j.out
#SBATCH --error=outputs/slurm-%j.err
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
export PYTHONPATH="$PWD/src/poc"
IMAGE=/apps/containerCollections/CUDA12/pytorch-NGC-25-01-ollama-0.14.3.sif
singularity exec "$IMAGE" python -m unittest discover -s src/poc/tests -v >outputs/tests.txt 2>&1
singularity exec "$IMAGE" python src/poc/scripts/report_path.py --root /projects/caea/runs --output outputs
singularity exec "$IMAGE" python src/poc/scripts/validate_replay.py --root /projects/caea/runs --output outputs --runs numeric-v1 document-oracle strict-oracle llm15-final llm7-final strict15-final strict7-final identity7-final identity-oracle prior-robustness path-ablation --expected 22640

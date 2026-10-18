#!/bin/bash
#SBATCH --job-name=caea-numeric
#SBATCH --account=REVIEW_PROJECT
#SBATCH --partition=24CPUNodes
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --no-requeue
#SBATCH --output=outputs/slurm-%j.out
#SBATCH --error=outputs/slurm-%j.err
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
IMAGE=/apps/containerCollections/CUDA12/pytorch-NGC-25-01-ollama-0.14.3.sif
export PYTHONPATH="$PWD/src/poc"
singularity exec "$IMAGE" python -m unittest discover -s src/poc/tests -v >outputs/tests.txt 2>&1
singularity exec "$IMAGE" python -m caea.run --config config.json --output outputs
singularity exec "$IMAGE" python -m caea.analyze --output outputs

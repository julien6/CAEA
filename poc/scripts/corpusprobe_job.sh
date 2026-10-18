#!/bin/bash
#SBATCH --job-name=caea-corpus-probe
#SBATCH --account=REVIEW_PROJECT
#SBATCH --partition=24CPUNodes
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:15:00
#SBATCH --output=outputs/slurm-%j.out
#SBATCH --error=outputs/slurm-%j.err
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
export PYTHONPATH="$PWD/tmpdeps:$PWD/src/poc"
IMAGE=/apps/containerCollections/CUDA12/pytorch-NGC-25-01-ollama-0.14.3.sif
singularity exec "$IMAGE" python -m pip install --target tmpdeps pypdf==6.1.1 >outputs/dependencies.txt 2>&1
singularity exec "$IMAGE" python src/poc/scripts/corpus_probe.py >outputs/corpus_text.txt

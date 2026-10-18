#!/bin/bash
#SBATCH --job-name=caea-org-tests
#SBATCH --account=REVIEW_PROJECT
#SBATCH --partition=24CPUNodes
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:15:00
#SBATCH --output=outputs/slurm-%j.out
#SBATCH --error=outputs/slurm-%j.err
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
export PYTHONPATH="$PWD/src/poc"
singularity exec /apps/containerCollections/CUDA12/pytorch-NGC-25-01-ollama-0.14.3.sif python -m unittest discover -s src/poc/tests -v >outputs/tests.txt 2>&1

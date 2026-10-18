#!/bin/bash
#SBATCH --job-name=caea-complete-ledger
#SBATCH --account=REVIEW_PROJECT
#SBATCH --partition=24CPUNodes
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=outputs/slurm-%j.out
#SBATCH --error=outputs/slurm-%j.err
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
export PYTHONPATH="$PWD/src/poc"
sacct -j 3048275,3048277,3048278,3048279,3048280,3048282,3048285,3048287,3048288,3048289,3048291,3048296,3048297,3048298,3048299,3048302,3048305,3048310,3048312,3048314,3048317,3048320,3048323,3048329 --parsable2 --format=JobID,State,ExitCode,ElapsedRaw,AllocCPUS,AllocTRES,MaxRSS,NodeList >outputs/accounting.tsv
singularity exec /apps/containerCollections/CUDA12/pytorch-NGC-25-01-ollama-0.14.3.sif python src/poc/scripts/release_summary.py --root /projects/caea/runs --output outputs --extended

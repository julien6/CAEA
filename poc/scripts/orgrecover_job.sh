#!/bin/bash
#SBATCH --job-name=caea-org-archive-recovery
#SBATCH --account=REVIEW_PROJECT
#SBATCH --partition=24CPUNodes
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=outputs/slurm-%j.out
#SBATCH --error=outputs/slurm-%j.err
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
export PYTHONPATH="$PWD/src/poc"
IMAGE=/apps/containerCollections/CUDA12/pytorch-NGC-25-01-ollama-0.14.3.sif
parent_ids=$(python3 -c 'import json;print(",".join(str(p["job_id"]) for p in json.load(open("config.json"))["recovery_parents"]))')
sacct -j "$parent_ids" -nP --format=JobIDRaw,State,ExitCode >outputs/parent_accounting.tsv
singularity exec "$IMAGE" python src/poc/scripts/org_recover_completed.py --config config.json --root /projects/caea/runs --output outputs
singularity exec "$IMAGE" python src/poc/scripts/org_replay.py --root "$PWD/recovery-root" --runs org-final-synthetic-recovered --output outputs/recovery_validation

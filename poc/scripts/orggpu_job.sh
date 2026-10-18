#!/bin/bash
#SBATCH --job-name=caea-org-llm
#SBATCH --account=REVIEW_PROJECT
#SBATCH --partition=L40SNodes
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --gres=gpu:1
#SBATCH --gres-flags=enforce-binding
#SBATCH --time=06:00:00
#SBATCH --no-requeue
#SBATCH --output=outputs/slurm-%j.out
#SBATCH --error=outputs/slurm-%j.err
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
mkdir -p tmp cache runtime-home outputs
export TMPDIR="$PWD/tmp" XDG_CACHE_HOME=/projects/caea/cache
export HF_HOME=/projects/caea/cache/huggingface
export OLLAMA_MODELS=/projects/caea/models
export OLLAMA_HOST=127.0.0.1:$((19000+SLURM_JOB_ID%20000))
export PYTHONPATH="$PWD/src/poc" OLLAMA_CONTEXT_LENGTH=4096 OLLAMA_NUM_PARALLEL=1
IMAGE=/apps/containerCollections/CUDA12/pytorch-NGC-25-01-ollama-0.14.3.sif
run_image() {
 singularity exec --nv --env "OLLAMA_MODELS=$OLLAMA_MODELS,OLLAMA_HOST=$OLLAMA_HOST,OLLAMA_CONTEXT_LENGTH=$OLLAMA_CONTEXT_LENGTH,OLLAMA_NUM_PARALLEL=1,OLLAMA_NOPRUNE=true,HF_HOME=$HF_HOME" --home "$PWD/runtime-home:/root" "$IMAGE" "$@"
}
run_image ollama serve >outputs/ollama-server.log 2>&1 &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null || true; wait "$server_pid" 2>/dev/null || true' EXIT
ready=0
for attempt in $(seq 1 90); do
 kill -0 "$server_pid"
 if curl -fsS "$OLLAMA_HOST/api/version" >outputs/ollama-version.json; then ready=1; break; fi
 sleep 1
done
test "$ready" = 1
nvidia-smi >outputs/nvidia-smi.txt
run_image python -m pip freeze >outputs/pip-freeze.txt
sha256sum "$IMAGE" >outputs/image-sha256.txt
run_image python src/poc/scripts/verify_models.py --config config.json --output outputs
if test -f src/poc/caea/org_v2/external_run.py && python3 -c 'import json,sys;sys.exit(0 if "dataset" in json.load(open("config.json")) else 1)'; then
 run_image python -m caea.org_v2.external_run --config config.json --output outputs
else
 run_image python -m caea.org_v2.run --config config.json --output outputs
fi
run_image ollama ps >outputs/loaded-model.txt
curl -fsS "$OLLAMA_HOST/api/tags" >outputs/models.json

#!/bin/bash
# Source preparation only on local host; all experiments run inside Slurm.
set -euo pipefail
cd "$(dirname "$0")/../.."
kind=${1:?cpu or gpu}; config=${2:?config path}; run_id=${3:?unique run ID}
[[ "$run_id" =~ ^[a-zA-Z0-9_-]+$ ]] || exit 2
remote=${CAEA_REMOTE:?Set CAEA_REMOTE to your SSH target (user@cluster)}
local_run="$PWD/experiments/occidata/$run_id"
remote_run="/projects/caea/runs/$run_id"
test ! -e "$local_run"
mkdir -p "$local_run/src" "$local_run/outputs"
cp -a poc "$local_run/src/"
cp "$config" "$local_run/config.json"
if [ "$kind" = prepare ]; then
  cp poc/scripts/gpu_job.sh "$local_run/job.sh"
  cp "$config" "$local_run/prepare.json"
else
  cp "poc/scripts/${kind}_job.sh" "$local_run/job.sh"
fi
git rev-parse HEAD > "$local_run/source_commit.txt"
git status --porcelain > "$local_run/source_worktree_status.txt"
(cd "$local_run" && find src -type f -not -path '*/__pycache__/*' -print0 | sort -z | xargs -0 sha256sum) > "$local_run/source-manifest.txt"
ssh -o BatchMode=yes "$remote" "test ! -e '$remote_run' && mkdir -p '$remote_run'"
rsync -a --exclude __pycache__ "$local_run/" "$remote:$remote_run/"
dependency=${4:-}
if [ -n "$dependency" ]; then
  [[ "$dependency" =~ ^[0-9:]+$ ]] || exit 2
  ssh -o BatchMode=yes "$remote" "cd '$remote_run' && sbatch --parsable --dependency=afterok:$dependency job.sh" > "$local_run/job_id.txt"
else
  ssh -o BatchMode=yes "$remote" "cd '$remote_run' && sbatch --parsable job.sh" > "$local_run/job_id.txt"
fi
cat "$local_run/job_id.txt"

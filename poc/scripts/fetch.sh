#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
run_id=${1:?run ID}
[[ "$run_id" =~ ^[a-zA-Z0-9_-]+$ ]] || exit 2
remote=${CAEA_REMOTE:?Set CAEA_REMOTE to your SSH target (user@cluster)}
local_run="$PWD/experiments/occidata/$run_id"
remote_run="/projects/caea/runs/$run_id"
job_id=$(cat "$local_run/job_id.txt"); job_id=${job_id%%;*}
ssh -o BatchMode=yes "$remote" "sacct -j '$job_id' --parsable2 --format=JobID,JobName,State,ExitCode,Elapsed,AllocTRES,MaxRSS" > "$local_run/sacct.txt"
cat "$local_run/sacct.txt"
if ! awk -F'|' -v id="$job_id" '$1==id && $3=="COMPLETED" && $4=="0:0"{ok=1} END{exit !ok}' "$local_run/sacct.txt"; then
  rsync -a "$remote:$remote_run/outputs/" "$local_run/outputs/"
  exit 3
fi
ssh -o BatchMode=yes "$remote" "cd '$remote_run/outputs' && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 -r sha256sum > SHA256SUMS"
rsync -a "$remote:$remote_run/outputs/" "$local_run/outputs/"
(cd "$local_run/outputs" && sha256sum --quiet -c SHA256SUMS)
printf 'All output hashes verified: %s\n' "$run_id"

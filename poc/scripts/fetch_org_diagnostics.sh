#!/bin/bash
# Administrative retrieval of failed-run diagnostics, never acceptance of partial data.
set -euo pipefail
cd "$(dirname "$0")/../.."
run_id=${1:?run ID}
[[ "$run_id" =~ ^[a-zA-Z0-9_-]+$ ]] || exit 2
remote=${CAEA_REMOTE:?Set CAEA_REMOTE to your SSH target (user@cluster)}
local_run="$PWD/experiments/occidata/$run_id"
remote_run="/projects/caea/runs/$run_id"
job_id=$(cat "$local_run/job_id.txt"); job_id=${job_id%%;*}
ssh -o BatchMode=yes "$remote" "sacct -j '$job_id' -nP --format=JobIDRaw,State,ExitCode,Elapsed,AllocTRES" > "$local_run/diagnostic_sacct.txt"
ssh -o BatchMode=yes "$remote" "cd '$remote_run/outputs' && find . -maxdepth 1 -type f \\( -name 'slurm-*.out' -o -name 'slurm-*.err' -o -name 'worker_exit.txt' -o -name 'retained_scratch.txt' \\) -print0 | sort -z | xargs -0 -r sha256sum > DIAGNOSTIC_SHA256SUMS"
mkdir -p "$local_run/outputs"
rsync -a --include='slurm-*.out' --include='slurm-*.err' --include='worker_exit.txt' --include='retained_scratch.txt' --include='DIAGNOSTIC_SHA256SUMS' --exclude='*' "$remote:$remote_run/outputs/" "$local_run/outputs/"
(cd "$local_run/outputs" && sha256sum --quiet -c DIAGNOSTIC_SHA256SUMS)
printf 'Diagnostic hashes verified (partial data excluded): %s\n' "$run_id"

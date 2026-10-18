#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
run_id=${1:?run ID}
[[ "$run_id" =~ ^[a-zA-Z0-9_-]+$ ]] || exit 2
folder="$PWD/experiments/occidata/$run_id"
test -e "$folder/job.sh"
test ! -s "$folder/job_id.txt"
printf '%s\n' 'Previous submission rejected: expired completed-test dependency; no job was allocated.' >> "$folder/submission_attempts.txt"
ssh -o BatchMode=yes "${CAEA_REMOTE:?Set CAEA_REMOTE to your SSH target}" "cd '/projects/caea/runs/$run_id' && sbatch --parsable job.sh" > "$folder/job_id.txt"
cat "$folder/job_id.txt"

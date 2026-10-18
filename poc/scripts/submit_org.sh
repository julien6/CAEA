#!/bin/bash
# Archive transport and durable project work files; scientific execution is Slurm-only.
set -euo pipefail
cd "$(dirname "$0")/../.."
kind=${1:?kind}; config=${2:?config}; run_id=${3:?run ID}
[[ "$run_id" =~ ^[a-zA-Z0-9_-]+$ ]] || exit 2
remote=${CAEA_REMOTE:?Set CAEA_REMOTE to your SSH target (user@cluster)}
local_run="$PWD/experiments/occidata/$run_id"
remote_run="/projects/caea/runs/$run_id"
test ! -e "$local_run"
mkdir -p "$local_run/src" "$local_run/outputs"
cp -a poc "$local_run/src/";cp "$config" "$local_run/config.json"
git rev-parse HEAD > "$local_run/source_commit.txt"
git status --porcelain > "$local_run/source_worktree_status.txt"
(cd "$local_run" && find src -type f -not -path '*/__pycache__/*' -print0 | sort -z | xargs -0 sha256sum) > "$local_run/source-manifest.txt"
tar --exclude=__pycache__ -czf "$local_run/source.tar.gz" -C "$local_run" src
# Preserve scheduler resource directives of the selected job.
sed -n '/^#!/p; /^#SBATCH/p' "poc/scripts/${kind}_job.sh" > "$local_run/job.sh"
cat >> "$local_run/job.sh" <<'WRAP'
set -euo pipefail
run_dir="$SLURM_SUBMIT_DIR"
work=$(mktemp -d "$run_dir/work-${SLURM_JOB_ID}-XXXXXX")
finish() {
 status=$?
 if test -d "$work/outputs"; then
  (cd "$work/outputs" && find . -type f ! -name INNER_SHA256SUMS -print0 | sort -z | xargs -0 -r sha256sum > INNER_SHA256SUMS)
  tar -czf "$run_dir/outputs/artifacts.tar.gz" -C "$work/outputs" .
 fi
 printf '%s\n' "$status" > "$run_dir/outputs/worker_exit.txt"
 # Retain failing project-work paths; remove successful own work only after archiving.
 if test "$status" = 0; then
  if ! rm -rf "$work"; then
   printf '%s\n' "$work" > "$run_dir/outputs/retained_scratch.txt"
   printf '%s\n' 'Archived worker succeeded; NFS cleanup deferred.' > "$run_dir/outputs/cleanup_deferred.txt"
  fi
 else printf '%s\n' "$work" > "$run_dir/outputs/retained_scratch.txt"; fi
 exit "$status"
}
trap finish EXIT
cp "$run_dir/config.json" "$work/config.json"
tar -xzf "$run_dir/source.tar.gz" -C "$work"
mkdir -p "$work/outputs" "$work/tmp"
export TMPDIR="$work/tmp"
export SLURM_SUBMIT_DIR="$work"
WRAP
printf 'bash "$work/src/poc/scripts/%s_job.sh"\n' "$kind" >> "$local_run/job.sh"
# Only a handful of files traverse project storage, avoiding per-episode NFS traffic.
(cd "$local_run" && tar -czf - config.json job.sh source.tar.gz source_commit.txt source_worktree_status.txt source-manifest.txt) | ssh -o BatchMode=yes -o ConnectTimeout=20 "$remote" "test ! -e '$remote_run' && mkdir -p '$remote_run/outputs' && tar -xzf - -C '$remote_run'"
dependency=${4:-}
if [ -n "$dependency" ]; then
 [[ "$dependency" =~ ^[0-9:]+$ ]] || exit 2
 # Completed jobs can disappear rapidly from the Slurm controller. Use accounting
 # to establish success instead of submitting an expired dependency identifier.
 dependency_flag=$(ssh -o BatchMode=yes "$remote" "sacct -j '$dependency' -nP --format=JobID,State,ExitCode")
 if printf '%s\n' "$dependency_flag" | awk -F'|' -v id="$dependency" '$1==id && $2=="COMPLETED" && $3=="0:0"{ok=1} END{exit !ok}'; then
  ssh -o BatchMode=yes "$remote" "cd '$remote_run' && sbatch --parsable job.sh" > "$local_run/job_id.txt"
 else
  ssh -o BatchMode=yes "$remote" "cd '$remote_run' && sbatch --parsable --dependency=afterok:$dependency job.sh" > "$local_run/job_id.txt"
 fi
else
 ssh -o BatchMode=yes "$remote" "cd '$remote_run' && sbatch --parsable job.sh" > "$local_run/job_id.txt"
fi
cat "$local_run/job_id.txt"

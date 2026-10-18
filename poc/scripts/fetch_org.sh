#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
run_id=${1:?run ID}
bash poc/scripts/fetch.sh "$run_id"
folder="$PWD/experiments/occidata/$run_id/outputs"
if test -e "$folder/artifacts.tar.gz"; then
 # Archives are produced exclusively by the recorded Slurm wrapper.
 tar -xzf "$folder/artifacts.tar.gz" -C "$folder"
 (cd "$folder" && sha256sum --quiet -c INNER_SHA256SUMS)
 printf 'Inner artifacts verified: %s\n' "$run_id"
fi

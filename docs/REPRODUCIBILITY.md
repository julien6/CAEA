# Reproduction and verification

## 1. Inspect the fixed records

`results/index.json` lists every exported run, including historical work, pilots,
excluded attempts and recovery. Use the [evidence map](EVIDENCE.md) to identify
the finalized cohorts. A record's presence is not an assertion that it belongs
to a confirmatory result.

```bash
python3 tools/review_artifact.py --runs org-final-closeout-v2 org-final-manuscript-v6 --unpack
```

The destination is `results/unpacked/<run>/`; existing files are never overwritten.
Each chunk and each archived member is checked against its export SHA-256.
This operation is file verification, not scientific replay. Allow space for the
compressed repository plus the selected uncompressed runs. Neither `paper/` nor
private cluster access is required.

## 2. Replay recorded scientific episodes without LLM inference

Target runtime: Python 3.12+. The numeric/replay core uses the standard library.
Use an allocated CPU job for scientific replay; the original campaign used Slurm.
Unpack the selected runs first (on the storage attached to the allocation):

```bash
python3 tools/review_artifact.py --runs org-final-main-0 org-final-robust-0 --unpack
```

Inside a CPU allocation, with the repository as working directory:

```bash
export PYTHONPATH="$PWD/poc"
python3 poc/scripts/org_replay.py --root results/unpacked \
  --runs org-final-main-0 org-final-robust-0 --output replay-output/shard-0
```

Repeat for shards 1–4. Documentary replay additionally needs the original
per-run cases and recorded raw model calls, all included in these exports:

```bash
python3 tools/review_artifact.py --runs org-final-synthetic-recovered-v2 \
  org-final-synthetic-oracle org-final-external-llm org-final-external-control --unpack
# In an allocated CPU job, with PYTHONPATH set as above:
python3 poc/scripts/org_replay.py --root results/unpacked \
  --runs org-final-synthetic-recovered-v2 org-final-synthetic-oracle \
  org-final-external-llm org-final-external-control --output replay-output/documents
```

The replay regenerates synthetic cases, binds recorded calls to extractions and
compares acquisitions, messages, curves and metrics (tolerance 1e-12). It makes
no new model call. Model-generation nondeterminism is irrelevant to this replay;
new inference is a different experiment.

## 3. Recreate analyses and new numerical runs

Unpack all ten numerical shards and the four documentary runs above. Reporting
uses matplotlib in addition to Python. Inside a CPU allocation:

```bash
export PYTHONPATH="$PWD/poc"
python3 poc/scripts/org_study_report.py --root results/unpacked --output reproduction-analysis
python3 -m unittest discover -s poc/tests -v
python3 -m caea.org_v2.run --config poc/configs/org_main_0.json --output new-runs/main-0
```

The manuscript-summary runner uses fixed canonical input run names. To recreate
it, also unpack `org-final-report`; then run:

```bash
python3 poc/scripts/org_manuscript_results.py --root results/unpacked --output reproduction-tables
```

Generated table sources and plots are analysis outputs; manuscript sources are
not needed. Use fresh destinations and keep analyses separate from supplied
records. Full cohorts use all five main and five robustness configurations.

## 4. New Qwen inference

This step requires a GPU allocation, pinned model weights, tokenizer and Ollama.
The data guide records their identities and the 4096-token context/512-token
output contract. `poc/configs/org_synthetic_final_a.json` and `_b.json` define
disjoint cases; `org_external_final.json` defines the external Qwen study.
Adapt model/tokenizer paths and the external dataset location to the unpacked
corpus tasks, preserving model identity, prompts, seeds and scientific settings.
Never resume an LLM run into an output directory that already contains calls.

The scheduler wrappers illustrate the archived OcciData setup. Set
`CAEA_REMOTE=user@your-cluster`, replace `/projects/caea`, `REVIEW_PROJECT`,
partitions and container paths for your allocation. These are deployment
placeholders, not original account details or access instructions. Use a
container providing Python 3.12+, Ollama and tokenizer dependencies; archived
runtime metadata records measured package versions. Model weights and the
cluster container itself are not included in Git.

## Provenance and scope

Transport anonymization replaces operational usernames/project paths and creates
new manifests; it does not establish fresh successful replay. Existing validation
records document the completed campaign. Their original source-hash identifiers
may refer to private execution snapshots rather than this reviewer export.
Current source changes only generalize deployment identifiers and add artifact
tooling/documentation. Verification utilities do not launch Slurm or inference.

See [data and provenance](DATA.md) for the exact export omissions. Archived raw
source trees and scheduler logs are excluded to avoid duplicated code and author
identifiers. No claim is made that every original machine can be reconstructed
without separately obtaining its model weights and container.

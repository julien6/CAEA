# Data, models and export provenance

## Reviewer packaging

The original run directories are kept locally under `experiments/occidata/`.
The public reviewer transport is `results/`: one subdirectory per original run,
40 MiB gzip/tar parts, a member manifest and `index.json`. Unpacking restores a
run's `config.json` and `outputs/` layout, compatible with the scientific readers'
extracted-file path. No Git LFS client is needed.

Included: cases, compressed episode traces, original model calls and responses,
configuration copies, analysis CSV/JSON, plots, external PDFs/pages/tasks,
validation records, model/runtime metadata and resource summaries, whenever
present in the original extracted outputs. Pilots, historical conditions and
failures remain identifiable by their run names and records.

Excluded: duplicate outer archives and source checkouts, source commit/worktree
records, scheduler stdout/stderr and original transport manifests. These contain
redundant copies or author/machine identifiers. Operational username, host and
project identifiers are replaced in text metadata. Each member records its
export SHA-256, original-file SHA-256 and whether metadata was redacted. Original
manifests are not reused as though anonymized files had identical bytes.
Archive ownership/timestamps are normalized. The original private files are not
modified. Retained original source/config hashes describe the experimental
execution; the public manifest describes this distribution.

Directly browsable summaries and the complete final resource ledger have a
separate `results/supplemental_manifest.json`, checked by the same verifier.

The export is produced by `tools/export_review_artifact.py` from existing files.
It is packaging, not experimental computation. The verification utility rejects
unknown/duplicate archive members, checksum mismatches and overwrite attempts.

## External documentation

M57-Patents contributes eight public educational-scenario PDFs (31 pages),
not a recovered disk image or a judicial case. Four questions are development,
sixteen are test; all share a candidate document pool. Eight test questions use
one witness and eight use two. Required spans, normalized offsets and hashes
are automatically checked, without an independent human annotation audit.

Upstream source and terms:
[Digital Corpora M57-Patents](https://digitalcorpora.org/corpora/scenarios/m57-patents/)
and [Digital Corpora terms](https://digitalcorpora.org/about-digitalcorpora/terms-of-use/).
The corpus manifest retains original URLs and document hashes. Upstream default
CC0 terms have explicit-copyright exceptions; this repository does not assert a
blanket license for all files that might exist in disk images. Only the included
public documentation is used.

## Interpreter identity

- Model: Qwen2.5 7B, Q4_K_M, Ollama tag `qwen2.5:7b`.
- Model digest: `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`.
- Tokenizer: `Qwen/Qwen2.5-7B-Instruct`, revision `a09a35458c702b33eeacc393d103063234e8bc28`.
- Original runtime image: CUDA12 / PyTorch NGC 25.01 / Ollama 0.14.3;
  SHA-256 `5cd1ac8061592ec9601f8233ce471b7386bc6ae63d218047d1e48a4d8290d912`.
- Context: 4,096 tokens; output reserve: 512; temperature: 0; seed: 42.

Weights and container are not redistributed. Raw prompts and outputs are included
in documentary run exports. Source checks reject unsupported quotes and filenames.
The 6,862 calls comprise 4,778 synthetic and 2,084 external requests; seven
synthetic attempts fail or are refused. The external study accepts no literal
filename reference. Failed calls remain in the audit.

## Licensing and availability

External data and model weights retain their upstream terms. No new blanket
software license is inferred from their licenses; check the repository's actual
license terms before redistribution. The manuscript and supplementary PDF are supplied separately from this
implementation-and-results repository.

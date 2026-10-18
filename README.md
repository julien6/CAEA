# CAEA — Cooperative Active Evidence Acquisition

This is the anonymous research artifact accompanying **“Following Leads in Budgeted Multi-Agent Investigation.”**
The artifact provides the implementation, configurations, recorded observations,
results, external tasks and reproduction details. The self-contained manuscript is supplied through the submission system; no
auxiliary document is required to assess its contribution. `paper/`
and author working documents are intentionally excluded from this repository.

## Start here

1. Read [the study overview](docs/STUDY.md) and [formal-result guide](docs/THEORY.md)
   for the mechanism, assumptions, experiments and limits.
2. Browse [the aggregate results](results/summary/), [campaign completeness](results/completeness.json)
   and [final resource ledger](results/resource_accounting_final.json), then use [the evidence map](docs/EVIDENCE.md) to locate the records behind each claim.
3. Follow [reproduction instructions](docs/REPRODUCIBILITY.md) to inspect, verify,
   replay or rerun the artifact. Recorded-response replay requires no LLM inference.
4. See [data and provenance](docs/DATA.md) for the export format, anonymization,
   corpus and model identifiers, and the distinction between current and historical runs.

The anonymous access URL is
[anonymous.4open.science/r/CAEA-F04A](https://anonymous.4open.science/r/CAEA-F04A).


## What CAEA does

Agents progressively discover a tree of devices, folders and documents under one
acquisition budget. A document may point to a complementary source. CAEA retains
this lead as an unfinished obligation and prioritizes the legal access operations
needed to follow it. References never bypass discovery or access prerequisites.
The same scoring rule runs under four organizations:

| Organization | Coordination |
|---|---|
| CENT | A coordinator assigns reserved batches using received observations. |
| P2P | Peers decide locally and exchange intentions and observations on a ring. |
| COAL | Temporary groups of at most three workers pursue goals. |
| MKT | A cooperative auctioneer greedily allocates locally submitted offers. |

The environment enforces budgets and legality; an independent evaluator retains
hidden truth. Qwen is a document extractor, **not an agent selecting acquisitions**.
The organizations execute in a single-process simulator, not a physical distributed
investigation deployment.

## Results and boundaries

The finalized organizational study contains **35,840 episodes**: 19,200 primary
numerical episodes, 16,000 sensitivity episodes, 320 Qwen documentary episodes
and 320 matching extraction controls. Its archived closure records complete replay
without new inference. Historical centralized results and unsuccessful attempts
remain separately identifiable in the exported records.

In mixed complementary numerical cases, CAEA improves information–cost AUC over
the obligation-free baseline by **0.100–0.149**, depending on organization.
Synthetic Qwen documents retain gains of **0.059–0.090**. These are conditional
results: sequential feedback can be more cost-efficient; eight-worker coalitions
can fragment; fixed-horizon utility gains do not establish improved threshold
attainment after correction.

**No dependency-guided gain is demonstrated externally.** The sixteen test
questions belong to one M57-Patents educational documentation scenario. No
supported filename references are extracted, so CAEA ties the baseline.
These correlated questions are not sixteen independent investigations. The work
does not establish judicial usefulness or general retrieval superiority.

The archived ledger reports **3.249 GPU-hours and 16.578 CPU-core-hours across
70 organizational-study allocations**, including pilots, failures and recovery.
These are allocation durations, not simulated acquisition time or hardware speedups.

## Repository contents

| Path | Contents |
|---|---|
| `poc/caea/org_v2/` | Current environment, acquisition core, organizations, extraction and analysis |
| `poc/caea/` | Shared components and separately identified historical engine |
| `poc/configs/` | Fixed settings, controls, pilots and validation configurations |
| `poc/tests/` | Constructed invariant and compatibility checks |
| `poc/scripts/` | Scientific runners, analysis, replay and example Slurm wrappers |
| `results/` | Chunked run records, per-file checksums and export index |
| `tools/` | Transport verification, unpacking and export utilities; no scientific inference |
| `docs/` | Reviewer-oriented study, evidence and reproduction documentation |

## Verify the supplied records

Python 3.12+ is the target scientific runtime. Transport verification uses only
the Python standard library and does not run a simulation:

```bash
python3 tools/review_artifact.py --runs org-final-closeout-v2 org-final-manuscript-v6
# Check every exported run (larger disk/network read):
make verify-artifact
```

Raw records are split into 40 MiB parts to avoid individual oversized Git blobs.
They are ordinary gzip/tar data, not Git LFS pointers. The unpacking command
verifies both parts and individual files before restoring a selected run:

```bash
python3 tools/review_artifact.py --runs org-final-main-0 --unpack
```

Scientific simulations, tests, statistical analyses and inference were executed
on OcciData allocations. The reproduction guide distinguishes those operations
from local file verification and explains the machine-specific settings to adapt.
Model weights and the cluster container are not bundled; identities are recorded.
Anonymized metadata copies have fresh export checksums. Original private run
folders are not silently rewritten or presented as publicly included source snapshots.

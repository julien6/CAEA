# Evidence map

Unpack a run with `tools/review_artifact.py --runs RUN --unpack`. The paths below
then live under `results/unpacked/RUN/outputs/`. Each exported file has its own
checksum and original-file checksum in `results/RUN/manifest.json`.

| Question or claim | Run and record | Scope |
|---|---|---|
| Finalized episode counts and replay | `org-final-closeout-v2/outputs/closure.json` | 35,840 current episodes; historical cohorts separate |
| Main CAEA–Joint and CAEA–Myopic contrasts | `org-final-report/outputs/main/analysis.json` | Paired case comparisons; fixed Holm families |
| Sensitivity and coalition fragmentation | `org-final-report/outputs/robust/analysis.json` | Twenty one-factor settings |
| Final tables and temporal contrasts | `org-final-manuscript-v6/outputs/` | `study_summary.json`, `temporal_contrasts.json`, table sources and plots |
| Numerical trajectories | `org-final-main-0` through `-4`, `org-final-robust-0` through `-4` | Cases, episode records, messages and used settings |
| Synthetic Qwen observations | `org-final-synthetic-recovered-v2/outputs/` | Complete 192-episode recovery; raw calls preserved |
| Exact synthetic controls | `org-final-synthetic-oracle/outputs/` | Separate 192-episode control |
| External Qwen observations and deterministic controls | `org-final-external-llm`, `org-final-external-control` | 128 episodes each; no supported filename-reference gain |
| Corpus and witnesses | `org-corpus-bundle/outputs/corpus/` | Eight public PDFs, extracted pages, tasks and annotation audit |
| Full documentary replay | `org-final-documentary-validation-v4/outputs/replay.json` | 640 episodes; no new inference |
| Numerical replays | `org-final-numeric-replay-0` through `-4` | 7,040 episodes per shard |
| Resource/failure accounting | `results/resource_accounting_final.json` (directly readable) | Complete 70-allocation ledger, including the last bookkeeping job |
| Organizational semantics and invariants | `poc/caea/org_v2/`, `poc/tests/test_org.py` | Local-knowledge simulation; no physical deployment claim |

Recovery records preserve failed parent states: two GPU workers completed and
archived all planned episodes but subsequently failed during NFS cleanup. A
successful CPU recovery verified complete outputs and replayed them without
inference. These are not new GPU observations or silently relabelled jobs.
The export includes earlier records so exclusions remain inspectable, rather
than treating every historical directory as a final cohort.

Aggregates are also directly browsable in `results/summary/`, without unpacking.
The older `org-final-ledger` summary precedes its own bookkeeping allocation;
use `results/resource_accounting_final.json` for the complete 70-job total.

# CAEA implementation

Start with the [reviewer guide](../README.md) and
[reproduction instructions](../docs/REPRODUCIBILITY.md).

## Current organizational engine

`caea/org_v2/model.py` represents hidden cases and local knowledge;
`engine.py` handles legality, budget admission, simulated batches and evidence
accounting; `protocols.py` implements CENT, P2P, COAL and MKT; `extractor.py`
and `external.py` handle documentary interpretation and source-grounded tasks.
`analysis.py`, `storage.py`, `archive.py` and `staging.py` support statistics,
recording and replay. See `tests/test_org.py` for constructed checks.

The common core has four variants: Joint (no obligations), Myopic (companion-read
bonus), CAEA (access-path propagation) and exploratory CostPath. Policies do not
receive the evaluator's hidden labels or utility.

`configs/org_main_*.json` and `org_robust_*.json` define the numerical shards.
Synthetic Qwen shards A/B use disjoint cases. Exact/deterministic controls are
separate configurations. Runs containing raw model calls require fresh output
folders; recorded-response replay is a different operation from measured inference.

## Historical engine

Other modules under `caea/` preserve the earlier centralized study and shared
extractor/generator functionality. Earlier common-state policies are not the
current local-knowledge organizational protocols. Historical pilots, failed
extraction contracts and follow-up configurations are retained for provenance,
not counted as new confirmations of the organizational results.

## Execution

Use Python 3.12+ and `PYTHONPATH=poc`. Numeric execution and replay do not require
a GPU or model weights. Plotting uses matplotlib; Qwen extraction additionally
requires transformers/tokenizer resources and Ollama. The recorded model identity
and context contract are in the data guide.

Slurm wrappers are examples from the experimental workflow. The public source
uses `/projects/caea` and `REVIEW_PROJECT` as deployment placeholders; adapt these,
container paths and scheduler resources to your allocation. Set `CAEA_REMOTE`
for SSH transport. They do not grant access to the original cluster account.
The scientific Python entry points accept explicit input/output paths and can
run inside an allocated batch job without these transport wrappers.

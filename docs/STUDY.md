# Study specification for reviewers

## Problem and mechanism

A static rooted tree contains devices, folders and artifacts. Initially only root
metadata is known. `load` opens an exposed device; `discover` lists immediate
children; `read` acquires an accessible artifact subject to worker capacity.
Every accepted acquisition consumes the shared budget, including duplicates.
Evaluation deduplicates evidence by original source identifier. Only observations
and delivered messages enter an agent's local knowledge.

CAEA creates an obligation from an acquired, source-bound companion reference.
For a legal action on its path, the bonus is expected channel information divided
by remaining path-entry count plus current action cost. Myopic applies a bonus
only to a companion read; Joint omits obligations; CostPath uses estimated remaining
legal cost. These are fixed heuristics, not optimal planners or learned policies.

CENT has a separate coordinator view; P2P uses bidirectional-ring gossip and local
intention conflicts; COAL recruits temporary groups of at most three with one
membership per agent; MKT clears up to three local offers per worker greedily.
The validator admits simultaneous requests in a deterministic rotating order
independent of action scores. MKT makes no truthfulness guarantee.

## Finalized experimental design

| Study | Cases/repetitions and factors | Episodes |
|---|---|---:|
| Primary numerical | 100 fresh cases × 2 repetitions × 4 organizations × 4 cores × 6 conditions | 19,200 |
| Sensitivity | 50 other cases × 2 repetitions × 4 organizations × 2 cores × 20 one-factor settings | 16,000 |
| Synthetic documents | 24 new cases × 4 organizations × 2 cores; Qwen and exact controls | 384 |
| External documents | 16 test questions × 4 organizations × 2 cores; Qwen and deterministic controls | 256 |

Default numerical worlds have four questions, four channels per question and 128
artifacts across four devices with four folders each. Reliability is .85; complementary
channels use XOR shares whose strict subsets are uninformative. Budget is 72,
three workers and capacity three; artifact sizes are sampled from {1,1,2,3}.
The six primary conditions are direct, mixed (.65 split channels), pairs, absent
references, half-retained references and half-misdirected references. A misleading
link may reach noise or another informative channel.

Sensitivity settings separately vary worker count (1,2,4,8), communication
coefficients (.01,.1), delay (1,3), heterogeneous capacities, a scheduled outage,
misleading-link rates (.25,.75), depths (2,5), fragments (3,4), budget (36,120),
and bonus multipliers (.5,2). This is not a full Cartesian product.

## Metrics and inference

Cost AUC integrates exact information utility along cumulative acquisition cost,
normalizes by the shared budget and carries terminal utility to the remaining
interval. Global acquired information can combine sources held by different
workers before they communicate. It is not the time at which one agent knows a
conclusion. Local posterior Brier scores are separate record-based proxies.

Simulated batch time is maximum action duration plus synchronization and declared
communication latency. Linear, ten-times-slower and reproducible lognormal
models rescore schedules. None measures hardware speedup. Threshold failures
remain censored; restricted time caps them at the horizon rather than dropping them.

Two policy repetitions are averaged by case before 4,000 bootstrap resamples
and 10,000 two-sided sign-flip draws (seed 20261018, add-one correction). Main
Holm families have 48 contrasts per metric, exploratory CostPath 24, sensitivity
80. External questions share one scenario and are analyzed descriptively.

## Negative results and validity limits

The single-worker control remains competitive in cost efficiency. Three-worker
COAL can reproduce central allocations under the stated equal-information
conditions, whereas larger teams fragment without inter-group sharing. More
workers do not uniformly improve threshold attainment. External CAEA ties Joint
because no supported literal filename leads are extracted. Public M57 scenario
PDFs, an artificial PDF/page access layout and automatically checked witnesses
do not establish forensic or judicial operational validity.

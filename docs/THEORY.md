# Formal results and their scope

These statements summarize the finalized mechanism study. Complete statements,
assumptions and proof arguments are also in the submitted article and companion.
No new theoretical guarantee is introduced by this artifact documentation.

1. **Observable non-interference.** Fixed local parameters and seeds, initial
   local state and delivered observations/control histories determine local
   proposals, independently of unobserved hidden annotations. Induction over
   delivered events preserves local states. This is an interface guarantee,
   not a sandbox against arbitrary malicious Python code.
2. **Budget, capacity and provenance.** Each action is checked and charged
   atomically before admission. The shared budget and worker capacities remain
   feasible by induction. Original evidence is keyed by source identity;
   redundant acquisition costs money but relaying it does not duplicate evidence.
3. **Synthetic complementarity.** An incomplete XOR-share group has a missing
   independent uniform mask and is uninformative about the channel bit. The
   complete group recovers one noisy channel. Independent completed channels
   multiply likelihood ratios. This model does not establish a property of
   arbitrary natural-language evidence or LLM interpretations.
4. **Conditional propagation separation.** After the first share, let the only
   companion require one unit of folder discovery and one unit of reading, with
   remaining budget two. A known topic-labelled noise read scores .16. Myopic
   gives folder discovery only .055, spends one on noise and loses the channel.
   CAEA adds expected channel information divided by three, giving approximately
   .185 at posterior .5 and reliability .85; it discovers the folder and then
   reads the companion. This is a constructed existence result for fixed scores,
   not universal dominance or an optimality theorem.
5. **P2P communication horizon.** On a reliable ring with integer delay delta ≥ 1,
   a lead cannot influence a worker at distance d before d × delta rounds unless
   that worker independently observes its source. Every hop needs delta rounds.
   Immediate forwarding attains delivery at that horizon; acquisition can take
   longer. Zero-delay closure is a simulator idealization.
6. **Single-coalition reduction.** If a coalition contains all available workers
   and its leader matches CENT's record-based state, order, capacities, seeds and
   reservations, it proposes the same batch. Induct over identically selected
   worker assignments. Whole-run equality requires these hypotheses at every
   epoch; communication volume and timing can still differ.

These results explain the controlled contrasts. Sharing a scoring rule alone
establishes neither organizational equivalence nor a benefit from more workers.
Global acquisition utility can include sources held by different agents before
communication; local inference and deadline attainment are separate outcomes.

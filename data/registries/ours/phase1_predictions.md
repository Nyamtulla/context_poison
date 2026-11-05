# Phase 1 predictions for the proposed fix (specvote)

## When these were written, and what had run by then

The plan promised that the predictions would be "written into the runner
before it runs". That did not happen. They were stated once, in the Phase 1
plan the project lead approved (chat, 2026-11-04 22:41 UTC). They were first
committed in this file at 2026-11-04 18:29 CST (00:29 UTC on 11-05), after
Stage 2 had started.

By then three Stage 2 runs had finished on Mistral-7B:
- `specvote_incidental_stale_mistral7b.json`
- `specvote_incidental_stale_reworded_mistral7b.json`
- `specvote_distractor_evidence_mistral7b.json`

A fourth (misretrieval) was running. None of their results had been opened
or scored when this file was written. No attack condition had run.

The predictions below are copied word for word from the plan. Nothing in
them was changed after any run finished.

## Predictions (verbatim from the approved plan)

1. On both models, the fix gives the stale answer less often than
   ReliabilityRAG with five identical or five reworded stale copies, by more
   than the detection threshold.
2. On clean questions, the fix costs no more than 3 points against
   ReliabilityRAG and no more than 7 against the undefended model.
3. Against misretrieval and dilution it does no measurable harm.
4. Against PoisonedRAG it does about as well as RobustRAG.
5. **Our attack on the merge beats it** at three or more planted passages. We
   expect this and will report it as the fix's known limit, together with the
   number of passages needed.

## Changes to the plan since it was approved

- **Second model.** The plan named Llama-3-8B-Instruct. The project lead chose
  Llama-3.1-8B-Instruct (Stage 3). Predictions 1 and 2 ("on both models") now
  refer to Mistral-7B and Llama-3.1-8B.
- **PoisonedRAG has two versions.** The grid's attack contexts copy one text
  into every planted slot (RobustRAG's construction), so a fix that merges
  copies wins those by construction. Stage 2 adds `p1_poisonedrag_distinct`:
  PoisonedRAG's five released texts, one per slot. Prediction 4 was written
  before this split and does not say which version it means; it is scored on
  both and reported separately.
- **CorruptRAG** runs as its template version only (decided 2026-11-04), in
  Stage 4 rather than Stage 2.

## Added prediction (new, not in the approved plan)

Written in this file at the time above, before any attack condition had run.

6. On PoisonedRAG, the fix gives the planted answer more often with the five
   distinct texts than with the copied text, at three and at five planted
   passages, by more than the detection threshold.

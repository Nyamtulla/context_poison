# RQ6 (continued) — Transfer Predictions and Their Validation

Generated 2026-09-06, revised 2026-09-07. Companion to `rq6_case_studies.md`.

RQ6's nine case studies established *that* transfer tracks pipeline position:
ingestion-stage defenses generalized across threat models, reasoning-stage
results were mixed, and execution-stage defenses could not be evaluated at all.
This document takes the next step the finding invites — using it as a
**predictor** rather than a description, and then testing one prediction by
execution.

It is scoped deliberately. The audit of whether RQ5's coverage gap is real
lives in `rq5_coverage_matrix.md` (Addendum, 2026-09-07), because that work
corrected our own measurement rather than discovering anything about the
literature. What follows is the part that produces new claims.

## Headline result

**RQ6's intervention-point finding is predictive, and the first prediction
tested holds.** Every mechanism with no confirmed defense receives a ranked
transfer hypothesis; the highest-priority testable one was run, and RobustRAG —
never evaluated against BadRAG — neutralizes BadRAG's denial-of-service
payload almost completely.

## Transfer prediction

Uses RQ6's finding as a *predictor* rather than a description. RQ6 observed
that generalization tracked intervention point (ingestion 3/4 full, reasoning
1/3, execution 0/2 — neither execution defense would even run), so intervention
point becomes a prior, combined with the similarity between what a defense
*was* tested on and the untested mechanism.

```
score(defense, mechanism) = similarity(mechanism, closest mechanism the defense was tested on)
                          × transfer_prior(defense.intervention_point)
```

Similarity uses the taxonomy already in the registry: both channel and
consequence match = 1.0, consequence only = 0.6, channel only = 0.5, track
only = 0.2. Priors are RQ6's observed rates: ingestion 0.75, reasoning 0.33,
execution 0.10.

Every uncovered mechanism received at least one hypothesis;
**97** have a top candidate with released code. Output:
`data/registries/stage2_transfer_predictions.json`. These are claims to test,
not findings.

## Validation by execution: RobustRAG vs. BadRAG

The top-ranked testable pair. BadRAG (92 citations) and PoisonedRAG share
channel (RAG) and consequence (goal-hijack) — similarity 1.0 — and RobustRAG
was validated against PoisonedRAG but never against BadRAG.

**Why the outcome was not obvious.** PoisonedRAG plants a passage *asserting a
false answer*, which isolate-then-aggregate beats by construction: one wrong
isolated vote loses to the clean majority. BadRAG's payloads do something
else — its Alignment-as-an-Attack makes the model's own safety alignment fire
so it *refuses*, and refusal is not a wrong vote but an absent one.

Same dataset, model, defense config, top_k, corruption_size and slot placement
as our PoisonedRAG run, so attack type is the only variable. n=40,
Mistral-7B-Instruct-v0.2, RobustRAG keyword aggregation.

| Scenario | Undefended acc | Defended acc | Undefended refusal | Defended refusal |
|---|---:|---:|---:|---:|
| Clean | 72.5% | 60.0% | 0% | 0% |
| PoisonedRAG *(what RobustRAG was validated on)* | 10.0% | 55.0% | 0% | 0% |
| **BadRAG — DoS payload** | **22.5%** | **57.5%** | **52.5%** | **2.5%** |
| BadRAG — sentiment payload | 72.5% | 60.0% | 0% | 0% |

**The DoS transfer holds, and cleanly.** Undefended, BadRAG's payload drives
accuracy from 72.5% to 22.5% and makes the model refuse on 52.5% of questions.
RobustRAG restores accuracy to 57.5% — essentially its own clean defended
ceiling of 60.0% — and collapses refusals to 2.5%. On **20 of 40 items** the
undefended model refused and the defended model answered; on the example
inspected, correctly.

The mechanism is exactly the predicted one: isolation means only the single
poisoned passage yields a refusal, and keyword aggregation over the remaining
nine never sees it. A refusal-inducing passage is *weaker* against RobustRAG
than a false-answer passage, because it forfeits its vote instead of casting a
wrong one.

**The sentiment payload result is a scope limitation, not a defense success.**
It moved nothing (72.5% undefended = clean). RealtimeQA is short-answer
factual QA where the answer is a name, date or number; sentiment steering
targets open-ended generation, as in BadRAG's own NQ/MS MARCO setting. The
attack never landed, so **no transfer claim is made for it** — it is untested,
not defeated.

### Scope and honesty notes

- BadRAG's **retrieval phase is conceded, not reproduced.** Its COP
  gradient-optimization achieves 98.2% top-1 retrieval for triggered queries;
  we grant the attack its own demonstrated capability and place the poisoned
  passage in the retrieved set. RobustRAG operates after retrieval, so this is
  the input it would face in a successful BadRAG attack.
- The payload text **reimplements BadRAG's described payload strategy**
  (alignment-triggering content; selectively negative framing), not a
  byte-exact copy of COP-optimized passages, which were optimized against a
  specific retriever and carry no meaning outside it.
- One pair, n=40, one model. This validates the *method* and one hypothesis;
  it does not establish that ingestion defenses transfer generally.

## What this adds, and what it does not

**Adds:** a ranked, testable hypothesis for every mechanism nothing has been
evaluated against, derived from an empirical prior rather than intuition; and
one validated result showing a published ingestion-stage defense already
defeats a 92-citation attack nobody had run it against.

**Does not add:** any claim about the size of the coverage gap. The gap is
RQ5's finding, and the corrections that moved it from 63.4% to 61.0% were
repairs to our own extraction and a duplicate-paper bug, documented in
`rq5_coverage_matrix.md`. They are not evidence about the field and are
deliberately kept out of this document's claims.

**One pair, n=40, one model.** This validates the method and one hypothesis; it
does not establish that ingestion defenses transfer generally.

## Reproducing

```bash
python scripts/stage2_transfer_predictions.py      # ranked transfer hypotheses
# validation runs inside the RobustRAG reconstruction environment:
python scripts/stage3_badrag_robustrag.py --n 40

# the coverage-gap audit (a correction pass, reported under RQ5) is:
#   scripts/backfill_mechanism_citations.py
#   scripts/stage1_build_evidence.py
#   scripts/stage1_fulltext_scan.py
```

## Executed transfer tests: DataSentinel (2026-09-10)

The reverse scan established which candidate pairs were already answered in the
published literature (`rq5_coverage_matrix.md`). Of the 111 Stage 2 predictions,
three were: DataSentinel vs. DataFlip, ObliInjection and ToolHijacker, all three
already reported as defense failures. Those were struck from the queue rather
than re-derived. This section reports running the rest.

### What was actually testable

The queue held 130 untested candidate pairs with released code, collapsing onto
four defenses — DataSentinel (66 pairs), RobustRAG (43), ACON (12), CRAG (9).
Taking DataSentinel first, its 66 mechanisms triage as:

| | count | why |
|---|---:|---|
| reconstructable text payload | 26 | the paper describes text placed in a data channel |
| the optimizer *is* the attack | 26 | GCG variants, fuzzers, MCTS, RL — a hand-authored stand-in would test our writing, not their method |
| channel mismatch | 7 | image, audio or 3D carrier; DataSentinel takes text |
| no single payload | 6 | a composition, a cloaking policy, a missing protocol check |

The 39 excluded are listed individually in `scripts/transfer_scenarios.py`.
Excluding them is not a judgement about the attack — it means a run here could
not produce evidence about it, and a number that looks like evidence but is not
is worse than an acknowledged gap.

### The control, and why it matters

Every run carries DataSentinel's own attack (Open-Prompt-Injection's
CombineAttacker) as a positive control. It read **100%** detected, against
**0%** on clean text and **0%** on an appended non-instructional sentence.
The reconstruction reproduces the paper, so the rest of the run is
interpretable.

### The result that a detection table alone would have got wrong

Running the 26 payloads through the detector produces a striking-looking table:
13 mechanisms flagged 100% of the time, 11 flagged at 0–2.5%. Read alone, that
says DataSentinel misses eleven attacks.

It does not, and this is the methodological point of the section. **A defense
that misses an inert payload has not failed at anything.** So the same payloads
were run against an *undefended* victim (Llama-3.2-3B-Instruct — deliberately a
different model family from the detector's Mistral-7B-v0.1 base, so "hijacks the
victim" and "hijacks the detector" stay separate questions) to establish whether
each attack works at all.

Only **7 of 26** hijacked the victim. Crossing the two runs:

| verdict | n | mechanisms |
|---|---:|---|
| defense holds | 5 | Prompt Infection (95% hijack / 100% detected), ToolLeak (55/100), HARE (45/100), MAS hijacking (20/100), Cognitive Overload (15/100) |
| **defense misses an effective attack** | **1** | **memory-persistence framing (ChatGPT memory/URL-exfiltration bypass) — 30% hijack, 0% detected** |
| marginal | 2 | Silent Egress (5/2.5), MAD-Spear (5/0) |
| inconclusive | 19 | the reconstruction did not hijack the victim, so its detection number says nothing |

The one real hole is worth stating precisely: a payload phrased as a durable
instruction to *remember* ("remember for all future conversations in this
account — …") hijacked the victim 30% of the time and was flagged **zero**
times. DataSentinel's detection is a behavioural hijack test — it wraps the data
in a canary instruction and checks whether the model still emits the secret key
— so an instruction aimed at a *future* turn rather than the current one does
not hijack the canary, and reads as clean.

### The limitation that dominates the rest

19 of 26 are inconclusive, and the reason is structural rather than incidental.
DataSentinel's harness models a **text-classification victim** — a sentiment
task over a movie review. Most of the mechanisms in the queue attack **agents**:
plan state, skill files, MCP error paths, tool-call arguments, cross-app
context. Those payloads have nothing to act on in a sentiment prompt, so they do
not hijack, so their detection numbers are uninterpretable.

This is not a defect in the reconstruction. It is a statement about what this
defense's own evaluation apparatus can measure, and it applies to the published
result as much as to ours: **DataSentinel's reported generalization was
established on a text-classification victim, and the corpus's agentic mechanisms
are outside what that apparatus can speak to.** Testing them faithfully needs an
agent harness (AgentDojo, InjecAgent), which is a different piece of work and is
recorded here as the next step rather than approximated.

Artifacts: `data/registries/transfer_test_results_datasentinel.json`,
`scripts/transfer_scenarios.py` (payload constructions and the full exclusion
list), `scripts/run_transfer_tests.py`, `scripts/attack_efficacy_standalone.py`.

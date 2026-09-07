# RQ5b — Coverage Recovery and Transfer Validation

Generated 2026-09-06. Extends RQ5 (coverage matrix) and RQ6 (defense
generalization) to answer a question they raised but did not settle: **of the
mechanisms nothing has ever been tested against, how many are genuinely
undefended — and for those that are, which existing defense should work?**

Three stages: recover coverage the original extraction missed (Stage 1),
predict which defenses transfer to what remains (Stage 2), and test the top
prediction by execution (Stage 3).

## Headline result

**The 116 "never defended" mechanisms are almost entirely real, not a
measurement artifact — and the first transfer prediction tested holds.**

- Stage 1 recovered only **4** pairs from an exhaustive citation + full-text
  recovery pass: 116 → **112** uncovered. The gap is not an extraction failure.
- Stage 2 produced a ranked transfer hypothesis for **all 112**, with **97**
  testable today (top candidate has released code).
- Stage 3 tested the highest-priority testable pair and it **transferred**:
  RobustRAG, never evaluated against BadRAG, neutralizes BadRAG's
  denial-of-service payload almost completely.

## Stage 1 — Coverage recovery

RQ5 matched defenses to mechanisms using only the *extracted summary fields*,
so an attack named only in a results table or appendix was invisible to it.
Two independent recovery generators were run and every candidate adjudicated
by reading the surrounding text.

**A prerequisite fix.** The original snowball did BFS from the 51 seeds, so
forward citations were only ever fetched for seeds and hop-1 papers. Most
mechanism papers were found by keyword search or at hop 2, so "no defense
paper cites this attack" was *unmeasurable*, not false. Backfilling forward
citations for all 183 mechanism papers (`scripts/backfill_mechanism_citations.py`)
raised the uncovered papers with any recorded citer from **43 to 93 of 116**.

| Generator | Candidates | Survived "actually evaluated" |
|---|---:|---:|
| Citation (defense paper cites mechanism paper) | 147 | 3 |
| Full text, bibliography stripped | 35 | 4 |
| **Union (confirmed)** | | **4** |

The four: RETA ← RL-Hammer, PISmith, AutoInject (all named in its
adaptive-evaluation setup with per-attacker hyperparameters in Appendix C.1);
SnapGuard ← WebInject (named in its evaluation attack list and as a Table 1
column). Recorded with per-pair evidence in
`data/registries/rq5_supplementary_pairs.json`.

**Three method findings worth reporting:**

1. **Citation matching is complementary, not superior.** As a control it
   re-found only **19 of 67 (28%)** known-covered mechanisms — defense papers
   routinely evaluate an attack through a bundled benchmark (AgentDojo,
   InjecAgent) without citing the original attack paper. It also *missed*
   RETA ← AutoInject, which full-text found. Neither signal dominates; both
   are needed.
2. **Defense papers cite attack papers as related work, not as evaluation
   targets.** The overwhelming majority of the 147 citation candidates mention
   the mechanism only in the bibliography or one related-work sentence. This
   is direct evidence *for* RQ7's invention-outpaces-evaluation finding, not
   an artifact that explains it away.
3. **Generic-phrase mechanisms produce false positives.** Three separate
   defenses (CodeDelegator, Free()LM, AegisAgent) use "context pollution" to
   mean something other than the registry's `Context Pollution (evolutionary
   search history bias)` — CodeDelegator's paper is literally titled
   "Mitigating Context Pollution." A named-entity registry with common-noun
   names is an entity-resolution hazard.

**A permanent floor:** 20 of the 116 are `UNNAMED:` entries — descriptive
labels assigned during extraction, never terms the literature uses. No
name-based method can ever recover them.

RQ5's originally published numbers remain exactly reproducible via
`registry_source.load_all(include_supplementary=False)`.

## Stage 2 — Transfer prediction

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

Every one of the 112 uncovered mechanisms received at least one hypothesis;
**97** have a top candidate with released code. Output:
`data/registries/stage2_transfer_predictions.json`. These are claims to test,
not findings.

## Stage 3 — Validation by execution: RobustRAG vs. BadRAG

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

### Scope and honesty notes for Stage 3

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

## What this changes

RQ5 said 63.4% of mechanisms have never been defended. Stage 1 shows that is
real (63.4% → 61.2%, not an artifact). Stage 2 turns the gap from a static
complaint into 112 ranked, testable hypotheses. Stage 3 shows the first one
tested holds — an existing, published, ingestion-stage defense already defeats
a 92-citation attack nobody had ever run it against.

That is the constructive form of the SoK's contribution: not only "the field
does not cross-test," but "here is what cross-testing would find, and here is
one result it already yields."

## Reproducing

```bash
python scripts/backfill_mechanism_citations.py     # forward citations for mechanism papers
python scripts/stage1_build_evidence.py            # citation-based candidates
python scripts/stage1_fulltext_scan.py             # full-text candidates
python scripts/stage2_transfer_predictions.py      # ranked transfer hypotheses
# Stage 3 runs inside the RobustRAG reconstruction environment:
python scripts/stage3_badrag_robustrag.py --n 40
```

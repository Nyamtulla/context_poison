---
title: "SoK: Context Integrity for LLM Agents"
type: outline
target: manuscript/sok.qmd
plan_task: "RESEARCH_ROADMAP.md — SoK manuscript draft"
created: 2026-10-12
updated: 2026-10-12
target_words: 11000
status: draft
---

# Outline: SoK — Context Integrity for LLM Agents

## Thesis

Defenses published for *accidental* context degradation fail against
*deliberate* context attack in a systematic way, because the mechanism that
repairs accidental corruption — shifting the model's trust toward retrieved
text and away from its own parameters — is precisely the mechanism an attacker
who controls that text turns against the model.

## Claim chain

Two research communities describe the same failure, that a model cannot tell
which part of its context deserves trust, and they do not read each other:
60.5 % of the channel × intent × consequence taxonomy is empty, and
cross-citation runs at 11.7 % and 9.1 %. Neither community cross-tests at the
granularity its own claims require — 55.3 % of named mechanisms have no defense
evaluated against them, and 82.7 % of matched defenses were tested against
exactly one mechanism — so the question of whether one literature's defenses
survive the other's attacks has never been asked, let alone answered. We answer
it by execution rather than by reading: 70 (defense, attack) combinations run on
the authors' own released code and weights, each gated on an attack-works-first
control and a fixed detectability threshold. The result is sharper than
"defenses underperform": there is a design rule with a measured scope
condition, and the dominant variable in the matrix is frequently the base model
or the particular implementation rather than the defense family a reader would
generalize to. Reaching that required three controls neither literature
reports — a no-retrieval baseline, an abstention axis, and a model control —
and each of them overturned a conclusion we would otherwise have published,
which is itself the methodological contribution.

## Sections

### S1 — Introduction: one failure, two vocabularies

- **Claim:** The security and ML/AI literatures study one property under two
  vocabularies, and the gap between them is measurable rather than rhetorical.
- **Evidence:** `[@greshake-2023-not]`, `[@zhan-2024-injecagent]`,
  `[@zou-2024-poisonedrag]`, `[@xiang-2024-certifiably]`; RQ1/RQ2 numbers
- **Synthesis basis:** `rq1_taxonomy_analysis.md`, `cross_citation_analysis.md`
- **Function:** Establishes the gap as an empirical claim, and promises the
  execution test as the paper's distinguishing move.
- **Not here:** The design rule itself; that is earned in S7, not asserted up front.
- **Budget:** ~900 words
- **Status:** outlined

### S2 — Scope, corpus and taxonomy

- **Claim:** The taxonomy (9 channels × 3 intents × 6 consequences) is the
  minimum structure that lets the two literatures be compared at all, and the
  corpus construction is reproducible.
- **Evidence:** corpus pipeline; `config.yaml` screening criteria
- **Synthesis basis:** `paper_collection_methodology.md`, `rescreening_log.md`
- **Function:** Gives the reader the units every later count is expressed in.
- **Not here:** Findings. This section defines; it does not conclude.
- **Budget:** ~1100 words
- **Status:** outlined

### S3 — What is studied and what is not

- **Claim:** 60.5 % of the taxonomy is empty, and the emptiness is structured:
  two cells are mirror images, each holding one literature's work and nothing
  from the other.
- **Evidence:** RQ1 cell counts; tool-output × goal-hijack (61 attacks, 1
  defense); RAG × reasoning-corruption (13 defenses with code, no runnable attack)
- **Synthesis basis:** `rq1_taxonomy_analysis.md`, `next_cell_plan.md`
- **Function:** Locates the silent-corruption cell as the only place the
  execution test is possible, motivating S6.
- **Not here:** Why the field cross-tests so little; that is S5.
- **Budget:** ~1000 words
- **Status:** outlined

### S4 — The two literatures do not meet

- **Claim:** Cross-citation is 11.7 % (security → ML/AI) and 9.1 %
  (ML/AI → security) over the full coded population, not a sample.
- **Evidence:** `cross_citation_analysis.md`; citation-graph isolate audit
- **Synthesis basis:** `cross_citation_analysis.md`, `citation_graph_isolates.md`
- **Function:** Converts "the communities are separate" from an impression into
  a rate with a known denominator, and reports what the isolate audit corrected.
- **Not here:** Blame. The claim is structural, not about authors.
- **Budget:** ~800 words
- **Status:** outlined

### S5 — How the field evaluates

- **Claim:** There is essentially no generalist defense at this granularity:
  82.7 % of matched defenses were tested against exactly one mechanism, and
  55.3 % of mechanisms have zero defenses evaluated against them.
- **Evidence:** `rq5_coverage_matrix.md`; reverse-scan recovery of 37 pairs
- **Synthesis basis:** `rq5_coverage_matrix.md`, `screening_gap_analysis.md`
- **Function:** Establishes that the cross-literature test is missing because
  cross-testing in general is missing — the gap is not special to our question.
- **Not here:** Our own runs.
- **Budget:** ~1000 words
- **Status:** outlined

### S6 — Executing the test: method

- **Claim:** A transfer result is only reportable when the attack demonstrably
  works on the undefended arm and the observed change clears a pre-computed
  minimum detectable change; everything else is recorded as unresolvable.
- **Evidence:** control-fires-first rule; mdr at α=.05, power=.80; Wilson CIs;
  authors' own scorers imported unchanged
- **Synthesis basis:** `CELL_CAMPAIGN.md`, `transfer_stats.py`
- **Function:** Buys the right to report negative results as results.
- **Not here:** Any finding. Method only.
- **Budget:** ~1100 words
- **Status:** outlined

### S7 — The design rule and its scope condition

- **Claim:** Defenses that increase reliance on retrieved context are correct
  when the context is merely stale and dangerous when an attacker owns it —
  and the rule's real content is narrower than its usual wording: suppressing
  parametric memory hurts only where that memory held the right answer.
- **Evidence:** ParamMute, CK-PLUG, SpARE, SHIFT cells; saturation invariant
  (~32 pp); COIECD as the measured scope condition
- **Synthesis basis:** `SYNTHESIS_silent_corruption_cell.md`,
  `saturation_invariant.md`, `coiecd_result.md`
- **Function:** The paper's central positive claim, stated with its limits.
- **Not here:** Aggregation defenses — they do not have this failure mode (S8).
- **Budget:** ~1600 words
- **Status:** outlined

### S8 — Principle, implementation, or model?

- **Claim:** The unit a reader can act on is not the defense family: two
  implementations of one published principle disagree by 29.7 points inside one
  codebase, and changing only the base model changes an effect's size, its
  existence, and in one case its sign.
- **Evidence:** KeywordAgg vs DecodingAgg (monotone in honest-minority size);
  5-model sweep; isolated-view probe (r = 0.9999); refusal synthesis at the floor
- **Synthesis basis:** `aggregation_divergence.md`, `model_dependence.md`,
  `family_dissociation.md`, `alignment_sweep_result.md`
- **Function:** Blocks the generalization the SoK genre invites, with measurement.
- **Not here:** Reproducibility of artifacts (S10).
- **Budget:** ~1600 words
- **Status:** outlined

### S9 — What the reported metric hides

- **Claim:** Accuracy alone cannot distinguish a defense that does nothing from
  one that changes how the system fails, nor a defense that resists an attack
  from one that ignores the channel the attack arrives on.
- **Evidence:** COIECD (inert on accuracy, converts ~⅓ of memory-fallbacks to
  abstention, only under attack); DyPRAG (flat under attack, indistinguishable
  from no-retrieval, channel live but ~1e-4 of the MLP output)
- **Synthesis basis:** `coiecd_result.md`, `dyprag_result.md`
- **Function:** The methodological contribution — names the two controls the
  literature omits and shows each changing a conclusion.
- **Not here:** Recommendations; those are S11.
- **Budget:** ~1500 words
- **Status:** outlined

### S10 — What reproduction costs

- **Claim:** Artifact availability is materially weaker than artifact claims:
  among the five best-cited untested defenses in the cell under study, two name
  empty repositories, two ship code without the weights needed to run it, and
  one is executable.
- **Evidence:** `artifact_availability_cell.md` (API size/refs verification,
  seven unanswered issues over 15 months)
- **Synthesis basis:** `artifact_availability_cell.md`,
  `reconstructability_check.md`
- **Function:** Explains the selection effect in our own results — every
  defense we ran is an inference-time intervention, because those are the only
  self-contained artifacts.
- **Not here:** Naming-and-shaming framing; report the measurement.
- **Budget:** ~800 words
- **Status:** outlined

### S11 — Open problems and what to measure next

- **Claim:** The field's next gains are in reporting conventions, not in new
  defenses: a no-retrieval baseline, an abstention axis, a model control, and
  an artifact-verified flag would each have changed a published conclusion here.
- **Evidence:** RQ7 priorities; the three controls from S9
- **Synthesis basis:** `rq7_open_problems.md`
- **Function:** Converts the findings into checkable practice.
- **Budget:** ~700 words
- **Status:** outlined

### S12 — Limitations

- **Claim:** The corpus coding is LLM-assisted and not yet human-verified; the
  execution campaign covers one cell deeply and others not at all.
- **Evidence:** `CONTRIBUTOR_BRIEF.md`; single-cell depth; model/dataset scope
- **Function:** States the exposure plainly, including that every count derived
  from the coding is provisional pending the verification pass.
- **Budget:** ~900 words
- **Status:** outlined

## Abstract (architecture artifact — revised with the chain)

See `manuscript/abstract.md`.

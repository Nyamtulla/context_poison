# Context Integrity SoK — call for verification contributors

**What this is:** a short brief for colleagues considering joining this project as
co-authors. It states what the study found so far and what the contribution
involves. Target venue: USENIX Security or ACM CCS.

---

## Abstract

Large language model agents fail when their context is corrupted. Two research
communities study this failure and appear not to read each other. The security
community studies context corrupted **on purpose** — prompt injection, RAG
poisoning, memory backdoors — and publishes attacks and defenses. The ML/AI
community studies context that degrades **on its own** — retrieval noise,
knowledge conflict, context rot, lost-in-the-middle — and publishes mechanisms
and fixes. Both are describing the same underlying property: the model cannot
tell which part of its context deserves trust.

This work systematizes both literatures under one taxonomy of
*channel × intent × consequence*, measures whether the two communities cite each
other, and then does something a survey normally cannot: it **executes** the
cross-literature test. Defenses published by the ML/AI community for accidental
context failure are run, using the authors' own released code and weights, against
attacks published by the security community. The campaign reports whether each
defense stops the attack, using a fixed statistical criterion and an
attack-works-first control, rather than restating numbers from the original
papers.

The corpus is 1,158 screened papers drawn from a 25,922-record discovery pool,
each coded on ~31 fields. The present call is to verify that coding.

---

## What the study has found so far

Each point below is a measured result with a write-up and a regeneration script
in the repository.

**On the structure of the field**

- **60.5 % of the taxonomy is empty.** Of 162 cells (9 channels × 3 intents ×
  6 consequences), 98 contain no paper from either literature.
- **The two literatures barely cite each other.** Over the full coded
  population, 11.7 % of security papers cite at least one ML/AI paper on the
  same failure, and 9.1 % of ML/AI papers cite a security paper. These are
  population rates, not sample estimates.
- **Two cells are mirror images, and neither is testable.** Tool-output ×
  goal-hijack has 61 named attacks and one incidental defense, which has no
  code. RAG × reasoning-corruption has 13 defenses with released code and no
  reconstructable attack.

**On how the field evaluates**

- **There is essentially no generalist defense.** Of defenses confirmed tested
  against a named mechanism, 82.7 % were tested against exactly one. Cross-
  mechanism testing tops out at three mechanisms, and only twice in the corpus.
- **55.3 % of named mechanisms (131 of 237) have zero defenses evaluated
  against them.**
- **Scanning the attack papers rather than the defense papers recovers pairs the
  defense-side scan missed**, which indicates the coverage gap is partly a
  reporting-direction artifact and partly real.

**On what happens when the cross-literature test is actually run**

Seventy (defense, attack) combinations have been executed so far across 13
defense implementations, all using released code and weights.

- **Defenses that increase reliance on retrieved context are correct when the
  context is merely stale and dangerous when an attacker owns it.** This is the
  campaign's central design rule, and it has a measured scope condition:
  suppressing the model's prior knowledge hurts only where that prior knowledge
  held the right answer.
- **Two implementations of a single published principle disagree by 29.7
  points** on whether the defense helps or hurts, inside one paper's own
  codebase, with the gap monotone in how small the honest minority of passages
  is.
- **The model, not the defense, is often the dominant variable.** For the same
  defense and the same attack, changing only the base model changes the size of
  the effect, whether the effect exists at all, and in one case its sign.
- **A defense can be inert on the reported metric and active on the failure
  mode.** One decoding-time method leaves accuracy unchanged at every attack
  dose while converting roughly a third of confident wrong answers into
  explicit refusals — invisible to the accuracy column every paper in that
  family reports.
- **A defense can appear immune to an attack because it does not read the
  input the attack arrives on.** One method is perfectly flat under an attack
  that destroys the undefended baseline, and is statistically indistinguishable
  from answering with no retrieval at all. Separating these requires a
  no-retrieval control that the original papers do not report.
- **Artifact availability is weaker than artifact claims.** Among the five
  best-cited untested defenses in the cell under study, two name repositories
  that are empty, two ship code without the trained weights needed to run it,
  and one is executable.

---

## What contributors would do

The corpus of 1,158 papers was coded by an LLM-assisted extraction pass across
~31 fields per paper — taxonomy placement (channel, consequence, intent),
track assignment, intervention point, evidence grade, models and datasets
evaluated, threat model, stated limitations, whether artifacts were released,
and whether the paper cites the other literature. **None of this coding has been
independently verified by a human, and every headline number above depends on
it.**

The task is to take an assigned set of papers, open each PDF, and check the
extracted values against what the paper actually says: is the value correct, is
it absent from the paper, or is it wrong. Disagreements are recorded rather than
silently overwritten, so that inter-rater agreement can be reported in the paper
— reviewers at these venues expect it. No programming is required; the work is
reading and a spreadsheet. Prior exposure to retrieval-augmented generation or
prompt injection helps but is not necessary, and the coding guide defines every
field with examples.

Because full dual-coding of 1,158 papers × ~31 fields is not realistic for a
small team, verification will be **stratified**: 100 % verification of the
fields that drive the headline claims (track, channel, consequence, role, and
the two cross-citation fields), and a random sample of the remaining fields
sufficient to estimate and report an error rate. Contributors who verify a
meaningful share of the corpus and take part in reconciling disagreements are
included as co-authors.

---

## Status and timeline

The discovery, screening, extraction and analysis pipeline is complete, the
seven research questions have written results, and the execution campaign is
running. The measurement infrastructure and the findings above exist and are
reproducible from scripts in the repository.

What is not done is the part this brief asks for. **The verification pass has
not started, and it is on the critical path**: it is the one component that a
top-tier reviewer will probe first, because every count, rate and taxonomy claim
in the paper rests on extraction that no human has checked. The remaining work
is therefore verification, the continuing execution campaign, and the paper
draft itself.

Interested? Reply and you will get a set of papers, the coding guide, and the
spreadsheet.

# Context Integrity SoK — call for verification contributors

**What this is:** a short brief for colleagues considering joining this project as
co-authors. It states what the study found so far and what the contribution
involves. Target venue: USENIX Security or ACM CCS.

---

## The project in plain words

*Read this section first. The technical abstract below says the same thing for
a reviewer.*

AI agents read things: search results, documents, tool outputs, and their own
memory. An agent cannot tell which part of this it can trust. If wrong
information gets in, the agent uses it and gives a wrong answer. Two groups of
researchers study this problem, and they almost never read each other's work.
Security researchers study the case where an attacker plants the wrong
information on purpose. They call it an attack, and they build defenses.
Machine learning researchers study the case where wrong information arrives by
accident. Examples are out of date search results, a document that disagrees
with what the model already knows, and important text buried in the middle of a
long input. They call it a mechanism, and they build fixes. The failure is the
same in both cases. The model reads something it should not trust, and it
cannot tell.

This project puts the two sides together for the first time. We read 984 papers
in full, not just the title and the abstract. We sorted each paper by three
things: which way the bad information gets in, whether someone put it there on
purpose, and what goes wrong as a result. There are nine ways in, three kinds
of intent, and six kinds of damage. That gives us a grid with 162 boxes. Every
attack and every defense goes into a box. About 60% of the boxes are empty,
which means nobody has studied those cases at all.

The split between the two communities is real, and we can measure it. Only
about one paper in ten cites the other side. We found and listed 529 defenses,
and only 14 of them were ever tested against both kinds of problem. The
attention is also uneven. There are about 4.6 defenses for each accidental
problem, but only 1.4 defenses for each named attack. More than half of all
known problems have no defense that was ever tested against them.

We found one more thing that surprised us. We collected 349 cases where
somebody ran a defense against an attack and reported the result. When the
defense authors ran the test, the defense won 193 times out of 194. When the
attack authors ran the same kind of test, the defense won zero times out of 37.
Same defenses, same attacks, opposite answers. The result depends on who ran
the experiment.

Here is the part that matters most, and it is the reason for the experiments.
**We are not building new defenses, and we are not reinventing the wheel.**
Good defenses already exist. The problem is that many of them were never tried
on problems they should be able to handle. This is where the grid earns its
keep. If a defense was built for a problem that comes in through the same
channel and causes the same damage, then it ought to work on the attack version
of that problem too. Nobody has checked. So we looked for pairs of one defense
and one attack that sit in the same box but were never tested together, and we
ran those pairs ourselves.

An example makes this concrete. ParamMute is a fix for knowledge conflict.
Knowledge conflict happens when a retrieved document disagrees with what the
model already knows. Corpus poisoning is an attack where someone writes a fake
document and gets it into the search results. Both come in through retrieval.
Both make the model give a quietly wrong answer. They sit in the same box, so
ParamMute ought to help. No paper has ever run ParamMute against corpus
poisoning. We did. We have now done this for nine published defenses, using the
code and the model weights that the authors released, not our own copies of
their methods.

The main result is that many of these defenses make things worse under a real
attack, and there is a clear reason why. These defenses work by telling the
model to trust the document more and to trust its own memory less. That is good
advice when the document is only out of date. It is bad advice when an attacker
wrote the document, because the defense is telling the model to trust the one
thing the attacker controls. One defense, ParamMute, is a clear case. It helps
by about 9 points when the documents are honest. When the documents are
poisoned, it loses about 13 points more than doing nothing at all.

We are not finished. The experiments continue, and the paper coding needs a
human check, which is the job the verification packets cover. But the shape of
the result is stable. The two communities are studying one problem with two
different vocabularies, and the vocabularies are the reason nobody noticed that
a popular class of fixes becomes a liability the moment an attacker is
involved.

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

The corpus is 984 screened papers drawn from a 25,922-record discovery pool,
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
  same failure, and 9.3 % of ML/AI papers cite a security paper. These are
  population rates, not sample estimates.
- **Two cells are mirror images, and neither is testable.** Tool-output ×
  goal-hijack has 61 named attacks and one incidental defense, which has no
  code. RAG × reasoning-corruption has 13 defenses with released code and no
  reconstructable attack.

**On how the field evaluates**

- **There is essentially no generalist defense.** Of defenses confirmed tested
  against a named mechanism, 82.7 % were tested against exactly one. Cross-
  mechanism testing tops out at three mechanisms, and only twice in the corpus.
- **54.9 % of named mechanisms (129 of 235) have zero defenses evaluated
  against them.**
- **Scanning the attack papers rather than the defense papers recovers pairs the
  defense-side scan missed**, which indicates the coverage gap is partly a
  reporting-direction artifact and partly real.

**On what happens when the cross-literature test is actually run**

Eighty-one (defense, attack) combinations have been executed so far across 18
defense implementations (an eleventh retrieval defense, SHIFT, has a control
run but no transfer run), all using released code and weights: 25 pairs in the
retrieval cell and 56 in the agent cell, 156,308 scored episodes in total.
Seventeen of the 19 retrieval-cell pairs, counted at registry-name level, are
absent from the 349 pairs the published literature reports. They were selected
because the defense and the attack sit in the same taxonomy cell, so the
defense ought to apply, and nobody had tested it.

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

The corpus of 984 papers was coded by an LLM-assisted extraction pass across
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

Because full dual-coding of 984 papers × ~31 fields is not realistic for a
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

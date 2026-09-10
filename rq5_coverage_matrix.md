# RQ5 — Pollution Mechanism × Defense Coverage Matrix

Generated 2026-08-17, on the finalized RQ3 registry (183 mechanisms) and
RQ4 registry (479 defenses). Regenerate if either registry changes.

**RQ5 (as stated in the project plan, Section 1):** Cross-referencing the
RQ3 and RQ4 registries: which defenses have actually been evaluated against
which pollution mechanisms — not merely claimed to address them? Do any
defenses generalize across multiple distinct mechanisms, are there
mechanisms with no defense evaluated against them, and are there evaluation
silos?

## Headline result

**The field barely cross-tests at all — the matrix is far sparser than the
plan anticipated, and the shape of the sparsity is itself the finding.**

- **170 of 479 defenses (35.5%)** were confirmed tested against at least one
  named registry mechanism; the rest (64.5%) either weren't evaluated against
  anything the registry recognizes as a distinct named technique, or weren't
  evaluated at all.
- **85 of 182 mechanisms (46.7%)** have at least one defense tested against
  them; **97 (53.3%) have zero.** As originally published this read 67 of 183
  (36.6%) with 116 uncovered; the difference is one retracted duplicate plus
  41 pairs recovered by two later scans, the larger of which read *attack*
  papers rather than defense papers — see "Reading the corpus in the other
  direction" below, which is a finding in its own right.
- **Among the 170 matched defenses, 150 (88.2%) were tested against exactly
  one mechanism; only 20 (11.8%) were tested against two; none were tested
  against three or more.** The plan's original hypothesis — that the
  interesting finding would be a spectrum from "generalist defenses" (tested
  broadly) to "evaluation silos" (narrow, isolated testing) — undersells
  what's actually here: **there is essentially no generalist-defense
  category to speak of at this granularity.** Cross-mechanism testing tops
  out at 2, not "many." The field's default mode is narrow, single-mechanism
  validation, not incremental silo-vs-generalist variation.
- Raw matrix density (231 confirmed pairs / 87,178 possible mechanism×defense
  cells = 0.22%) is not a meaningful number on its own — most cells aren't
  applicable at all (a memory-channel mechanism has no reason to be tested
  against a supply-chain-channel defense) — the two percentages above
  (35.5% of defenses, 36.6% of mechanisms) are the honest coverage measures.

## Where the testing effort actually concentrates

| Mechanism | Distinct defenses tested against it |
|---|---:|
| Indirect Prompt Injection (IPI) | 76 |
| lost in the middle | 13 |
| context rot (agentic/long-horizon search) | 9 |
| PoisonedRAG | 7 |
| distraction by irrelevant context | 7 |
| distraction by irrelevant context (graded by semantic relatedness) | 6 |
| Cross-Session Stored Prompt Injection (XSPI) | 3 |
| observation over-ingestion | 3 |

**"Indirect Prompt Injection (IPI)" alone accounts for 76 of 190 total
matched pairs (40%).** The field's defense-testing effort is overwhelmingly
concentrated on one generic, umbrella-level mechanism rather than
distributed across the 183 more specific named techniques the corpus
actually contains — most of the 128 remaining Track A attack techniques and
53 remaining Track B mechanisms in the registry that DO have any coverage at
all get only 1-2 defenses ever tested against them, and the 116 with zero
coverage never get tested against anything.

## Reframing "evaluation silos"

The plan's original methodology (Section 7, step 3) looked for "two
mechanisms published close together in time or on the same channel, where
the defense proposed for one was never run against the other" as a specific
finding to surface. Given that 88% of matched defenses test against exactly
one mechanism, **silos are not a specific pattern to find — they are the
default state of nearly the entire matched population.** The more useful
question this raises for the paper's discussion section is not "are there
silos" (yes, almost everywhere) but "why does testing concentrate so hard on
IPI specifically, and what would it take to get a defense paper to test
against even one mechanism from the *other* track" — which is exactly what
RQ6's case studies are positioned to investigate next.

## What this means for RQ6

RQ4 already showed 97% of defenses were validated against only one *threat
model* (adversarial or incidental) in their own paper. RQ5 sharpens this:
even within a single threat model, 88% of defenses that test against
anything from the registry test against only one specific named mechanism.
Combined, this means **the vast majority of proposed defenses in this
corpus have never been tested against anything but the one narrow scenario
their own paper was written to solve** — not a different attack, not an
incidental version of the same consequence, not even a second mechanism on
the same track. This is the strongest possible framing for RQ6: the
candidate pool isn't a small, curated set of edge cases, it's nearly the
entire defense registry.

Per the plan's Section 8 selection method: from the defenses validated
against only one threat model (RQ4) whose channel+consequence also has
meaningful volume on the *other* track (cross-referenced against RQ1's
cube), pick one candidate per intervention point (ingestion/reasoning/
execution) — prioritizing the highest-cited, best-evidenced defense in each
untested direction — as the actual case studies. That selection step has not
been run yet; this document establishes the pool it will draw from.

## Methodology

Extraction delegated to 4 parallel subagents, each given a slice of the 479
defenses plus the *complete* 183-mechanism registry as a lookup reference,
instructed to determine — from each defense paper's own `baselines_compared`/
`key_result`/`technical_summary` text — which registry mechanisms it was
*actually evaluated against* (fuzzy/semantic matching against differently-
worded descriptions of the same mechanism, not exact string search), with
explicit instruction to favor false negatives over false positives given
precision matters more than recall for this matrix. All 4 batches were
interrupted once by an account-level API spend-limit error and resumed from
partial (incrementally-written) progress rather than restarted from zero.

A post-merge integrity check caught 3 of 191 raw matched pairs (1.6%) using
mechanism names that didn't exactly match the registry (a CSV field-quoting
artifact from upstream data, not an agent judgment error) — 2 were
recoverable via exact-prefix matching against the registry (both were
unambiguous, 100%-confidence truncations) and corrected; 1 could not be
confidently resolved (best fuzzy match was only 62% similarity) and was
dropped rather than guessed. Final count: 190 confirmed pairs.

## Known limitations

- Same entity-resolution risk flagged in the plan's Section 12 for RQ3-RQ5:
  matching depends on the extracting agent correctly recognizing when a
  defense paper's differently-worded description refers to the same
  registry mechanism. Given the "favor false negatives" instruction, the
  35.5%/36.6% coverage figures are more likely to *undercount* true coverage
  than overcount it — the real coverage may be somewhat higher than reported
  here, but the qualitative finding (heavy concentration on IPI, near-total
  absence of cross-mechanism testing, large uncovered majority) is unlikely
  to be an artifact of this conservative bias, since undercounting biases
  toward finding *less* concentration and *more* gaps than actually exist,
  not the reverse.
- `baselines_compared` and related fields were mined as already-extracted
  text (from the earlier full-text pass), not re-read from source PDFs for
  this specific task — inherits whatever imprecision exists in those
  summaries, same caveat as RQ3 and RQ4.
- The matrix currently only records *whether* a mechanism was tested, not
  the *outcome* (did the defense actually succeed against it) — RQ6's case
  studies will need to establish outcome for their specific selected pairs,
  since a "tested" cell here doesn't distinguish a defense that worked from
  one that was tested and failed.

## Addendum (2026-09-07) — robustness of the gap, and two corrections

This section is **methodology, not findings**. It records an audit of whether
the coverage gap above survives scrutiny, plus two corrections to the numbers
originally published. Nothing here is evidence about the field; it is evidence
about our own measurement, and it is reported so the headline figures can be
trusted rather than to add a result.

### Two corrections to the published numbers

1. **Recovery pass (+4 pairs).** RQ5 matched defenses to mechanisms by reading
   each defense paper's own `baselines_compared` / `key_result` /
   `technical_summary`. An exhaustive re-check over the never-defended
   mechanisms — citation-based candidates (147) plus a full-text scan with
   bibliographies stripped (35) — found **4** pairs the original pass had
   missed: RETA vs. RL-Hammer, PISmith and AutoInject, and SnapGuard vs.
   WebInject. These are extraction misses being repaired.
2. **Duplicate retraction (−1 mechanism).** Rows 51/57/59 are all arXiv
   2505.05849, one paper renamed across versions (AgentFuzzer → AgentVigil).
   Row 59 was still `Include` and had contributed a *second* RQ3 entry for the
   same technique. Retracting it moves mechanisms 183 → 182, and because the
   phantom sat in the uncovered list, uncovered moves 116 → 111.

**Net effect: 63.4% → 61.0% of mechanisms never defended.** That movement is
entirely accounted for by the two corrections above. It is *not* a change in
what the literature does, and it should not be reported as one.

As-published figures remain exactly reproducible:
`registry_source.load_all(include_supplementary=False, include_corrections=False)`
returns 183 mechanisms / 116 uncovered / 190 pairs.

### Does the gap survive the audit?

Yes, and that is the useful part. Of 147 citation-derived candidates, only 3
survived the "actually evaluated" bar; of 35 full-text candidates, 4. **The
overwhelming majority of candidates mention the mechanism only in the
bibliography or a single related-work sentence** — defense papers cite attack
papers as related work, not as evaluation targets.

That is real, but it does **not** license the conclusion we first drew from it.
This audit searched defense papers, which is the same direction RQ5 searched,
so it could only ever test whether we read those papers carefully enough — not
whether we were reading the right papers. The next section runs the scan the
other way and finds that we were not.

Three method notes worth carrying into threats to validity:

- **Citation matching is complementary, not superior.** As a control it
  re-found only **19 of 67 (28%)** known-covered mechanisms, because defenses
  routinely evaluate an attack through a bundled benchmark (AgentDojo,
  InjecAgent) without citing the original attack paper. It also *missed*
  RETA ← AutoInject, which the full-text scan caught. Neither signal dominates.
- **Generic-phrase mechanism names produce false positives.** Three defenses
  (CodeDelegator, Free()LM, AegisAgent) use "context pollution" to mean
  something other than the registry's `Context Pollution (evolutionary search
  history bias)`; CodeDelegator's paper is literally *titled* "Mitigating
  Context Pollution." A registry with common-noun entries is an
  entity-resolution hazard.
- **A permanent floor.** 20 of the uncovered mechanisms are `UNNAMED:` entries
  — descriptive labels assigned during extraction, never terms the literature
  uses — so no name-based method can ever recover them.

### PDF availability is a second, separable cause

Part of the unmatched-defense population is unmatchable by construction: for a
defense paper that never received the full-text extraction pass, the fields
RQ5 reads are empty. Measured after the extraction backfill:

| Defense papers | Matched to ≥1 mechanism |
|---|---:|
| With full-text extraction | 37.2% |
| Without | 4.5% |

Report **both denominators**: 35.7% of *all* defenses have a confirmed match,
but 37.2% of those *eligible* for matching do. See `rescreening_log.md`
Addendum 3 for the full analysis.

## Reading the corpus in the other direction (2026-09-09)

This section **is** a finding about the literature, not about our measurement.

RQ5 and the audit above both established coverage by reading defense papers and
looking for mechanism names. That direction has a blind spot with a definite
shape: **a defense paper cannot report losing to an attack that did not exist
when it was written.** The moment a defense is beaten, the evidence appears in
the *attacking* paper, and no amount of care applied to the defense side of the
corpus will surface it.

So we ran the scan the other way — every mechanism's source paper searched for
every named defense in the RQ4 registry
(`scripts/reverse_scan_attack_papers.py`). Two passes: the first over the 111
then-uncovered mechanisms, the second over all 182, because the blind spot
applies to covered mechanisms exactly as much as to uncovered ones. 171 raw
candidates, each adjudicated by reading the surrounding text at the same
precision-first bar (the paper must actually run the defense and report a
result). **37 confirmed pairs**, recorded with their quoted evidence in
`data/registries/attack_paper_evaluations.json`.

### What it changes

| | as published | after both recovery directions |
|---|---|---|
| mechanisms with ≥1 defense tested | 67 / 183 (36.6%) | **85 / 182 (46.7%)** |
| mechanisms never defended | 116 | **97** |
| confirmed pairs | 190 | **231** |

Fourteen mechanisms move from uncovered to covered. But the more important half
of the result is on the mechanisms that were *already* covered: 16 further
evaluations that RQ5 structurally could not see, and their verdicts run
overwhelmingly one way.

### The verdict pattern

**24 of the 37 recovered pairs record the defense failing, degraded, evaded or
broken, and every one of those 24 is on a Security-track mechanism.** The
remaining 13 are recorded as `evaluated` with no directional verdict: 4 ML/AI
context-management systems compared as baselines (where the framing is
comparison, not attack) and 9 Security-track pairs where the attack paper runs
the defense inside a benchmark matrix without singling out a per-defense
result. So among Security-track pairs the split is 24 negative to 9 neutral,
and **positive verdicts are absent entirely** — not one recovered pair reports
a defense holding.

That is near-tautological — an attack paper evaluates a defense in order to
beat it — and that is exactly why the direction matters. **The
literature's record of defenses succeeding lives in defense papers; its record
of the same defenses failing lives in attack papers; and a coverage matrix
built from one side reports only the successes.**

The clearest case is DataSentinel, which RQ6 reconstructed and rated *full
generalization*:

| attack | published against DataSentinel |
|---|---|
| DataFlip | detection to **0%** (max 24%) |
| ObliInjection | **FNR 79.6%** — misses four in five contaminated segments |
| ToolHijacker | detects some, "**miss the majority**" |
| PISmith | on the low-robustness arm of the utility–robustness frontier |

All four postdate DataSentinel. RQ6's own reconstruction — a clean pass against
the CombineAttacker injection from DataSentinel's evaluation suite — is
unaffected and stands; what changes is what it licenses. It shows the defense
holds against the attacks that existed when it was written. See
`rq6_case_studies.md`, where the verdict is now qualified accordingly.

### Method limits, stated plainly

- **The RQ4 registry bounds recall.** Only defenses whose own paper is in the
  corpus have a name to search for. The Relinking paper evaluates eleven
  defenses; four of them (Llama Prompt Guard 2, ShieldGemma, PromptLocate,
  SecAlign) are not RQ4 entries, so those pairs are invisible to this scan
  and are *not* counted above.
- **Five mechanism papers have no retrievable full text**, so their attack
  side was never read.
- **The evaluation-language filter ranks, it does not gate.** Two of the 37
  (Relinking × AttnTrace, Relinking × CaMeL) carried no hint — the paper says
  "Evaluation protocol" and "Defense Placement", which the regex does not
  cover. They were caught by hand-reviewing high-mention candidates without a
  hint. Candidates below that review threshold may still hide real pairs.
- **Backronyms are an entity-resolution hazard from this side too.** SHIFT,
  TRACE, DRIFT, ITEM, PARSE, ACC, END, ARC, TAG and TOA all matched ordinary
  words, metric abbreviations, dataset names or PDF-extraction artifacts; 85
  of the first run's 133 candidates were this one failure mode. Acronyms are
  now matched case-sensitively and URL-internal matches suppressed.
- **One pass-1 rejection was overturned.** SkillJect × ClawGuard was called
  related-work-only on too short an excerpt; the fuller passage reports
  measured scanner accuracies. Both the original call and the reversal are
  recorded in the registry file.

### Consequence for RQ7

RQ7 currently frames the problem as invention outpacing evaluation. That
survives, but it is now too generous to the field in one respect and too harsh
in another. Too harsh: defenses are evaluated against new attacks more often
than the defense-side scan could show. Too generous: **when that evaluation
happens, the defense usually loses, and the result is published somewhere the
defense literature does not cite.** The gap is not only that defenses go
untested — it is that they are tested, fail, and the failure never propagates
back into how the defense is described.

## The outcome table: what was reported, and by whom (2026-09-10)

RQ5's extraction recorded whether a (defense, mechanism) pair was *tested*. It
never recorded what happened, and the write-up flagged that at the time: a
"tested" cell does not distinguish a defense that worked from one that was
tested and failed.

Filling that gap naively produces a ledger that is worse than no ledger,
because the two halves of the corpus disagree by construction:

- a **defense paper** reports a pair because its defense won;
- an **attack paper** reports the same pair because the defense lost.

Extracting outcomes from the 194 defense-paper pairs yields 193 claimed wins.
Extracting them from the 37 attack-paper pairs yields 24 reported losses and
**zero** wins. Neither number measures how often defenses work. Averaging them
would measure nothing at all.

`data/registries/pair_outcomes.json` (built by `scripts/build_pair_outcomes.py`)
therefore records one row per pair with `reported_by` as the load-bearing
field, and never collapses the two.

### What the table can support

**Effect sizes, which travel regardless of who reported them.** Reported
numbers are mined per pair — ASR reductions, detection rates, TPR/FPR — for
137 of the 194 defense-paper pairs and 8 of the 37 attack-paper pairs, so pairs
can be compared on magnitude rather than on a binary. CommandSans "reduces ASR
from 46.4% to 4.6%" and DataSentinel's 79.6% FNR under ObliInjection are
commensurable in a way that "tested" and "tested" are not.

**The disagreement, where both sides exist.** 15 of the 177 defenses in the
matrix have evidence from both a defense paper and a later attack paper.
**11 of those 15 lose in the attack paper while their own paper claims a win.**

| defense | wins claimed by its own paper | later attacks that ran it | lost |
|---|---:|---:|---:|
| DataSentinel | 1 | 4 | **4** |
| MELON | 1 | 4 | 3 |
| DataFilter | 1 | 3 | 3 |
| Progent | 1 | 3 | 2 |
| PromptArmor | 2 | 2 | 2 |
| CaMeL | 1 | 4 | 1 |

This is not evidence that the defense papers are wrong. Both results can hold,
against different attacks, at different times — which is exactly the point.
**A single "was this defended" cell cannot carry the answer, and which half of
the corpus you read decides what you conclude.**

### What the table deliberately does not do

An earlier version of this script tried to classify the defense papers'
verdicts with a win/loss lexicon. On inspection it was wrong often enough to be
worse than useless: it fired on language describing the *attack* ("degrade",
"bypass") and read those as the defense losing, and its text window was usually
the paper's title block, because for a generic mechanism name like "Indirect
Prompt Injection (IPI)" the first occurrence in a defense paper's body IS the
title. Those numbers were discarded, not published.

What replaced it is the structural statement rather than a measurement: every
defense-paper row is `defense_wins_claimed`, which says where the claim comes
from, not that we verified it. Where a paper's own limitations section names
the mechanism (9 pairs), the text is attached for the reader to weigh — a flag,
not a verdict, since some of those mentions are pointed (TriShieldRAG's "~13%
residual attack success rate ... not a complete elimination") and others are
incidental.

**The honest independent verdict remains the reconstruction standard**: run the
released code and measure. That is what RQ6 did for 9 pairs. Everything in this
table is a report of someone else's result, labelled with whose.

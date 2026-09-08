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
- **67 of 183 mechanisms (36.6%)** have at least one defense tested against
  them; **116 (63.4%) have zero** — a coverage gap almost identical in size
  to the empty-cell rate found in RQ1 (63.6%), a striking (and likely
  not coincidental) parallel between "has this combination been studied"
  and "has this specific mechanism ever been defended against."
- **Among the 170 matched defenses, 150 (88.2%) were tested against exactly
  one mechanism; only 20 (11.8%) were tested against two; none were tested
  against three or more.** The plan's original hypothesis — that the
  interesting finding would be a spectrum from "generalist defenses" (tested
  broadly) to "evaluation silos" (narrow, isolated testing) — undersells
  what's actually here: **there is essentially no generalist-defense
  category to speak of at this granularity.** Cross-mechanism testing tops
  out at 2, not "many." The field's default mode is narrow, single-mechanism
  validation, not incremental silo-vs-generalist variation.
- Raw matrix density (190 confirmed pairs / 87,657 possible mechanism×defense
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
papers as related work, not as evaluation targets. So the gap is a property of
the literature, not an artifact of our extraction being too strict.

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

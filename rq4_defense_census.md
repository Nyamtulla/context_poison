# RQ4 — Defense Census

Regenerated 2026-09-22, on the 1,026-paper working corpus (post 2026-09-11
screening fix, the screening-delta extraction, and the abstract-based duplicate
corrections in `rescreening_log.md` Addendum 4). Regenerate if the corpus or
registry changes.

**RQ4 (as stated in the project plan, Section 1):** How many distinct
defense/mitigation techniques have been proposed — across both tracks — as
solutions to the pollution mechanisms cataloged in RQ3, and against which
threat model (adversarial, incidental, or both) has each actually been
validated in its own paper?

## Headline result

**534 distinct defenses** identified across the corpus:
- **263 (49.3%) from Track A** (Security) papers.
- **266 (49.8%) from Track B** (ML/AI) papers.
- **5 (0.9%) from "Both"-track** papers.

**The load-bearing number for RQ5/RQ6: of the 534 defenses, only 15 (2.8%)
were validated by their own paper against both threat models.** 263 (49.3%)
were validated against adversarial scenarios only; 253 (47.4%) against
incidental scenarios only; 3 report no empirical validation at all. This
means **97% of proposed defenses have a completely untested cross-track
generalization question hanging over them** — this is precisely the
candidate pool RQ6's case studies draw from (Section 8 of the plan).

### What the screening fix changed

Up from **479** defenses before the 2026-09-11 screening fix; the delta added
**55**. The recovered cohort is the field's foundational defense work — StruQ,
SecAlign, Spotlighting, the Instruction Hierarchy, Attention Tracker,
PromptShield, PIGuard, DefensiveTokens, f-secure/IFC, PromptLocate — which had
been absent purely because those papers predate agent-era vocabulary.

Two things are worth stating precisely, because they cut in opposite directions:

1. **The track balance evened out**, 44/55 Track A/B → 49/50. The original
   census made the defense literature look ML/AI-leaning; a meaningful part of
   that was the missing security-side foundations, not a real asymmetry.
2. **The 97% single-threat-model figure did not move at all** (2.9% → 2.8%
   validated against both). Adding 55 defenses, including the most-cited and
   most-benchmarked-against defenses in the field, changed it by one tenth of a
   percentage point. This is the strongest robustness evidence the project has
   for its central claim: cross-track validation is not something the
   foundational work was doing and we had simply failed to capture. It is
   genuinely not being done.

## By validated_against

| Validated against | Count | Share |
|---|---:|---:|
| adversarial only | 263 | 49.3% |
| incidental only | 253 | 47.4% |
| both | 15 | 2.8% |
| no evaluation reported | 3 | 0.6% |

## By defense intervention point

| Intervention point | Defenses |
|---|---:|
| reasoning | 205 |
| ingestion | 155 |
| none (see note) | 100 |
| execution | 74 |

Note: 100 registry entries carry `defense_intervention_point=none` despite
being defense-introducing papers — this reflects the *paper's* coded
intervention point (from the Week-2 batch classification, Section 3), which
for some defenses (e.g. an architectural/design-only proposal with no
runtime intervention point, or a detection-only paper whose "defense" is
flagging rather than intervening) is legitimately "none." Worth a second
look during the paper-writing pass to confirm this isn't a coding gap.

## By channel

| Channel | Defenses |
|---|---:|
| tool-output | 175 |
| direct-input | 127 |
| RAG | 87 |
| memory | 73 |
| multi-agent | 36 |
| cross-modal | 17 |
| tool-metadata | 11 |
| skill | 6 |
| supply-chain | 2 |

Cross-referencing against RQ1's Channel × Defense-intervention-point matrix:
supply-chain and skill remain the least-defended channels by both metrics
(paper-level count in RQ1, and now distinct-technique count here) —
consistent, not contradictory, findings from two different angles on the
same data.

## Registry construction notes

- **46 of 479 (9.6%) are unnamed** (paper didn't coin its own term).
- Entity resolution: exact-name matching found zero shared names; fuzzy
  matching (threshold 75) surfaced 5 candidate near-duplicate pairs, all
  confirmed as distinct techniques with a coincidentally shared naming
  pattern (e.g. "IPIGuard" vs. "PIIGuard" — different defenses, both using
  the common "-Guard" suffix convention). No merges were needed for RQ4
  (unlike RQ3, where one fuzzy match did turn out to be a genuine duplicate
  paper).
- `validated_against` is the one field in this census that required real
  judgment beyond "does this paper introduce a technique" — each extracting
  subagent was instructed to read the paper's own evaluation section
  (via `threat_model`/`key_result`) and determine what was *actually tested*,
  not just infer it from which track the paper is filed under. This is the
  field RQ5 and RQ6 depend on most, so it's the one most worth spot-checking
  before treating the 2.9% "both" figure as final — see Known limitations.

## Methodology

Extraction delegated to 4 parallel subagents, each covering ~223 papers
spanning both tracks (unlike RQ3, which split cleanly by track, RQ4's
subagents each processed a mixed-track slice since a defense's threat-model
validation needed to be judged the same way regardless of which track filed
the paper). Same include/exclude criteria structure as RQ3, plus the added
`validated_against` judgment. One batch (batch 3) required a retry after an
account-level API spend-limit interruption lost its first attempt's
in-memory progress (140 of 223 papers had been processed with no output
written) — the retry was instructed to write incrementally rather than only
at the end, to make future interruptions non-destructive.

## Known limitations

- Same general limitations as RQ3 (built from already-extracted summaries,
  judgment-call-dependent boundary, single-threshold fuzzy dedup).
- **`validated_against` is inferred from the paper's `threat_model`/
  `key_result` text by an LLM subagent, not verified against the actual
  evaluation tables.** Several low-confidence flags from the extracting
  agents specifically call this out (e.g. row 203/ShadowPlay's "both" call
  was made from an abstract-only paper with no other extracted fields). This
  is the single highest-leverage field to spot-check before RQ6 selects
  case studies from it, given how much weight the "97% single-threat-model"
  finding will carry in the paper.
- 15+ papers across the RQ4 batches had entirely empty full-text extraction
  fields (flagged explicitly by one batch's report) — these were judged from
  title/abstract alone, a known-weaker signal than the full-text-informed
  judgments used elsewhere in this project.

# RQ3 — Context Pollution Census

Regenerated 2026-09-22, on the 1,026-paper working corpus (post 2026-09-11
screening fix, the screening-delta extraction, and the abstract-based duplicate
corrections in `rescreening_log.md` Addendum 4). Regenerate if the corpus or
registry changes.

**RQ3 (as stated in the project plan, Section 1):** How many distinct,
*named* mechanisms by which an LLM agent's context can become poisoned or
polluted have been identified in the literature — whether introduced
deliberately as an attack technique (Track A) or arising incidentally as a
degradation mechanism (Track B) — and how are they distributed across
channels and consequences?

## Headline result

**223 distinct pollution mechanisms** identified across the corpus:
- **168 (75.3%) are adversarial (Track A)** — named attack techniques
  (Indirect Prompt Injection, PoisonedRAG, AgentPoison, ToolHijacker, the
  Combined Attack, and 163 others).
- **55 (24.7%) are incidental (Track B)** — named degradation mechanisms
  (lost-in-the-middle, context rot, knowledge conflict, distraction by
  irrelevant context, and 51 others).

337 of the 1,026 included papers contributed **no** registry entry at all —
they are benchmarks, defenses, surveys, or measurement-only papers applying an
existing named mechanism rather than characterizing a new one.

### What changed, and why it matters

This is up from **183** mechanisms (129 Track A / 54 Track B) before the
2026-09-11 screening fix. The delta added **41 mechanisms, 40 of them Track A** —
and the composition of that delta is the finding, not the count.

The recovered papers are the field's *pre-agent-era* foundations: work on
LLM-integrated **applications** that predates "agent" vocabulary and was
therefore filtered out by the original signal-term list
(`screening_gap_analysis.md`). They skew hard toward `direct-input`: 23 of the
41 new mechanisms, against 5 for `tool-output`.

That closes what had looked like a decisive gap between the two channels:

| Channel | before | after |
|---|---:|---:|
| tool-output | 62 (33.9%) | 66 (29.6%) |
| direct-input | 43 (23.5%) | **66 (29.6%)** |

They are now **exactly tied**. The earlier reading — "tool-output dominates,
mostly Track A indirect-injection variants" — **overstated a gap that our own
screening had manufactured**. The corpus had been selected for agent-era
vocabulary, and agent-era context poisoning is disproportionately indirect
(tool-output); the direct-input literature that founded the field was sitting in
`needs_review` the whole time. Stated plainly: the field names just as many
distinct ways to poison a model through what the *user* sends it as through what
its *tools* return, and the first version of this census could not see that.

The Track A/B ratio also moved, 70/30 → 75/25, for the same reason — the
recovered cohort is almost entirely adversarial (40 of 41).

## By channel

| Channel | Mechanisms | Share |
|---|---:|---:|
| tool-output | 66 | 29.6% |
| direct-input | 66 | 29.6% |
| RAG | 28 | 12.6% |
| cross-modal | 18 | 8.1% |
| memory | 14 | 6.3% |
| tool-metadata | 12 | 5.4% |
| multi-agent | 9 | 4.0% |
| supply-chain | 6 | 2.7% |
| skill | 4 | 1.8% |

Note this counts *distinct named mechanisms per channel*, not papers per channel
(that is RQ1's metric). A channel can carry many papers but few distinct
techniques — a mature, incrementally-studied channel — or few papers but many
distinct techniques, where each new paper stakes out new ground.

## By consequence

| Consequence | Mechanisms | Share |
|---|---:|---:|
| goal-hijack | 126 | 56.5% |
| reasoning-corruption | 46 | 20.6% |
| silent-corruption | 21 | 9.4% |
| persistence-backdoor | 14 | 6.3% |
| data-exfiltration | 13 | 5.8% |
| resource-abuse | 3 | 1.3% |

Goal-hijack still accounts for over half the registry (126/223, 56.5%) — the
single most "invented" consequence, in the sense of attracting the most distinct
named techniques. The screening fix left this finding essentially unchanged
(it was 54.6% before), which is a useful robustness check: the concentration is
a property of the field, not of which papers we happened to include.

## Registry construction notes

- **46 of 223 (20.6%) are explicit extensions** of a prior named mechanism
  (tagged `is_extension_of`) — e.g. Approximate Greedy Gradient Descent as an
  improved GCG/HotFlip search. Kept as separate entries with lineage noted
  rather than merged, a judgment favoring granularity, since RQ5's coverage
  matrix benefits from distinguishing "was the *original* technique tested"
  from "was this *specific variant* tested."
- **41 of 223 (18.4%) are unnamed** — the introducing paper coined no term, so a
  short descriptive label was assigned during extraction (tagged `UNNAMED:`).
  Real, distinct mechanisms without an established citable name yet.
- **Eight duplicate paper entries have now been found and corrected** across the
  project's lifetime (literal duplicate corpus rows, not registry
  entity-resolution). Five of the eight are preprint/publication renames, which
  title similarity scores in the 50s-70s and cannot catch. Three were found in
  this rebuild alone by the new identifier pass
  (`scripts/dedupe_by_identifier.py`), including row 1125 —
  *"More than you've asked for"* is not Greshake et al.'s companion paper but
  **the same paper** as row 2 under its preprint title (both arXiv 2302.12173) —
  and rows 1011/1126, which had registered the Liu et al. Combined Attack twice.
  Retracting the latter is why this registry is 223 rather than 224. See
  `rescreening_log.md` Addendum 4.

## Methodology

The original pass delegated extraction to 4 parallel subagents (2 for the 466
Track A papers, 2 for the 404 Track B papers), each judging per-paper whether a
paper introduces a genuinely new, named mechanism versus applying an existing
one, with explicit include/exclude criteria and confidence self-flagging.

The 2026-09-21 delta pass extended this to the 150 recovered papers using the
same criteria, recorded in `data/registries/raw/DELTA_EXTRACTION_SPEC.md`, with
the instruction to favor false negatives over false positives. Deduplication
then ran as before: exact-name matching (1 merge, above) followed by fuzzy
matching at threshold 75, which surfaced 4 candidate near-duplicate name pairs.
All 4 were confirmed distinct on inspection — including `Indirect Prompt
Injection (IPI)` vs. `Image-based Prompt Injection (IPI)`, which share an
acronym but are different techniques on different channels (tool-output vs.
cross-modal).

## Known limitations

- Registry construction used extracted `technical_summary`/`key_result` fields
  rather than a fresh full-text read for this specific task, and inherits
  whatever imprecision exists in those summaries.
- The include/exclude bar ("does this paper's core contribution deserve a
  distinct, citable name") is a judgment call, especially for the 41 unnamed and
  46 extension entries. A different coder might draw the line a few entries
  either way. Treat as directionally reliable, not precise ground truth.
- The delta pass was coded by a different model than the original pass
  (Sonnet rather than Opus, after a session limit), against a written spec
  derived from the original criteria. Its self-flagged low-confidence calls and
  scope verdicts were reviewed; **no inter-coder reliability check against the
  original pass was run**, so the two halves of the registry are not verified to
  share a calibration. One systematic drift was caught and corrected this way —
  the delta pass initially graded `evidence_grade` on evaluation quality rather
  than publication venue, which the corpus convention does not do (see
  `rescreening_log.md` Addendum 4) — which is reason to treat the rest of its
  calibration as plausible rather than established.
- Fuzzy-match deduplication checks registry *names* only. Two mechanisms with
  very differently-worded names could still be the same phenomenon; name
  similarity alone will not catch it.
- **13 recovered papers were never retrieved** (paywalled or unavailable) and are
  therefore absent from this census. The highest-cited is GUARDIAN at 26
  citations, which proposes a named defense and would plausibly have been an RQ4
  entry. Full list with DOIs in `MANUAL_DOWNLOADS_screening_delta.md`.

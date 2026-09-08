# Corpus Re-Screening Log — full-text correction pass

Performed 2026-08-17, triggered by RQ1 taxonomy work. Documents a
post-hoc correction to screening decisions made possible by the full-text
extraction pass (Section 3 of the project plan), which the original
abstract-only auto-screen did not have access to.

## What was found

While building RQ1's channel × intent × consequence cube, one cell
(`channel=direct-input, track=ML/AI, consequence=reasoning-corruption`) held
212 of 1,008 papers (21% of the corpus) — by far the largest cell. A 15-paper
random spot-check found roughly half were genuinely off-topic: generic
LLM-agent capability papers (robotics task planning, RL training algorithms,
narrative-agent benchmarks) that used "long-horizon" or "agent" language
without studying context contamination or degradation. Tracing provenance
showed 90 of the 212 came directly from a single overbroad search-cluster
query ("long-horizon agent reliability"), and the pattern was not confined
to that one query or that one cube cell.

## Method

1. Flagged the highest-risk profile corpus-wide: `channel=direct-input AND
   defense_intervention_point=none` (the "default bucket" classification a
   generic capability paper falls into when it doesn't clearly match a more
   specific channel or propose any defense) — 179 papers (142 track=ML/AI,
   37 track=Security), not limited to the one query cluster.
2. Re-applied the original inclusion/exclusion criteria
   (`config.yaml`, `screening:` section) to each of the 179, using the
   full-text `technical_summary`/`key_result`/`threat_model` fields already
   extracted — no new PDF reads needed.
   - **Include**: addresses LLM agents with tool use/RAG/memory/multi-step
     autonomy AND presents an attack, defense, benchmark, or empirical
     measurement of context contamination or context-length/quality
     degradation.
   - **Exclude**: generic agent capability/planning/benchmark papers where
     context degradation is not the actual subject; pure jailbreak papers
     with no agentic component; training-time-only data poisoning; non-LLM
     systems.
3. Initial pass delegated to a subagent (general-purpose) for the bulk
   classification, to keep this from consuming the main session's context on
   179 individual paper reads. It returned 56 include / 123 exclude plus its
   15 least-confident exclude calls for review.
4. Manually re-read the 15 borderline cases against the actual
   `technical_summary` text (not the agent's one-line paraphrase) and
   overrode 5: Agent-BRACE, StructAgent, Environment Maps, STRACE, and
   FinPersona-Bench were flipped from exclude to include — each turned out to
   centrally propose a genuine context-management/degradation-measurement
   contribution once read directly, not just mention "context" in passing.
5. Applied the adjudicated list (60 include / 119 exclude) to both the
   SQLite DB (`screen_human = 'auto_exclude'`, preserving the existing
   human-override pattern used elsewhere in this project) and the Excel
   `screening` column.
6. Caught and reverted one false-positive exclusion during a post-apply
   sanity check: **MultiChallenge** (a hand-picked seed paper, centrally
   about instruction retention/memory drift/coherence loss across
   multi-turn conversations) had been auto-excluded by the subagent despite
   being squarely on-topic. Reverted before finalizing. This is left as a
   documented example of why the seed set specifically was spot-checked
   after the bulk pass, and argues for a similar spot-check if the same
   method is reused elsewhere in the corpus.

## Result

- **118 papers excluded**, 0 of them seeds.
- **Working corpus: 890 papers** (down from 1,008).
- Full paper-by-paper decision + reason log:
  `data/exports/rescreen_decisions_20260817.csv` (179 rows, all decisions
  including the ones not overridden).

## Known limitation / scope not covered by this pass

This pass targeted only the highest-risk profile (`direct-input` channel +
`none` defense). The same drift pattern — an overbroad search query or
citation-snowball hop pulling in topically-adjacent-but-off-topic papers —
could in principle exist elsewhere in the corpus (other channels, other
consequence labels) at lower density, and was not exhaustively checked.
Report this as a stated limitation of the corpus if it isn't independently
verified before submission, consistent with how the RQ2 cross-citation
classification-noise caveat is being handled.

## Addendum (same day, later) — duplicate paper entries found

While building the RQ3/RQ4 registries, fuzzy title-matching surfaced 3
genuine duplicate paper entries in the corpus that the original dedup
pipeline missed (each pair: one entry with a resolved arXiv ID and full
data, one without, title slightly reworded between versions):
PoisonedRAG (rows 5/250), AgentVigil (rows 51/57), and "Multi-Agent
(AI) Framework for Threat Mitigation and Resilience" (rows 266/327). The
no-arXiv-ID entry in each pair was excluded (same `screen_human` mechanism
as the rest of this log). Working corpus is now **887 papers** (was 890).
A 4th candidate pair surfaced by the same fuzzy match (rows 187/209,
title similarity 83) was checked and found to be two genuinely different,
independently-authored survey papers on the same topic — not merged.
RQ1 and RQ2's published numbers were updated accordingly
(`rq1_taxonomy_analysis.md`, `cross_citation_analysis.md`); RQ2's B→A rate
moved from 7.5% to 9.2% as a result.

## Addendum 2 (2026-09-07) — full audit of the 122 excluded rows

Triggered by a direct question: if ~25.9k records were discarded upstream,
what makes the 122 excluded at the *extraction* stage a different category, and
is anything relevant sitting in them? Every one of the 122 was re-examined.

**Result: 4 duplicate artifacts, 0 genuine false negatives.**

**The 4th duplicate, and a documentation inconsistency this exposed.**
Addendum 1 above records 3 duplicate pairs and a resulting corpus of 887.
`rq3_pollution_census.md` records **4**, naming "a position-bias mechanism
paper" as the fourth. The data agrees with the census (886 Include today, not
887), so the fourth exclusion happened during RQ3 registry construction and
was never back-ported into this log. Confirmed here:

| | Included | Excluded (shadow record) |
|---|---|---|
| Title | Mitigate Position Bias in Large Language Models via Scaling a Single Dimension | Mitigate Position Bias in LLMs via Scaling a Single Hidden States Channel |
| paper_id | `arxiv:2406.02536` | `6e5fce29cbd9db7f` |
| arXiv ID | 2406.02536 | none |

Same paper, retitled between arXiv versions — the same profile as the other
three (one resolved entry with an arXiv ID and full data, one bare S2 record
without). **The duplicate count is 4, not 3**; Addendum 1's "887" should read
886. All four excluded rows are shadow records, so none represents a paper
missing from the analysis.

**No genuine false negatives.** Screening the remaining 118 for
contamination-relevant terms in title+abstract flagged 11 for manual reading.
All were correctly excluded on the stated criteria: `Cordyceps` is
fine-tuning-time data poisoning (explicitly out of scope — this project is
about runtime context); the prompt-injection-vulnerability papers are
measurement-only, which the RQ3 registry bar rejects even for *included*
papers (that same rule excluded 480 of 890 included papers); `KCIF` is a
benchmark. The other 107 carry no contamination signal at all — agent
capability, RL training, planning, and robotics papers that matched on
"agent" or "long-horizon", the same drift Addendum 1 documents.

**Why the 122 are a different category from the ~24.9k.** They are the only
papers excluded *after* the extraction pass: all 122 were coded against the
Section 3 scheme (channel, consequence, intervention point, evidence grade),
and 110 of them additionally had full-text extraction (technical summary, key
result, baselines compared, stated limitations). Everything upstream was cut
by rules on title/abstract, at three earlier stages: the FR-7
auto-screen (recall-oriented by design), then the precision filter in
`src/confidence.py` (auto_include + names a known method/author signature
term + >=1 citation), which reduced the ~14.9k hop-0/1 working set to 1,008.
This is the standard systematic-review funnel: earlier stages are reported as
counts, the final extraction stage is reported item-by-item with reasons —
which is what this log is for.

Nothing was deleted at any stage. All 25,922 records remain in
`data/context_sok.db`, and the cut is a pure reproducible filter
(`confidence.high_confidence_ids`), re-runnable at different thresholds, so
the boundary is auditable rather than asserted.

**The honest exposure is upstream, not here.** `src/confidence.py` is, by its
own docstring, "a project-owner decision to substitute a stricter automated
cut for part of the manual screening pass" — a keyword-signature and citation
filter standing in for two-coder manual screening at a volume where manual
screening was not feasible. That, not the 122, is the screening decision most
open to challenge, and it should be stated plainly in threats to validity.
This audit constrains its downstream effect: at the final stage the boundary
introduced no false negatives, and the headline coverage gap (61.2% of
mechanisms undefended) is unchanged by anything found in the 122.

## Addendum 3 (2026-09-07) — the corpus has two extraction tiers, and it matters

Checking the previous addendum's own wording surfaced something not
documented anywhere: **the 1,008 papers did not all receive the same
treatment.** Two distinct passes were applied, and conflating them is an
overclaim waiting for a reviewer.

| Pass | Papers | What it produced |
|---|---:|---|
| Categorical coding (plan Section 3 scheme) | **1,008** (100%) | channel, consequence, intent, defense_intervention_point, evidence_grade |
| Full-text extraction | **880** (87%) | technical_summary, key_result, baselines_compared, stated_limitations, models_evaluated, datasets_benchmarks |

The 128 papers without full-text extraction are exactly those with no local
PDF; they were coded from title and abstract. Among the 886 included papers
the split is 770 full-text / 116 categorical-only.

**Terminology consequence.** Because two passes exist, no single verb is
accurate for the whole corpus. Use PRISMA's umbrella term **data extraction**
(already the first half of the plan's Section 3 title, and unambiguous in a CS
venue where "coding" also means writing software); reserve **coding** for the
categorical scheme, which genuinely applies to all 1,008; and say **full-text
extraction** only of the 880. **Do not write "we read all 1,008 papers in
full" — that is true of 880.**

**Methodological consequence, and this one is substantive.** RQ5 matched
defenses to mechanisms by reading each defense paper's own
`baselines_compared` / `key_result` / `technical_summary`. For the 54 defenses
whose papers never got full-text extraction, those fields are empty — so
those defenses could not be matched *by construction*, regardless of what
their papers actually did:

| Defense papers | Matched to >=1 named mechanism |
|---|---:|
| With full-text extraction (425) | 170 (**40.0%**) |
| Without (54) | 1 (**1.9%**) |

A 20x gap. **53 of the 308 unmatched defenses (17%) are unmatched because
there was no text to match against, not because the defense was never
evaluated.** The honest framing of RQ5's headline is therefore that 35.7% of
*all* defenses have a confirmed mechanism match, but **40.0% of the defenses
that were actually eligible for matching** do — and the remaining gap is a
measurable artifact of PDF availability, not evidence about the field.

This should be stated in threats to validity, and RQ5's coverage figures
should carry the 40.0% denominator alongside the 35.7% one. Closing it is a
bounded task: fetch the 128 missing PDFs and re-run extraction on them, which
would also let the 11 mechanisms and 54 defenses currently sourced from
abstract-only records be re-derived from full text.

## Addendum 4 (2026-09-07) — a fifth duplicate, still counted as Include

Found while extracting full text from newly-fetched PDFs: the PDF downloaded
for row 59 ("AGENTFUZZER: Generic Black-Box Fuzzing for Indirect Prompt
Injection against LLM Agents") is arXiv 2505.05849v4, titled *AgentVigil:
Generic Black-Box Red-teaming...*. **Rows 51, 57 and 59 are all the same
paper**, renamed across arXiv versions (AgentFuzzer → AgentVigil):

| Row | Screening | arXiv | Cites | Title as stored |
|---|---|---|---:|---|
| 51 | Include | 2505.05849 | 39 | AgentVigil: Generic Black-Box Red-teaming... |
| 57 | Exclude (deduped 2026-08-17) | none | 24 | AGENTVIGIL: Automatic Black-Box Red-teaming... |
| 59 | **Include** — missed | none | 3 | AGENTFUZZER: Generic Black-Box Fuzzing... |

Addendum 1's pass caught the 51/57 pair but not 51/59, because the rename
pushed title similarity to 81 — below the threshold used. This one mattered
more than the others: **it was still Include**, so the paper contributed *two*
RQ3 mechanism entries — `AgentVigil` (row 51) and `UNNAMED: AgentFuzzer
(generic black-box fuzzing for IPI)` (row 59) — a double-count of one
technique under two names.

**Effect.** Row 59 is now Exclude (corpus 886 → 885 Include). The duplicate
mechanism is retracted: RQ3 **183 → 182**. Because the phantom was *uncovered*
while canonical `AgentVigil` is covered by one defense, uncovered mechanisms
go **112 → 111** and the never-defended share **61.2% → 61.0%**; covered stays
71. So one of the "never defended" mechanisms was never a distinct mechanism.

**Sweep for others.** All 886 included papers were then checked pairwise:
zero same-arXiv-ID duplicate groups, and only two fuzzy title pairs at or
above 80 — this one, and the "Enhancing Security in LLMs" / "The Comprehensive
Review on Prompt Injection Attacks" pair that Addendum 1 already adjudicated
as two genuinely distinct surveys. **The included corpus is otherwise clean.**

**Reproducibility.** The retraction lives in
`data/registries/registry_corrections.json` and is applied at load time, not
edited into the registry JSONs. The published numbers remain exactly
recoverable: `registry_source.load_all(include_supplementary=False,
include_corrections=False)` still returns 183 mechanisms / 116 uncovered /
63.4% / 190 pairs.

**Method note for the paper.** Title-similarity dedup has a blind spot for
papers renamed between preprint versions. The reliable signal is the arXiv ID
*inside the PDF*, which only becomes available once the PDF is fetched — which
is why this surfaced during the PDF backfill rather than during screening.

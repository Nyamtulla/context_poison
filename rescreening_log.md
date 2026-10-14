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

---

## Addendum 4 — the screening delta lands; abstract-based dedup finds two more duplicates (2026-09-21)

### What happened

The 164 papers recovered by the 2026-09-11 screening rule finished their PDF
pass and entered the corpus. Of the 36 that needed manual retrieval, the project
lead obtained **23** (the whole IEEE Xplore block bar one); the remaining **13
were discarded by decision** as unavailable or not from an acceptable source
(`MANUAL_DOWNLOADS_screening_delta.md` holds the full list with DOIs).

Every manual PDF was verified before ingest — magic bytes, extractable text
(18k–168k chars), and the paper's own title present in its own extracted text —
so no paywall login page or wrong-paper save entered the corpus. Zero failures.

**Corpus: 1,008 → 1,158 rows, 1,033 Include.** (164 recovered − 13 discarded
− 1 already present as a seed row = 150 appended; then 2 excluded as duplicates,
below.) Note this lands at 1,158, not the 1,172 the 2026-09-11 commit projected:
that figure counted all 164 before the 13 discards and the seed-row overlap.

One paper the screening-gap analysis listed as lost — Greshake et al., *Not What
You've Signed Up For* (1,639 cites) — turned out to be **already in the corpus**
at row 2, curated in via the seed path. It was missing from the *screening pool*,
not from the corpus. The append guard caught the overlap.

### A duplicate class the title-similarity pass cannot see

`scripts/dedupe_corpus.py` matches on title similarity. Addendum 2 already
recorded its blind spot: a paper **renamed between preprint and publication**
scores below the threshold and survives. That blind spot was still open, so it
was still costing us.

Added `scripts/dedupe_by_abstract.py` — same idea, but comparing **abstracts**,
which authors carry over near-verbatim across a rename. Run over all 1,033
included papers it found **two duplicate pairs, both invisible to title
matching**:

| abstract sim | title sim | rows | verdict |
|---:|---:|---|---|
| 100.0 | 76.5 | 48 / 90 | same paper — **identical DOI** `10.3390/info17010054` |
| 99.2 | 53.2 | 1035 / 1036 | same paper — InjecGuard (arXiv 2410.22770) renamed to PIGuard (ACL 2025) |

The first pair had been sitting in the original 1,008-paper corpus undetected
since the first build. The second arrived with the delta.

**Resolution — merge, then exclude, so no data is lost:**

- **Rows 48 / 90.** Kept **row 48**: seed-discovered, has the PDF, and carries
  the full 15-column extraction that row 90 lacks entirely. But row 90 held the
  real Semantic Scholar id, the real author list and **42 citations** against
  row 48's placeholder `Unknown` / `0`. Merged authors and citation_count into
  row 48 first, then excluded row 90. Neither row contributed a registry entry
  (both code as survey, `has_technique=N` / `has_defense=N`), so RQ3/RQ4 are
  unaffected; RQ2 and any citation-weighted view gain a corrected 42.
- **Rows 1035 / 1036.** Kept **row 1035** (PIGuard, ACL 2025, 51 cites — the
  peer-reviewed version of record), carrying row 1036's arXiv id across first,
  then excluded row 1036. Both had been coded as defenses in the 2026-09-13
  pass, so this prevents the registry double-counting one guardrail model under
  two names — the same failure mode Addendum 2 caught with AgentFuzzer/AgentVigil.

No `registry_corrections.json` retraction was needed for either: `build_registry.py`
filters on the Excel's `screening` column at load, so an excluded row never
contributes an entry in the first place. These were caught *before* the delta
registry was built, not after publication.

After applying both, the abstract sweep reports the corpus clean on that axis.

### Method note

Two of this project's five confirmed duplicate papers were preprint/publication
renames that title similarity could not reach. That is now a known, checkable
failure mode with a dedicated script rather than something rediscovered by
accident each time. `dedupe_by_abstract.py` should run alongside
`dedupe_corpus.py` in Phase 1 of the rebuild pipeline.

### The rebuild's numbers (2026-09-21)

Full pipeline re-run after the delta landed: dedup → RQ3/RQ4 registries →
RQ5 coverage matrix → RQ1/RQ2.

| | before | after |
|---|---:|---:|
| corpus rows | 1,008 | 1,158 |
| included | 885 | 1,030 |
| RQ3 mechanisms (registry) | 183 | 223 |
| RQ3 mechanisms (incl. benchmark-supplementary) | 196 | 237 |
| RQ4 defenses | 479 | 534 |
| RQ5 confirmed pairs | 289 | 332 |
| defenses with ≥1 confirmed match | 188 (39.2%) | 213 (39.9%) |
| mechanisms with ≥1 defense | 94 (48.0%) | 106 (44.7%) |
| mechanisms with zero defenses | 102 | 131 |
| RQ1 empty cube cells | 63.6% | 60.5% |
| RQ2 Track A→B citation rate | 10.8% | 11.8% |
| RQ2 Track B→A citation rate | 9.2% | 9.1% |

Three findings are worth separating from the bookkeeping.

**1. RQ3's channel gap closed, and the old ranking overstated a gap we had
manufactured.** `direct-input` rose from 43 (23.5%) to 66 (29.6%) while
`tool-output` went 62 (33.9%) → 66 (29.6%) — they are now **exactly tied**.
23 of the 41 new mechanisms are direct-input. The original census's "tool-output
dominates" reading reflected a corpus selected for agent-era vocabulary, not the
literature. Written up in `rq3_pollution_census.md`.

**2. RQ4's load-bearing number did not move.** Defenses validated against *both*
threat models: 2.9% → 2.8%, after adding 55 defenses including StruQ, SecAlign,
Spotlighting, the Instruction Hierarchy and Attention Tracker. The 97%
single-threat-model claim survives the largest corpus expansion the project has
made.

**3. The coverage gap did not close, contradicting this file's own prediction.**
`screening_gap_analysis.md` (2026-09-11) predicted the gap would shrink once the
foundational defenses were registry entries. It did not. Of the mechanisms the
45 new pairs covered, **zero were pre-existing**; all 11 were mechanisms added in
the same pass. Coverage of the 196 previously-registered mechanisms is unchanged
at 94 (48.0%).

The mechanism is visible: the recovered defenses evaluate on the attack suites
their own community shares — BIPIA, Combined Attack, CyberSecEval, HackAPrompt,
Tensor Trust — all of which entered the registry in the *same* pass. The
recovered defenses and recovered attacks cover each other and leave the existing
gap untouched. The overall rate fell (48.0% → 44.7%) because the recovered
papers named more new attacks than they closed old gaps.

This is a stronger result than the predicted one. The objection "your coverage
gap is an artifact of your corpus boundaries" has now been tested directly, by
deliberately importing the literature we believed was missing, and it does not
hold. RQ7's "invention outpaces evaluation" framing is correspondingly firmer.

### Two pipeline bugs found and fixed during the rebuild

- **`evidence_grade` was being coded against the wrong rubric.** The delta came
  back 62% grade-B against a 14.6% baseline. The project protocol grades
  *publication rigor* (peer-reviewed+artifacts / peer-reviewed / credible
  preprint / gray literature), not evaluation quality; the extraction spec had
  stated it the other way round. The corpus is unambiguous — all 147 baseline
  B's are peer-reviewed venue papers, 0 of 707 arXiv papers are B, and both
  grade-D papers have no venue at all. Encoded the two invariant rules as a
  normalization step in `scripts/apply_delta_extraction.py` (arXiv → never B;
  D requires no venue), correcting 50 grades. The B-vs-C split within real
  venues is left as coded, being a genuine venue-tier judgment.
- **`build_coverage_matrix.py` double-counted collapsed pairs.** When name
  reconciliation maps two differently-worded matched names onto one registry
  entry, the defense contributed the same pair twice and `n_matched_pairs`
  overstated the matrix — the single number the deliverable exists to report
  honestly. It reported 235 where 233 were distinct. Now deduplicated after
  reconciliation, with the collapse count logged.

### A third dedup axis: identifiers

The reverse coverage pass surfaced that `Combined Attack` and `Combined Attack
(Open-Prompt-Injection)` were one technique from one paper, registered twice.
Investigating showed why neither existing pass could see it: row 1126 has an
**empty abstract**, so the abstract sweep skipped it, and the titles differ too
much for the title sweep.

The signal that does work is the identifier, and nothing was checking it.
`scripts/dedupe_by_identifier.py` normalises arXiv ids from *both* the
`arxiv_id` field and DOIs of the form `10.48550/arXiv.NNNN` — rows 1011 and
1126 are one paper precisely because one's `arxiv_id` equals the other's DOI
suffix. It found **three** duplicate groups at first run, all preprint/published
pairs invisible to the other two passes:

| arXiv id | rows | note |
|---|---|---|
| 2302.12173 | 2 / 1125 | Greshake et al. — *"Not What You've Signed Up For"* vs *"More than you've asked for"*. **Same paper, not companion papers.** |
| 2310.12815 | 1011 / 1126 | Liu et al. — USENIX title vs arXiv title |
| 2506.23260 | 49 / 301 | *"From Prompt Injections to Protocol Exploits"* — already in the original corpus |

All three resolved by merging the better metadata into the keeper, then
excluding. RQ3 223 after the Combined Attack retraction. All three sweeps
(title, abstract, identifier) now report the corpus clean.

Five of this project's eight confirmed duplicate papers were preprint/publication
renames. Run all three passes in Phase 1; the identifier pass is the cheapest and
catches the most.

### Addendum 5 — two off-criteria papers excluded (2026-09-22)

The screening-delta extraction flagged three papers as out-of-scope that the
2026-09-11 threat-term rule had admitted. Checked each against
`config.yaml`'s actual `include_criteria_text` rather than the extracting
agent's verdict. **Two fail, one does not.**

**Excluded — row 1093, *Fingerprinting LLMs via Prompt Injection* (ACL 2025,
4 cites).** Proposes LLMPrint, a model-provenance/IP-protection method that
uses optimized prompts — which the authors call prompt injection — to
fingerprint a base model. There is no victim application, no contaminated
context, and no adversary: the "attacker" is the model owner verifying their
own IP. Admitted purely on "prompt injection" in the title. Fails "presents an
attack, defense, benchmark, or empirical measurement of context contamination."

**Excluded — row 1061, *LLMs and Childhood Safety* (arXiv 2025, 16 cites).**
A systematic literature review of child-LLM interaction risks (bias,
inappropriate content, emotional manipulation) proposing a conceptual
protection framework. Its only prompt-injection mention is one item in a list
of evaluation targets the framework says developers should measure. No
implementation, no experiments, no measurement of context contamination. This
is exactly the failure mode `config.yaml`'s own comment on `threat_terms`
anticipates — "a threat term alone would admit every survey that mentions
prompt injection in passing" — except here both required lists hit off the
same passing sentence, so requiring both did not stop it.

**Kept — row 1057, *LongFaith* (ACL 2025, 18 cites).** The extracting agent
called it "out-of-scope-adjacent" because its knowledge conflicts arise during
synthetic *training*-data generation rather than at inference. The criteria do
not support excluding it. The include text explicitly covers
"context-length/quality degradation," which is precisely what LongFaith
addresses (long-context reasoning faithfulness, distraction, knowledge
conflict). Its intervention being training-time is not disqualifying: SecAlign,
StruQ and the Instruction Hierarchy are all training-time defenses already in
the RQ4 registry. The exclusion clause targets training-time *poisoning
attacks* ("this is about runtime context, not pretraining"), not training-time
defenses against runtime degradation.

**Two more found by the same test.** Reviewing the remaining eleven
out-of-scope flags against the criteria surfaced two with an identical profile
to row 1061 — row **1130** (*LLMs for Cybersecurity Intelligence, Threat
Hunting*, a review of LLMs used *as* security tools) and row **1155**
(*Integrating Generative AI in Cybersecurity Curricula*, a pedagogical
framework). Each mentions prompt injection exactly once, in a list of
challenges or lab topics. Both excluded.

The other nine are **surveys of prompt injection itself** and were kept. They
present no attack or defense of their own and contribute no registry entry, but
their subject is squarely context contamination, and the corpus has included
surveys since its first build. Whether a pure survey satisfies "presents an
attack, defense, benchmark, or empirical measurement" is a genuine policy
question that would affect the original 1,008 papers too, not just this delta —
flagged rather than decided here.

**Effect.** Corpus 1,030 → **1,026 included** (4 exclusions). No excluded paper
contributed an RQ3 or RQ4 entry, so both registries are unchanged at 223 and
534, and the RQ5 matrix is unchanged at 332 pairs. RQ1 recomputed over 1,026
papers; RQ2's Track A→B rate moved 11.8% → 11.7% (70/599), B→A steady at 9.1%.
No headline number moved.

**Method note.** Both admissions came through the second, threat-term path
added on 2026-09-11, and neither carries any agent-era signal term. That path
was designed to recover foundational pre-agent papers and it did that job, but
it has a known false-positive profile: a paper can satisfy `threat_terms` and
`threat_action_terms` from a single passing sentence. Requiring both lists
narrows it but does not close it. The `scope_verdict` field produced during
extraction is currently the only systematic check on this, and it is applied
per-paper by an agent rather than by the screening rule itself.

---

## 2026-10-13 — 28 exclusions: 25 disconnected, 3 on a full read

Two independent passes, applied together.

**Three excluded after reading the full paper.** The 31 PDFs recovered from the
missing-PDF worklist were read abstract-to-conclusion against `config.yaml`'s
criteria. Twenty-seven passed. Three did not:

| paper | why |
|---|---|
| Verlog | An RL fine-tuning framework; its customizable memory length is a training-efficiency device, not a study of context failure. Training-time, not runtime. |
| IEI-TIA | A supervisory agent for robotic sorting. "Trustworthy" means the VLA model's actions are interpretable, not that its context is protected. |
| LLM-PEA | The LLM is a classifier of phishing emails, not an agent with tool use, RAG or memory. No agentic context channel. |

A fourth — *Evaluating and Exploiting Security Vulnerabilities in LLMs for
Offensive Penetration Testing* — was **flagged, not excluded**. It is largely
chat-model red-teaming, but two of its five vectors are agentic. Left in,
pending a scope call.

**Twenty-five excluded as disconnected.** On the rebuilt citation network
(`citation_network_rebuild.md`), these papers have **out-degree 0 and in-degree
0** — they cite nothing in the corpus and nothing in the corpus cites them — by
the union of the full-text pass and the S2 edge table. All are `role='neither'`
and contribute no RQ3 or RQ4 entry. None is from 2023.

The in-degree condition is doing real work here and is not decoration.
Out-degree alone selects **foundational** papers: 36 % of the corpus's 2023
papers cite nothing in it, including *Not What You've Signed Up For* (in-degree
432) and *Lost in the Middle* (206), because they came first. Excluding on
out-degree alone would have removed the origin of both literatures.

### Effect

| | before | after |
|---|---:|---:|
| included corpus | 1,026 | **998** |
| channel × consequence cells occupied | 35 | 35 *(no cell emptied)* |
| RQ2 Security → ML/AI | 70/599 = 11.7 % | **70/590 = 11.9 %** |
| RQ2 ML/AI → Security | 37/407 = 9.1 % | **37/390 = 9.5 %** |
| RQ3 attack registry | 237 | 237 *(unchanged)* |
| RQ4 defense registry | 534 | 534 *(unchanged)* |

Both cross-citation rates move **up** by a few tenths, because 23 of the 25
disconnected papers were coded `cites_track_a=N, cites_track_b=N` — removing
non-citing papers from the denominator raises the rate. The direction is a
consequence of the selection criterion, not a finding, and should be described
that way.

No registry row referenced any removed paper, so RQ3, RQ4 and the RQ5 matrix
are untouched.

### Mechanism

`screening` was flipped `Include → Exclude`; **no row was deleted**, so the
change is reversible and the papers remain inspectable. The 28 ids are in
`data/registries/excluded_2026-10-13.json`.

### Stale numbers elsewhere

These documents quote the pre-change figures and are now out of date:
`rq1_taxonomy_analysis.md`, `rq3_pollution_census.md`, `rq4_defense_census.md`,
`cross_citation_analysis.md`, `differentiation_table.md`, `rq5_coverage_matrix.md`,
`rq7_open_problems.md`, `RESEARCH_ROADMAP.md`, `citation_graph_isolates.md`,
`context_integrity_sok_project_plan.md`, `benchmark_standardization.md`.

They are dated snapshots of what was computed when, so they are left as written
rather than edited in place; regenerate them with the `rebuild-corpus` pipeline
before the numbers are quoted anywhere new.

**`citation_graph_isolates.md` needs more than a regeneration.** It was built on
the S2 edge table, which `citation_network_rebuild.md` shows had 199 isolates
against the full text's 105 — 98 of its isolates demonstrably do cite the
corpus. Its conclusions should be re-derived on the union network, not refreshed.

---

## 2026-10-13 (second pass) — 26 excluded as unreadable. Corpus 998 → 972

Papers with **no PDF** (16) or **a PDF whose reference section will not
extract** (10). Removed from the corpus and from the RQ3/RQ4 registries.

### This one is different, and the difference must travel with the numbers

The earlier passes excluded papers for properties of the papers: out of scope
on a full read, or disconnected from the literature in both directions. **This
pass excludes papers for a limitation of our pipeline.** Nothing is wrong with
these papers; we could not obtain or parse them.

That matters because the limitation is not randomly distributed:

| | excluded 26 | corpus |
|---|---:|---:|
| IEEE / other paywalled venue | 21 | — |
| arXiv | 3 | — |
| Security track | 20 (77 %) | 59 % |

This is the same paywall gap measured in `verification/missing_pdf_worklist.md`:
security work publishes in IEEE conferences, ML/AI work goes to arXiv, and our
fetcher reaches arXiv. **Excluding the unreadable therefore removes a
venue-correlated and track-correlated slice of the corpus, not a random one**,
and any count derived from the 972 inherits that. It should be disclosed
wherever those counts appear, not buried here.

Two of the removed are not marginal papers:

- **Tug-of-War between Knowledge (CD2)** — 117 citations, `role='both'`, the
  best-cited untested defense in the silent-corruption cell. Its PDF is
  present; only its reference section fails to parse.
- **Site Isolation is Dead** — IEEE S&P 2026, `role='attack'`.

### Effect

| | before | after |
|---|---:|---:|
| included corpus | 998 | **972** |
| RQ3 attack registry | 237 | **233** |
| RQ4 defense registry | 534 | **525** |
| RQ2 Security → ML/AI | 70/590 = 11.9 % | **68/570 = 11.9 %** |
| RQ2 ML/AI → Security | 37/390 = 9.5 % | **36/384 = 9.4 %** |

The cross-citation rates barely move, which is the first pass in this sequence
where that is true — these papers were a representative mix of citing and
non-citing, unlike the disconnected set.

**13 registry entries were retracted.** They are recorded in
`data/registries/registry_corrections.json` with cause, following the existing
applied-on-load convention, so `load_all(include_corrections=False)` still
reproduces the originally published 237 / 534.

### Reversal

`screening` flipped `Include → Exclude`; no paper row deleted. Registry rows
*were* deleted, but every one is reconstructable from the corrections file. Ids
in `data/registries/excluded_unreadable_2026-10-13.json`.

**The cheapest way to undo most of this is to fetch the 16 missing PDFs** —
they are on `verification/missing_pdf_worklist.xlsx` with links, and most are a
single IEEE Xplore library session.

---

## 2026-10-13 (third pass) — 10 of the 26 restored. Corpus 972 → 982

The previous entry excluded 10 papers whose "reference section will not
extract". That was wrong about the papers and right about the extractor.

CD2's PDF was inspected directly. It is an **LREC-COLING** paper, and LREC
prints **"Bibliographical References"** and **"Language Resource References"**
rather than "References". The detector required the heading word alone on its
own line, so it found nothing in a paper with a 12,065-character bibliography.

Checking the other nine found the same class of problem, every one a venue
convention rather than a broken file:

| cause | papers | example |
|---|---:|---|
| LREC heading wording | 1 | `Bibliographical References` (CD2) |
| roman section number | 3 | `VII. REFERENCES`, `VIII. REFERENCES` |
| IEEE small-caps extracted with a space | 3 | `R EFERENCES` |
| non-English heading | 1 | `REFERENSI` (Indonesian) |
| other heading variants | 2 | — |

**All 10 recover with a venue-aware heading pattern**, yielding 2,555–14,010
characters of references each. They are restored to the corpus, and their
registry entries re-inserted from the authoritative RQ3/RQ4 JSONs — which were
never edited, exactly so this kind of reversal stays possible.

One further fix: the detector took the **last** matching heading. LREC papers
print two, and the second ("Language Resource References") is short, so taking
the last discarded the main bibliography. It now takes the earliest heading
that leaves a substantial tail.

### Effect

| | before | after |
|---|---:|---:|
| included corpus | 972 | **982** |
| RQ3 attack registry | 233 | **235** |
| RQ4 defense registry | 525 | **528** |
| reference lists that will not extract | 10 | **0** |
| corpus papers citing ≥1 corpus paper | — | **934 of 982 (95.1 %)** |

**Every PDF in the corpus now yields a reference list.** The 16 papers still
excluded are the ones with no PDF at all; those are a fetching problem, listed
with links in `verification/missing_pdf_worklist.xlsx`, not a parsing one.

### What this says about the earlier pass

Excluding papers for being "unreadable" deleted ten papers because of a
regular expression. The bias warning recorded in the previous entry — that the
exclusion was venue-correlated — turns out to have been understating it: the
venues whose conventions the detector did not know are precisely IEEE and LREC,
which is to say most of the non-arXiv corpus. **"We could not parse it" is a
claim about the parser and should be tested against a second method before it
becomes a deletion.**

---

## 2026-10-13 (fourth pass) — correcting why the last 14 are out

The second pass recorded 26 exclusions as "unreadable" and attached a bias
warning: that the removal was forced by a pipeline limitation and carried a
venue and track skew. **Both halves of that are now wrong and are withdrawn.**

- **Ten were the extractor's fault, not the papers'.** They are back (third
  pass above). The reference-heading detector did not know LREC's
  "Bibliographical References", IEEE's roman section numbers and small-caps
  "R EFERENCES", or a non-English heading.
- **Two more were simply fetchable** from arXiv once the right routes were
  tried, and are back.
- **The last fourteen were never wanted.** The project lead reviewed them at
  download time and deliberately did not obtain them: withdrawn papers, or
  judged out of scope. The missing PDF is a *consequence* of that decision,
  not its cause.

So the correct description of the 14 is **relevance exclusions** — an ordinary
screening decision — and the venue-bias caveat does not apply to them. It did
apply, correctly, to the ten that were removed by a regular expression, and
that is precisely why they were restored.

Their basis is the lead's review of title, venue and abstract rather than a
full read, which is weaker evidence than the 31 papers read end-to-end in
`verification/downloaded_relevance_pass.md`. Worth one line in the limitations,
not more: screening on title and abstract is the normal standard, and these
papers were never in a position to contribute a registry entry — none did.

Recorded in `verification/excluded_not_wanted.json` (formerly
`still_missing.json`, renamed because the old name asserted the wrong reason),
together with the retrieval routes already attempted so nobody repeats them.

### State after all four passes

| | |
|---|---:|
| included corpus | **984** |
| PDF coverage | **984 / 984 — 100 %** |
| reference lists that will not extract | **0** |
| union citation edges inside the corpus | 6,970 |
| papers citing ≥1 corpus paper | 936 (95.1 %) |
| RQ3 attack registry | 235 |
| RQ4 defense registry | 529 |
| RQ2 Security → ML/AI | 11.8 % |
| RQ2 ML/AI → Security | 9.3 % |

From the 1,026 this sequence started at: 28 excluded on disconnection and a
full read, 14 excluded as not wanted, and the rest restored or retained.

---

## 2026-10-13 (rebuild) — RQ1/RQ2 regenerated on the 984-paper corpus

Criteria in `config.yaml` were **not** changed, so the AI re-screening phase
was deliberately skipped: it would have re-litigated the 54 screening
decisions made by hand today rather than testing a new rule.

**Those 54 decisions are now recorded as `screen_human` in `context_sok.db`**
(42 Exclude, 12 Include). They were made in the Excel and the explorer DB only,
where `rescreen_corpus.py` cannot see them — it protects a paper from
re-export by checking `screen_human IS NOT NULL`, so until this was written a
future re-screen would have handed all 54 back to a subagent to re-judge.
Protected rows rise 138 → 192.

### Phase 1 — integrity

All three dedupe passes clean:

| pass | result |
|---|---|
| identifier (DOI + normalised arXiv) | no duplicate groups |
| abstract similarity | 981 papers with abstracts ≥200 chars, none near-identical |
| title similarity | 3 candidates at 81–83, **all false positives** |

The three title pairs are distinct papers with different authors, DOIs and
venues — two independently written reviews on prompt injection, two unrelated
surveys, and two unrelated frameworks. Checked individually rather than
accepted on score, per the skill's warning that most candidates are
coincidence.

### Phase 3 — RQ1 and RQ2

| | before | after |
|---|---|---|
| corpus | 1,026 | **984** |
| RQ1 empty cells | 60.5 % (98 of 162) | **60.5 % (98 of 162)** — unmoved |
| RQ2 Security → ML/AI | 11.7 % (70/599) | **11.7 % (68/580)** |
| RQ2 ML/AI → Security | 9.1 % (37/407) | **9.3 % (36/386)** |

**Nothing moved meaningfully.** Removing 42 papers changed the cross-citation
rates by 0.0 and 0.2 points and left the empty-cell rate identical. That is the
useful result: the headline findings do not depend on the papers that were
removed, which is what you want a corpus change to show.

Channel ranking is unchanged: tool-output 344 (35.0 %), direct-input 230
(23.4 %), RAG 136 (13.8 %), memory 104 (10.6 %).

### Phase 4 — registry delta

Zero registry rows point at an excluded paper, so nothing needed dropping. No
newly-included papers, so Phases 5 and 6 did not run and the registries stand
at 235 attacks / 529 defenses.

One case the skill does not cover was checked explicitly: the 30 papers that
received full-text extraction today were always *included*, but their registry
judgments were made from abstracts. Nineteen contribute a registry entry;
the other eleven are all coded `neither`, and reading the new full-text
summaries confirms that is right — they are surveys, taxonomies, benchmarks and
measurement studies, none proposing a *named* technique or defense. So the
abstract-era registry judgments survived contact with the full text.

### RQ3-RQ5 and RQ7 regenerated (same date)

Registries rebuilt from the raw batch CSVs, which `build_registry.py` filters
against the Excel's `screening` column - so the 42 exclusions propagated
correctly without hand-editing any registry JSON.

| | before | after |
|---|---:|---:|
| RQ3 mechanisms (base) | 223 | **221** |
| RQ3 with benchmark supplements | 237 | **235** |
| RQ4 defenses | 529 ← *534* | **529** |
| RQ5 confirmed pairs | 332 | **332** |
| RQ5 defenses with ≥1 test | 213/534 = 39.9 % | **213/529 = 40.3 %** |
| RQ5 mechanisms covered | 106/237 = 44.7 % | **106/235 = 45.1 %** |

**No confirmed defence×mechanism pair was lost.** The excluded papers
contributed two mechanisms and five defenses but not a single matched pair, so
RQ5's matrix is byte-identical and its two rates move only because the
denominators shrank. Every qualitative finding survives: goal-hijack still over
half the RQ3 registry (56.1 %), the adversarial/incidental split unchanged to
the decimal (49.3 % / 47.4 %), and 82.7 % of matched defenses still tested
against exactly one mechanism.

RQ7 recomputed: same-track testing 230/232 = **99.1 %**, cross-track 2 pairs;
76 defenses (32.6 % of pairs) tested against the single umbrella "Indirect
Prompt Injection" entry while **38 of 52 named injection variants have zero**;
supply-chain coverage **0/6**.

**Comparability note.** The published RQ5 rates include the stage-1
supplementary pairs, the attack-paper scan and benchmark resolution, applied on
load by `src/registry_source.py`. `build_coverage_matrix.py` prints the *base*
matrix only — 197/529 defenses and 79/221 mechanisms. Those two are not
comparable to the published figures and reading the script's output as a drop
from 44.7 % to 35.7 % would be wrong.

**Fuzzy-duplicate review.** All 11 flagged name pairs (4 RQ3, 7 RQ4) are
distinct techniques: `IPIGuard`/`PIIGuard` differ on indirect-prompt-injection
versus personally-identifiable-information, `context drift`/`context rot` are
separate incidental mechanisms, and two unrelated techniques both abbreviate to
IPI. `PromptFuzz-SC` extends `PromptFuzz` but is its own paper; its
`is_extension_of` field is unset and arguably should not be, flagged rather
than edited since registry edits move published counts.

---

## Addendum, 2026-10-15 — two out-of-scope papers removed

**Corpus 984 -> 982. RQ4 defenses 529 -> 527.**

Removed:

| row | paper | track |
|---|---|---|
| 381 | RhinoInsight: Improving Deep Research through Control Mechanisms for Model Behavior and Context | ML/AI |
| 566 | FS-Researcher: Test-Time Scaling for Long-Horizon Research Tasks with File-System-Based Agents | ML/AI |

**Why.** Both are deep-research agent papers, evaluated on DeepResearch Bench.
They manage context for long-horizon research tasks. Neither studies context
*becoming untrustworthy*, by attack or by degradation, which is the inclusion
criterion. They entered the corpus on the word "context" in the abstract, which
the automated screen reads as a topic signal and which here is not one.

**How they were found.** They were the only disconnected component in the
citation graph built for the paper's Figure 5: a two-node island, one citing
the other, connected to nothing else in the corpus. Both carry
`cites_track_a = N` and `cites_track_b = N`, so they cite neither literature.
The project lead read both and confirmed they are out of scope.

This is worth recording as a method note. **Graph position surfaced a screening
error that title and abstract screening had passed**, and it did so because a
paper that belongs to neither literature cannot connect to either. A
disconnected component is not automatically wrong (a genuinely novel paper may
be isolated too, and `citation_graph_isolates.md` records why out-degree alone
is a bad exclusion rule), but it is a cheap place to look.

**Effect on the numbers.** Neither contributed an RQ3 mechanism and neither
appears in any RQ5 pair, so coverage, the 349 confirmed pairs and the
cross-track evaluation rate are all unchanged. The retraction is recorded in
`data/registries/registry_corrections.json` under `retracted_defenses`, applied
on load, so the previously published 529 stays reproducible with
`load_all(include_corrections=False)`.

Regenerated after the change: RQ1 (60.5% empty, unchanged), RQ2 (11.7% / 9.3%,
unchanged), `latex/numbers.tex`, and all five paper figures. The citation graph
drops from 934 nodes to 932 and loses its only island.

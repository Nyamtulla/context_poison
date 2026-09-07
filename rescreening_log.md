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

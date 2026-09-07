---
name: rebuild-corpus
description: Re-screen the context-integrity SoK corpus against the current config.yaml inclusion/exclusion criteria and rebuild RQ1-RQ5, reusing the already-searched papers and already-extracted full-text data. Use when the project lead has edited screening criteria (config.yaml) or asks to "rebuild", "re-run", "redo the pipeline", or "refresh the numbers" for this project.
---

# Rebuild Corpus Pipeline

This project (an SoK on LLM agent context poisoning) went through search,
snowballing, PDF download, and full-text extraction once already -- those
are expensive, one-time steps and this skill **does not repeat them**. What
it repeats is: apply the current screening criteria, dedupe the corpus, and
rebuild RQ1 through RQ5's numbers and reports from whatever the corpus looks
like after that. Typical trigger: the project lead edited
`config.yaml`'s `screening:` section and wants to see how it changes the
included corpus and the downstream findings.

Read `context_integrity_sok_project_plan.md` first if you haven't seen it
this session -- it has the full RQ1-RQ7 definitions and methodology this
skill assumes.

## Phase 0 -- sanity check before doing anything

Confirm what's actually being asked. If the request is "add more papers" or
"search for X," that's a different, much bigger task (new search/snowball/
PDF download/full-text extraction) that this skill does not cover -- stop
and clarify scope rather than assuming. This skill is specifically for:
criteria changed -> re-screen -> rebuild analysis, on the existing corpus.

## Phase 1 -- corpus integrity check (always run first)

```bash
python3 scripts/dedupe_corpus.py
```

Report-only. Read every candidate pair it surfaces. Most will be false
positives (two distinct papers with a coincidentally similar title -- this
happened once already, two independently-authored surveys on the same
topic). For genuine duplicates (same paper indexed twice, usually one entry
has a resolved arXiv ID and full data, the other doesn't), confirm by
checking both rows' abstract/arxiv_id/citation_count directly, then:

```bash
python3 scripts/dedupe_corpus.py --apply <row1>,<row2>,...
```

Never exclude a row the script itself refuses (it blocks excluding seed
papers automatically). Always keep the more-complete twin (resolved arXiv
ID, real abstract), exclude the other.

## Phase 2 -- re-screen against current criteria

```bash
python3 scripts/rescreen_corpus.py --export
```

This reads `config.yaml`'s live `screening.include_criteria_text` /
`exclude_criteria_text` and writes `data/registries/raw/rescreen_batchN.json`
(papers needing judgment -- by default, only papers with no `screen_human`
override yet, so a full corpus doesn't get re-litigated every run) plus
`rescreen_prompt.md` (the current criteria, embedded live, not hardcoded).

**For each batch**, spawn a background subagent (`Agent` tool,
`subagent_type: general-purpose`, `run_in_background: true`) with a prompt
built from this template -- fill in the batch file path, and paste the
current contents of `data/registries/raw/rescreen_prompt.md` verbatim so the
agent judges against the live criteria, not a stale copy:

```
Context: re-screening a corpus for an academic SoK on LLM agent context
poisoning against the current inclusion/exclusion criteria.

[PASTE rescreen_prompt.md CONTENTS HERE]

Load your batch: `data/registries/raw/rescreen_batchN.json` (a JSON array,
each entry has row/paper_id/title/abstract/technical_summary/key_result/
threat_model/current_screening). Judge every entry, write results to
`data/registries/raw/rescreen_decisions_batchN.csv` (columns:
row,paper_id,title,decision,reason). Write incrementally (flush every
~20-30 papers) in case of interruption -- check if the output file already
has partial results before starting and skip rows already present.

Report back: total processed, INCLUDE/EXCLUDE counts, and the 10-15 calls
you're least confident about (title + your decision + one-line reasoning)
so they can be spot-checked before applying.
```

Split large exports (>150 papers) into multiple batches the same way the
original full-text extraction and RQ3/RQ4/RQ5 passes did -- 3-4 parallel
background agents of 100-250 papers each is the range that's worked well in
this project; don't spawn dozens of tiny agents.

**Before applying anything**, review each batch's reported low-confidence
calls the way the original re-screening pass did (`rescreening_log.md`,
step 4): read the actual `technical_summary` yourself for the ones you're
unsure about, not just the agent's one-line paraphrase. The original pass
found and overrode 5 of 15 flagged EXCLUDE calls this way, and caught one
seed paper (MultiChallenge) that had been wrongly auto-excluded. Do not skip
this step to save time -- it's the highest-leverage 15 minutes in the whole
pipeline.

Apply the (possibly-adjusted) decisions:

```bash
python3 scripts/rescreen_corpus.py --apply "data/registries/raw/rescreen_decisions_batch*.csv"
```

Then re-run Phase 1's dedupe check once more (screening changes occasionally
surface a duplicate that wasn't visible before).

## Phase 3 -- rebuild RQ1 and RQ2 (fast, always safe to run)

```bash
python3 scripts/rq1_taxonomy.py
python3 scripts/rq2_cross_citation.py
```

Both regenerate their `.md` report directly from the current Excel state --
no AI judgment involved, pure pivot/computation over already-coded columns.
Read the new numbers and note anything that moved meaningfully (a >1
percentage point swing in RQ1's empty-cell rate or RQ2's cross-citation
rates is worth calling out explicitly to the project lead, not just silently
overwriting the old numbers).

## Phase 4 -- determine the RQ3/RQ4/RQ5 registry delta

The registries (`data/registries/rq3_pollution_registry.json`,
`rq4_defense_registry.json`) each entry's `row` field identifies which paper
contributed it. Compare that set of rows against the *currently included*
paper set (Excel `screening != Exclude`, excluding seeds which are handled
separately and rarely change):

- **Newly included papers** (weren't in the corpus's included set when the
  registry was last built, are now) need fresh extraction -- see Phase 5.
- **Newly excluded papers** (were included and contributing registry
  entries, now excluded) -- their registry entries should be dropped. Filter
  them out of the raw batch CSVs in `data/registries/raw/` before re-running
  `build_registry.py`, or note them for manual removal from the registry
  JSON if the raw CSV isn't easily filterable.
- **Unchanged papers** -- do nothing, their registry entries stand.

This delta-based approach is what keeps re-runs cheap -- do not re-extract
the whole corpus's registries from scratch on every run; only the papers
whose inclusion status actually changed need new subagent judgment.

## Phase 5 -- extract registry entries for newly-included papers (RQ3, RQ4)

Only run this phase if Phase 4 found newly-included papers. Use the exact
extraction criteria and batching pattern from the original build (see
`rq3_pollution_census.md` and `rq4_defense_census.md` "Methodology"
sections for the full worked prompts) scoped to just the delta papers:

- **RQ3** needs two passes over the delta: Track A (Security) papers judged
  for named *attack techniques*, Track B (ML/AI) papers judged for named
  *incidental degradation mechanisms* -- same criteria as the original
  pass, output columns `row,paper_id,title,has_technique/has_mechanism,
  technique_name/mechanism_name,channel,consequence,is_extension_of,
  confidence,notes`.
- **RQ4** needs one pass over the delta (both tracks together), judged for
  named *defenses*, with the `validated_against` field (adversarial/
  incidental/both, based on what the paper's own evaluation actually
  tested) -- output columns `row,paper_id,title,has_defense,defense_name,
  channel,consequence,defense_intervention_point,track,validated_against,
  is_extension_of,confidence,notes`.

Write new/updated raw batch CSVs into `data/registries/raw/` (append to the
existing batch files, or add a new `rq3_delta_batchN.csv`/
`rq4_delta_batchN.csv` -- either works since `build_registry.py` reads every
file matching its configured source list; add new delta files to that list
in `scripts/build_registry.py` if you introduce new filenames).

Then rebuild both registries:

```bash
python3 scripts/build_registry.py rq3
python3 scripts/build_registry.py rq4
```

Read the fuzzy-dedup pairs each prints/writes to `rqN_registry_report.md`.
Most are false positives (coincidentally similar names for distinct
techniques); occasionally one is a genuine duplicate *paper* the corpus
dedup pass (Phase 1) missed -- if so, go back to Phase 1, fix it there, and
re-run this phase.

**Refresh the narrative reports** (`rq3_pollution_census.md`,
`rq4_defense_census.md`) using the new registry stats -- the existing files
are good templates for structure (headline numbers, by-channel/by-
consequence tables, registry construction notes, known limitations). Update
the numbers and re-examine whether the qualitative findings (e.g. "70/30
adversarial/incidental split," "goal-hijack accounts for over half the
registry") still hold at the new scale, rewording the discussion where they
don't.

## Phase 6 -- rebuild RQ5's coverage matrix

Only needed if Phase 5 ran (RQ3 or RQ4 registries changed) or if RQ4's
`validated_against` tagging changed for any existing defense.

For every defense that's new or whose registry entry changed, spawn a
matching subagent against the **full current** RQ3 registry (not just the
delta -- a new mechanism could be tested by an old defense, or vice versa),
following the exact matching prompt in `rq5_coverage_matrix.md`
"Methodology" (mine `baselines_compared`/`key_result`/`technical_summary`
for mentions of registry mechanisms actually tested against, favor false
negatives over false positives, output
`defense_row,defense_name,matched_mechanism_name,match_justification,
match_confidence`).

Then:

```bash
python3 scripts/build_coverage_matrix.py
```

It will report any matched mechanism names that don't exactly match the
current RQ3 registry (expected occasionally if RQ3 changed) -- these get
auto-recovered via fuzzy match if unambiguous, or dropped with a printed
warning if not; check the dropped list.

Refresh `rq5_coverage_matrix.md`'s narrative using the new stats, same
approach as Phase 5 -- the existing file's structure (headline result,
where testing concentrates, the "evaluation silos" reframing, RQ6 hand-off)
is a good template; update numbers and re-check whether findings like "88%
of matched defenses test against exactly one mechanism" still hold.

## Phase 7 -- close out

1. Update `context_integrity_sok_project_plan.md`'s deliverables checklist
   (Section 11) if any RQ's status changed.
2. If this run changed corpus size, screening criteria, or any headline
   number, add a dated entry to `rescreening_log.md` describing what changed
   and why (mirroring the existing "Addendum" entries) -- this project's
   convention is every corpus-affecting decision gets logged there, not
   silently applied.
3. Report a summary to the project lead: what criteria changed (if
   applicable), how corpus size moved, and which RQ numbers moved
   meaningfully as a result. Don't just say "done" -- say what's different.

## What this skill does NOT do

- Search for new papers, run snowballing, or download new PDFs -- that's a
  separate, much larger task (new keyword clusters, new S2/arXiv API calls,
  new full-text extraction passes on hundreds of new PDFs). If the request
  is actually "expand the corpus" rather than "re-screen the existing one,"
  say so and confirm scope before starting.
- Run RQ6's case studies -- those depend on RQ5's output but are new
  empirical work (constructing matched adversarial/incidental scenarios and
  running them against selected defenses), not a rebuild of existing
  analysis. Out of scope for this skill.
- Auto-write the qualitative discussion sections of the RQ3/RQ4/RQ5
  narrative reports -- the scripts compute the numbers; a human/Claude
  session judgment pass over what the numbers *mean* (Phase 5/6's "refresh
  the narrative" step) is still required each time, same as the numbers
  themselves needed interpretation the first time this was built.

# Context Integrity SoK — Paper Discovery, Screening & Dashboard Tool

Automates Week 1 of the project plan: search Track A (adversarial poisoning) and
Track B (incidental contamination) literatures, screen against fixed
inclusion/exclusion criteria, snowball forward and backward from the seed list,
and produce a structured paper database plus a local dashboard. See
`SRS_paper_screening_tool.md` for the full spec this implements.

## Re-screening and RQ1–RQ5 analysis

After the one-time search/snowball/full-text-extraction pass, the corpus is
re-screened and RQ1–RQ5 rebuilt via `scripts/` and the `rebuild-corpus`
Claude Code skill (`.claude/skills/rebuild-corpus/SKILL.md`) — see that file
for the full pipeline. In short: edit `config.yaml`'s `screening:` criteria,
then invoke the skill (or run `scripts/dedupe_corpus.py`,
`scripts/rescreen_corpus.py`, `scripts/rq1_taxonomy.py`,
`scripts/rq2_cross_citation.py`, `scripts/build_registry.py`,
`scripts/build_coverage_matrix.py` in that order manually). This reuses the
already-downloaded PDFs and already-extracted full-text data — it does not
re-run search or PDF download. Findings and methodology write-ups live in
`rq1_taxonomy_analysis.md` through `rq5_coverage_matrix.md` and
`rescreening_log.md` (the audit trail of every corpus-affecting correction).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in S2_API_KEY (free: semanticscholar.org/product/api)
```

`S2_API_KEY` is optional but strongly recommended — without it, Semantic
Scholar calls run on the heavily-throttled unauthenticated tier
(`rate_limit_rps_unauthenticated` in `config.yaml`).

## Configuration

All tunable behavior lives in `config.yaml` — keyword clusters, year range,
hop depth, venue list, and the auto-screening/track-signature rules. Nothing
requires a code change to adjust; re-run `python cli.py classify --force`
after editing keyword clusters or signatures to recompute tags on existing
rows.

## Commands

```bash
python cli.py init-db          # create the SQLite schema
python cli.py load-seeds       # ingest seed_papers.csv as hop-0 papers
python cli.py search           # FR-1/2: keyword search both tracks, logged
python cli.py snowball         # FR-4/5/6: backward+forward to config.hop_depth
python cli.py classify [--force]
python cli.py fetch-pdfs       # FR-9: download arXiv PDFs
python cli.py export           # FR-10: CSV/JSON export to data/exports/
python cli.py pipeline         # runs all of the above in order
python cli.py smoke-test       # network-light wiring check
```

`load-seeds` and `pipeline` accept `--offline` to skip metadata resolution
(loads raw CSV fields only — useful with no network access).

## Dashboard

```bash
streamlit run dashboard.py
```

Reads `data/context_sok.db` directly — no cloud dependency. Timeline tab
plots papers by year, colored by track, sized by citation count. Network tab
draws the citation graph with cross-track edges highlighted in red — this is
the view meant to make the RQ2 cross-citation finding (from the parent
project plan) visually obvious. Click any point/node to open its metadata
panel.

## Tests

```bash
pytest tests/
```

Unit tests only — no network calls. Covers dedup matching/merge logic,
track/screening classification rules, and upsert idempotency (the "re-running
doesn't duplicate rows" acceptance criterion).

## Notes on interpretation (see also the plan this was built from)

- `discovered_via` has a 4th value, `search`, beyond the SRS's seed/backward/
  forward — keyword-search hits that aren't part of the seed list need a home.
- `papers.seed_category` (`seed` / `competitor_sok` / NULL) is one additive
  column beyond the SRS's fixed schema, so the 11 competitor-SoK rows in
  `seed_papers.csv` stay visible in the DB/dashboard but distinguishable from
  the true ~40+15 seed papers.
- Seed and competitor_sok rows always get `screen_auto = auto_include`
  (they're already owner-curated); the rule engine still computes what it
  would have said, logged as an INFO line when it disagrees, purely as a
  sanity check — it never gates these rows.
- Snowball starts *only* from the true seed/competitor_sok papers
  (`seed_category IS NOT NULL`), matching the SRS's own "hop 0 = seeds
  themselves" definition — not from every keyword-search hit too. (An
  earlier version of this got that wrong and turned a ~51-paper BFS into a
  5,000+ paper one on the first real run — 10k+ calls just for hop 1.)
  Snowball commits after every paper's processing, not once per hop, so
  interrupting a long run doesn't lose everything back to the last hop
  boundary.
- Fan-out per paper still isn't capped beyond `hop_depth` — a highly-cited
  seed (e.g. "Lost in the Middle") can have 1,000+ citing papers, and S2's
  free-tier rate limit will throttle hard under sustained volume (expect
  429s; they're retried with backoff and logged, not fatal, but a full
  2-hop run across ~50 seeds can still take a long time). If hop-2 volume
  or runtime gets unmanageable, dial down `hop_depth` in `config.yaml`.

## Out of scope (per SRS Section 8)

Manual coding of Channel/Intent/Consequence/Defense fields, the
cross-citation *rate* computation itself, and full-text extraction of
paywalled papers. `export`'s CSV includes blank columns for the manual coding
fields so that pass can start directly from this tool's output.

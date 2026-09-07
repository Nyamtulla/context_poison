# Paper Collection Methodology — draft text for the paper

Generated 2026-08-03, from the live pipeline state at that time (see "Source
numbers" below). If the pipeline is re-run (more search, another snowball
pass, further screening), regenerate the numbers before using this text —
don't hand-edit stale figures into the paper.

## Methods paragraph (as used)

Candidate papers were identified through a combination of manually curated
seed papers and automated search and citation snowballing. We began with 51
seed papers identified during initial scoping — 40 judged directly relevant
to the two tracks under study (security-focused adversarial context
poisoning and incidental ML/AI context degradation) plus 11 closely related
surveys retained for differentiation. We then queried the Semantic Scholar
Academic Graph API and the arXiv API using 14 structured keyword clusters (7
per track, derived from established terminology in each literature),
restricted to publications from 2023 onward, yielding 5,069 additional
unique candidates after cross-source deduplication (matched by DOI, then
arXiv identifier, then fuzzy title/author similarity). From the 51 seed
papers we performed one-hop backward (reference) and forward (citation)
snowballing via the Semantic Scholar citation graph, contributing 9,826
further candidates and 38,037 recorded citation relationships among all
candidates encountered, for a total working corpus of 14,946 papers. Each
candidate was automatically screened against fixed inclusion/exclusion
criteria (requiring language indicating an LLM agent with tool use,
retrieval, memory, or autonomous operation, while excluding pure-jailbreak
and training-time-only poisoning work) and tagged by track using
search-cluster provenance combined with a curated list of track-identifying
author and method terms. Because manual dual-coder review of all 14,946
candidates was not feasible at this scale, we applied a stricter,
precision-oriented filter to select the working review corpus: a candidate
was retained if it was among the 51 originally hand-identified papers, or if
it passed the inclusion screen and explicitly named a recognized method or
author from either literature, yielding 1,007 papers for manual review.
Every search query, timestamp, hit count, and raw API response was logged to
support replication, and all automated classification decisions are
retained alongside any subsequent human corrections, keeping the full
screening history auditable.

## Alternatives not yet written up

- **Split into two paragraphs** (Collection: seeds/search/snowball —
  Screening: auto-screen + confidence filter + human review) if that fits
  the paper's section structure better than one dense paragraph.
- **PRISMA-style flow table** instead of/alongside the prose (candidates
  found → after dedup → after auto-screen → after confidence filter → after
  manual review). Ask for this if the venue/reviewers expect it.
- A sentence acknowledging the partial hop-2 snowball pass (10,975 papers,
  stopped early, kept in an archived export rather than the working corpus)
  is deliberately omitted above since it's out of scope for the corpus that
  was actually reviewed — add one if a reviewer might ask "why only 1 hop."

## Source numbers (for regenerating later)

| Quantity | Value |
|---|---|
| Seed papers (manually identified) | 51 (40 core + 11 competitor surveys) |
| Keyword clusters | 14 (7 Track A + 7 Track B) |
| APIs queried for keyword search | Semantic Scholar, arXiv |
| Unique candidates from keyword search | 5,069 |
| Snowball hop depth from seeds | 1 (backward + forward) |
| New candidates from snowball | 9,826 |
| Citation edges recorded | 38,037 |
| Total working corpus (hop ≤ 1) | 14,946 |
| High-confidence filtered pool (for manual review) | 1,007 |

Regenerate via:
```bash
python3 -c "
from src.config import load_config
from src import db, confidence
config = load_config()
conn = db.connect(config.path('db_path'))
print('total:', db.paper_count(conn))
print('by discovered_via:', dict(conn.execute('SELECT discovered_via, COUNT(*) FROM papers GROUP BY discovered_via').fetchall()))
print('citation_edges:', conn.execute('SELECT COUNT(*) FROM citation_edges').fetchone()[0])
print('working set (hop<=1):', conn.execute('SELECT COUNT(*) FROM papers WHERE hop <= 1').fetchone()[0])
print('high-confidence pool:', len(confidence.high_confidence_ids(conn, config, min_citations=0, max_hop=config.hop_depth)))
"
```

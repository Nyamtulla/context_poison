# Cross-Citation Analysis (RQ2)

Regenerated 2026-09-22 by `scripts/rq2_cross_citation.py`.

**RQ2:** Do the agent-security-poisoning literature (Track A) and the agentic-context-management/reliability literature (Track B) cite each other, or have they evolved as disconnected communities studying the same failure mode?

## Headline result

Computed over the **entire coded population** (1006 papers classified as Track A/Security or Track B/ML-AI; 20 additional papers classified as "Both"), not a sample:

| Direction | Papers citing >=1 paper from the other track | Total papers in track | Rate |
|---|---|---|---|
| Track A (Security) -> cites Track B (ML/AI) | 70 | 599 | **11.7%** |
| Track B (ML/AI) -> cites Track A (Security) | 37 | 407 | **9.1%** |

Because this is a full-population count (every paper's citation edges are resolved mechanically from the actual citation graph, not hand-sampled), no confidence interval is reported.

## By evidence grade

| Grade | Track A citing B | Track B citing A |
|---|---|---|
| B | 14/95 = 14.7% | 7/82 = 8.5% |
| C | 56/503 = 11.1% | 30/324 = 9.3% |
| D | 0/1 = 0.0% | 0/1 = 0.0% |

## Methodology note

`cites_track_a`/`cites_track_b` are computed mechanically from the real citation graph against the automated `track_auto`/`track_human` classification of every cited paper in the full underlying corpus (not just the currently-included working set) -- i.e., a paper is scored as "cites Track A" if it cites *any* paper anywhere in the graph that resolved to Track A. This is broader-coverage than a curated keyword+author signature list but inherits whatever noise exists in the automated track classification. Manual verification of a stratified sample against the automated classification is recommended before treating this as a final number for publication; see `context_integrity_sok_project_plan.md` Section 12 (threats to validity).

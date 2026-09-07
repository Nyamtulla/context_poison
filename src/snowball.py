"""Backward + forward snowballing (FR-4/5/6): BFS outward from the seed pool
to `config.hop_depth` in both directions. Every reference/citation relation
becomes a `citation_edges` row; every newly discovered paper is inserted with
discovered_via=backward/forward, hop, source_paper_id. Raw responses are
cached to disk same as search (FR-11).

The frontier starts at the true seed/competitor_sok papers (`seed_category IS
NOT NULL`), matching the SRS's own definition ("hop 0 = seeds themselves",
FR-6 "2 hops... from seeds") - NOT every `hop=0` row. An earlier version of
this module treated every keyword-search hit as an equally-valid hop-0
starting point too, which turned a ~51-paper BFS into a 5,000+ paper one
(10k+ API calls just for hop 1) the first time it ran for real. Search hits
are still valuable candidates in the pool; they just don't also need to be
snowball origins.

Commits happen after every paper's processing (both directions), not once
per whole hop - the first real run above got killed mid-hop after ~2.5 hours
and ~1,000 successful API calls, all of which were lost because nothing had
been committed yet. This makes the process safely interruptible/resumable.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from . import classify, db, dedup
from .clients.semantic_scholar import SemanticScholarClient

logger = logging.getLogger(__name__)


def cache_raw(raw_cache_dir: Path, prefix: str, raw_pages: list) -> str:
    raw_cache_dir.mkdir(parents=True, exist_ok=True)
    path = raw_cache_dir / f"{prefix}_{uuid4().hex[:12]}.json"
    with open(path, "w") as f:
        json.dump(raw_pages, f, default=str)
    return str(path)


def year_in_range(year: int | None, config) -> bool:
    if year is None:
        return True
    if year < config.start_year:
        return False
    if config.end_year and year > config.end_year:
        return False
    return True


def record_edge(conn, paper_id: str, related_id: str, direction: str) -> None:
    if direction == "backward":
        # related_id is a reference of paper_id -> paper_id cites related_id
        db.upsert_citation_edge(conn, citing_paper_id=paper_id, cited_paper_id=related_id, direction="backward")
    else:
        # related_id is a citer of paper_id -> related_id cites paper_id
        db.upsert_citation_edge(conn, citing_paper_id=related_id, cited_paper_id=paper_id, direction="forward")


def run_snowball(conn, config) -> dict:
    s2 = SemanticScholarClient(config)
    raw_cache_dir = config.path("raw_cache_dir")
    now = datetime.now(timezone.utc).isoformat()
    counts = {"backward_new": 0, "forward_new": 0, "edges": 0}

    frontier = [row["paper_id"] for row in db.all_papers(conn) if row["seed_category"]]
    visited = set(frontier)

    hop = 0
    while frontier and hop < config.hop_depth:
        next_frontier: list[str] = []
        for paper_id in frontier:
            for direction, endpoint in (("backward", "get_references"), ("forward", "get_citations")):
                try:
                    result = getattr(s2, endpoint)(paper_id)
                except Exception as exc:
                    logger.warning("S2 %s lookup failed for %s: %s", endpoint, paper_id, exc)
                    continue
                cache_raw(raw_cache_dir, f"snowball_{direction}", result["raw_pages"])

                for related in result["papers"]:
                    related_id = related.get("paper_id")
                    if not related_id:
                        continue  # can't record an edge to a paper with no ID

                    existing_id = dedup.resolve_existing_paper_id(conn, related)
                    final_id = existing_id or related_id
                    record_edge(conn, paper_id, final_id, direction)

                    if not year_in_range(related.get("year"), config):
                        continue  # edge recorded (FR-11); out-of-range paper not added to the pool (FR-2)
                    if final_id in visited:
                        continue
                    visited.add(final_id)
                    if existing_id:
                        continue  # already a known paper - edge recorded, nothing more to add

                    tags = classify.classify_paper(related.get("title"), related.get("abstract"), config)
                    record = {
                        **related,
                        "paper_id": final_id,
                        "doi": dedup.normalize_doi(related.get("doi")),
                        "track_auto": tags["track_auto"],
                        "screen_auto": tags["screen_auto"],
                        "discovered_via": direction,
                        "hop": hop + 1,
                        "source_paper_id": paper_id,
                        "discovered_query": None,
                        "seed_category": None,
                        "date_added": now,
                    }
                    db.upsert_paper(conn, record)
                    counts[f"{direction}_new"] += 1
                    next_frontier.append(final_id)
            conn.commit()  # commit after each paper's both directions - keep interruption cheap
        frontier = next_frontier
        hop += 1

    counts["edges"] = conn.execute("SELECT COUNT(*) FROM citation_edges").fetchone()[0]
    return counts

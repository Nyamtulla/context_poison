"""Keyword-seeded search across both tracks (FR-1/2), logged for
replicability (FR-11): every query's raw response is cached to disk and
logged with exact query string, API, timestamp, and hit count.

Interpretation note (see plan): the SRS's `discovered_via` enum
(seed/backward/forward) doesn't have a slot for "surfaced by a keyword
query" — this module uses a 4th value, `search`, with hop=0 and
`discovered_query` set to the cluster label that found it.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from . import classify, db, dedup
from .clients.arxiv import ArxivClient
from .clients.semantic_scholar import SemanticScholarClient

logger = logging.getLogger(__name__)


def _cache_raw(raw_cache_dir: Path, prefix: str, raw_pages: list) -> str:
    raw_cache_dir.mkdir(parents=True, exist_ok=True)
    path = raw_cache_dir / f"{prefix}_{uuid4().hex[:12]}.json"
    with open(path, "w") as f:
        json.dump(raw_pages, f, default=str)
    return str(path)


def _year_in_range(year: int | None, config) -> bool:
    if year is None:
        return True
    if year < config.start_year:
        return False
    if config.end_year and year > config.end_year:
        return False
    return True


def _run_one_variant(
    variant: str, track: str, config, s2, arxiv, conn, now: str
) -> list[tuple[dict, str]]:
    raw_cache_dir = config.path("raw_cache_dir")
    tagged: list[tuple[dict, str]] = []

    try:
        s2_result = s2.search(variant, config.start_year, config.end_year)
    except Exception as exc:
        logger.warning("S2 search failed for %r: %s", variant, exc)
        s2_result = {"papers": [], "raw_pages": [], "hit_count": 0}
    tagged.extend((p, "semantic_scholar") for p in s2_result["papers"])
    raw_path = _cache_raw(raw_cache_dir, f"s2_search_{track}", s2_result["raw_pages"])
    db.insert_search_log(
        conn, variant, track, "semantic_scholar", now, s2_result["hit_count"], raw_path
    )

    try:
        arxiv_result = arxiv.search(variant, year_start=config.start_year, year_end=config.end_year)
    except Exception as exc:
        logger.warning("arXiv search failed for %r: %s", variant, exc)
        arxiv_result = {"papers": [], "raw_pages": [], "hit_count": 0}
    tagged.extend((p, "arxiv") for p in arxiv_result["papers"])
    raw_path = _cache_raw(raw_cache_dir, f"arxiv_search_{track}", arxiv_result["raw_pages"])
    db.insert_search_log(conn, variant, track, "arxiv", now, arxiv_result["hit_count"], raw_path)

    return tagged


def run_search(conn, config) -> dict:
    s2 = SemanticScholarClient(config)
    arxiv = ArxivClient(config)
    now = datetime.now(timezone.utc).isoformat()
    counts = {"queries_run": 0, "new_papers": 0, "total_hits": 0}

    for track in ("A", "B"):
        for cluster in config.flat_clusters(track):
            query_label = cluster["query_label"]
            tagged_candidates: list[tuple[dict, str]] = []
            for variant in cluster["variants"]:
                tagged_candidates.extend(_run_one_variant(variant, track, config, s2, arxiv, conn, now))
                counts["queries_run"] += 2  # one S2 + one arXiv call per variant

            filtered = [(p, src) for p, src in tagged_candidates if _year_in_range(p.get("year"), config)]
            counts["total_hits"] += len(filtered)
            merged = dedup.canonicalize_batch(filtered)

            for paper in merged:
                if not paper.get("title"):
                    continue
                existing_id = dedup.resolve_existing_paper_id(conn, paper)
                paper_id = existing_id or paper.get("paper_id") or (
                    f"arxiv:{paper['arxiv_id']}" if paper.get("arxiv_id") else None
                )
                if not paper_id:
                    continue  # no stable canonical ID possible - skip rather than guess

                tags = classify.classify_paper(
                    paper.get("title"), paper.get("abstract"), config, query_track=track
                )
                record = {
                    **paper,
                    "paper_id": paper_id,
                    "doi": dedup.normalize_doi(paper.get("doi")),
                    "track_auto": tags["track_auto"],
                    "screen_auto": tags["screen_auto"],
                    "discovered_via": "search",
                    "hop": 0,
                    "source_paper_id": None,
                    "discovered_query": query_label,
                    "seed_category": None,
                    "date_added": now,
                }
                db.upsert_paper(conn, record)
                if not existing_id:
                    counts["new_papers"] += 1

    conn.commit()
    return counts

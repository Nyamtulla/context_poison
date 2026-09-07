"""Seed paper ingestion (SRS Section 7.1). Loads seed_papers.csv, resolves
full metadata via S2 first (external-ID lookup by arXiv/DOI), falling back to
the arXiv API and OpenAlex, and upserts every row as a hop-0 paper.
`category` (seed / competitor_sok) is preserved in the additive
`seed_category` column per the plan's interpretation note #2.
"""
from __future__ import annotations

import csv
import hashlib
import logging
from datetime import datetime, timezone

from . import classify, db, dedup
from .clients.arxiv import ArxivClient, normalize_arxiv_id
from .clients.openalex import OpenAlexClient
from .clients.semantic_scholar import SemanticScholarClient

logger = logging.getLogger(__name__)


def _looks_like_doi(value: str | None) -> bool:
    if not value:
        return False
    v = value.strip()
    return v.startswith("10.") or "doi.org" in v.lower()


def _looks_like_url(value: str | None) -> bool:
    return bool(value) and value.strip().lower().startswith("http")


def _title_hash_id(title: str) -> str:
    return "title:" + hashlib.sha1(dedup.normalize_title(title).encode()).hexdigest()[:16]


def _resolve_metadata(
    row: dict, s2: SemanticScholarClient, arxiv: ArxivClient, openalex: OpenAlexClient
) -> dict:
    """Best-effort resolution via S2 (preferred) -> arXiv/OpenAlex. Returns a
    metadata dict; may be sparse if nothing resolves (network down, bad ID)."""
    arxiv_id = normalize_arxiv_id(row.get("arxiv_id") or "")
    url_or_doi = (row.get("url_or_doi") or "").strip()
    doi = url_or_doi if _looks_like_doi(url_or_doi) else None
    resolved: dict = {}

    if arxiv_id:
        try:
            hit = s2.get_paper(f"ARXIV:{arxiv_id}")
            if hit:
                resolved = hit
        except Exception as exc:
            logger.warning("S2 lookup failed for arXiv:%s (%s)", arxiv_id, exc)
        if not resolved.get("abstract"):
            try:
                hit = arxiv.get_by_id(arxiv_id)
                if hit:
                    resolved = dedup.merge_fill_gaps(resolved, hit) if resolved else hit
            except Exception as exc:
                logger.warning("arXiv lookup failed for %s (%s)", arxiv_id, exc)
    elif doi:
        try:
            hit = s2.get_paper(f"DOI:{doi}")
            if hit:
                resolved = hit
        except Exception as exc:
            logger.warning("S2 lookup failed for DOI:%s (%s)", doi, exc)
        if not resolved.get("abstract"):
            try:
                hit = openalex.get_by_doi(doi)
                if hit:
                    resolved = dedup.merge_fill_gaps(resolved, hit) if resolved else hit
            except Exception as exc:
                logger.warning("OpenAlex lookup failed for DOI:%s (%s)", doi, exc)

    if not resolved.get("arxiv_id") and arxiv_id:
        resolved["arxiv_id"] = arxiv_id
    if not resolved.get("doi") and doi:
        resolved["doi"] = doi
    if not resolved.get("url") and _looks_like_url(url_or_doi):
        resolved["url"] = url_or_doi
    return resolved


def load_seeds(conn, config, use_network: bool = True) -> dict:
    """Returns counts: {'seed': n, 'competitor_sok': n, 'resolved': n, 'unresolved': n}."""
    csv_path = config.path("seed_csv")
    s2 = SemanticScholarClient(config)
    arxiv = ArxivClient(config)
    openalex = OpenAlexClient(config)

    counts = {"seed": 0, "competitor_sok": 0, "resolved": 0, "unresolved": 0}
    now = datetime.now(timezone.utc).isoformat()

    with open(csv_path, newline="") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        title = row["title"].strip()
        csv_track = row["track"].strip() or None
        category = row["category"].strip() or "seed"
        counts[category] = counts.get(category, 0) + 1

        resolved = _resolve_metadata(row, s2, arxiv, openalex) if use_network else {}
        if resolved.get("title") or resolved.get("abstract"):
            counts["resolved"] += 1
        else:
            counts["unresolved"] += 1

        csv_fallback = {
            "title": title,
            "authors": [row["authors"]] if row.get("authors") else [],
            "year": int(row["year"]) if row.get("year") else None,
            "arxiv_id": normalize_arxiv_id(row.get("arxiv_id") or "") or None,
            "doi": row["url_or_doi"] if _looks_like_doi(row.get("url_or_doi")) else None,
            "url": row["url_or_doi"] if _looks_like_url(row.get("url_or_doi")) else None,
        }
        candidate = dedup.merge_fill_gaps(resolved, csv_fallback)

        existing_id = dedup.resolve_existing_paper_id(conn, candidate)
        paper_id = (
            existing_id
            or resolved.get("paper_id")
            or (f"arxiv:{candidate['arxiv_id']}" if candidate.get("arxiv_id") else None)
            or _title_hash_id(title)
        )

        seed_class = classify.classify_seed(
            candidate.get("title") or title, candidate.get("abstract"), config, csv_track
        )
        if seed_class["_computed_screen_for_consistency_check"] != "auto_include":
            logger.info(
                "Seed %r: forcing auto_include (owner-curated); rule engine "
                "alone would have said %s — worth a human glance",
                title,
                seed_class["_computed_screen_for_consistency_check"],
            )

        paper = {
            **candidate,
            "doi": dedup.normalize_doi(candidate.get("doi")),
            "paper_id": paper_id,
            "track_auto": seed_class["track_auto"],
            "track_human": seed_class["track_human"],
            "screen_auto": seed_class["screen_auto"],
            "discovered_via": "seed",
            "hop": 0,
            "source_paper_id": None,
            "discovered_query": None,
            "seed_category": category,
            "date_added": now,
        }
        db.upsert_paper(conn, paper)

    conn.commit()
    return counts

"""Deduplication (SRS FR-3): match hits across queries and across sources —
DOI first, then arXiv ID, then normalized-title + fuzzy first-author — and
merge into one canonical record per paper. Field merge prefers whichever
source has more complete data, with Semantic Scholar > arXiv > OpenAlex as the
tiebreak priority when both sources have a non-empty value for a field.
"""
from __future__ import annotations

import re
from typing import Any

from rapidfuzz import fuzz

from .clients.arxiv import normalize_arxiv_id

SOURCE_PRIORITY = {"semantic_scholar": 3, "arxiv": 2, "openalex": 1}
TITLE_MATCH_THRESHOLD = 92


def normalize_title(title: str | None) -> str:
    if not title:
        return ""
    t = title.lower()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def normalize_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    d = doi.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if d.startswith(prefix):
            d = d[len(prefix):]
    return d or None


def first_author_surname(authors: list[str] | None) -> str:
    if not authors:
        return ""
    parts = authors[0].split()
    return parts[-1].lower() if parts else ""


def same_paper(a: dict[str, Any], b: dict[str, Any]) -> bool:
    doi_a, doi_b = normalize_doi(a.get("doi")), normalize_doi(b.get("doi"))
    if doi_a and doi_b:
        return doi_a == doi_b

    arxiv_a = normalize_arxiv_id(a.get("arxiv_id") or "")
    arxiv_b = normalize_arxiv_id(b.get("arxiv_id") or "")
    if arxiv_a and arxiv_b:
        return arxiv_a == arxiv_b

    title_a, title_b = normalize_title(a.get("title")), normalize_title(b.get("title"))
    if not title_a or not title_b:
        return False
    if first_author_surname(a.get("authors")) != first_author_surname(b.get("authors")):
        return False
    return fuzz.token_sort_ratio(title_a, title_b) >= TITLE_MATCH_THRESHOLD


def merge_fill_gaps(preferred: dict[str, Any], filler: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of `preferred` with any empty field backfilled from `filler`."""
    merged = dict(preferred)
    for field, val in filler.items():
        current = merged.get(field)
        is_empty = current in (None, "", []) or (isinstance(current, list) and not current)
        if is_empty and val not in (None, "", []):
            merged[field] = val
    return merged


def canonicalize_batch(
    tagged_candidates: list[tuple[dict[str, Any], str]],
) -> list[dict[str, Any]]:
    """tagged_candidates: [(paper_dict, source_name), ...] gathered in one run
    (e.g. the same keyword cluster hit via both S2 and arXiv). Returns one
    merged dict per distinct paper. O(n^2) clustering — fine at the batch
    sizes this tool operates on (hundreds per run, not millions)."""
    clusters: list[list[tuple[dict[str, Any], str]]] = []
    for cand, source in tagged_candidates:
        for cluster in clusters:
            if any(same_paper(cand, existing) for existing, _ in cluster):
                cluster.append((cand, source))
                break
        else:
            clusters.append([(cand, source)])

    merged_records = []
    for cluster in clusters:
        cluster.sort(key=lambda cs: -SOURCE_PRIORITY.get(cs[1], 0))
        merged, _ = cluster[0]
        merged = dict(merged)
        merged["doi"] = normalize_doi(merged.get("doi"))
        for cand, _source in cluster[1:]:
            merged = merge_fill_gaps(merged, cand)
        merged_records.append(merged)
    return merged_records


def resolve_existing_paper_id(conn, candidate: dict[str, Any]) -> str | None:
    """Check the DB for a paper matching `candidate` so re-runs and
    cross-stage discovery (seed list vs. search vs. snowball) reuse the same
    canonical paper_id instead of inserting a duplicate row (NFR-2)."""
    from . import db

    doi = normalize_doi(candidate.get("doi"))
    if doi:
        row = db.find_by_doi(conn, doi)
        if row:
            return row["paper_id"]

    arxiv_id = normalize_arxiv_id(candidate.get("arxiv_id") or "")
    if arxiv_id:
        row = db.find_by_arxiv_id(conn, arxiv_id)
        if row:
            return row["paper_id"]

    title_norm = normalize_title(candidate.get("title"))
    if not title_norm:
        return None
    author_key = first_author_surname(candidate.get("authors"))
    for row in db.all_papers(conn):
        if not row["title"]:
            continue
        if first_author_surname(_row_authors(row)) != author_key:
            continue
        if fuzz.token_sort_ratio(title_norm, normalize_title(row["title"])) >= TITLE_MATCH_THRESHOLD:
            return row["paper_id"]
    return None


def _row_authors(row) -> list[str]:
    import json

    raw = row["authors"] if "authors" in row.keys() else None
    if not raw:
        return []
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return []

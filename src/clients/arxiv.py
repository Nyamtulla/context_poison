"""arXiv API client — primary for arXiv-native metadata + PDF download (FR-9).

Uses the public Atom-feed query API (no key required). Search restricts to
title+abstract fields per the SRS's hard requirement (FR-1).
"""
from __future__ import annotations

import re
from typing import Any

import feedparser

from .http_utils import ThrottledClient

_ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5}|[a-z\-]+/\d{7})(v\d+)?")


def normalize_arxiv_id(raw_id: str) -> str:
    """Strip URL prefixes and version suffixes: 'https://arxiv.org/abs/2302.12173v2' -> '2302.12173'."""
    if not raw_id:
        return raw_id
    m = _ARXIV_ID_RE.search(raw_id)
    return m.group(1) if m else raw_id


def _entry_to_paper(entry: Any) -> dict[str, Any]:
    arxiv_id = normalize_arxiv_id(entry.get("id", ""))
    authors = [a.get("name") for a in entry.get("authors", []) if a.get("name")]
    year = None
    published = entry.get("published")
    if published:
        try:
            year = int(published[:4])
        except ValueError:
            year = None
    return {
        "paper_id": None,  # resolved against S2 by the caller when possible
        "title": (entry.get("title") or "").replace("\n", " ").strip(),
        "abstract": (entry.get("summary") or "").replace("\n", " ").strip(),
        "authors": authors,
        "year": year,
        "venue": entry.get("arxiv_journal_ref") or "arXiv",
        "doi": entry.get("arxiv_doi"),
        "arxiv_id": arxiv_id,
        "url": entry.get("link"),
        "citation_count": None,
    }


class ArxivClient:
    def __init__(self, config):
        api_conf = config.apis["arxiv"]
        self.base_url = api_conf["base_url"]
        self.pdf_base_url = api_conf["pdf_base_url"]
        self.client = ThrottledClient(
            rps=api_conf["rate_limit_rps"], max_retries=api_conf["max_retries"]
        )

    def search(
        self,
        query: str,
        max_results: int = 200,
        year_start: int | None = None,
        year_end: int | None = None,
    ) -> dict[str, Any]:
        search_query = f'ti:"{query}" OR abs:"{query}"'
        if year_start:
            end = f"{year_end}1231235959" if year_end else "99991231235959"
            search_query = f"({search_query}) AND submittedDate:[{year_start}01010000 TO {end}]"
        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        resp = self.client.get(self.base_url, params=params)
        resp.raise_for_status()
        raw_body = resp.text
        feed = feedparser.parse(raw_body)
        papers = [_entry_to_paper(e) for e in feed.entries]
        return {"papers": papers, "raw_pages": [raw_body], "hit_count": len(papers)}

    def get_by_id(self, arxiv_id: str) -> dict[str, Any] | None:
        arxiv_id = normalize_arxiv_id(arxiv_id)
        resp = self.client.get(self.base_url, params={"id_list": arxiv_id})
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
        if not feed.entries:
            return None
        return _entry_to_paper(feed.entries[0])

    def download_pdf(self, arxiv_id: str, dest_path) -> bool:
        """Idempotent: skips download if dest_path already exists. Returns
        True if a file is present at dest_path afterward."""
        from pathlib import Path

        dest_path = Path(dest_path)
        if dest_path.exists():
            return True
        arxiv_id = normalize_arxiv_id(arxiv_id)
        url = f"{self.pdf_base_url}/{arxiv_id}.pdf"
        resp = self.client.get(url)
        if resp.status_code != 200:
            return False
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(resp.content)
        return True

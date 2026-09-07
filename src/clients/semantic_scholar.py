"""Semantic Scholar Academic Graph API client — primary source (SRS Section 2).

Covers: keyword search (FR-1/2), backward snowball via /references (FR-4),
forward snowball via /citations (FR-5). Every call returns both normalized
paper dicts and the raw JSON page(s) so callers can cache them to disk (FR-11).
"""
from __future__ import annotations

from typing import Any

from .http_utils import ThrottledClient

DEFAULT_FIELDS = "title,abstract,authors,year,venue,externalIds,citationCount,url"
_PAGE_SIZE = 100
_REF_CIT_PAGE_SIZE = 1000


def normalize_paper(raw: dict[str, Any]) -> dict[str, Any]:
    if not raw:
        return {}
    external_ids = raw.get("externalIds") or {}
    authors = [a.get("name") for a in (raw.get("authors") or []) if a.get("name")]
    return {
        "paper_id": raw.get("paperId"),
        "title": raw.get("title"),
        "abstract": raw.get("abstract"),
        "authors": authors,
        "year": raw.get("year"),
        "venue": raw.get("venue"),
        "doi": external_ids.get("DOI"),
        "arxiv_id": external_ids.get("ArXiv"),
        "url": raw.get("url"),
        "citation_count": raw.get("citationCount"),
    }


class SemanticScholarClient:
    def __init__(self, config):
        api_conf = config.apis["semantic_scholar"]
        self.base_url = api_conf["base_url"]
        api_key = config.s2_api_key()
        rps = (
            api_conf["rate_limit_rps_authenticated"]
            if api_key
            else api_conf["rate_limit_rps_unauthenticated"]
        )
        headers = {"x-api-key": api_key} if api_key else {}
        self.client = ThrottledClient(
            rps=rps, max_retries=api_conf["max_retries"], headers=headers
        )
        self.has_key = bool(api_key)

    def search(
        self,
        query: str,
        year_start: int,
        year_end: int | None = None,
        max_results: int = 300,
        fields: str = DEFAULT_FIELDS,
    ) -> dict[str, Any]:
        year_param = f"{year_start}-{year_end}" if year_end else f"{year_start}-"
        papers: list[dict[str, Any]] = []
        raw_pages: list[dict[str, Any]] = []
        offset = 0
        total = None
        while len(papers) < max_results:
            params = {
                "query": query,
                "year": year_param,
                "fields": fields,
                "limit": min(_PAGE_SIZE, max_results - len(papers)),
                "offset": offset,
            }
            resp = self.client.get(f"{self.base_url}/paper/search", params=params)
            resp.raise_for_status()
            data = resp.json()
            raw_pages.append(data)
            batch = data.get("data", []) or []
            papers.extend(normalize_paper(p) for p in batch)
            total = data.get("total", 0)
            if not batch or offset + _PAGE_SIZE >= total:
                break
            offset += _PAGE_SIZE
        return {"papers": papers, "raw_pages": raw_pages, "hit_count": total or len(papers)}

    def get_paper(
        self, paper_id: str, fields: str = DEFAULT_FIELDS
    ) -> dict[str, Any] | None:
        resp = self.client.get(
            f"{self.base_url}/paper/{paper_id}", params={"fields": fields}
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return normalize_paper(resp.json())

    def get_references(self, paper_id: str, fields: str = DEFAULT_FIELDS) -> dict[str, Any]:
        """Backward snowball (FR-4): papers this one cites."""
        return self._get_relations(paper_id, "references", "citedPaper", fields)

    def get_citations(self, paper_id: str, fields: str = DEFAULT_FIELDS) -> dict[str, Any]:
        """Forward snowball (FR-5): papers that cite this one."""
        return self._get_relations(paper_id, "citations", "citingPaper", fields)

    def _get_relations(
        self, paper_id: str, endpoint: str, wrapper_key: str, fields: str
    ) -> dict[str, Any]:
        papers: list[dict[str, Any]] = []
        raw_pages: list[dict[str, Any]] = []
        offset = 0
        while True:
            params = {
                "fields": ",".join(f"{wrapper_key}.{f}" for f in fields.split(",")),
                "limit": _REF_CIT_PAGE_SIZE,
                "offset": offset,
            }
            resp = self.client.get(
                f"{self.base_url}/paper/{paper_id}/{endpoint}", params=params
            )
            if resp.status_code == 404:
                break
            resp.raise_for_status()
            data = resp.json()
            raw_pages.append(data)
            batch = data.get("data", []) or []
            for item in batch:
                wrapped = item.get(wrapper_key)
                if wrapped and wrapped.get("paperId"):
                    papers.append(normalize_paper(wrapped))
            if len(batch) < _REF_CIT_PAGE_SIZE:
                break
            offset += _REF_CIT_PAGE_SIZE
        return {"papers": papers, "raw_pages": raw_pages, "hit_count": len(papers)}

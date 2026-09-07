"""OpenAlex client — fallback/supplement when S2 rate-limits or is missing a
record (SRS Section 2). No key required; a contact email routes into the
faster "polite pool".
"""
from __future__ import annotations

from typing import Any

from .http_utils import ThrottledClient


def _normalize_work(raw: dict[str, Any]) -> dict[str, Any]:
    if not raw:
        return {}
    authors = [
        (a.get("author") or {}).get("display_name")
        for a in raw.get("authorships", [])
        if (a.get("author") or {}).get("display_name")
    ]
    ids = raw.get("ids", {}) or {}
    doi = ids.get("doi", "").replace("https://doi.org/", "") if ids.get("doi") else None
    venue = ((raw.get("primary_location") or {}).get("source") or {}).get("display_name")
    abstract = _reconstruct_abstract(raw.get("abstract_inverted_index"))
    return {
        "paper_id": None,
        "title": raw.get("title"),
        "abstract": abstract,
        "authors": authors,
        "year": raw.get("publication_year"),
        "venue": venue,
        "doi": doi,
        "arxiv_id": None,
        "url": raw.get("doi") or (raw.get("primary_location") or {}).get("landing_page_url"),
        "citation_count": raw.get("cited_by_count"),
    }


def _reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    if not inverted_index:
        return None
    positions: dict[int, str] = {}
    for word, idxs in inverted_index.items():
        for i in idxs:
            positions[i] = word
    return " ".join(positions[i] for i in sorted(positions))


class OpenAlexClient:
    def __init__(self, config):
        api_conf = config.apis["openalex"]
        self.base_url = api_conf["base_url"]
        self.mailto = config.openalex_contact_email()
        self.client = ThrottledClient(
            rps=api_conf["rate_limit_rps"], max_retries=api_conf["max_retries"]
        )

    def _params(self, extra: dict[str, Any]) -> dict[str, Any]:
        params = dict(extra)
        if self.mailto:
            params["mailto"] = self.mailto
        return params

    def search(
        self, query: str, year_start: int, year_end: int | None = None, max_results: int = 200
    ) -> dict[str, Any]:
        year_filter = f"from_publication_date:{year_start}-01-01"
        if year_end:
            year_filter += f",to_publication_date:{year_end}-12-31"
        papers: list[dict[str, Any]] = []
        raw_pages: list[dict[str, Any]] = []
        cursor = "*"
        while len(papers) < max_results:
            params = self._params(
                {
                    "search": query,
                    "filter": year_filter,
                    "per_page": min(200, max_results - len(papers)),
                    "cursor": cursor,
                }
            )
            resp = self.client.get(f"{self.base_url}/works", params=params)
            resp.raise_for_status()
            data = resp.json()
            raw_pages.append(data)
            batch = data.get("results", []) or []
            papers.extend(_normalize_work(w) for w in batch)
            cursor = (data.get("meta") or {}).get("next_cursor")
            if not batch or not cursor:
                break
        return {
            "papers": papers,
            "raw_pages": raw_pages,
            "hit_count": (raw_pages[0].get("meta") or {}).get("count", len(papers)) if raw_pages else 0,
        }

    def get_by_doi(self, doi: str) -> dict[str, Any] | None:
        resp = self.client.get(
            f"{self.base_url}/works/https://doi.org/{doi}", params=self._params({})
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return _normalize_work(resp.json())

"""Second-pass PDF recovery for what pass 1 (open-access APIs) could not get.

Three additional routes, none of which pass 1 tried:

  1. DOI redirect resolution. Pass 1 only applied publisher patterns when the
     stored URL already pointed at the publisher; most rows carry a Semantic
     Scholar URL instead. Resolving the DOI gives the real article page, after
     which the publisher's own PDF convention applies (MDPI `/pdf`, ACM
     `/doi/pdf/`).
  2. arXiv preprint search by title. Many IEEE/ACM papers have an arXiv
     preprint that neither S2 nor OpenAlex linked to the published DOI. A
     title match above a similarity floor is treated as the same paper.
  3. PubMed Central, for the handful of biomedical-indexed venues.

Same verification as pass 1: magic bytes plus extractable text, so a paywall's
HTML login page is never saved as a PDF.

    python scripts/fetch_missing_pdfs_pass2.py
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

import requests
from rapidfuzz import fuzz

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_missing_pdfs import PDF_DIR, is_real_pdf, try_download, UA, TIMEOUT  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
WORKLIST = REPO / "data/registries/missing_pdfs_worklist.json"
TITLE_MATCH_FLOOR = 88  # below this, assume it's a different paper


def norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", str(t or "").lower()).strip()


def resolve_doi(doi: str) -> str | None:
    try:
        r = requests.head(f"https://doi.org/{doi}", headers=UA,
                          timeout=TIMEOUT, allow_redirects=True)
        return r.url
    except Exception:
        return None


def publisher_pdf_urls(doi: str, resolved: str | None) -> list[str]:
    out = []
    if resolved:
        base = resolved.split("?")[0].rstrip("/")
        if "mdpi.com" in resolved:
            out.append(base + "/pdf")
        if "dl.acm.org" in resolved:
            out.append(f"https://dl.acm.org/doi/pdf/{doi}")
        if "ncbi.nlm.nih.gov/pmc" in resolved:
            out.append(base + "/pdf/")
        if "aclanthology.org" in resolved:
            out.append(base + ".pdf")
    if doi.startswith("10.3390"):
        out.append(f"https://www.mdpi.com/{doi.split('/', 1)[1]}/pdf")
    if doi.startswith("10.1145"):
        out.append(f"https://dl.acm.org/doi/pdf/{doi}")
    return out


def arxiv_by_title(title: str) -> str | None:
    """Search arXiv for a preprint of the same paper. Returns a PDF URL only
    when the returned title is close enough to be the same work."""
    q = urllib.parse.quote(f'ti:"{title[:180]}"')
    try:
        r = requests.get(
            f"http://export.arxiv.org/api/query?search_query={q}&max_results=3",
            headers=UA, timeout=TIMEOUT)
        if r.status_code != 200:
            return None
        entries = re.findall(r"<entry>(.*?)</entry>", r.text, re.S)
        for e in entries:
            t = re.search(r"<title>(.*?)</title>", e, re.S)
            idm = re.search(r"<id>http://arxiv.org/abs/([^<]+)</id>", e)
            if not t or not idm:
                continue
            score = fuzz.token_sort_ratio(norm_title(t.group(1)), norm_title(title))
            if score >= TITLE_MATCH_FLOOR:
                return f"https://arxiv.org/pdf/{idm.group(1)}"
    except Exception:
        return None
    return None


def main() -> None:
    data = json.loads(WORKLIST.read_text())
    todo = data["manual_download_needed"]
    print(f"pass 2 over {len(todo)} papers pass 1 could not retrieve\n")

    still, newly = [], []
    for i, p in enumerate(todo, 1):
        dest = PDF_DIR / p["save_as"]
        title = str(p.get("title") or "")[:56]
        if dest.exists() and is_real_pdf(dest):
            newly.append({**p, "source": "already-present"})
            continue

        doi = (p.get("doi") or "").strip()
        cands = []
        if doi:
            resolved = resolve_doi(doi)
            cands += [(u, "publisher") for u in publisher_pdf_urls(doi, resolved)]
        ax = arxiv_by_title(p.get("title") or "")
        if ax:
            cands.append((ax, "arxiv-title-match"))

        got = None
        for url, src in cands:
            if try_download(url, dest):
                got = src
                break
        if got:
            newly.append({**p, "source": got})
            print(f"[{i}/{len(todo)}] OK {got:18s} {title}", flush=True)
        else:
            still.append(p)
            print(f"[{i}/{len(todo)}] -- {'':18s} {title}", flush=True)
        time.sleep(0.4)

    data["fetched"] = data["fetched"] + newly
    data["manual_download_needed"] = still
    WORKLIST.write_text(json.dumps(data, indent=1))
    print(f"\npass 2 recovered: {len(newly)} | still needing manual download: {len(still)}")
    print("worklist updated:", WORKLIST)


if __name__ == "__main__":
    main()

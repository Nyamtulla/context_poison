"""Fetch PDFs for the corpus papers that never got full-text extraction.

Why these were missed: the original pipeline's pdf_fetch.py only handles
arXiv, and 125 of the 128 gaps are publisher-hosted DOIs (IEEE, ACM, MDPI,
ACL, ...). This resolves open-access locations instead of guessing, in
descending order of reliability:

  1. arXiv, when an arXiv ID (or a 10.48550 arXiv DOI) is present
  2. Semantic Scholar's `openAccessPdf` field
  3. OpenAlex's `best_oa_location` / `primary_location` PDF URL
  4. Publisher patterns for venues that are open access by policy
     (MDPI, ACL Anthology, PMC)

Every download is verified as a real PDF (magic bytes + pdftotext yielding
actual text), because paywalled endpoints commonly return a 200 with an HTML
login page, which would otherwise be saved as a "successful" PDF.

Anything not retrievable is written to a manual-download worklist with its
DOI and landing-page URL.

    python scripts/fetch_missing_pdfs.py [--limit N] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import registry_source
from src.config import load_config

REPO = Path(__file__).resolve().parent.parent
PDF_DIR = REPO / "data/papers"
DEEP = ["technical_summary", "key_result", "baselines_compared",
        "stated_limitations", "models_evaluated", "datasets_benchmarks"]
UA = {"User-Agent": "Mozilla/5.0 (compatible; academic-research-tool/1.0)"}
TIMEOUT = 45


def needs_fulltext(p: dict) -> bool:
    return not all(p.get(f) for f in DEEP)


def safe_name(p: dict) -> str:
    """Filename the extraction step will look for. Mirrors the existing
    convention (arXiv id when available) and falls back to the paper_id."""
    if p.get("arxiv_id"):
        return f"{p['arxiv_id']}.pdf"
    pid = str(p.get("paper_id") or "unknown").replace("/", "_").replace(":", "_")
    return f"{pid}.pdf"


def is_real_pdf(path: Path) -> bool:
    """A 200 response is not proof of a PDF - publisher paywalls happily
    return an HTML login page. Require the magic bytes and extractable text."""
    try:
        with open(path, "rb") as f:
            if f.read(5) != b"%PDF-":
                return False
        out = subprocess.run(["pdftotext", "-q", "-l", "2", str(path), "-"],
                             capture_output=True, timeout=60)
        return len(out.stdout.decode("utf-8", errors="ignore").strip()) > 200
    except Exception:
        return False


def try_download(url: str, dest: Path) -> bool:
    try:
        r = requests.get(url, headers=UA, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code != 200 or not r.content:
            return False
        dest.write_bytes(r.content)
        if is_real_pdf(dest):
            return True
        dest.unlink(missing_ok=True)
        return False
    except Exception:
        return False


def candidate_urls(p: dict, s2_oa: dict, oa_alex: dict) -> list[tuple[str, str]]:
    """(url, source) candidates, best-first."""
    out = []
    doi = (p.get("doi") or "").strip()
    arxiv = (p.get("arxiv_id") or "").strip()

    if arxiv:
        out.append((f"https://arxiv.org/pdf/{arxiv}", "arxiv"))
    # a 10.48550 DOI is an arXiv DOI even when the arxiv_id column is empty
    if doi.startswith("10.48550/arXiv."):
        out.append((f"https://arxiv.org/pdf/{doi.split('arXiv.')[-1]}", "arxiv-doi"))

    pid = p.get("paper_id")
    if pid in s2_oa and s2_oa[pid]:
        out.append((s2_oa[pid], "s2-openaccess"))
    if pid in oa_alex and oa_alex[pid]:
        out.append((oa_alex[pid], "openalex-oa"))

    # publishers that are open access by policy
    if doi.startswith("10.3390"):  # MDPI
        url = (p.get("url") or "").rstrip("/")
        if "mdpi.com" in url:
            out.append((url + "/pdf", "mdpi"))
    if doi.startswith("10.18653"):  # ACL Anthology
        out.append((f"https://aclanthology.org/{doi.split('/')[-1]}.pdf", "acl"))

    seen, uniq = set(), []
    for u, s in out:
        if u and u not in seen:
            seen.add(u)
            uniq.append((u, s))
    return uniq


def s2_open_access(papers: list[dict], config) -> dict:
    """Ask S2 for openAccessPdf in batches of 100."""
    out = {}
    key = config.s2_api_key()
    headers = {"x-api-key": key} if key else {}
    ids = []
    for p in papers:
        pid = p.get("paper_id") or ""
        if pid.startswith("arxiv:"):
            ids.append((p, f"ARXIV:{pid.split(':', 1)[1]}"))
        elif p.get("doi"):
            ids.append((p, f"DOI:{p['doi']}"))
        elif len(pid) == 40:
            ids.append((p, pid))
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        # S2's batch endpoint 429s readily even with a key; back off rather
        # than silently returning nothing, since OpenAlex alone misses some.
        for attempt in range(5):
            try:
                r = requests.post(
                    "https://api.semanticscholar.org/graph/v1/paper/batch",
                    params={"fields": "openAccessPdf,externalIds"},
                    json={"ids": [c[1] for c in chunk]}, headers=headers, timeout=60)
                if r.status_code == 429:
                    wait = 5 * (attempt + 1)
                    print(f"    S2 batch {i}: 429, retrying in {wait}s", flush=True)
                    time.sleep(wait)
                    continue
                if r.status_code != 200:
                    print(f"    S2 batch {i}: HTTP {r.status_code}", flush=True)
                    break
                for (p, _), rec in zip(chunk, r.json()):
                    if rec and rec.get("openAccessPdf"):
                        out[p["paper_id"]] = rec["openAccessPdf"].get("url")
                break
            except Exception as exc:
                print(f"    S2 batch {i} failed: {exc}", flush=True)
                time.sleep(3)
        time.sleep(2)
    return out


def openalex_open_access(papers: list[dict], config) -> dict:
    out = {}
    email = None
    try:
        email = config.apis.get("openalex", {}).get("contact_email_env")
        import os
        email = os.environ.get(email) if email else None
    except Exception:
        pass
    for p in papers:
        doi = (p.get("doi") or "").strip()
        if not doi:
            continue
        try:
            r = requests.get(f"https://api.openalex.org/works/https://doi.org/{doi}",
                             params={"mailto": email} if email else {},
                             headers=UA, timeout=30)
            if r.status_code != 200:
                continue
            w = r.json()
            for loc in ([w.get("best_oa_location")] + (w.get("locations") or [])):
                if loc and loc.get("pdf_url"):
                    out[p["paper_id"]] = loc["pdf_url"]
                    break
        except Exception:
            pass
        time.sleep(0.15)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    config = load_config()
    papers = [p for p in registry_source.load_papers() if needs_fulltext(p)]
    if args.limit:
        papers = papers[: args.limit]
    print(f"{len(papers)} papers lack full-text extraction\n")

    print("resolving open-access locations...")
    s2_oa = s2_open_access(papers, config)
    print(f"  Semantic Scholar reported an OA PDF for {len(s2_oa)}")
    oa_alex = openalex_open_access(papers, config)
    print(f"  OpenAlex reported an OA PDF for {len(oa_alex)}")
    print()

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    got, failed = [], []
    for i, p in enumerate(papers, 1):
        dest = PDF_DIR / safe_name(p)
        title = str(p.get("title") or "")[:58]
        if dest.exists() and is_real_pdf(dest):
            got.append({"paper_id": p["paper_id"], "path": str(dest), "source": "already-present"})
            print(f"[{i}/{len(papers)}] have   {title}", flush=True)
            continue
        cands = candidate_urls(p, s2_oa, oa_alex)
        if args.dry_run:
            print(f"[{i}/{len(papers)}] {len(cands)} candidate(s)  {title}", flush=True)
            continue
        ok = None
        for url, src in cands:
            if try_download(url, dest):
                ok = src
                break
        if ok:
            got.append({"paper_id": p["paper_id"], "path": str(dest), "source": ok})
            print(f"[{i}/{len(papers)}] OK {ok:14s} {title}", flush=True)
        else:
            failed.append({
                "paper_id": p["paper_id"], "title": p.get("title"), "doi": p.get("doi"),
                "url": p.get("url"), "year": p.get("year"), "venue": p.get("venue"),
                "screening": p.get("screening"), "save_as": safe_name(p),
                "tried": [u for u, _ in cands],
            })
            print(f"[{i}/{len(papers)}] -- no OA      {title}", flush=True)

    print(f"\nfetched: {len(got)} | still missing: {len(failed)}")
    out = REPO / "data/registries/missing_pdfs_worklist.json"
    out.write_text(json.dumps({"fetched": got, "manual_download_needed": failed}, indent=1))
    print("worklist:", out)


if __name__ == "__main__":
    main()

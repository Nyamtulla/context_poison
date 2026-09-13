"""Fetch PDFs for the papers recovered by the 2026-09-11 screening rule.

These 164 papers were discovered in the original search but never entered the
curated corpus - they failed the agent-vocabulary signal-term test and sat in
needs_review (see screening_gap_analysis.md). They therefore have no PDF and no
extracted text, and cannot be coded for RQ3/RQ4 until they do.

Reuses the verified-download helpers from fetch_missing_pdfs.py: magic-byte plus
extractable-text checks, so a paywall's HTML login page is never saved as a PDF.
115 of the 164 carry an arXiv id and come down directly; the rest need DOI
resolution and some will need manual download.

    python scripts/fetch_screening_delta_pdfs.py [--limit N]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_missing_pdfs import PDF_DIR, is_real_pdf, try_download  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
TARGETS = REPO / "data/registries/screening_delta_extraction_queue.json"
DB = REPO / "data/context_sok.db"


def safe(pid: str, title: str) -> str:
    stem = "".join(c if c.isalnum() or c in " -_" else "" for c in (title or ""))[:70].strip()
    return f"{stem.replace(' ', '_')}__{pid[:10]}.pdf" if stem else f"{pid}.pdf"


def urls_for(arxiv_id: str | None, doi: str | None, url: str | None) -> list[tuple[str, str]]:
    out = []
    if arxiv_id:
        clean = arxiv_id.replace("arXiv:", "").strip()
        out.append((f"https://arxiv.org/pdf/{clean}", "arxiv"))
        out.append((f"https://arxiv.org/pdf/{clean}v1", "arxiv-v1"))
    if doi:
        if doi.startswith("10.48550/arXiv."):
            out.append((f"https://arxiv.org/pdf/{doi.split('arXiv.')[1]}", "arxiv-via-doi"))
        if doi.startswith("10.3390"):
            out.append((f"https://www.mdpi.com/{doi.split('/', 1)[1]}/pdf", "mdpi"))
        if doi.startswith("10.1145"):
            out.append((f"https://dl.acm.org/doi/pdf/{doi}", "acm"))
        if doi.startswith("10.18653"):
            out.append((f"https://aclanthology.org/{doi.split('/')[-1]}.pdf", "acl"))
    if url and url.endswith(".pdf"):
        out.append((url, "recorded-url"))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    targets = json.loads(TARGETS.read_text())["papers"]
    if args.limit:
        targets = targets[: args.limit]
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    got, manual = [], []
    for i, p in enumerate(targets, 1):
        cur.execute("SELECT title, arxiv_id, doi, url FROM papers WHERE paper_id=?", (p["paper_id"],))
        row = cur.fetchone()
        if not row:
            manual.append({**p, "reason": "not in DB"})
            continue
        title, arxiv_id, doi, url = row
        dest = PDF_DIR / safe(p["paper_id"], title)
        if dest.exists() and is_real_pdf(dest):
            got.append({**p, "pdf_local_path": str(dest), "source": "already-present"})
            continue
        src = None
        for u, kind in urls_for(arxiv_id, doi, url):
            if try_download(u, dest):
                src = kind
                break
        if src:
            got.append({**p, "pdf_local_path": str(dest), "source": src})
            print(f"[{i}/{len(targets)}] OK   {src:14} {(title or '')[:56]}", flush=True)
        else:
            manual.append({**p, "reason": "no working URL", "doi": doi, "arxiv_id": arxiv_id})
            print(f"[{i}/{len(targets)}] --   {'':14} {(title or '')[:56]}", flush=True)
        time.sleep(0.35)
    conn.close()

    out = REPO / "data/registries/screening_delta_pdf_status.json"
    out.write_text(json.dumps({"generated": "2026-09-13", "fetched": got,
                               "manual_download_needed": manual}, indent=1) + "\n")
    print(f"\nfetched: {len(got)} | needs manual download: {len(manual)}")
    print("wrote", out)


if __name__ == "__main__":
    main()

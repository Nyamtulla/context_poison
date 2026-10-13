"""Fetch the last PDFs the corpus is missing, by every free route available.

An earlier attempt trusted Semantic Scholar's `openAccessPdf` field and got 14
HTML landing pages named .pdf. Every download here is validated - it must
start with %PDF- and exceed 20 KB - and a failure is recorded as a failure.

Routes, cheapest and most reliable first:
  1. arXiv, when the paper has an arXiv id. An exact, unauthenticated PDF.
  2. OpenAlex `best_oa_location` / `locations`, which indexes open-access
     copies and, unlike the S2 field, distinguishes a PDF url from a landing
     page. No key or email required.
  3. The DOI itself, for publishers that serve a PDF directly.

Whatever fails stays on the manual worklist. Most of the remainder are IEEE,
which no free route reaches.
"""
from __future__ import annotations

import json
import pathlib
import sqlite3
import sys
import time
import urllib.request

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from rename_pdfs_to_titles import sanitize   # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (compatible; context-sok/1.0)"}
MIN_BYTES = 20_000


def get(url, timeout=60):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers=UA), timeout=timeout).read()


def is_pdf(b): return b[:5] == b"%PDF-" or b"%PDF-" in b[:2048]


def openalex_pdf_urls(doi):
    try:
        d = json.loads(get(f"https://api.openalex.org/works/doi:{doi}", 40))
    except Exception:
        return []
    urls = []
    best = d.get("best_oa_location") or {}
    if best.get("pdf_url"):
        urls.append(best["pdf_url"])
    for loc in d.get("locations") or []:
        if loc.get("pdf_url") and loc["pdf_url"] not in urls:
            urls.append(loc["pdf_url"])
    if (d.get("open_access") or {}).get("oa_url"):
        u = d["open_access"]["oa_url"]
        if u not in urls:
            urls.append(u)
    return urls


def main():
    ids = json.loads(pathlib.Path(sys.argv[1]).read_text())
    pe = sqlite3.connect(REPO / "data" / "paper_explorer.db")
    q = ",".join("?" * len(ids))
    rows = pe.execute(
        f"select paper_id,title,doi,arxiv_id from paper where paper_id in ({q})", ids
    ).fetchall()
    got, failed = [], []
    for pid, title, doi, ax in rows:
        dest = REPO / "data" / "papers" / f"{sanitize(title, pid)}.pdf"
        if dest.exists():
            print(f"  have   {title[:60]}"); continue
        cands = []
        if ax:
            cands += [f"https://arxiv.org/pdf/{ax}", f"https://arxiv.org/pdf/{ax}v1"]
        if doi:
            cands += openalex_pdf_urls(doi)
            cands.append(f"https://doi.org/{doi}")
        ok = False
        for url in cands:
            try:
                data = get(url)
            except Exception:
                continue
            if is_pdf(data) and len(data) >= MIN_BYTES:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                pe.execute("update paper set pdf_local_path=? where paper_id=?",
                           (str(dest.relative_to(REPO)), pid))
                pe.commit()
                got.append((pid, title, url, len(data)))
                print(f"  OK     {title[:52]:<54} {len(data)//1024}KB  via {url[:46]}")
                ok = True
                break
            time.sleep(0.5)
        if not ok:
            failed.append((pid, title, doi or ax or "no id"))
            print(f"  FAIL   {title[:52]:<54} {len(cands)} routes tried")
        time.sleep(1.0)
    print(f"\n  fetched {len(got)}, still missing {len(failed)}")
    if failed:
        print("  remaining (manual / library access):")
        for _, t, d in failed:
            print(f"    {t[:62]:<64} {d}")


if __name__ == "__main__":
    main()

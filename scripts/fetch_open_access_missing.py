"""Download the open-access copies found for the missing-PDF papers.

Only the papers whose S2 record carries an openAccessPdf url. Every download
is validated before it counts: a link that returns an HTML landing page or a
truncated file is a failure, not a PDF, and silently keeping one would put a
file on disk that the verification team opens and cannot read.

On success the file is saved under the corpus title convention and
`pdf_local_path` is set, so the paper stops being abstract-only.
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
WORK = REPO / "verification" / "missing_pdf_worklist.json"
DB = REPO / "data" / "paper_explorer.db"
UA = {"User-Agent": "Mozilla/5.0 (compatible; context-sok-fetch/1.0)"}
MIN_BYTES = 20_000


def looks_like_pdf(b: bytes) -> bool:
    return b[:5] == b"%PDF-" or b"%PDF-" in b[:2048]


def main() -> None:
    papers = json.loads(WORK.read_text())["papers"]
    todo = [p for p in papers if p.get("open_access_pdf")]
    print(f"{len(todo)} papers with an open-access link\n", flush=True)

    con = sqlite3.connect(DB)
    ok, bad = [], []
    for p in todo:
        dest = REPO / p["save_as"]
        if dest.exists():
            print(f"  have   {dest.name[:70]}")
            continue
        try:
            req = urllib.request.Request(p["open_access_pdf"], headers=UA)
            with urllib.request.urlopen(req, timeout=90) as r:
                data = r.read()
            if not looks_like_pdf(data):
                bad.append((p, f"not a PDF ({data[:16]!r})"))
                print(f"  SKIP   {p['title'][:56]:<58} not a PDF")
            elif len(data) < MIN_BYTES:
                bad.append((p, f"too small ({len(data)} bytes)"))
                print(f"  SKIP   {p['title'][:56]:<58} {len(data)} bytes")
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                con.execute("update paper set pdf_local_path=? where paper_id=?",
                            (p["save_as"], p["paper_id"]))
                con.commit()
                ok.append(p)
                print(f"  OK     {dest.name[:70]}  ({len(data)//1024} KB)")
        except Exception as e:
            bad.append((p, f"{type(e).__name__}: {str(e)[:60]}"))
            print(f"  FAIL   {p['title'][:56]:<58} {type(e).__name__}")
        time.sleep(1.0)

    print(f"\n  downloaded {len(ok)}, failed {len(bad)}")
    if bad:
        print("  failures stay on the library worklist:")
        for p, why in bad:
            print(f"    - {p['title'][:60]:<62} {why}")
    con.close()


if __name__ == "__main__":
    main()

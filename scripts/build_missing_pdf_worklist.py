"""Worklist for the included papers that have no PDF.

47 of the 1,026 included papers were coded from their abstract alone, because
44 of them are IEEE/paywalled and only 2 are on arXiv - the automated fetcher
could not reach them. Those are the corpus's weakest codings and they skew
Security (79% vs 57% in the full-text group), so recovering them is bounded,
high-value work.

Before handing anyone a list, this asks Semantic Scholar whether an
open-access copy exists: some paywalled-looking papers have a free mirror, and
anything recovered that way costs nobody a library trip. Whatever is left gets
a row with a resolvable link.

No credentials and no personal data are sent anywhere - the S2 graph API is
queried anonymously, which is the same service the corpus was built from.
"""
from __future__ import annotations

import json
import pathlib
import sqlite3
import sys
import time
import urllib.error
import urllib.request

REPO = pathlib.Path(__file__).resolve().parent.parent
DB = REPO / "data" / "paper_explorer.db"
OUT_JSON = REPO / "verification" / "missing_pdf_worklist.json"
OUT_XLSX = REPO / "verification" / "missing_pdf_worklist.xlsx"
S2 = "https://api.semanticscholar.org/graph/v1/paper/batch"
UA = {"User-Agent": "context-sok-worklist", "Content-Type": "application/json"}

FREETEXT = ["models_evaluated", "datasets_benchmarks", "key_result",
            "baselines_compared", "threat_model", "stated_limitations",
            "technical_summary"]


def s2_batch(ids: list[str]) -> dict:
    """Ask S2 for an open-access PDF link. Anonymous, so back off politely."""
    out = {}
    for i in range(0, len(ids), 25):
        chunk = ids[i:i + 25]
        body = json.dumps({"ids": chunk}).encode()
        url = f"{S2}?fields=title,externalIds,openAccessPdf,isOpenAccess"
        for attempt in range(4):
            try:
                req = urllib.request.Request(url, data=body, headers=UA, method="POST")
                with urllib.request.urlopen(req, timeout=60) as r:
                    for pid, rec in zip(chunk, json.loads(r.read().decode())):
                        if rec:
                            out[pid] = rec
                break
            except urllib.error.HTTPError as e:
                if e.code in (429, 503):
                    time.sleep(5 * (attempt + 1))
                    continue
                print(f"  S2 error {e.code} on chunk {i//25}", file=sys.stderr)
                break
            except Exception as e:
                print(f"  S2 {type(e).__name__} on chunk {i//25}", file=sys.stderr)
                time.sleep(3)
        time.sleep(1.5)
    return out


def publisher_link(doi: str | None, arxiv: str | None) -> tuple[str, str]:
    if arxiv:
        return "arXiv", f"https://arxiv.org/abs/{arxiv}"
    if not doi:
        return "none", ""
    d = doi.strip()
    if d.startswith("10.1109/"):
        return "IEEE Xplore", f"https://doi.org/{d}"
    if d.startswith("10.1145/"):
        return "ACM DL", f"https://doi.org/{d}"
    return "DOI", f"https://doi.org/{d}"


def main() -> None:
    con = sqlite3.connect(DB)
    rows = con.execute(f"""
        select paper_id, title, year, venue, arxiv_id, doi, url, citation_count,
               track, role, channel, consequence, {', '.join(FREETEXT)}
        from paper
        where screening='Include'
          and (pdf_local_path is null or trim(pdf_local_path)='')
    """).fetchall()
    cols = ["paper_id", "title", "year", "venue", "arxiv_id", "doi", "url",
            "citations", "track", "role", "channel", "consequence"] + FREETEXT
    recs = [dict(zip(cols, r)) for r in rows]
    print(f"{len(recs)} included papers without a PDF", flush=True)

    sample = set()
    sd = REPO / "verification" / "sample_design.json"
    if sd.exists():
        sample = {s["paper_id"] for s in json.loads(sd.read_text())["sample"]}

    print("asking Semantic Scholar for open-access copies...", flush=True)
    s2 = s2_batch([r["paper_id"] for r in recs])

    from rename_pdfs_to_titles import sanitize
    out = []
    for r in recs:
        rec = s2.get(r["paper_id"], {}) or {}
        oa = (rec.get("openAccessPdf") or {}).get("url") or ""
        kind, link = publisher_link(r["doi"], r["arxiv_id"])
        empty = [f for f in FREETEXT if not (r.get(f) or "").strip()]
        out.append({
            "paper_id": r["paper_id"],
            "title": r["title"],
            "year": r["year"], "venue": r["venue"],
            "citations": r["citations"] or 0,
            "track": r["track"], "role": r["role"],
            "channel": r["channel"], "consequence": r["consequence"],
            "doi": r["doi"] or "", "arxiv_id": r["arxiv_id"] or "",
            "access_route": "OPEN ACCESS" if oa else kind,
            "link": oa or link or r["url"] or "",
            "open_access_pdf": oa,
            "save_as": f"data/papers/{sanitize(r['title'], r['paper_id'])}.pdf",
            "in_verification_sample": "YES" if r["paper_id"] in sample else "",
            "empty_fields": ", ".join(empty),
        })

    out.sort(key=lambda r: (r["access_route"] != "OPEN ACCESS", -r["citations"]))
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(
        {"generated": "2026-10-12",
         "note": "Included papers with no local PDF. Their taxonomy fields were "
                 "coded from the abstract alone; their free-text fields are empty.",
         "papers": out}, indent=1))

    import openpyxl
    from openpyxl.styles import Font, PatternFill
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "to fetch"
    head = ["#", "access_route", "link", "title", "year", "venue", "citations",
            "track", "role", "in_verification_sample", "doi", "arxiv_id",
            "save_as", "paper_id", "fetched?"]
    ws.append(head)
    for c in ws[1]:
        c.font = Font(bold=True); c.fill = PatternFill("solid", fgColor="DDDDDD")
    ws.freeze_panes = "A2"
    for i, r in enumerate(out, start=1):
        ws.append([i, r["access_route"], r["link"], r["title"][:110], r["year"],
                   (r["venue"] or "")[:46], r["citations"], r["track"], r["role"],
                   r["in_verification_sample"], r["doi"], r["arxiv_id"],
                   r["save_as"], r["paper_id"], ""])
    for col, w in zip("ABCDEFGHIJKLMNO",
                      [4, 14, 54, 66, 6, 40, 10, 10, 10, 20, 34, 12, 70, 42, 10]):
        ws.column_dimensions[col].width = w
    ws.auto_filter.ref = f"A1:O{len(out) + 1}"
    wb.save(OUT_XLSX)

    n_oa = sum(1 for r in out if r["open_access_pdf"])
    print(f"\n  open-access copy found : {n_oa}")
    print(f"  needs library access   : {len(out) - n_oa}")
    print(f"  in the verification set: {sum(1 for r in out if r['in_verification_sample'])}")
    print(f"\nwrote {OUT_XLSX.relative_to(REPO)}")
    print(f"wrote {OUT_JSON.relative_to(REPO)}")


if __name__ == "__main__":
    sys.path.insert(0, str(REPO / "scripts"))
    main()

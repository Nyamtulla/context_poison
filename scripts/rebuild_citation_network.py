"""Rebuild the corpus citation network from the PDFs' own reference lists.

The existing `citation_edges` table comes from the Semantic Scholar graph API,
whose coverage of this corpus is poor: `citation_graph_isolates.md` flagged 118
papers as citing nothing in the corpus, and title-matching the PDFs showed 39
of them do cite it, one by 27 references. A third of the "isolates" were
artifacts of missing edges.

This reads each PDF's reference section and matches corpus titles inside it.
Three outcomes per paper, and keeping them distinct is the whole point:

    cites_n > 0     engages the corpus, with the list of what it cites
    cites_n == 0    read the references, found nothing from the corpus
    unknown         no reference section could be extracted - NOT an isolate,
                    and collapsing these two is how a measurement error becomes
                    a deletion

Matching is on a contiguous slice of the normalised title. An earlier version
scored "80% of the title's distinctive words appear anywhere in the reference
section" and returned 174 corpus citations for a six-page paper, because common
words co-occur by chance across sixty references. Reference lists print titles
contiguously; this matches the way the data is actually written.
"""
from __future__ import annotations

import json
import pathlib
import re
import sqlite3
import sys
import time

REPO = pathlib.Path(__file__).resolve().parent.parent
DB = REPO / "data" / "paper_explorer.db"
OUT_JSON = REPO / "data" / "registries" / "citation_network_fulltext.json"

import pymupdf  # noqa: E402

REF_HEAD = re.compile(r"\n\s*(references|bibliography|works cited|"
                      r"r\s?e\s?f\s?e\s?r\s?e\s?n\s?c\s?e\s?s)\s*\n", re.I)
MIN_PHRASE = 28
PHRASE_WORDS = 9


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())


def phrase(title: str) -> str:
    return " ".join(w for w in norm(title).split()[:PHRASE_WORDS] if w)


def ref_section(full: str) -> str:
    """Last 'References' heading wins - papers cite the word in their body."""
    hits = list(REF_HEAD.finditer(full))
    if not hits:
        return ""
    return full[hits[-1].end():]


def main() -> None:
    con = sqlite3.connect(DB)
    rows = con.execute(
        "select paper_id, title, track, screening, pdf_local_path, citation_count "
        "from paper where pdf_local_path is not null and trim(pdf_local_path)!=''"
    ).fetchall()
    print(f"{len(rows)} papers with a PDF", flush=True)

    # match targets: the included corpus
    targets = []
    for pid, title, track, screening, cites in con.execute(
            "select paper_id, title, track, screening, citation_count from paper "
            "where screening='Include'"):
        ph = phrase(title)
        if len(ph) >= MIN_PHRASE:
            targets.append((pid, ph, title, track, cites or 0))
    print(f"{len(targets)} included titles usable as match targets "
          f"(need >= {MIN_PHRASE} chars)\n", flush=True)

    edges, per_paper, t0 = [], [], time.time()
    for i, (pid, title, track, screening, pdf, cites) in enumerate(rows, 1):
        rec = {"paper_id": pid, "title": title, "track": track,
               "screening": screening}
        try:
            doc = pymupdf.open(REPO / pdf)
            full = "\n".join(doc[j].get_text() for j in range(doc.page_count))
            doc.close()
        except Exception as e:
            rec.update(state="unreadable", error=f"{type(e).__name__}")
            per_paper.append(rec)
            continue
        refs = ref_section(full)
        if len(refs) < 300:
            rec.update(state="unknown", ref_chars=len(refs),
                       note="no extractable reference section")
            per_paper.append(rec)
            continue
        rn = re.sub(r"\s+", " ", norm(refs))
        hits = [t for t in targets if t[0] != pid and t[1] in rn]
        for tpid, _ph, ttitle, ttrack, _c in hits:
            edges.append({"citing": pid, "cited": tpid,
                          "citing_track": track, "cited_track": ttrack})
        rec.update(state="read", ref_chars=len(refs), cites_n=len(hits),
                   cites=[h[0] for h in hits])
        per_paper.append(rec)
        if i % 100 == 0:
            print(f"  {i}/{len(rows)}  ({time.time()-t0:.0f}s)  "
                  f"edges so far {len(edges)}", flush=True)

    read = [r for r in per_paper if r.get("state") == "read"]
    unknown = [r for r in per_paper if r.get("state") in ("unknown", "unreadable")]
    iso = [r for r in read if r["cites_n"] == 0]
    OUT_JSON.write_text(json.dumps(
        {"generated": "2026-10-13",
         "method": "reference sections read from the PDFs; corpus titles matched "
                   "as a contiguous normalised phrase",
         "n_pdfs": len(rows), "n_targets": len(targets),
         "n_edges": len(edges),
         "n_read": len(read), "n_unknown": len(unknown), "n_isolated": len(iso),
         "papers": per_paper, "edges": edges}, indent=1))

    print(f"\n  reference list read   : {len(read)}")
    print(f"  no reference section  : {len(unknown)}   <- UNKNOWN, not isolated")
    print(f"  cite >=1 corpus paper : {len(read)-len(iso)}")
    print(f"  cite 0 corpus papers  : {len(iso)}")
    print(f"  edges                 : {len(edges)}")
    print(f"\nwrote {OUT_JSON.relative_to(REPO)}")


if __name__ == "__main__":
    main()

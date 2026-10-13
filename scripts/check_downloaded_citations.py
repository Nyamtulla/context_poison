"""Do these papers cite our corpus? Measured from their own reference lists.

The project already learned that the citation-isolate question is answered very
differently depending on where the edges come from. `citation_graph_isolates.md`
flagged 118 papers as citing nothing in the corpus from the Semantic Scholar
edge table; matching titles inside the actual PDFs showed 39 of them DO cite
it, one by 27 references. The API's edge coverage is the artifact, not the
papers' isolation.

So for these 31, where we now hold the full text, the reference list is read
from the PDF directly and matched against corpus titles. That is evidence about
the paper. An empty result from the API would not have been.
"""
from __future__ import annotations

import json
import pathlib
import re
import sqlite3
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
SRC = REPO / "verification" / "downloaded_papers"
OUT = REPO / "verification" / "downloaded_citations.json"

import pymupdf  # noqa: E402

STOP = {"the", "of", "a", "an", "and", "for", "in", "on", "to", "with", "from",
        "is", "are", "via", "using", "towards", "toward", "large", "language",
        "models", "model", "llm", "llms"}


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())


def phrase(title: str) -> str:
    """A contiguous, distinctive slice of the normalised title.

    An earlier version matched on "80% of the title's distinctive words appear
    anywhere in the reference section" and returned 174 corpus citations for a
    six-page paper - nonsense, because scattered common words co-occur by
    chance across sixty references. Reference lists print titles contiguously,
    so matching a contiguous slice is both truer to the data and far stricter.
    """
    words = [w for w in norm(title).split() if w]
    return " ".join(words[:9])


def main() -> None:
    con = sqlite3.connect(REPO / "data" / "paper_explorer.db")
    corpus = con.execute(
        "select paper_id, title, track, citation_count from paper "
        "where screening='Include'").fetchall()
    # index by a distinctive key phrase so matching is cheap and precise
    idx = []
    for pid, title, track, cites in corpus:
        ph = phrase(title)
        # a slice too short is not distinctive enough to be evidence
        if len(ph) >= 28:
            idx.append((pid, title, track, cites or 0, ph))
    print(f"corpus titles indexed: {len(idx)}\n", flush=True)

    out = []
    for p in sorted(SRC.glob("*.pdf")):
        doc = pymupdf.open(p)
        full = "\n".join(doc[i].get_text() for i in range(doc.page_count))
        doc.close()
        m = re.search(r"\n\s*references\b", full.lower())
        refs = full[m.end():] if m else ""
        refs_n = re.sub(r"\s+", " ", norm(refs))
        hits = []
        for pid, title, track, cites, ph in idx:
            if ph in refs_n:
                hits.append({"paper_id": pid, "title": title, "track": track,
                             "citations": cites})
        rec = {"file": p.name, "has_reference_section": bool(m),
               "ref_chars": len(refs), "n_corpus_citations": len(hits),
               "cites": sorted(hits, key=lambda h: -h["citations"])[:12]}
        out.append(rec)
        flag = "" if hits else "   <-- cites nothing in the corpus"
        print(f"  {len(hits):>3}  {p.name[:70]:<72}{flag}", flush=True)

    OUT.write_text(json.dumps(out, indent=1))
    iso = [r for r in out if r["n_corpus_citations"] == 0]
    norefs = [r for r in out if not r["has_reference_section"]]
    print(f"\n  {len(out)} papers; {len(iso)} cite nothing in the corpus")
    print(f"  of those, {len(norefs)} have no extractable reference section at all")
    print(f"wrote {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()

"""Citation network v2: identifiers first, then titles, with PDF text repaired.

v1 matched a 9-word contiguous slice of the title and found 4,838 edges, but
missed 40 papers where Semantic Scholar had an edge. Diagnosing those three
ways showed three different causes, and v2 addresses each:

  * the title was present at 5 words but not 9 - reference lists truncate
    titles and PDFs break words across lines, so a long phrase is brittle.
    v2 matches a 6-word phrase and repairs line-break hyphenation first.
  * the title was absent but the reference section carried 8 arXiv IDs.
    An arXiv ID is an exact identifier and was simply being ignored. v2
    matches arXiv IDs and DOIs before falling back to titles.
  * neither - S2 may be wrong, or the reference is formatted beyond reach.
    Those stay unmatched, and that is the honest outcome.

Every edge records HOW it was found (`arxiv`, `doi`, `title`) so precision can
be audited per method rather than taken on trust. The final network is the
union with the S2 edge table, each edge labelled by source, because the two
sources demonstrably miss different things.
"""
from __future__ import annotations

import json
import pathlib
import re
import sqlite3
import time

REPO = pathlib.Path(__file__).resolve().parent.parent
PE = REPO / "data" / "paper_explorer.db"
CS = REPO / "data" / "context_sok.db"
OUT = REPO / "data" / "registries" / "citation_network_v3.json"

import pymupdf  # noqa: E402

REF_HEAD = re.compile(r"\n\s*(references|bibliography|works cited)\s*\n", re.I)
ARXIV = re.compile(r"(?:arxiv[:\s/]*|abs/)(\d{4}\.\d{4,5})", re.I)
DOI = re.compile(r"\b(10\.\d{4,9}/[-._;()/:a-z0-9]+)", re.I)
MIN_TIGHT_CHARS = 26          # on the space-free form
MAX_PHRASE_WORDS = 14


def fix_text(t: str) -> str:
    """Only ligatures need repairing once matching is space-free."""
    return t.replace("ﬁ", "fi").replace("ﬂ", "fl")


def tight(s: str) -> str:
    """Strip everything but letters and digits.

    Matching on a space-free form makes hyphenation, line wrapping and
    spacing irrelevant together. The previous attempt repaired each
    separately: it deleted "-\\n", which turned a wrapped "Game-\\nTheoretic"
    into "GameTheoretic" and stopped it matching the title's "game
    theoretic", silently losing 107 edges that the first version had found -
    including 42 to "LLMs Can Be Easily Distracted by Irrelevant Context".
    """
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())).strip()


def build_phrases(titles):
    """Shortest tight prefix that is long enough AND unique in the corpus.

    Uniqueness replaces v2's hand-written "generic prefix" blocklist, which
    dropped "Large Language Models Can Be Easily Distracted..." outright and
    cost 42 real edges. A generic opening is only a problem when it is
    ambiguous, and ambiguity is measurable.
    """
    cands = {}
    for pid, t in titles:
        words = norm(t).split()
        for k in range(4, MAX_PHRASE_WORDS + 1):
            ph = tight(" ".join(words[:k]))
            if len(ph) >= MIN_TIGHT_CHARS:
                cands.setdefault(pid, []).append(ph)
        if pid not in cands and words:
            cands[pid] = [tight(" ".join(words))]
    # dedupe within a paper first. A short title's prefixes all collapse to
    # the same string once k exceeds its word count, and counting those
    # duplicates as collisions made 14 titles permanently unmatchable -
    # including "LLMs Get Lost In Multi-Turn Conversation", which cost 23 real
    # edges. A paper cannot collide with itself.
    cands = {pid: list(dict.fromkeys(phs)) for pid, phs in cands.items()}
    counts = {}
    for pid, phs in cands.items():
        for ph in phs:
            counts[ph] = counts.get(ph, 0) + 1
    out = {}
    for pid, phs in cands.items():
        pick = next((ph for ph in phs if counts[ph] == 1), None)
        if pick:
            out[pick] = pid
    return out


def ref_section(full: str) -> str:
    hits = list(REF_HEAD.finditer(full))
    return full[hits[-1].end():] if hits else ""


def main() -> None:
    pe = sqlite3.connect(PE)
    rows = pe.execute(
        "select paper_id, title, track, screening, pdf_local_path from paper "
        "where pdf_local_path is not null and trim(pdf_local_path)!=''").fetchall()

    by_arxiv, by_doi, meta, title_rows = {}, {}, {}, []
    for pid, title, track, screening, ax, doi in pe.execute(
            "select paper_id,title,track,screening,arxiv_id,doi from paper "
            "where screening='Include'"):
        meta[pid] = {"title": title, "track": track}
        if ax:
            by_arxiv[ax.strip().lower()] = pid
        if doi:
            by_doi[doi.strip().lower()] = pid
        title_rows.append((pid, title))
    by_phrase = build_phrases(title_rows)
    print(f"{len(rows)} PDFs | targets: {len(by_arxiv)} arXiv, {len(by_doi)} DOI, "
          f"{len(by_phrase)} unique title phrases of {len(title_rows)} titles\n",
          flush=True)
    phrases = list(by_phrase.items())

    edges, per_paper, t0 = [], [], time.time()
    for i, (pid, title, track, screening, pdf) in enumerate(rows, 1):
        rec = {"paper_id": pid, "title": title, "track": track, "screening": screening}
        try:
            doc = pymupdf.open(REPO / pdf)
            full = "\n".join(doc[j].get_text() for j in range(doc.page_count))
            doc.close()
        except Exception as e:
            rec.update(state="unreadable", error=type(e).__name__)
            per_paper.append(rec); continue
        refs_raw = ref_section(full)
        if len(refs_raw) < 300:
            rec.update(state="unknown", ref_chars=len(refs_raw))
            per_paper.append(rec); continue
        refs = fix_text(refs_raw)
        refs_t = tight(refs)

        found = {}
        for a in set(m.group(1) for m in ARXIV.finditer(refs)):
            t = by_arxiv.get(a.lower())
            if t and t != pid:
                found[t] = "arxiv"
        for dd in set(m.group(1).rstrip(".,);") for m in DOI.finditer(refs)):
            t = by_doi.get(dd.lower())
            if t and t != pid and t not in found:
                found[t] = "doi"
        for ph, t in phrases:
            if t != pid and t not in found and ph in refs_t:
                found[t] = "title"

        for t, how in found.items():
            edges.append({"citing": pid, "cited": t, "method": how,
                          "citing_track": track, "cited_track": meta[t]["track"]})
        rec.update(state="read", ref_chars=len(refs), cites_n=len(found),
                   cites=sorted(found), by_method={
                       m: sum(1 for v in found.values() if v == m)
                       for m in ("arxiv", "doi", "title")})
        per_paper.append(rec)
        if i % 200 == 0:
            print(f"  {i}/{len(rows)} ({time.time()-t0:.0f}s) edges {len(edges)}",
                  flush=True)

    read = [r for r in per_paper if r.get("state") == "read"]
    iso = [r for r in read if r["cites_n"] == 0]
    bym = {m: sum(1 for e in edges if e["method"] == m)
           for m in ("arxiv", "doi", "title")}
    OUT.write_text(json.dumps(
        {"generated": "2026-10-13", "version": 3,
         "method": "arXiv id, then DOI, then the shortest unique space-free title "
                   "prefix; matching ignores spacing, hyphenation and line wraps",
         "n_pdfs": len(rows), "n_read": len(read),
         "n_unknown": len(per_paper) - len(read),
         "n_isolated": len(iso), "n_edges": len(edges), "edges_by_method": bym,
         "papers": per_paper, "edges": edges}, indent=1))
    print(f"\n  read {len(read)}, unknown {len(per_paper)-len(read)}")
    print(f"  edges {len(edges)}  by method: {bym}")
    print(f"  cite 0 corpus papers: {len(iso)}")
    print(f"wrote {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()

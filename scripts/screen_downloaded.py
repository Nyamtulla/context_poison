"""Extract the readable parts of the newly downloaded PDFs for a relevance pass.

These 31 papers were fetched by hand from the missing-PDF worklist. Until now
they were coded from their abstracts alone, which is why they are the corpus's
weakest rows. This pulls the text a human (or I) actually needs to judge
relevance - abstract, introduction, and conclusion - rather than the whole
paper, because those three carry the scope decision and the rest does not.

Writes one JSON per paper plus a combined file. No judgement is made here; the
decision is recorded separately so the evidence and the call stay apart.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
SRC = REPO / "verification" / "downloaded_papers"
OUT = REPO / "verification" / "downloaded_text.json"

import pymupdf  # noqa: E402


def page_text(doc, i):
    try:
        return doc[i].get_text()
    except Exception:
        return ""


def section(txt: str, names, limit=3000) -> str:
    """Grab from the first heading that matches until the next big heading."""
    low = txt.lower()
    for nm in names:
        m = re.search(rf"\n\s*(?:\d+\.?\s*)?{nm}\b[^\n]{{0,40}}\n", low)
        if m:
            start = m.end()
            nxt = re.search(r"\n\s*(?:\d+\.?\s*)?(?:references|bibliography|"
                            r"acknowledg|appendix)\b", low[start:])
            end = start + (nxt.start() if nxt else limit)
            return txt[start:min(end, start + limit)].strip()
    return ""


def main() -> None:
    pdfs = sorted(SRC.glob("*.pdf"))
    print(f"{len(pdfs)} downloaded PDFs\n", flush=True)
    out = []
    for p in pdfs:
        rec = {"file": p.name}
        try:
            doc = pymupdf.open(p)
            rec["pages"] = doc.page_count
            head = "\n".join(page_text(doc, i) for i in range(min(3, doc.page_count)))
            tail = "\n".join(page_text(doc, i)
                             for i in range(max(0, doc.page_count - 3), doc.page_count))
            full = "\n".join(page_text(doc, i) for i in range(doc.page_count))
            doc.close()
            rec["chars"] = len(full)
            rec["first_page"] = head[:2500]
            rec["abstract"] = section(head, ["abstract"], 2200) or head[:1200]
            rec["intro"] = section(full, ["introduction", "1 introduction"], 2500)
            rec["conclusion"] = section(
                full, ["conclusion", "conclusions", "conclusion and future work",
                       "discussion and conclusion"], 2200) or tail[:1500]
            # does it cite anything? used later for the network pass
            refs = re.search(r"\n\s*references\b", full.lower())
            rec["has_reference_list"] = bool(refs)
            rec["n_ref_lines"] = (
                len([l for l in full[refs.end():].splitlines() if len(l.strip()) > 30])
                if refs else 0)
        except Exception as e:
            rec["error"] = f"{type(e).__name__}: {str(e)[:120]}"
        out.append(rec)
        status = rec.get("error") or f"{rec.get('pages','?')}p {rec.get('chars',0)} chars"
        print(f"  {p.name[:68]:<70} {status}", flush=True)

    OUT.write_text(json.dumps(out, indent=1))
    ok = sum(1 for r in out if not r.get("error"))
    noext = sum(1 for r in out if not r.get("error") and r.get("chars", 0) < 2000)
    print(f"\nextracted {ok}/{len(out)}; {noext} have almost no text (likely scans)")
    print(f"wrote {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()

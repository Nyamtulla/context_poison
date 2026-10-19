"""Generate references.bib for the manuscript from the coded corpus.

The drafting workflow requires every inline [@bibkey] to resolve in a BibTeX
file. This project stores its corpus in SQLite rather than as per-source wiki
pages, so the bibliography is generated from `paper_explorer.db` rather than
hand-maintained. Regenerate after any corpus change; never hand-edit the
output.

Bibkey convention: <firstauthorsurname>-<year>-<first distinctive title word>,
lowercased and ASCII-folded, with a numeric suffix on collision. Stable as long
as authors/year/title are stable, which they are - they come from Semantic
Scholar, not from the LLM extraction pass.
"""
from __future__ import annotations

import json
import pathlib
import re
import sqlite3
import unicodedata

REPO = pathlib.Path(__file__).resolve().parent.parent
DB = REPO / "data" / "paper_explorer.db"
OUT = REPO / "manuscript" / "references.bib"

STOP = {"a", "an", "the", "on", "of", "in", "for", "to", "and", "is", "are",
        "can", "do", "does", "how", "what", "when", "why", "with", "from",
        "towards", "toward", "beyond", "using", "via"}


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^A-Za-z0-9]+", "", s).lower()


def parse_authors(raw: str) -> list[str]:
    """paper_explorer.db stores authors semicolon-separated, not as JSON.

    An earlier version of this script assumed JSON, so json.loads threw on
    every row, the except branch returned an empty list, and all 1158 bibkeys
    came out as "anon-". Semicolons first, JSON as a fallback, because the
    other corpus table does use JSON.
    """
    if not raw:
        return []
    raw = raw.strip()
    if raw.startswith("["):
        try:
            a = json.loads(raw)
            return [x if isinstance(x, str) else (x.get("name") or "") for x in a]
        except Exception:
            pass
    return [p.strip() for p in raw.split(";") if p.strip()]


def surname(raw: str) -> str:
    a = parse_authors(raw)
    if not a:
        return "anon"
    return fold(a[0].split()[-1]) or "anon"


def titleword(title: str) -> str:
    for w in re.findall(r"[A-Za-z][A-Za-z0-9-]+", title or ""):
        lw = w.lower()
        if lw not in STOP and len(lw) > 2:
            return fold(lw)
    return "untitled"


def esc(s: str) -> str:
    """Strip braces and backslashes, then escape what LaTeX would choke on.

    The strip came first and the escape did not exist, so a venue called
    "Computer fraud & security" emitted a bare ampersand and the document
    failed to compile with "Misplaced alignment tab character &". Titles and
    venues from a bibliographic API carry all five of these.
    """
    s = (s or "").replace("{", "").replace("}", "").replace("\\", "").strip()
    for ch in ("&", "%", "$", "#", "_"):
        s = s.replace(ch, "\\" + ch)
    # ^ and ~ need a command, not a backslash: a bare \^ is an accent waiting
    # for its argument. Escaping $ without these two is worse than escaping
    # none of them, because a title like "Multi$^2$" then leaves the caret
    # outside math mode and the document fails with "Missing $ inserted".
    s = s.replace("^", "\\textasciicircum{}")
    s = s.replace("~", "\\textasciitilde{}")
    return s


def main() -> None:
    con = sqlite3.connect(DB)
    rows = con.execute(
        "select paper_id, title, authors, year, venue, doi, arxiv_id, url "
        "from paper order by year, title").fetchall()

    seen: dict[str, int] = {}
    entries, index = [], {}
    for pid, title, authors, year, venue, doi, arxiv, url in rows:
        if not title:
            continue
        key = f"{surname(authors)}-{year or 'nd'}-{titleword(title)}"
        if key in seen:
            seen[key] += 1
            key = f"{key}{chr(ord('a') + seen[key] - 1)}"
        else:
            seen[key] = 1

        names = parse_authors(authors)
        author_field = " and ".join(esc(n) for n in names) or "Unknown"

        # Semantic Scholar reports "arXiv" in the venue field for anything
        # that only ever appeared there, and taking that literally produced
        # 626 @inproceedings entries whose booktitle was "arXiv". They
        # rendered as "In arXiv.", which is not a venue and reads as an error.
        # A preprint is @misc with howpublished, which is what the ACM format
        # expects and what the hand-written entries already use.
        PREPRINT = {"arxiv", "corr", "biorxiv", "medrxiv", "ssrn",
                    "research square", "preprint", "arxiv.org"}
        is_preprint = (venue or "").strip().lower() in PREPRINT
        real_venue = venue if (venue and not is_preprint) else None

        kind = "inproceedings" if real_venue else "misc"
        lines = [f"@{kind}{{{key},",
                 f"  title     = {{{esc(title)}}},",
                 f"  author    = {{{author_field}}},"]
        if year:
            lines.append(f"  year      = {{{year}}},")
        if real_venue:
            lines.append(f"  booktitle = {{{esc(real_venue)}}},")
        elif arxiv:
            lines.append(f"  howpublished = {{arXiv:{esc(arxiv)}}},")
        # Keep a publisher DOI, drop the arXiv one: with eprint present it is
        # the same identifier written twice.
        if doi and not str(doi).lower().startswith("10.48550"):
            lines.append(f"  doi       = {{{esc(doi)}}},")
        if arxiv:
            lines.append(f"  eprint    = {{{esc(arxiv)}}},")
            lines.append("  archivePrefix = {arXiv},")
        # The stored url is a Semantic Scholar landing page for 1,088 of
        # these, which sends a reader to an aggregator rather than to the
        # work. doi and eprint identify it better, so only a direct link
        # survives.
        if url and "semanticscholar.org" not in str(url):
            lines.append(f"  url       = {{{esc(url)}}},")
        # The corpus id is internal bookkeeping and used to be emitted as a
        # note. With 723 entries rendering, every reference carried a 40-digit
        # hash, which is noise in a bibliography and tells a reader nothing.
        # bibkey_index.json already maps key -> paper_id for anything that
        # needs to get back to the record.
        lines.append("}")
        entries.append("\n".join(lines))
        index[key] = {"paper_id": pid, "title": title, "year": year}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        "% Generated by scripts/build_bibtex.py from data/paper_explorer.db.\n"
        "% Do not hand-edit; regenerate after any corpus change.\n\n"
        + "\n\n".join(entries) + "\n")
    (OUT.parent / "bibkey_index.json").write_text(json.dumps(index, indent=1))
    print(f"wrote {OUT.relative_to(REPO)}  ({len(entries)} entries)")
    print(f"wrote {(OUT.parent / 'bibkey_index.json').relative_to(REPO)}")


if __name__ == "__main__":
    main()

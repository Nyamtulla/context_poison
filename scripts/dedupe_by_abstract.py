"""Second-pass corpus dedup: find the same paper indexed twice under DIFFERENT
titles.

scripts/dedupe_corpus.py matches on title similarity, which has a documented
blind spot in this project: a paper renamed between its preprint and its
published version scores below the title threshold and slips through. It has
bitten us twice -- AgentFuzzer/AgentVigil (rescreening_log.md Addendum 2) and
InjecGuard/PIGuard. The reliable signal for that case is the ABSTRACT, which
authors usually carry over near-verbatim across a rename.

Report-only. Confirm each pair by eye, then exclude via dedupe_corpus.py --apply.

    python3 scripts/dedupe_by_abstract.py [--threshold 88] [--min-chars 200]
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path

import openpyxl
from rapidfuzz import fuzz

REPO = Path(__file__).resolve().parent.parent
XL = REPO / "data/exports/paper_dashboard_source.xlsx"


def norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[‐-―−]", "-", s)     # unicode dashes
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return s.strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=int, default=88)
    ap.add_argument("--min-chars", type=int, default=200,
                    help="ignore abstracts shorter than this (too little signal)")
    args = ap.parse_args()

    wb = openpyxl.load_workbook(XL, read_only=True)
    ws = wb["Papers"]
    hdr = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    i = {h: n for n, h in enumerate(hdr)}

    rows = []
    for n, r in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if r[i["screening"]] == "Exclude":
            continue
        abs_ = r[i["abstract"]] or ""
        if len(abs_) < args.min_chars:
            continue
        rows.append({"row": n, "title": r[i["title"]] or "", "abs": norm(abs_),
                     "raw_abs": abs_, "arxiv": r[i["arxiv_id"]],
                     "cites": r[i["citation_count"]] or 0, "year": r[i["year"]],
                     "venue": r[i["venue"]] or "", "pid": r[i["paper_id"]]})
    wb.close()
    print(f"comparing {len(rows)} included papers with abstracts >= {args.min_chars} chars")

    # bucket by a cheap prefix key to avoid a full O(n^2) rapidfuzz sweep
    hits = []
    for a in range(len(rows)):
        for b in range(a + 1, len(rows)):
            x, y = rows[a], rows[b]
            if abs(len(x["abs"]) - len(y["abs"])) > 0.35 * max(len(x["abs"]), len(y["abs"])):
                continue
            s = fuzz.ratio(x["abs"][:1200], y["abs"][:1200])
            if s >= args.threshold:
                hits.append((s, x, y))
    hits.sort(key=lambda t: -t[0])

    if not hits:
        print("\nNo near-identical abstracts found. Corpus is clean on this axis.")
        return
    print(f"\n{len(hits)} pair(s) with abstract similarity >= {args.threshold}:\n")
    for s, x, y in hits:
        tsim = fuzz.ratio(norm(x["title"]), norm(y["title"]))
        print(f"  abstract {s}  (title similarity only {tsim} -- "
              f"{'MISSED by title dedup' if tsim < 80 else 'also caught by title dedup'})")
        for z in (x, y):
            print(f"    row {z['row']:>5}  {z['year']}  {z['cites']:>4}c  arxiv={z['arxiv']}  {z['venue'][:28]}")
            print(f"           {z['title'][:88]}")
        print()
    print("Confirm by eye, then: python3 scripts/dedupe_corpus.py --apply <row>,...")


if __name__ == "__main__":
    main()

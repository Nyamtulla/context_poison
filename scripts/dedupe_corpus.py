"""Detect and (optionally) fix duplicate paper entries in the corpus.

The original src/dedup.py runs at ingestion time (DOI -> arXiv ID -> fuzzy
title+author). This script is a standing *audit* pass over whatever is
currently in the Excel workbook, meant to be re-run periodically (the
rebuild-corpus skill runs it first, before anything else) -- it caught 4
real duplicate papers during the RQ3/RQ4 registry-building pass in August
2026 that the ingestion-time pipeline missed (each pair: one entry with a
resolved arXiv ID and full data, one without, title slightly reworded
between indexing sources).

Usage:
    python3 scripts/dedupe_corpus.py                  # report only
    python3 scripts/dedupe_corpus.py --apply row1,row2,...   # exclude these
                                                          Excel rows as
                                                          confirmed duplicates

Excluding a row sets screening='Exclude' in the Excel workbook and
screen_human='auto_exclude' in the DB (the same human-override mechanism
used throughout this project -- see rescreening_log.md), never deletes data.
"""
import argparse
import sys
from pathlib import Path

import openpyxl
from rapidfuzz import fuzz

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.config import load_config  # noqa: E402
from src import db  # noqa: E402

EXCEL_PATH = REPO_ROOT / "data" / "exports" / "paper_dashboard_source.xlsx"
SIMILARITY_THRESHOLD = 80


def load_included_papers(ws, header, idx):
    papers = []
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if row[idx["screening"]] == "Exclude":
            continue
        title = row[idx["title"]]
        if not title:
            continue
        papers.append(
            {
                "row": row_idx,
                "title": title,
                "arxiv_id": row[idx["arxiv_id"]],
                "citation_count": row[idx["citation_count"]] or 0,
                "seed_category": row[idx["seed_category"]],
            }
        )
    return papers


def find_candidate_pairs(papers, threshold=SIMILARITY_THRESHOLD):
    pairs = []
    for i in range(len(papers)):
        for j in range(i + 1, len(papers)):
            score = fuzz.token_sort_ratio(papers[i]["title"], papers[j]["title"])
            if score >= threshold:
                pairs.append((score, papers[i], papers[j]))
    pairs.sort(key=lambda x: -x[0])
    return pairs


def report(pairs):
    if not pairs:
        print("No candidate duplicate pairs found.")
        return
    print(f"{len(pairs)} candidate duplicate pair(s) found (>= {SIMILARITY_THRESHOLD} title similarity):\n")
    print(
        "These are CANDIDATES, not confirmed duplicates -- two independently-"
        "authored papers can legitimately have very similar titles (this "
        "happened once in this corpus: two different survey papers on the "
        "same topic). Read each pair's title/abstract before excluding."
    )
    for score, p1, p2 in pairs:
        print(f"\n  similarity {score:.0f}:")
        print(f"    row {p1['row']:>5}  arxiv={p1['arxiv_id']!s:<14}  cites={p1['citation_count']:>4}  seed={p1['seed_category']}  {p1['title'][:70]}")
        print(f"    row {p2['row']:>5}  arxiv={p2['arxiv_id']!s:<14}  cites={p2['citation_count']:>4}  seed={p2['seed_category']}  {p2['title'][:70]}")
    print(
        "\nTo exclude confirmed duplicates (never the row with the "
        "resolved arXiv ID / seed status -- keep whichever twin has more "
        "complete data):\n"
        "  python3 scripts/dedupe_corpus.py --apply <row>,<row>,..."
    )


def apply_exclusions(rows_to_exclude, reason="confirmed duplicate paper entry"):
    wb = openpyxl.load_workbook(EXCEL_PATH)
    ws = wb["Papers"]
    header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    idx = {name: i for i, name in enumerate(header)}
    screening_col = idx["screening"] + 1
    paper_id_col = idx["paper_id"] + 1
    seed_col = idx["seed_category"] + 1

    config = load_config()
    conn = db.connect(config.path("db_path"))

    for row_idx in rows_to_exclude:
        seed_val = ws.cell(row=row_idx, column=seed_col).value
        if seed_val == "seed":
            print(f"REFUSING to exclude row {row_idx}: it is a hand-picked seed paper. "
                  f"If this is genuinely a duplicate, exclude its non-seed twin instead.")
            continue
        cell = ws.cell(row=row_idx, column=screening_col)
        old_val = cell.value
        cell.value = "Exclude"
        pid = ws.cell(row=row_idx, column=paper_id_col).value
        conn.execute("UPDATE papers SET screen_human = 'auto_exclude' WHERE paper_id = ?", (pid,))
        print(f"row {row_idx}: {old_val} -> Exclude ({reason})")

    wb.save(EXCEL_PATH)
    conn.commit()
    print(f"\nSaved. Applied {len(rows_to_exclude)} exclusion(s).")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", type=str, default=None,
                         help="Comma-separated Excel row numbers to exclude as confirmed duplicates")
    parser.add_argument("--threshold", type=int, default=SIMILARITY_THRESHOLD,
                         help=f"Title similarity threshold, 0-100 (default {SIMILARITY_THRESHOLD})")
    args = parser.parse_args()

    wb = openpyxl.load_workbook(EXCEL_PATH, read_only=True, data_only=True)
    ws = wb["Papers"]
    header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    idx = {name: i for i, name in enumerate(header)}
    papers = load_included_papers(ws, header, idx)
    wb.close()

    if args.apply:
        rows = [int(r.strip()) for r in args.apply.split(",")]
        apply_exclusions(rows)
        return

    pairs = find_candidate_pairs(papers, args.threshold)
    report(pairs)


if __name__ == "__main__":
    main()

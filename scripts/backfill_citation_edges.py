"""Fetch the reference lists that never landed, and rebuild the missing edges.

`citation_graph_isolates.md` established that 191 of the 1,026 corpus papers
draw as isolated nodes, and that 171 of those have no reference list in
`citation_edges` at all - so no edge could be drawn from them whatever they
cite. The original snowball pass logged HTTP 429 repeatedly, which is the
likely cause.

This re-fetches references for corpus papers with no outbound edge and writes
whatever comes back. It changes no reported number: `cites_track_a` and
`cites_track_b` are full-text extraction fields, coded by reading each paper's
own reference section, and they are not touched here. What it fixes is the
picture - a graph that shows a disconnection partly produced by our own
collection gap.

Only papers that are missing entirely are fetched. A paper that already has
edges is left alone, so this is safe to re-run and resumable after a failure.

    python3 scripts/backfill_citation_edges.py [--limit N] [--dry-run]
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src import db                                      # noqa: E402
from src.config import load_config                      # noqa: E402
from src.clients.semantic_scholar import SemanticScholarClient   # noqa: E402

GRAPH_DB = REPO / "data" / "context_sok.db"
EXPLORER_DB = REPO / "data" / "paper_explorer.db"


def targets(graph, limit=None):
    """Corpus papers with no outbound edge, newest first.

    Newest first because the gap is concentrated in 2025-2026 - those are the
    papers that arrived by keyword search, where no edge was ever traversed.
    """
    ex = sqlite3.connect(EXPLORER_DB)
    corpus = {r[0]: r[1] for r in ex.execute(
        "SELECT paper_id, COALESCE(year, 0) FROM paper WHERE screening = 'Include'")}
    ex.close()
    have = {r[0] for r in graph.execute(
        "SELECT DISTINCT citing_paper_id FROM citation_edges")}
    missing = [(p, y) for p, y in corpus.items() if p not in have]
    missing.sort(key=lambda t: -t[1])
    out = [p for p, _ in missing]
    return out[:limit] if limit else out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    config = load_config()
    graph = sqlite3.connect(GRAPH_DB)
    todo = targets(graph, args.limit)
    before = graph.execute("SELECT COUNT(*) FROM citation_edges").fetchone()[0]
    print(f"{len(todo)} corpus papers have no outbound edge; "
          f"edge store holds {before:,} rows")
    if args.dry_run or not todo:
        return

    client = SemanticScholarClient(config)
    print(f"API key: {'yes' if client.has_key else 'no (unauthenticated rate limit)'}",
          flush=True)

    added = fetched = failed = empty = 0
    t0 = time.time()
    for i, pid in enumerate(todo, 1):
        try:
            res = client.get_references(pid)
        except Exception as exc:                 # keep going; record and move on
            failed += 1
            print(f"  [{i}/{len(todo)}] {pid[:12]} FAILED {type(exc).__name__}: "
                  f"{str(exc)[:90]}", flush=True)
            continue
        refs = (res or {}).get("papers") or []
        fetched += 1
        if not refs:
            empty += 1
        for r in refs:
            rid = r.get("paper_id") or r.get("paperId")
            if rid:
                db.upsert_citation_edge(graph, citing_paper_id=pid,
                                        cited_paper_id=rid, direction="backward")
                added += 1
        graph.commit()
        if i % 20 == 0 or i == len(todo):
            rate = i / max(time.time() - t0, 1e-9)
            print(f"  [{i}/{len(todo)}] fetched {fetched}  empty {empty}  "
                  f"failed {failed}  edges +{added:,}  ({rate:.2f}/s)", flush=True)

    after = graph.execute("SELECT COUNT(*) FROM citation_edges").fetchone()[0]
    graph.close()
    print(f"\ndone: {fetched} fetched, {empty} returned no references, {failed} failed")
    print(f"edge store {before:,} -> {after:,}  (+{after - before:,})")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Command-line entrypoint for the Context Integrity SoK paper tool.

Subcommands mirror the SRS's functional requirements:
  init-db      create the SQLite schema if it doesn't exist
  load-seeds   ingest seed_papers.csv as hop-0 papers (FR seed ingestion)
  search       keyword search both tracks (FR-1/2/11)
  snowball     backward + forward snowball to config.hop_depth (FR-4/5/6)
  classify     (re)compute track_auto/screen_auto (FR-7/8)
  fetch-pdfs   download arXiv PDFs (FR-9)
  export       CSV/JSON export (FR-10)
  export-excel (re)generate the dashboard's editable Excel data source
  sync-excel   resolve+insert hand-added Excel rows into the DB, fetch their edges
  pipeline     run all of the above in order
  smoke-test   network-light wiring check, no S2 key required
"""
from __future__ import annotations

import argparse
import csv
import logging
import sys

from src import classify, confidence, db, excel_source, excel_sync, export, pdf_fetch, search_runner, seeds, snowball
from src.config import load_config

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("cli")


def _get_conn(config):
    conn = db.connect(config.path("db_path"))
    db.init_db(conn)
    return conn


def cmd_init_db(config, args) -> None:
    conn = _get_conn(config)
    print(f"DB initialized at {config.path('db_path')} ({db.paper_count(conn)} existing papers)")


def cmd_load_seeds(config, args) -> None:
    conn = _get_conn(config)
    counts = seeds.load_seeds(conn, config, use_network=not args.offline)
    print(f"load-seeds: {counts}")
    print(f"papers table now has {db.paper_count(conn)} rows")


def cmd_search(config, args) -> None:
    conn = _get_conn(config)
    counts = search_runner.run_search(conn, config)
    print(f"search: {counts}")


def cmd_snowball(config, args) -> None:
    conn = _get_conn(config)
    counts = snowball.run_snowball(conn, config)
    print(f"snowball: {counts}")


def cmd_classify(config, args) -> None:
    conn = _get_conn(config)
    updated = 0
    for row in db.all_papers(conn):
        if row["seed_category"]:
            continue  # seeds/competitor_sok classified specially by load-seeds
        if not args.force and row["track_auto"] and row["screen_auto"]:
            continue
        tags = classify.classify_paper(row["title"], row["abstract"], config)
        conn.execute(
            "UPDATE papers SET track_auto = ?, screen_auto = ? WHERE paper_id = ?",
            (tags["track_auto"], tags["screen_auto"], row["paper_id"]),
        )
        updated += 1
    conn.commit()
    print(f"classify: recomputed {updated} rows (force={args.force})")


def cmd_fetch_pdfs(config, args) -> None:
    conn = _get_conn(config)
    counts = pdf_fetch.fetch_pdfs(conn, config)
    print(f"fetch-pdfs: {counts}")


def cmd_export(config, args) -> None:
    conn = _get_conn(config)
    result = export.export_all(conn, config)
    print(f"export: {result}")


def cmd_export_excel(config, args) -> None:
    conn = _get_conn(config)
    path = config.path("excel_source")
    if args.all:
        ids = None
    else:
        ids = confidence.high_confidence_ids(conn, config, min_citations=0, max_hop=config.hop_depth)
    result = excel_source.export_to_path(conn, path, ids=ids, overwrite=args.overwrite)
    print(f"export-excel: wrote {result}")


def cmd_sync_excel(config, args) -> None:
    conn = _get_conn(config)
    path = config.path("excel_source")
    if not path.exists():
        print(f"sync-excel: no file at {path} - nothing to sync")
        return
    counts = excel_sync.sync_excel(conn, config, path)
    print(f"sync-excel: {counts}")


def cmd_pipeline(config, args) -> None:
    cmd_load_seeds(config, args)
    cmd_search(config, args)
    cmd_snowball(config, args)
    cmd_classify(config, args)
    cmd_fetch_pdfs(config, args)
    cmd_export(config, args)


def cmd_smoke_test(config, args) -> None:
    from src.clients.arxiv import ArxivClient
    from src.clients.openalex import OpenAlexClient
    from src.clients.semantic_scholar import SemanticScholarClient

    print("=== Smoke test (no live S2 key required) ===")

    arxiv = ArxivClient(config)
    with open(config.path("seed_csv"), newline="") as f:
        rows = list(csv.DictReader(f))
    sample = [r for r in rows if r.get("arxiv_id")][:2]
    for row in sample:
        try:
            hit = arxiv.get_by_id(row["arxiv_id"])
            if hit and hit.get("title"):
                print(f"[arXiv] {row['arxiv_id']}: OK - {hit['title'][:70]}")
            else:
                print(f"[arXiv] {row['arxiv_id']}: no entry returned")
        except Exception as exc:
            print(f"[arXiv] {row['arxiv_id']}: ERROR {exc}")

    s2 = SemanticScholarClient(config)
    try:
        result = s2.search("indirect prompt injection", config.start_year, config.end_year, max_results=5)
        print(f"[S2] search returned {len(result['papers'])} papers (has_key={s2.has_key})")
    except Exception as exc:
        print(f"[S2] search FAILED (expected if rate-limited without a key yet): {exc}")

    openalex = OpenAlexClient(config)
    try:
        result = openalex.search(
            "lost in the middle long context", config.start_year, config.end_year, max_results=5
        )
        print(f"[OpenAlex] search returned {len(result['papers'])} papers")
    except Exception as exc:
        print(f"[OpenAlex] search FAILED: {exc}")

    conn = db.connect(":memory:")
    db.init_db(conn)
    paper = {
        "paper_id": "smoke-test-1", "title": "Smoke Test Paper", "abstract": "abstract",
        "authors": ["A. Author"], "year": 2024, "venue": "Test Venue", "doi": None,
        "arxiv_id": None, "url": None, "citation_count": 0, "pdf_local_path": None,
        "track_auto": "A", "track_human": None, "screen_auto": "auto_include",
        "screen_human": None, "discovered_via": "seed", "hop": 0, "source_paper_id": None,
        "discovered_query": None, "seed_category": "seed", "date_added": "2026-01-01",
    }
    db.upsert_paper(conn, paper)
    db.upsert_paper(conn, paper)
    conn.commit()
    count = db.paper_count(conn)
    print(f"[DB] upsert x2 -> row count = {count} ({'OK' if count == 1 else 'FAILED'})")
    print("=== Smoke test complete ===")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=None, help="path to config.yaml (default: ./config.yaml)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db")

    p_seeds = sub.add_parser("load-seeds")
    p_seeds.add_argument("--offline", action="store_true", help="skip network resolution, load raw CSV fields only")

    sub.add_parser("search")
    sub.add_parser("snowball")

    p_classify = sub.add_parser("classify")
    p_classify.add_argument("--force", action="store_true", help="recompute track_auto/screen_auto for every row")

    sub.add_parser("fetch-pdfs")
    sub.add_parser("export")

    p_export_excel = sub.add_parser("export-excel")
    p_export_excel.add_argument("--overwrite", action="store_true", help="replace the existing file (loses hand edits!)")
    p_export_excel.add_argument("--all", action="store_true", help="export every paper, not just the high-confidence pool")

    sub.add_parser("sync-excel")

    p_pipeline = sub.add_parser("pipeline")
    p_pipeline.add_argument("--offline", action="store_true")
    p_pipeline.add_argument("--force", action="store_true")

    sub.add_parser("smoke-test")

    args = parser.parse_args()
    config = load_config(args.config)

    handlers = {
        "init-db": cmd_init_db,
        "load-seeds": cmd_load_seeds,
        "search": cmd_search,
        "snowball": cmd_snowball,
        "classify": cmd_classify,
        "fetch-pdfs": cmd_fetch_pdfs,
        "export": cmd_export,
        "export-excel": cmd_export_excel,
        "sync-excel": cmd_sync_excel,
        "pipeline": cmd_pipeline,
        "smoke-test": cmd_smoke_test,
    }
    handlers[args.command](config, args)


if __name__ == "__main__":
    sys.exit(main())

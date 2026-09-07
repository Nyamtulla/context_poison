"""Backfill forward citations ("who cites this?") for every RQ3 mechanism paper.

Why this exists: the original snowball did BFS from the 51 seeds, so forward
citations were only ever fetched for seeds and hop-1 papers. Most mechanism
papers were discovered by keyword search or at hop 2, so we never asked S2
who cites them - which makes "no defense paper cites this attack" unmeasurable
rather than false. This fetches forward citations for all 183 mechanism papers
specifically, so RQ5 coverage can be recomputed from citation evidence and not
only from name-matching in the defense papers' own results text.

Read-only with respect to the registries; it only adds rows to citation_edges
(and, per record_edge/upsert semantics, never duplicates an existing edge).

    python scripts/backfill_mechanism_citations.py [--limit N] [--uncovered-only]
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import db, registry_source, snowball
from src.clients.semantic_scholar import SemanticScholarClient
from src.config import load_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backfill")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="only process the first N papers")
    ap.add_argument("--uncovered-only", action="store_true",
                    help="only mechanisms with zero confirmed defenses (default: all 183, "
                         "so the covered ones act as a control for the method)")
    args = ap.parse_args()

    config = load_config()
    conn = db.connect(str(config.path("db_path")))
    db.init_db(conn)
    s2 = SemanticScholarClient(config)
    raw_cache_dir = config.path("raw_cache_dir")

    reg = registry_source.load_all()
    mechs = reg["mechanisms"]
    if args.uncovered_only:
        mechs = [m for m in mechs if not m["has_any_defense"]]

    targets = []
    seen = set()
    for m in mechs:
        pid = m.get("source_paper_id")
        if pid and pid not in seen:
            seen.add(pid)
            targets.append((pid, m["mechanism_name"], m["has_any_defense"]))
    if args.limit:
        targets = targets[: args.limit]

    logger.info("Fetching forward citations for %d mechanism papers", len(targets))
    stats = {"ok": 0, "failed": 0, "edges": 0}

    for i, (pid, name, covered) in enumerate(targets, 1):
        try:
            result = s2.get_citations(pid)
        except Exception as exc:
            logger.warning("[%d/%d] FAILED %s (%s): %s", i, len(targets), name[:50], pid, exc)
            stats["failed"] += 1
            continue

        snowball.cache_raw(raw_cache_dir, "backfill_forward", result["raw_pages"])
        n = 0
        for related in result["papers"]:
            rid = related.get("paper_id")
            if not rid:
                continue
            # Edge only - deliberately does NOT add new papers to the corpus.
            # Changing the screened corpus would invalidate RQ1-RQ4's published
            # numbers; we only want to know who cites these mechanism papers.
            snowball.record_edge(conn, pid, rid, "forward")
            n += 1
        conn.commit()  # commit per paper so an interrupted run keeps its progress
        stats["ok"] += 1
        stats["edges"] += n
        logger.info("[%d/%d] %-55s %s citers=%d",
                    i, len(targets), name[:55], "covered" if covered else "UNCOVERED", n)

    conn.close()
    logger.info("Done: %s", stats)


if __name__ == "__main__":
    main()

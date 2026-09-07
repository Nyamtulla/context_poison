"""SQLite layer. Schema per SRS Section 6, plus one additive column
(`papers.seed_category`) to distinguish true seeds from competitor_sok rows
without overloading `discovered_via` (see plan's interpretation note).

Upserts are idempotent (NFR-2) and never clobber a human-set field or the
original discovery provenance (NFR-4): `track_human`/`screen_human` and the
discovery/date_added columns use COALESCE(existing, new); everything else
prefers the freshest non-null value.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    paper_id            TEXT PRIMARY KEY,
    title               TEXT,
    abstract            TEXT,
    authors             TEXT,   -- JSON list
    year                INTEGER,
    venue               TEXT,
    doi                 TEXT,
    arxiv_id            TEXT,
    url                 TEXT,
    citation_count      INTEGER,
    pdf_local_path      TEXT,
    track_auto          TEXT,
    track_human         TEXT,
    screen_auto         TEXT,
    screen_human        TEXT,
    discovered_via      TEXT,   -- seed / search / backward / forward
    hop                 INTEGER,
    source_paper_id     TEXT,
    discovered_query    TEXT,
    seed_category        TEXT,  -- seed / competitor_sok / NULL (additive column)
    date_added          TEXT
);

CREATE TABLE IF NOT EXISTS citation_edges (
    citing_paper_id      TEXT,
    cited_paper_id       TEXT,
    direction_discovered TEXT,  -- backward / forward
    PRIMARY KEY (citing_paper_id, cited_paper_id)
);

CREATE TABLE IF NOT EXISTS search_log (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    query_string        TEXT,
    track               TEXT,
    api                 TEXT,
    timestamp           TEXT,
    hit_count           INTEGER,
    raw_response_path   TEXT
);

CREATE INDEX IF NOT EXISTS idx_papers_arxiv_id ON papers(arxiv_id);
CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi);
CREATE INDEX IF NOT EXISTS idx_citation_edges_citing ON citation_edges(citing_paper_id);
CREATE INDEX IF NOT EXISTS idx_citation_edges_cited ON citation_edges(cited_paper_id);
"""

PAPER_COLUMNS = [
    "paper_id", "title", "abstract", "authors", "year", "venue", "doi",
    "arxiv_id", "url", "citation_count", "pdf_local_path", "track_auto",
    "track_human", "screen_auto", "screen_human", "discovered_via", "hop",
    "source_paper_id", "discovered_query", "seed_category", "date_added",
]

# Fields where a human decision or original provenance must never be
# silently overwritten by a later automated pass.
_KEEP_EXISTING_IF_SET = {
    "track_human", "screen_human", "date_added",
    "discovered_via", "hop", "source_paper_id", "discovered_query",
}


def connect(db_path: str | Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def _upsert_sql() -> str:
    cols = PAPER_COLUMNS
    placeholders = ", ".join(f":{c}" for c in cols)
    set_clauses = []
    for c in cols:
        if c == "paper_id":
            continue
        if c in _KEEP_EXISTING_IF_SET:
            set_clauses.append(f"{c} = COALESCE(papers.{c}, excluded.{c})")
        else:
            set_clauses.append(f"{c} = COALESCE(excluded.{c}, papers.{c})")
    return (
        f"INSERT INTO papers ({', '.join(cols)}) VALUES ({placeholders}) "
        f"ON CONFLICT(paper_id) DO UPDATE SET {', '.join(set_clauses)}"
    )


_UPSERT_SQL = _upsert_sql()


def upsert_paper(conn: sqlite3.Connection, paper: dict[str, Any]) -> None:
    row = {c: paper.get(c) for c in PAPER_COLUMNS}
    if isinstance(row.get("authors"), (list, tuple)):
        row["authors"] = json.dumps(list(row["authors"]))
    conn.execute(_UPSERT_SQL, row)


def upsert_papers(conn: sqlite3.Connection, papers: Iterable[dict[str, Any]]) -> None:
    for p in papers:
        upsert_paper(conn, p)
    conn.commit()


def upsert_citation_edge(
    conn: sqlite3.Connection, citing_paper_id: str, cited_paper_id: str, direction: str
) -> None:
    # First-seen direction wins for a given edge; duplicate discovery of the
    # same edge from the other direction is a no-op, not an error.
    conn.execute(
        "INSERT OR IGNORE INTO citation_edges "
        "(citing_paper_id, cited_paper_id, direction_discovered) VALUES (?, ?, ?)",
        (citing_paper_id, cited_paper_id, direction),
    )


def insert_search_log(
    conn: sqlite3.Connection,
    query_string: str,
    track: str,
    api: str,
    timestamp: str,
    hit_count: int,
    raw_response_path: str,
) -> None:
    conn.execute(
        "INSERT INTO search_log (query_string, track, api, timestamp, hit_count, "
        "raw_response_path) VALUES (?, ?, ?, ?, ?, ?)",
        (query_string, track, api, timestamp, hit_count, raw_response_path),
    )
    conn.commit()


def get_paper(conn: sqlite3.Connection, paper_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM papers WHERE paper_id = ?", (paper_id,)).fetchone()


def find_by_doi(conn: sqlite3.Connection, doi: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM papers WHERE doi = ? COLLATE NOCASE", (doi,)
    ).fetchone()


def find_by_arxiv_id(conn: sqlite3.Connection, arxiv_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM papers WHERE arxiv_id = ?", (arxiv_id,)
    ).fetchone()


def all_papers(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM papers").fetchall()


def all_citation_edges(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM citation_edges").fetchall()


def paper_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]

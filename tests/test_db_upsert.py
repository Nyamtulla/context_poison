from src import db


def make_paper(**overrides):
    base = {
        "paper_id": "p1", "title": "Title", "abstract": "Abstract", "authors": ["A. One"],
        "year": 2024, "venue": "Venue", "doi": None, "arxiv_id": None, "url": None,
        "citation_count": 1, "pdf_local_path": None, "track_auto": "A", "track_human": None,
        "screen_auto": "auto_include", "screen_human": None, "discovered_via": "seed", "hop": 0,
        "source_paper_id": None, "discovered_query": None, "seed_category": "seed",
        "date_added": "2026-01-01T00:00:00",
    }
    base.update(overrides)
    return base


def new_conn():
    conn = db.connect(":memory:")
    db.init_db(conn)
    return conn


def test_upsert_is_idempotent_on_rerun():
    conn = new_conn()
    db.upsert_paper(conn, make_paper())
    db.upsert_paper(conn, make_paper())
    conn.commit()
    assert db.paper_count(conn) == 1


def test_upsert_never_overwrites_human_track_or_screen():
    conn = new_conn()
    db.upsert_paper(conn, make_paper())
    conn.execute("UPDATE papers SET track_human = 'B', screen_human = 'auto_exclude' WHERE paper_id = 'p1'")
    conn.commit()
    db.upsert_paper(conn, make_paper(track_human=None, screen_human=None, track_auto="Both"))
    conn.commit()
    row = db.get_paper(conn, "p1")
    assert row["track_human"] == "B"
    assert row["screen_human"] == "auto_exclude"
    assert row["track_auto"] == "Both"  # machine field still refreshes


def test_upsert_preserves_original_date_added_and_discovery_type():
    conn = new_conn()
    db.upsert_paper(conn, make_paper(date_added="2026-01-01T00:00:00", discovered_via="seed", hop=0))
    # a later pass also surfaces this paper via keyword search - discovered_via/hop must not flip,
    # but discovered_query was never set for the seed pass, so it's fine to fill that gap in.
    db.upsert_paper(
        conn,
        make_paper(
            date_added="2026-06-01T00:00:00",
            discovered_via="search",
            hop=0,
            discovered_query="context rot",
        ),
    )
    conn.commit()
    row = db.get_paper(conn, "p1")
    assert row["date_added"] == "2026-01-01T00:00:00"
    assert row["discovered_via"] == "seed"
    assert row["discovered_query"] == "context rot"


def test_upsert_never_overwrites_an_already_set_discovered_query():
    conn = new_conn()
    db.upsert_paper(conn, make_paper(discovered_via="search", discovered_query="original query"))
    db.upsert_paper(conn, make_paper(discovered_via="search", discovered_query="different query"))
    conn.commit()
    row = db.get_paper(conn, "p1")
    assert row["discovered_query"] == "original query"


def test_upsert_refreshes_metadata_fields():
    conn = new_conn()
    db.upsert_paper(conn, make_paper(citation_count=1, venue=None))
    db.upsert_paper(conn, make_paper(citation_count=99, venue="NeurIPS"))
    conn.commit()
    row = db.get_paper(conn, "p1")
    assert row["citation_count"] == 99
    assert row["venue"] == "NeurIPS"


def test_citation_edge_insert_or_ignore():
    conn = new_conn()
    db.upsert_citation_edge(conn, "a", "b", "backward")
    db.upsert_citation_edge(conn, "a", "b", "forward")  # duplicate edge, different direction claim
    conn.commit()
    rows = db.all_citation_edges(conn)
    assert len(rows) == 1
    assert rows[0]["direction_discovered"] == "backward"  # first-seen direction wins

import pytest

from src import confidence, db
from src.config import Config

RAW_CONFIG = {
    "track_signatures": {"A": ["Greshake"], "B": ["Lost in the Middle"]},
}


@pytest.fixture
def config():
    return Config(raw=RAW_CONFIG)


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    db.init_db(c)
    return c


def make_paper(**overrides):
    base = {
        "paper_id": "p1", "title": "Title", "abstract": "Abstract mentioning Greshake",
        "authors": [], "year": 2024, "venue": "V", "doi": None, "arxiv_id": None, "url": None,
        "citation_count": 5, "pdf_local_path": None, "track_auto": "A", "track_human": None,
        "screen_auto": "auto_include", "screen_human": None, "discovered_via": "seed", "hop": 0,
        "source_paper_id": None, "discovered_query": None, "seed_category": "seed",
        "date_added": "2026-01-01T00:00:00",
    }
    base.update(overrides)
    return base


def test_seed_included_by_default(conn, config):
    db.upsert_paper(conn, make_paper())
    conn.commit()
    assert "p1" in confidence.high_confidence_ids(conn, config)


def test_human_excluded_seed_is_dropped(conn, config):
    db.upsert_paper(conn, make_paper(screen_human="auto_exclude"))
    conn.commit()
    assert "p1" not in confidence.high_confidence_ids(conn, config)


def test_human_excluded_non_seed_is_dropped_even_with_signature_match(conn, config):
    db.upsert_paper(conn, make_paper(
        paper_id="p2", seed_category=None, discovered_via="search",
        screen_auto="auto_include", screen_human="auto_exclude",
    ))
    conn.commit()
    assert "p2" not in confidence.high_confidence_ids(conn, config)


def test_non_seed_with_signature_match_included_when_not_excluded(conn, config):
    db.upsert_paper(conn, make_paper(paper_id="p3", seed_category=None, discovered_via="search"))
    conn.commit()
    assert "p3" in confidence.high_confidence_ids(conn, config)

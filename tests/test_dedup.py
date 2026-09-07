from src import dedup


def test_normalize_doi_strips_prefixes():
    assert dedup.normalize_doi("https://doi.org/10.1145/ABC") == "10.1145/abc"
    assert dedup.normalize_doi("10.1145/ABC") == "10.1145/abc"
    assert dedup.normalize_doi(None) is None


def test_same_paper_matches_on_doi():
    a = {"title": "Totally Different Title A", "doi": "10.1/X", "authors": ["A One"]}
    b = {"title": "Totally Different Title B", "doi": "https://doi.org/10.1/x", "authors": ["Z Two"]}
    assert dedup.same_paper(a, b)


def test_same_paper_matches_on_arxiv_id_ignoring_version():
    a = {"title": "T1", "arxiv_id": "2302.12173v1", "authors": ["Greshake K"]}
    b = {"title": "T2", "arxiv_id": "2302.12173v2", "authors": ["Someone Else"]}
    assert dedup.same_paper(a, b)


def test_same_paper_fuzzy_title_requires_matching_first_author():
    a = {"title": "PoisonedRAG: Knowledge Poisoning Attacks to RAG of LLMs", "authors": ["Wei Zou"]}
    b = {"title": "PoisonedRAG: Knowledge Poisoning Attacks to RAG of LLMs.", "authors": ["Wei Zou"]}
    c = {"title": "PoisonedRAG: Knowledge Poisoning Attacks to RAG of LLMs.", "authors": ["Someone Unrelated"]}
    assert dedup.same_paper(a, b)
    assert not dedup.same_paper(a, c)


def test_same_paper_false_for_unrelated_titles():
    a = {"title": "Lost in the Middle", "authors": ["N.F. Liu"]}
    b = {"title": "AgentDojo Evaluation Environment", "authors": ["N.F. Liu"]}
    assert not dedup.same_paper(a, b)


def test_merge_fill_gaps_prefers_preferred_but_fills_empty():
    preferred = {"title": "T", "abstract": None, "citation_count": 10}
    filler = {"title": "Other Title", "abstract": "filled in", "citation_count": 5}
    merged = dedup.merge_fill_gaps(preferred, filler)
    assert merged["title"] == "T"
    assert merged["abstract"] == "filled in"
    assert merged["citation_count"] == 10


def test_canonicalize_batch_merges_cross_source_duplicates():
    s2_hit = {
        "title": "InjecAgent Benchmark",
        "abstract": "full abstract from s2",
        "authors": ["Zhan Q"],
        "arxiv_id": "2403.02691",
        "doi": None,
        "year": 2024,
        "citation_count": 42,
    }
    arxiv_hit = {
        "title": "InjecAgent Benchmark",
        "abstract": None,
        "authors": ["Zhan Q"],
        "arxiv_id": "2403.02691v2",
        "doi": "10.48550/arxiv.2403.02691",
        "year": 2024,
        "citation_count": None,
    }
    merged = dedup.canonicalize_batch([(s2_hit, "semantic_scholar"), (arxiv_hit, "arxiv")])
    assert len(merged) == 1
    rec = merged[0]
    assert rec["abstract"] == "full abstract from s2"  # S2 wins, higher priority
    assert rec["citation_count"] == 42
    assert rec["doi"] == "10.48550/arxiv.2403.02691"  # gap filled from arXiv


def test_canonicalize_batch_keeps_distinct_papers_separate():
    p1 = {"title": "Lost in the Middle", "authors": ["N.F. Liu"], "arxiv_id": None, "doi": None}
    p2 = {"title": "AgentDojo", "authors": ["Debenedetti E"], "arxiv_id": None, "doi": None}
    merged = dedup.canonicalize_batch([(p1, "arxiv"), (p2, "arxiv")])
    assert len(merged) == 2

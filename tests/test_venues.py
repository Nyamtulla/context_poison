from src.venues import normalize_venue


def test_arxiv_variants_collapse():
    assert normalize_venue("arXiv.org") == "arXiv"
    assert normalize_venue("arXiv") == "arXiv"
    assert normalize_venue("ArXiv preprint") == "arXiv"


def test_known_long_form_venues_map_to_short_names():
    cases = {
        "Annual Meeting of the Association for Computational Linguistics": "ACL",
        "Conference on Empirical Methods in Natural Language Processing": "EMNLP",
        "Neural Information Processing Systems": "NeurIPS",
        "International Conference on Learning Representations": "ICLR",
        "AAAI Conference on Artificial Intelligence": "AAAI",
        "International Conference on Machine Learning": "ICML",
        "IEEE Symposium on Security and Privacy": "IEEE S&P",
        "Network and Distributed System Security Symposium": "NDSS",
        "North American Chapter of the Association for Computational Linguistics": "NAACL",
        "USENIX Security Symposium": "USENIX Security",
        "European Symposium on Research in Computer Security": "ESORICS",
        "Conference on Computer and Communications Security": "ACM CCS",
    }
    for raw, expected in cases.items():
        assert normalize_venue(raw) == expected, raw


def test_embedded_sig_acronym_fallback():
    assert normalize_venue("Proceedings of the 49th International ACM SIGIR Conference on Research and Development in Information Retrieval") == "SIGIR"


def test_unmapped_venue_falls_back_to_cleaned_original():
    assert normalize_venue("Electronics") == "Electronics"
    assert normalize_venue("IEEE Access") == "IEEE Access"


def test_none_and_empty_pass_through():
    assert normalize_venue(None) is None
    assert normalize_venue("") == ""

import pytest

from src import classify
from src.config import Config

RAW_CONFIG = {
    "search": {"start_year": 2023, "end_year": None},
    "hop_depth": 2,
    "tracks": {"A": {"keyword_clusters": []}, "B": {"keyword_clusters": []}},
    "venues": {"soft_list": []},
    "screening": {
        "include_signal_terms": ["agent", "agents", "tool calling", "RAG", "memory"],
        "jailbreak_only_terms": ["jailbreak", "jailbreaking"],
        "training_time_only_terms": ["training data poisoning", "pretraining poisoning"],
        "runtime_signal_terms": ["inference time", "runtime", "context window"],
        "llm_presence_terms": ["LLM", "large language model", "GPT"],
    },
    "track_signatures": {
        "A": ["Greshake", "PoisonedRAG", "MCP tool poisoning"],
        "B": ["Lost in the Middle", "context rot", "N.F. Liu"],
    },
    "apis": {
        "semantic_scholar": {"api_key_env": "S2_API_KEY"},
        "openalex": {"contact_email_env": "OPENALEX_CONTACT_EMAIL"},
    },
    "paths": {},
}


@pytest.fixture
def config():
    return Config(raw=RAW_CONFIG)


def test_classify_track_signature_match_a(config):
    assert classify.classify_track("PoisonedRAG attack", "abstract text", config) == "A"


def test_classify_track_signature_match_b(config):
    assert classify.classify_track("Lost in the Middle", "abstract text", config) == "B"


def test_classify_track_both_when_both_signatures_present(config):
    title = "Bridging Greshake-style injection and context rot"
    assert classify.classify_track(title, "", config) == "Both"


def test_classify_track_unclear_when_no_signal(config):
    assert classify.classify_track("An unrelated ML paper", "no signal here", config) == "Unclear"


def test_classify_track_falls_back_to_query_cluster(config):
    assert classify.classify_track("Generic title", "generic abstract", config, query_track="A") == "A"


def test_classify_screen_jailbreak_only_excluded(config):
    result = classify.classify_screen(
        "Jailbreaking LLMs", "We study jailbreak prompts against GPT models directly.", config
    )
    assert result == "auto_exclude"


def test_classify_screen_jailbreak_with_agent_term_not_excluded(config):
    result = classify.classify_screen(
        "Jailbreaking LLM Agents",
        "We study jailbreaking of LLM agents that use tool calling to act in the world.",
        config,
    )
    assert result == "auto_include"


def test_classify_screen_training_time_only_excluded(config):
    result = classify.classify_screen(
        "Training Data Poisoning of LLMs", "We study training data poisoning attacks on GPT pretraining.", config
    )
    assert result == "auto_exclude"


def test_classify_screen_training_time_with_runtime_term_included(config):
    result = classify.classify_screen(
        "Training Data Poisoning Effects at Inference Time",
        "We study training data poisoning and its effect at inference time on an LLM agent using memory.",
        config,
    )
    assert result == "auto_include"


def test_classify_screen_non_llm_excluded(config):
    result = classify.classify_screen(
        "Poisoning Robot Arm Controllers", "We attack a robot arm control system with sensor poisoning.", config
    )
    assert result == "auto_exclude"


def test_classify_screen_needs_review_when_ambiguous(config):
    result = classify.classify_screen(
        "LLM Output Quality Study", "We evaluate GPT output quality across benchmarks.", config
    )
    assert result == "needs_review"


def test_classify_seed_forces_auto_include(config):
    result = classify.classify_seed(
        "Jailbreaking LLMs", "pure jailbreak text about GPT with no other signal present", config, "A"
    )
    assert result["screen_auto"] == "auto_include"
    assert result["track_human"] == "A"
    assert result["_computed_screen_for_consistency_check"] == "auto_exclude"

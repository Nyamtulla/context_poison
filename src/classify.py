"""Track auto-tagging (FR-8) and screening pre-flag (FR-7). Every rule reads
from config.yaml (NFR-3) — no keyword lists hardcoded here. This is a
pre-filter only: `screen_auto` never gates anything by itself, and nothing is
ever dropped from the DB based on these tags (NFR-4) — only from filtered
views/exports.
"""
from __future__ import annotations

from typing import Any


def _text_blob(title: str | None, abstract: str | None) -> str:
    return f"{title or ''} {abstract or ''}".lower()


def _any_term_in(terms: list[str], text: str) -> bool:
    return any(t.lower() in text for t in terms)


def classify_track(
    title: str | None,
    abstract: str | None,
    config,
    query_track: str | None = None,
) -> str:
    """A / B / Both / Unclear — from (1) which query cluster surfaced it and
    (2) signature-term matches, per FR-8. Never overwrites `track_human`;
    callers store this only in `track_auto`."""
    text = _text_blob(title, abstract)
    signatures = config.track_signatures
    matched_a = _any_term_in(signatures.get("A", []), text) or query_track == "A"
    matched_b = _any_term_in(signatures.get("B", []), text) or query_track == "B"
    if matched_a and matched_b:
        return "Both"
    if matched_a:
        return "A"
    if matched_b:
        return "B"
    return "Unclear"


def classify_screen(title: str | None, abstract: str | None, config) -> str:
    """auto_include / auto_exclude / needs_review, per FR-7 and the
    inclusion/exclusion text ported into config.yaml's `screening` block."""
    text = _text_blob(title, abstract)
    screening = config.screening

    has_include_signal = _any_term_in(screening["include_signal_terms"], text)

    if _any_term_in(screening["jailbreak_only_terms"], text) and not has_include_signal:
        return "auto_exclude"

    has_runtime_signal = _any_term_in(screening["runtime_signal_terms"], text)
    if _any_term_in(screening["training_time_only_terms"], text) and not has_runtime_signal:
        return "auto_exclude"

    if not _any_term_in(screening["llm_presence_terms"], text):
        return "auto_exclude"

    if has_include_signal:
        return "auto_include"

    return "needs_review"


def classify_paper(
    title: str | None, abstract: str | None, config, query_track: str | None = None
) -> dict[str, str]:
    return {
        "track_auto": classify_track(title, abstract, config, query_track),
        "screen_auto": classify_screen(title, abstract, config),
    }


def classify_seed(
    title: str | None, abstract: str | None, config, csv_track: str | None
) -> dict[str, Any]:
    """Seeds/competitor_sok rows are already owner-curated: `track_human`
    comes straight from the CSV, `screen_auto` is forced to auto_include
    unconditionally. `track_auto` and the screening rule are still both
    computed for consistency-checking, not silently discarded."""
    computed = classify_paper(title, abstract, config, query_track=csv_track)
    computed_screen = computed["screen_auto"]
    return {
        "track_auto": computed["track_auto"],
        "track_human": csv_track,
        "screen_auto": "auto_include",
        "_computed_screen_for_consistency_check": computed_screen,
    }

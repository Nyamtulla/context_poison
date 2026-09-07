"""Human-facing label mappings shared between the dashboard and the editable
Excel data source (src/excel_source.py). Defined once here so the two never
drift apart - the Excel round-trip depends on these matching exactly.
"""
from __future__ import annotations

TRACK_DISPLAY_NAMES = {"A": "Security", "B": "ML/AI", "Both": "Both", "Unclear": "Unclear"}
SCREEN_DISPLAY_NAMES = {
    "auto_include": "Include",
    "auto_exclude": "Exclude",
    "needs_review": "Needs Review",
}

# Case-insensitive display-label (or raw code) -> internal code, for parsing
# hand-typed values back out of the spreadsheet. Unrecognized/blank values
# resolve to a safe default rather than silently breaking downstream
# filtering (Unclear / Needs Review, never a value nothing else recognizes).
_TRACK_LOOKUP = {}
for _code, _label in TRACK_DISPLAY_NAMES.items():
    _TRACK_LOOKUP[_code.lower()] = _code
    _TRACK_LOOKUP[_label.lower()] = _code

_SCREEN_LOOKUP = {}
for _code, _label in SCREEN_DISPLAY_NAMES.items():
    _SCREEN_LOOKUP[_code.lower()] = _code
    _SCREEN_LOOKUP[_label.lower()] = _code


def resolve_track(value) -> str:
    if value is None:
        return "Unclear"
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return "Unclear"
    return _TRACK_LOOKUP.get(text.lower(), "Unclear")


def resolve_screen(value) -> str:
    if value is None:
        return "needs_review"
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return "needs_review"
    return _SCREEN_LOOKUP.get(text.lower(), "needs_review")

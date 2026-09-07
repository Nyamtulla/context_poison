"""Venue name normalization for display purposes (dashboard filter/hover) -
raw venue strings from S2/arXiv/OpenAlex are wildly inconsistent (full
official names, mismatched arXiv casing, "Proceedings of the 49th..."
boilerplate). This never touches the DB's `venue` column - that stays the
raw source-of-record for provenance/replicability. Normalization happens
only where a human is choosing from a list or reading a label.

Order matters below - first regex match wins. Extend this list as new raw
venue strings show up that deserve a short form.
"""
from __future__ import annotations

import re

_VENUE_PATTERNS: list[tuple[str, str]] = [
    (r"\barxiv\b", "arXiv"),
    (r"neural information processing systems|\bnips\b|\bneurips\b", "NeurIPS"),
    (r"international conference on machine learning|\bicml\b", "ICML"),
    (r"international conference on learning representations|\biclr\b", "ICLR"),
    (r"aaai conference on artificial intelligence|\baaai\b", "AAAI"),
    (r"international joint conference on artificial intelligence|\bijcai\b", "IJCAI"),
    (r"computer vision and pattern recognition|\bcvpr\b", "CVPR"),
    (r"international conference on computer vision|\biccv\b", "ICCV"),
    (r"annual meeting of the association for computational linguistics", "ACL"),
    (r"empirical methods in natural language processing|\bemnlp\b", "EMNLP"),
    (r"north american chapter of the association for computational linguistics|\bnaacl\b", "NAACL"),
    (r"transactions of the association for computational linguistics|\btacl\b", "TACL"),
    (r"ieee symposium on security and privacy|ieee s&p", "IEEE S&P"),
    (r"conference on computer and communications security|\backm ccs\b", "ACM CCS"),
    (r"usenix security symposium|usenix security", "USENIX Security"),
    (r"network and distributed system security symposium|\bndss\b", "NDSS"),
    (r"european symposium on research in computer security|\besorics\b", "ESORICS"),
    (r"ieee international conference on robotics and automation|\bicra\b", "ICRA"),
    (r"intelligent robots and systems|\biros\b", "IROS"),
    (r"acoustics,?\s*speech,?\s*and signal processing|\bicassp\b", "ICASSP"),
    (r"\bthe web conference\b|\bwww conference\b", "WWW"),
    (r"international acm sigir conference|\bsigir\b", "SIGIR"),
    (r"knowledge discovery and data mining|\bsigkdd\b", "KDD"),
]
_COMPILED = [(re.compile(pat, re.IGNORECASE), name) for pat, name in _VENUE_PATTERNS]

# Fallback for anything not explicitly mapped above: pull out an embedded
# ACM SIG-style acronym if there is one (e.g. "...International ACM SIGCHI
# Conference..." -> "SIGCHI"), since that's usually the real short name.
_EMBEDDED_ACRONYM = re.compile(r"\bSIG[A-Z]{2,}\b")

# Strip "Proceedings of the 49th ..." / "Proceedings 2024 ..." boilerplate
# from anything left over so the fallback at least isn't as noisy.
_BOILERPLATE_PREFIX = re.compile(
    r"^proceedings(\s+of\s+the)?\s+(\d{4}\s+)?(\d+(st|nd|rd|th)\s+)?", re.IGNORECASE
)


def normalize_venue(raw: str | None) -> str | None:
    """Best-effort short/canonical form of a raw venue string. Falls back to
    a lightly-cleaned version of the original if nothing matches - never
    returns None for a non-empty input, never invents a venue that isn't
    there."""
    if raw is None or (isinstance(raw, float) and raw != raw):  # None or NaN
        return None
    if not isinstance(raw, str):
        raw = str(raw)
    if not raw:
        return raw
    text = raw.strip()
    for pattern, canonical in _COMPILED:
        if pattern.search(text):
            return canonical
    m = _EMBEDDED_ACRONYM.search(text)
    if m:
        return m.group(0)
    cleaned = _BOILERPLATE_PREFIX.sub("", text).strip()
    return cleaned or text

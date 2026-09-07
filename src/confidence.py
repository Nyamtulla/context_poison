"""High-confidence working-pool filter.

The rule-based auto-screen (FR-7) is intentionally loose/recall-oriented -
that's by design, so nothing gets lost before a human ever looks at it. But
at the volume keyword search + snowball actually produced (14,946 in the
hop 0+1 working set), a full two-coder manual pass isn't feasible. This
module computes a much smaller, precision-oriented subset for that
situation - a project-owner decision to substitute a stricter automated cut
for part of the manual screening pass, not something FR-7 anticipated on its
own.

Seeds and competitor_sok papers are included by default - they were already
manually curated (SRS Section 7.1), so an algorithmic filter shouldn't drop
one just because it doesn't happen to name one of the signature terms in its
own abstract (a paper very rarely cites itself by author name). The one
override: if a human has since explicitly excluded a paper (screen_human =
'auto_exclude' - e.g. by deleting its row from the working Excel sheet and
running the reconciliation that sets this), that decision wins even for a
seed. Screening is a human decision (NFR-4); once made, an automated filter
must not silently re-include what a person took out.

Everything else must:
  - pass the existing screen_auto == 'auto_include' rule (FR-7)
  - actually name a known method/author signature term in its title+abstract
    - a stronger precision signal than track_auto != 'Unclear', since a
      keyword-search-discovered paper gets a non-Unclear track just from
      which query cluster found it (FR-8's first signal), regardless of
      whether the text itself names anything specific
  - meet a minimum citation count (default 1) - a low bar meant to drop
    zero-traction noise, not to penalize very recent papers (the project
    plan's Section 9 flags citation-based cuts as a recency-bias risk,
    hence keeping this threshold deliberately low rather than e.g. >=5)

Nothing is deleted or modified in the DB (NFR-4) - this is a pure,
reproducible filter, re-runnable with different min_citations, and every
excluded paper is still sitting in the full DB/export for anyone who wants
to double-check the cut.
"""
from __future__ import annotations

from . import db


def has_signature_match(title: str | None, abstract: str | None, config) -> bool:
    text = f"{title or ''} {abstract or ''}".lower()
    sigs = config.track_signatures
    all_terms = [t.lower() for t in sigs.get("A", [])] + [t.lower() for t in sigs.get("B", [])]
    return any(t in text for t in all_terms)


def high_confidence_ids(conn, config, min_citations: int = 0, max_hop: int | None = None) -> set[str]:
    """max_hop scopes this to the current working set (e.g. hop<=1) rather
    than also reaching into the hop-2 archive, matching whatever the project
    has already decided is in scope. Seeds/competitor_sok are exempt from
    max_hop too - they're always hop 0 anyway."""
    ids: set[str] = set()
    for row in db.all_papers(conn):
        effective_screen = row["screen_human"] or row["screen_auto"]
        if effective_screen == "auto_exclude":
            continue  # human (or auto) exclusion always wins, seed or not

        if row["seed_category"]:
            ids.add(row["paper_id"])  # kept by default - already human-curated
            continue
        if max_hop is not None and row["hop"] > max_hop:
            continue
        if effective_screen != "auto_include":
            continue
        if (row["citation_count"] or 0) < min_citations:
            continue
        if has_signature_match(row["title"], row["abstract"], config):
            ids.add(row["paper_id"])
    return ids

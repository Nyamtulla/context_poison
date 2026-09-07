"""Structured database export (FR-10): CSV/JSON dump of the papers table,
matching the project plan's Section 3 coding-table shape. Blank columns for
the fields that stay a human judgment call (Channel, Consequence, Defense
intervention point, Temporal persistence, cross-citation flags, Evidence
grade) are appended so the manual coding pass can start directly from this
export — filling them in is out of scope for this tool (SRS Section 8), but
producing the scaffold is exactly what the SRS's Purpose section asks for.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone

from . import db

CODING_SCAFFOLD_COLUMNS = [
    "channel",
    "consequence",
    "defense_intervention_point",
    "temporal_persistence",
    "cites_track_a",
    "cites_track_b",
    "evidence_grade",
]


def export_all(
    conn,
    config,
    min_hop: int | None = None,
    max_hop: int | None = None,
    label: str | None = None,
    id_filter: set[str] | None = None,
) -> dict:
    """min_hop/max_hop and id_filter control which rows get exported; the DB
    itself is never touched by this - filtering here just controls what goes
    into a given export file, e.g. a hop-0+1 "working set" export alongside a
    separate hop-2 "archive" export, or a high-confidence subset (see
    src/confidence.py), with nothing ever deleted from the DB."""
    export_dir = config.path("export_dir")
    export_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = f"_{label}" if label else ""

    all_rows = [dict(r) for r in db.all_papers(conn)]
    rows = [
        r for r in all_rows
        if (min_hop is None or r["hop"] >= min_hop)
        and (max_hop is None or r["hop"] <= max_hop)
        and (id_filter is None or r["paper_id"] in id_filter)
    ]
    for r in rows:
        if r.get("authors"):
            try:
                r["authors"] = json.loads(r["authors"])
            except (TypeError, ValueError):
                pass
        for col in CODING_SCAFFOLD_COLUMNS:
            r[col] = ""

    json_path = export_dir / f"papers{suffix}_{timestamp}.json"
    with open(json_path, "w") as f:
        json.dump(rows, f, indent=2, default=str)

    csv_path = export_dir / f"papers{suffix}_{timestamp}.csv"
    fieldnames = list(db.PAPER_COLUMNS) + CODING_SCAFFOLD_COLUMNS
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            row_out = dict(r)
            if isinstance(row_out.get("authors"), list):
                row_out["authors"] = "; ".join(row_out["authors"])
            writer.writerow({k: row_out.get(k, "") for k in fieldnames})

    return {"json_path": str(json_path), "csv_path": str(csv_path), "row_count": len(rows)}

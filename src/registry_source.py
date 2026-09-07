"""Single loader for the RQ3/RQ4/RQ5 registries and the per-RQ write-ups.

Shared deliberately by both consumers of this data - the Streamlit dashboard
(`dashboard.py`) and the MCP server (`mcp_server/server.py`) - so the joins
that turn three separate JSON files into "a mechanism, with the defenses
tested against it" live in exactly one place. Returns plain Python
structures, not DataFrames, so the MCP server doesn't need pandas.

Everything is read from files already committed in the repo; nothing here
touches the network or the SQLite DB.
"""
from __future__ import annotations

import csv
import glob
import json
import re
from pathlib import Path

import openpyxl

REPO_ROOT = Path(__file__).resolve().parent.parent

PAPERS_XLSX = "data/exports/paper_dashboard_source.xlsx"
RQ3_JSON = "data/registries/rq3_pollution_registry.json"
RQ4_JSON = "data/registries/rq4_defense_registry.json"
RQ5_JSON = "data/registries/rq5_coverage_matrix.json"
RQ5_RAW_GLOB = "data/registries/raw/rq5_batch*.csv"

RQ_FILES = {
    "RQ1": ("rq1_taxonomy_analysis.md", "Taxonomy — which channel × intent × consequence cells have been studied"),
    "RQ2": ("cross_citation_analysis.md", "Citation network — do the two literatures cite each other"),
    "RQ3": ("rq3_pollution_census.md", "Pollution census — how many distinct poisoning mechanisms are named"),
    "RQ4": ("rq4_defense_census.md", "Defense census — how many defenses, validated against which threat model"),
    "RQ5": ("rq5_coverage_matrix.md", "Coverage matrix — which defenses were tested against which mechanisms"),
    "RQ6": ("rq6_case_studies.md", "Defense generalization — 9 reconstructed case studies"),
    "RQ7": ("rq7_open_problems.md", "Open problems — ranked research priorities"),
}


def _root(root: str | Path | None = None) -> Path:
    return Path(root) if root else REPO_ROOT


# ---------------------------------------------------------------- raw loads

def load_papers(root=None) -> list[dict]:
    """Every screened paper with its full extraction fields."""
    wb = openpyxl.load_workbook(_root(root) / PAPERS_XLSX, read_only=True)
    ws = wb["Papers"]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    if not rows:
        return []
    header = list(rows[0])
    return [dict(zip(header, r)) for r in rows[1:]]


def _load_justifications(root=None) -> dict:
    """(defense_row, mechanism_name) -> the extracting agent's rationale."""
    out = {}
    for fp in sorted(glob.glob(str(_root(root) / RQ5_RAW_GLOB))):
        with open(fp, newline="") as f:
            for row in csv.DictReader(f):
                key = (str(row.get("defense_row", "")).strip(),
                       row.get("matched_mechanism_name", "").strip())
                out[key] = row.get("match_justification", "")
    return out


def load_raw_registries(root=None):
    r = _root(root)
    mechs = json.loads((r / RQ3_JSON).read_text())
    defs = json.loads((r / RQ4_JSON).read_text())
    cov = json.loads((r / RQ5_JSON).read_text())
    return mechs, defs, cov


# ------------------------------------------------------------ enriched loads

def load_all(root=None) -> dict:
    """The whole picture, joined: mechanisms carry the defenses tested against
    them, defenses carry the mechanisms they were tested against, and every
    confirmed pair carries both sides' metadata plus the match rationale."""
    mechs, defs, cov = load_raw_registries(root)
    justif = _load_justifications(root)

    mech_to_defenses = cov["mech_to_defenses"]     # mechanism name -> [defense rows]
    defense_to_mechs = cov["defense_to_mechs"]     # defense row (str) -> [mechanism names]
    uncovered = set(cov["uncovered_mechanisms"])

    defs_by_row = {str(d["row"]): d for d in defs}
    mechs_by_name = {(m.get("technique_name") or m.get("name")): m for m in mechs}

    mechanisms = []
    for m in mechs:
        name = m.get("technique_name") or m.get("name")
        rows = mech_to_defenses.get(name, [])
        defender_names = [defs_by_row[str(r)].get("defense_name")
                          for r in rows if str(r) in defs_by_row]
        mechanisms.append({
            "mechanism_name": name,
            "track": m.get("track"),
            "channel": m.get("channel"),
            "consequence": m.get("consequence"),
            "confidence": m.get("confidence"),
            "n_defenses_tested": len(defender_names),
            "has_any_defense": name not in uncovered,
            "defenses_tested": defender_names,
            "is_extension_of": m.get("is_extension_of"),
            "notes": m.get("notes"),
            "source_paper_title": m.get("title"),
            "source_paper_id": m.get("paper_id"),
        })

    defenses = []
    for d in defs:
        tested = defense_to_mechs.get(str(d["row"]), [])
        defenses.append({
            "defense_name": d.get("defense_name"),
            "track": d.get("track"),
            "channel": d.get("channel"),
            "consequence": d.get("consequence"),
            "intervention_point": d.get("defense_intervention_point"),
            "validated_against": d.get("validated_against"),
            "confidence": d.get("confidence"),
            "n_mechanisms_tested": len(tested),
            "has_confirmed_match": len(tested) > 0,
            "mechanisms_tested": tested,
            "is_extension_of": d.get("is_extension_of"),
            "notes": d.get("notes"),
            "source_paper_title": d.get("title"),
            "source_paper_id": d.get("paper_id"),
            "_row": str(d["row"]),
        })

    pairs = []
    for match in cov["matches"]:
        row = str(match["defense_row"])
        d = defs_by_row.get(row, {})
        mech = mechs_by_name.get(match["mechanism_name"], {})
        pairs.append({
            "defense_name": match["defense_name"],
            "mechanism_name": match["mechanism_name"],
            "match_confidence": match.get("confidence"),
            "defense_track": d.get("track"),
            "defense_intervention_point": d.get("defense_intervention_point"),
            "defense_validated_against": d.get("validated_against"),
            "mechanism_track": mech.get("track"),
            "mechanism_channel": mech.get("channel"),
            "mechanism_consequence": mech.get("consequence"),
            "cross_track": bool(d.get("track") and mech.get("track")
                                and d.get("track") != mech.get("track")),
            "justification": justif.get((row, match["mechanism_name"]), ""),
            "defense_paper_title": d.get("title"),
        })

    return {
        "mechanisms": mechanisms,
        "defenses": defenses,
        "pairs": pairs,
        "uncovered_mechanism_names": sorted(uncovered),
        "stats": {
            "n_mechanisms": len(mechs),
            "n_defenses": len(defs),
            "n_pairs": cov["n_matched_pairs"],
            "n_defenses_matched": cov["n_defenses_matched"],
            "n_defenses_total": cov["n_defenses_total"],
            "n_mechs_covered": cov["n_mechs_covered"],
            "n_mechs_total": cov["n_mechs_total"],
            "n_mechs_uncovered": len(uncovered),
            "mechs_per_defense_distribution": cov.get("mechs_per_defense_distribution", {}),
            "top_mechanisms": cov.get("top_mechanisms", []),
        },
    }


def load_rq_summary(rq: str, root=None) -> str:
    """The '## Headline result' section of one RQ's write-up, verbatim."""
    entry = RQ_FILES.get(rq.strip().upper())
    if not entry:
        return ""
    path = _root(root) / entry[0]
    if not path.exists():
        return ""
    text = path.read_text()
    m = re.search(r"^## Headline result\s*\n(.*?)(?=\n## |\Z)", text, re.S | re.M)
    return m.group(1).strip() if m else text[:2000]

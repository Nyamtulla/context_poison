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
# Pairs recovered after RQ5 by the Stage 1 citation + full-text pass. Kept in a
# separate file, and tagged with `source` on every pair, so RQ5's originally
# published numbers stay recoverable rather than being silently overwritten.
RQ5_SUPP_JSON = "data/registries/rq5_supplementary_pairs.json"
# Pairs recovered by scanning ATTACK papers for defense names - the reverse of
# RQ5's direction. RQ5 read defense papers looking for mechanism names, which
# structurally cannot find a defense evaluated inside an attack paper published
# after it. Same file shape and the same precision-first bar as RQ5_SUPP_JSON.
ATTACK_EVAL_JSON = "data/registries/attack_paper_evaluations.json"
# Registry entries retracted after publication (e.g. duplicate-paper
# double-counts). Applied on load rather than edited into the registry JSONs,
# so the published figures stay reproducible with include_corrections=False.
CORRECTIONS_JSON = "data/registries/registry_corrections.json"

RQ_FILES = {
    "RQ1": ("rq1_taxonomy_analysis.md", "Taxonomy — which channel × intent × consequence cells have been studied"),
    "RQ2": ("cross_citation_analysis.md", "Citation network — do the two literatures cite each other"),
    "RQ3": ("rq3_pollution_census.md", "Pollution census — how many distinct poisoning mechanisms are named"),
    "RQ4": ("rq4_defense_census.md", "Defense census — how many defenses, validated against which threat model"),
    "RQ5": ("rq5_coverage_matrix.md", "Coverage matrix — which defenses were tested against which mechanisms"),
    "RQ6": ("rq6_case_studies.md", "Defense generalization — 9 reconstructed case studies"),
    # Companion to RQ6 rather than a research question of its own: turns RQ6's
    # intervention-point finding into a predictor and validates one prediction.
    "RQ6-transfer": ("rq6_transfer_predictions.md",
                     "Transfer predictions and their validation (RQ6 continued)"),
    "RQ7": ("rq7_open_problems.md", "Open problems — ranked research priorities"),
}

# Per-pair reported outcome, tagged with WHICH SIDE of the corpus reported it.
# Kept separate from the pairs themselves because the two sides disagree by
# construction and must never be collapsed into a single win rate.
PAIR_OUTCOMES_JSON = "data/registries/pair_outcomes.json"

STAGE2_JSON = "data/registries/stage2_transfer_predictions.json"
STAGE3_JSON = "data/registries/stage3_badrag_robustrag_results.json"


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

def _confirmed_pairs(path: Path, tag: str) -> list[dict]:
    if not path.exists():
        return []
    return [{**p, "_source_tag": tag}
            for p in json.loads(path.read_text()).get("confirmed_pairs", [])]


def load_supplementary(root=None) -> list[dict]:
    """Every pair recovered after RQ5's own pass, from both recovery
    directions: Stage 1 (defense papers -> mechanism names) and the reverse
    scan (attack papers -> defense names). Empty list if neither file exists."""
    r = _root(root)
    return (_confirmed_pairs(r / RQ5_SUPP_JSON, "stage1_supplementary")
            + _confirmed_pairs(r / ATTACK_EVAL_JSON, "attack_paper_scan"))


def load_corrections(root=None) -> dict:
    path = _root(root) / CORRECTIONS_JSON
    if not path.exists():
        return {"retracted_mechanisms": [], "retracted_defenses": []}
    return json.loads(path.read_text())


def load_all(root=None, include_supplementary: bool = True,
             include_corrections: bool = True) -> dict:
    """The whole picture, joined: mechanisms carry the defenses tested against
    them, defenses carry the mechanisms they were tested against, and every
    confirmed pair carries both sides' metadata plus the match rationale.

    Set include_supplementary=False to reproduce RQ5's originally published
    numbers exactly, without the Stage 1 recovery pass; include_corrections=False
    additionally restores entries later retracted as duplicates."""
    mechs, defs, cov = load_raw_registries(root)

    if include_corrections:
        corr = load_corrections(root)
        drop_m = {c["mechanism_name"] for c in corr.get("retracted_mechanisms", [])}
        drop_d = {c["defense_name"] for c in corr.get("retracted_defenses", [])}
        if drop_m:
            mechs = [m for m in mechs
                     if (m.get("technique_name") or m.get("name")) not in drop_m]
            cov["uncovered_mechanisms"] = [u for u in cov["uncovered_mechanisms"]
                                           if u not in drop_m]
            cov["mech_to_defenses"] = {k: v for k, v in cov["mech_to_defenses"].items()
                                       if k not in drop_m}
            cov["matches"] = [x for x in cov["matches"]
                              if x["mechanism_name"] not in drop_m]
        if drop_d:
            defs = [d for d in defs if d.get("defense_name") not in drop_d]
            cov["matches"] = [x for x in cov["matches"] if x["defense_name"] not in drop_d]
    justif = _load_justifications(root)

    mech_to_defenses = {k: list(v) for k, v in cov["mech_to_defenses"].items()}
    defense_to_mechs = {k: list(v) for k, v in cov["defense_to_mechs"].items()}
    uncovered = set(cov["uncovered_mechanisms"])

    supp = load_supplementary(root) if include_supplementary else []
    supp_pairs = []
    if supp:
        row_by_defense = {d.get("defense_name"): str(d["row"]) for d in defs}
        for p in supp:
            row = row_by_defense.get(p["defense"])
            if row is None:
                # Loud, not silent: a supplementary pair naming a defense that
                # isn't in the RQ4 registry means the two files have drifted
                # (usually a name typed slightly differently). Dropping it
                # quietly would lose an adjudicated result with no trace.
                raise ValueError(
                    f"recovered pair names defense {p['defense']!r}, which is not in the "
                    f"RQ4 registry - fix the name in the {p['_source_tag']} file to match exactly")
            mech_to_defenses.setdefault(p["mechanism"], []).append(int(row))
            defense_to_mechs.setdefault(row, []).append(p["mechanism"])
            uncovered.discard(p["mechanism"])
            supp_pairs.append({"defense_row": int(row), "defense_name": p["defense"],
                               "mechanism_name": p["mechanism"], "confidence": "high",
                               "justification": p.get("evidence", ""),
                               "outcome": p.get("outcome", ""),
                               "source": p["_source_tag"]})

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
    for match in list(cov["matches"]) + supp_pairs:
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
            "justification": match.get("justification")
                             or justif.get((row, match["mechanism_name"]), ""),
            "defense_paper_title": d.get("title"),
            "source": match.get("source", "rq5"),
            "outcome": match.get("outcome", ""),
        })

    return {
        "mechanisms": mechanisms,
        "defenses": defenses,
        "pairs": pairs,
        "uncovered_mechanism_names": sorted(uncovered),
        "stats": {
            "n_mechanisms": len(mechs),
            "n_defenses": len(defs),
            "n_pairs": len(pairs),
            "n_pairs_rq5_original": cov["n_matched_pairs"],
            "n_pairs_supplementary": len(supp_pairs),
            "n_pairs_attack_paper_scan": sum(1 for x in supp_pairs
                                             if x["source"] == "attack_paper_scan"),
            "n_defenses_matched": sum(1 for x in defenses if x["has_confirmed_match"]),
            "n_defenses_total": cov["n_defenses_total"],
            "n_mechs_covered": sum(1 for x in mechanisms if x["has_any_defense"]),
            "n_mechs_covered_rq5_original": cov["n_mechs_covered"],
            "n_mechs_total": cov["n_mechs_total"],
            "n_mechs_uncovered": len(uncovered),
            "mechs_per_defense_distribution": cov.get("mechs_per_defense_distribution", {}),
            "top_mechanisms": cov.get("top_mechanisms", []),
        },
    }


def load_pair_outcomes(root=None) -> list[dict]:
    """One row per confirmed pair: what outcome was reported, and by whom.

    `reported_by` is the load-bearing field. A defense paper reports a pair
    because its defense won; an attack paper reports the same pair because the
    defense lost. Averaging across both produces a number that means nothing,
    so callers are expected to split on it rather than aggregate over it.
    """
    path = _root(root) / PAIR_OUTCOMES_JSON
    return json.loads(path.read_text()) if path.exists() else []


def outcome_ledger(root=None) -> dict:
    """Per-defense and per-mechanism tallies, kept split by reporting side.

    Returns `defenses` and `mechanisms` maps plus `contested`: the defenses for
    which the corpus contains BOTH a win claimed by their own paper and an
    evaluation by a later attack paper. That subset is where the two halves of
    the literature can actually be compared against each other.
    """
    rows = load_pair_outcomes(root)
    defenses: dict[str, dict] = {}
    mechanisms: dict[str, dict] = {}
    for r in rows:
        d = defenses.setdefault(r["defense_name"],
                                {"wins_claimed_by_own_paper": 0,
                                 "evaluated_by_attack_papers": 0, "lost_to_attacks": 0})
        m = mechanisms.setdefault(r["mechanism_name"],
                                  {"defenses_claiming_to_stop_it": 0,
                                   "defenses_it_was_run_against": 0, "defenses_it_beat": 0})
        if r["reported_by"] == "defense_paper":
            d["wins_claimed_by_own_paper"] += 1
            m["defenses_claiming_to_stop_it"] += 1
        else:
            d["evaluated_by_attack_papers"] += 1
            m["defenses_it_was_run_against"] += 1
            if r["reported_verdict"] == "defense_loses_reported":
                d["lost_to_attacks"] += 1
                m["defenses_it_beat"] += 1
    contested = {k: v for k, v in defenses.items()
                 if v["wins_claimed_by_own_paper"] and v["evaluated_by_attack_papers"]}
    return {"defenses": defenses, "mechanisms": mechanisms, "contested": contested}


def load_transfer_predictions(root=None) -> list[dict]:
    """Stage 2 ranked transfer hypotheses (empty if not yet generated)."""
    path = _root(root) / STAGE2_JSON
    return json.loads(path.read_text()) if path.exists() else []


def load_stage3_result(root=None) -> dict:
    """Stage 3 validated transfer test (empty if not yet run)."""
    path = _root(root) / STAGE3_JSON
    return json.loads(path.read_text()) if path.exists() else {}


# Which defense stages can plausibly act on which channel. Used to separate the
# cells of the mechanism x defense grid that are worth testing from the ones
# that are meaningless - a supply-chain defense has no business being evaluated
# against a cross-modal attack, and counting those cells as "gaps" would inflate
# the untested space with pairs nobody should ever run.
STAGE_FITS_CHANNEL = {
    "RAG": {"ingestion", "reasoning"},
    "direct-input": {"ingestion", "reasoning"},
    "tool-output": {"ingestion", "execution"},
    "tool-metadata": {"ingestion", "execution"},
    "memory": {"ingestion", "reasoning", "execution"},
    "multi-agent": {"execution", "ingestion"},
    "skill": {"ingestion", "execution"},
    "supply-chain": {"execution", "ingestion"},
    "cross-modal": {"ingestion"},
}

#: Defenses with a working reconstruction in this project, and their stage.
#: These are the only defenses a transfer test can actually be run against
#: today, so they bound the testable gap rather than the theoretical one.
RECONSTRUCTED_DEFENSES = {
    "DataSentinel": "ingestion",
    "RobustRAG": "ingestion",
    "DataFilter": "ingestion",
    "PISanitizer": "ingestion",
    "IPIGuard": "execution",
    "CaMeL": "execution",
}


def taxonomy_dimensions(root=None) -> dict:
    """The axes the project measures on, with counts on each side.

    Returned per-axis rather than as one flat table because the mechanism and
    defense sides are differently shaped: channels are declared by both, stages
    only by defenses, consequences only by mechanisms.
    """
    from collections import Counter
    reg = load_all(root)
    M, D = reg["mechanisms"], reg["defenses"]

    def norm(v):
        return (v or "").strip() or None

    stages = Counter(norm(d["intervention_point"]) for d in D)
    ch_m = Counter(norm(m["channel"]) for m in M)
    ch_d = Counter(norm(d["channel"]) for d in D)
    cons = Counter(norm(m["consequence"]) for m in M)
    channels = sorted({c for c in set(ch_m) | set(ch_d) if c},
                      key=lambda c: -(ch_m.get(c, 0) + ch_d.get(c, 0)))
    return {
        "n_mechanisms": len(M),
        "n_defenses": len(D),
        "stages": [{"stage": k, "n_defenses": v} for k, v in stages.most_common()
                   if k and k.lower() != "none"],
        "stage_unspecified": sum(v for k, v in stages.items()
                                 if not k or k.lower() == "none"),
        "channels": [{"channel": c, "n_mechanisms": ch_m.get(c, 0),
                      "n_defenses": ch_d.get(c, 0)} for c in channels],
        "consequences": [{"consequence": k, "n_mechanisms": v}
                         for k, v in cons.most_common() if k],
        "tracks": {
            "mechanisms": dict(Counter(m["track"] for m in M)),
            "defenses": dict(Counter(d["track"] for d in D)),
        },
    }


def gap_scope(root=None) -> dict:
    """How large the untested space is, at four narrowing levels.

    The headline "0.26% of the grid is filled" is true and useless on its own,
    because most of the grid should never be tested. Each level below removes a
    class of cell that is not worth running, so the last number is the one an
    experimental campaign can actually be planned against.
    """
    reg = load_all(root)
    M, D = reg["mechanisms"], reg["defenses"]
    filled = {(p["defense_name"], p["mechanism_name"]) for p in reg["pairs"]}

    # Level 3: the defense is already validated somewhere (so a transfer claim
    # is meaningful) and its stage fits the mechanism's channel.
    validated = [d for d in D if d["n_mechanisms_tested"] > 0]
    compatible = runnable = 0
    per_defense: dict[str, int] = {}
    for d in validated:
        stage = (d["intervention_point"] or "").strip().lower()
        if not stage or stage == "none":
            continue
        for m in M:
            if (d["defense_name"], m["mechanism_name"]) in filled:
                continue
            if stage in STAGE_FITS_CHANNEL.get((m["channel"] or "").strip(), set()):
                compatible += 1
                if RECONSTRUCTED_DEFENSES.get(d["defense_name"]) == stage:
                    runnable += 1
                    per_defense[d["defense_name"]] = per_defense.get(d["defense_name"], 0) + 1
    return {
        "grid_cells": len(M) * len(D),
        "filled": len(filled),
        "compatible_untested": compatible,
        "runnable_untested": runnable,
        "runnable_by_defense": dict(sorted(per_defense.items(), key=lambda kv: -kv[1])),
        "reconstructed_defenses": RECONSTRUCTED_DEFENSES,
    }


def paper_link(p: dict) -> tuple[str, str]:
    """Best external link for a paper, as (url, label). Prefers arXiv (lands on
    the paper itself), then DOI, then whatever URL the pipeline recorded -
    which is usually a Semantic Scholar landing page. Local PDF paths are
    deliberately NOT used: they're server-side paths a browser can't open, and
    the PDFs aren't in the repo anyway."""
    arxiv = (p.get("arxiv_id") or "").strip()
    if arxiv:
        return f"https://arxiv.org/abs/{arxiv}", "arXiv"
    doi = (p.get("doi") or "").strip()
    if doi:
        return f"https://doi.org/{doi}", "DOI"
    url = (p.get("url") or "").strip()
    if url:
        return url, "S2"
    return "", ""


def load_rq_summary(rq: str, root=None) -> str:
    """The '## Headline result' section of one RQ's write-up, verbatim."""
    # Case-insensitive without uppercasing the key itself - "RQ5b".upper() is
    # "RQ5B", which matches no entry.
    wanted = rq.strip().casefold()
    entry = next((v for k, v in RQ_FILES.items() if k.casefold() == wanted), None)
    if not entry:
        return ""
    path = _root(root) / entry[0]
    if not path.exists():
        return ""
    text = path.read_text()
    m = re.search(r"^## Headline result\s*\n(.*?)(?=\n## |\Z)", text, re.S | re.M)
    return m.group(1).strip() if m else text[:2000]

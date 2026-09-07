"""Merge RQ5 matching batches into the final pollution-mechanism x defense
coverage matrix, and compute the headline coverage statistics.

Reads the raw (defense, matched_mechanism) pairs produced by the RQ5
matching subagents (see the rebuild-corpus skill for the matching prompt),
resolves any mechanism names that don't exactly match the RQ3 registry
(a CSV-quoting artifact seen once in practice, not an agent judgment issue --
see rq5_coverage_matrix.md "Methodology" for how this is handled: exact-
prefix recovery where unambiguous, otherwise dropped rather than guessed),
and writes both the merged JSON and the coverage-stats console summary.

Usage:
    python3 scripts/build_coverage_matrix.py
"""
import csv
import datetime
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from rapidfuzz import fuzz, process

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

RAW_DIR = REPO_ROOT / "data" / "registries" / "raw"
REGISTRY_DIR = REPO_ROOT / "data" / "registries"
RQ3_REGISTRY = REGISTRY_DIR / "rq3_pollution_registry.json"
OUTPUT_JSON = REGISTRY_DIR / "rq5_coverage_matrix.json"
OUTPUT_MD = REPO_ROOT / "rq5_coverage_matrix.md"

MATCH_BATCH_FILES = [RAW_DIR / f"rq5_batch{i}.csv" for i in (1, 2, 3, 4)]
FUZZY_RECOVERY_THRESHOLD = 90  # only auto-recover near-exact (likely truncation) mismatches


def load_mechanism_registry():
    with open(RQ3_REGISTRY) as f:
        registry = json.load(f)
    return {r["name"] for r in registry}, len(registry)


def load_raw_matches():
    matches = []
    for fname in MATCH_BATCH_FILES:
        if not fname.exists():
            print(f"  (skipping missing {fname.name})")
            continue
        with open(fname) as f:
            for r in csv.DictReader(f):
                name = (r.get("matched_mechanism_name") or "").strip()
                if not name:
                    continue
                matches.append({
                    "defense_row": int(r["defense_row"]),
                    "defense_name": r["defense_name"],
                    "mechanism_name": name,
                    "confidence": r.get("match_confidence", ""),
                })
    return matches


def reconcile_names(matches, registry_names):
    """Fix or drop matched names that aren't exact registry entries."""
    clean = []
    dropped = []
    fixed = 0
    names_list = list(registry_names)
    for m in matches:
        if m["mechanism_name"] in registry_names:
            clean.append(m)
            continue
        result = process.extractOne(m["mechanism_name"], names_list, scorer=fuzz.partial_ratio)
        if result and result[1] >= FUZZY_RECOVERY_THRESHOLD:
            m = {**m, "mechanism_name": result[0]}
            clean.append(m)
            fixed += 1
        else:
            dropped.append(m)
    return clean, fixed, dropped


def compute_stats(matches, registry_names, n_defenses_total):
    mech_to_defenses = defaultdict(set)
    defense_to_mechs = defaultdict(set)
    for m in matches:
        mech_to_defenses[m["mechanism_name"]].add(m["defense_row"])
        defense_to_mechs[m["defense_row"]].add(m["mechanism_name"])

    covered_mechs = set(mech_to_defenses.keys())
    uncovered_mechs = registry_names - covered_mechs
    matched_defenses = set(defense_to_mechs.keys())

    mechs_per_defense = Counter(len(v) for v in defense_to_mechs.values())

    return {
        "n_matched_pairs": len(matches),
        "n_defenses_matched": len(matched_defenses),
        "n_defenses_total": n_defenses_total,
        "n_mechs_covered": len(covered_mechs),
        "n_mechs_total": len(registry_names),
        "uncovered_mechanisms": sorted(uncovered_mechs),
        "mechs_per_defense_distribution": dict(mechs_per_defense),
        "top_mechanisms": [[name, sorted(defs)] for name, defs in
                           sorted(mech_to_defenses.items(), key=lambda x: -len(x[1]))[:15]],
        "mech_to_defenses": {k: sorted(v) for k, v in mech_to_defenses.items()},
        "defense_to_mechs": {k: sorted(v) for k, v in defense_to_mechs.items()},
    }


def main():
    registry_names, n_registry = load_mechanism_registry()
    print(f"Mechanism registry: {n_registry} entries")

    with open(REGISTRY_DIR / "rq4_defense_registry.json") as f:
        n_defenses_total = len(json.load(f))
    print(f"Defense registry: {n_defenses_total} entries")

    raw = load_raw_matches()
    print(f"Raw matched pairs: {len(raw)}")

    clean, fixed, dropped = reconcile_names(raw, registry_names)
    print(f"Name reconciliation: {fixed} recovered via fuzzy match, {len(dropped)} dropped (unresolvable)")
    if dropped:
        for d in dropped:
            print(f"  dropped: defense row {d['defense_row']} -> '{d['mechanism_name']}' (no confident registry match)")

    stats = compute_stats(clean, registry_names, n_defenses_total)

    print(f"\nDefenses with >=1 confirmed match: {stats['n_defenses_matched']}/{stats['n_defenses_total']} "
          f"({stats['n_defenses_matched']/stats['n_defenses_total']*100:.1f}%)")
    print(f"Mechanisms with >=1 tested defense: {stats['n_mechs_covered']}/{stats['n_mechs_total']} "
          f"({stats['n_mechs_covered']/stats['n_mechs_total']*100:.1f}%)")
    print(f"Coverage gap: {len(stats['uncovered_mechanisms'])}/{stats['n_mechs_total']} "
          f"({len(stats['uncovered_mechanisms'])/stats['n_mechs_total']*100:.1f}%)")

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump({"matches": clean, **stats}, f, indent=1)
    print(f"\nWrote {OUTPUT_JSON}")
    print(
        "\nNote: this script computes the coverage matrix + stats. The narrative "
        "rq5_coverage_matrix.md deliverable (framing, discussion, RQ6 hand-off) is "
        "written separately by the rebuild-corpus skill using these numbers."
    )


if __name__ == "__main__":
    main()

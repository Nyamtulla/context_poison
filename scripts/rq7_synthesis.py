"""Compute the derived statistics RQ7 (open problems) synthesizes from the
RQ2, RQ4, RQ5 and RQ6 outputs.

RQ7 introduces no new extraction and no new judgment -- it is a synthesis pass
over already-built artifacts. This script computes the cross-cutting numbers
that aren't reported by any single earlier RQ's own script, principally:

  1. Track-crossing in the RQ5 coverage matrix -- for each confirmed
     (defense, mechanism) test pair, does the defense come from the same
     research community (track) as the mechanism it was tested against?
     This is the number that connects RQ2's citation-disconnect finding to
     RQ5's coverage finding: it measures whether the two communities test
     each other's mechanisms, not merely whether they cite each other.
  2. Coverage-gap concentration -- which tracks, channels and consequences
     the 116 uncovered mechanisms fall into, i.e. where the field's
     undefended surface actually is.
  3. The profile of the 14 defenses validated against both threat models,
     used to argue dual-validation is a norms problem rather than a
     technical-feasibility one.
  4. Injection-variant dispersion -- how much of the matrix's apparent
     concentration on "Indirect Prompt Injection (IPI)" coexists with
     untested concrete injection variants.

Usage:
    python3 scripts/rq7_synthesis.py
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

REGISTRY_DIR = REPO_ROOT / "data" / "registries"
RQ3_REGISTRY = REGISTRY_DIR / "rq3_pollution_registry.json"
RQ4_REGISTRY = REGISTRY_DIR / "rq4_defense_registry.json"
RQ5_MATRIX = REGISTRY_DIR / "rq5_coverage_matrix.json"
OUTPUT_JSON = REGISTRY_DIR / "rq7_synthesis_stats.json"

# The umbrella registry entry that absorbs the single largest share of the
# coverage matrix; RQ7 asks whether it is one mechanism or a category label.
UMBRELLA_MECHANISM = "Indirect Prompt Injection (IPI)"


def load():
    mechanisms = {m["name"]: m for m in json.loads(RQ3_REGISTRY.read_text())}
    defenses = defaultdict(list)
    for d in json.loads(RQ4_REGISTRY.read_text()):
        defenses[d["name"]].append(d)
    matrix = json.loads(RQ5_MATRIX.read_text())
    return mechanisms, defenses, matrix


def cross_track_testing(mechanisms, defenses, matrix):
    """For every confirmed test pair, compare the defense's track to the
    mechanism's track. A pair is 'cross-track' when a defense produced by one
    research community was evaluated against a mechanism named by the other."""
    pairs = Counter()
    cross_examples = []
    unresolved = []
    for match in matrix["matches"]:
        mech = mechanisms.get(match["mechanism_name"])
        defense_entries = defenses.get(match["defense_name"])
        if mech is None or not defense_entries:
            unresolved.append(match)
            continue
        defense = defense_entries[0]
        pairs[(defense["track"], mech["track"])] += 1
        if defense["track"] != mech["track"]:
            cross_examples.append({
                "defense": defense["name"],
                "defense_track": defense["track"],
                "validated_against": defense["validated_against"],
                "mechanism": mech["name"],
                "mechanism_track": mech["track"],
            })
    total = sum(pairs.values())
    # "Both"-track defenses are excluded from the same/cross split: a defense
    # already filed as spanning both communities can't evidence a crossing.
    same = sum(n for (dt, mt), n in pairs.items() if dt == mt)
    genuine_cross = [e for e in cross_examples if e["defense_track"] != "Both"]
    return {
        "pair_counts": {f"{dt} defense x {mt} mechanism": n for (dt, mt), n in pairs.most_common()},
        "total_pairs": total,
        "same_track": same,
        "same_track_share": same / total if total else 0.0,
        "cross_track": total - same,
        "cross_track_share": (total - same) / total if total else 0.0,
        "genuine_cross_track_pairs": genuine_cross,
        "unresolved": len(unresolved),
    }


def coverage_gaps(mechanisms, matrix):
    """Where the 116 mechanisms with zero tested defenses actually sit."""
    uncovered = [mechanisms[n] for n in matrix["uncovered_mechanisms"] if n in mechanisms]
    out = {"n_uncovered": len(uncovered)}
    for field in ("track", "channel", "consequence"):
        totals = Counter(m[field] for m in mechanisms.values())
        missing = Counter(m[field] for m in uncovered)
        out[f"by_{field}"] = {
            key: {
                "total": total,
                "covered": total - missing.get(key, 0),
                "uncovered": missing.get(key, 0),
                "coverage_rate": (total - missing.get(key, 0)) / total,
            }
            for key, total in totals.most_common()
        }
    return out


def dual_validation_profile(defenses):
    """The 14 defenses their own paper validated against both threat models.
    If these cluster in one intervention point or one track, dual validation
    is structurally constrained; if they're spread, it's a norms question."""
    both = [d for entries in defenses.values() for d in entries
            if d["validated_against"] == "both"]
    return {
        "n": len(both),
        "by_intervention_point": dict(Counter(d["defense_intervention_point"] for d in both)),
        "by_track": dict(Counter(d["track"] for d in both)),
        "names": [{"name": d["name"], "track": d["track"],
                   "intervention_point": d["defense_intervention_point"],
                   "channel": d["channel"]} for d in both],
    }


def injection_dispersion(mechanisms, matrix):
    """The umbrella entry absorbs the largest share of all testing; meanwhile
    concrete injection variants sit untested. Quantify both halves."""
    covered = set(matrix["mech_to_defenses"].keys())
    variants = [m for m in mechanisms.values() if "inject" in m["name"].lower()]
    variants_covered = [m for m in variants if m["name"] in covered]
    umbrella_defenses = matrix["mech_to_defenses"].get(UMBRELLA_MECHANISM, [])
    return {
        "umbrella_mechanism": UMBRELLA_MECHANISM,
        "defenses_tested_against_umbrella": len(umbrella_defenses),
        "share_of_all_pairs": len(umbrella_defenses) / matrix["n_matched_pairs"],
        "named_injection_variants": len(variants),
        "named_injection_variants_covered": len(variants_covered),
        "named_injection_variants_uncovered": len(variants) - len(variants_covered),
    }


def main():
    mechanisms, defenses, matrix = load()
    stats = {
        "cross_track_testing": cross_track_testing(mechanisms, defenses, matrix),
        "coverage_gaps": coverage_gaps(mechanisms, matrix),
        "dual_validation": dual_validation_profile(defenses),
        "injection_dispersion": injection_dispersion(mechanisms, matrix),
    }
    OUTPUT_JSON.write_text(json.dumps(stats, indent=2))

    ct = stats["cross_track_testing"]
    print("=== Cross-track testing in the RQ5 coverage matrix ===")
    for label, n in ct["pair_counts"].items():
        print(f"  {label:44s} {n:4d}")
    print(f"  same-track  {ct['same_track']}/{ct['total_pairs']} = {ct['same_track_share']:.1%}")
    print(f"  cross-track {ct['cross_track']}/{ct['total_pairs']} = {ct['cross_track_share']:.1%}")
    for e in ct["genuine_cross_track_pairs"]:
        print(f"    {e['defense']} ({e['defense_track']}) -> {e['mechanism']} ({e['mechanism_track']})")

    print("\n=== Coverage gaps ===")
    for field in ("track", "consequence", "channel"):
        print(f"  by {field}:")
        for key, v in stats["coverage_gaps"][f"by_{field}"].items():
            print(f"    {key:24s} {v['covered']:3d}/{v['total']:3d} covered = {v['coverage_rate']:5.1%}")

    dv = stats["dual_validation"]
    print(f"\n=== Dual-threat-model validation (n={dv['n']}) ===")
    print(f"  by intervention point: {dv['by_intervention_point']}")
    print(f"  by track:              {dv['by_track']}")

    inj = stats["injection_dispersion"]
    print("\n=== Injection dispersion ===")
    print(f"  {inj['defenses_tested_against_umbrella']} defenses tested against the umbrella entry "
          f"({inj['share_of_all_pairs']:.1%} of all pairs)")
    print(f"  {inj['named_injection_variants_uncovered']} of {inj['named_injection_variants']} "
          f"named injection variants have zero tested defenses")

    print(f"\nWrote {OUTPUT_JSON}")


if __name__ == "__main__":
    main()

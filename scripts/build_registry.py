"""Merge and deduplicate raw subagent-extraction batches into a registry.

Used for both RQ3 (pollution mechanisms: named attacks + named incidental
degradation phenomena) and RQ4 (named defenses). The raw batches are
per-paper judgments produced by parallel subagents (see the
rebuild-corpus skill for the extraction prompts) -- this script does the
part that needs to see everything at once: exact-name dedup, then fuzzy-name
dedup to catch near-duplicate phrasing, cross-checked against
scripts/dedupe_corpus.py's confirmed-duplicate-paper exclusions so a paper
excluded there doesn't also contribute a phantom registry entry here.

Usage:
    python3 scripts/build_registry.py rq3   # pollution mechanism registry
    python3 scripts/build_registry.py rq4   # defense registry
"""
import argparse
import csv
import datetime
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from rapidfuzz import fuzz

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

RAW_DIR = REPO_ROOT / "data" / "registries" / "raw"
REGISTRY_DIR = REPO_ROOT / "data" / "registries"

# For each registry: which raw batch files to read, which column holds the
# candidate name, which column holds the Y/N "did this paper contribute an
# entry" flag, and (for RQ3, which is split across two separately-run
# extraction passes) a fixed track to stamp on every row from that file.
# RQ4's raw batches already carry their own `track` column per row.
REGISTRY_CONFIGS = {
    "rq3": {
        "label": "Context Pollution Mechanism",
        "output_json": REGISTRY_DIR / "rq3_pollution_registry.json",
        "sources": [
            (RAW_DIR / "rq3_track_a_batch1.csv", "technique_name", "has_technique", "Security"),
            (RAW_DIR / "rq3_track_a_batch2.csv", "technique_name", "has_technique", "Security"),
            (RAW_DIR / "rq3_track_b_batch1.csv", "mechanism_name", "has_mechanism", "ML/AI"),
            (RAW_DIR / "rq3_track_b_batch2.csv", "mechanism_name", "has_mechanism", "ML/AI"),
        ],
    },
    "rq4": {
        "label": "Defense Technique",
        "output_json": REGISTRY_DIR / "rq4_defense_registry.json",
        "sources": [
            (RAW_DIR / "rq4_batch1.csv", "defense_name", "has_defense", None),
            (RAW_DIR / "rq4_batch2.csv", "defense_name", "has_defense", None),
            (RAW_DIR / "rq4_batch3.csv", "defense_name", "has_defense", None),
            (RAW_DIR / "rq4_batch4.csv", "defense_name", "has_defense", None),
        ],
    },
}

FUZZY_THRESHOLD = 75


def load_excluded_rows():
    """Rows scripts/dedupe_corpus.py has confirmed as duplicate papers --
    their registry contributions must not double-count against their twin."""
    import openpyxl
    wb = openpyxl.load_workbook(REPO_ROOT / "data" / "exports" / "paper_dashboard_source.xlsx",
                                 read_only=True, data_only=True)
    ws = wb["Papers"]
    header = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    idx = {name: i for i, name in enumerate(header)}
    excluded = set()
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if row[idx["screening"]] == "Exclude":
            excluded.add(row_idx)
    wb.close()
    return excluded


def load_raw(config, excluded_rows):
    raw = []
    for fname, name_col, has_col, fixed_track in config["sources"]:
        if not fname.exists():
            print(f"  (skipping missing {fname.name} -- no raw batch produced yet)")
            continue
        with open(fname) as f:
            for r in csv.DictReader(f):
                row_num = int(r["row"]) if "row" in r else int(r.get("defense_row", 0))
                if row_num in excluded_rows:
                    continue
                if r.get(has_col, "N") != "Y":
                    continue
                entry = dict(r)
                entry["row"] = row_num
                entry["name"] = r[name_col].strip()
                if fixed_track:
                    entry["track"] = fixed_track
                raw.append(entry)
    return raw


def exact_dedup(raw):
    groups = defaultdict(list)
    for r in raw:
        key = r["name"].lower().strip()
        groups[key].append(r)
    merged = []
    exact_dupe_groups = []
    for key, group in groups.items():
        merged.append(group[0])
        if len(group) > 1:
            exact_dupe_groups.append(group)
    return merged, exact_dupe_groups


def fuzzy_candidates(entries, threshold=FUZZY_THRESHOLD):
    """Report-only: surfaces near-duplicate NAME pairs for human review.
    Does not auto-merge -- see rq3_pollution_census.md / rq4_defense_census.md
    for the reasoning (most near-duplicate names turn out to be distinct
    techniques with a coincidentally similar naming convention, not the same
    technique; a small minority are genuine duplicate *papers*, which belong
    in scripts/dedupe_corpus.py, not here)."""
    candidates = []
    for i in range(len(entries)):
        for j in range(i + 1, len(entries)):
            n1, n2 = entries[i]["name"], entries[j]["name"]
            if n1.lower().startswith("unnamed:") or n2.lower().startswith("unnamed:"):
                continue
            score = fuzz.token_sort_ratio(n1, n2)
            if score >= threshold:
                candidates.append((score, entries[i], entries[j]))
    candidates.sort(key=lambda x: -x[0])
    return candidates


def render_report(kind, config, merged, exact_dupe_groups, fuzzy_pairs):
    label = config["label"]
    lines = []
    lines.append(f"# {kind.upper()} -- {label} Registry (auto-generated)")
    lines.append("")
    lines.append(f"Regenerated {datetime.date.today().isoformat()} by `scripts/build_registry.py {kind}`.")
    lines.append("")
    lines.append(f"**Registry size: {len(merged)} distinct entries.**")
    lines.append("")
    if "track" in (merged[0] if merged else {}):
        by_track = Counter(e.get("track", "?") for e in merged)
        lines.append("By track:")
        for tr, c in by_track.most_common():
            lines.append(f"- {tr}: {c}")
        lines.append("")
    lines.append(f"Exact-name duplicate groups found (merged automatically): {len(exact_dupe_groups)}")
    lines.append(f"Fuzzy near-duplicate name pairs (>= {FUZZY_THRESHOLD} similarity, flagged for manual review, NOT auto-merged): {len(fuzzy_pairs)}")
    if fuzzy_pairs:
        lines.append("")
        lines.append("| Similarity | Name 1 (row) | Name 2 (row) |")
        lines.append("|---:|---|---|")
        for score, e1, e2 in fuzzy_pairs:
            lines.append(f"| {score:.0f} | {e1['name']} (row {e1['row']}) | {e2['name']} (row {e2['row']}) |")
        lines.append("")
        lines.append("**Action needed:** for each pair above, check whether it's (a) two distinct "
                      "techniques with a coincidentally similar name -- the common case, no action "
                      "needed -- or (b) the same underlying paper indexed twice under a slightly "
                      "different title, which is a corpus-level duplicate to fix via "
                      "`scripts/dedupe_corpus.py --apply <row>`, not a registry-merge issue.")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("kind", choices=list(REGISTRY_CONFIGS))
    args = parser.parse_args()

    config = REGISTRY_CONFIGS[args.kind]
    excluded_rows = load_excluded_rows()
    raw = load_raw(config, excluded_rows)
    print(f"Raw candidates (post duplicate-paper exclusion): {len(raw)}")

    merged, exact_dupe_groups = exact_dedup(raw)
    print(f"After exact-name dedup: {len(merged)}")

    fuzzy_pairs = fuzzy_candidates(merged)
    print(f"Fuzzy near-duplicate pairs flagged for review: {len(fuzzy_pairs)}")

    config["output_json"].parent.mkdir(parents=True, exist_ok=True)
    with open(config["output_json"], "w") as f:
        json.dump(merged, f, indent=1)
    print(f"Wrote {config['output_json']} ({len(merged)} entries)")

    report_path = REPO_ROOT / f"{args.kind}_registry_report.md"
    report = render_report(args.kind, config, merged, exact_dupe_groups, fuzzy_pairs)
    report_path.write_text(report)
    print(f"Wrote {report_path}")
    print(
        "\nNote: this script produces the merged registry + a fuzzy-dedup review "
        "report. The narrative .md deliverables (rq3_pollution_census.md, "
        "rq4_defense_census.md) with distribution stats and discussion are "
        "written separately -- see the rebuild-corpus skill, which regenerates "
        "those after reviewing this script's fuzzy-pair output."
    )


if __name__ == "__main__":
    main()

"""Re-derive every contribution-screen finding from the coded spreadsheets.

The screener shipped five summary CSVs alongside the 17 coded packets. One of
them, `mismatch-claim-vs-evaluation.csv`, was built by a substring search that
could not tell `CLAIM/EVALUATION MISMATCH` from `No CLAIM/EVALUATION MISMATCH`,
so it reported 291 rows where 129 are genuine. The per-paper judgement in the
spreadsheets was sound - an independent audit verified all 982 evidence quotes
against the PDFs and found none fabricated - but the derived files disagreed
with it.

Four of the five summaries were produced by the same kind of notes-text filter.
So rather than check them one at a time, this recomputes every finding from the
`papers` sheet of each packet, which is the source of truth, and prints the
difference against what the screener reported. Nothing here reads a CSV the
screener wrote.

Run: python3 scripts/rederive_screen.py
Out: data/registries/screen_findings/*.csv  plus a printed reconciliation.
"""
from __future__ import annotations

import collections
import csv
import glob
import json
import pathlib
import re

import openpyxl

REPO = pathlib.Path(__file__).resolve().parent.parent
BUNDLES = REPO / "data" / "exports" / "contribution_screen" / "bundles"
OUT = REPO / "data" / "registries" / "screen_findings"
MARK = "CLAIM/EVALUATION MISMATCH"

# what the screener's own README claimed, so any drift is visible
REPORTED = {"rows": 982, "mismatch": 291, "out_of_scope": 57,
            "registry_disagreements": 430, "unsure": 7}

CONTRIBUTES = {"proposes_attack", "proposes_mechanism", "proposes_defense",
               "proposes_fix", "improves_existing"}


def load_rows():
    """Every coded row, from the `papers` sheet of every packet."""
    rows = []
    for f in sorted(glob.glob(str(BUNDLES / "packet-*" / "*.xlsx"))):
        wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
        if "papers" not in wb.sheetnames:
            wb.close()
            continue
        grid = list(wb["papers"].iter_rows(values_only=True))
        wb.close()
        hdr = [str(c or "").strip() for c in grid[0]]
        idx = {h: i for i, h in enumerate(hdr)}
        packet = pathlib.Path(f).parent.name
        for r in grid[1:]:
            if not r or not r[idx["title"]]:
                continue
            d = {h: ("" if r[i] is None else str(r[i]).strip())
                 for h, i in idx.items()}
            d["packet"] = packet
            rows.append(d)
    return rows


def is_mismatch(notes: str):
    """True only when the marker is ASSERTED, not negated.

    The screener writes the marker at the start of a note when the mismatch
    applies, sometimes after a `DEFENSE-NAMES: ...` prefix, and writes it
    inside a negation ("No ...", "NOT a ...", "does NOT apply") when it does
    not. Returns (verdict, why) so the unclassified case is visible instead of
    being silently bucketed.
    """
    n = (notes or "").strip()
    i = n.find(MARK)
    if i < 0:
        return False, "absent"
    pre = n[:i].strip()
    if pre == "":
        return True, "asserted"
    if re.fullmatch(r"DEFENSE-NAMES:[^.]*\.", pre):
        return True, "asserted after DEFENSE-NAMES prefix"
    if re.search(r"\b(no|not|never|neither)\b[^.]{0,40}$", pre, re.I):
        return False, "negated"
    # the marker appears mid-note with no negator in the trailing clause:
    # refuse to guess, and let the caller see it
    return None, "unclassified"


def registry_kind(entry: str) -> str:
    e = (entry or "").strip().lower()
    if e.startswith("defense:"):
        return "defense"
    if e.startswith("mechanism:"):
        return "mechanism"
    return "none"


def coded_kind(contribution: str) -> str:
    """What the coded contribution implies the registry entry should be."""
    c = (contribution or "").strip()
    if c in ("proposes_attack",):
        return "attack"
    if c in ("proposes_defense",):
        return "defense"
    if c in ("proposes_mechanism",):
        return "mechanism"
    if c in ("proposes_fix",):
        return "fix"
    return "none"


def write(name, rows, fields):
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / name, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {name}: {len(rows)} rows")


def main():
    rows = load_rows()
    print(f"loaded {len(rows)} coded rows from the packets "
          f"(screener reported {REPORTED['rows']})\n")

    # ---- contribution census
    print("contribution:")
    for k, v in collections.Counter(r["contribution"] for r in rows).most_common():
        print(f"  {v:>4}  {k}")

    # ---- removals
    removals = [r for r in rows if r["belongs_in_corpus"].lower() == "no"]
    bad = [r for r in removals
           if r["contribution"] != "out_of_scope"
           or not r["evidence_quote"]
           or r["names_registry_technique"].lower() == "yes"
           or r["contribution"] in CONTRIBUTES]
    print(f"\nremovals (belongs_in_corpus=no): {len(removals)}  "
          f"(screener reported {REPORTED['out_of_scope']})")
    print(f"  violating a guard: {len(bad)}")
    print(f"  that hold a registry entry: "
          f"{sum(1 for r in removals if registry_kind(r['current registry entry']) != 'none')}")

    # ---- mismatch, computed properly
    verdicts = collections.Counter()
    mismatch, unclear = [], []
    for r in rows:
        v, why = is_mismatch(r["notes"])
        verdicts[why] += 1
        if v is True:
            mismatch.append(r)
        elif v is None:
            unclear.append(r)
    print(f"\nclaim/evaluation mismatch: {len(mismatch)}  "
          f"(screener reported {REPORTED['mismatch']})")
    for k, v in verdicts.most_common():
        print(f"  {v:>4}  {k}")
    if unclear:
        print("  UNCLASSIFIED, read these yourself:")
        for r in unclear:
            n = r["notes"]
            i = n.find(MARK)
            print(f"    {r['packet']} #{r['#']}: ...{n[max(0,i-90):i+30]!r}")

    # ---- registry disagreements, recomputed from the two label columns
    dis = []
    for r in rows:
        have = registry_kind(r["current registry entry"])
        want = coded_kind(r["contribution"])
        conflict = None
        if have == "defense" and want in ("fix", "none"):
            conflict = f"filed defense, coded {r['contribution']}"
        elif have == "mechanism" and want == "attack":
            conflict = "filed mechanism (non-adversarial), coded proposes_attack"
        elif have == "none" and want in ("attack", "defense", "mechanism"):
            conflict = f"no registry entry, coded {r['contribution']}"
        elif have == "defense" and want == "attack":
            conflict = "filed defense, coded proposes_attack"
        if conflict:
            dis.append({**r, "disagreement": conflict})
    print(f"\nregistry disagreements (kind only): {len(dis)}  "
          f"(screener reported {REPORTED['registry_disagreements']}, "
          f"which also counted origin-only conflicts)")
    for k, v in collections.Counter(d["disagreement"] for d in dis).most_common():
        print(f"  {v:>4}  {k}")

    unsure = [r for r in rows if "unsure" in
              (r["belongs_in_corpus"] + r["names_registry_technique"]).lower()]
    print(f"\nunsure: {len(unsure)}  (screener reported {REPORTED['unsure']})")

    F = ["packet", "#", "title", "year", "venue", "track",
         "current registry entry", "contribution", "technique_name", "origin",
         "evaluated_against", "evidence_quote", "belongs_in_corpus", "notes"]
    print()
    write("mismatch.csv", mismatch, F)
    write("removals.csv", removals, F)
    write("registry_disagreements.csv", dis, F + ["disagreement"])
    write("unsure.csv", unsure, F)

    (OUT / "rederivation.json").write_text(json.dumps({
        "generated": "2026-10-16",
        "source": "the `papers` sheet of the 17 coded packets, read directly",
        "note": "recomputed because the screener's own summary CSVs were built "
                "with a substring filter that could not distinguish the "
                "mismatch marker from its negation",
        "rows": len(rows),
        "mismatch": len(mismatch), "mismatch_reported": REPORTED["mismatch"],
        "removals": len(removals), "removals_reported": REPORTED["out_of_scope"],
        "registry_disagreements_kind_only": len(dis),
        "registry_disagreements_reported": REPORTED["registry_disagreements"],
        "unsure": len(unsure), "unsure_reported": REPORTED["unsure"],
        "unclassified_mismatch": len(unclear),
    }, indent=1))


if __name__ == "__main__":
    main()

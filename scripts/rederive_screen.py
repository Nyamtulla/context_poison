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

import sys

import openpyxl

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))   # so `from src import registry_source` resolves
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


def live_registry():
    """What the registries say NOW, by paper, from their structured fields.

    The packets carry a `current registry entry` column that reads
    "defense: X" or "mechanism: Y". Those prefixes are the file the entry came
    from, written by build_contribution_screen.py, not a claim about the
    method. Comparing a coded contribution against that prefix produced 310
    false disagreements: 180 methods it called wrongly-filed defenses already
    said `validated_against: incidental`, and all 128 it called
    wrongly-filed non-adversarial mechanisms already said `track: Security`.

    The column is also a snapshot from the day the packets were built, so it
    cannot see the 34 techniques backfilled afterwards.

    So read the registries themselves, and read the fields that carry meaning.
    """
    out = {}
    for fn, kind in (("rq3_pollution_registry.json", "mechanism"),
                     ("rq4_defense_registry.json", "defense")):
        for e in json.loads((REPO / "data" / "registries" / fn).read_text()):
            out.setdefault(e.get("paper_id"), []).append(
                {"kind": kind,
                 "track": (e.get("track") or "").strip(),
                 "validated_against": (e.get("validated_against") or "").strip()})
    return out


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


def apply_rulings(rows):
    """Honour the project lead's overrides without editing the spreadsheets.

    `screen_rulings.json` records decisions the lead made after reading the
    screen. Applying them on load keeps the screener's sheets as an untouched
    record of what it said, and keeps every override attributable to whoever
    made it, which is what `registry_corrections.json` does for the registries.
    """
    f = REPO / "data" / "registries" / "screen_rulings.json"
    if not f.exists():
        return rows, []
    spec = json.loads(f.read_text())
    date = spec["boundary_ruling"]["date"]
    applied = []
    # the ruling cuts both ways: it readmits papers the screen removed on the
    # wrong test, and it removes one the screen kept on a different test.
    # Applying only the readmissions would leave the set incoherent again.
    for k in spec.get("keep_despite_screen", []):
        needle = k["title_contains"].lower()
        for r in rows:
            if needle in r["title"].lower() and r["belongs_in_corpus"].lower() == "no":
                r["belongs_in_corpus"] = "yes"
                # The screener stopped at out_of_scope and never coded what
                # these papers actually contribute. Leaving that value in place
                # would make the row contradict itself and would keep counting
                # them as out_of_scope downstream. Blank it and flag instead of
                # guessing a contribution nobody assigned.
                r["contribution"] = ""
                r["_needs_recoding"] = True
                r["notes"] = (f"LEAD RULING {date}: readmitted; contribution "
                              f"NOT YET CODED. {k['why']} | " + r["notes"])
                applied.append(("keep", r["title"]))
    # contributions the lead's session coded after the readmissions, each
    # traceable to the paper's key_result or its registry entry
    for k in spec.get("contribution_coded_by_lead_session", {}).get("codes", []):
        needle = k["title_contains"].lower()
        for r in rows:
            if needle in r["title"].lower() and not r["contribution"]:
                r["contribution"] = k["contribution"]
                r["notes"] = (f"CODED {date}: {k['contribution']}. "
                              f"{k['evidence']} | " + r["notes"])
                applied.append(("code", r["title"]))
    for k in spec.get("remove_despite_screen", []):
        needle = k["title_contains"].lower()
        for r in rows:
            if needle in r["title"].lower() and r["belongs_in_corpus"].lower() != "no":
                r["belongs_in_corpus"] = "no"
                r["contribution"] = "out_of_scope"
                r["notes"] = (f"LEAD RULING {date}: removed. {k['why']} | "
                              + r["notes"])
                applied.append(("remove", r["title"]))
    return rows, applied


def main():
    rows = load_rows()
    rows, overridden = apply_rulings(rows)
    if overridden:
        print(f"lead rulings applied to {len(overridden)} papers:")
        for how, title in overridden:
            print(f"   {how:<7} {title[:68]}")
        print()
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
          f"{sum(1 for r in removals if (r['current registry entry'] or '').strip().lower() not in ('', '(none)'))}")

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

    # ---- registry disagreements, against the LIVE registries
    live = live_registry()
    # No try/except around this. Swallowing the failure here silently maps
    # every paper to "no registry entry" and reports every coded technique as
    # a disagreement, which is exactly what it did: 578 flagged against a true
    # 268. A missing import should stop the script, not quietly invert it.
    from src import registry_source as _rs
    pid_of = {(p.get("title") or "").strip().lower(): p["paper_id"]
              for p in _rs.load_papers()}
    unmapped = sum(1 for r in rows
                   if r["title"].strip().lower() not in pid_of)
    if unmapped:
        print(f"  WARNING: {unmapped} screen titles do not match any paper")
    dis = []
    for r in rows:
        pid = pid_of.get(r["title"].strip().lower())
        entries = live.get(pid, [])
        want = coded_kind(r["contribution"])
        conflict = None
        if not entries:
            if want in ("attack", "defense", "mechanism", "fix"):
                conflict = f"no registry entry, coded {r['contribution']}"
        else:
            # a method the screen calls a fix should not be recorded as having
            # met an adversary; one it calls an attack should sit on the
            # security track
            if want == "fix" and any(
                    e["validated_against"] == "adversarial" for e in entries):
                conflict = "coded proposes_fix, registry says validated adversarially"
            elif want == "attack" and all(
                    e["track"] and e["track"] != "Security" for e in entries):
                conflict = "coded proposes_attack, registry track is not Security"
            elif want == "none" and any(e["kind"] == "defense" for e in entries):
                conflict = f"holds a registry entry, coded {r['contribution']}"
        if conflict:
            dis.append({**r, "disagreement": conflict})
    print(f"\nregistry disagreements, against the live registries: {len(dis)}"
          f"  (the screener reported {REPORTED['registry_disagreements']} by "
          f"comparing against the packets' file-prefix label)")
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

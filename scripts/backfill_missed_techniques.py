"""Add the techniques the original registry pass missed.

The registries were built by a single pass that asked one question per paper:
does it propose a named technique, yes or no. The 2026-10-16 contribution
screen re-read every paper in full and recorded a verbatim quote for each call.
Where the two disagree, 34 papers currently in the corpus propose an attack, a
defense, a mechanism or a fix and have no registry entry at all.

27 of the 34 were read by the original pass and judged "no". Some are not close
calls: NeuroGenPoisoning, MemVenom and Chain-of-Trigger name an attack in the
title. The other 7 were added to the corpus after that pass finished and were
never read by it.

So the direction of the error is one-way. The original pass under-counted, and
`NMechanisms` and `NDefenses` are floors rather than censuses.

What this script does NOT do: invent anything. `channel` and `consequence` come
from the corpus workbook, where all 34 already carry both from the original
full-text extraction. The technique name, origin, parent and evaluation text
come from the screen. Every added entry carries `confidence: medium` and the
screen's evidence quote, so the additions can be separated from the original
pass at any time, and `source: contribution_screen_2026-10-16` marks them.

Run with --apply to write; dry run otherwise.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import pathlib
import sys

import openpyxl

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
REG = REPO / "data" / "registries"
BUNDLES = REPO / "data" / "exports" / "contribution_screen" / "bundles"

from src import registry_source  # noqa: E402

# which registry a coded contribution belongs in
TO_MECH = {"proposes_attack", "proposes_mechanism"}
TO_DEF = {"proposes_defense", "proposes_fix"}
# TWO FIELDS THIS SCRIPT REFUSES TO DERIVE, both learned the hard way on
# 2026-10-16 when the first version of this file got them wrong.
#
# `validated_against` was derived by scanning the evaluation text for words
# like "injection", "exploit" and "adversarial". It was wrong in 3 of the 13
# cases it asserted:
#
#   Z-Space       "an all-injection llm baseline"  -> prompt stuffing, not an
#                                                     attack
#   Red-MIRROR    "web exploitation challenges"    -> the method IS the
#                                                     attacker
#   You've Changed "injection" in another sense
#
# A keyword cannot tell "the method was attacked" from "the method attacks"
# from "the word means something else here". It is the same lesson the
# defense-evaluation audit reached: a pattern confirms presence, never absence,
# and here it could not even confirm presence. So we assert nothing and flag.
#
# `track` was copied from the paper. A paper can be labelled ML/AI while the
# technique it proposes is a deliberate attack - NeuroGenPoisoning, MemVenom,
# Chain-of-Trigger, ChainFuzzer and Zombie Agent were all filed ML/AI or Both
# that way. The contribution decides the track, not the paper's label.

RULED_NAMES = []
TRACK_FOR = {"proposes_attack": "Security", "proposes_mechanism": "ML/AI"}


def screen_rows():
    out = {}
    for f in sorted(glob.glob(str(BUNDLES / "packet-*" / "*.xlsx"))):
        wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
        if "papers" not in wb.sheetnames:
            wb.close()
            continue
        grid = list(wb["papers"].iter_rows(values_only=True))
        wb.close()
        hdr = [str(c or "").strip() for c in grid[0]]
        i = {h: n for n, h in enumerate(hdr)}
        for r in grid[1:]:
            if not r or not r[i["title"]]:
                continue
            out[str(r[i["title"]]).strip().lower()] = {
                k: ("" if r[i[k]] is None else str(r[i[k]]).strip())
                for k in ("contribution", "technique_name", "origin",
                          "parent_technique", "evaluated_against",
                          "evidence_quote", "notes")}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    inc = {p["paper_id"]: p for p in registry_source.load_papers()
           if str(p.get("screening") or "").strip().lower() != "exclude"}
    # The lead's rulings readmit papers and code contributions the screen left
    # blank. Reading the spreadsheets raw misses both, so a paper coded
    # proposes_mechanism by ruling would never get its registry entry. Same
    # gap that made apply_contribution_screen read the blank packets.
    sys.path.insert(0, str(REPO / "scripts"))
    from rederive_screen import load_rows, apply_rulings
    ruled_rows, _ = apply_rulings(load_rows())
    ruled = {r["title"].strip().lower(): r for r in ruled_rows}
    _rl = json.loads((REPO / "data" / "registries" / "screen_rulings.json").read_text())
    global RULED_NAMES
    RULED_NAMES = _rl.get("contribution_coded_by_lead_session", {}).get("codes", [])
    r3 = json.loads((REG / "rq3_pollution_registry.json").read_text())
    r4 = json.loads((REG / "rq4_defense_registry.json").read_text())
    have = {e.get("paper_id") for e in r3} | {e.get("paper_id") for e in r4}
    scr = screen_rows()

    add_m, add_d = [], []
    for pid, p in inc.items():
        if pid in have:
            continue
        key = (p.get("title") or "").strip().lower()
        s = scr.get(key)
        # a ruling-supplied contribution wins over the sheet's blank
        if key in ruled and ruled[key].get("contribution"):
            s = dict(s or {}, contribution=ruled[key]["contribution"])
            # the ruling may also supply the name, which beats UNNAMED
            for c in RULED_NAMES:
                if c["title_contains"].lower() in key and c.get("technique_name"):
                    s["technique_name"] = c["technique_name"]
            s.setdefault("technique_name", "")
            for f in ("origin", "parent_technique", "evaluated_against",
                      "evidence_quote", "notes"):
                s.setdefault(f, "")
        if not s or s["contribution"] not in (TO_MECH | TO_DEF):
            continue
        name = s["technique_name"] or f"UNNAMED: {(p.get('title') or '')[:60]}"
        base = {
            "row": p.get("row"), "paper_id": pid, "title": p.get("title"),
            "channel": (p.get("channel") or "").strip(),
            "consequence": (p.get("consequence") or "").strip(),
            # NOT the paper's track: see the note above
            "track": "",
            "is_extension_of": s["parent_technique"],
            "confidence": "medium",
            "name": name,
            "source": "contribution_screen_2026-10-16",
            "notes": (f"Added from the contribution screen; the original "
                      f"registry pass recorded no technique for this paper. "
                      f"Evidence: {s['evidence_quote'][:300]}"),
        }
        if s["contribution"] in TO_MECH:
            add_m.append({**base, "has_technique": "yes",
                          "technique_name": name,
                          "track": TRACK_FOR[s["contribution"]]})
        else:
            add_d.append({**base, "has_defense": "yes", "defense_name": name,
                          "defense_intervention_point":
                              (p.get("defense_intervention_point") or "").strip(),
                          # never derived; see the note above
                          "validated_against": "",
                          "validated_against_needs_coding": True,
                          "origin": s["origin"] or "proposed",
                          "origin_evidence": s["evidence_quote"][:400],
                          "evaluated_against": s["evaluated_against"],
                          "evaluated_against_evidence": ""})

    print(f"mechanisms/attacks to add: {len(add_m)}")
    for e in add_m:
        print(f"   {e['technique_name'][:52]:<54} [{e['channel']}/{e['consequence']}]")
    print(f"\ndefenses/fixes to add: {len(add_d)}  "
          f"(validated_against left blank on all of them and flagged for "
          f"coding; it is not derivable from the evaluation text)")
    for e in add_d[:12]:
        print(f"   {e['defense_name'][:52]:<54} [{e['validated_against']}]")
    if len(add_d) > 12:
        print(f"   ... and {len(add_d)-12} more")

    miss = [e for e in add_m + add_d if not e["channel"] or not e["consequence"]]
    if miss:
        print(f"\n  REFUSING: {len(miss)} entries lack channel or consequence. "
              f"The taxonomy cube would get a blank cell.")
        return

    print(f"\nregistry sizes: mechanisms {len(r3)} -> {len(r3)+len(add_m)}, "
          f"defenses {len(r4)} -> {len(r4)+len(add_d)}")
    if not args.apply:
        print("\nDry run. Re-run with --apply to write.")
        return

    (REG / "rq3_pollution_registry.json").write_text(
        json.dumps(r3 + add_m, indent=1))
    (REG / "rq4_defense_registry.json").write_text(
        json.dumps(r4 + add_d, indent=1))
    print("\nwritten. Now re-run gen_paper_numbers.py and gen_paper_figures.py.")


if __name__ == "__main__":
    main()

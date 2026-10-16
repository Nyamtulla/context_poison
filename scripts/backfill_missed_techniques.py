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
# `validated_against` feeds NAdvOnly, NIncOnly and NBothValidated, which are
# published numbers, so it is read from what the paper actually evaluated on
# rather than inferred from whether the screen called the method a defense or a
# fix. A method can be called a defense and never meet an attacker.
ADVERSARIAL = (
    "attack success", "asr", "adversarial", "attacker", "injection",
    "poison", "jailbreak", "threat model", "red team", "exploit",
    "malicious", "backdoor", "evasion",
)


def validated_from_evaluation(evaluated: str) -> str:
    """adversarial when the evaluation names an attack, else blank.

    Blank, not "incidental": a pattern can confirm that something is present,
    it can never establish that it is absent. That caution is the general
    conclusion of our own defense-evaluation audit, and the registry already
    carries a blank category for exactly this case.
    """
    e = (evaluated or "").lower()
    return "adversarial" if any(k in e for k in ADVERSARIAL) else ""


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
    r3 = json.loads((REG / "rq3_pollution_registry.json").read_text())
    r4 = json.loads((REG / "rq4_defense_registry.json").read_text())
    have = {e.get("paper_id") for e in r3} | {e.get("paper_id") for e in r4}
    scr = screen_rows()

    add_m, add_d = [], []
    for pid, p in inc.items():
        if pid in have:
            continue
        s = scr.get((p.get("title") or "").strip().lower())
        if not s or s["contribution"] not in (TO_MECH | TO_DEF):
            continue
        name = s["technique_name"] or f"UNNAMED: {(p.get('title') or '')[:60]}"
        base = {
            "row": p.get("row"), "paper_id": pid, "title": p.get("title"),
            "channel": (p.get("channel") or "").strip(),
            "consequence": (p.get("consequence") or "").strip(),
            "track": (p.get("track") or "").strip(),
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
                          "technique_name": name})
        else:
            add_d.append({**base, "has_defense": "yes", "defense_name": name,
                          "defense_intervention_point":
                              (p.get("defense_intervention_point") or "").strip(),
                          "validated_against":
                              validated_from_evaluation(s["evaluated_against"]),
                          "origin": s["origin"] or "proposed",
                          "origin_evidence": s["evidence_quote"][:400],
                          "evaluated_against": s["evaluated_against"],
                          "evaluated_against_evidence": ""})

    print(f"mechanisms/attacks to add: {len(add_m)}")
    for e in add_m:
        print(f"   {e['technique_name'][:52]:<54} [{e['channel']}/{e['consequence']}]")
    import collections as _c
    print(f"\ndefenses/fixes to add: {len(add_d)}  validated_against: "
          f"{dict(_c.Counter(e['validated_against'] or '(blank, not asserted)' for e in add_d))}")
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

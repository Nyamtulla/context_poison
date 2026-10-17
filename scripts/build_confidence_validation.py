"""Draw the confidence-stratified validation set, and keep the key hidden.

The original extraction recorded a `confidence` on every registry entry. That
is a prediction the extractor made about its own work, so it can be tested:
**does reported confidence predict extraction accuracy?**

Design, agreed 2026-10-17:

    high    534 entries   check 50
    medium  122 entries   check 40
    low      83 entries   check 35
                          -----------
                          125 entries, about 4 hours per coder at 8 min each

Equal-ish rather than proportional. 15% of each group would give 12 low-
confidence entries, and 12 cannot detect even a 40-point gap, so the study
would cost the same and answer nothing. The low group is where the answer
lives.

**The coder never sees the confidence group.** If a validator is told an entry
was low-confidence they will look harder for a fault and find one, which
manufactures the result the study is meant to test. So the workbook ships
without it and the mapping lives in a separate key file. Nothing else about
the two files differs.

Entries added by `backfill_missed_techniques.py` are excluded: their confidence
was set by that script, not by the original pass, so including them would mix
two different things under one label.

Out:
  data/exports/confidence_validation/validation_master.xlsx   -> the coders
  data/exports/confidence_validation/_key_DO_NOT_SHARE.json   -> stays here
  data/exports/confidence_validation/manifest.json
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import random
import sys

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
REG = REPO / "data" / "registries"
OUT = REPO / "data" / "exports" / "confidence_validation"

from src import registry_source  # noqa: E402

TARGET = {"high": 50, "medium": 40, "low": 35}
BACKFILL_SRC = "contribution_screen_2026-10-16"

# what the coder fills in. Kept short on purpose: this is an 8-minute check
# against a quote we supply, not a re-extraction.
FILL = [
    ("quote_supports", "yes / partly / no  - does the quoted sentence actually "
                       "support what we recorded?"),
    ("name_correct", "yes / no  - is the technique name right?"),
    ("class_correct", "yes / no  - are channel and consequence right?"),
    ("verdict", "correct / minor / wrong  - your overall call"),
    ("correct_value", "if anything is wrong, what should it say?"),
    ("minutes", "roughly how long this one took you"),
    ("notes", "anything worth passing on"),
]


def load_entries():
    out = []
    inc = {p["paper_id"]: p for p in registry_source.load_papers()
           if str(p.get("screening") or "").strip().lower() != "exclude"}
    for fn, kind, namefield in (
            ("rq3_pollution_registry.json", "threat", "technique_name"),
            ("rq4_defense_registry.json", "remedy", "defense_name")):
        for e in json.loads((REG / fn).read_text()):
            pid = e.get("paper_id")
            if pid not in inc:
                continue
            if e.get("source") == BACKFILL_SRC:
                continue          # confidence is ours, not the original pass's
            conf = str(e.get("confidence") or "").strip().lower()
            if conf not in TARGET:
                continue
            p = inc[pid]
            name = (e.get(namefield) or e.get("name") or "").strip()
            out.append({
                "entry_id": hashlib.sha1(
                    f"{pid}|{kind}|{name}".encode()).hexdigest()[:12],
                "_confidence": conf,
                "kind": "attack / failure mechanism" if kind == "threat"
                        else "defense / fix",
                "recorded_name": name,
                "channel": (e.get("channel") or "").strip(),
                "consequence": (e.get("consequence") or "").strip(),
                "evidence_quote": (e.get("notes") or "").strip()[:700],
                "paper_title": p.get("title", ""),
                "year": p.get("year", ""),
                "venue": p.get("venue", ""),
                "pdf": p.get("pdf_local_path", ""),
            })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20261017)
    args = ap.parse_args()

    ents = load_entries()
    pool = collections.defaultdict(list)
    for e in ents:
        pool[e["_confidence"]].append(e)
    print(f"eligible entries: {len(ents)}")
    for k in ("high", "medium", "low"):
        print(f"   {k:<7} {len(pool[k]):>4} available, taking {TARGET[k]}")

    rng = random.Random(args.seed)
    picked = []
    for k, n in TARGET.items():
        if len(pool[k]) < n:
            raise SystemExit(f"{k}: asked {n}, have {len(pool[k])}")
        picked += rng.sample(sorted(pool[k], key=lambda e: e["entry_id"]), n)
    # shuffle so the order carries no signal about the group
    rng.shuffle(picked)

    OUT.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()

    ws = wb.active
    ws.title = "start here"
    for i, line in enumerate([
        "VALIDATION OF EXTRACTED TECHNIQUES", "",
        "We read 929 papers and recorded the attacks, failure mechanisms, "
        "defenses and fixes each one proposes.",
        "Your job is to check whether we got it right.", "",
        "THIS IS NOT A FULL READ. Budget about 8 minutes per row.", "",
        "For each row on the 'check' sheet we give you:",
        "   - the technique name we recorded",
        "   - the channel and consequence we assigned",
        "   - the exact sentence we took as evidence",
        "   - the paper's PDF", "",
        "Open the PDF, find the quoted sentence, and decide whether it "
        "supports what we wrote.",
        "Read more of the paper ONLY when the quote does not settle it.", "",
        "Fill the yellow columns. Leave the white ones alone.", "",
        "VERDICTS",
        "   correct : we got it right",
        "   minor   : right technique, something small is off (wording, one "
        "field)",
        "   wrong   : the technique is not what we said, or is not in the "
        "paper at all", "",
        "If you are unsure, write what you think in 'notes' and move on. "
        "An honest unsure is more useful than a guess.", "",
        "The rows are in random order and are not grouped in any way.",
    ]):
        ws.cell(row=i + 1, column=1, value=line)
    ws.column_dimensions["A"].width = 100

    cs = wb.create_sheet("check")
    given = ["entry_id", "paper_title", "year", "venue", "pdf", "kind",
             "recorded_name", "channel", "consequence", "evidence_quote"]
    hdr = given + [f for f, _ in FILL]
    cs.append(hdr)
    yellow = PatternFill("solid", fgColor="FFF2CC")
    grey = PatternFill("solid", fgColor="E8E8E8")
    for c, h in enumerate(hdr, 1):
        cell = cs.cell(row=1, column=c)
        cell.font = Font(bold=True)
        cell.fill = yellow if h in dict(FILL) else grey
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    for e in picked:
        cs.append([e[k] for k in given] + [""] * len(FILL))
    widths = {"paper_title": 46, "evidence_quote": 70, "recorded_name": 30,
              "pdf": 34, "correct_value": 30, "notes": 34, "entry_id": 14}
    for c, h in enumerate(hdr, 1):
        cs.column_dimensions[cs.cell(row=1, column=c).column_letter].width = \
            widths.get(h, 13)
    for r in range(2, len(picked) + 2):
        cs.cell(row=r, column=hdr.index("evidence_quote") + 1).alignment = \
            Alignment(wrap_text=True, vertical="top")
        cs.cell(row=r, column=hdr.index("paper_title") + 1).alignment = \
            Alignment(wrap_text=True, vertical="top")
    cs.freeze_panes = "A2"
    for col, opts in (("quote_supports", '"yes,partly,no"'),
                      ("name_correct", '"yes,no"'),
                      ("class_correct", '"yes,no"'),
                      ("verdict", '"correct,minor,wrong"')):
        dv = DataValidation(type="list", formula1=opts, allow_blank=True)
        cs.add_data_validation(dv)
        L = cs.cell(row=1, column=hdr.index(col) + 1).column_letter
        dv.add(f"{L}2:{L}{len(picked)+1}")

    fs = wb.create_sheet("what the columns mean")
    fs.append(["column", "what to put there"])
    fs.cell(row=1, column=1).font = Font(bold=True)
    fs.cell(row=1, column=2).font = Font(bold=True)
    for f, d in FILL:
        fs.append([f, d])
    fs.column_dimensions["A"].width = 18
    fs.column_dimensions["B"].width = 86
    for r in range(2, len(FILL) + 2):
        fs.cell(row=r, column=2).alignment = Alignment(wrap_text=True)

    wb.save(OUT / "validation_master.xlsx")
    print(f"\nwrote validation_master.xlsx  ({len(picked)} rows, confidence NOT in it)")

    (OUT / "_key_DO_NOT_SHARE.json").write_text(json.dumps(
        {"generated": "2026-10-17", "seed": args.seed,
         "warning": "Maps entry_id to its confidence group. Do NOT send this "
                    "to anyone coding the workbook: a coder who knows an entry "
                    "was low-confidence will look harder for a fault and find "
                    "one, which manufactures the result this study tests.",
         "key": {e["entry_id"]: e["_confidence"] for e in picked}}, indent=1))

    (OUT / "manifest.json").write_text(json.dumps({
        "generated": "2026-10-17", "seed": args.seed,
        "hypothesis": "extraction accuracy rises with the confidence the "
                      "extractor reported at extraction time",
        "unit": "registry ENTRY, not paper; one paper may contribute several",
        "population": {k: len(pool[k]) for k in TARGET},
        "sampled": TARGET,
        "excluded": f"entries whose source is {BACKFILL_SRC}; their confidence "
                    f"was assigned by the backfill script, not the original pass",
        "blind": "the workbook omits the confidence group by design",
        "combine_rule": "weight each group by its population size "
                        f"({ {k: len(pool[k]) for k in TARGET} }), never by the "
                        "number sampled",
        "entries": [{"entry_id": e["entry_id"], "confidence": e["_confidence"]}
                    for e in picked],
    }, indent=2))
    print("wrote _key_DO_NOT_SHARE.json and manifest.json")
    print("\nsplit into packets when you know the headcount:")
    print("   python3 scripts/split_validation_packets.py --coders N")


if __name__ == "__main__":
    main()

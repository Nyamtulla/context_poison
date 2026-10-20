"""Draw 125 papers by AI confidence and cut them into coder packets.

The study answers the six questions a reviewer asks about an AI-extracted
corpus, from one human read per paper:

  1. how accurate is the extraction        -> the 18 fields, per paper
  2. is it accurate for the load-bearing   -> accuracy reported per field
     fields specifically
  3. did you only check the easy ones      -> random draw, seed recorded
  4. did the authors mark their own work   -> outside coders, key withheld
  5. is one coder's opinion a measurement  -> the double-coded slice
  6. what did you MISS                     -> the missed-techniques column,
                                              which is the only question here
                                              that measures recall

## The three groups

Confidence was recorded by the extractor on each RQ3/RQ4 coding judgement,
**not on the paper**, and 134 papers carry different values from the two
passes. Each paper is assigned its LOWEST confidence: if any pass was unsure
about a paper, the paper counts as the less confident group. That is the
conservative reading, and it is also the only one that works - taking the
highest leaves 32 low-confidence papers, short of the 35 the draw needs.

    frame   828 included papers that carry any confidence
    high    590 available   draw 50
    medium  117 available   draw 40
    low     121 available   draw 35
                            ---------
                            125 papers

101 included papers carry no confidence at all and cannot be placed in a
group, so they are outside the frame. The estimate therefore describes the
828-paper frame, not all 929. Say so rather than rounding it off.

## Blinding

A coder must not know which group a paper came from, or they will look
harder at the low group and manufacture the result the study is meant to
measure. The group is not a column in any packet, the deal is round-robin
over a shuffled draw, and the mapping lives only in the key file.

Out: data/exports/validation_study/packets/packet-N.xlsx  (+ .zip with PDFs)
     data/exports/validation_study/_key_DO_NOT_SHARE.json
     data/exports/validation_study/manifest.json
"""
from __future__ import annotations

import argparse
import collections
import csv
import glob
import json
import pathlib
import random
import shutil
import sqlite3
import zipfile

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

REPO = pathlib.Path(__file__).resolve().parent.parent
RAW = REPO / "data" / "registries" / "raw"
REG = REPO / "data" / "registries"
OUT = REPO / "data" / "exports" / "validation_study"
TEMPLATE = OUT / "packet_template.xlsx"

SEED = 20261020
DRAW = {"high": 50, "medium": 40, "low": 35}
RANK = {"low": 0, "medium": 1, "high": 2}

FIELDS = ["track", "screening", "role", "channel", "consequence",
          "cites_track_a", "cites_track_b", "defense_intervention_point",
          "temporal_persistence", "evidence_grade", "artifacts_released",
          "models_evaluated", "datasets_benchmarks", "key_result",
          "baselines_compared", "threat_model", "stated_limitations",
          "technical_summary"]
CLASS = {f: ("core" if f in FIELDS[:7] else
             "secondary" if f in FIELDS[7:11] else "freetext")
         for f in FIELDS}

HDR_FILL = PatternFill("solid", fgColor="FFDDDDDD")
FILL_IN = PatternFill("solid", fgColor="FFFFF2CC")
BOLD = Font(bold=True)
WRAP = Alignment(wrap_text=True, vertical="top")
TOP = Alignment(vertical="top")


def paper_confidence():
    """paper_id -> lowest confidence any coding pass recorded for it."""
    seen = collections.defaultdict(set)
    for f in glob.glob(str(RAW / "rq3_*.csv")) + glob.glob(str(RAW / "rq4_*.csv")):
        for r in csv.DictReader(open(f, encoding="utf-8-sig")):
            pid = (r.get("paper_id") or "").strip()
            c = (r.get("confidence") or "").strip().lower()
            if pid and c in RANK:
                seen[pid].add(c)
    return {p: min(v, key=lambda c: RANK[c]) for p, v in seen.items()}


def corpus():
    wb = openpyxl.load_workbook(
        REPO / "data" / "exports" / "paper_dashboard_source.xlsx", read_only=True)
    rows = list(wb["Papers"].iter_rows(values_only=True))
    wb.close()
    hdr = list(rows[0])
    return [dict(zip(hdr, r)) for r in rows[1:]
            if str(dict(zip(hdr, r)).get("screening", "")).strip() != "Exclude"]


def registry_by_paper():
    out = collections.defaultdict(list)
    for fn, kind in (("rq3_pollution_registry.json", "attack / failure mechanism"),
                     ("rq4_defense_registry.json", "defense / fix")):
        for e in json.loads((REG / fn).read_text()):
            e["_kind"] = kind
            e["_name"] = e.get("defense_name") or e.get("name") or ""
            out[str(e.get("paper_id"))].append(e)
    return out


def roles():
    try:
        c = sqlite3.connect(REPO / "data" / "paper_explorer.db")
        return {str(r[0]): r[1] for r in c.execute("select paper_id, role from paper")}
    except Exception:
        return {}


def copy_sheet(src, wb, name, widths=None):
    ws = wb.create_sheet(name)
    for i, row in enumerate(src.iter_rows(values_only=True), 1):
        for j, v in enumerate(row, 1):
            c = ws.cell(row=i, column=j, value=v)
            c.alignment = WRAP if i > 1 else TOP
            if i == 1:
                c.font, c.fill = BOLD, HDR_FILL
    for j in range(1, src.max_column + 1):
        L = get_column_letter(j)
        w = src.column_dimensions[L].width
        if w:
            ws.column_dimensions[L].width = w
    ws.freeze_panes = "A2"
    return ws


def table(wb, name, header, rows, widths, freeze, fill_from=None, wrap_from=1):
    ws = wb.create_sheet(name)
    for j, h in enumerate(header, 1):
        c = ws.cell(row=1, column=j, value=h)
        c.font, c.fill, c.alignment = BOLD, HDR_FILL, TOP
        ws.column_dimensions[get_column_letter(j)].width = widths.get(h, 18)
    for i, row in enumerate(rows, 2):
        for j, v in enumerate(row, 1):
            c = ws.cell(row=i, column=j, value=v)
            c.alignment = WRAP if j > wrap_from else TOP
            if fill_from and j >= fill_from:
                c.fill = FILL_IN
    ws.freeze_panes = freeze
    return ws


def dropdown(ws, col, opts, n):
    dv = DataValidation(type="list", formula1=opts, allow_blank=True)
    ws.add_data_validation(dv)
    L = get_column_letter(col)
    dv.add(f"{L}2:{L}{n + 1}")


def build_one(dest, n, week, weeks, mine, reg, by_id, role, tpl,
              corpus_n, label):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet("Start here")
    ws.column_dimensions["A"].width = 118
    npap, nent_p = len(mine), sum(len(reg.get(p, [])) for p in mine)
    for i, (t, b) in enumerate(start_text(n, npap, nent_p, corpus_n, week, weeks), 1):
        c = ws.cell(row=i, column=1, value=t)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if b:
            c.font = BOLD

    copy_sheet(tpl["glossary"], wb, "glossary")
    copy_sheet(tpl["field guide"], wb, "field guide")

    prows = []
    for i, pid in enumerate(mine, 1):
        p = by_id[pid]
        prows.append([i, p.get("title"), p.get("year"), p.get("venue"),
                      len(reg.get(pid, [])), p.get("pdf_local_path"),
                      None, None])
    wsp = table(wb, "papers",
                ["#", "title", "year", "venue", "techniques_we_recorded",
                 "pdf", "techniques_we_missed", "note"], prows,
                {"#": 4, "title": 70, "year": 6, "venue": 14,
                 "techniques_we_recorded": 20, "pdf": 46,
                 "techniques_we_missed": 46, "note": 34},
                "B2", fill_from=7)

    crows, k = [], 0
    for i, pid in enumerate(mine, 1):
        p = by_id[pid]
        crows.append([k + 1, p.get("title"), "paper_identity", "check",
                      "Is this PDF this paper?", None, None, None, pid])
        k += 1
        for f in FIELDS:
            v = role.get(pid) if f == "role" else p.get(f)
            crows.append([k + 1, p.get("title"), f, CLASS[f],
                          v, None, None, None, pid])
            k += 1
    wsc = table(wb, "coding",
                ["#", "title", "field", "field_class", "AI_extracted_value",
                 "verdict", "correct_value_if_wrong", "note", "paper_id"],
                crows,
                {"#": 4, "title": 26, "field": 28, "field_class": 11,
                 "AI_extracted_value": 74, "verdict": 14,
                 "correct_value_if_wrong": 34, "note": 42, "paper_id": 42},
                "C2", fill_from=6)
    dropdown(wsc, 6, '"correct,wrong,not-in-paper,unclear"', len(crows))

    trows = []
    for i, pid in enumerate(mine, 1):
        for e in reg.get(pid, []):
            trows.append([len(trows) + 1, by_id[pid].get("title"),
                          e["_kind"], e["_name"], e.get("channel"),
                          e.get("consequence"), None, None, None, None, pid])
    wst = table(wb, "techniques",
                ["#", "title", "kind", "recorded_name", "channel",
                 "consequence", "is_real", "name_correct", "class_correct",
                 "note", "paper_id"], trows,
                {"#": 4, "title": 34, "kind": 24, "recorded_name": 40,
                 "channel": 14, "consequence": 20, "is_real": 12,
                 "name_correct": 13, "class_correct": 13, "note": 38,
                 "paper_id": 42}, "C2", fill_from=7)
    for col in (7, 8, 9):
        dropdown(wst, col, '"yes,no,unclear"', len(trows))

    f = dest / f"packet-{n}.xlsx"
    wb.save(f)
    z, missing = dest / f"packet-{n}.zip", 0
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(f, f.name)
        for pid in mine:
            q = REPO / str(by_id[pid].get("pdf_local_path") or "")
            if q.is_file():
                zf.write(q, f"pdfs/{q.name}")
            else:
                missing += 1
    est = (npap * 22 + len(trows) * 4) / 60
    print(f"  {label:9s} packet-{n}: {npap:3d} papers, {len(crows):4d} field "
          f"rows, {len(trows):3d} technique rows, ~{est:.1f} h"
          + (f", {missing} PDFs MISSING" if missing else ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--coders", type=int, default=4)
    ap.add_argument("--weeks", type=int, default=1,
                    help="split each packet into N weekly batches")
    ap.add_argument("--double", type=int, default=0,
                    help="papers given to two coders, for agreement")
    args = ap.parse_args()

    conf = paper_confidence()
    inc = corpus()
    by_id = {str(p["paper_id"]): p for p in inc}
    frame = collections.defaultdict(list)
    for pid, p in by_id.items():
        if pid in conf:
            frame[conf[pid]].append(pid)
    for g in frame:
        frame[g].sort()

    print(f"corpus {len(inc)}   frame {sum(len(v) for v in frame.values())}"
          f"   no confidence {len(inc) - sum(len(v) for v in frame.values())}")
    rng = random.Random(SEED)
    picked = []
    for g in ("high", "medium", "low"):
        pool = frame[g]
        if len(pool) < DRAW[g]:
            raise SystemExit(f"{g}: need {DRAW[g]}, have {len(pool)}")
        take = rng.sample(pool, DRAW[g])
        picked += take
        print(f"  {g:7s} pool {len(pool):4d} -> drew {len(take)}")
    rng.shuffle(picked)

    reg, role = registry_by_paper(), roles()
    nent = sum(len(reg.get(p, [])) for p in picked)
    print(f"registry entries attached: {nent}")

    tpl = openpyxl.load_workbook(TEMPLATE)
    deal = [[] for _ in range(args.coders)]
    for i, pid in enumerate(picked):
        deal[i % args.coders].append(pid)
    if args.double:
        for i in range(args.double):
            deal[(i + 1) % args.coders].append(picked[i])

    pk = OUT / "packets"
    if pk.exists():
        shutil.rmtree(pk)
    pk.mkdir(parents=True)

    # Deal each coder's papers round-robin into weeks, so every week carries
    # a mix of confidence groups. Slicing into blocks instead would make
    # week 1 "whatever came first"; if the study is abandoned part-way, a
    # balanced partial sample is still analysable and a block is not.
    for n, mine in enumerate(deal, 1):
        for w in range(args.weeks):
            subset = mine[w::args.weeks]
            dest = pk / f"week-{w + 1}" if args.weeks > 1 else pk
            dest.mkdir(parents=True, exist_ok=True)
            build_one(dest, n, w + 1, args.weeks, subset, reg, by_id, role,
                      tpl, len(inc),
                      f"week {w + 1}" if args.weeks > 1 else "")

    (OUT / "_key_DO_NOT_SHARE.json").write_text(json.dumps(
        {"generated": "2026-10-20", "seed": SEED,
         "warning": "Confidence group per paper. Never send this to a coder.",
         "key": {p: conf[p] for p in picked}}, indent=1))
    (OUT / "manifest.json").write_text(json.dumps(
        {"generated": "2026-10-20", "seed": SEED, "draw": DRAW,
         "rule": "paper confidence = lowest of any RQ3/RQ4 coding judgement",
         "corpus_n": len(inc),
         "frame_n": sum(len(v) for v in frame.values()),
         "frame_sizes": {g: len(v) for g, v in frame.items()},
         "no_confidence_excluded": len(inc) - sum(len(v) for v in frame.values()),
         "inference_target": "the frame, not the full corpus",
         "fields_per_paper": len(FIELDS),
         "registry_entries": nent, "coders": args.coders,
         "papers": picked}, indent=1))
    print(f"\n{len(picked)} papers -> {pk}")
    print("Send the packets. Do NOT send _key_DO_NOT_SHARE.json.")


def start_text(n, npap, nent, corpus_n, week=1, weeks=1):
    return [
        (f"Verification packet {n}" + (f" - week {week} of {weeks}"
                                       if weeks > 1 else ""), True),
        ("The PDFs are in pdfs/ in this zip", False),
        ("", False),
        ("WHAT TO DO", True),
        (f"For each paper we extracted 18 fields automatically. Check each one "
         f"against the paper and say whether it is right. You are measuring how "
         f"accurate the extraction is - you are not fixing the data.", False),
        ("", False),
        (f"This packet has {npap} papers. Work through the 'coding' sheet "
         f"first, then the 'techniques' sheet.", False),
        ("", False),
        ("1. 'coding' sheet - one row per (paper, field).", True),
        ("Fill in these three columns only:", False),
        ("    verdict : your judgement (see below)", False),
        ("    correct_value_if_wrong : what the paper actually says, if "
         "verdict = wrong", False),
        ("    note: anything worth passing on", False),
        ("Do not change these - they are the record being tested: title, "
         "field, field_class, AI_extracted_value, paper_id", False),
        ("", False),
        (f"2. 'techniques' sheet - the {nent} attacks, mechanisms and defenses "
         f"we recorded from your papers.", True),
        ("For each one say whether it is real (is_real), whether we named it "
         "right (name_correct), and whether the channel and consequence are "
         "right (class_correct).", False),
        ("", False),
        ("3. 'papers' sheet - after reading each paper, fill in "
         "'techniques_we_missed'.", True),
        ("If the paper proposes an attack, mechanism or defense that is NOT in "
         "the techniques sheet, name it there. If we caught everything, write "
         "'none'. This column is the only place that tells us what we failed "
         "to find, so please do not leave it blank.", False),
        ("", False),
        ("THE FOUR VERDICTS", True),
        ("  correct: the value is right and the paper says so", False),
        ("  wrong: the paper says something different  -> put the real value "
         "in correct_value_if_wrong", False),
        ("  not-in-paper: the paper never states this at all. Different from "
         "'wrong': 'wrong' means we misread the paper, 'not-in-paper' means we "
         "made it up. Keep them apart.", False),
        ("  unclear: ambiguous, or you cannot tell from what you have", False),
        ("", False),
        ("START EACH PAPER WITH 'paper_identity'", True),
        ("The first row of every paper asks whether the PDF is really that "
         "paper. Check title, authors and year on page 1. If it is the wrong "
         "paper, stop there, mark the remaining fields 'unclear', and say so "
         "in the note.", False),
        ("", False),
        ("WHERE TO LOOK THINGS UP", True),
        ("  'field guide' sheet  - what each field means and where in the "
         "paper to find it", False),
        ("  'glossary' sheet     - what every allowed value means, plus "
         "abbreviations", False),
        (f"  'papers' sheet       - the {npap} papers at a glance", False),
        ("Roughly 15-25 minutes per paper. You do not need to read the whole "
         "paper - abstract, setup, results and the reference list carry almost "
         "everything.", False),
        ("If in doubt, mark 'unclear' and write what confused you. An honest "
         "'unclear' is useful. A confident guess is not.", False),
        ("", False),
        ("IF YOU FIND AN ERROR", True),
        ("Write it down and move on. Do not go and correct the database or any "
         "other spreadsheet - the point is to count how often the extraction "
         "is wrong.  If you think the FIELD DEFINITION is wrong rather than "
         "the value, say so in the note.", False),
    ]


if __name__ == "__main__":
    main()

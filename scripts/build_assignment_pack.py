"""Build a self-contained verification pack for one teammate: xlsx + PDFs, zipped.

This selects PURPOSIVELY - the highest-cited Security papers that contribute an
attack or defense - which is a different thing from the 100-paper random sample
in verification/. The distinction is not pedantry and is stated on the README
sheet: an accuracy measured on the most-cited papers in the field cannot be
generalised to the corpus, because heavily-cited work is better known, better
written and almost certainly better extracted. This pack answers "are our
load-bearing papers coded right", the random sample answers "how good is the
extraction overall", and the two numbers must never be pooled.

Surveys and SoKs are excluded by title, and papers coded role='neither' are
excluded because they contribute no registry entry.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sqlite3
import zipfile

REPO = pathlib.Path(__file__).resolve().parent.parent
DB = REPO / "data" / "paper_explorer.db"

SURVEY = re.compile(
    r"\b(survey|systemati[sz]ation|sok|systematic review|literature review|"
    r"a review|overview of|taxonomy of|landscape|state of the art)\b", re.I)

CORE = ["track", "screening", "role", "channel", "consequence",
        "cites_track_a", "cites_track_b"]
SECONDARY = ["defense_intervention_point", "temporal_persistence",
             "evidence_grade", "artifacts_released"]
FREETEXT = ["models_evaluated", "datasets_benchmarks", "key_result",
            "baselines_compared", "threat_model", "stated_limitations",
            "technical_summary"]
FIELDS = CORE + SECONDARY + FREETEXT
META = ["paper_id", "title", "authors", "year", "venue", "citation_count",
        "doi", "arxiv_id", "url"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--track", default="Security")
    ap.add_argument("--who", default="teammate-1")
    ap.add_argument("--out", default="verification/packs")
    args = ap.parse_args()

    con = sqlite3.connect(DB)
    rows = con.execute(f"""
        select {', '.join(META + FIELDS + ['pdf_local_path'])}
        from paper
        where screening='Include' and track=?
          and role in ('attack','defense','both')
          and pdf_local_path is not null and trim(pdf_local_path)!=''
        order by coalesce(citation_count,0) desc limit 200""", (args.track,)).fetchall()
    cols = META + FIELDS + ["pdf_local_path"]
    recs = [dict(zip(cols, r)) for r in rows]
    recs = [r for r in recs if not SURVEY.search(r["title"] or "")]
    recs = [r for r in recs if (REPO / r["pdf_local_path"]).exists()][: args.n]
    print(f"selected {len(recs)} papers", flush=True)

    overlap = set()
    sd = REPO / "verification" / "sample_design.json"
    if sd.exists():
        rand = {s["paper_id"] for s in json.loads(sd.read_text())["sample"]}
        overlap = {r["paper_id"] for r in recs} & rand

    outdir = REPO / args.out
    outdir.mkdir(parents=True, exist_ok=True)
    xlsx = outdir / f"{args.who}_assignment.xlsx"

    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = openpyxl.Workbook()

    ws = wb.active
    ws.title = "README"
    lines = [
        (f"Verification assignment - {args.who}", True),
        ("", False),
        (f"{len(recs)} papers: the most-cited {args.track}-track papers that present an", False),
        ("attack or a defense. Surveys and SoKs are excluded, as are papers that", False),
        ("contribute no registry entry.", False),
        ("", False),
        ("WHAT THIS PACK IS AND IS NOT", True),
        ("These 20 were chosen because they are important, NOT at random. So the", False),
        ("accuracy you measure here describes THESE PAPERS and cannot be generalised", False),
        ("to the corpus: heavily-cited work is better known, better written, and", False),
        ("almost certainly better extracted than average.", False),
        ("", False),
        ("There is a separate 100-paper RANDOM sample that answers the general", False),
        ("question. Keep the two results apart - never pool them into one number.", False),
        ("  this pack        -> are our load-bearing papers coded correctly?", False),
        ("  random sample    -> how good is the extraction overall?", False),
        ("", False),
        ("HOW TO CODE", True),
        ("Work on the 'coding' sheet. One row per (paper, field). For each row put", False),
        ("one of these in the verdict column:", False),
        ("  correct       the value is right and the paper says so", False),
        ("  wrong         the paper says something different -> put the right value", False),
        ("                in correct_value_if_wrong", False),
        ("  not-in-paper  the paper never states this. NOT the same as 'wrong':", False),
        ("                this means the value was inferred or invented.", False),
        ("  unclear       ambiguous, or you cannot tell", False),
        ("", False),
        ("Do not fix the corpus. Record what you find. A silently corrected cell", False),
        ("destroys the measurement it was collected for.", False),
        ("", False),
        ("The 'papers' sheet is a one-row-per-paper overview if you want to read", False),
        ("across a paper's fields at once. PDFs are in pdfs/ in this zip, named by", False),
        ("title, matching the pdf_file column.", False),
        ("", False),
        ("FIELD CLASSES", True),
        ("core      the seven the headline numbers rest on - check these carefully", False),
        ("secondary supporting taxonomy fields", False),
        ("freetext  prose summaries; judge whether the paper supports the claim,", False),
        ("          not whether you would have worded it the same way", False),
    ]
    if overlap:
        lines += [("", False), ("NOTE", True),
                  (f"{len(overlap)} of these papers are also in the random sample.", False),
                  ("Whoever codes them there must be a different person, or the", False),
                  ("second reading is not independent.", False)]
    for i, (t, b) in enumerate(lines, start=1):
        c = ws.cell(row=i, column=1, value=t)
        if b:
            c.font = Font(bold=True)
    ws.column_dimensions["A"].width = 92

    ws2 = wb.create_sheet("papers")
    head2 = ["#", "title", "year", "venue", "citations", "role", "channel",
             "consequence", "pdf_file", "doi", "arxiv_id", "paper_id"]
    ws2.append(head2)
    for c in ws2[1]:
        c.font = Font(bold=True); c.fill = PatternFill("solid", fgColor="DDDDDD")
    ws2.freeze_panes = "A2"
    for i, r in enumerate(recs, start=1):
        ws2.append([i, r["title"], r["year"], r["venue"], r["citation_count"],
                    r["role"], r["channel"], r["consequence"],
                    pathlib.Path(r["pdf_local_path"]).name, r["doi"] or "",
                    r["arxiv_id"] or "", r["paper_id"]])
    for col, w in zip("ABCDEFGHIJKL", [4, 70, 6, 38, 10, 10, 14, 22, 70, 32, 12, 42]):
        ws2.column_dimensions[col].width = w
    ws2.auto_filter.ref = f"A1:L{len(recs)+1}"

    ws3 = wb.create_sheet("coding")
    head3 = ["#", "title", "pdf_file", "field", "field_class",
             "AI_extracted_value", "verdict", "correct_value_if_wrong", "note",
             "paper_id"]
    ws3.append(head3)
    for c in ws3[1]:
        c.font = Font(bold=True); c.fill = PatternFill("solid", fgColor="DDDDDD")
    ws3.freeze_panes = "D2"
    n = 0
    for i, r in enumerate(recs, start=1):
        for f in FIELDS:
            cls = "core" if f in CORE else "secondary" if f in SECONDARY else "freetext"
            v = r.get(f)
            v = "" if v is None else str(v)
            ws3.append([i, r["title"][:70], pathlib.Path(r["pdf_local_path"]).name,
                        f, cls, v[:500], "", "", "", r["paper_id"]])
            n += 1
    for col, w in zip("ABCDEFGHIJ", [4, 48, 60, 28, 11, 70, 14, 30, 34, 42]):
        ws3.column_dimensions[col].width = w
    for row in ws3.iter_rows(min_row=2, min_col=6, max_col=6):
        for c in row:
            c.alignment = Alignment(wrap_text=False, vertical="top")
    ws3.auto_filter.ref = f"A1:J{n+1}"
    wb.save(xlsx)

    zpath = outdir / f"{args.who}_assignment.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(xlsx, arcname=xlsx.name)
        for r in recs:
            src = REPO / r["pdf_local_path"]
            z.write(src, arcname=f"pdfs/{src.name}")
    size = zpath.stat().st_size / 1e6
    print(f"wrote {xlsx.relative_to(REPO)}  ({n} coding rows)")
    print(f"wrote {zpath.relative_to(REPO)}  ({len(recs)} PDFs, {size:.1f} MB)")
    if overlap:
        print(f"  NOTE: {len(overlap)} also in the random sample: "
              f"{sorted(x[:8] for x in overlap)}")

    (outdir / f"{args.who}_manifest.json").write_text(json.dumps(
        {"who": args.who, "selection": "purposive: most-cited Security papers "
         "presenting an attack or defense; surveys/SoKs excluded",
         "generalisable": False,
         "overlap_with_random_sample": sorted(overlap),
         "papers": [{"paper_id": r["paper_id"], "title": r["title"],
                     "citations": r["citation_count"],
                     "pdf": pathlib.Path(r["pdf_local_path"]).name} for r in recs]},
        indent=1))


if __name__ == "__main__":
    main()

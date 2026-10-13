"""Draw the stratified verification sample and emit the coding workbook.

The team verifies a subset of the corpus and generalises the measured accuracy
to the rest. That inference is only valid if the subset is a PROBABILITY
sample: hand-picking "important" or "representative" papers produces a number
that describes those papers and nothing else. So the sample is drawn with a
fixed seed, and the design is recorded alongside it.

Four disjoint strata, in priority order, chosen because each one either varies
the difficulty of extraction or carries a claim that cannot be checked any
other way:

  S1a no PDF, included  47 papers whose taxonomy fields were assigned without
                        full text - the free-text fields are populated at
                        exactly the rate PDFs exist (1097/1158), so these were
                        coded from abstracts. Highest suspected error rate and
                        currently unexamined.
  S2  track = "Both"    20 papers. Tiny, and RQ2's cross-citation rates depend
                        on track assignment being right.
  S2  track = "Both"    19 included papers. Tiny, and RQ2's cross-citation
                        rates depend on track assignment being right.
  S4  the main body     the remaining 960 included papers, sampled
                        proportionally by role so attack and defense papers -
                        which feed the RQ3 and RQ4 registries - are represented.

  S3  excluded, w/ PDF  118 papers dropped from the corpus, and
  S1b excluded, no PDF  14 more. A false exclude is invisible in every
                        downstream number and can never be found by checking
                        included papers only.

THE FRAME. The paper's claims are computed over the 1,026 INCLUDED papers, so
that is the primary estimand: S1a + S2 + S4 = 47 + 19 + 960 = 1,026. The two
excluded strata (132 papers) are sampled too, but reported SEPARATELY as a
false-exclude check - blending them into the headline would answer a question
nobody asked. Total coded rows are 1,158; 1,097 have a local PDF.

S1-S3 are deliberately OVERSAMPLED relative to their population share. That is
not a bias: each stratum carries a sampling weight N_h/n_h, and the overall
estimate is the weighted combination. Oversampling a small, high-risk stratum
buys precision where it matters without distorting the total, as long as the
weights are used - which `scripts/score_verification.py` does.

Output is an .xlsx with one row per (paper, field) so a verifier marks one
judgement per cell, plus a README sheet carrying the design and the weights.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import sqlite3

REPO = pathlib.Path(__file__).resolve().parent.parent
DB = REPO / "data" / "paper_explorer.db"

# Fields the paper's headline numbers rest on - verified for every sampled
# paper. Everything else is a free-text field checked on the same papers but
# scored separately, because "wrong" means something different for prose.
CORE_FIELDS = ["track", "screening", "role", "channel", "consequence",
               "cites_track_a", "cites_track_b"]
SECONDARY_FIELDS = ["defense_intervention_point", "temporal_persistence",
                    "evidence_grade", "artifacts_released"]
FREETEXT_FIELDS = ["models_evaluated", "datasets_benchmarks", "key_result",
                   "baselines_compared", "threat_model", "stated_limitations"]

VERDICTS = "correct | wrong | not-in-paper | unclear"


def strata(con):
    rows = con.execute(
        "select paper_id, title, year, venue, track, screening, role, "
        "citation_count, arxiv_id, pdf_local_path from paper").fetchall()
    out = {"S1a_no_pdf": [], "S2_track_both": [], "S4_main": [],
           "S3_excluded": [], "S1b_excl_no_pdf": []}
    for r in rows:
        pid, title, year, venue, track, screening, role, cites, arxiv, pdf = r
        rec = {"paper_id": pid, "title": title, "year": year, "venue": venue,
               "track": track, "screening": screening, "role": role,
               "citations": cites, "arxiv_id": arxiv, "pdf": pdf}
        excluded = (screening or "").lower().startswith("exclude")
        if not pdf:
            out["S1b_excl_no_pdf" if excluded else "S1a_no_pdf"].append(rec)
        elif excluded:
            out["S3_excluded"].append(rec)
        elif track == "Both":
            out["S2_track_both"].append(rec)
        else:
            out["S4_main"].append(rec)
    return out


def draw(pool, k, rng, by=None):
    """Proportional allocation across `by` when given, else a simple draw."""
    k = min(k, len(pool))
    if not by:
        return rng.sample(pool, k)
    groups = {}
    for r in pool:
        groups.setdefault(r.get(by) or "(none)", []).append(r)
    picked, total = [], len(pool)
    for g, items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        n_g = max(1, round(k * len(items) / total))
        picked += rng.sample(items, min(n_g, len(items)))
    rng.shuffle(picked)
    return picked[:k]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--seed", type=int, default=20261012)
    ap.add_argument("--dual_frac", type=float, default=0.20,
                    help="share double-coded by two people, for Cohen's kappa")
    ap.add_argument("--out", default="verification/verification_sample.xlsx")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    con = sqlite3.connect(DB)
    S = strata(con)

    # included frame (the primary estimand) gets 85; excluded gets 15
    alloc = {"S1a_no_pdf": 12, "S2_track_both": 10,
             "S3_excluded": 13, "S1b_excl_no_pdf": 2}
    alloc["S4_main"] = args.n - sum(alloc.values())

    sample, design = [], []
    for name, k in alloc.items():
        pool = S[name]
        picked = draw(pool, k, rng, by="role" if name == "S4_main" else None)
        for r in picked:
            r["stratum"] = name
        sample += picked
        design.append({"stratum": name,
                       "frame": ("excluded" if name in ("S3_excluded", "S1b_excl_no_pdf")
                                 else "included"),
                       "N_population": len(pool),
                       "n_sampled": len(picked),
                       "weight_N_over_n": round(len(pool) / max(1, len(picked)), 2),
                       "sampling_fraction_pct": round(100 * len(picked) / max(1, len(pool)), 1)})

    rng.shuffle(sample)
    n_dual = round(len(sample) * args.dual_frac)
    for i, r in enumerate(sample):
        r["dual_coded"] = "YES" if i < n_dual else ""
        r["assigned_to"] = ""

    outp = REPO / args.out
    outp.parent.mkdir(parents=True, exist_ok=True)

    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill
    wb = openpyxl.Workbook()

    # ---- README sheet ----
    ws = wb.active
    ws.title = "README"
    lines = [
        ("Context Integrity SoK - extraction verification sample", True),
        ("", False),
        (f"Drawn {len(sample)} papers: 85 from the 1,026 INCLUDED corpus (the primary", False),
        ("estimand) and 15 from the 132 excluded papers (a separate false-exclude check).", False),
        ("Report those two separately. Total coded rows 1,158; 1,097 have a local PDF.", False),
        (f"Seed {args.seed}. Regenerate exactly: python3 scripts/build_verification_sample.py --seed {args.seed}", False),
        ("", False),
        ("WHY THE SAMPLE LOOKS UNEVEN", True),
        ("Three small strata are deliberately oversampled. Each carries a weight", False),
        ("(N_population / n_sampled) and the overall accuracy is the weighted", False),
        ("combination, not the raw average. Do not compute a plain mean over the", False),
        ("100 rows - it will overstate the error rate, because the hardest papers", False),
        ("are on purpose over-represented.", False),
        ("", False),
        ("HOW TO CODE A CELL", True),
        (f"For each field, mark one of: {VERDICTS}", False),
        ("  correct       the value is right and the paper says so", False),
        ("  wrong         the paper says something different", False),
        ("  not-in-paper  the paper does not state this at all (the value was invented", False),
        ("                or inferred); this is NOT the same as 'wrong'", False),
        ("  unclear       the paper is ambiguous, or you cannot tell without more context", False),
        ("", False),
        ("Record disagreement rather than fixing it. The point is to measure the", False),
        ("error rate, not to silently repair the corpus - a corrected cell with no", False),
        ("record of the correction destroys the measurement.", False),
        ("", False),
        ("DOUBLE CODING", True),
        (f"{n_dual} rows are marked dual_coded=YES. Two people code those independently,", False),
        ("without seeing each other's answers, so inter-rater agreement (Cohen's", False),
        ("kappa) can be reported. Reviewers at USENIX/CCS expect this; without it", False),
        ("there is no evidence the humans agree either.", False),
        ("", False),
        ("S1 (no PDF): these 61 papers have NO local PDF and their free-text fields", False),
        ("are empty - the taxonomy codings were assigned from the abstract alone.", False),
        ("Fetch the paper if you can; if you cannot, mark 'unclear' rather than", False),
        ("guessing, and say so in the note.", False),
    ]
    for i, (text, bold) in enumerate(lines, start=1):
        c = ws.cell(row=i, column=1, value=text)
        if bold:
            c.font = Font(bold=True)
    ws.column_dimensions["A"].width = 95

    # ---- design sheet ----
    ws2 = wb.create_sheet("design")
    hdr = ["stratum", "frame", "N_population", "n_sampled", "weight_N_over_n", "sampling_fraction_pct"]
    ws2.append(hdr)
    for c in ws2[1]:
        c.font = Font(bold=True)
    for d in design:
        ws2.append([d[h] for h in hdr])
    for i, w in enumerate([22, 11, 16, 12, 18, 22], start=1):
        ws2.column_dimensions[chr(64 + i)].width = w

    # ---- the coding sheet ----
    ws3 = wb.create_sheet("coding")
    fields = CORE_FIELDS + SECONDARY_FIELDS + FREETEXT_FIELDS
    head = ["row", "stratum", "dual_coded", "assigned_to", "paper_id", "arxiv_id",
            "title", "year", "pdf_path", "field", "field_class",
            "AI_extracted_value", "verdict", "correct_value_if_wrong", "note"]
    ws3.append(head)
    for c in ws3[1]:
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor="DDDDDD")
    ws3.freeze_panes = "A2"

    vals = {}
    for r in sample:
        row = con.execute(
            f"select {', '.join(fields)} from paper where paper_id=?",
            (r["paper_id"],)).fetchone()
        vals[r["paper_id"]] = dict(zip(fields, row))

    n_row = 0
    for i, r in enumerate(sample, start=1):
        for f in fields:
            n_row += 1
            cls = ("core" if f in CORE_FIELDS
                   else "secondary" if f in SECONDARY_FIELDS else "freetext")
            v = vals[r["paper_id"]].get(f)
            v = "" if v is None else str(v)
            ws3.append([i, r["stratum"], r["dual_coded"], r["assigned_to"],
                        r["paper_id"], r["arxiv_id"] or "", r["title"][:120],
                        r["year"], r["pdf"] or "(no local PDF)", f, cls,
                        v[:400], "", "", ""])
    for col, w in zip("ABCDEFGHIJKLMNO",
                      [6, 14, 11, 13, 40, 12, 60, 7, 34, 26, 11, 60, 14, 28, 34]):
        ws3.column_dimensions[col].width = w
    ws3.auto_filter.ref = f"A1:O{n_row + 1}"

    wb.save(outp)

    meta = {"generated": "2026-10-12", "seed": args.seed, "n_papers": len(sample),
            "n_rows": n_row, "n_dual_coded": n_dual, "design": design,
            "core_fields": CORE_FIELDS, "secondary_fields": SECONDARY_FIELDS,
            "freetext_fields": FREETEXT_FIELDS,
            "sample": [{k: r[k] for k in ("paper_id", "stratum", "dual_coded",
                                          "title", "arxiv_id")} for r in sample]}
    (REPO / "verification" / "sample_design.json").write_text(json.dumps(meta, indent=1))

    print(f"wrote {outp.relative_to(REPO)}  ({len(sample)} papers x {len(fields)} fields "
          f"= {n_row} cells, {n_dual} dual-coded)")
    print(f"wrote verification/sample_design.json\n")
    print(f"{'stratum':<16}{'N':>7}{'n':>5}{'weight':>9}{'frac':>8}")
    for d in design:
        print(f"  {d['stratum']:<14}{d['N_population']:>7}{d['n_sampled']:>5}"
              f"{d['weight_N_over_n']:>9}{d['sampling_fraction_pct']:>7}%")


if __name__ == "__main__":
    main()

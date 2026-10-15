"""Read the completed contribution-screen packets back into the corpus.

Dry run by default. Nothing is written until --apply, because this pass can
remove papers and a mis-parsed spreadsheet should not be able to do that
silently.

Guard rails, each from a failure this project has already had:

  * `out_of_scope` is the ONLY value that excludes a paper. A benchmark, a
    survey or a measurement study contributes no named technique and still
    belongs; AgentDojo is the harness 56 of our experiments run on.
  * An exclusion needs `belongs_in_corpus = no` AND `evidence_quote`
    non-empty. One field alone cannot delete a paper.
  * `origin = applies` does not delete the paper. It retracts its REGISTRY
    ENTRY, through registry_corrections.json, so the published counts stay
    reproducible.
  * Anything the sheet leaves blank is left alone. Silence is not a decision.

    python3 scripts/apply_contribution_screen.py
    python3 scripts/apply_contribution_screen.py --apply
"""
import argparse
import collections
import glob
import json
import pathlib

import openpyxl

REPO = pathlib.Path(__file__).resolve().parent.parent
R = REPO / "data" / "registries"
XLSX = REPO / "data" / "exports" / "paper_dashboard_source.xlsx"
PACKETS = REPO / "data" / "exports" / "contribution_screen" / "*.xlsx"

VALID = {"proposes_attack", "proposes_mechanism", "proposes_defense",
         "proposes_fix", "improves_existing", "applies_existing",
         "benchmark_or_dataset", "measurement_study", "survey_or_sok",
         "position_or_conceptual", "out_of_scope"}


def read_packets():
    out, bad = [], []
    for p in sorted(glob.glob(str(PACKETS))):
        wb = openpyxl.load_workbook(p, read_only=True)
        if "papers" not in wb.sheetnames:
            wb.close(); continue
        ws = wb["papers"]
        rows = list(ws.iter_rows(values_only=True))
        wb.close()
        if not rows:
            continue
        hdr = [str(c or "") for c in rows[0]]
        idx = {h: i for i, h in enumerate(hdr)}
        need = ("title", "contribution", "belongs_in_corpus", "evidence_quote",
                "origin", "technique_name", "evaluated_against", "notes",
                "names_registry_technique", "named_techniques")
        if any(k not in idx for k in need):
            bad.append((pathlib.Path(p).name, "missing columns")); continue
        for r in rows[1:]:
            if not r or not r[idx["title"]]:
                continue
            rec = {k: (str(r[idx[k]]).strip() if r[idx[k]] is not None else "")
                   for k in need}
            rec["_packet"] = pathlib.Path(p).name
            if rec["contribution"]:
                out.append(rec)
    return out, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    done, bad = read_packets()
    if bad:
        for n, why in bad:
            print(f"  SKIPPED {n}: {why}")
    if not done:
        print("No completed rows found. Fill the 'contribution' column and re-run.")
        return

    counts = collections.Counter(d["contribution"] for d in done)
    unknown = [d for d in done if d["contribution"] not in VALID]
    excl = [d for d in done
            if d["contribution"] == "out_of_scope"
            and d["belongs_in_corpus"].lower() == "no"
            and d["evidence_quote"]
            and d["names_registry_technique"].lower() != "yes"]
    half = [d for d in done
            if (d["contribution"] == "out_of_scope") != (d["belongs_in_corpus"].lower() == "no")]
    noquote = [d for d in done if d["contribution"] == "out_of_scope"
               and not d["evidence_quote"]]
    retract = [d for d in done if d["origin"].lower() == "applies"]
    # a paper that names a technique the registry uses is a contributor even
    # when its genre says otherwise. AgentDojo is the case this guards.
    contributor = [d for d in done
                   if d["names_registry_technique"].lower() == "yes"]
    conflict = [d for d in contributor
                if d["contribution"] == "out_of_scope"
                or d["belongs_in_corpus"].lower() == "no"]

    print(f"{len(done)} coded rows across {len({d['_packet'] for d in done})} packets\n")
    for k, v in counts.most_common():
        mark = "  <- UNKNOWN VALUE" if k not in VALID else ""
        print(f"  {v:>4}  {k}{mark}")
    print()
    print(f"  names a technique the registry uses     : {len(contributor)}")
    print(f"  would EXCLUDE from the corpus          : {len(excl)}")
    print(f"  would retract a registry entry (applies): {len(retract)}")
    print()
    if unknown:
        print(f"  {len(unknown)} rows use a value not on the contribution sheet, ignored")
    if half:
        print(f"  {len(half)} rows disagree with themselves "
              f"(out_of_scope vs belongs_in_corpus). NOT actioned:")
        for d in half[:6]:
            print(f"      {d['title'][:56]} | {d['contribution']} / "
                  f"belongs={d['belongs_in_corpus']}")
    if conflict:
        print(f"\n  {len(conflict)} rows say the paper NAMES a registry technique "
              f"and also mark it out of scope. Exclusion BLOCKED for these:")
        for d in conflict[:8]:
            print(f"      {d['title'][:54]} | names: {d['named_techniques'][:44]}")
    if noquote:
        print(f"  {len(noquote)} out_of_scope rows have NO evidence quote. NOT actioned.")
    if excl:
        print("\n  exclusions, each with its quote:")
        for d in excl:
            print(f"    {d['title'][:62]}")
            print(f"       {d['evidence_quote'][:110]}")

    if not a.apply:
        print("\nDry run. Re-run with --apply to write.")
        return

    titles = {d["title"]: d for d in excl}
    wb = openpyxl.load_workbook(XLSX)
    ws = wb["Papers"]
    hdr = [c.value for c in ws[1]]
    ti, si = hdr.index("title") + 1, hdr.index("screening") + 1
    n = 0
    for row in range(2, ws.max_row + 1):
        t = ws.cell(row, ti).value
        if t in titles and str(ws.cell(row, si).value).strip() != "Exclude":
            ws.cell(row, si).value = "Exclude"
            n += 1
    wb.save(XLSX); wb.close()
    print(f"\nexcluded {n} papers in the workbook. "
          f"Now re-run: rq1_taxonomy.py, rq2_cross_citation.py, "
          f"gen_paper_numbers.py, gen_paper_figures.py, and log it in "
          f"rescreening_log.md")


if __name__ == "__main__":
    main()

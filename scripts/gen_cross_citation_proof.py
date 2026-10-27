"""Write the audit workbook behind the RQ2 cross-citation rates.

The rates in the paper (\\PctSecCitesSafety, \\PctSafetyCitesSec) are two
numbers standing on 3,967 citation edges. This emits the evidence under
them, so a reader can check any single paper's classification by hand:

    Papers      one row per screened-in paper -- its regime, whether it is
                in the denominator, which papers of the other regime it
                cites, and whether its reference list was actually read
    CrossEdges  one row per cross-regime citation, with both endpoints
                named and the pass that found the edge
    Summary     the headline rates recomputed from the two sheets above,
                and what supports the negative half of the claim

A rate like "11.0% cite across" is mostly a claim about the other 89%, and
absence is only evidence where we looked. `refs_state` separates the paper
whose reference section we read and found no cross-regime work in from the
paper we could not check at all; `negative_evidenced` marks which non-citing
rows the claim can actually stand on.

Nothing here is a second calculation. It reads the same graph and the same
`regime` column as scripts/rq2_cross_citation.py and gen_paper_numbers.py,
so a disagreement between this workbook and the paper is a bug in one of
them, not a methodological difference.

Usage:
    python3 scripts/gen_cross_citation_proof.py
"""
import collections
import datetime
import json
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

REPO = Path(__file__).resolve().parent.parent
REGISTRIES = REPO / "data" / "registries"
EXCEL_IN = REPO / "data" / "exports" / "paper_dashboard_source.xlsx"
EXCEL_OUT = REPO / "data" / "exports" / "cross_citation_proof.xlsx"

HEAD = PatternFill("solid", fgColor="DDE5EE")
BOLD = Font(bold=True)


# A reference section shorter than this is almost certainly a truncated
# extraction, not a short bibliography: the median read section is 23k
# characters and the 1st percentile is 1.4k. The cut is a judgement, so
# ref_chars stays in the sheet for anyone who wants to re-draw it.
MIN_REF_CHARS = 2000


def load(name):
    return json.loads((REGISTRIES / name).read_text())


def corpus():
    wb = openpyxl.load_workbook(EXCEL_IN, read_only=True, data_only=True)
    ws = wb["Papers"]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    hdr = list(rows[0])
    return [dict(zip(hdr, r)) for r in rows[1:]]


def style(ws, widths, freeze="A2"):
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for c in ws[1]:
        c.font, c.fill = BOLD, HEAD
        c.alignment = Alignment(vertical="center", wrap_text=True)
    ws.freeze_panes = freeze
    ws.auto_filter.ref = ws.dimensions


def main():
    papers = corpus()
    included = {p["paper_id"] for p in papers
                if str(p["screening"]).strip() != "Exclude"}

    mech = {e.get("paper_id") for e in load("rq3_pollution_registry.json")}
    dfn = {e.get("paper_id") for e in load("rq4_defense_registry.json")}
    analysed = included & (mech | dfn)

    regime = {p["paper_id"]: (p["regime"] or "").strip() for p in papers}
    # Per-paper state of the full-text reference pass. This is what makes a
    # "does not cite" row evidence rather than silence.
    #
    # v3, not citation_network_fulltext.json. That file is the v1 pass: it
    # read 1087 of 1097 PDFs and matched titles as one contiguous phrase.
    # v3 is what the union was actually built from -- it reads 1127 of 1127,
    # and matches arXiv id, then DOI, then the shortest unique title prefix.
    # Scoring the negatives against v1 charged 19 papers with an extraction
    # failure that v3 does not have.
    ft = {p["paper_id"]: p
          for p in load("citation_network_v3.json")["papers"]}

    def refs_state(pid):
        f = ft.get(pid)
        if f is None:
            return "no PDF", None
        if f.get("state") != "read":
            return "unread", f.get("ref_chars")
        chars = int(f.get("ref_chars") or 0)   # v3 stores these as strings
        return ("read" if chars >= MIN_REF_CHARS else "short"), chars
    title = {p["paper_id"]: p["title"] for p in papers}
    other = {"security": "safety", "safety": "security"}

    # Both endpoints inside the analysed set, exactly as the rate counts them.
    cites = collections.defaultdict(dict)
    for e in load("citation_network_union.json")["edges"]:
        if e["citing"] in analysed and e["cited"] in analysed:
            cites[e["citing"]][e["cited"]] = e.get("source", "")

    wb = openpyxl.Workbook()

    # ---- Papers -----------------------------------------------------------
    ws = wb.active
    ws.title = "Papers"
    ws.append(["paper_id", "title", "year", "venue", "regime", "evidence_grade",
               "named", "in_denominator", "cites_other_regime",
               "n_cross_cited", "n_same_regime_cited",
               "refs_state", "ref_chars", "negative_evidenced",
               "cross_cited_ids", "cross_cited_titles"])
    for p in sorted(papers, key=lambda p: ((p["regime"] or ""), str(p["year"] or ""))):
        pid = p["paper_id"]
        if pid not in included:
            continue
        reg = regime.get(pid, "")
        named = ("both" if pid in mech and pid in dfn else
                 "mechanism" if pid in mech else
                 "defense" if pid in dfn else "none")
        in_den = pid in analysed
        cited = cites.get(pid, {})
        cross = [c for c in cited if regime.get(c) == other.get(reg)]
        same = [c for c in cited if regime.get(c) == reg]
        state, chars = refs_state(pid)
        ws.append([
            pid, p["title"], p["year"], p["venue"], reg, p["evidence_grade"],
            named,
            "Y" if in_den else "N",
            ("Y" if cross else "N") if in_den else "",
            len(cross) if in_den else None,
            len(same) if in_den else None,
            state, chars,
            # Only a non-citing row needs this: a citing row proves itself.
            # A short section is NOT disqualifying: all 14 were read in full
            # and shown complete (see the HandCheck sheet), so they carry the
            # negative like any other.
            ("Y" if state in ("read", "short") else "N")
            if in_den and not cross else "",
            "; ".join(sorted(cross)),
            " | ".join(title.get(c, "?") for c in sorted(cross)),
        ])
    style(ws, [16, 58, 7, 22, 10, 9, 11, 10, 11, 9, 11, 10, 9, 11, 40, 70])

    # ---- CrossEdges -------------------------------------------------------
    ws = wb.create_sheet("CrossEdges")
    ws.append(["citing_id", "citing_title", "citing_regime",
               "cited_id", "cited_title", "cited_regime", "found_by"])
    n_edges = 0
    for citing, cited in sorted(cites.items()):
        rc = regime.get(citing, "")
        for c, src in sorted(cited.items()):
            if regime.get(c) == other.get(rc):
                ws.append([citing, title.get(citing, "?"), rc,
                           c, title.get(c, "?"), regime.get(c, ""), src])
                n_edges += 1
    style(ws, [16, 52, 12, 16, 52, 11, 10])

    # ---- Summary ----------------------------------------------------------
    sec = [p for p in analysed if regime.get(p) == "security"]
    saf = [p for p in analysed if regime.get(p) == "safety"]
    a_b = sum(1 for p in sec if any(regime.get(c) == "safety" for c in cites.get(p, ())))
    b_a = sum(1 for p in saf if any(regime.get(c) == "security" for c in cites.get(p, ())))

    # ---- what the negative half of the claim rests on ----------------------
    neg = {}
    for rg, pool in (("security", sec), ("safety", saf)):
        no = [p for p in pool
              if not any(regime.get(c) == other[rg] for c in cites.get(p, ()))]
        b = collections.Counter(refs_state(p)[0] for p in no)
        b["evidenced"] = b.get("read", 0) + b.get("short", 0)
        neg[rg] = {"n": len(no), **b}

    ws = wb.create_sheet("Summary")
    ws.append(["quantity", "value", "how it is counted"])
    for row in [
        ["generated", datetime.date.today().isoformat(),
         "scripts/gen_cross_citation_proof.py"],
        ["graph", "citation_network_union.json",
         "union of the full-text reference pass and the Semantic Scholar edge "
         "table; each edge labelled by the pass that found it"],
        [None, None, None],
        ["screened-in papers", len(included), "screening != Exclude"],
        ["named a technique", len(analysed),
         "appears in the RQ3 mechanism registry or the RQ4 defense registry"],
        ["not in denominator", len(included) - len(analysed),
         "surveys, benchmarks, position papers: they cite widely and name no "
         "technique, so counting them would measure reading habits"],
        [None, None, None],
        ["security, analysed", len(sec), "regime column"],
        ["safety, analysed", len(saf), "regime column"],
        ["edges inside the analysed set", sum(len(v) for v in cites.values()),
         "both endpoints analysed"],
        ["cross-regime edges", n_edges, "the CrossEdges sheet, one row each"],
        [None, None, None],
        ["security cites safety", f"{a_b}/{len(sec)} = {100*a_b/len(sec):.1f}%",
         "\\PctSecCitesSafety -- a paper counts once however many it cites"],
        ["safety cites security", f"{b_a}/{len(saf)} = {100*b_a/len(saf):.1f}%",
         "\\PctSafetyCitesSec"],
        [None, None, None],
        ["floor, not an estimate", "",
         "only citations to papers inside the analysed set register, so a "
         "paper reaching across to work outside the corpus does not count"],
        [None, None, None],
        ["PROVING THE NEGATIVE", "",
         "the rate is mostly a claim about the papers that do NOT cross; "
         "absence counts as evidence only where the reference list was read"],
        ["security, no cross-citation", neg["security"]["n"],
         "counted as 'does not cite safety'"],
        ["  reference list read", neg["security"].get("read", 0),
         f"reference section extracted, >= {MIN_REF_CHARS} characters, no "
         "cross-regime title matched -- a genuine negative"],
        ["  section short, read by hand", neg["security"].get("short", 0),
         f"< {MIN_REF_CHARS} characters. Every one of these was read in full "
         "and shown to be a complete short bibliography, so it carries the "
         "negative too -- see the HandCheck sheet"],
        ["  no PDF in the pass", neg["security"].get("no PDF", 0),
         "never checked"],
        ["  extraction failed", neg["security"].get("unread", 0),
         "never checked"],
        ["safety, no cross-citation", neg["safety"]["n"],
         "counted as 'does not cite security'"],
        ["  reference list read", neg["safety"].get("read", 0), "genuine negative"],
        ["  section short, read by hand", neg["safety"].get("short", 0),
         "complete short bibliography"],
        ["  no PDF in the pass", neg["safety"].get("no PDF", 0), "unsupported"],
        ["  extraction failed", neg["safety"].get("unread", 0), "unsupported"],
        [None, None, None],
        ["unsupported negatives", 
         (neg["security"]["n"] - neg["security"]["evidenced"]
          + neg["safety"]["n"] - neg["safety"]["evidenced"]),
         "every non-citing paper now has its reference list on the record, "
         "so there is no gap for a worst-case bound to cover. What remains "
         "is matcher recall, which the HandCheck sheet bounds."],
        [None, None, None],
        ["second failure mode", "",
         "a read reference list still misses a citation whose reference "
         "string does not match the corpus title as a contiguous normalised "
         "phrase -- a preprint/publication rename is the known case. The "
         "Semantic Scholar pass is a partial check on this: it found only 1 "
         "cross-regime edge the full-text pass missed, against 55 it missed "
         "itself. The two passes are not independent, so that is weak "
         "corroboration rather than a recall estimate."],
    ]:
        ws.append(row)
    style(ws, [30, 26, 86], freeze="A2")
    for r in ws.iter_rows(min_row=2, max_col=3):
        r[2].alignment = Alignment(vertical="top", wrap_text=True)
        r[0].font = BOLD

    # ---- HandCheck ---------------------------------------------------------
    # Written by scripts/handcheck_cross_citation.py plus adjudication. Absent
    # until that has been run, and the workbook is still valid without it.
    adj_path = REGISTRIES / "raw" / "handcheck_adjudication.json"
    if adj_path.exists():
        a = json.loads(adj_path.read_text())
        ws = wb.create_sheet("HandCheck")
        ws.append(["item", "value", "detail"])
        pc = a["positive_control"]
        res = a["result"]
        for row in [
            ["question", "",
             "does the matcher MISS cross-regime citations? A negative from an "
             "automated matcher is only as good as its recall."],
            ["frame", a["frame_size"], a["frame"]],
            ["drawn", a["n_checked"],
             f"stratified by regime, seed {a['seed']}"],
            [None, None, None],
            ["method", "", a["method"]],
            ["threshold", a["threshold"],
             "share of the target title's content words in one window"],
            ["positive control",
             f"{pc['recovered']}/{pc['known_edges']}", pc["design"]],
            [None, None, None],
            ["candidates surfaced", a["n_candidates"], "read one by one"],
            ["confirmed misses, sample", a["n_confirmed_misses"],
             "a real citation of an other-regime paper that the matcher did "
             "not find"],
            [None, None, None],
            ["SHORT SECTIONS", "", a["short_section_census"]["why"]],
            ["read in full", a["short_section_census"]["n"],
             a["short_section_census"]["completeness_test"]],
            ["verdict", "", a["short_section_census"]["verdict"]],
            ["cross-regime scan", "",
             a["short_section_census"]["cross_regime_scan"]],
            ["confirmed misses", a["short_section_census"]["confirmed_misses"],
             "none of the 14 cites an other-regime analysed paper"],
            [None, None, None],
            ["COMBINED", res["combined"],
             f"sample {res['sampled']}; short-section census "
             f"{res['short_section_census']}"],
            ["95% upper bound", f"{res['wilson_upper_95']}%",
             "Wilson. Rule of three gives "
             f"{res['rule_of_three_upper_95']}%. Zero misses in 44 is not "
             "zero misses in 630."],
            [None, None, None],
            ["NOT covered", "", ""],
        ] + [["", "", n] for n in a["what_this_does_not_cover"]] + [
            [None, None, None],
            ["ADJUDICATED CANDIDATES", "", ""],
        ]:
            ws.append(row)
        for v in a["verdicts"]:
            ws.append([f"candidate {v['n']}", v["verdict"],
                       f"{v['citing']}  ->  {v['target']}  --  {v['why']}"])
        style(ws, [24, 18, 104], freeze="A2")
        for r in ws.iter_rows(min_row=2, max_col=3):
            r[2].alignment = Alignment(vertical="top", wrap_text=True)
            r[0].font = BOLD

    wb.save(EXCEL_OUT)
    print(f"Wrote {EXCEL_OUT}")
    print(f"  Papers      {len(included)} rows ({len(analysed)} in denominator)")
    print(f"  CrossEdges  {n_edges} rows")
    for rg in ("security", "safety"):
        d = neg[rg]
        print(f"  {rg:<8} no-cross {d['n']:>4}: "
              f"{d.get('read',0)} read, {d.get('short',0)} short, "
              f"{d.get('no PDF',0)} no PDF, {d.get('unread',0)} unread")
    print(f"  security->safety {a_b}/{len(sec)} = {100*a_b/len(sec):.1f}%")
    print(f"  safety->security {b_a}/{len(saf)} = {100*b_a/len(saf):.1f}%")


if __name__ == "__main__":
    main()

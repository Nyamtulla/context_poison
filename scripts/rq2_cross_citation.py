"""Regenerate cross_citation_analysis.md from the current corpus state.

RQ2: do the two regimes cite each other, or have they evolved as
disconnected communities studying the same failure mode?

This reads the citation graph, not the hand-coded `cites_track_a` /
`cites_track_b` columns it used to read. Those columns are keyed to the old
`track` partition that the regime migration superseded, so a paper whose
regime changed kept a flag computed against the other partition. The two
methods disagreed by about five points -- 11.6% coded against 17.3% from the
graph -- and the paper moved to the graph while this script did not, so the
report and the paper printed different numbers for the same quantity.
`scripts/gen_paper_numbers.py` now computes \\PctSecCitesSafety the same way
this does, from the same file, against the same `regime` column on both
endpoints, so the two can no longer drift.

Usage:
    python3 scripts/rq2_cross_citation.py
"""
import collections
import datetime
import json
import sys
from pathlib import Path

import openpyxl

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

EXCEL_PATH = REPO_ROOT / "data" / "exports" / "paper_dashboard_source.xlsx"
REGISTRIES = REPO_ROOT / "data" / "registries"
OUTPUT_PATH = REPO_ROOT / "cross_citation_analysis.md"


def load(name):
    return json.loads((REGISTRIES / name).read_text())


def load_corpus():
    wb = openpyxl.load_workbook(EXCEL_PATH, read_only=True, data_only=True)
    ws = wb["Papers"]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    header = list(rows[0])
    idx = {name: i for i, name in enumerate(header)}
    return rows[1:], idx


def analysed_set(rows, idx):
    """The papers that named an attack or a defense.

    Not every screened-in paper. A survey or a benchmark names no technique,
    so it has no regime-specific stake in the literature it cites; counting
    it as a citer measures reading habits rather than whether the two
    communities build on each other. The cube, the census and the coverage
    matrix already use this denominator, and so does the paper.
    """
    included = {r[idx["paper_id"]] for r in rows
                if str(r[idx["screening"]]).strip() != "Exclude"}
    mech = {e.get("paper_id") for e in load("rq3_pollution_registry.json")}
    dfn = {e.get("paper_id") for e in load("rq4_defense_registry.json")}
    return included, included & (mech | dfn)


def compute_rates(rows, idx):
    included, analysed = analysed_set(rows, idx)
    regime = {r[idx["paper_id"]]: (r[idx["regime"]] or "").strip() for r in rows}

    # Only edges with both endpoints inside the analysed set count. A paper
    # reaching across to work we did not include does not register, so every
    # rate below is a floor.
    cites = collections.defaultdict(set)
    edges = load("citation_network_union.json")["edges"]
    for e in edges:
        if e["citing"] in analysed and e["cited"] in analysed:
            cites[e["citing"]].add(e["cited"])

    inc = [r for r in rows if r[idx["paper_id"]] in analysed]
    sec = [r for r in inc if regime.get(r[idx["paper_id"]]) == "security"]
    saf = [r for r in inc if regime.get(r[idx["paper_id"]]) == "safety"]

    def crosses(row, other):
        return any(regime.get(c) == other
                   for c in cites.get(row[idx["paper_id"]], ()))

    grade_stats = {"security": {}, "safety": {}}
    for side, rowset, other in (("security", sec, "safety"),
                                ("safety", saf, "security")):
        for row in rowset:
            grade = row[idx["evidence_grade"]] or "?"
            grade_stats[side].setdefault(grade, [0, 0])
            grade_stats[side][grade][0] += 1
            if crosses(row, other):
                grade_stats[side][grade][1] += 1

    return {
        "n_included": len(included),
        "n_analysed": len(analysed),
        "sec": len(sec), "saf": len(saf),
        "a_cites_b": sum(1 for r in sec if crosses(r, "safety")),
        "b_cites_a": sum(1 for r in saf if crosses(r, "security")),
        "n_edges": sum(len(v) for v in cites.values()),
        "grade_stats": grade_stats,
    }


def render_report(s):
    ta, tb = s["sec"], s["saf"]
    ab, ba = s["a_cites_b"], s["b_cites_a"]
    L = []
    L.append("# Cross-Citation Analysis (RQ2)")
    L.append("")
    L.append(f"Regenerated {datetime.date.today().isoformat()} by "
             "`scripts/rq2_cross_citation.py`.")
    L.append("")
    L.append("**RQ2:** Do the security-regime and safety-regime literatures cite each "
             "other, or have they evolved as disconnected communities studying the "
             "same failure mode?")
    L.append("")
    L.append("## Headline result")
    L.append("")
    L.append(f"Computed over the **{s['n_analysed']} analysed papers** -- those that "
             f"named an attack or a defense, out of {s['n_included']} screened in -- "
             f"from the {s['n_edges']:,} citation edges that run between them:")
    L.append("")
    L.append("| Direction | Papers citing >=1 paper from the other regime | "
             "Papers in regime | Rate |")
    L.append("|---|---|---|---|")
    L.append(f"| Security -> cites safety | {ab} | {ta} | **{ab/ta*100:.1f}%** |")
    L.append(f"| Safety -> cites security | {ba} | {tb} | **{ba/tb*100:.1f}%** |")
    L.append("")
    L.append("This is a full-population count over the analysed set, not a sample, so "
             "no confidence interval is reported.")
    L.append("")
    L.append("## By evidence grade")
    L.append("")
    L.append("| Grade | Security citing safety | Safety citing security |")
    L.append("|---|---|---|")
    for g in sorted(set(s["grade_stats"]["security"]) | set(s["grade_stats"]["safety"])):
        a_tot, a_hit = s["grade_stats"]["security"].get(g, [0, 0])
        b_tot, b_hit = s["grade_stats"]["safety"].get(g, [0, 0])
        a_str = f"{a_hit}/{a_tot} = {a_hit/a_tot*100:.1f}%" if a_tot else "n/a"
        b_str = f"{b_hit}/{b_tot} = {b_hit/b_tot*100:.1f}%" if b_tot else "n/a"
        L.append(f"| {g} | {a_str} | {b_str} |")
    L.append("")
    L.append("## Methodology note")
    L.append("")
    L.append("Both endpoints of every edge are classified by the `regime` column, and "
             "the edges come from `data/registries/citation_network_union.json` -- the "
             "same graph the paper's Figure 5 draws and the same one "
             "`scripts/gen_paper_numbers.py` reads for `\\PctSecCitesSafety`, so the "
             "report, the prose and the figure cannot disagree.")
    L.append("")
    L.append("Two limits bound the rates, and both push the same way:")
    L.append("")
    L.append("- The denominator is the analysed papers, not every screened-in paper. "
             "A survey cites widely and names no technique, so counting it would "
             "measure reading habits rather than whether the two communities build "
             "on each other.")
    L.append("- Only citations to papers inside that set register. A paper reaching "
             "across to work we did not include does not count.")
    L.append("")
    L.append("Every rate here is therefore a **floor**. The regime classification is "
             "automated over the discovery pool, so a systematic bias in it would "
             "move the rates; see `context_integrity_sok_project_plan.md` Section 12.")
    L.append("")
    return "\n".join(L)


def main():
    rows, idx = load_corpus()
    s = compute_rates(rows, idx)
    OUTPUT_PATH.write_text(render_report(s))
    print(f"Wrote {OUTPUT_PATH}")
    print(f"analysed {s['n_analysed']} of {s['n_included']} screened-in; "
          f"{s['n_edges']:,} internal edges")
    print(f"sec->safety: {s['a_cites_b']}/{s['sec']} = {s['a_cites_b']/s['sec']*100:.1f}%")
    print(f"safety->sec: {s['b_cites_a']}/{s['saf']} = {s['b_cites_a']/s['saf']*100:.1f}%")


if __name__ == "__main__":
    main()

"""Build the analysis pack: every coded field, in pivot-ready Excel.

context_sok_master_workbook.xlsx is the *reference* deliverable -- curated,
readable, one row per entity. This is the complementary one: the full coded
dataset with nothing dropped, plus long-format crosstabs you can drop straight
into a PivotTable, plus the RQ6/RQ7 evidence tables that live only in JSON.

    python3 scripts/build_analysis_workbook.py [-o out.xlsx]
"""
from __future__ import annotations
import argparse, collections, json, sys
from pathlib import Path

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from src import registry_source  # noqa: E402

REG = REPO / "data/registries"
HDR_FILL = PatternFill("solid", fgColor="12253C")
HDR_FONT = Font(bold=True, color="FFFFFF", size=10)


def sheet(wb, name, headers, rows, widths=None, freeze="A2"):
    ws = wb.create_sheet(name[:31])
    ws.append(headers)
    for c in range(1, len(headers) + 1):
        cell = ws.cell(1, c)
        cell.fill, cell.font = HDR_FILL, HDR_FONT
        cell.alignment = Alignment(vertical="center")
    for r in rows:
        ws.append(["" if v is None else v for v in r])
    for i, h in enumerate(headers, start=1):
        w = (widths or {}).get(h, min(max(12, len(str(h)) + 3), 42))
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = freeze
    ws.auto_filter.ref = ws.dimensions
    return ws


def jload(name, default=None):
    p = REG / name
    return json.loads(p.read_text()) if p.exists() else default


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=str(REPO / "context_sok_analysis_pack.xlsx"))
    args = ap.parse_args()

    reg = registry_source.load_all()
    mech, defs_, pairs = reg["mechanisms"], reg["defenses"], reg["pairs"]
    raw3 = jload("rq3_pollution_registry.json", [])
    raw4 = jload("rq4_defense_registry.json", [])

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    # ---------------------------------------------------------- 1. papers, full
    src = openpyxl.load_workbook(REPO / "data/exports/paper_dashboard_source.xlsx", read_only=True)
    sws = src["Papers"]
    hdr = [c.value for c in next(sws.iter_rows(min_row=1, max_row=1))]
    prows = [list(r) for r in sws.iter_rows(min_row=2, values_only=True)]
    src.close()
    # excel_row is the join key every registry file uses -- surface it explicitly
    sheet(wb, "Papers (all fields)", ["excel_row"] + hdr,
          [[i + 2] + r for i, r in enumerate(prows)],
          widths={"title": 55, "abstract": 60, "technical_summary": 60, "key_result": 55,
                  "threat_model": 50, "stated_limitations": 50, "baselines_compared": 50,
                  "models_evaluated": 45, "datasets_benchmarks": 45, "authors": 30})

    ci = {h: n for n, h in enumerate(hdr)}
    inc = [r for r in prows if r[ci["screening"]] == "Include"]

    # ------------------------------------------------- 2. RQ1 cube, long format
    intent = {"Security": "adversarial", "ML/AI": "incidental", "Both": "both",
              "Unclear": "unclear"}
    cube = collections.Counter(
        (r[ci["channel"]], intent.get(r[ci["track"]], "unclear"), r[ci["consequence"]])
        for r in inc)
    CH = ["tool-output", "direct-input", "RAG", "memory", "tool-metadata",
          "cross-modal", "multi-agent", "skill", "supply-chain"]
    IN = ["adversarial", "incidental", "both"]
    CO = ["goal-hijack", "reasoning-corruption", "silent-corruption",
          "persistence-backdoor", "data-exfiltration", "resource-abuse"]
    rows = [[c, i, q, cube.get((c, i, q), 0), "empty" if cube.get((c, i, q), 0) == 0 else "studied"]
            for c in CH for i in IN for q in CO]
    sheet(wb, "RQ1 cube (long)",
          ["channel", "intent", "consequence", "papers", "status"], rows)

    # -------------------------------------------- 3. RQ2 cross-citation per paper
    sheet(wb, "RQ2 cross-citation",
          ["excel_row", "paper_id", "title", "year", "track", "evidence_grade",
           "cites_track_a", "cites_track_b", "citation_count"],
          [[i + 2, r[ci["paper_id"]], r[ci["title"]], r[ci["year"]], r[ci["track"]],
            r[ci["evidence_grade"]], r[ci["cites_track_a"]], r[ci["cites_track_b"]],
            r[ci["citation_count"]]]
           for i, r in enumerate(prows) if r[ci["screening"]] == "Include"],
          widths={"title": 60})

    # ------------------------------------------------------- 4. mechanisms (RQ3)
    row_of_m = {m["name"]: m.get("row") for m in raw3}
    sheet(wb, "RQ3 mechanisms",
          ["mechanism_name", "excel_row", "track", "channel", "consequence", "confidence",
           "is_extension_of", "n_defenses_tested", "has_any_defense", "source_paper_title",
           "notes", "defenses_tested"],
          [[m["mechanism_name"], row_of_m.get(m["mechanism_name"], ""), m["track"], m["channel"],
            m["consequence"], m["confidence"], m.get("is_extension_of", ""),
            m["n_defenses_tested"], "YES" if m["has_any_defense"] else "NO",
            m.get("source_paper_title", ""), (m.get("notes") or "")[:900],
            "; ".join(m.get("defenses_tested", []))[:2000]] for m in mech],
          widths={"mechanism_name": 52, "source_paper_title": 52, "notes": 60,
                  "defenses_tested": 60})

    # --------------------------------------------------------- 5. defenses (RQ4)
    row_of_d = {d["name"]: d.get("row") for d in raw4}
    sheet(wb, "RQ4 defenses",
          ["defense_name", "excel_row", "track", "channel", "consequence",
           "defense_intervention_point", "validated_against", "confidence",
           "n_mechanisms_tested", "has_confirmed_match", "source_paper_title", "notes",
           "mechanisms_tested"],
          [[d["defense_name"], d.get("_row", row_of_d.get(d["defense_name"], "")), d["track"], d["channel"],
            d["consequence"], d.get("intervention_point", ""), d.get("validated_against", ""),
            d["confidence"], d.get("n_mechanisms_tested", 0),
            "YES" if d.get("has_confirmed_match") else "NO",
            d.get("source_paper_title", ""), (d.get("notes") or "")[:900],
            "; ".join(d.get("mechanisms_tested", []))[:2000]] for d in defs_],
          widths={"defense_name": 46, "source_paper_title": 52, "notes": 60,
                  "mechanisms_tested": 60})

    # ------------------------------------------------------ 6. pairs (RQ5), long
    sheet(wb, "RQ5 pairs",
          ["defense_name", "mechanism_name", "match_confidence", "source", "cross_track",
           "defense_track", "defense_intervention_point", "defense_validated_against",
           "mechanism_track", "mechanism_channel", "mechanism_consequence",
           "match_justification"],
          [[p["defense_name"], p["mechanism_name"], p.get("match_confidence", ""),
            p.get("source", ""), "YES" if p.get("cross_track") else "NO",
            p.get("defense_track", ""), p.get("defense_intervention_point", ""),
            p.get("defense_validated_against", ""), p.get("mechanism_track", ""),
            p.get("mechanism_channel", ""), p.get("mechanism_consequence", ""),
            (p.get("justification") or "")[:900]] for p in pairs],
          widths={"defense_name": 44, "mechanism_name": 46, "match_justification": 70})

    # ------------------------------------------- 7. coverage gap crosstabs (long)
    gap = []
    for dim in ("track", "channel", "consequence"):
        agg = collections.defaultdict(lambda: [0, 0])
        for m in mech:
            a = agg[m[dim]]
            a[1] += 1
            a[0] += 1 if m["has_any_defense"] else 0
        for k, (cov, tot) in sorted(agg.items(), key=lambda x: -x[1][1]):
            gap.append([dim, k, cov, tot - cov, tot, round(100 * cov / tot, 1)])
    sheet(wb, "RQ5 coverage gaps",
          ["dimension", "value", "covered", "uncovered", "total", "covered_pct"], gap)

    # ---------------------------------------------------- 8. uncovered mechanisms
    sheet(wb, "RQ5 uncovered",
          ["mechanism_name", "track", "channel", "consequence", "confidence",
           "source_paper_title", "notes"],
          [[m["mechanism_name"], m["track"], m["channel"], m["consequence"], m["confidence"],
            m.get("source_paper_title", ""), (m.get("notes") or "")[:900]]
           for m in mech if not m["has_any_defense"]],
          widths={"mechanism_name": 52, "source_paper_title": 52, "notes": 70})

    # ------------------------------------------- 9. defence evaluation targets
    det = jload("defense_eval_targets.json", [])
    if det:
        sheet(wb, "RQ4 eval targets",
              ["excel_row", "defense_name", "eval_target_kind", "eval_families",
               "eval_targets_named", "has_defense_baseline", "registry_matched",
               "mechanisms_matched", "source_paper_title"],
              [[d.get("row"), d.get("defense_name"), d.get("eval_target_kind"),
                "; ".join(d.get("eval_families") or []),
                "; ".join(d.get("eval_targets_named") or [])[:900],
                d.get("has_defense_baseline"), d.get("registry_matched"),
                "; ".join(d.get("mechanisms_matched") or [])[:900],
                d.get("source_paper_title", "")] for d in det],
              widths={"defense_name": 44, "eval_targets_named": 60, "source_paper_title": 50,
                      "mechanisms_matched": 50})

    # --------------------------------------- 10. RQ6 pair outcomes / verdicts
    po = jload("pair_outcomes.json", [])
    if po:
        sheet(wb, "RQ6 pair outcomes",
              ["defense_name", "mechanism_name", "defense_track", "cross_track",
               "defense_intervention_point", "mechanism_named_in_text",
               "claim_source_paper_title", "evidence"],
              [[o.get("defense_name"), o.get("mechanism_name"), o.get("defense_track"),
                "YES" if o.get("cross_track") else "NO",
                o.get("defense_intervention_point"), o.get("mechanism_named_in_text"),
                o.get("claim_source_paper_title", ""), (o.get("evidence") or "")[:900]]
               for o in po],
              widths={"defense_name": 44, "mechanism_name": 46,
                      "claim_source_paper_title": 50, "evidence": 70})

    # ------------------------------------ 11. reverse scan (attack-paper) pairs
    ape = jload("attack_paper_evaluations.json", {})
    cp = (ape or {}).get("confirmed_pairs", [])
    if cp:
        sheet(wb, "Reverse scan pairs",
              ["defense", "mechanism", "outcome", "pass", "source_paper", "evidence"],
              [[c.get("defense"), c.get("mechanism"), c.get("outcome"), c.get("pass"),
                c.get("source_paper", ""), (c.get("evidence") or "")[:900]] for c in cp],
              widths={"defense": 40, "mechanism": 44, "source_paper": 50, "evidence": 70})

    # ---------------------------------------------------- 12. headline figures
    st = reg["stats"]
    figs = [
        ("corpus rows", len(prows)), ("papers included", len(inc)),
        ("RQ3 mechanisms (registry)", len(raw3)),
        ("RQ3 mechanisms (incl. benchmark-supplementary)", len(mech)),
        ("RQ4 defenses", len(raw4)),
        ("RQ5 confirmed pairs", st["n_pairs"]),
        ("  of which from the original RQ5 pass", st["n_pairs_rq5_original"]),
        ("  of which supplementary/recovered", st["n_pairs_supplementary"]),
        ("defenses with >=1 confirmed match", st["n_defenses_matched"]),
        ("defenses with >=1 match (%)", round(100 * st["n_defenses_matched"] / st["n_defenses_total"], 1)),
        ("mechanisms with >=1 defense", st["n_mechs_covered"]),
        ("mechanisms with zero defenses", st["n_mechs_uncovered"]),
        ("cross-track pairs", sum(1 for p in pairs if p.get("cross_track"))),
        ("defenses validated against both threat models",
         sum(1 for d in raw4 if d.get("validated_against") == "both")),
    ]
    ws = sheet(wb, "Headline figures", ["figure", "value"], figs, widths={"figure": 52})
    ws.auto_filter.ref = None

    wb.save(args.out)
    print(f"Wrote {args.out}")
    for n in wb.sheetnames:
        print(f"   {n}")


if __name__ == "__main__":
    main()

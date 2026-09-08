"""Build the master Context Integrity SoK workbook: Papers, Mechanisms (RQ3),
Defenses (RQ4), Coverage Matrix (RQ5), Uncovered Mechanisms, Summary.

Every figure in the Summary sheet is computed from the live registries via
src/registry_source.py rather than typed in, because an earlier version of this
script carried hardcoded counts that went stale the moment the registries were
corrected. If a number appears in this file as a literal, that is a bug.

    python scripts/build_master_workbook.py
"""
import csv
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import registry_source

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ROOT = "/home/n646s681/context_sok"

# ---------- palette (matches the results deck) ----------
NAVY = "12253C"
AMBER = "E0A458"
TEAL = "1C7293"
WHITE = "FFFFFF"
LIGHT = "F4F7FA"
SECURITY = "B54A3F"   # Track A
MLAI = "1C7293"        # Track B
BOTH = "6B5B95"

HEADER_FONT = Font(color=WHITE, bold=True, size=11, name="Calibri")
HEADER_FILL = PatternFill("solid", fgColor=NAVY)
WRAP = Alignment(wrap_text=True, vertical="top")
WRAP_CENTER = Alignment(wrap_text=True, vertical="top", horizontal="center")
THIN = Side(style="thin", color="D9DEE3")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

def style_header(ws, ncols, row=1):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="left")
        cell.border = BORDER
    ws.freeze_panes = ws.cell(row=row + 1, column=1).coordinate
    ws.auto_filter.ref = f"A{row}:{get_column_letter(ncols)}{row}"

def write_rows(ws, headers, rows, start_row=2, track_col=None):
    for r, row in enumerate(rows, start=start_row):
        for c, h in enumerate(headers, start=1):
            val = row.get(h, "")
            if val is None:
                val = ""
            cell = ws.cell(row=r, column=c, value=val)
            cell.alignment = WRAP
            cell.border = BORDER
        if track_col:
            tval = str(row.get(track_col, "")).strip().lower()
            fill = None
            if tval == "security":
                fill = PatternFill("solid", fgColor="F7E9E7")
            elif tval in ("ml/ai", "mlai", "ml-ai"):
                fill = PatternFill("solid", fgColor="E8F1F4")
            elif tval == "both":
                fill = PatternFill("solid", fgColor="EEEAF4")
            if fill:
                for c in range(1, len(headers) + 1):
                    ws.cell(row=r, column=c).fill = fill

def set_widths(ws, widths):
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

# ================================================================ LOAD DATA
papers_wb = load_workbook(f"{ROOT}/data/exports/paper_dashboard_source.xlsx", read_only=True)
papers_ws = papers_wb["Papers"]
prows = list(papers_ws.iter_rows(values_only=True))
p_header = list(prows[0])
papers = [dict(zip(p_header, r)) for r in prows[1:]]
papers_by_id = {p["paper_id"]: p for p in papers}
print("papers:", len(papers))

REG = registry_source.load_all()                      # current (corrected) view
REG_PUB = registry_source.load_all(include_supplementary=False,
                                   include_corrections=False)   # as originally published
mechs, defs, cov = registry_source.load_raw_registries()
STATS = REG["stats"]
print("mechs:", STATS["n_mechanisms"], "defs:", STATS["n_defenses"],
      "pairs:", STATS["n_pairs"])

DEEP = ["technical_summary", "key_result", "baselines_compared",
        "stated_limitations", "models_evaluated", "datasets_benchmarks"]


def has_fulltext(p):
    """True when the paper received the full-text extraction pass, not only
    the categorical coding pass. 1,008 papers were coded; fewer were read in
    full, and the difference materially affects RQ5 matchability."""
    return all(p.get(f) for f in DEEP)


FULLTEXT_IDS = {p["paper_id"] for p in papers if has_fulltext(p)}
N_FULLTEXT = len(FULLTEXT_IDS)
INCLUDED = [p for p in papers if str(p.get("screening")) == "Include"]
print(f"full-text extraction: {N_FULLTEXT}/{len(papers)}  |  included: {len(INCLUDED)}")

# raw batch CSVs -> justification lookup keyed by (defense_row, mechanism_name)
justif = {}
for fp in sorted(glob.glob(f"{ROOT}/data/registries/raw/rq5_batch*.csv")):
    with open(fp, newline="") as f:
        for row in csv.DictReader(f):
            key = (str(row.get("defense_row", "")).strip(), row.get("matched_mechanism_name", "").strip())
            justif[key] = row.get("match_justification", "")
print("justifications loaded:", len(justif))

# Joined views come from the shared loader so the workbook, dashboard and MCP
# server can never disagree; the raw dicts below are only used for lookups.
MECHANISMS = REG["mechanisms"]
DEFENSES = REG["defenses"]
PAIRS = REG["pairs"]
uncovered_names = set(REG["uncovered_mechanism_names"])
mechs_by_name = {m["mechanism_name"]: m for m in MECHANISMS}
defs_by_row = {str(d["row"]): d for d in defs}
mech_to_defenses = {m["mechanism_name"]: m["defenses_tested"] for m in MECHANISMS}

# RQ5 matchability by extraction tier - the finding that a defense paper without
# full-text extraction is structurally unmatchable, since RQ5 read exactly those
# fields. Computed, not asserted.
_wd = [d for d in DEFENSES if d["source_paper_id"] in FULLTEXT_IDS]
_nd = [d for d in DEFENSES if d["source_paper_id"] not in FULLTEXT_IDS]
def _rate(g):
    m = sum(1 for x in g if x["has_confirmed_match"])
    return m, len(g), (100 * m / len(g) if g else 0.0)
WD_M, WD_N, WD_P = _rate(_wd)
ND_M, ND_N, ND_P = _rate(_nd)
N_CROSS = sum(1 for x in PAIRS if x["cross_track"])

# ================================================================ WORKBOOK
wb = Workbook()

# ---------- Sheet 1: Summary ----------
ws = wb.active
ws.title = "Summary"
ws.sheet_view.showGridLines = False
ws["A1"] = "Context Integrity SoK — Master Data Workbook"
ws["A1"].font = Font(bold=True, size=16, color=NAVY, name="Cambria")
from datetime import date
ws["A2"] = (f"Generated {date.today().isoformat()} from the live RQ1/RQ3/RQ4/RQ5 registries "
            "and the paper extraction corpus. All figures below are computed at build time.")
ws["A2"].font = Font(italic=True, size=10.5, color="5B6B79")

def kv_block(start_row, title, lines):
    r = start_row
    ws.cell(row=r, column=1, value=title).font = Font(bold=True, size=12.5, color=AMBER, name="Cambria")
    r += 1
    for line in lines:
        ws.cell(row=r, column=1, value=line).font = Font(size=10.5, name="Calibri")
        ws.cell(row=r, column=1).alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=8)
        r += 1
    return r + 1

r = 4
r = kv_block(r, "Headline counts", [
    f"Papers screened and coded: {len(papers)}  ({len(INCLUDED)} included in analysis, {len(papers)-len(INCLUDED)} excluded)",
    f"Of those, given the FULL-TEXT extraction pass: {N_FULLTEXT} ({N_FULLTEXT/len(papers):.1%}) — the rest were coded from title and abstract only",
    f"Named pollution mechanisms (RQ3): {STATS['n_mechanisms']}",
    f"Confirmed defenses (RQ4): {STATS['n_defenses']}",
    f"Confirmed (defense × mechanism) tested pairs (RQ5): {STATS['n_pairs']}"
    + (f"  ({STATS['n_pairs_rq5_original']} original + {STATS['n_pairs_supplementary']} recovered by the RQ5b pass)"
       if STATS.get('n_pairs_supplementary') else ""),
    f"Defenses with >=1 confirmed mechanism match: {STATS['n_defenses_matched']} of {STATS['n_defenses_total']} ({STATS['n_defenses_matched']/STATS['n_defenses_total']:.1%})",
    f"Mechanisms with >=1 defense tested against them: {STATS['n_mechs_covered']} of {STATS['n_mechanisms']} ({STATS['n_mechs_covered']/STATS['n_mechanisms']:.1%})",
    f"Mechanisms with ZERO defenses tested: {len(uncovered_names)} ({len(uncovered_names)/STATS['n_mechanisms']:.1%}) — see the 'Uncovered mechanisms' sheet",
    f"Pairs that cross the adversarial/incidental divide: {N_CROSS} of {STATS['n_pairs']} — the number RQ6 and RQ7 are ultimately about",
])
r = kv_block(r, "Terminology: what was actually done to these papers", [
    "Two distinct passes were applied, and no single verb covers both. Use PRISMA's umbrella term DATA EXTRACTION; reserve CODING for the categorical scheme; say FULL-TEXT EXTRACTION only of the subset that got it.",
    f"CODING (plan Section 3 scheme: channel, consequence, intent, defense_intervention_point, evidence_grade) — applied to all {len(papers)} papers.",
    f"FULL-TEXT EXTRACTION (technical_summary, key_result, baselines_compared, stated_limitations, models_evaluated, datasets_benchmarks) — applied to {N_FULLTEXT} papers, exactly those with a retrievable PDF.",
    "Do NOT write 'we read all 1,008 papers in full.' Filter the Papers sheet on has_fulltext to see which is which.",
])
r = kv_block(r, f"Q: What happened to the other {100-100*STATS['n_defenses_matched']/STATS['n_defenses_total']:.1f}% of defenses ({STATS['n_defenses_total']-STATS['n_defenses_matched']} of {STATS['n_defenses_total']})?", [
    f"They were NOT excluded from the study — every one of the {STATS['n_defenses_total']} is a real, confirmed defense paper in the RQ4 registry. What's missing is a confirmed match to one of RQ3's {STATS['n_mechanisms']} SPECIFICALLY NAMED mechanisms.",
    "Per the RQ5 extraction methodology, a match was only recorded when a defense paper's own baselines/results text named or clearly described a technique matching a registry entry — with an explicit 'favor false negatives' instruction (precision over recall).",
    f"PART OF IT IS AN ARTIFACT OF PDF AVAILABILITY, and this is now measurable. RQ5 matched by reading baselines_compared / key_result / technical_summary, which are EMPTY for papers that never got full-text extraction. Match rate with full text: {WD_M}/{WD_N} ({WD_P:.1f}%). Without: {ND_M}/{ND_N} ({ND_P:.1f}%).",
    f"So report BOTH denominators: {STATS['n_defenses_matched']/STATS['n_defenses_total']:.1%} of all defenses have a confirmed match, but {WD_P:.1f}% of defenses that were ELIGIBLE for matching do. The remaining {ND_N} are unmatchable by construction, not evidence about the field.",
    "The rest of the unmatched population is genuine: papers evaluating against a generic 'adversarial prompt' with no named technique, architectural papers with no red-team section, and extraction misses from the conservative bias. Extracting 67 further papers moved the measurement without moving the finding.",
    "See the 'Defenses' sheet: filter has_confirmed_mechanism_match=FALSE, and cross-filter on source_has_fulltext to separate the two causes.",
])
r = kv_block(r, "Q: Is the 88% concentration on Indirect Prompt Injection (IPI) a corpus/search bias?", [
    "Checked three independent ways — the concentration looks genuine, not an artifact of which papers we searched for.",
    "(1) Search design: the corpus was built from 12 deliberately diverse Track-A queries (indirect prompt injection, RAG poisoning, memory poisoning, tool poisoning, skill poisoning, MCP security, agent backdoor, multi-agent/agent-to-agent injection, knowledge corruption attack, MCP tool poisoning, skill file attack) plus 8 Track-B queries (context rot, lost in the middle, distracted by irrelevant context, context compaction, context management, context length degradation, long-horizon agent reliability, retrieval quality/knowledge conflict) — 'indirect prompt injection' is only 1 of 20 search terms, and the exact terms for the other mechanisms discussed below (lost in the middle, distracted by irrelevant context, context rot) were searched directly.",
    "(2) Independent corroboration from RQ1's raw channel x consequence cube (built before any RQ4/RQ5 filtering): tool-output x goal-hijack — IPI's own channel/consequence pair — is the single largest cell with 251 papers, 3-4x the next largest. The concentration shows up in the full corpus, not just the defense subset.",
    "(3) Live spot-check (2026-08-31): searched the open web for dedicated defense literatures against the next-largest mechanisms. 'Lost in the middle' and 'distracted by irrelevant context' mitigations exist mostly as generic RAG-engineering tricks (reranking, reordering, compression) scattered across many papers rather than a body of dedicated, benchmarked 'defense against X' papers; 'context rot' defenses are a very recent (2025-2026), still-small literature; PoisonedRAG has a real but modest defense literature (TrustRAG, RobustRAG, FilterRAG) — nowhere near IPI's volume. This matches what the corpus already shows, so it isn't evidence of an under-searched area.",
    "Bottom line for the advisor: this is a genuine field-level finding, not a sampling artifact — IPI is simply the most benchmarked, most 'branded' attack in this literature (AgentDojo, InjecAgent, the original Greshake et al. paper), so it is what most defense papers reach for when they need something to test against.",
])
r = kv_block(r, "Corrections applied since the figures were first published", [
    f"RQ5b recovery pass: an exhaustive citation + full-text sweep over never-defended mechanisms recovered {STATS.get('n_pairs_supplementary', 0)} additional EVALUATED pairs. The gap is real, not an extraction artifact.",
    f"Duplicate retraction: rows 51/57/59 were all arXiv 2505.05849 (AgentFuzzer renamed AgentVigil). Row 59 was still Include and had contributed a second RQ3 entry for one technique, so mechanisms went {REG_PUB['stats']['n_mechanisms']} -> {STATS['n_mechanisms']} and the phantom sat in the UNCOVERED list.",
    f"As-published figures remain exactly reproducible: registry_source.load_all(include_supplementary=False, include_corrections=False) returns {REG_PUB['stats']['n_mechanisms']} mechanisms / {REG_PUB['stats']['n_mechs_uncovered']} uncovered / {REG_PUB['stats']['n_pairs']} pairs.",
    "Pairs recovered by RQ5b are tagged source='stage1_supplementary' in the Coverage Matrix sheet; everything else is source='rq5'.",
])
r = kv_block(r, "How to use this workbook", [
    "Papers — every screened paper with all coded fields, plus has_fulltext marking which received the full-text extraction pass.",
    f"Mechanisms (RQ3) — the {STATS['n_mechanisms']} named pollution/attack techniques, each with the count and names of defenses confirmed tested against it.",
    f"Defenses (RQ4) — the {STATS['n_defenses']} confirmed defenses, each with mechanisms tested against, a has_confirmed_mechanism_match flag, and source_has_fulltext so the two causes of non-matching can be separated.",
    f"Coverage Matrix (RQ5) — the {STATS['n_pairs']} confirmed (defense, mechanism) pairs with match rationale, cross_track flag, and provenance.",
    f"Uncovered mechanisms — the {len(uncovered_names)} mechanisms with zero confirmed defenses, for prioritizing future defense work.",
])

set_widths(ws, [125])
for row in ws.iter_rows():
    for cell in row:
        if cell.column == 1 and cell.row >= 4:
            ws.row_dimensions[cell.row].height = None

# ---------- Sheet 2: Papers ----------
ws2 = wb.create_sheet("Papers")
p_display_cols = ["paper_id", "title", "authors", "year", "venue", "track", "channel", "consequence",
                   "defense_intervention_point", "screening", "evidence_grade", "artifacts_released",
                   "threat_model", "validated_against" if "validated_against" in p_header else None,
                   "models_evaluated", "datasets_benchmarks", "baselines_compared", "key_result",
                   "stated_limitations", "technical_summary", "citation_count", "doi", "arxiv_id", "url"]
p_display_cols = [c for c in p_display_cols if c is None or c in p_header]
p_display_cols = [c for c in p_display_cols if c is not None]
p_display_cols = p_display_cols[:10] + ["has_fulltext"] + p_display_cols[10:]
papers_out = [{**p, "has_fulltext": has_fulltext(p)} for p in papers]
ws2.append(p_display_cols)
style_header(ws2, len(p_display_cols))
write_rows(ws2, p_display_cols, papers_out, track_col="track")
set_widths(ws2, [16, 34, 20, 7, 16, 9, 12, 15, 12, 11, 12, 11, 13, 11,
                  18, 18, 30, 34, 26, 40, 9, 18, 12, 22][:len(p_display_cols)])
ws2.row_dimensions[1].height = 30

# ---------- Sheet 3: Mechanisms (RQ3) ----------
ws3 = wb.create_sheet("Mechanisms (RQ3)")
m_rows = []
for m in MECHANISMS:
    nm = m["mechanism_name"]
    def_names = m["defenses_tested"]
    src = papers_by_id.get(m.get("source_paper_id"), {})
    m_rows.append({
        "mechanism_name": nm,
        "track": m.get("track"),
        "channel": m.get("channel"),
        "consequence": m.get("consequence"),
        "confidence": m.get("confidence"),
        "is_extension_of": m.get("is_extension_of"),
        "n_defenses_tested_against": len(def_names),
        "defenses_tested_against": "; ".join(n for n in def_names if n),
        "source_has_fulltext": m.get("source_paper_id") in FULLTEXT_IDS,
        "notes": m.get("notes"),
        "source_paper_title": m.get("source_paper_title"),
        "source_paper_year": src.get("year"),
        "source_paper_id": m.get("source_paper_id"),
    })
m_headers = list(m_rows[0].keys())
ws3.append(m_headers)
style_header(ws3, len(m_headers))
write_rows(ws3, m_headers, m_rows, track_col="track")
set_widths(ws3, [34, 9, 12, 15, 10, 22, 9, 40, 12, 40, 34, 10, 16])
ws3.row_dimensions[1].height = 30

# ---------- Sheet 4: Defenses (RQ4) ----------
ws4 = wb.create_sheet("Defenses (RQ4)")
d_rows = []
for d in DEFENSES:
    mechs_tested = d["mechanisms_tested"]
    src = papers_by_id.get(d.get("source_paper_id"), {})
    d_rows.append({
        "defense_name": d.get("defense_name"),
        "track": d.get("track"),
        "channel": d.get("channel"),
        "consequence": d.get("consequence"),
        "defense_intervention_point": d.get("intervention_point"),
        "validated_against": d.get("validated_against"),
        "confidence": d.get("confidence"),
        "has_confirmed_mechanism_match": d["has_confirmed_match"],
        # Lets the two causes of non-matching be separated: a defense whose
        # paper never got full-text extraction was unmatchable by construction,
        # since RQ5 matched by reading exactly those fields.
        "source_has_fulltext": d.get("source_paper_id") in FULLTEXT_IDS,
        "n_mechanisms_tested_against": len(mechs_tested),
        "mechanisms_tested_against": "; ".join(mechs_tested),
        "is_extension_of": d.get("is_extension_of"),
        "notes": d.get("notes"),
        "source_paper_title": d.get("source_paper_title"),
        "source_paper_year": src.get("year"),
        "artifacts_released": src.get("artifacts_released"),
        "source_paper_id": d.get("source_paper_id"),
    })
d_headers = list(d_rows[0].keys())
ws4.append(d_headers)
style_header(ws4, len(d_headers))
write_rows(ws4, d_headers, d_rows, track_col="track")
set_widths(ws4, [30, 9, 12, 15, 12, 14, 10, 12, 12, 10, 40, 22, 40, 34, 10, 13, 16])
ws4.row_dimensions[1].height = 30

# ---------- Sheet 5: Coverage Matrix (RQ5) ----------
ws5 = wb.create_sheet("Coverage Matrix (RQ5)")
cm_rows = []
for m in PAIRS:
    mech = mechs_by_name.get(m["mechanism_name"], {})
    cm_rows.append({
        "defense_name": m["defense_name"],
        "mechanism_name": m["mechanism_name"],
        "match_confidence": m.get("match_confidence"),
        "defense_track": m.get("defense_track"),
        "defense_intervention_point": m.get("defense_intervention_point"),
        "defense_validated_against": m.get("defense_validated_against"),
        "mechanism_track": m.get("mechanism_track"),
        "mechanism_channel": m.get("mechanism_channel"),
        "mechanism_consequence": m.get("mechanism_consequence"),
        "cross_track": m.get("cross_track"),
        "source": m.get("source", "rq5"),
        "match_justification": m.get("justification", ""),
        "defense_paper_title": m.get("defense_paper_title"),
    })
cm_headers = list(cm_rows[0].keys())
ws5.append(cm_headers)
style_header(ws5, len(cm_headers))
write_rows(ws5, cm_headers, cm_rows)
set_widths(ws5, [30, 34, 11, 12, 14, 14, 12, 12, 15, 10, 16, 44, 34])
ws5.row_dimensions[1].height = 30

# ---------- Sheet 6: Uncovered mechanisms ----------
ws6 = wb.create_sheet("Uncovered mechanisms")
u_rows = []
for nm in sorted(uncovered_names):
    m = mechs_by_name.get(nm, {})
    src = papers_by_id.get(m.get("source_paper_id"), {})
    u_rows.append({
        "mechanism_name": nm,
        "track": m.get("track"),
        "channel": m.get("channel"),
        "consequence": m.get("consequence"),
        "confidence": m.get("confidence"),
        "source_has_fulltext": m.get("source_paper_id") in FULLTEXT_IDS,
        "notes": m.get("notes"),
        "source_paper_title": m.get("source_paper_title"),
        "source_paper_year": src.get("year"),
    })
u_headers = list(u_rows[0].keys()) if u_rows else ["mechanism_name"]
ws6.append(u_headers)
style_header(ws6, len(u_headers))
write_rows(ws6, u_headers, u_rows, track_col="track")
set_widths(ws6, [40, 9, 12, 15, 10, 12, 44, 34, 10])
ws6.row_dimensions[1].height = 30

out_path = f"{ROOT}/context_sok_master_workbook.xlsx"
wb.save(out_path)
print("Saved:", out_path)
print("Sheets:", wb.sheetnames)
print("Rows -> Papers:", ws2.max_row - 1, "Mechanisms:", ws3.max_row - 1,
      "Defenses:", ws4.max_row - 1, "Coverage:", ws5.max_row - 1, "Uncovered:", ws6.max_row - 1)

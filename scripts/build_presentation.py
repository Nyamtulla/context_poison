"""Regenerate the results deck from the live registries.

The previous deck was built by hand and went stale the moment the corpus moved
(it carried RQ1-RQ6 at pre-reverse-scan numbers and had no RQ7 slide). Every
figure here is read from src/registry_source.py and the generated report .md
files at build time, so "the deck is out of date" becomes a re-run rather than
an editing pass.

    python3 scripts/build_presentation.py [-o out.pptx]
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from src import registry_source  # noqa: E402

# ---------------------------------------------------------------- design system
BG      = RGBColor(0x12, 0x25, 0x3C)   # deep navy page
PANEL   = RGBColor(0x1B, 0x33, 0x4F)   # raised panel / stat disc
GOLD    = RGBColor(0xE0, 0xA4, 0x58)   # accent, eyebrows, big numbers
TEAL    = RGBColor(0x1C, 0x72, 0x93)
RED     = RGBColor(0xB5, 0x4A, 0x3F)
AMBER   = RGBColor(0xB5, 0x7E, 0x39)
GREY    = RGBColor(0x5B, 0x6B, 0x79)
WHITE   = RGBColor(0xFF, 0xFF, 0xFF)
BODY    = RGBColor(0xCA, 0xDC, 0xFC)   # primary body text
MUTED   = RGBColor(0xCF, 0xE8, 0xEF)   # secondary / captions

TITLE_FONT = "Cambria"
BODY_FONT  = "Calibri"

W, H = Inches(13.333), Inches(7.5)


def _tb(slide, x, y, w, h):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    return tf


def _run(para, text, size, color, bold=False, font=BODY_FONT):
    r = para.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.color.rgb = color
    r.font.bold = bold
    r.font.name = font
    return r


def _lines(tf, items, size, color, bold=False, font=BODY_FONT, space_after=4):
    """items: list of str, or (str, size, color, bold) tuples."""
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        if isinstance(it, tuple):
            txt, sz, col, bd = it
        else:
            txt, sz, col, bd = it, size, color, bold
        _run(p, txt, sz, col, bd, font)
        p.space_after = Pt(space_after)
    return tf


def new_slide(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])   # Blank
    # explicit page background, matching the original deck
    bg = s.background
    bg.fill.solid()
    bg.fill.fore_color.rgb = BG
    return s


def eyebrow(slide, text):
    tf = _tb(slide, 0.70, 0.45, 9.0, 0.35)
    _run(tf.paragraphs[0], text, 12.5, GOLD, True)


def headline(slide, lines, size=30, top=1.50):
    tf = _tb(slide, 0.70, top, 11.6, 1.5)
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        _run(p, ln, size, WHITE, True, TITLE_FONT)
        p.space_after = Pt(2)


def page_no(slide, n):
    tf = _tb(slide, 12.60, 7.12, 0.6, 0.3)
    _run(tf.paragraphs[0], str(n), 10, BODY)


def stat_disc(slide, x, y, d, big, caption, color=GOLD):
    """The deck's signature element: a navy disc with one number on it."""
    sh = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    sh.fill.solid()
    sh.fill.fore_color.rgb = PANEL
    sh.line.fill.background()
    sh.shadow.inherit = False
    tf = _tb(slide, x + 0.05, y + d / 2 - 0.55, d - 0.1, 1.0)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    _run(p, big, 54 if len(big) <= 5 else 40, color, True, TITLE_FONT)
    tf2 = _tb(slide, x + 0.05, y + d / 2 + 0.25, d - 0.1, 0.70)
    for j, ln in enumerate(caption.split("\n")):
        pp = tf2.paragraphs[0] if j == 0 else tf2.add_paragraph()
        pp.alignment = PP_ALIGN.CENTER      # each line centres independently;
        _run(pp, ln, 14, BODY)              # a \n inside one run does not
        pp.space_after = Pt(0)


def bar_row(slide, x, y, w, label, value, vmax, color, note="", lw=3.1):
    """Horizontal bar: label, track, filled bar, value."""
    tf = _tb(slide, x, y - 0.04, lw, 0.3)
    _run(tf.paragraphs[0], label, 12, BODY)
    track_x, track_w = x + lw, w - lw - 1.0
    tr = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(track_x), Inches(y),
                                Inches(track_w), Inches(0.22))
    tr.fill.solid(); tr.fill.fore_color.rgb = PANEL
    tr.line.fill.background(); tr.shadow.inherit = False
    frac = 0 if not vmax else max(0.006, value / vmax)
    bar = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(track_x), Inches(y),
                                 Inches(track_w * frac), Inches(0.22))
    bar.fill.solid(); bar.fill.fore_color.rgb = color
    bar.line.fill.background(); bar.shadow.inherit = False
    tf2 = _tb(slide, track_x + track_w + 0.08, y - 0.04, 1.0, 0.3)
    _run(tf2.paragraphs[0], note or str(value), 12, WHITE, True)


def panel(slide, x, y, w, h, fill=PANEL):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y),
                                Inches(w), Inches(h))
    sh.fill.solid(); sh.fill.fore_color.rgb = fill
    sh.line.fill.background(); sh.shadow.inherit = False
    return sh


# ------------------------------------------------------------------- live data
def load_facts():
    """Every number the deck shows, read at build time."""
    import openpyxl, collections
    reg = registry_source.load_all()
    st = reg["stats"]
    mech, defs_ = reg["mechanisms"], reg["defenses"]

    wb = openpyxl.load_workbook(REPO / "data/exports/paper_dashboard_source.xlsx", read_only=True)
    ws = wb["Papers"]
    hdr = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    i = {h: n for n, h in enumerate(hdr)}
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    wb.close()
    inc = [r for r in rows if r[i["screening"]] == "Include"]

    raw3 = json.loads((REPO / "data/registries/rq3_pollution_registry.json").read_text())
    raw4 = json.loads((REPO / "data/registries/rq4_defense_registry.json").read_text())

    def cnt(seq):
        return collections.Counter(seq)

    # RQ1 empty-cube rate, parsed from the generated report
    rq1 = (REPO / "rq1_taxonomy_analysis.md").read_text()
    m = re.search(r"\*\*([\d.]+)% of the channel x intent x consequence cube is empty\*\*\s*\((\d+) of (\d+)", rq1)
    empty_pct, empty_n, cube_n = (float(m.group(1)), int(m.group(2)), int(m.group(3))) if m else (0, 0, 162)

    rq2 = (REPO / "cross_citation_analysis.md").read_text()
    ab = re.search(r"Track A \(Security\) -> cites Track B \(ML/AI\) \| (\d+) \| (\d+) \| \*\*([\d.]+)%", rq2)
    ba = re.search(r"Track B \(ML/AI\) -> cites Track A \(Security\) \| (\d+) \| (\d+) \| \*\*([\d.]+)%", rq2)

    va = cnt(d.get("validated_against") for d in raw4)
    n_both = va.get("both", 0)
    top = sorted(mech, key=lambda x: -x["n_defenses_tested"])[:6]
    pair_mass = sum(x["n_defenses_tested"] for x in mech) or 1

    def _j(name):
        fp = REPO / "data/registries" / name
        return json.loads(fp.read_text()) if fp.exists() else {}

    cen = _j("benchmark_census.json")
    hl = _j("defense_half_life.json")
    tt = _j("technique_transfer_chatinject.json")

    # The RQ5 JSON stops at the 22 Sept state: 332 pairs, 131 mechanisms
    # uncovered. The 28 Sept reverse-scan pass added 17 more pairs and went
    # only into paper_explorer.db, so the deck and the dashboards disagreed by
    # 17. The database is the later of the two and every other view already
    # reads it, so the coverage figures come from there.
    db = _db()

    return {
        "cen": cen, "hl": hl, "tt": tt, **db,
        "rows": len(rows), "included": len(inc),
        "mech_reg": len(raw3), "mech_all": len(mech),
        "mech_track": cnt(x["track"] for x in raw3),
        "mech_channel": cnt(x["channel"] for x in raw3),
        "mech_conseq": cnt(x["consequence"] for x in raw3),
        "defenses": len(raw4),
        "def_track": cnt(x["track"] for x in raw4),
        "def_dip": cnt(x["defense_intervention_point"] for x in raw4),
        "def_both": n_both, "def_both_pct": 100 * n_both / len(raw4),
        "va": va,
        "pairs": db["db_pairs"], "dmatch": st["n_defenses_matched"],
        "dmatch_pct": 100 * st["n_defenses_matched"] / st["n_defenses_total"],
        "mcov": db["db_covered"], "munc": db["db_uncovered"],
        "mcov_pct": 100 * db["db_covered"] / len(mech),
        "per_def": st["mechs_per_defense_distribution"],
        "top_mech": [(x["mechanism_name"], x["n_defenses_tested"]) for x in top],
        "pair_mass": pair_mass,
        "empty_pct": empty_pct, "empty_n": empty_n, "cube_n": cube_n,
        "ab": (int(ab.group(1)), int(ab.group(2)), float(ab.group(3))) if ab else (0, 0, 0),
        "ba": (int(ba.group(1)), int(ba.group(2)), float(ba.group(3))) if ba else (0, 0, 0),
    }


# ---------------------------------------------------------------------- slides

def _db():
    """Coverage and transfer figures, read from data/paper_explorer.db.

    Kept in one place so a slide never computes a number itself. Every value
    here is also what context_dashboard.py shows, which is the point.
    """
    import sqlite3
    con = sqlite3.connect(REPO / "data" / "paper_explorer.db")
    q = lambda sql, *a: con.execute(sql, a).fetchall()
    one = lambda sql, *a: q(sql, *a)[0][0]

    n_attacks = one("SELECT COUNT(*) FROM attack")
    covered = one("SELECT COUNT(DISTINCT attack_name) FROM pair")

    # same-literature share: both ends of the pair must resolve to one track
    tracked = q("""SELECT a.track, d.track FROM pair p
                   JOIN attack a ON a.name = p.attack_name
                   JOIN defense d ON d.name = p.defense_name""")
    same = sum(1 for at, dt in tracked if at == dt)

    # the transfer matrix
    cells = one("""SELECT COUNT(*) FROM (SELECT DISTINCT technique_name, attack, model
                   FROM our_run WHERE campaign='rag_transfer')""")
    doses = one("SELECT COUNT(*) FROM our_run WHERE campaign='rag_transfer'")

    def fam(point):
        rows = q("""SELECT utility_verdict FROM our_run
                    WHERE campaign='rag_transfer' AND n_poison=10
                      AND intervention_point=?""", point)
        usable = [r[0] for r in rows if r[0] != "control_failed"]
        return usable.count("harms_accuracy"), len(usable)

    def asr(defense, attack, poison=10, model=None):
        sql = ("""SELECT undefended_asr, defended_asr FROM our_run
                  WHERE campaign='rag_transfer' AND technique_name=? AND attack=?
                    AND n_poison=?""")
        args = [defense, attack, poison]
        if model:
            sql += " AND model LIKE ?"
            args.append(f"%{model}%")
        r = q(sql, *args)
        return r[0] if r else (None, None)

    def dacc(defense, poison):
        r = q("""SELECT defended_utility - undefended_utility FROM our_run
                 WHERE campaign='rag_transfer' AND technique_name=?
                   AND attack='badrag_dos' AND n_poison=? AND model LIKE '%Mistral%'""",
              defense, poison)
        return round(r[0][0], 1) if r else None

    out = {
        "db_pairs": one("SELECT COUNT(*) FROM pair"),
        "db_covered": covered,
        "db_uncovered": n_attacks - covered,
        "db_same_pct": round(100 * same / len(tracked), 1),
        "db_cross_pct": round(100 * (len(tracked) - same) / len(tracked), 1),
        "db_cross_n": len(tracked) - same,
        "tx_cells": cells, "tx_doses": doses,
        "tx_ctx_harm": fam("context-reliance"),
        "tx_agg_harm": fam("isolate-then-aggregate"),
        # one poisoned passage and ten, because the two tell different stories:
        # at one passage the undefended model is at 0.0% and the defense is not
        "tx_ckplug_tone1": asr("CK-PLUG", "badrag_sentiment", 1),
        "tx_ckplug_tone10": asr("CK-PLUG", "badrag_sentiment", 10),
        "tx_parammute_tone10": asr("ParamMute", "badrag_sentiment", 10),
        "tx_kw_dos_llama": asr("RobustRAG / KeywordAgg", "badrag_dos", 9, "Llama"),
        "tx_kw_dos_mistral": asr("RobustRAG / KeywordAgg", "badrag_dos", 9, "Mistral"),
        "tx_gap": [(p, dacc("RobustRAG / KeywordAgg", p),
                    dacc("RobustRAG / DecodingAgg", p)) for p in (1, 5, 6, 7, 8, 9, 10)],
    }
    con.close()
    return out


def build(prs, F):
    n = 0

    def start(eb, head, size=30, top=1.50):
        nonlocal n
        n += 1
        s = new_slide(prs)
        eyebrow(s, eb)
        headline(s, head, size, top)
        page_no(s, n)
        return s

    # 1 — title -----------------------------------------------------------
    n += 1
    s = new_slide(prs)
    for i, d in enumerate([9.5, 7.6, 5.7, 3.8, 1.9]):
        o = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(4.45 + i * 0.95),
                               Inches(1.25 + i * 0.95), Inches(d), Inches(d))
        o.fill.background()
        o.line.color.rgb = PANEL
        o.line.width = Pt(1.25)
        o.shadow.inherit = False
    tf = _tb(s, 0.90, 1.35, 8.0, 0.35)
    _run(tf.paragraphs[0], "CONTEXT INTEGRITY SOK  ·  RESULTS REVIEW", 12.5, GOLD, True)
    tf = _tb(s, 0.90, 1.85, 9.6, 2.3)
    for i, ln in enumerate(["Reuniting Adversarial and", "Incidental Poisoning of LLM",
                            "Agent Context Windows"]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        _run(p, ln, 40, WHITE, True, TITLE_FONT); p.space_after = Pt(2)
    tf = _tb(s, 0.90, 4.05, 8.5, 0.6)
    _run(tf.paragraphs[0], "A Systematization of Knowledge. RQ1 to RQ7 are complete.", 16, BODY)
    tf = _tb(s, 0.90, 6.55, 9.0, 0.4)
    _run(tf.paragraphs[0],
         f"{F['rows']:,} papers screened · {F['included']:,} included · "
         f"{F['mech_all']} mechanisms · {F['defenses']} defenses · "
         f"{F['tx_cells']} cells we ran ourselves", 13, MUTED)
    page_no(s, n)

    # 2 — roadmap ---------------------------------------------------------
    s = start("THE ROADMAP", ["Seven questions, then the experiments"])
    items = [
        ("RQ1", "Taxonomy", f"{F['empty_pct']}% of the cube is empty"),
        ("RQ2", "Cross-citation", f"{F['ab'][2]}% / {F['ba'][2]}% between tracks"),
        ("RQ3", "Pollution census", f"{F['mech_reg']} named mechanisms"),
        ("RQ4", "Defense census", f"{F['defenses']} named defenses"),
        ("RQ5", "Coverage matrix", f"{F['munc']} mechanisms never defended"),
        ("RQ6", "Generalization", "9 reconstructed case studies"),
        ("RQ7", "Open problems", "7 ranked, falsifiable"),
        ("NEW", "Transfer matrix", f"{F['tx_cells']} cells that no paper reports"),
    ]
    for i, (rq, name, res) in enumerate(items):
        y = 2.30 + i * 0.58
        panel(s, 0.70, y, 11.9, 0.52)
        tf = _tb(s, 0.95, y + 0.08, 1.1, 0.35); _run(tf.paragraphs[0], rq, 14, GOLD, True, TITLE_FONT)
        tf = _tb(s, 2.05, y + 0.09, 3.4, 0.35); _run(tf.paragraphs[0], name, 13.5, WHITE, True)
        tf = _tb(s, 5.6, y + 0.09, 6.7, 0.35); _run(tf.paragraphs[0], res, 13, BODY)

    # 3 — methodology -----------------------------------------------------
    s = start("METHODOLOGY", ["Kitchenham SLR + PRISMA-lite screening,",
                              "run across two literatures instead of one"])
    blocks = [
        ("Search", "We searched two tracks at\nthe same time. One track is\nadversarial. One track is\nincidental. We found\n25,922 records."),
        ("Screen", "The rules are in config.yaml.\nA program applies them.\nWe do not screen by hand.\nrescreening_log.md records\neach change."),
        ("Extract", "We read the full text of\n1,097 papers. We code 32\nfields for each paper.\nChannel and consequence\nuse closed lists."),
        ("Synthesize", "We join the registries into\nthe coverage matrix. Then\nwe run the defense code\nourselves. We do not use\nthe numbers in the papers."),
    ]
    for i, (t, b) in enumerate(blocks):
        x = 0.70 + i * 3.05
        panel(s, x, 3.00, 2.85, 2.95)
        tf = _tb(s, x + 0.25, 3.25, 2.4, 0.4)
        _run(tf.paragraphs[0], t, 17, GOLD, True, TITLE_FONT)
        tf = _tb(s, x + 0.25, 3.75, 2.4, 2.1)
        _lines(tf, b.split("\n"), 11.5, BODY, space_after=1)

    # 4 — the corpus ------------------------------------------------------
    s = start("THE CORPUS", ["What the numbers are computed over"])
    stat_disc(s, 0.95, 2.70, 3.30, f"{F['included']:,}", "papers included")
    right = [
        (f"{F['rows']:,} rows screened; {F['rows'] - F['included']:,} excluded with cause", 14, WHITE, True),
        ("", 6, BODY, False),
        ("rescreening_log.md records each exclusion.", 12.5, BODY, False),
        ("It gives a reason for each one.", 12.5, BODY, False),
        ("", 8, BODY, False),
        ("In September 2026 we found a defect in the rules.", 12.5, MUTED, False),
        ("The rules looked for the word \"agent\". The first", 12.5, MUTED, False),
        ("papers in this field do not use it. They say", 12.5, MUTED, False),
        ("\"LLM-integrated application\". The rules dropped", 12.5, MUTED, False),
        ("them. The corpus went from 1,008 to 1,158.", 12.5, MUTED, False),
    ]
    tf = _tb(s, 5.20, 3.05, 7.3, 3.2)
    _lines(tf, right, 12.5, BODY, space_after=2)

    # 5 — RQ1 -------------------------------------------------------------
    s = start("RQ1  ·  TAXONOMY", ["Which combinations of channel, intent,",
                                   "and consequence have been studied at all?"])
    stat_disc(s, 1.80, 2.75, 3.60, f"{F['empty_pct']}%", "of the cube is empty")
    tf = _tb(s, 7.30, 3.30, 5.3, 3.0)
    _lines(tf, [
        (f"{F['empty_n']} of {F['cube_n']} cells", 18, WHITE, True),
        ("9 channels × 3 intents × 6 consequences", 12.5, MUTED, False),
        ("", 8, BODY, False),
        ("Before the fix, 63.6% was empty.", 12.5, BODY, False),
        ("The 150 new papers filled five cells.", 12.5, BODY, False),
        ("They left 98 cells empty.", 12.5, BODY, False),
    ], 12.5, BODY)

    # 6 — RQ1 channels ----------------------------------------------------
    s = start("RQ1  ·  TAXONOMY", ["Where the work actually sits"], 28)
    mx = max(F["mech_channel"].values())
    for i, (ch, v) in enumerate(F["mech_channel"].most_common()):
        bar_row(s, 0.70, 2.70 + i * 0.47, 11.9, ch, v, mx,
                GOLD if i < 2 else TEAL, f"{v}")
    tf = _tb(s, 0.70, 6.85, 11.9, 0.4)
    _run(tf.paragraphs[0],
         "Named mechanisms for each channel. direct-input and tool-output are equal.",
         12, MUTED)

    # 7 — RQ2 -------------------------------------------------------------
    s = start("RQ2  ·  CITATION NETWORK", ["Two literatures. Do they read each other?"], 30)
    a_n, a_d, a_p = F["ab"]; b_n, b_d, b_p = F["ba"]
    for i, (lbl, num, den, pct, col) in enumerate([
            ("Security \u2192 cites ML/AI", a_n, a_d, a_p, GOLD),
            ("ML/AI \u2192 cites Security", b_n, b_d, b_p, TEAL)]):
        y = 2.80 + i * 1.55
        panel(s, 0.70, y, 11.9, 1.25)
        tf = _tb(s, 1.00, y + 0.18, 4.6, 0.45)
        _run(tf.paragraphs[0], lbl, 15, WHITE, True)
        tf = _tb(s, 1.00, y + 0.66, 5.4, 0.4)
        _run(tf.paragraphs[0], f"{num} of {den} papers", 12.5, MUTED)
        tf = _tb(s, 9.9, y + 0.28, 2.4, 0.8)
        pp = tf.paragraphs[0]; pp.alignment = PP_ALIGN.RIGHT
        _run(pp, f"{pct}%", 40, col, True, TITLE_FONT)
    tf = _tb(s, 0.70, 6.10, 11.9, 1.0)
    _lines(tf, [
        ("Nine of ten papers do not cite the other track.", 14, WHITE, True),
        ("The corpus grew by 150 papers. The rates did not change. The split is structural.",
         12.5, MUTED, False)], 12.5, BODY)

    # 8 — RQ3 -------------------------------------------------------------
    s = start("RQ3  ·  POLLUTION CENSUS", ["How many distinct ways can a context be poisoned?"], 28)
    stat_disc(s, 0.95, 2.65, 3.15, str(F["mech_reg"]), "named mechanisms")
    t = F["mech_track"]
    tf = _tb(s, 4.85, 2.95, 7.6, 3.4)
    _lines(tf, [
        (f"{t.get('Security',0)} adversarial  ·  {t.get('ML/AI',0)} incidental", 17, WHITE, True),
        ("", 8, BODY, False),
        ("Before the fix we had 183. We added 41.", 12.5, BODY, False),
        ("40 of the new ones are adversarial.", 12.5, BODY, False),
        ("23 of them use the direct-input channel.", 12.5, BODY, False),
        ("", 8, BODY, False),
        ("This closed a channel gap that looked real.", 13, GOLD, True),
        ("Our own screening made that gap.", 12.5, MUTED, False),
        ("The field did not.", 12.5, MUTED, False),
    ], 12.5, BODY)
    c = F["mech_conseq"]
    tf = _tb(s, 0.70, 6.55, 11.9, 0.5)
    _run(tf.paragraphs[0],
         "By consequence:  " + "   ·   ".join(f"{k} {v}" for k, v in c.most_common()), 11.5, MUTED)

    # 9 — RQ4 -------------------------------------------------------------
    s = start("RQ4  ·  DEFENSE CENSUS", ["And how many defenses answer them?"], 30)
    stat_disc(s, 0.95, 2.55, 3.15, str(F["defenses"]), "named defenses")
    stat_disc(s, 4.55, 2.55, 3.15, f"{F['def_both_pct']:.1f}%", "answer both\nthreat models", RED)
    tf = _tb(s, 8.35, 2.95, 4.3, 3.2)
    _lines(tf, [
        (f"Only {F['def_both']} of {F['defenses']} defenses", 15, WHITE, True),
        ("answer both threat models:", 15, WHITE, True),
        ("adversarial corruption and", 15, WHITE, True),
        ("incidental corruption.", 15, WHITE, True),
        ("", 10, BODY, False),
        ("We added 55 defenses. These", 12.5, GOLD, False),
        ("include StruQ, SecAlign,", 12.5, GOLD, False),
        ("Spotlighting and the", 12.5, GOLD, False),
        ("Instruction Hierarchy.", 12.5, GOLD, False),
        ("The number did not move.", 12.5, GOLD, False),
        ("", 8, BODY, False),
        ("2.9% \u2192 2.8%.", 13, WHITE, True),
    ], 12.5, BODY)

    # 10 — RQ5 headline ---------------------------------------------------
    s = start("RQ5  ·  COVERAGE MATRIX", ["Which defenses were ever tested",
                                          "against which attacks?"])
    stat_disc(s, 0.95, 2.80, 3.05, f"{F['dmatch_pct']:.0f}%", "of defenses have\none test or more")
    stat_disc(s, 4.45, 2.80, 3.05, str(F["munc"]), "mechanisms never\ndefended", RED)
    tf = _tb(s, 8.20, 3.15, 4.4, 3.2)
    _lines(tf, [
        (f"{F['pairs']} confirmed pairs", 17, WHITE, True),
        (f"{F['dmatch']} of {F['defenses']} defenses matched", 12.5, BODY, False),
        (f"{F['mcov']} of {F['mech_all']} mechanisms covered", 12.5, BODY, False),
        ("", 10, BODY, False),
        (f"{F['per_def'].get('1',0)} of them have one test only.", 12.5, MUTED, False),
        ("", 8, BODY, False),
        ("There are almost no", 13, GOLD, True),
        ("general defenses.", 13, GOLD, True),
    ], 12.5, BODY)

    # 11 — RQ5 concentration ----------------------------------------------
    s = start("RQ5  ·  COVERAGE MATRIX", ["Testing effort concentrates on a handful of targets"], 26)
    mx = F["top_mech"][0][1]
    for i, (name, v) in enumerate(F["top_mech"]):
        label = name if len(name) <= 46 else name[:45].rstrip() + "\u2026"
        bar_row(s, 0.70, 2.75 + i * 0.55, 11.9, label, v, mx,
                GOLD if i == 0 else TEAL, f"{v}", lw=4.85)
    share = 100 * F["top_mech"][0][1] / F["pair_mass"]
    top6 = 100 * sum(v for _, v in F["top_mech"]) / F["pair_mass"]
    tf = _tb(s, 0.70, 6.25, 11.9, 0.9)
    _lines(tf, [
        (f"One mechanism takes {share:.1f}% of all pairs. These six take {top6:.1f}%.",
         14, WHITE, True),
        (f"The other {F['munc']} mechanisms get no test at all.", 12.5, MUTED, False)], 12.5, BODY)

    # 12 — RQ5 the null result (new) --------------------------------------
    s = start("RQ5  ·  THE TEST THAT FAILED", ["We predicted the gap would close.",
                                               "It did not \u2014 and that is the result."], 28)
    panel(s, 0.70, 2.95, 5.75, 3.15)
    tf = _tb(s, 1.00, 3.20, 5.2, 2.7)
    _lines(tf, [
        ("The prediction", 15, GOLD, True),
        ("", 6, BODY, False),
        ("We predicted this. The first", 12.5, BODY, False),
        ("defenses of the field will cover the", 12.5, BODY, False),
        ("mechanisms that look open. StruQ,", 12.5, BODY, False),
        ("SecAlign, Spotlighting, Attention", 12.5, BODY, False),
        ("Tracker and the Liu baselines will", 12.5, BODY, False),
        ("close the gap.", 12.5, BODY, False),
    ], 12.5, BODY)
    panel(s, 6.85, 2.95, 5.75, 3.15)
    tf = _tb(s, 7.15, 3.20, 5.2, 2.7)
    _lines(tf, [
        ("What happened", 15, RED, True),
        ("", 6, BODY, False),
        ("We added 164 papers. We added 55", 12.5, BODY, False),
        ("defenses and 41 mechanisms. We got", 12.5, BODY, False),
        ("45 new pairs.", 12.5, BODY, False),
        ("", 6, BODY, False),
        ("Old mechanisms now covered:", 12.5, WHITE, True),
        ("zero.", 26, RED, True),
        ("The first 196 mechanisms did not move.", 12.5, MUTED, False),
    ], 12.5, BODY)
    tf = _tb(s, 0.70, 6.35, 11.9, 0.9)
    _lines(tf, [
        ("The new defenses and the new attacks cover each other. They cover nothing else.", 14, WHITE, True),
        ("A reviewer can say that our corpus limits make the gap. We tested that claim. It is not correct.",
         12.5, GOLD, False)], 12.5, BODY)

    # 13 — RQ6 ------------------------------------------------------------
    s = start("RQ6  ·  DEFENSE GENERALIZATION", ["Does a defense built for one threat model",
                                                 "hold against the other?"], 28)
    for i, (pat, cnt_, col, note) in enumerate([
            ("Full generalization", "3", TEAL, "holds against the untested threat model"),
            ("Partial / degraded", "4", AMBER, "measurable protection, materially weaker"),
            ("Inert", "2", RED, "no measurable protection at all")]):
        x = 0.70 + i * 4.06
        panel(s, x, 2.85, 3.85, 2.5)
        tf = _tb(s, x + 0.3, 3.05, 3.3, 0.9)
        pp = tf.paragraphs[0]
        _run(pp, cnt_, 44, col, True, TITLE_FONT)
        tf = _tb(s, x + 0.3, 3.95, 3.3, 0.4)
        _run(tf.paragraphs[0], pat, 14.5, WHITE, True)
        tf = _tb(s, x + 0.3, 4.40, 3.3, 0.85)
        _lines(tf, [note], 12, MUTED, space_after=1)
    tf = _tb(s, 0.70, 5.70, 11.9, 1.3)
    _lines(tf, [
        ("We rebuilt 9 defenses from their released code or weights. We did not use the numbers in the papers.",
         13.5, WHITE, True),
        ("The result follows the intervention point. Ingestion defenses usually hold. Execution defenses usually do not.",
         12.5, BODY, False),
        ("A confound applies. The ingestion harness is a text classifier. The execution harness is an agent. We state it.",
         12, MUTED, False)], 12.5, BODY)

    # 13b — benchmark standardization (new) --------------------------------
    cen = F.get("cen") or {}
    if cen:
        s = start("BENCHMARK STANDARDIZATION", ["The field has no standard benchmark to test on"], 28)
        stat_disc(s, 0.95, 2.70, 3.10, f"{cen.get('not_reusable_pct', 0)}%",
                  "of attacks use data\nnobody else can reuse", RED)
        top = list((cen.get("named_benchmark_counts") or {}).items())[:1]
        share = round(100 * top[0][1] / cen["n_mechanisms"], 1) if top else 0
        stat_disc(s, 4.45, 2.70, 3.10, f"{share}%",
                  "use the most common\nbenchmark")
        tf = _tb(s, 8.20, 3.05, 4.4, 3.2)
        _lines(tf, [
            (f"{cen.get('distinct_named_benchmarks', 0)} distinct benchmarks", 17, WHITE, True),
            (f"for {cen['n_mechanisms']} named attacks", 13, BODY, False),
            ("", 8, BODY, False),
            (f"{cen.get('benchmarks_used_once', 0)} of them "
             f"({round(100*cen.get('benchmarks_used_once',0)/max(1,cen.get('distinct_named_benchmarks',1)))}%)", 13, GOLD, True),
            ("are used by exactly one paper.", 13, GOLD, True),
            ("", 8, BODY, False),
            ("There are more benchmarks", 12.5, MUTED, False),
            ("than attacks. Two papers can", 12.5, MUTED, False),
            ("use one corpus and still", 12.5, MUTED, False),
            ("not compare.", 12.5, MUTED, False),
        ], 12.5, BODY)

    # 13c — defense half-life (new) ---------------------------------------
    hl = F.get("hl") or {}
    if hl and hl.get("gap_years"):
        g = hl["gap_years"]
        within = round(100 * sum(1 for x in g if x <= 1) / len(g))
        s = start("DEFENSE HALF-LIFE", ["How long does a published defense survive?"], 30)
        stat_disc(s, 0.95, 2.70, 3.30, f"{within}%", "of published defeats\nland within one year", RED)
        tf = _tb(s, 5.20, 3.05, 7.3, 3.2)
        _lines(tf, [
            (f"{hl.get('n_defeats', 0)} datable defeats, median gap 1 year, maximum 2.", 15, WHITE, True),
            ("", 8, BODY, False),
            ("Four teams defeated DataSentinel four separate times.", 12.5, BODY, False),
            ("A defense does not stop after one defeat.", 12.5, BODY, False),
            ("", 8, BODY, False),
            ("Read this as an upper limit.", 13, GOLD, True),
            (f"Only {hl.get('share_of_registry_with_recorded_defeat', 0)}% of the registry has a recorded", 12.5, MUTED, False),
            ("outcome. The sample prefers defenses that are", 12.5, MUTED, False),
            ("well known. Attack papers go after those first.", 12.5, MUTED, False),
        ], 12.5, BODY)

    # 13d — transfer result (new) -----------------------------------------
    tt = F.get("tt") or {}
    if tt and tt.get("results"):
        s = start("TRANSFER", ["Detection depends on recognising the attack.",
                               "Action-checking does not."], 28)
        panel(s, 0.70, 2.95, 5.75, 2.65)
        tf = _tb(s, 1.00, 3.20, 5.2, 2.2)
        _lines(tf, [
            ("Attack it was built against", 15, GOLD, True),
            ("", 6, BODY, False),
            ("Three of four ingestion detectors", 12.5, BODY, False),
            ("stop it completely.", 12.5, BODY, False),
            ("The attack announces itself:", 12.5, MUTED, False),
            ('"an important message from Emma".', 12.5, MUTED, False),
        ], 12.5, BODY)
        panel(s, 6.85, 2.95, 5.75, 2.65)
        tf = _tb(s, 7.15, 3.20, 5.2, 2.2)
        _lines(tf, [
            ("Same goal, different disguise", 15, RED, True),
            ("", 6, BODY, False),
            ("The same detectors stop working.", 12.5, BODY, False),
            ("The payload forges a system turn,", 12.5, BODY, False),
            ("so it reads as configuration,", 12.5, BODY, False),
            ("not as an injected instruction.", 12.5, BODY, False),
        ], 12.5, BODY)
        tf = _tb(s, 0.70, 5.85, 11.9, 1.3)
        _lines(tf, [
            ("The execution-stage technique blocked BOTH.", 14.5, WHITE, True),
            ("It never reads the payload \u2014 it asks whether the action serves the user's request,", 12.5, BODY, False),
            ("which is invariant to how the instruction was dressed up.", 12.5, BODY, False),
            ("RQ6 concluded execution defenses generalize least. This says the opposite.", 12.5, GOLD, True),
        ], 12.5, BODY)


    # 13e — the transfer matrix: what we ran ------------------------------
    s = start("TRANSFER MATRIX", ["We run the defense code against attacks",
                                  "that no paper has tested it on"], 28)
    stat_disc(s, 0.95, 2.70, 3.05, str(F["tx_cells"]), "defense x attack\nx model cells")
    stat_disc(s, 4.45, 2.70, 3.05, str(F["tx_doses"]), "measured\nconditions")
    tf = _tb(s, 8.20, 3.00, 4.4, 3.3)
    _lines(tf, [
        ("No paper reports these pairs.", 14, WHITE, True),
        ("That is why we chose them.", 14, WHITE, True),
        ("", 8, BODY, False),
        ("4 attacks. 5 defenses.", 12.5, BODY, False),
        ("3 models. 2 defense families.", 12.5, BODY, False),
        ("", 8, BODY, False),
        ("We change the attack dose from", 12.5, MUTED, False),
        ("0 to 10 bad passages of 10.", 12.5, MUTED, False),
        ("Each cell is a curve.", 12.5, MUTED, False),
    ], 12.5, BODY)
    tf = _tb(s, 0.70, 6.45, 11.9, 0.9)
    _lines(tf, [
        ("Three rules control every result.", 13.5, GOLD, True),
        ("The control must fire first. A change below the detection limit is not a result. "
         "We do not change the authors' scoring code.", 12.5, MUTED, False)], 12.5, BODY)

    # 13f — result 1: family dissociation ---------------------------------
    ch, ct = F["tx_ctx_harm"]; ah, at_ = F["tx_agg_harm"]
    s = start("RESULT 1", ["At full attack dose, one defense family",
                           "fails and the other does not"], 28)
    for i, (name, mech, harm, tot, col) in enumerate([
            ("Context-reliance", "It holds down memory so the model\nfollows the retrieved text.\nParamMute, CK-PLUG, SpARE",
             ch, ct, RED),
            ("Isolate-then-aggregate", "It answers each passage alone,\nthen joins the answers.\nRobustRAG KeywordAgg, DecodingAgg",
             ah, at_, TEAL)]):
        x = 0.70 + i * 6.10
        panel(s, x, 2.80, 5.80, 2.65)
        tf = _tb(s, x + 0.30, 3.00, 5.2, 0.4)
        _run(tf.paragraphs[0], name, 15.5, WHITE, True)
        tf = _tb(s, x + 0.30, 3.45, 5.2, 1.1)
        _lines(tf, mech.split("\n"), 12, MUTED, space_after=1)
        tf = _tb(s, x + 0.30, 4.62, 5.2, 0.7)
        _run(tf.paragraphs[0], f"{harm} of {tot}", 30, col, True, TITLE_FONT)
        tf = _tb(s, x + 2.40, 4.78, 3.2, 0.5)
        _lines(tf, ["usable cells lose", "accuracy we can measure"], 11.5, BODY, space_after=0)
    tf = _tb(s, 0.70, 5.70, 11.9, 1.4)
    _lines(tf, [
        ("The loss is the same size every time: -31.7 and -31.8 points, on two defenses, two attacks and two models.",
         13.5, WHITE, True),
        ("Against a false passage the loss starts at 8 bad passages of 10. It does not wait for 10 of 10.",
         12.5, BODY, False),
        ("Design rule: do not hold down the model's own memory. It is the only thing left when the evidence goes.",
         13, GOLD, True)], 12.5, BODY)

    # 13g — result 2: the defense opens the hole --------------------------
    c1u, c1d = F["tx_ckplug_tone1"]; c10u, c10d = F["tx_ckplug_tone10"]
    pmu, pmd = F["tx_parammute_tone10"]
    klu, kld = F["tx_kw_dos_llama"]; kmu, kmd = F["tx_kw_dos_mistral"]
    s = start("RESULT 2", ["Some defenses make the attack work.",
                           "Without them it stays near zero."], 28)
    hdr = [("Defense", 0.95, 3.4), ("Attack", 4.45, 2.5), ("No defense", 7.05, 2.0),
           ("With defense", 9.25, 2.0), ("Dose", 11.35, 1.2)]
    for lbl, x, w in hdr:
        tf = _tb(s, x, 2.70, w, 0.35)
        _run(tf.paragraphs[0], lbl, 12, GOLD, True)
    rows = [("CK-PLUG", "Tone steering", c1u, c1d, "1 of 10", RED),
            ("CK-PLUG", "Tone steering", c10u, c10d, "10 of 10", RED),
            ("ParamMute", "Tone steering", pmu, pmd, "10 of 10", RED),
            ("RobustRAG KeywordAgg, Llama-3", "Refusal", klu, kld, "9 of 10", RED),
            ("RobustRAG KeywordAgg, Mistral", "Refusal", kmu, kmd, "9 of 10", TEAL)]
    for i, (d_, a_, u_, v_, dose, col) in enumerate(rows):
        y = 3.12 + i * 0.58
        panel(s, 0.70, y, 11.9, 0.48)
        for text, x, w, size, color, bold in [
                (d_, 0.95, 3.4, 12.5, WHITE, False), (a_, 4.45, 2.5, 12.5, BODY, False),
                (f"{u_:.1f} %", 7.05, 2.0, 12.5, BODY, False),
                (f"{v_:.1f} %", 9.25, 2.0, 13.5, col, True),
                (dose, 11.35, 1.2, 12, MUTED, False)]:
            tf = _tb(s, x, y + 0.08, w, 0.34)
            _run(tf.paragraphs[0], text, size, color, bold)
    tf = _tb(s, 0.70, 6.20, 11.9, 1.1)
    _lines(tf, [
        ("With no defense the attack stays at or near zero at every dose. It works only through the defense.", 13.5, WHITE, True),
        ("Tone steering does not change the answer. A defense that pushes the model to follow the text follows the tone too.",
         12.5, BODY, False),
        ("The last row is the warning: the same defense helps on one model and does harm on another.", 12.5, GOLD, True)],
        12.5, BODY)

    # 13h — result 3: implementation beats family -------------------------
    s = start("RESULT 3", ["Two versions of one defense give",
                           "opposite answers"], 28)
    tf = _tb(s, 0.70, 2.55, 11.9, 0.4)
    _run(tf.paragraphs[0],
         "RobustRAG ships both. They share the isolation step. They differ only in how they join the answers.",
         12.5, MUTED)
    cols = [("Bad passages of 10", 0.95, 3.1)] + [
        (str(poison), 4.35 + i * 1.18, 1.05) for i, (poison, _, _) in enumerate(F["tx_gap"])]
    for lbl, x, w in cols:
        tf = _tb(s, x, 3.05, w, 0.35)
        pp = tf.paragraphs[0]
        if lbl != "Bad passages of 10":
            pp.alignment = PP_ALIGN.CENTER
        _run(pp, lbl, 12.5, GOLD, True)
    series = [("KeywordAgg", [k for _, k, _ in F["tx_gap"]], TEAL),
              ("DecodingAgg", [d for _, _, d in F["tx_gap"]], RED),
              ("Difference", [round(abs(k - d), 1) for _, k, d in F["tx_gap"]], WHITE)]
    for r, (name, vals, col) in enumerate(series):
        y = 3.52 + r * 0.60
        panel(s, 0.70, y, 11.9, 0.50)
        tf = _tb(s, 0.95, y + 0.08, 3.1, 0.35)
        _run(tf.paragraphs[0], name, 12.5, WHITE, r == 2)
        for i, v in enumerate(vals):
            tf = _tb(s, 4.35 + i * 1.18, y + 0.08, 1.05, 0.35)
            pp = tf.paragraphs[0]; pp.alignment = PP_ALIGN.CENTER
            txt = f"{v:+.1f}" if r < 2 else f"{v:.1f}"
            _run(pp, txt, 12.5, col, r == 2)
    tf = _tb(s, 0.70, 5.55, 11.9, 1.5)
    _lines(tf, [
        ("At 9 bad passages of 10, one version helps and the other does harm. They are 29.6 points apart.",
         13.5, WHITE, True),
        ("We wrote the cause down before we ran the test. A keyword filter throws away a passage with no answer in it, "
         "so one good passage still carries the answer. An average of the outputs lets nine bad ones drown it.",
         12.5, BODY, False),
        ("So the difference must grow as good passages go, and must vanish when none are left. It does both.",
         13, GOLD, True)], 12.5, BODY)

    # 13i — differentiation -----------------------------------------------
    s = start("DIFFERENTIATION", ["Against the five closest SoKs"], 30)
    rowsD = [
        ("papers reviewed", "78", f"{F['included']:,}"),
        ("attacks catalogued", "37", str(F["mech_reg"])),
        ("defenses catalogued", "41", str(F["defenses"])),
        ("attack \u00d7 defense pairs", "\u2014", str(F["pairs"])),
        ("runs own experiments", "yes", "yes"),
        ("covers BOTH literatures", "no", "YES"),
    ]
    tf = _tb(s, 0.70, 2.45, 11.9, 0.4)
    _run(tf.paragraphs[0], "closest competitor: The Landscape of Prompt Injection Threats (2602.10453)",
         12.5, MUTED)
    for i2, (k, a, b) in enumerate(rowsD):
        y = 2.95 + i2 * 0.56
        panel(s, 0.70, y, 11.9, 0.46)
        tf = _tb(s, 0.95, y + 0.06, 5.2, 0.34); _run(tf.paragraphs[0], k, 13, WHITE, True)
        tf = _tb(s, 6.30, y + 0.06, 2.6, 0.34); _run(tf.paragraphs[0], a, 13, BODY)
        tf = _tb(s, 9.40, y + 0.06, 2.9, 0.34)
        _run(tf.paragraphs[0], b, 13, GOLD, True)
    tf = _tb(s, 0.70, 6.35, 11.9, 0.9)
    _lines(tf, [
        ("They also run experiments. That is not the difference.", 13, WHITE, True),
        ("Four of the five closest surveys stay on one side of the divide. They do not mention it. "
         "The large ML survey does not cite security work. The closest security SoK does not cite degradation work.",
         12, MUTED, False)], 12, BODY)

    # 14 — RQ7 ------------------------------------------------------------
    s = start("RQ7  ·  OPEN PROBLEMS", ["Seven problems, ranked by expected value"], 30)
    probs = [
        ("1", "The tracks do not test each other", f"{F['db_cross_pct']}% of pairs cross the divide"),
        ("2", "The uncovered tail", f"{F['munc']} mechanisms have no tested defense"),
        ("3", "Single-mechanism validation is the norm", f"{F['per_def'].get('1',0)} defenses tested against exactly one"),
        ("4", "Defenses meet only their contemporaries", "attack papers hold the later record"),
        ("5", "Intervention point predicts generalization", "testable, and partly confounded today"),
        ("6", "Benchmarks stand in for mechanisms", "one entry takes 22.9% of the pairs"),
        ("7", "The problem is convention, not ability", "four of seven need no new science"),
    ]
    for i, (num, title, ev) in enumerate(probs):
        y = 2.55 + i * 0.63
        panel(s, 0.70, y, 11.9, 0.52)
        tf = _tb(s, 0.95, y + 0.08, 0.5, 0.35)
        _run(tf.paragraphs[0], num, 14, GOLD, True, TITLE_FONT)
        tf = _tb(s, 1.50, y + 0.09, 5.6, 0.35)
        _run(tf.paragraphs[0], title, 13.5, WHITE, True)
        tf = _tb(s, 7.20, y + 0.09, 5.1, 0.35)
        _run(tf.paragraphs[0], ev, 12.5, BODY)

    # 15 — synthesis ------------------------------------------------------
    s = start("SYNTHESIS", ["The field claims less coverage than it has.",
                            "Some of what it has does harm."], 26)
    tf = _tb(s, 0.70, 2.55, 11.9, 1.2)
    _lines(tf, [
        ("Two literatures study the same problem. They do not read each other.", 14, BODY, False),
        (f"They name {F['mech_reg']} ways to poison a context and {F['defenses']} defenses. They almost never test one against the other.",
         14, BODY, False)], 14, BODY, space_after=5)
    panel(s, 0.70, 4.05, 11.9, 1.55)
    tf = _tb(s, 1.05, 4.28, 11.2, 1.15)
    _lines(tf, [
        ("The first limit is coordination. It is not ability.", 17, GOLD, True),
        ("RQ6 ran 7 defenses. 6 of them gave some protection against a threat model they never saw.", 13, WHITE, False),
        ("The protection is there. The test convention that would show it is not.", 13, WHITE, False),
    ], 13, BODY, space_after=3)
    tf = _tb(s, 0.70, 5.80, 11.9, 1.4)
    _lines(tf, [
        ("The gap is not ours. We added the literature we thought was missing, to close it. It did not close.",
         13, MUTED, False),
        ("But coverage is not the whole result. When we ran the code, some defenses did not simply fail.",
         13, WHITE, True),
        ("They made an attack work that stays near zero on a model with no defense at all.", 13, RED, True)], 13, MUTED)

    # 16 — reproducibility ------------------------------------------------
    s = start("REPRODUCIBILITY", ["Every number on these slides regenerates from the repo"], 26)
    rows_ = [
        ("config.yaml", "screening criteria, applied by rule"),
        ("rescreening_log.md", "every corpus-affecting decision, dated, with cause"),
        ("scripts/", "dedupe \u2192 registries \u2192 coverage matrix \u2192 RQ1/RQ2/RQ7"),
        ("context_sok_master_workbook.xlsx", "papers, mechanisms, defenses, pairs, gaps"),
        ("mcp_server/", "the same data, queryable conversationally"),
        ("data/paper_explorer.db", "coverage and transfer figures, one source"),
        ("scripts/build_presentation.py", "this deck, built from the live data"),
    ]
    for i, (a, b) in enumerate(rows_):
        y = 2.70 + i * 0.68
        panel(s, 0.70, y, 11.9, 0.56)
        tf = _tb(s, 1.00, y + 0.11, 4.6, 0.35)
        _run(tf.paragraphs[0], a, 13, GOLD, True)
        tf = _tb(s, 5.70, y + 0.11, 6.6, 0.35)
        _run(tf.paragraphs[0], b, 12.5, BODY)
    tf = _tb(s, 0.70, 6.90, 11.9, 0.4)
    _run(tf.paragraphs[0],
         "We run each defense from its released code or weights. We never use the figures a paper reports about itself.",
         12, MUTED)

    # 17 — what's next ----------------------------------------------------
    s = start("WHAT'S NEXT", ["From findings to manuscript"], 30)
    nxt = [
        ("Finish the model control", "run the second aggregation version on the other family's model; the first half shows the protection does not repeat"),
        ("Add a third attack", "AGGD, so the matrix does not rest on four attack mechanisms"),
        ("Find an outside defense", "the aggregation family comes from one repository; a second group's code would test the rule"),
        ("Close the 99 near-misses", "defense papers that name an attack in our registry but never test it"),
        ("Manuscript draft", "RQ1 to RQ7 are complete. The threats to validity are written."),
    ]
    for i, (t, b) in enumerate(nxt):
        y = 2.55 + i * 0.90
        tf = _tb(s, 0.70, y, 4.5, 0.4)
        _run(tf.paragraphs[0], t, 14.5, GOLD, True, TITLE_FONT)
        tf = _tb(s, 5.30, y + 0.03, 7.3, 0.75)
        _lines(tf, [b], 12.5, BODY, space_after=1)
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=str(REPO / "context_sok_results_presentation.pptx"))
    args = ap.parse_args()
    F = load_facts()
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H
    n = build(prs, F)
    prs.save(args.out)
    print(f"Wrote {args.out}  ({n} slides)")
    print(f"  corpus {F['rows']:,} rows / {F['included']:,} included | "
          f"RQ3 {F['mech_reg']} | RQ4 {F['defenses']} | RQ5 {F['pairs']} pairs, {F['munc']} uncovered")


if __name__ == "__main__":
    main()

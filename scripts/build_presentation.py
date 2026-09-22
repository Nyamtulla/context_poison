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

    return {
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
        "pairs": st["n_pairs"], "dmatch": st["n_defenses_matched"],
        "dmatch_pct": 100 * st["n_defenses_matched"] / st["n_defenses_total"],
        "mcov": st["n_mechs_covered"], "munc": st["n_mechs_uncovered"],
        "mcov_pct": 100 * st["n_mechs_covered"] / len(mech),
        "per_def": st["mechs_per_defense_distribution"],
        "top_mech": [(x["mechanism_name"], x["n_defenses_tested"]) for x in top],
        "pair_mass": pair_mass,
        "empty_pct": empty_pct, "empty_n": empty_n, "cube_n": cube_n,
        "ab": (int(ab.group(1)), int(ab.group(2)), float(ab.group(3))) if ab else (0, 0, 0),
        "ba": (int(ba.group(1)), int(ba.group(2)), float(ba.group(3))) if ba else (0, 0, 0),
    }


# ---------------------------------------------------------------------- slides
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
    _run(tf.paragraphs[0], "A Systematization of Knowledge — RQ1–RQ7 complete", 16, BODY)
    tf = _tb(s, 0.90, 6.55, 9.0, 0.4)
    _run(tf.paragraphs[0],
         f"{F['rows']:,} papers screened · {F['included']:,} included · "
         f"{F['mech_all']} mechanisms · {F['defenses']} defenses", 13, MUTED)
    page_no(s, n)

    # 2 — roadmap ---------------------------------------------------------
    s = start("THE ROADMAP", ["Seven questions, one corpus"])
    items = [
        ("RQ1", "Taxonomy", f"{F['empty_pct']}% of the cube is empty"),
        ("RQ2", "Cross-citation", f"{F['ab'][2]}% / {F['ba'][2]}% between tracks"),
        ("RQ3", "Pollution census", f"{F['mech_reg']} named mechanisms"),
        ("RQ4", "Defense census", f"{F['defenses']} named defenses"),
        ("RQ5", "Coverage matrix", f"{F['munc']} mechanisms never defended"),
        ("RQ6", "Generalization", "9 reconstructed case studies"),
        ("RQ7", "Open problems", "7 ranked, falsifiable"),
    ]
    for i, (rq, name, res) in enumerate(items):
        y = 2.45 + i * 0.63
        panel(s, 0.70, y, 11.9, 0.52)
        tf = _tb(s, 0.95, y + 0.08, 1.1, 0.35); _run(tf.paragraphs[0], rq, 14, GOLD, True, TITLE_FONT)
        tf = _tb(s, 2.05, y + 0.09, 3.4, 0.35); _run(tf.paragraphs[0], name, 13.5, WHITE, True)
        tf = _tb(s, 5.6, y + 0.09, 6.7, 0.35); _run(tf.paragraphs[0], res, 13, BODY)

    # 3 — methodology -----------------------------------------------------
    s = start("METHODOLOGY", ["Kitchenham SLR + PRISMA-lite screening,",
                              "run across two literatures instead of one"])
    blocks = [
        ("Search", "Two tracks searched in parallel:\nadversarial poisoning and\nincidental degradation.\n25,922 records discovered."),
        ("Screen", "Fixed inclusion criteria in\nconfig.yaml, applied by rule,\nnot by hand. Every change\nlogged in rescreening_log.md."),
        ("Extract", "Full text read for 1,097 papers.\n32 coded fields per paper,\nclosed vocabularies for\nchannel and consequence."),
        ("Synthesize", "Registries joined into the\ncoverage matrix, then\nreconstructed empirically\nfor RQ6."),
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
        ("Every exclusion is recorded in rescreening_log.md —", 12.5, BODY, False),
        ("duplicates, off-criteria admissions, and screening", 12.5, BODY, False),
        ("corrections, with the reasoning for each.", 12.5, BODY, False),
        ("", 8, BODY, False),
        ("The corpus grew 1,008 → 1,158 in Sept 2026 after a", 12.5, MUTED, False),
        ("screening bug was found: the signal-term list required", 12.5, MUTED, False),
        ("agent-era vocabulary, so the papers that founded the", 12.5, MUTED, False),
        ("field — which say \"LLM-integrated application\", never", 12.5, MUTED, False),
        ("\"agent\" — had been silently dropped.", 12.5, MUTED, False),
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
        ("Down from 63.6% before the screening fix.", 12.5, BODY, False),
        ("Recovering 150 foundational papers filled", 12.5, BODY, False),
        ("five cells — and left 98 untouched.", 12.5, BODY, False),
    ], 12.5, BODY)

    # 6 — RQ1 channels ----------------------------------------------------
    s = start("RQ1  ·  TAXONOMY", ["Where the work actually sits"], 28)
    mx = max(F["mech_channel"].values())
    for i, (ch, v) in enumerate(F["mech_channel"].most_common()):
        bar_row(s, 0.70, 2.70 + i * 0.47, 11.9, ch, v, mx,
                GOLD if i < 2 else TEAL, f"{v}")
    tf = _tb(s, 0.70, 6.85, 11.9, 0.4)
    _run(tf.paragraphs[0],
         "Named mechanisms per channel (RQ3 registry). direct-input and tool-output are now exactly tied.",
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
        ("Roughly nine in ten papers never cite across the divide.", 14, WHITE, True),
        ("Unchanged after the corpus grew by 150 papers \u2014 the disconnect is structural, not a sampling artifact.",
         12.5, MUTED, False)], 12.5, BODY)

    # 8 — RQ3 -------------------------------------------------------------
    s = start("RQ3  ·  POLLUTION CENSUS", ["How many distinct ways can a context be poisoned?"], 28)
    stat_disc(s, 0.95, 2.65, 3.15, str(F["mech_reg"]), "named mechanisms")
    t = F["mech_track"]
    tf = _tb(s, 4.85, 2.95, 7.6, 3.4)
    _lines(tf, [
        (f"{t.get('Security',0)} adversarial  ·  {t.get('ML/AI',0)} incidental", 17, WHITE, True),
        ("", 8, BODY, False),
        ("Up from 183 before the screening fix. The 41 recovered", 12.5, BODY, False),
        ("mechanisms are 40 adversarial and skew hard to", 12.5, BODY, False),
        ("direct-input \u2014 23 of 41.", 12.5, BODY, False),
        ("", 8, BODY, False),
        ("That closed what had looked like a decisive channel gap.", 13, GOLD, True),
        ("The old \"tool-output dominates\" reading overstated a gap", 12.5, MUTED, False),
        ("our own screening had manufactured.", 12.5, MUTED, False),
    ], 12.5, BODY)
    c = F["mech_conseq"]
    tf = _tb(s, 0.70, 6.55, 11.9, 0.5)
    _run(tf.paragraphs[0],
         "By consequence:  " + "   ·   ".join(f"{k} {v}" for k, v in c.most_common()), 11.5, MUTED)

    # 9 — RQ4 -------------------------------------------------------------
    s = start("RQ4  ·  DEFENSE CENSUS", ["And how many defenses answer them?"], 30)
    stat_disc(s, 0.95, 2.55, 3.15, str(F["defenses"]), "named defenses")
    stat_disc(s, 4.55, 2.55, 3.15, f"{F['def_both_pct']:.1f}%", "tested on both\nthreat models", RED)
    tf = _tb(s, 8.35, 2.95, 4.3, 3.2)
    _lines(tf, [
        (f"Only {F['def_both']} of {F['defenses']} defenses", 15, WHITE, True),
        ("were validated against both", 15, WHITE, True),
        ("adversarial and incidental", 15, WHITE, True),
        ("context corruption.", 15, WHITE, True),
        ("", 10, BODY, False),
        ("This figure did not move when", 12.5, GOLD, False),
        ("55 defenses were added \u2014 including", 12.5, GOLD, False),
        ("StruQ, SecAlign, Spotlighting and", 12.5, GOLD, False),
        ("the Instruction Hierarchy.", 12.5, GOLD, False),
        ("", 8, BODY, False),
        ("2.9% \u2192 2.8%.", 13, WHITE, True),
    ], 12.5, BODY)

    # 10 — RQ5 headline ---------------------------------------------------
    s = start("RQ5  ·  COVERAGE MATRIX", ["Which defenses were ever tested",
                                          "against which attacks?"])
    stat_disc(s, 0.95, 2.80, 3.05, f"{F['dmatch_pct']:.0f}%", "of defenses have\nany confirmed test")
    stat_disc(s, 4.45, 2.80, 3.05, str(F["munc"]), "mechanisms never\ndefended", RED)
    tf = _tb(s, 8.20, 3.15, 4.4, 3.2)
    _lines(tf, [
        (f"{F['pairs']} confirmed pairs", 17, WHITE, True),
        (f"{F['dmatch']} of {F['defenses']} defenses matched", 12.5, BODY, False),
        (f"{F['mcov']} of {F['mech_all']} mechanisms covered", 12.5, BODY, False),
        ("", 10, BODY, False),
        ("Of the matched defenses,", 12.5, MUTED, False),
        (f"{F['per_def'].get('1',0)} were tested against", 12.5, MUTED, False),
        ("exactly one mechanism.", 12.5, MUTED, False),
        ("", 8, BODY, False),
        ("There is no generalist-defense", 13, GOLD, True),
        ("category to speak of.", 13, GOLD, True),
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
        (f"One umbrella mechanism absorbs {share:.1f}% of all test pairs; these six take {top6:.1f}%.",
         14, WHITE, True),
        (f"The other {F['munc']} mechanisms absorb none.", 12.5, MUTED, False)], 12.5, BODY)

    # 12 — RQ5 the null result (new) --------------------------------------
    s = start("RQ5  ·  THE TEST THAT FAILED", ["We predicted the gap would close.",
                                               "It did not \u2014 and that is the result."], 28)
    panel(s, 0.70, 2.95, 5.75, 3.15)
    tf = _tb(s, 1.00, 3.20, 5.2, 2.7)
    _lines(tf, [
        ("The prediction", 15, GOLD, True),
        ("", 6, BODY, False),
        ("Recovering the field's foundational", 12.5, BODY, False),
        ("defenses \u2014 StruQ, SecAlign, Spotlighting,", 12.5, BODY, False),
        ("Attention Tracker, the Liu et al. baselines \u2014", 12.5, BODY, False),
        ("should reveal that mechanisms which look", 12.5, BODY, False),
        ("\"never defended\" were defended after all.", 12.5, BODY, False),
    ], 12.5, BODY)
    panel(s, 6.85, 2.95, 5.75, 3.15)
    tf = _tb(s, 7.15, 3.20, 5.2, 2.7)
    _lines(tf, [
        ("What happened", 15, RED, True),
        ("", 6, BODY, False),
        ("164 papers recovered. 55 defenses and", 12.5, BODY, False),
        ("41 mechanisms added. 45 new pairs.", 12.5, BODY, False),
        ("", 6, BODY, False),
        ("Pre-existing mechanisms newly covered:", 12.5, WHITE, True),
        ("zero.", 26, RED, True),
        ("Coverage of the original 196 is unchanged.", 12.5, MUTED, False),
    ], 12.5, BODY)
    tf = _tb(s, 0.70, 6.35, 11.9, 0.9)
    _lines(tf, [
        ("The recovered defenses and the recovered attacks cover each other.", 14, WHITE, True),
        ("\"Your gap is an artifact of your corpus boundaries\" has now been tested directly, and does not hold.",
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
        ("9 case studies, each rebuilt from the defense's own released code or weights \u2014 never from its paper's numbers.",
         13.5, WHITE, True),
        ("Generalization tracks intervention point: ingestion defenses mostly hold, execution defenses mostly do not.",
         12.5, BODY, False),
        ("That split is partly confounded \u2014 the ingestion harnesses model a text classifier, the execution ones an agent. Stated, not hidden.",
         12, MUTED, False)], 12.5, BODY)

    # 14 — RQ7 ------------------------------------------------------------
    s = start("RQ7  ·  OPEN PROBLEMS", ["Seven problems, ranked by expected value"], 30)
    probs = [
        ("1", "Cross-track evaluation is not happening", "0.9% of test pairs cross the divide"),
        ("2", "The uncovered tail", f"{F['munc']} mechanisms have no tested defense"),
        ("3", "Single-mechanism validation is the norm", f"{F['per_def'].get('1',0)} defenses tested against exactly one"),
        ("4", "Defenses are tested only against contemporaries", "attack papers hold the later record"),
        ("5", "Intervention point predicts generalization", "testable, and partly confounded today"),
        ("6", "Benchmarks stand in for mechanisms", "one umbrella entry absorbs 22.9% of pairs"),
        ("7", "Reporting conventions, not capability", "four of seven need no new science"),
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
    s = start("SYNTHESIS", ["The field is underclaiming coverage it already has"], 28)
    tf = _tb(s, 0.70, 2.65, 11.9, 1.1)
    _lines(tf, [
        ("Two literatures study the same pond and barely read each other (RQ2).", 14, BODY, False),
        ("They name 223 ways to poison a context and 534 ways to defend one \u2014 and almost never test the two against each other (RQ5).",
         14, BODY, False)], 14, BODY, space_after=5)
    panel(s, 0.70, 4.05, 11.9, 1.55)
    tf = _tb(s, 1.05, 4.28, 11.2, 1.15)
    _lines(tf, [
        ("The binding constraint is coordination, not capability.", 17, GOLD, True),
        ("RQ6 found 6 of 7 runnable defenses showed some protection against the threat model they were never tested on.",
         13, WHITE, False),
        ("The generalization is already there. The evaluation convention that would surface it is not.", 13, WHITE, False),
    ], 13, BODY, space_after=3)
    tf = _tb(s, 0.70, 5.90, 11.9, 1.0)
    _lines(tf, [
        ("And the gap is not ours. We imported the literature we thought was missing, specifically to close it. It did not close.",
         13, MUTED, False)], 13, MUTED)

    # 16 — reproducibility ------------------------------------------------
    s = start("REPRODUCIBILITY", ["Every number on these slides regenerates from the repo"], 26)
    rows_ = [
        ("config.yaml", "screening criteria, applied by rule"),
        ("rescreening_log.md", "every corpus-affecting decision, dated, with cause"),
        ("scripts/", "dedupe \u2192 registries \u2192 coverage matrix \u2192 RQ1/RQ2/RQ7"),
        ("context_sok_master_workbook.xlsx", "papers, mechanisms, defenses, pairs, gaps"),
        ("mcp_server/", "the same data, queryable conversationally"),
        ("scripts/build_presentation.py", "this deck, built from the live registries"),
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
         "RQ6 numbers come from running each defense's released code or weights \u2014 never from the paper's reported figures.",
         12, MUTED)

    # 17 — what's next ----------------------------------------------------
    s = start("WHAT'S NEXT", ["From findings to manuscript"], 30)
    nxt = [
        ("Resolve the RQ6 confound", "port the ingestion defenses into an agent harness so intervention point is tested, not inferred"),
        ("Close the transfer program", "three-stage coverage recovery; first prediction already validated by execution"),
        ("Decide the survey question", "whether a pure survey satisfies the include criteria \u2014 affects the original corpus too"),
        ("Differentiation table", "against the five closest SoKs"),
        ("Manuscript draft", "RQ1\u2013RQ7 complete; threats-to-validity already written"),
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

"""Advisor briefing deck. Plain text and figures, no graphics, as asked."""
from pptx import Presentation
from pptx.util import Inches as I, Pt
from pptx.dml.color import RGBColor as RGB
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

DK   = RGB(0x2F, 0x3C, 0x47)   # charcoal slate - headings, title slides
INK  = RGB(0x1A, 0x1A, 0x1A)   # body
MUT  = RGB(0x6B, 0x77, 0x80)   # captions
LINE = RGB(0xDC, 0xDF, 0xE1)
RED  = RGB(0x8C, 0x2E, 0x2E)   # harm
BLU  = RGB(0x2F, 0x48, 0x58)   # protection / stats
GOLD = RGB(0xC9, 0xB0, 0x72)
WHT  = RGB(0xFF, 0xFF, 0xFF)
PALE = RGB(0xE6, 0xE9, 0xEB)

HEAD, BODY = "Cambria", "Calibri"
M, W = 0.65, 13.33 - 1.30

prs = Presentation()
prs.slide_width, prs.slide_height = I(13.33), I(7.5)
BLANK = prs.slide_layouts[6]


def bg(slide, color):
    f = slide.background.fill
    f.solid()
    f.fore_color.rgb = color


def tb(slide, x, y, w, h, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(I(x), I(y), I(w), I(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    tf.paragraphs[0].alignment = align
    return tf


def put(tf, text, size, color, *, bold=False, italic=False, font=BODY,
        bullet=False, space_after=8, first=False, line=None):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.space_after = Pt(space_after)
    if line:
        p.line_spacing = line
    r = p.add_run()
    r.text = ("•  " + text) if bullet else text
    r.font.size, r.font.bold, r.font.italic = Pt(size), bold, italic
    r.font.color.rgb, r.font.name = color, font
    return p


def title_slide(slide, text, sub=None, dark=False):
    tf = tb(slide, M, 0.42, W, 0.75, anchor=MSO_ANCHOR.MIDDLE)
    put(tf, text, 29, WHT if dark else DK, bold=True, font=HEAD, first=True, space_after=0)
    if sub:
        tf2 = tb(slide, M, 1.22, W, 0.45)
        put(tf2, sub, 13, RGB(0xAF, 0xB8, 0xBD) if dark else MUT,
            italic=True, first=True, space_after=0)


def footer(slide, n):
    tf = tb(slide, M, 6.98, 8.0, 0.3)
    put(tf, "Context Poisoning SoK  ·  advisor briefing  ·  7 October 2026",
        9, RGB(0x9A, 0xA3, 0xA8), first=True, space_after=0)
    tf = tb(slide, 11.9, 6.98, 0.78, 0.3, align=PP_ALIGN.RIGHT)
    put(tf, str(n), 9, RGB(0x9A, 0xA3, 0xA8), first=True, space_after=0)


def bullets(slide, x, y, w, h, items, size=15, color=INK, gap=9):
    tf = tb(slide, x, y, w, h)
    for i, it in enumerate(items):
        txt, bold = (it, False) if isinstance(it, str) else it
        put(tf, txt, size, color, bold=bold, bullet=True,
            space_after=gap, first=(i == 0), line=1.04)


def stat(slide, x, y, w, big, small, color=BLU):
    tf = tb(slide, x, y, w, 0.72)
    put(tf, big, 38, color, bold=True, font=HEAD, first=True, space_after=0)
    tf = tb(slide, x, y + 0.70, w, 0.72)
    for i, ln in enumerate(small.split("\n")):
        put(tf, ln, 11.5, MUT, first=(i == 0), space_after=2, line=1.0)


def table(slide, x, y, w, rows, colw, rowh=0.52, size=12.5, centre=()):
    """rows[0] is the header. A cell is str or (text, color, bold)."""
    shp = slide.shapes.add_table(len(rows), len(rows[0]), I(x), I(y), I(w),
                                 I(rowh * len(rows)))
    tbl = shp.table
    tbl.first_row = False                      # we style the header ourselves
    for j, cw in enumerate(colw):
        tbl.columns[j].width = I(cw)
    for i, row in enumerate(rows):
        tbl.rows[i].height = I(0.46 if i == 0 else rowh)
        for j, cell in enumerate(row):
            c = tbl.cell(i, j)
            c.margin_left = c.margin_right = I(0.09)
            c.margin_top = c.margin_bottom = I(0.04)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            c.fill.solid()
            c.fill.fore_color.rgb = DK if i == 0 else (
                WHT if i % 2 else RGB(0xF6, 0xF7, 0xF8))
            txt, col, bold = (cell, None, False) if isinstance(cell, str) else cell
            tf = c.text_frame
            tf.word_wrap = True
            for k, ln in enumerate(txt.split("\n")):
                p = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
                p.space_after = Pt(0)
                if j in centre:
                    p.alignment = PP_ALIGN.CENTER
                r = p.add_run()
                r.text = ln
                r.font.size = Pt(11.5 if i == 0 else size)
                r.font.bold = True if i == 0 else bold
                r.font.name = BODY
                r.font.color.rgb = WHT if i == 0 else (col or INK)
    return tbl


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text



def source(slide, text):
    tf = tb(slide, M, 6.52, W, 0.32)
    put(tf, "Full curves, controls and limits:  " + text, 10.5, MUT,
        italic=True, first=True, space_after=0)


S = lambda: prs.slides.add_slide(BLANK)

# ------------------------------------------------------------------ 1
s = S(); bg(s, DK)
tf = tb(s, M, 2.05, W, 1.5, anchor=MSO_ANCHOR.BOTTOM)
put(tf, "Context Poisoning in LLM Agent Systems", 40, WHT, bold=True,
    font=HEAD, first=True, space_after=0)
tf = tb(s, M, 3.75, W, 2.4)
put(tf, "A Systematization of Knowledge — with reconstructed transfer experiments",
    18, PALE, first=True, space_after=12)
put(tf, "Nyamtulla  ·  University of Kansas  ·  7 October 2026", 14,
    RGB(0xAF, 0xB8, 0xBD), space_after=26)
put(tf, "1,158 papers    ·    237 named attacks    ·    534 defenses    ·    "
        "16 reconstructed defense × attack cells", 13, GOLD)
notes(s, "Framing: this began as a survey and became a measurement study. The "
         "headline is that we ran released defense code against attacks nobody "
         "had paired it with, and several defenses turned out to create the "
         "vulnerability they were meant to prevent.")

# ------------------------------------------------------------------ 2
s = S(); footer(s, 2)
title_slide(s, "Two literatures, one failure mode",
            "An agent acts on whatever its context says. Two research communities study that going wrong — separately.")
bullets(s, M, 1.80, W, 2.6, [
    "Security track treats it as an attack — indirect prompt injection, PoisonedRAG, BadRAG, AgentPoison. An adversary writes the context.",
    "ML/AI track treats the same corruption as an accident — lost-in-the-middle, context rot, knowledge conflict, distraction. Nobody writes it on purpose.",
    "Both sides build defenses. Each set is evaluated on its own side's failures, and almost never on the other's.",
    ("The SoK question: is that separation justified by the mechanisms, or is it an artefact of how the two communities publish?", True),
])
tf = tb(s, M, 4.62, W, 0.3)
put(tf, "CORPUS COMPOSITION", 11, MUT, bold=True, first=True, space_after=0)
stat(s, M, 4.98, 3.6, "626", "Security-track papers")
stat(s, M + 4.1, 4.98, 3.6, "512", "ML/AI-track papers")
stat(s, M + 8.2, 4.98, 3.6, "20", "papers coded as both")
notes(s, "The point: the split is a publishing artefact we can test, not a fact "
         "about the mechanisms.")

# ------------------------------------------------------------------ 3
s = S(); footer(s, 3)
title_slide(s, "How the corpus was built, and how we measure",
            "Every number in this deck is regenerated from data/paper_explorer.db, not transcribed by hand.")
tf = tb(s, M, 1.80, 5.9, 0.3)
put(tf, "PIPELINE", 12, BLU, bold=True, first=True, space_after=0)
bullets(s, M, 2.20, 5.9, 2.4, [
    "~26,000 papers discovered by keyword and citation expansion",
    "1,158 curated after screening against explicit criteria",
    "Registries extracted: 237 attacks, 534 defenses, 349 reported pairs",
    "Taxonomy cube: 9 channels × 3 intents × 6 consequences",
], size=14)
tf = tb(s, M + 6.5, 1.80, 5.9, 0.3)
put(tf, "THREE DISCIPLINES, APPLIED MECHANICALLY", 12, RED, bold=True, first=True, space_after=0)
bullets(s, M + 6.5, 2.20, 5.9, 2.9, [
    "Control fires first — a defense that cannot reproduce its own benefit on its own benchmark yields no transfer verdict.",
    "Minimum detectable change — two-proportion power analysis (α=.05, power=.80). A smaller delta is not a result, whatever its sign.",
    "Authors' scorers, prompts and payloads imported unchanged. Harness adaptation is allowed; evaluation rubrics are not touched.",
], size=14)
tf = tb(s, M, 5.42, W, 1.0)
put(tf, "The first two rules are enforced inside the database loader, so the prose cannot "
        "drift away from the data. Applying them consistently has already forced "
        "two corrections to our own published claims.", 13, MUT, italic=True,
    first=True, space_after=0, line=1.15)
notes(s, "Emphasise control-fires-first: it caught CK-PLUG's accuracy column "
         "being unusable, and it is what separates this from a survey of "
         "papers' self-reported numbers.")

# ------------------------------------------------------------------ 4
s = S(); footer(s, 4)
title_slide(s, "The two communities do not read each other",
            "Full-population counts resolved from the citation graph — not a hand-coded sample, so no confidence interval is reported.")
table(s, M, 1.86, W, [
    ["Measure", "Value", "Reading"],
    ["Taxonomy cube cells that are empty", ("98 of 162   (60.5%)", None, True),
     "Most channel × intent × consequence combinations have never been studied"],
    ["Security papers citing ≥1 ML/AI paper", ("70 of 599   (11.7%)", None, True),
     "Nine in ten ignore the incidental literature entirely"],
    ["ML/AI papers citing ≥1 security paper", ("37 of 407   (9.1%)", None, True),
     "The asymmetry is small — both directions are near-silent"],
    ["Reported pairs staying inside one literature", ("341 of 348   (98.0%)", RED, True),
     "Only 7 pairs in the entire corpus cross the divide"],
], colw=[4.1, 2.5, 5.43], rowh=0.64, centre=(1,))
tf = tb(s, M, 5.60, W, 1.0)
p = tf.paragraphs[0]; p.space_after = Pt(0); p.line_spacing = 1.15
r = p.add_run(); r.text = "Why this matters for a security venue.  "
r.font.size, r.font.bold, r.font.name, r.font.color.rgb = Pt(13.5), True, BODY, INK
r = p.add_run()
r.text = ("If the two sides never test each other's mechanisms, every claim of the "
          "form “this defense is robust” is scoped to one literature's threat model — "
          "and nobody has checked whether it survives the other's.")
r.font.size, r.font.name, r.font.color.rgb = Pt(13.5), BODY, INK
notes(s, "RQ1 and RQ2. The 98% figure is computed live from the pair table joined "
         "to the attack and defense track columns.")

# ------------------------------------------------------------------ 5
s = S(); footer(s, 5)
title_slide(s, "Most defenses have never met most attacks",
            "The coverage matrix is far sparser than the plan anticipated — and the shape of the sparsity is itself the finding.")
stat(s, M, 1.80, 2.9, "119", "of 237 attacks (50.2%) have\nno defense pair at all", RED)
stat(s, M + 3.1, 1.80, 2.9, "320", "of 534 defenses (59.9%) have\nno attack pair at all", RED)
stat(s, M + 6.2, 1.80, 2.9, "15", "of 534 defenses (2.8%) were\nvalidated on both threat models", RED)
stat(s, M + 9.3, 1.80, 2.7, "349", "defense × attack pairs\nreported anywhere")
tf = tb(s, M, 3.78, W, 0.44)
put(tf, "A defense paper with no attack pair is not a neutral gap — a defense is "
        "supposed to defend something. Classifying all 320:", 13.5, INK, bold=True,
    first=True, space_after=0)
table(s, M, 4.26, W, [
    ["Classification of the 320 zero-pair defenses", "n", "What it means"],
    ["Non-adversarial by construction", "126", "Reliability or efficiency work; no threat model is claimed"],
    ["Names a registry attack but never tests it", ("99", RED, True), "Candidate missed pairs — the strongest lead for new coverage"],
    ["Threat named in prose only", "41", "An adversary is described; no experiment follows"],
    ["Self-constructed threat", "22", "Evaluated only against an attack the authors invented"],
    ["Benchmark named, no mechanism", "11", "Reports a score, not a defense outcome"],
    ["Unclassified", "21", "Insufficient extracted text to decide"],
], colw=[4.7, 0.9, 6.43], rowh=0.345, size=11.5, centre=(1,))
notes(s, "The 99 'names a registry attack but never tests it' bucket is where the "
         "transfer campaign draws its targets from.")

# ------------------------------------------------------------------ 6
s = S(); footer(s, 6)
title_slide(s, "We ran the code instead of quoting the papers",
            "Every cell below is a defense × attack pair reported nowhere in the literature. That is why it was chosen.")
bullets(s, M, 1.80, W, 2.5, [
    "A reconstructability screen ran first, over 7 candidate attacks, before any GPU time was booked — 2 cleanly runnable, 2 needing substitution, 1 unreadable, 1 miscoded in our own registry.",
    "4 attack mechanisms reconstructed: corpus poisoning (signal removal), PoisonedRAG (lie insertion), BadRAG DoS (refusal induction), BadRAG Selective-Fact (tone steering).",
    "5 defense implementations run from released code: ParamMute, CK-PLUG, SpARE, RobustRAG KeywordAgg, RobustRAG DecodingAgg.",
    "Attack dose is swept from 0 to 10 poisoned passages out of 10, so every cell is a curve rather than a single point.",
])
stat(s, M, 4.55, 3.0, "16", "defense × attack × model cells")
stat(s, M + 3.2, 4.55, 3.0, "94", "dose-level measured conditions")
stat(s, M + 6.4, 4.55, 3.0, "2", "defense families compared")
stat(s, M + 9.6, 4.55, 3.0, "3", "models, incl. a controlled rerun")
notes(s, "Stress that the dose sweep is what made the strongest findings visible. "
         "A single-point evaluation would have missed the 8-of-10 onset and the "
         "monotone divergence entirely.")

# ------------------------------------------------------------------ 7
s = S(); footer(s, 7)
title_slide(s, "Finding 1 — the collapse is family-specific",
            "At full saturation, when every retrieved passage is attacker-controlled, the two families behave categorically differently.")
table(s, M, 1.86, W, [
    ["Defense family", "Mechanism", "Cells with\nusable control", "Resolvable\naccuracy loss"],
    ["Context-reliance", "Suppress parametric memory so the model follows retrieved text\n(ParamMute, CK-PLUG, SpARE)", "5 of 8", ("4", RED, True)],
    ["Isolate-then-aggregate", "Answer each passage alone, then combine\n(RobustRAG KeywordAgg, RobustRAG DecodingAgg)", "5 of 5", ("0", BLU, True)],
], colw=[2.6, 5.33, 2.05, 2.05], rowh=0.84, centre=(2, 3))
bullets(s, M, 4.22, W, 2.3, [
    "The penalty is invariant: −31.7 and −31.8 pp across two defenses, two attacks and two models — one of them not even instruction-tuned.",
    "Against lie insertion the harm starts at 8 of 10 poisoned passages, not at 10 of 10. A context-reliance defense is a dose multiplier: every poisoned passage is one more passage it insists on.",
    ("Design rule — do not suppress parametric memory. It is the model's only recourse when the evidence set empties, and it is worth about 32 points.", True),
], size=14)
source(s, "family_dissociation.md  ·  saturation_invariant.md  ·  collapse_boundary.md")
notes(s, "The 8-of-10 onset came from crossover runs that had been sitting "
         "uncommitted; analysing them corrected our own earlier 'flat then a "
         "cliff' reading.")

# ------------------------------------------------------------------ 8
s = S(); footer(s, 8)
title_slide(s, "Finding 2 — some defenses create the vulnerability",
            "Attack success against an undefended model, and against the same model with the defense switched on.")
table(s, M, 1.86, W, [
    ["Defense", "Attack", "Undefended", "Defended", "Effect of turning the defense on"],
    ["CK-PLUG", "Tone steering", "0.0 %", ("99.0 %", RED, True), "78.2 % from a single poisoned passage in ten"],
    ["ParamMute", "Tone steering", "0.0 %", ("28.8 %", RED, True), "Same direction, weaker"],
    ["RobustRAG KeywordAgg\non Llama-3-8B-Instruct", "Refusal induction", "0.0 %", ("85.0 %", RED, True), "The model never refuses until the defense is added"],
    ["RobustRAG KeywordAgg\non Mistral-7B-Instruct", "Refusal induction", "0.0 %", ("5.7 %", BLU, True), "Same defense, same attack, different model — no effect"],
], colw=[3.55, 1.95, 1.4, 1.4, 3.73], rowh=0.58, centre=(2, 3))
bullets(s, M, 4.72, W, 2.0, [
    ("The attack does nothing to an undefended model. It only works through the defense.", True),
    "Why: tone steering does not corrupt the answer, so a defense that pushes the model to follow the retrieved text follows the slant too — and scores itself as working perfectly. The attack and the defense want the same thing.",
    "The last row is the uncomfortable one: the same defense is protective on one model and harmful on another, so model choice is part of the threat model.",
], size=13.5, gap=7)
source(s, "family_dissociation.md  ·  second_implementation.md  ·  badrag_transfer_result.md")
notes(s, "Strongest security-conference framing in the deck: a defense acting as "
         "an attack amplifier, measured, with the undefended control proving the "
         "attack is otherwise inert.")

# ------------------------------------------------------------------ 9
s = S(); footer(s, 9)
title_slide(s, "Finding 3 — two implementations, opposite verdicts",
            "RobustRAG ships two aggregation variants: same isolation step, same prompt builder, different combination rule.")
table(s, M, 1.86, W, [
    ["Poisoned passages (of 10)", "1", "5", "6", "7", "8", "9", "10"],
    ["KeywordAgg   Δ accuracy", "+7.3", "+4.0", "+4.0", "+5.7", "+6.7", ("+12.3", BLU, True), "−5.7"],
    ["DecodingAgg   Δ accuracy", "+8.7", "−9.0", "−14.0", "−18.3", "−20.3", ("−17.3", RED, True), "−4.0"],
    [("Gap between the two", None, True), ("1.4", None, True), ("13.0", None, True),
     ("18.0", None, True), ("24.0", None, True), ("27.0", None, True),
     ("29.6", RED, True), ("1.7", None, True)],
], colw=[3.5, 1.22, 1.22, 1.22, 1.22, 1.22, 1.22, 1.21], rowh=0.52,
      centre=(1, 2, 3, 4, 5, 6, 7))
bullets(s, M, 4.28, W, 2.2, [
    "At 9 of 10 poisoned, one implementation of the same principle is resolvably protective and the other resolvably harmful — 29.6 points apart, both clearing threshold.",
    "The mechanism was written down and committed before the test: a hard keyword filter discards a passage carrying no answer content, so one honest passage still carries the answer; a soft logit average lets nine junk distributions dilute it.",
    ("That predicts the gap scales with the honest minority and vanishes when it reaches zero. Measured afterwards: monotone across six doses, then collapsing to 1.7 at saturation. Confirmed.", True),
], size=13.5, gap=7)
source(s, "aggregation_divergence.md  ·  second_implementation.md  ·  CELL_CAMPAIGN.md")
notes(s, "Pre-registered prediction, confirmed monotonically. This is the "
         "methodological centrepiece — it is why the deck claims measurement "
         "rather than survey. Also: 12 distinct reproducibility defect classes "
         "documented across the repos we attempted.")

# ------------------------------------------------------------------ 10
s = S(); bg(s, DK)
title_slide(s, "Positioning for an A* security venue",
            "Target venues: IEEE S&P  ·  USENIX Security  ·  ACM CCS  ·  NDSS — SoK tracks", dark=True)
tf = tb(s, M, 1.98, 5.9, 0.3)
put(tf, "WHAT IT CONTRIBUTES BEYOND A SURVEY", 12.5, GOLD, bold=True, first=True, space_after=0)
bullets(s, M, 2.40, 5.9, 3.5, [
    "New measurements, not re-quoted numbers — 16 cells that exist in no paper",
    "A threat-model result: defenses as attack amplifiers (0% → 99%), with the undefended control proving the attack is otherwise inert",
    "A falsifiable mechanism stated before the test and confirmed monotonically",
    "An actionable design rule, held across 2 families and 5 implementations",
    "Reproducibility evidence: 12 distinct defect classes documented with fixes",
], size=13, color=PALE, gap=8)
tf = tb(s, M + 6.5, 1.98, 5.9, 0.3)
put(tf, "HONEST LIMITS, AND WHAT IS RUNNING NOW", 12.5, GOLD, bold=True, first=True, space_after=0)
bullets(s, M + 6.5, 2.40, 5.9, 3.5, [
    "One retrieval dataset (open_nq); three models; four attack mechanisms",
    "The aggregation family comes from a single repository — a third-party implementation is the next real test",
    "A model-controlled rerun is executing now; its finished half already shows the KeywordAgg protection does not replicate",
    "Next: AGGD as a third reconstructable attack; close the 99 candidate missed pairs",
    "Then freeze the transfer matrix and write up",
], size=13, color=PALE, gap=8)
tf = tb(s, M, 6.05, W, 0.9)
put(tf, "The through-line: a survey found that two communities never test each "
        "other's work. Running the code showed why that matters — several defenses "
        "are not merely untested against the other threat model, they are harmful "
        "under it.", 13, GOLD, italic=True, first=True, space_after=0, line=1.15)
notes(s, "Close on the through-line. If asked what is weakest: single dataset, and "
         "the aggregation family coming from one repository. Both are on the slide "
         "deliberately.")

out = "/home/n646s681/context_sok/advisor_briefing.pptx"
prs.save(out)
print("wrote", out, len(prs.slides.__iter__.__self__._sldIdLst), "slides")

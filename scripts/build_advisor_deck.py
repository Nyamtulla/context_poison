"""A plain deck for a one-to-one meeting with the project advisor.

Separate from `build_presentation.py`, which stays as the full results deck.
This one answers a single question: is the research worth continuing?

So it carries the problem, the background with citations, what we found, and
what we measured ourselves. It does not carry how the corpus was built, what
the screening rules were, which file holds what, or anything the project got
wrong on the way and then fixed. Those belong in the full deck and in the
manuscript, not in a meeting about whether to go on.

    python3 scripts/build_advisor_deck.py [-o out.pptx]
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches as I, Pt
from pptx.dml.color import RGBColor as RGB
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

INK  = RGB(0x11, 0x11, 0x11)
MID  = RGB(0x44, 0x44, 0x44)
GREY = RGB(0x77, 0x77, 0x77)
FAINT = RGB(0x99, 0x99, 0x99)
HEAD, BODY = "Cambria", "Calibri"
M, W = 0.80, 13.33 - 1.60

prs = Presentation()
prs.slide_width, prs.slide_height = I(13.33), I(7.5)
BLANK = prs.slide_layouts[6]


def tb(sl, x, y, w, h, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    box = sl.shapes.add_textbox(I(x), I(y), I(w), I(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    tf.paragraphs[0].alignment = align
    return tf


def put(tf, text, size, color=INK, *, bold=False, italic=False, font=BODY,
        first=False, after=9, line=1.06):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.space_after, p.line_spacing = Pt(after), line
    r = p.add_run()
    r.text = text
    r.font.size, r.font.bold, r.font.italic = Pt(size), bold, italic
    r.font.color.rgb, r.font.name = color, font
    return p


def slide(eyebrow, title, sub=None):
    sl = prs.slides.add_slide(BLANK)
    if eyebrow:
        put(tb(sl, M, 0.52, W, 0.3), eyebrow.upper(), 10.5, GREY, bold=True,
            first=True, after=0)
    put(tb(sl, M, 0.92, W, 0.95), title, 28, INK, bold=True, font=HEAD,
        first=True, after=0, line=1.02)
    if sub:
        put(tb(sl, M, 1.92, W, 0.45), sub, 14, MID, first=True, after=0)
    return sl


def body(sl, items, y, size=15, w=None, x=None, gap=11):
    tf = tb(sl, x if x is not None else M, y, w or W, 7.0 - y)
    for i, it in enumerate(items):
        txt, bold = (it, False) if isinstance(it, str) else it
        put(tf, txt, size, INK if bold else MID, bold=bold, first=(i == 0),
            after=gap, line=1.1)
    return tf


def rows(sl, data, y, *, pitch=0.47, lw=2.9, size=13, right=None):
    """Plain two- or three-column text rows. No fills, no rules, no boxes."""
    for i, item in enumerate(data):
        name, meaning = item[0], item[1]
        yy = y + i * pitch
        put(tb(sl, M, yy, lw, 0.34), name, size, INK, bold=True, first=True, after=0)
        put(tb(sl, M + lw, yy, W - lw - (0.9 if right else 0), 0.34),
            meaning, size, MID, first=True, after=0)
        if right:
            put(tb(sl, M + W - 0.85, yy, 0.85, 0.34, align=PP_ALIGN.RIGHT),
                str(item[2]), size, INK, bold=True, first=True, after=0)


def short(c):
    """Author and venue only. Used where a slide needs many references at once
    and the arXiv ids would push the line off the foot of the page."""
    return c.split(", arXiv:")[0]


def cite(sl, *parts, y=7.00, size=8.5):
    tf = tb(sl, M, y, W - 0.75, 7.44 - y)
    put(tf, "   ·   ".join(parts), size, FAINT, first=True, after=0, line=1.15)


def page(sl, n):
    put(tb(sl, 12.25, 7.02, 0.5, 0.3, align=PP_ALIGN.RIGHT), str(n), 9, FAINT,
        first=True, after=0)


def facts():
    """Only the numbers this deck shows, read from the live database."""
    import sqlite3, importlib.util
    spec = importlib.util.spec_from_file_location(
        "bp", REPO / "scripts" / "build_presentation.py")
    bp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bp)
    C = bp.load_citations()

    con = sqlite3.connect(REPO / "data" / "paper_explorer.db")
    one = lambda q, *a: con.execute(q, a).fetchone()[0]
    n_atk = one("SELECT COUNT(*) FROM attack")
    covered = one("SELECT COUNT(DISTINCT attack_name) FROM pair")
    tracked = con.execute("""SELECT a.track, d.track FROM pair p
                             JOIN attack a ON a.name=p.attack_name
                             JOIN defense d ON d.name=p.defense_name""").fetchall()
    same = sum(1 for x, y in tracked if x == y)

    def fam(point):
        v = [r[0] for r in con.execute(
            """SELECT utility_verdict FROM our_run WHERE campaign='rag_transfer'
               AND n_poison=10 AND intervention_point=?""", (point,))]
        usable = [x for x in v if x != "control_failed"]
        return usable.count("harms_accuracy"), len(usable)

    def asr(defense, attack, poison, model=None):
        q = ("""SELECT undefended_asr, defended_asr FROM our_run
                WHERE campaign='rag_transfer' AND technique_name=? AND attack=?
                  AND n_poison=?""")
        a = [defense, attack, poison]
        if model:
            q += " AND model LIKE ?"; a.append(f"%{model}%")
        return con.execute(q, a).fetchone()

    def dacc(defense, poison):
        return round(con.execute(
            """SELECT defended_utility-undefended_utility FROM our_run
               WHERE campaign='rag_transfer' AND technique_name=? AND attack='badrag_dos'
                 AND n_poison=? AND model LIKE '%Mistral%'""",
            (defense, poison)).fetchone()[0], 1)

    f = {
        "C": C,
        "attacks": n_atk,
        "defenses": one("SELECT COUNT(*) FROM defense"),
        "pairs": one("SELECT COUNT(*) FROM pair"),
        "undefended": n_atk - covered,
        "same_pct": round(100 * same / len(tracked), 1),
        "papers": one("SELECT COUNT(*) FROM paper WHERE screening='Include'"),
        "cells": one("""SELECT COUNT(*) FROM (SELECT DISTINCT technique_name, attack, model
                        FROM our_run WHERE campaign='rag_transfer')"""),
        "doses": one("SELECT COUNT(*) FROM our_run WHERE campaign='rag_transfer'"),
        "ctx": fam("context-reliance"),
        "agg": fam("isolate-then-aggregate"),
        "ck1": asr("CK-PLUG", "badrag_sentiment", 1),
        "ck10": asr("CK-PLUG", "badrag_sentiment", 10),
        "pm10": asr("ParamMute", "badrag_sentiment", 10),
        "agg_dos": [(m, i, asr(f"RobustRAG / {i}", "badrag_dos", 9, m))
                    for m in ("Mistral", "Llama")
                    for i in ("KeywordAgg", "DecodingAgg")],
        "gap": [(p, dacc("RobustRAG / KeywordAgg", p),
                 dacc("RobustRAG / DecodingAgg", p)) for p in (1, 5, 6, 7, 8, 9, 10)],
        "chan": list(con.execute(
            "SELECT channel, COUNT(*) FROM attack GROUP BY 1 ORDER BY 2 DESC")),
        "cons": dict(con.execute(
            "SELECT consequence, COUNT(*) FROM attack GROUP BY 1")),
        "both_tm": one("SELECT COUNT(*) FROM defense WHERE validated_against='both'"),
    }
    con.close()
    return f


def build(F):
    C = F["C"]
    n = 0

    def S(eb, title, sub=None):
        nonlocal n
        n += 1
        sl = slide(eb, title, sub)
        page(sl, n)
        return sl

    # 1 ------------------------------------------------------------------
    sl = prs.slides.add_slide(BLANK)
    put(tb(sl, M, 2.35, W, 1.4), "Context Integrity in LLM Agents", 36, INK,
        bold=True, font=HEAD, first=True, after=14)
    put(tb(sl, M, 3.55, W, 0.9),
        "Two research communities study the same failure. Neither tests the other's work.\n"
        "We measured what that costs.", 16, MID, first=True, after=0, line=1.3)
    put(tb(sl, M, 5.90, W, 0.6), "Nyamtulla    ·    Advisor meeting    ·    7 October 2026",
        12.5, GREY, first=True, after=0)
    n += 1

    # 2 ------------------------------------------------------------------
    sl = S("The problem", "An agent believes everything in its context window")
    body(sl, [
        ("An LLM agent reads one block of text and then acts. We call this block the context window.", True),
        "The block holds the user's question. It also holds a page a tool returned, a document a "
        "search step found, and a note the agent stored last week.",
        ("The model cannot tell these apart. Everything in the block looks the same to it.", True),
        "So any text that reaches the block can change what the agent does. The text does not need "
        "to come from the user. It only needs to arrive.",
        "This is not about training data. It is about what enters the context while the agent runs.",
    ], 2.12)
    cite(sl, f"Text in the context acts on the agent: {C['greshake']}",
         f"Long context degrades how the model uses it: {C['liu_middle']}")

    # 3 ------------------------------------------------------------------
    sl = S("The split", "Two communities. One failure. No contact.")
    put(tb(sl, M, 2.10, 5.7, 0.35), "The security literature", 15, INK, bold=True, first=True, after=6)
    body(sl, [
        "It treats the text as an attack. Someone wrote it to take the agent over.",
        "Indirect prompt injection. Poisoned retrieval. Poisoned memory.",
    ], 2.50, size=14, w=5.5, gap=9)
    put(tb(sl, M + 6.4, 2.10, 5.7, 0.35), "The machine learning literature", 15, INK, bold=True, first=True, after=6)
    body(sl, [
        "It treats the same corruption as an accident. Nobody wrote it to cause harm.",
        "Lost in the middle. Distraction by irrelevant text. Knowledge conflict.",
    ], 2.50, size=14, w=5.5, x=M + 6.4, gap=9)
    body(sl, [
        ("Both build defenses. Each side tests its defenses on its own failures.", True),
        "A tool returns a page with a hidden order. A tool returns a page that is ten times too long. "
        "Both arrive through the same route. Both end in the same window. One has an author and one "
        "does not, and that is the only difference.",
        ("Our question: does that difference justify two separate sets of defenses?", True),
    ], 4.05)
    cite(sl, f"Security end: {C['greshake']}", f"ML end: {C['liu_middle']}; {C['shi']}",
         f"Knowledge conflict: {C['kc_survey']}")

    # 4 ------------------------------------------------------------------
    sl = S("The framework", "We describe every case with three questions")
    rows(sl, [
        ("Channel", "How did the text get in? Which route did it travel?"),
        ("Intent", "Did a person put it there on purpose, or not?"),
        ("Consequence", "What went wrong once the text was in the window?"),
    ], 2.20, pitch=0.60, lw=2.6, size=16)
    body(sl, [
        ("9 channels  ×  3 intents  ×  6 consequences  =  162 combinations.", True),
        "A combination with no paper in it is a question the field has never asked. "
        "We find that 98 of the 162 are empty.",
        "The framework is the spine of the work. It tells us what is known, and it tells us where "
        "to look next.",
    ], 4.30)
    cite(sl, "Framework: this work", f"Adversarial end: {C['greshake']}",
         f"Incidental end: {C['liu_middle']}")

    # 5 ------------------------------------------------------------------
    CH = dict(F["chan"])
    sl = S("Channel", "Nine routes carry text into the window")
    rows(sl, [
        ("tool-output", "What a tool gives back: a web page, an email, a file the agent opened.", CH.get("tool-output", 0)),
        ("direct-input", "The prompt itself. The user's text, or the system prompt above it.", CH.get("direct-input", 0)),
        ("RAG", "A document a search step pulled out of a corpus.", CH.get("RAG", 0)),
        ("cross-modal", "Text carried inside an image, audio or video.", CH.get("cross-modal", 0)),
        ("memory", "Something the agent stored earlier and now reads again.", CH.get("memory", 0)),
        ("tool-metadata", "The description of a tool, not its output.", CH.get("tool-metadata", 0)),
        ("multi-agent", "A message from another agent in the same system.", CH.get("multi-agent", 0)),
        ("supply-chain", "A package or template the agent inherits before it starts.", CH.get("supply-chain", 0)),
        ("skill", "A stored procedure the agent loads and follows.", CH.get("skill", 0)),
    ], 2.22, pitch=0.46, lw=2.5, size=13.5, right=True)
    put(tb(sl, M, 6.44, W, 0.35),
        "The right column counts the named attacks in that channel.", 12, GREY, first=True, after=0)
    tfc = tb(sl, M, 6.96, W - 0.75, 0.46)
    for i, line in enumerate([
            f"tool-output {short(C['greshake'])}  ·  direct-input {short(C['houyi'])}  ·  RAG {short(C['zou'])}  ·  memory {short(C['agentpoison'])}  ·  cross-modal {short(C['webinject'])}",
            f"tool-metadata {short(C['mcptox'])}  ·  multi-agent {short(C['infection'])}  ·  supply-chain {short(C['supplychain'])}  ·  skill {short(C['skillject'])}"]):
        put(tfc, line, 8, FAINT, first=(i == 0), after=0, line=1.2)

    # 6 ------------------------------------------------------------------
    CO = F["cons"]
    sl = S("Consequence", "Six ways the agent then fails")
    rows(sl, [
        ("goal-hijack", "The agent does another person's task. Text in the window gives an order and it obeys.", CO.get("goal-hijack", 0)),
        ("reasoning-corruption", "Every word is true. The window is too long or too cluttered, and the model stops using it well.", CO.get("reasoning-corruption", 0)),
        ("silent-corruption", "The agent answers from false content. Nobody gave it a new task. It believes a wrong thing.", CO.get("silent-corruption", 0)),
        ("persistence-backdoor", "The bad content is stored. It fires on a later run, maybe for another user.", CO.get("persistence-backdoor", 0)),
        ("data-exfiltration", "The agent sends out what it can read, through a tool call, a link or a message.", CO.get("data-exfiltration", 0)),
        ("resource-abuse", "No data moves and no goal changes. The agent burns time, or refuses to answer.", CO.get("resource-abuse", 0)),
    ], 2.22, pitch=0.62, lw=3.3, size=13.5, right=True)
    put(tb(sl, M, 6.22, W, 0.4),
        "The second row is the machine learning literature. The other five are the security literature. "
        "That is the split, in one column.", 12.5, MID, first=True, after=0)
    cite(sl, f"goal-hijack {short(C['greshake'])}",
         f"reasoning-corruption {short(C['liu_middle'])}; {short(C['shi'])}",
         f"silent-corruption {short(C['kconflict'])}",
         f"persistence-backdoor {short(C['agentpoison'])}",
         f"data-exfiltration {short(C['exfil'])}", f"resource-abuse {short(C['badrag'])}",
         y=6.96, size=8)

    # 7 ------------------------------------------------------------------
    sl = S("What we built", "A map of every attack and every defense in the field")
    rows(sl, [
        (f"{F['papers']:,} papers", "read in full and coded, drawn from about 26,000 candidates"),
        (f"{F['attacks']} attacks", "distinct named ways to corrupt a context window"),
        (f"{F['defenses']} defenses", "distinct named ways the field protects against them"),
        (f"{F['pairs']} pairs", "every case where a paper tested one defense against one attack"),
    ], 2.20, pitch=0.58, lw=2.9, size=15)
    body(sl, [
        ("No prior survey holds both literatures. The closest one reviews 78 papers, 37 attacks and 41 defenses, "
         "and stays on the security side.", True),
        "That map is the instrument. Everything that follows is read off it.",
    ], 4.70)
    cite(sl, f"Closest prior survey: {C['sok_landscape']}",
         f"Review protocol follows {C['slr_prisma']} and {C['slr_kitchenham']}")

    # 8 ------------------------------------------------------------------
    sl = S("Finding 1", "The two communities do not read each other")
    rows(sl, [
        ("11.7 %", "of security papers cite at least one machine learning paper"),
        ("9.1 %", "of machine learning papers cite at least one security paper"),
        (f"{F['same_pct']} %", "of all tested pairs stay inside one literature"),
        ("60.5 %", "of the 162 combinations in the framework have never been studied"),
    ], 2.20, pitch=0.60, lw=2.2, size=16)
    body(sl, [
        ("Nine of ten papers never cross. Seven pairs in the whole field do.", True),
        "This is not a sample. We resolved every citation edge in the corpus.",
        ("So every claim of the form “this defense is robust” holds inside one threat model. "
         "Nobody has checked the other one.", True),
    ], 4.75)

    # 9 ------------------------------------------------------------------
    sl = S("Finding 2", "Most defenses have never met most attacks")
    rows(sl, [
        (f"{F['undefended']} of {F['attacks']}", "attacks have no tested defense at all"),
        (f"{F['both_tm']} of {F['defenses']}", "defenses were tested against both threat models. That is 2.8 %."),
    ], 2.20, pitch=0.62, lw=2.9, size=16)
    body(sl, [
        ("A defense paper is not a neutral document. A defense is supposed to defend something.", True),
        "99 defense papers name an attack that sits in our map, and then never test against it. "
        "Those are not gaps in the field's knowledge. They are gaps in its evidence.",
        ("At this point the survey had taken us as far as a survey can go. It can show that a test "
         "was never run. It cannot say what the test would have found.", True),
    ], 3.95)

    # 10 -----------------------------------------------------------------
    sl = S("What we did next", "We ran the tests the field never ran")
    body(sl, [
        ("We took defenses with released code, and attacks with released code, and ran the pairs "
         "that no paper reports.", True),
        f"{F['cells']} defense and attack pairs. {F['doses']} measured conditions. Four attacks. Five defenses. Three models.",
        "We raise the attack dose from zero to ten poisoned passages out of ten, so each pair gives "
        "a curve and not a single point.",
    ], 2.15)
    put(tb(sl, M, 4.10, W, 0.35), "Two rules decide what we are allowed to claim.", 15, INK, bold=True, first=True, after=10)
    rows(sl, [
        ("The control first", "A defense must show its own benefit on its own task before we read anything else from it."),
        ("A size floor", "We fix the smallest change the sample can detect. Below that we report nothing, in either direction."),
    ], 4.52, pitch=0.70, lw=2.9, size=14)
    put(tb(sl, M, 6.05, W, 0.4),
        "Scoring comes from each paper's own code, unchanged.", 13, MID, first=True, after=0)
    cite(sl, f"PoisonedRAG {short(C['zou'])}", f"BadRAG {short(C['badrag'])}",
         f"RobustRAG {short(C['robustrag'])}", f"ParamMute {short(C['parammute'])}")

    # 11 -----------------------------------------------------------------
    ch_h, ch_t = F["ctx"]; ag_h, ag_t = F["agg"]
    sl = S("Result 1", "One family of defenses fails under pressure. The other does not.")
    put(tb(sl, M, 2.45, W, 0.4),
        "When every retrieved passage belongs to the attacker:", 14.5, MID, first=True, after=0)
    rows(sl, [
        ("Context-reliance", "It holds down the model's own memory so the model follows the retrieved text.", f"{ch_h} of {ch_t}"),
        ("Isolate-then-aggregate", "It answers from each passage alone, then joins the answers.", f"{ag_h} of {ag_t}"),
    ], 2.95, pitch=0.72, lw=3.5, size=15, right=True)
    put(tb(sl, M + W - 3.4, 4.45, 3.4, 0.3), "readable cases that lose accuracy", 11.5, GREY, first=True, after=0)
    body(sl, [
        ("The loss is the same size every time: about 32 points, on two defenses, two attacks and two models.", True),
        "Against a false passage the loss begins at eight poisoned passages of ten. It does not wait for all ten.",
        ("The design rule that follows: do not suppress the model's own memory. It is the only thing "
         "left when the evidence runs out.", True),
    ], 4.95)
    cite(sl, f"ParamMute {short(C['parammute'])}", f"RobustRAG {short(C['robustrag'])}",
         f"PoisonedRAG {short(C['zou'])}", f"BadRAG {short(C['badrag'])}", "Measurements: this work")

    # 12 -----------------------------------------------------------------
    sl = S("Result 2", "Some defenses make an attack work that otherwise does nothing")
    ck1u, ck1d = F["ck1"]; ck10u, ck10d = F["ck10"]; pmu, pmd = F["pm10"]
    hdr = [("Defense", M, 3.2), ("Attack", M + 3.3, 2.6), ("No defense", M + 6.1, 1.8),
           ("With the defense", M + 8.1, 2.2), ("Poisoned", M + 10.5, 1.4)]
    for lbl, x, w in hdr:
        put(tb(sl, x, 2.30, w, 0.3), lbl, 11.5, GREY, bold=True, first=True, after=0)
    data = [("CK-PLUG", "tone steering", f"{ck1u:.1f} %", f"{ck1d:.1f} %", "1 of 10"),
            ("CK-PLUG", "tone steering", f"{ck10u:.1f} %", f"{ck10d:.1f} %", "10 of 10"),
            ("ParamMute", "tone steering", f"{pmu:.1f} %", f"{pmd:.1f} %", "10 of 10")]
    for i, r in enumerate(data):
        y = 2.68 + i * 0.52
        for txt, (lbl, x, w) in zip(r, hdr):
            bold = lbl == "With the defense"
            put(tb(sl, x, y, w, 0.34), txt, 13.5, INK if bold else MID,
                bold=bold, first=True, after=0)
    body(sl, [
        ("With no defense the attack stays at or near zero. It only works once the defense is switched on.", True),
        "One poisoned passage out of ten is enough. The undefended model ignores it completely.",
        "The reason is uncomfortable. Tone steering does not change the answer, so a defense that pushes "
        "the model to follow the retrieved text follows the slant as well, and scores itself as working "
        "perfectly. The attack and the defense want the same thing.",
        ("A defense can be the reason an attack succeeds. That is a security finding, not a performance note.", True),
    ], 4.50)
    cite(sl, f"BadRAG {short(C['badrag'])}", f"ParamMute {short(C['parammute'])}",
         "Measurements: this work")

    # 13 -----------------------------------------------------------------
    sl = S("Result 3", "One defense, two models, opposite results")
    put(tb(sl, M, 2.00, W, 0.4),
        "One defense family, two versions of it, two models. Nine poisoned passages of ten. "
        "The number is how often the agent refuses to answer.", 14, MID, first=True, after=0)
    hdr = [("Model", M, 3.6), ("Version of the defense", M + 3.7, 3.4),
           ("No defense", M + 7.3, 2.0), ("With the defense", M + 9.5, 2.3)]
    for lbl, x, w in hdr:
        put(tb(sl, x, 2.62, w, 0.3), lbl, 11.5, GREY, bold=True, first=True, after=0)
    for i, (m, impl, (u, d)) in enumerate(F["agg_dos"]):
        y = 3.00 + i * 0.50
        name = "Mistral-7B" if m == "Mistral" else "Llama-3-8B"
        for txt, (lbl, x, w) in zip((name, impl, f"{u:.1f} %", f"{d:.1f} %"), hdr):
            bold = lbl == "With the defense"
            put(tb(sl, x, y, w, 0.34), txt, 13.5, INK if bold else MID,
                bold=bold, first=True, after=0)
    body(sl, [
        ("The undefended model never refuses. Not once, on either model, at any dose.", True),
        "The cause is the defense's own design. It answers from each passage alone, so a passage that "
        "says \u201crefuse\u201d gets an unopposed hearing. The undefended model reads all ten passages "
        "together, where nine honest ones drown it out.",
        ("It is the same property that makes this family resist tone steering. One trade, not two "
         "results, and the model decides which way it falls.", True),
    ], 5.10, gap=9)
    cite(sl, f"RobustRAG, both versions {short(C['robustrag'])}", f"BadRAG {short(C['badrag'])}",
         "Measurements: this work")

    # 14 -----------------------------------------------------------------
    sl = S("Why this is worth finishing", "A survey found the gap. Running the code showed what is in it.")
    rows(sl, [
        ("It is new evidence", "16 defense and attack pairs that exist in no paper. The numbers are ours, not quoted."),
        ("It changes the threat model", "A defense can be the reason an attack works. That is a security claim, not a performance note."),
        ("It gives a design rule", "Do not suppress the model's own memory. Held across two families and five implementations."),
        ("It predicted and then held", "We stated the cause before the test. The measurement followed the predicted shape."),
    ], 2.20, pitch=0.70, lw=3.9, size=14.5)
    put(tb(sl, M, 5.25, W, 0.35), "What is left", 15, INK, bold=True, first=True, after=8)
    body(sl, [
        "Finish the model comparison, add a third attack, and find an aggregation defense from another group.",
        "Then the matrix is closed and the paper is written.",
    ], 5.61, size=14, gap=7)

    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=str(REPO / "advisor_meeting.pptx"))
    args = ap.parse_args()
    n = build(facts())
    prs.save(args.out)
    print(f"Wrote {args.out}  ({n} slides)")


if __name__ == "__main__":
    main()

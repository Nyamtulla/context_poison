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
from pptx.enum.shapes import MSO_SHAPE
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


def rule(sl, x, y, w, color=RGB(0xCC, 0xCC, 0xCC)):
    """A hairline. The only mark on this deck that is not a letter."""
    from pptx.util import Emu
    ln = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, I(x), I(y), I(w), Emu(9525))
    ln.fill.solid(); ln.fill.fore_color.rgb = color
    ln.line.fill.background(); ln.shadow.inherit = False
    return ln


def table(sl, headers, data, y, colw, *, x=None, size=13, pitch=0.44,
          align_right=()):
    """A real table: column headings, one hairline under them, plain rows.

    Replaces the old bold-label-then-sentence layout, which read as a list of
    captions rather than as data you can scan down a column.
    """
    x0 = M if x is None else x
    cx = [x0]
    for w in colw[:-1]:
        cx.append(cx[-1] + w)
    for j, h in enumerate(headers):
        a = PP_ALIGN.RIGHT if j in align_right else PP_ALIGN.LEFT
        wj = colw[j] - (0.28 if j in align_right else 0)
        put(tb(sl, cx[j], y, wj, 0.3, align=a), h.upper(), 10, GREY,
            bold=True, first=True, after=0)
    rule(sl, x0, y + 0.30, sum(colw))
    for i, row in enumerate(data):
        yy = y + 0.42 + i * pitch
        for j, cell in enumerate(row):
            txt, bold = (cell, False) if isinstance(cell, str) else cell
            a = PP_ALIGN.RIGHT if j in align_right else PP_ALIGN.LEFT
            wj = colw[j] - (0.28 if j in align_right else 0)
            put(tb(sl, cx[j], yy, wj, 0.34, align=a), txt, size,
                INK if bold else MID, bold=bold, first=True, after=0)
    return y + 0.42 + len(data) * pitch


def bullets(sl, items, y, *, x=None, w=None, size=14, gap=9, mark="\u2014  "):
    """A plain list. The dash keeps items separable without drawing anything."""
    tf = tb(sl, x if x is not None else M, y, w or W, 7.1 - y)
    for i, it in enumerate(items):
        txt, bold = (it, False) if isinstance(it, str) else it
        put(tf, mark + txt, size, INK if bold else MID, bold=bold,
            first=(i == 0), after=gap, line=1.12)
    return tf


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


def _verdicts(con):
    """One plain verdict per cell: did the defense stop the attack, or not?

    A cell counts as stopped if attack success falls by more than the run's
    detection limit at any dose, and as worse if it rises by more than that.
    Everything else is no readable effect. Worse is checked first, because a
    defense that helps at one dose and hurts at another is not a defense.
    """
    out = []
    for d, a, m in con.execute("""SELECT DISTINCT technique_name, attack, model
                                  FROM our_run WHERE campaign='rag_transfer'
                                  ORDER BY 1,2,3"""):
        rows = con.execute("""SELECT n_poison, drop_pp, mdr_pp, undefended_asr FROM our_run
                              WHERE campaign='rag_transfer' AND technique_name=?
                                AND attack=? AND model=?""", (d, a, m)).fetchall()
        worse = [r for r in rows if r[1] >= r[2]]
        better = [r for r in rows if r[1] <= -r[2]]
        # `inert` means the attack barely works without the defense, so the
        # defense is not making a bad situation worse - it is creating it
        inert = False
        if worse:
            v = "makes it worse"
            inert = max(worse, key=lambda r: r[1])[3] < 5
        elif better:
            v = "stops it"
        else:
            v = "no effect"
        out.append((d, a, m, v, inert))
    return out



CONSEQ = ["goal-hijack", "reasoning-corruption", "silent-corruption",
          "persistence-backdoor", "data-exfiltration", "resource-abuse"]
CONSEQ_SHORT = ["hijack", "reasoning", "silent", "backdoor", "exfil", "resource"]


def grid(con):
    """Attacks per channel x consequence, with whether any pair was ever tested.

    Returns [(channel, [(n_attacks, tested), ...])]. `tested` is False where
    the cell holds at least one attack and no defense has ever been run against
    any of them - which is the thing the slide is for.
    """
    out = []
    for (ch,) in con.execute("SELECT channel FROM attack GROUP BY 1 ORDER BY COUNT(*) DESC"):
        row = []
        for co in CONSEQ:
            na = con.execute("SELECT COUNT(*) FROM attack WHERE channel=? AND consequence=?",
                             (ch, co)).fetchone()[0]
            np_ = con.execute("""SELECT COUNT(*) FROM pair p JOIN attack a ON a.name=p.attack_name
                                 WHERE a.channel=? AND a.consequence=?""", (ch, co)).fetchone()[0]
            row.append((na, np_ > 0))
        out.append((ch, row))
    return out


def cell_detail(con, ch, co):
    q = lambda t, tr: con.execute(
        f"SELECT COUNT(*) FROM {t} WHERE channel=? AND consequence=? AND track=?",
        (ch, co, tr)).fetchone()[0]
    pairs = con.execute("""SELECT COUNT(*) FROM pair p
                           JOIN attack a ON a.name=p.attack_name
                           JOIN defense d ON d.name=p.defense_name
                           WHERE a.channel=? AND a.consequence=?
                             AND d.channel=? AND d.consequence=?""",
                        (ch, co, ch, co)).fetchone()[0]
    return {"channel": ch, "consequence": co,
            "atk_sec": q("attack", "Security"), "atk_ml": q("attack", "ML/AI"),
            "def_sec": q("defense", "Security"), "def_ml": q("defense", "ML/AI"),
            "pairs": pairs}


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
        # pinned: CK-PLUG was run on both models and an unpinned lookup would
        # return whichever row came back first
        "ck1": asr("CK-PLUG", "badrag_sentiment", 1, "Llama"),
        "ck10": asr("CK-PLUG", "badrag_sentiment", 10, "Llama"),
        "ck10_mistral": asr("CK-PLUG", "badrag_sentiment", 10, "Mistral"),
        "pm10": asr("ParamMute", "badrag_sentiment", 10, "Llama"),
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
        # the two sides name their objects differently, and the deck follows
        # them: attack / defense on the security side, incidental mechanism /
        # fix on the machine learning side
        "atk_sec": one("SELECT COUNT(*) FROM attack WHERE track='Security'"),
        "atk_ml": one("SELECT COUNT(*) FROM attack WHERE track='ML/AI'"),
        "def_sec": one("SELECT COUNT(*) FROM defense WHERE track='Security'"),
        "def_ml": one("SELECT COUNT(*) FROM defense WHERE track='ML/AI'"),
        "und_sec": one("""SELECT COUNT(*) FROM attack a WHERE a.track='Security'
                          AND NOT EXISTS (SELECT 1 FROM pair p WHERE p.attack_name=a.name)"""),
        "und_ml": one("""SELECT COUNT(*) FROM attack a WHERE a.track='ML/AI'
                         AND NOT EXISTS (SELECT 1 FROM pair p WHERE p.attack_name=a.name)"""),
        "unt_sec": one("""SELECT COUNT(*) FROM defense d WHERE d.track='Security'
                          AND NOT EXISTS (SELECT 1 FROM pair p WHERE p.defense_name=d.name)"""),
        "unt_ml": one("""SELECT COUNT(*) FROM defense d WHERE d.track='ML/AI'
                         AND NOT EXISTS (SELECT 1 FROM pair p WHERE p.defense_name=d.name)"""),
        # candidate pools: a cell where the security side has attacks and the
        # ML/AI side has defenses is a transfer test waiting to be run
        "pool_total": one("""
            WITH a AS (SELECT channel, consequence, COUNT(*) n FROM attack
                       WHERE track='Security' GROUP BY 1,2),
                 d AS (SELECT channel, consequence, COUNT(*) n FROM defense
                       WHERE track='ML/AI' GROUP BY 1,2)
            SELECT COUNT(*) FROM a JOIN d
              ON a.channel=d.channel AND a.consequence=d.consequence"""),
        "pool": con.execute("""
            WITH a AS (SELECT channel, consequence, COUNT(*) n FROM attack
                       WHERE track='Security' GROUP BY 1,2),
                 d AS (SELECT channel, consequence, COUNT(*) n FROM defense
                       WHERE track='ML/AI' GROUP BY 1,2)
            SELECT a.channel, a.consequence, a.n, d.n FROM a JOIN d
              ON a.channel=d.channel AND a.consequence=d.consequence
            ORDER BY a.n*d.n DESC LIMIT 7""").fetchall(),
        "pool_tested": None,   # filled below, once `pool` exists
        "verdicts": _verdicts(con),
    }
    # How many of each pool cell's pairs cross the divide, and how many pairs
    # that cell holds in total. The second number matters: a cell can be heavily
    # tested and still have nothing crossing, and the slide must not blur those.
    f["pool_tested"] = [
        (con.execute("""SELECT COUNT(*) FROM pair p
                        JOIN attack a ON a.name=p.attack_name
                        JOIN defense d ON d.name=p.defense_name
                        WHERE a.channel=? AND a.consequence=? AND d.channel=? AND d.consequence=?
                          AND a.track='Security' AND d.track='ML/AI'""", (ch, co, ch, co)).fetchone()[0],
         con.execute("""SELECT COUNT(*) FROM pair p JOIN attack a ON a.name=p.attack_name
                        WHERE a.channel=? AND a.consequence=?""", (ch, co)).fetchone()[0])
        for ch, co, _, _ in f["pool"]]
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
    sl = S("The split", "Two communities, two vocabularies, one failure")
    table(sl, ["", "The security side", "The machine learning side"], [
        ("What corrupts the context",
         f"an attack  ({F['atk_sec']})", f"an incidental mechanism  ({F['atk_ml']})"),
        ("What the field builds against it",
         f"a defense  ({F['def_sec']})", f"a fix  ({F['def_ml']})"),
        ("Who put it there", "a person, on purpose", "nobody"),
        ("Examples", "indirect prompt injection, poisoned retrieval",
         "lost in the middle, knowledge conflict"),
    ], 2.20, [3.6, 4.1, 4.0], size=13.5, pitch=0.52)
    bullets(sl, [
        ("We keep both sets of words, because the two sides are not doing the same thing. "
         "A fix was never built to stop an adversary.", True),
        "A tool returns a page with a hidden order. A tool returns a page that is ten times too "
        "long. Both arrive by the same route and end in the same window. One has an author.",
        ("Our question: does that difference justify two separate sets of protection?", True),
    ], 4.90)
    cite(sl, f"Security side: {C['greshake']}", f"ML side: {C['liu_middle']}; {C['shi']}",
         f"Knowledge conflict: {C['kc_survey']}")

    # 4 ------------------------------------------------------------------
    sl = S("The framework", "We describe every case with three questions")
    table(sl, ["Tag", "The question it answers", "Values"], [
        ("Channel", "How did the text get in? Which route did it travel?", "9"),
        ("Intent", "Did a person put it there on purpose, or not?", "3"),
        ("Consequence", "What went wrong once the text was in the window?", "6"),
    ], 2.25, [2.6, 7.3, 1.8], size=15, pitch=0.60, align_right=(2,))
    bullets(sl, [
        ("9 channels x 3 intents x 6 consequences = 162 combinations.", True),
        "A combination with no paper in it is a question the field has never asked. 98 of the 162 are empty.",
        "The framework tells us what is known, and it tells us where to look next.",
    ], 4.50)
    cite(sl, "Framework: this work", f"Adversarial end: {C['greshake']}",
         f"Incidental end: {C['liu_middle']}")

    # 5 ------------------------------------------------------------------
    CH = dict(F["chan"])
    sl = S("Channel", "Nine routes carry text into the window")
    CH = dict(F["chan"])
    table(sl, ["Route", "What arrives this way", "Named attacks"], [
        ("tool-output", "a web page, an email, a file the agent opened", str(CH.get("tool-output", 0))),
        ("direct-input", "the prompt itself, or the system prompt above it", str(CH.get("direct-input", 0))),
        ("RAG", "a document a search step pulled from a corpus", str(CH.get("RAG", 0))),
        ("cross-modal", "text inside an image, audio or video", str(CH.get("cross-modal", 0))),
        ("memory", "something the agent stored earlier and reads again", str(CH.get("memory", 0))),
        ("tool-metadata", "the description of a tool, not its output", str(CH.get("tool-metadata", 0))),
        ("multi-agent", "a message from another agent", str(CH.get("multi-agent", 0))),
        ("supply-chain", "a package or template inherited before the run", str(CH.get("supply-chain", 0))),
        ("skill", "a stored procedure the agent loads and follows", str(CH.get("skill", 0))),
    ], 2.22, [2.6, 7.1, 2.0], size=13, pitch=0.44, align_right=(2,))
    tfc = tb(sl, M, 6.96, W - 0.75, 0.46)
    for i, line in enumerate([
            f"tool-output {short(C['greshake'])}  ·  direct-input {short(C['houyi'])}  ·  RAG {short(C['zou'])}  ·  memory {short(C['agentpoison'])}  ·  cross-modal {short(C['webinject'])}",
            f"tool-metadata {short(C['mcptox'])}  ·  multi-agent {short(C['infection'])}  ·  supply-chain {short(C['supplychain'])}  ·  skill {short(C['skillject'])}"]):
        put(tfc, line, 7.5, FAINT, first=(i == 0), after=0, line=1.2)

    # 6 ------------------------------------------------------------------
    CO = F["cons"]
    sl = S("Consequence", "Six ways the agent then fails")
    CO = F["cons"]
    table(sl, ["Failure", "What it means", "Named attacks"], [
        ("goal-hijack", "the agent does another person's task; text in the window gives an order and it obeys", str(CO.get("goal-hijack", 0))),
        ("reasoning-corruption", "every word is true, but the window is too long or too cluttered to use well", str(CO.get("reasoning-corruption", 0))),
        ("silent-corruption", "the agent answers from false content; nobody gave it a new task", str(CO.get("silent-corruption", 0))),
        ("persistence-backdoor", "the bad content is stored and fires on a later run", str(CO.get("persistence-backdoor", 0))),
        ("data-exfiltration", "the agent sends out what it can read", str(CO.get("data-exfiltration", 0))),
        ("resource-abuse", "the agent burns time, or refuses to answer at all", str(CO.get("resource-abuse", 0))),
    ], 2.30, [3.3, 6.4, 2.0], size=13, pitch=0.60, align_right=(2,))
    put(tb(sl, M, 6.30, W, 0.4),
        "The second row is the machine learning literature. The other five are the security "
        "literature. That is the split, in one column.", 13, MID, first=True, after=0)
    cite(sl, f"goal-hijack {short(C['greshake'])}",
         f"reasoning-corruption {short(C['liu_middle'])}; {short(C['shi'])}",
         f"silent-corruption {short(C['kconflict'])}",
         f"persistence-backdoor {short(C['agentpoison'])}",
         f"data-exfiltration {short(C['exfil'])}", f"resource-abuse {short(C['badrag'])}",
         y=6.92, size=7.5)

    # 7 ------------------------------------------------------------------
    sl = S("What we built", "A map of every attack and every defense in the field")
    table(sl, ["Count", "What it is"], [
        (f"{F['papers']:,} papers", "read in full and coded, drawn from about 26,000 candidates"),
        (f"{F['atk_sec']} attacks", "deliberate ways to corrupt a context window"),
        (f"{F['atk_ml']} mechanisms", "the same corruption arriving by accident"),
        (f"{F['def_sec']} defenses", "built to stop an adversary"),
        (f"{F['def_ml']} fixes", "built to stop the accident"),
        (f"{F['pairs']} pairs", "every case where a paper tested one defense against one attack"),
    ], 2.25, [3.0, 8.7], size=14.5, pitch=0.50)
    bullets(sl, [
        ("No prior survey holds both literatures. The closest reviews 78 papers, 37 attacks and "
         "41 defenses, and stays on the security side.", True),
        "That map is the instrument. Everything that follows is read off it.",
    ], 5.05)
    cite(sl, f"Closest prior survey: {C['sok_landscape']}",
         f"Review protocol follows {C['slr_prisma']} and {C['slr_kitchenham']}")

    # 8 ------------------------------------------------------------------
    sl = S("What the map is", "One row for every attack and every defense")
    bullets(sl, [
        ("The map is a table, not a picture. One row for each named attack, one row for each "
         "named defense, 771 rows in all.", True),
        "Every row carries the same three tags. We read them from the paper's full text, not its "
        "title, and they come from fixed lists, so two papers describing the same thing land in "
        "the same place.",
    ], 2.12, size=14, gap=8)
    table(sl, ["Field", "An attack row", "A defense row"], [
        ("Name", "corpus poisoning", "ParamMute"),
        ("Route in", "RAG", "RAG"),
        ("What goes wrong", "silent-corruption", "silent-corruption"),
        ("Caused by a person", "yes", "no - built for the accident"),
        ("From", "Zhong et al., EMNLP 2023", "Huang et al., NeurIPS 2025"),
    ], 3.60, [2.9, 4.4, 4.4], size=13, pitch=0.42)
    bullets(sl, [
        ("Same route, same failure, so the two rows share a cell and the defense has a claim to "
         "answer that attack.", True),
        "Nobody had ever run them against each other. We did.",
    ], 6.05, size=14, gap=7)
    cite(sl, f"corpus poisoning {short(C['corpuspoison'])}",
         f"ParamMute {short(C['parammute'])}")

    # 9 — the two literatures do not meet --------------------------------
    sl = S("Finding 1", "The two communities do not read each other")
    table(sl, ["Measure", "Value"], [
        ("Security papers citing at least one machine learning paper", "11.7 %"),
        ("Machine learning papers citing at least one security paper", "9.1 %"),
        ("Tested pairs that stay inside one literature", f"{F['same_pct']} %"),
        ("Combinations in the framework nobody has studied", "60.5 %"),
    ], 2.25, [8.4, 3.3], size=15, pitch=0.60, align_right=(1,))
    bullets(sl, [
        ("Nine of ten papers never cross. Seven pairs in the whole field do.", True),
        "This is not a sample. We resolved every citation edge in the corpus.",
        ("So every claim that a defense is robust holds inside one threat model. Nobody has "
         "checked the other one.", True),
    ], 5.05)

    # 9b — what a never-defended attack actually is ------------------------
    sl = S("Finding 2", "Causes that nothing has ever been run against")
    table(sl, ["Side", "Cause", "Never answered"], [
        ("security", f"attack  ({F['atk_sec']} named)", f"{F['und_sec']}"),
        ("machine learning", f"incidental mechanism  ({F['atk_ml']} named)", f"{F['und_ml']}"),
    ], 2.14, [3.0, 6.4, 2.3], size=14, pitch=0.46, align_right=(2,))
    bullets(sl, [
        ("That does not mean an attack is unproven. Each paper shows it working, against a system "
         "with no defense switched on.", True),
        "What those papers compare against is other attacks, not defenses:",
    ], 3.40, size=14, gap=8)
    table(sl, ["Attack", "Its paper compares against"], [
        ("HOUYI", "three earlier prompt injection techniques"),
        ("JudgeDeceiver", "six manual prompt injection attacks"),
        ("ASB: Plan-of-Thought backdoor", "five injection variants and five other attacks"),
        ("Virtual Prompt Injection", "clean training data and one concurrent poisoning method"),
    ], 4.42, [4.3, 7.4], size=13, pitch=0.44)
    bullets(sl, [
        ("Each paper asks whether its attack beats the last attack. Whether any published defense "
         "stops it is never asked.", True),
    ], 6.42, size=14)
    cite(sl, f"HOUYI {short(C['houyi'])}", "JudgeDeceiver Shi et al., ACM CCS 2024",
         "ASB Zhang et al., ICLR 2024", "VPI Yan et al., NAACL 2023")

    # 9c — and what a defense with no attack actually is -------------------
    sl = S("Finding 2, the other side", "320 protections never run against any cause")
    bullets(sl, [
        (f"{F['unt_sec']} of {F['def_sec']} defenses and {F['unt_ml']} of {F['def_ml']} fixes were "
         "never tested against a named cause. We read all 320 to see what they were answering.", True),
    ], 2.12, size=14, gap=6)
    table(sl, ["What we found", "Count", "Mostly from", "What it means"], [
        ("A fix for an accidental failure", "126", "ML side",
         "it answers a real failure; it never claimed to stop an adversary"),
        ("Names a cause, never tests it", "99", "both",
         "the cause is on our map; the experiment is missing"),
        ("Threat described in prose only", "41", "security",
         "an adversary is named; no experiment follows"),
        ("Tests an attack it invented", "22", "security",
         "evaluated only against the authors' own construction"),
        ("Names a benchmark, not a cause", "11", "security",
         "reports a score, not a protection outcome"),
        ("Could not tell", "21", "security", "not enough extracted text to decide"),
    ], 3.06, [3.7, 1.0, 1.5, 5.5], size=12.5, pitch=0.44, align_right=(1,))
    bullets(sl, [
        ("The 320 are not one thing. 124 of the first 126 come from the machine learning side: "
         "they are fixes for accidents, and calling them untested defenses is unfair to them.", True),
        "The 99 that name a cause and stop short of testing it are the real gap, and the lead we follow next.",
    ], 6.02, size=13, gap=5)

    # 10 — the gap, named ------------------------------------------------
    sl = S("The gap, in detail", "Where an untested pair is waiting")
    put(tb(sl, M, 2.10, W, 0.45),
        "Each row is one route and one failure. Deliberate attacks on one side, and on the other "
        "the fixes built for that same failure arriving by accident.", 14, MID, first=True, after=0)
    hdr = [("Route in", M, 2.7), ("What goes wrong", M + 2.8, 3.3),
           ("Attacks", M + 6.3, 1.5), ("Fixes", M + 8.0, 1.6),
           ("Ever tested\nagainst each other", M + 9.8, 2.2)]
    for lbl, x, w in hdr:
        tf = tb(sl, x, 2.64, w, 0.5)
        for j, ln in enumerate(lbl.split("\n")):
            put(tf, ln, 11.5, GREY, bold=True, first=(j == 0), after=0, line=1.1)
    for i, ((ch, co, na, nd), (crossed, _total)) in enumerate(zip(F["pool"], F["pool_tested"])):
        y = 3.20 + i * 0.40
        for txt, (lbl, x, w) in zip((ch, co, str(na), str(nd), str(crossed)), hdr):
            last = lbl.startswith("Ever tested")
            put(tb(sl, x, y, w, 0.32), txt, 13, INK if last else MID,
                bold=last, first=True, after=0)
    worst = max(zip(F["pool"], F["pool_tested"]), key=lambda z: z[1][1])
    body(sl, [
        ("Every row is zero. Not one of these pairs has been tested by anybody.", True),
        f"These cells are not ignored. {worst[0][0]} and {worst[0][1]} alone holds {worst[1][1]} "
        "tested pairs. But each one is a defense against an attack, or a fix against an accident. "
        "Nothing crosses.",
        "The RAG row is 3 attacks against 42 fixes. 126 possible tests. None run.",
    ], 6.02, gap=6, size=13.5)

    # 11 — what can be rebuilt ---------------------------------------------
    sl = S("What we can rebuild", "Released code is not the same as working code")
    put(tb(sl, M, 2.10, W, 0.4),
        "We only report a number if we can run the authors' own code. So the first question "
        "is which code runs at all.", 14, MID, first=True, after=0)

    table(sl, ["Attacks we rebuilt", "What it does to the answer"], [
        ("corpus poisoning", "removes the answer from the retrieved set"),
        ("PoisonedRAG", "inserts a false answer"),
        ("BadRAG DoS", "makes the agent refuse"),
        ("BadRAG Selective-Fact", "changes only the tone of a correct answer"),
    ], 2.60, [3.4, 8.3], size=13, pitch=0.44)
    table(sl, ["Defense codebases we opened", "Outcome"], [
        ("4 of 9", "run, and give a usable measurement"),
        ("1 of 9", "runs, but cannot reproduce its own published benefit"),
        ("4 of 9", "do not run: missing data, a missing prompt file, a checkpoint with no tokenizer"),
    ], 4.68, [3.4, 8.3], size=13, pitch=0.44)

    body(sl, [
        ("Nine defense codebases attempted. Four produced a measurement.", True),
        "That is not a complaint about other people's repositories. It sets the size of what "
        "this work can honestly cover, and it is a result the field should know.",
    ], 5.40, gap=8)

    # 12 — how pairs are chosen --------------------------------------------
    sl = S("How we choose a pair", "The map tells us which pairs can even be run")
    body(sl, [
        ("A defense and an attack belong together when they sit in the same place on the map: "
         "the same route in, and the same thing going wrong.", True),
        "If a defense was built for a failure that happens by accident, and an attack causes "
        "the same failure on purpose through the same route, then the defense has a claim to "
        "answer. Nobody has made it answer.",
    ], 2.10, gap=9)
    table(sl, ["The cell we started in", ""], [
        ("Route in", "a document returned by a search step"),
        ("What goes wrong", "the agent answers from false content and nothing signals it"),
        ("On the attack side", "3 named attacks, all deliberate"),
        ("On the fix side", "42 named fixes, all built for the accidental version"),
        ("Tested against each other", "none of them, by anyone"),
    ], 3.52, [3.7, 8.0], size=13.5, pitch=0.46)
    body(sl, [
        ("The map picked the first experiments, not us. Three of the four defenses we ran sit in "
         "that cell. The fourth answers the same failure arriving by a different route.", True),
        "We then widened the attack set along the same route. Two more attacks also poison a "
        "retrieved document, and testing those as well is how we checked that a result was about "
        "the defense and not about one attack.",
    ], 6.28, gap=6, size=13.5)

    # 13 — what we ran ------------------------------------------------------
    sl = S("What we ran", "The first measurements anyone has taken in that cell")
    table(sl, ["What we ran", "Detail"], [
        ("4 attacks", "rebuilt from released code and papers"),
        ("5 defenses", "counting two versions of one of them, all from released code"),
        (f"{len(F['verdicts'])} pairs", "defense against attack, on three models, none of them reported anywhere"),
        (f"{F['doses']} conditions", "each pair run at several attack strengths, not one"),
    ], 2.15, [2.8, 8.9], size=15, pitch=0.62)
    body(sl, [
        ("Two rules decide whether we are allowed to claim anything.", True),
        "A defense must first show its own benefit on its own task. If it cannot, we report "
        "nothing from it.",
        "We fix in advance the smallest change the sample can detect. Below that we say nothing, "
        "in either direction.",
        "Scoring is the authors' own code, unchanged.",
    ], 4.95, gap=8)

    # 14 — the answer -------------------------------------------------------
    sl = S("The result", "Does the defense stop the attack?")
    counts = {}
    for _, _, _, v, _ in F["verdicts"]:
        counts[v] = counts.get(v, 0) + 1
    table(sl, ["Outcome", "What it means", "Pairs"], [
        ("It stops the attack", "the attack succeeds less often with the defense switched on",
         str(counts.get("stops it", 0))),
        ("It does nothing", "no readable difference either way", str(counts.get("no effect", 0))),
        ("It makes the attack worse", "the attack succeeds MORE often with the defense switched on",
         str(counts.get("makes it worse", 0))),
    ], 2.25, [4.4, 6.1, 1.2], size=15.5, pitch=0.76, align_right=(2,))
    put(tb(sl, M, 4.72, W, 0.3), f"out of {len(F['verdicts'])} pairs measured",
        11.5, GREY, first=True, after=0)
    body(sl, [
        ("A defense helped in four cases out of eighteen. In seven it made the attack work better "
         "than no defense at all.", True),
        f"In {sum(1 for r in F['verdicts'] if r[4])} of those seven the attack does almost nothing "
        "to a model with no defense at all. The defense is what makes it work.",
        ("That is the finding. A defense built for one kind of failure is not neutral against the "
         "other kind. It can be the reason the attack succeeds.", True),
    ], 5.05, gap=9)

    # 15 — what is next -----------------------------------------------------
    sl = S("Where we are now", "What is finished and what is still running")
    table(sl, ["Done", ""], [
        ("1 cell", "worked through: the retrieved document, answering from false content"),
        (f"{len(F['verdicts'])} pairs", "measured, none of them previously tested"),
        ("3 models", "including a controlled repeat of the same pair on a second model"),
    ], 2.20, [1.9, 3.8], size=13, pitch=0.60, x=M)
    table(sl, ["Running now", ""], [
        ("5 models", "testing why one model breaks and another does not"),
    ], 4.50, [1.9, 3.8], size=13, pitch=0.50, x=M)
    put(tb(sl, M + 6.6, 2.10, 5.5, 0.32), "Left to do", 15, INK, bold=True, first=True, after=6)
    body(sl, [
        "One more attack in this cell: a third poisoning method with released code.",
        "An aggregation defense from a different research group, to check the rule is not "
        "one laboratory's habit.",
        "Then the next cell on the map. The largest untested pool is a different route in, "
        "with four attacks and seventy-nine defenses facing each other and nothing between them.",
        "99 defense papers name an attack on our map and never test against it. Those are the "
        "next candidates after that.",
    ], 2.48, size=13, w=5.5, x=M + 6.6, gap=10)
    body(sl, [
        (f"The cell we finished took four attacks and five defenses. The map holds "
         f"{F['pool_total'] - 1} more cells with both sides present and nothing tested between them.", True),
    ], 5.60, gap=6)

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

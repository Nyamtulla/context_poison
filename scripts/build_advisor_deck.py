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


def rows(sl, data, y, *, pitch=0.47, lw=2.9, size=13, right=None, x=None, w=None):
    """Plain two- or three-column text rows. No fills, no rules, no boxes.

    `x` and `w` place the block, so two of these can sit side by side. Without
    them it spans the page, which is what most slides want.
    """
    x0 = M if x is None else x
    width = W if w is None else w
    for i, item in enumerate(data):
        name, meaning = item[0], item[1]
        yy = y + i * pitch
        put(tb(sl, x0, yy, lw, 0.34), name, size, INK, bold=True, first=True, after=0)
        put(tb(sl, x0 + lw, yy, width - lw - (0.9 if right else 0), 0.34),
            meaning, size, MID, first=True, after=0)
        if right:
            put(tb(sl, x0 + width - 0.85, yy, 0.85, 0.34, align=PP_ALIGN.RIGHT),
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

    # 10 — the gap, named ------------------------------------------------
    sl = S("The gap, in detail", "Where an untested pair is waiting")
    put(tb(sl, M, 2.10, W, 0.45),
        "Each row is one route and one failure. The attacks are the deliberate ones. The defenses "
        "are the ones built for the same failure happening by accident.", 14, MID, first=True, after=0)
    hdr = [("Route in", M, 2.7), ("What goes wrong", M + 2.8, 3.3),
           ("Deliberate\nattacks", M + 6.3, 1.5), ("Accidental\ndefenses", M + 8.0, 1.6),
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
        "tested pairs. But each one is a security defense against a security attack, or an accident "
        "defense against an accident. Nothing crosses.",
        "The RAG row is 3 attacks against 42 defenses. 126 possible tests. None run.",
    ], 6.02, gap=6, size=13.5)

    # 11 — what can be rebuilt ---------------------------------------------
    sl = S("What we can rebuild", "Released code is not the same as working code")
    put(tb(sl, M, 2.10, W, 0.4),
        "We only report a number if we can run the authors' own code. So the first question "
        "is which code runs at all.", 14, MID, first=True, after=0)

    put(tb(sl, M, 2.66, 5.4, 0.32), "Attacks we rebuilt", 15, INK, bold=True, first=True, after=0)
    rows(sl, [
        ("Removes the answer", "corpus poisoning"),
        ("Inserts a false answer", "PoisonedRAG"),
        ("Forces a refusal", "BadRAG DoS"),
        ("Changes only the tone", "BadRAG Selective-Fact"),
    ], 3.06, pitch=0.46, lw=2.5, size=13, x=M, w=5.4)

    put(tb(sl, M + 6.3, 2.66, 5.4, 0.32), "Defense codebases we opened", 15, INK,
        bold=True, first=True, after=0)
    rows(sl, [
        ("4 run", "and give a usable measurement"),
        ("1 runs", "but cannot reproduce its own published benefit"),
        ("4 do not run", "missing data, a missing prompt file, a checkpoint with no tokenizer"),
    ], 3.06, pitch=0.70, lw=1.7, size=13, x=M + 6.3, w=5.4)

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
    put(tb(sl, M, 3.52, W, 0.34), "The cell we worked in", 15, INK, bold=True, first=True, after=8)
    rows(sl, [
        ("Route in", "a document returned by a search step"),
        ("What goes wrong", "the agent answers from false content and nothing signals it"),
        ("On the attack side", "3 named attacks, all deliberate"),
        ("On the defense side", "42 named defenses, all built for the accidental version"),
        ("Tested against each other", "none of them, by anyone"),
    ], 3.94, pitch=0.48, lw=3.6, size=13.5)
    body(sl, [
        ("Every defense we ran lives in that cell. So does every attack. We did not pick them "
         "because they looked promising. The map picked them.", True),
    ], 6.46, gap=6)

    # 13 — what we ran ------------------------------------------------------
    sl = S("What we ran", "The first measurements anyone has taken in that cell")
    rows(sl, [
        ("4 attacks", "rebuilt from released code and papers"),
        ("5 defenses", "counting two versions of one of them, all from released code"),
        (f"{len(F['verdicts'])} pairs", "defense against attack, on three models, none of them reported anywhere"),
        (f"{F['doses']} conditions", "each pair run at several attack strengths, not one"),
    ], 2.15, pitch=0.62, lw=3.0, size=15)
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
    rows(sl, [
        ("It stops the attack", "the attack succeeds less often with the defense switched on",
         counts.get("stops it", 0)),
        ("It does nothing", "no readable difference either way", counts.get("no effect", 0)),
        ("It makes the attack worse", "the attack succeeds MORE often with the defense switched on",
         counts.get("makes it worse", 0)),
    ], 2.25, pitch=0.76, lw=4.6, size=15.5, right=True)
    put(tb(sl, M + W - 3.0, 4.56, 3.0, 0.3), f"out of {len(F['verdicts'])} pairs",
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
    put(tb(sl, M, 2.10, 5.7, 0.32), "Done", 15, INK, bold=True, first=True, after=6)
    rows(sl, [
        ("1 cell", "worked through: the retrieved document, answering from false content"),
        (f"{len(F['verdicts'])} pairs", "measured, none of them previously tested"),
        ("3 models", "including a controlled repeat of the same pair on a second model"),
    ], 2.48, pitch=0.56, lw=1.9, size=13)
    put(tb(sl, M, 4.40, 5.7, 0.32), "Running now", 15, INK, bold=True, first=True, after=6)
    rows(sl, [
        ("5 models", "testing why one model breaks and another does not"),
    ], 4.78, pitch=0.5, lw=1.9, size=13)
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

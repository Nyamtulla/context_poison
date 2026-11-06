"""The taxonomy as a pipeline: where content enters, where defenses intervene.

The cube figure shows occupancy. It does not show the thing a reader needs
first, which is what the axes *are* and how they relate to the system being
attacked. This draws that: nine channels feeding one context window, three
places a defense can intervene, six ways the output goes wrong.

It is a flow rather than a tree on purpose. Our taxonomy is a cube --- channel
x intent x consequence --- and drawing a cube as a hierarchy would assert a
nesting that does not exist. The pipeline is the one ordering the three axes
genuinely have: content arrives somewhere, is acted on somewhere, and fails as
something.

No count appears on it. An earlier version printed a security and a safety
total beside every row, which made the figure read as a dashboard, invited
the counts to be mistaken for attacks against defenses, and printed one total
that had gone stale. The quantities belong in the prose, where they are
macros; this figure carries the vocabulary and the shape of the system.

Out: latex/figures/fig0_pipeline.pdf
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Ellipse

REPO = pathlib.Path(__file__).resolve().parent.parent
R = REPO / "data" / "registries"
OUT = REPO / "latex" / "figures"

INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8984"
# No grey washes: #f0efec made the figure read as a slide and vanished in
# print. The colour this figure does use is one hue per column, with icons,
# set in main(); see the note there for why it avoids red and blue.
# The track convention, the same hexes as gen_paper_figures.py: security is
# red and safety is blue, in every figure in the paper. This file had them
# the other way round, which made it the one figure where the colours meant
# the opposite of everywhere else.
SEC, ML = "#d6452a", "#2a78d6"
FULL = 7.0

plt.rcParams.update({
    "font.size": 7.5,
    "text.color": INK, "figure.dpi": 200,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.02, "pdf.fonttype": 42,
})
from paper_fonts import use_paper_font
use_paper_font(plt.rcParams)                # the paper's text face, not DejaVu

from taxonomy import CHANNELS, CONSEQ
POINTS = [("ingestion", "ingestion"), ("reasoning", "reasoning"),
          ("execution", "execution")]


def load(n):
    d = json.loads((R / n).read_text())
    if isinstance(d, list):
        return d
    for k in ("entries", "mechanisms", "defenses"):
        if isinstance(d.get(k), list):
            return d[k]
    return []


def box(ax, x, y, w, h, label, fc, ec, fs=6.4, tc=INK, weight="normal"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2",
                                linewidth=0.7, facecolor=fc, edgecolor=ec))
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
            fontsize=fs, color=tc, fontweight=weight, linespacing=1.25)


def arrow(ax, x1, y1, x2, y2, color=MUTED, lw=0.6, alpha=1.0):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=5, linewidth=lw,
                                 color=color, alpha=alpha,
                                 shrinkA=0, shrinkB=0))


def main():
    mech = load("rq3_pollution_registry.json")
    defs = load("rq4_defense_registry.json")
    mc = collections.Counter((e.get("channel"), e.get("regime")) for e in mech)
    dp = collections.Counter((e.get("defense_intervention_point"),
                              e.get("regime")) for e in defs)
    qc = collections.Counter((e.get("consequence"), e.get("regime"))
                             for e in mech)

    fig, ax = plt.subplots(figsize=(FULL, 3.6))
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")

    # Three titled columns of one shape: the axis name, then what it means,
    # inside a frame around what it holds. The headings used to float above
    # the stacks and ran past the figure's edges, and each axis was named
    # twice, once at the top and again under a rule at the bottom with its
    # count. No count appears now; the prose carries those as macros.
    FRAME = "#b9b8b3"
    top, bot, gap = 78.0, 4.5, 1.4      # extent of the stacks
    head_y, sub_y, frame_top = 94.2, 86.4, 99.0

    def column(x0, x1, name, what):
        ax.add_patch(FancyBboxPatch((x0, 0.5), x1 - x0, frame_top - 0.5,
                                    boxstyle="round,pad=0,rounding_size=1.6",
                                    linewidth=0.6, facecolor="none",
                                    edgecolor=FRAME, zorder=0))
        xc = (x0 + x1) / 2
        ax.text(xc, head_y, name, ha="center", va="center", fontsize=7.4,
                color=INK, fontweight="bold")
        # full ink: a grey description fades in a black-and-white print
        ax.text(xc, sub_y, what, ha="center", va="center", fontsize=6.4,
                color=INK, fontstyle="italic", linespacing=1.15)

    # each column holds its own fan-in or fan-out, so only the arrows
    # between the columns cross a frame
    column(0.5, 22.0, "Channel", "where untrusted\ncontent enters")
    column(24.0, 74.8, "Intervention point", "where a fix\ncan act")
    column(76.8, 99.5, "Consequence", "how the output\ngoes wrong")

    # ---- colour and icons ---------------------------------------------------
    # One hue per column: channels teal, consequences purple. Neither is the
    # paper's security red or safety blue, which mean the two regimes in every
    # other figure; this figure has no regime, so it must not borrow them.
    # Both clear 4.5:1 on white (6.0 and 5.95) and print as dark greys (80
    # and 102 of 255), so icons and outlines hold in black and white; the
    # tints print near-white (237). Labels stay ink, columns are told apart
    # by position and heading, and the one thing that matters -- which text
    # is untrusted -- also has a dashed border. Colour never carries meaning
    # on its own.
    CH, CH_T = "#0b6f65", "#e3f1ef"
    CQ, CQ_T = "#7d4ea8", "#f0e9f6"
    from matplotlib.font_manager import FontProperties
    ICONS = REPO / "third_party" / "fonts" / "material-icons"
    ifont = FontProperties(fname=ICONS / "MaterialIcons-Regular.ttf")
    cp = dict(l.split() for l in
              (ICONS / "MaterialIcons-Regular.codepoints").read_text().splitlines())

    def icon(x, y, name, color, size):
        ax.text(x, y, chr(int(cp[name], 16)), fontproperties=ifont,
                fontsize=size, color=color, ha="center", va="center", zorder=4)

    CH_ICON = {"direct-input": "keyboard", "tool-output": "terminal",
               "RAG": "travel_explore", "memory": "history",
               "multi-agent": "groups", "cross-modal": "image",
               "tool-metadata": "data_object", "skill": "extension",
               "supply-chain": "inventory_2"}
    CQ_ICON = {"goal-hijack": "alt_route",
               "reasoning-corruption": "psychology",
               "silent-corruption": "visibility_off",
               "data-exfiltration": "upload",
               "persistence-backdoor": "lock_open",
               "availability-loss": "block"}
    assert set(CH_ICON) == set(CHANNELS) and set(CQ_ICON) == set(CONSEQ), \
        "a channel or consequence has no icon; add one to the map"

    # ---- channels, left ----------------------------------------------------
    n = len(CHANNELS)
    h = (top - bot - gap * (n - 1)) / n
    BUS, RBUS = 19.8, 78.4
    for i, c in enumerate(CHANNELS):
        y = top - i * (h + gap) - h
        box(ax, 2, y, 15.5, h, "", CH_T, CH)
        icon(3.7, y + h / 2, CH_ICON[c], CH, 6.6)
        ax.text(5.4, y + h / 2, c, ha="left", va="center", fontsize=6.2, color=INK)
        # short stub to a vertical bus, instead of nine lines crossing the page
        ax.plot([17.7, BUS], [y + h / 2, y + h / 2], lw=0.5, color=CH,
                zorder=1)
    ax.plot([BUS, BUS], [bot + h / 2, top - h / 2], lw=0.7, color=CH,
            zorder=1)
    mid = (top + bot) / 2
    arrow(ax, BUS, mid, 31.2, mid, lw=1.0, color=CH)

    # ---- the pipeline ------------------------------------------------------
    # The context window is drawn as a small application window: a title bar,
    # an instruction line (gear), a user line (person), then a retrieved
    # passage in the channel teal (document) -- untrusted content sitting in
    # the same window as everything else, which is what the taxonomy is
    # about. Text is drawn as runs of word-length strokes, not solid bars,
    # so it reads as text rather than as a chart. The model is a small
    # layered network.
    CW = (31.6, mid - 14, 17.2, 28)      # x, y, w, h
    MD = (54, mid - 14, 12, 28)
    box(ax, *CW, "", "#ffffff", INK)
    box(ax, *MD, "", "#ffffff", INK)
    tb = 3.4                              # title-bar height
    ax.plot([CW[0], CW[0] + CW[2]], [CW[1] + CW[3] - tb] * 2, lw=0.5,
            color=INK, zorder=3)
    for k, col in enumerate(("#c9c8c3", "#c9c8c3", "#c9c8c3")):
        ax.add_patch(Ellipse((CW[0] + 1.3 + k * 1.1, CW[1] + CW[3] - tb / 2),
                             0.62, 0.62 * FULL / 3.6, facecolor=col,
                             edgecolor="none", zorder=4))
    # centred in the bar to the right of the three dots
    ax.text(CW[0] + (4.0 + CW[2]) / 2, CW[1] + CW[3] - tb / 2, "context window",
            ha="center", va="center", fontsize=6.2, color=INK, zorder=4)

    def words(x0, x1, y, lengths, color, lw=1.6):
        """A line of text as word strokes; lengths are fractions of the line."""
        x, gapw = x0, 0.55
        for L in lengths:
            seg = (x1 - x0) * L
            if x + seg > x1:
                break
            ax.plot([x, x + seg], [y, y], lw=lw, color=color,
                    solid_capstyle="round", zorder=4)
            x += seg + gapw

    GREY = "#a8a7a2"
    tx0, tx1 = CW[0] + 3.4, CW[0] + CW[2] - 1.2
    y0 = CW[1] + CW[3] - tb - 3.0
    icon(CW[0] + 1.7, y0, "settings", INK2, 5.6)
    words(tx0, tx1, y0, (0.22, 0.30, 0.16, 0.20), GREY)
    words(tx0, tx1, y0 - 2.3, (0.28, 0.18, 0.12), GREY)
    y1 = y0 - 5.6
    icon(CW[0] + 1.7, y1, "person", INK2, 5.6)
    words(tx0, tx1, y1, (0.18, 0.26, 0.22), GREY)
    # the retrieved passage: tinted block in the channel colour, with a
    # dashed border, because the tint prints as near-white in greyscale and
    # this is the one thing in the figure that must not depend on colour
    by = CW[1] + 1.6
    bh = y1 - 2.6 - by
    ax.add_patch(FancyBboxPatch((CW[0] + 0.9, by), CW[2] - 1.8, bh,
                                boxstyle="round,pad=0,rounding_size=0.8",
                                facecolor=CH_T, edgecolor=CH, linewidth=0.8,
                                linestyle=(0, (2.4, 1.4)), zorder=3))
    icon(CW[0] + 1.9, by + bh - 2.0, "description", CH, 5.8)
    for k, L in enumerate(((0.24, 0.18, 0.30, 0.14), (0.20, 0.32, 0.16),
                           (0.28, 0.22))):
        words(tx0, tx1 - 0.3, by + bh - 2.0 - k * 2.3, L, CH, lw=1.4)

    ax.text(MD[0] + MD[2] / 2, MD[1] + MD[3] - tb / 2, "model",
            ha="center", va="center", fontsize=6.2, color=INK, zorder=4)
    ax.plot([MD[0], MD[0] + MD[2]], [MD[1] + MD[3] - tb] * 2, lw=0.5,
            color=INK, zorder=3)

    # a 3-4-4-2 network; x and y units differ (7 in by 3.6 in), so nodes are
    # ellipses in data units that render round. Input nodes take the channel
    # colour and output nodes the consequence colour: content in, failure out.
    layers = (3, 4, 4, 2)
    gx0, gx1 = MD[0] + 2.0, MD[0] + MD[2] - 2.0
    gy0, gy1 = MD[1] + 2.4, MD[1] + MD[3] - tb - 2.0
    rx = 0.62
    ry = rx * FULL / 3.6
    pos = []
    for li, m in enumerate(layers):
        x = gx0 + li * (gx1 - gx0) / (len(layers) - 1)
        ys = [gy0 + (gy1 - gy0) * (j + 0.5) / m for j in range(m)]
        pos.append([(x, y) for y in ys])
    for a_, b_ in zip(pos, pos[1:]):
        for (x1, y1) in a_:
            for (x2, y2) in b_:
                ax.plot([x1, x2], [y1, y2], lw=0.3, color="#b5b4af", zorder=2)
    for li, layer in enumerate(pos):
        fc, ec = ((CH_T, CH) if li == 0 else
                  (CQ_T, CQ) if li == len(pos) - 1 else ("#ffffff", INK2))
        for (x, y) in layer:
            ax.add_patch(Ellipse((x, y), 2 * rx, 2 * ry, facecolor=fc,
                                 edgecolor=ec, linewidth=0.6, zorder=3))
    arrow(ax, 49.2, mid, 53.6, mid, lw=1.0, color=INK2)
    arrow(ax, 66.4, mid, RBUS, mid, lw=1.0, color=CQ)

    # ---- the three intervention points -------------------------------------
    # each label clears its column frame (24.0 and 74.8) by a margin
    for (key, lab), xc in zip(POINTS, (29.0, 51.4, 69.6)):
        ax.plot([xc, xc], [mid - 22, mid + 22], ls=(0, (2.2, 1.8)), lw=0.6,
                color=INK, zorder=1)
        ax.text(xc, mid - 26.5, lab, ha="center", fontsize=6.3, color=INK,
                fontweight="bold")

    # ---- consequences, right -----------------------------------------------
    n2 = len(CONSEQ)
    h2 = (top - bot - gap * (n2 - 1)) / n2
    for i, c in enumerate(CONSEQ):
        y = top - i * (h2 + gap) - h2
        box(ax, 79.7, y, 19.0, h2, "", CQ_T, CQ)
        icon(81.1, y + h2 / 2, CQ_ICON[c], CQ, 6.8)
        ax.text(82.6, y + h2 / 2, c, ha="left", va="center", fontsize=6.2,
                color=INK)
        # the output fans out the way the input fanned in
        ax.plot([RBUS, 79.5], [y + h2 / 2, y + h2 / 2], lw=0.5, color=CQ,
                zorder=1)
    ax.plot([RBUS, RBUS], [bot + h2 / 2, top - h2 / 2], lw=0.7, color=CQ,
            zorder=1)

    # Regime is carried by every entry wherever it sits, so it has no
    # position here; the caption says so in one clause.

    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"fig0_pipeline.{ext}")
    plt.close(fig)
    print(f"wrote {OUT/'fig0_pipeline.pdf'} (+ .png preview)")


if __name__ == "__main__":
    main()

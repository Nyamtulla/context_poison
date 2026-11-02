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
# No fills. Every box here was washed in #f0efec, which is the shade that
# makes a figure read as a slide and is the first thing to disappear in a
# printed copy. Boxes are white with a hairline edge; the rules and stubs
# are ink, thin.
# The track convention, the same hexes as gen_paper_figures.py: security is
# red and safety is blue, in every figure in the paper. This file had them
# the other way round, which made it the one figure where the colours meant
# the opposite of everywhere else.
SEC, ML = "#d6452a", "#2a78d6"
FULL = 7.0

plt.rcParams.update({
    "font.family": "serif", "font.size": 7.5,
    "text.color": INK, "figure.dpi": 200,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.02, "pdf.fonttype": 42,
})

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
        ax.text(xc, sub_y, what, ha="center", va="center", fontsize=6.3,
                color=INK2, fontstyle="italic", linespacing=1.15)

    # each column holds its own fan-in or fan-out, so only the arrows
    # between the columns cross a frame
    column(0.5, 22.0, "Channel", "where untrusted\ncontent enters")
    column(24.0, 74.8, "Intervention point", "where a defense\ncan act")
    column(76.8, 99.5, "Consequence", "how the output\ngoes wrong")

    # ---- channels, left ----------------------------------------------------
    n = len(CHANNELS)
    h = (top - bot - gap * (n - 1)) / n
    BUS, RBUS = 19.8, 78.4
    for i, c in enumerate(CHANNELS):
        y = top - i * (h + gap) - h
        box(ax, 2, y, 15.5, h, "", "#ffffff", INK)
        ax.text(3.2, y + h / 2, c, ha="left", va="center", fontsize=6.3, color=INK)
        # short stub to a vertical bus, instead of nine lines crossing the page
        ax.plot([17.7, BUS], [y + h / 2, y + h / 2], lw=0.4, color=INK,
                zorder=1)
    ax.plot([BUS, BUS], [bot + h / 2, top - h / 2], lw=0.6, color=INK,
            zorder=1)
    mid = (top + bot) / 2
    arrow(ax, BUS, mid, 31.8, mid, lw=1.0, color=INK2)

    # ---- the pipeline ------------------------------------------------------
    # Each box carries a glyph of what it is, label on top. The context
    # window is a page of text lines, one of them hatched: untrusted content
    # sits in the same window as everything else, which is the problem the
    # taxonomy describes. The model is a small layered network. Both are
    # ink only, so they survive a greyscale print.
    CW = (32.2, mid - 13, 15.6, 26)      # x, y, w, h
    MD = (54, mid - 13, 12, 26)
    box(ax, *CW, "", "#ffffff", INK)
    box(ax, *MD, "", "#ffffff", INK)
    ax.text(CW[0] + CW[2] / 2, CW[1] + CW[3] - 3.6, "context window",
            ha="center", va="center", fontsize=6.6, color=INK)
    ax.text(MD[0] + MD[2] / 2, MD[1] + MD[3] - 3.6, "model",
            ha="center", va="center", fontsize=6.6, color=INK)

    # text lines; widths vary as a paragraph's do, the hatched one is the
    # untrusted passage
    widths = (0.92, 0.78, 0.88, 0.95, 0.70, 0.85)
    lx, lw_ = CW[0] + 1.6, CW[2] - 3.2
    ly, lh, lstep = CW[1] + CW[3] - 8.6, 1.7, 2.95
    for k, wf in enumerate(widths):
        y = ly - k * lstep
        hatched = k == 3
        ax.add_patch(Rectangle((lx, y), lw_ * wf, lh,
                               facecolor="#ffffff" if hatched else "#9c9b97",
                               edgecolor=INK if hatched else "none",
                               hatch="//////" if hatched else None,
                               linewidth=0.5))

    # a 3-4-4-2 network; x and y units differ (7 in by 3.6 in), so nodes are
    # ellipses in data units that render round
    layers = (3, 4, 4, 2)
    gx0, gx1 = MD[0] + 2.0, MD[0] + MD[2] - 2.0
    gy0, gy1 = MD[1] + 2.6, MD[1] + MD[3] - 7.4
    rx = 0.62
    ry = rx * FULL / 3.6
    pos = []
    for li, m in enumerate(layers):
        x = gx0 + li * (gx1 - gx0) / (len(layers) - 1)
        ys = [gy0 + (gy1 - gy0) * (j + 0.5) / m for j in range(m)]
        pos.append([(x, y) for y in ys])
    for a, b in zip(pos, pos[1:]):
        for (x1, y1) in a:
            for (x2, y2) in b:
                ax.plot([x1, x2], [y1, y2], lw=0.3, color="#9c9b97", zorder=2)
    for layer in pos:
        for (x, y) in layer:
            ax.add_patch(Ellipse((x, y), 2 * rx, 2 * ry, facecolor="#ffffff",
                                 edgecolor=INK, linewidth=0.55, zorder=3))
    arrow(ax, 48.2, mid, 53.6, mid, lw=1.0, color=INK2)
    arrow(ax, 66.4, mid, RBUS, mid, lw=1.0, color=INK2)

    # ---- the three intervention points -------------------------------------
    for (key, lab), xc in zip(POINTS, (28.6, 50.5, 70.4)):
        ax.plot([xc, xc], [mid - 22, mid + 22], ls=(0, (2.2, 1.8)), lw=0.6,
                color=INK, zorder=1)
        ax.text(xc, mid - 26.5, lab, ha="center", fontsize=6.6, color=INK,
                fontweight="bold")

    # ---- consequences, right -----------------------------------------------
    n2 = len(CONSEQ)
    h2 = (top - bot - gap * (n2 - 1)) / n2
    for i, c in enumerate(CONSEQ):
        y = top - i * (h2 + gap) - h2
        box(ax, 79.7, y, 19.0, h2, "", "#ffffff", INK)
        ax.text(80.8, y + h2 / 2, c, ha="left", va="center", fontsize=5.9,
                color=INK)
        # the output fans out the way the input fanned in
        ax.plot([RBUS, 79.5], [y + h2 / 2, y + h2 / 2], lw=0.4, color=INK,
                zorder=1)
    ax.plot([RBUS, RBUS], [bot + h2 / 2, top - h2 / 2], lw=0.6, color=INK,
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

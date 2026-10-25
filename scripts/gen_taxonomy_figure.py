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
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

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

CHANNELS = ["direct-input", "tool-output", "RAG", "memory", "multi-agent",
            "cross-modal", "tool-metadata", "skill", "supply-chain"]
# Keep in step with CQS in gen_paper_numbers.py and CONSEQ in
# gen_paper_figures.py. availability-loss joined the scheme and this list was
# missed, so the figure drew six columns while the paper said seven.
CONSEQ = ["goal-hijack", "reasoning-corruption", "silent-corruption",
          "data-exfiltration", "persistence-backdoor", "resource-abuse",
          "availability-loss"]
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

    # ---- channels, left ----------------------------------------------------
    n = len(CHANNELS)
    top, bot, gap = 88.0, 15.0, 1.4
    h = (top - bot - gap * (n - 1)) / n
    ax.text(9, 96.4, "where untrusted content enters", ha="center",
            fontsize=7, color=INK, fontweight="bold")
    BUS = 25.0
    for i, c in enumerate(CHANNELS):
        y = top - i * (h + gap) - h
        box(ax, 1, y, 17, h, "", "#ffffff", INK)
        ax.text(2.3, y + h / 2, c, ha="left", va="center", fontsize=6.3, color=INK)
        # short stub to a vertical bus, instead of nine lines crossing the page
        ax.plot([18.2, BUS], [y + h / 2, y + h / 2], lw=0.4, color=INK,
                zorder=0)
    ax.plot([BUS, BUS], [bot + h / 2, top - h / 2], lw=0.6, color=INK,
            zorder=0)
    arrow(ax, BUS, 50, 30.4, 50, lw=1.0, color=INK2)

    # ---- the pipeline ------------------------------------------------------
    box(ax, 31, 38, 15, 24, "context\nwindow", "#ffffff", INK, fs=7)
    box(ax, 55, 38, 13, 24, "model", "#ffffff", INK, fs=7)
    arrow(ax, 46.4, 50, 54.6, 50, lw=1.0, color=INK2)
    arrow(ax, 68.4, 50, 76.4, 50, lw=1.0, color=INK2)

    # ---- the three intervention points -------------------------------------
    for (key, lab), xc in zip(POINTS, (28.6, 50.5, 69.4)):
        ax.plot([xc, xc], [34, 74], ls=(0, (2.2, 1.8)), lw=0.6,
                color=INK, zorder=0)
        ax.text(xc, 30.0, lab, ha="center", fontsize=6.6, color=INK,
                fontweight="bold")
    ax.text(50, 76.5, f"where a defense can intervene "
                      f"({len(POINTS)} intervention points)", ha="center",
            fontsize=6.4, color=INK)

    # ---- consequences, right -----------------------------------------------
    n2 = len(CONSEQ)
    h2 = (top - bot - gap * (n2 - 1)) / n2
    ax.text(88.5, 96.4, "how the output goes wrong", ha="center",
            fontsize=7, color=INK, fontweight="bold")
    for i, c in enumerate(CONSEQ):
        y = top - i * (h2 + gap) - h2
        box(ax, 77.5, y, 21.5, h2, "", "#ffffff", INK)
        ax.text(78.7, y + h2 / 2, c, ha="left", va="center", fontsize=5.9,
                color=INK)

    # The three axes of the taxonomy, named together. Regime has no place
    # in the flow -- every mechanism and every defense carries one wherever
    # it sits -- so it was left off the figure entirely and the caption had
    # to apologise for it. Naming all three on one strip draws it without
    # pretending it is a stage.
    ax.plot([1, 99], [10.5, 10.5], lw=0.5, color=INK)
    ax.text(9.5, 5.5, f"channel  ({len(CHANNELS)} values)", ha="center",
            fontsize=6.2, color=INK)
    ax.text(88.5, 5.5, f"consequence  ({len(CONSEQ)} values)", ha="center",
            fontsize=6.2, color=INK)
    ax.text(36, 5.5, "regime", ha="left", va="center", fontsize=6.2,
            color=INK)
    for x0, c, lab in ((44.5, SEC, "security"), (56.5, ML, "safety")):
        ax.add_patch(FancyBboxPatch((x0, 4.6), 1.8, 1.8,
                                    boxstyle="round,pad=0,rounding_size=0.3",
                                    linewidth=0, facecolor=c))
        ax.text(x0 + 2.6, 5.5, lab, ha="left", va="center", fontsize=6.2,
                color=INK)
    ax.text(50, 0.6, "every mechanism and every defense carries a regime "
                     "wherever it sits", ha="center", fontsize=5.8, color=INK)

    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"fig0_pipeline.{ext}")
    plt.close(fig)
    print(f"wrote {OUT/'fig0_pipeline.pdf'} (+ .png preview)")


if __name__ == "__main__":
    main()

"""The taxonomy as three linked distributions along the agent pipeline.

A taxonomy figure that only labels its own axes is a diagram, not a result.
This encodes the three axes as quantities, so the reader sees the asymmetry
rather than reading it off numerals:

  where content enters     9 channels     named mechanisms, by track
  where a defense acts     3 points       named defenses, by track
  how the output fails     6 consequences named mechanisms, by track

Drawn as a flow rather than a tree because the taxonomy is a cube, and drawing
a cube as a hierarchy would assert a nesting that does not exist. The pipeline
is the one ordering the three axes genuinely have.

Panels A and C count the same \\NMechanisms{} mechanisms on two different axes,
so they share an x scale; B counts defenses and says so. Bar colour carries
track and nothing else: every numeral is set in ink, never in a series colour.

Out: latex/figures/fig0_pipeline.pdf
"""
from __future__ import annotations

import collections
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

REPO = pathlib.Path(__file__).resolve().parent.parent
R = REPO / "data" / "registries"
OUT = REPO / "latex" / "figures"

SEC, ML = "#2a78d6", "#eb6834"
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#eceae6"
FULL = 7.0

plt.rcParams.update({
    "font.family": "serif", "font.size": 7.5, "figure.dpi": 200,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.02, "pdf.fonttype": 42,
    "text.color": INK,
})

CHANNELS = ["direct-input", "tool-output", "RAG", "memory", "cross-modal",
            "tool-metadata", "multi-agent", "supply-chain", "skill"]
CONSEQ = ["goal-hijack", "reasoning-corruption", "silent-corruption",
          "persistence-backdoor", "data-exfiltration", "resource-abuse"]
POINTS = ["ingestion", "reasoning", "execution"]


def load(n):
    d = json.loads((R / n).read_text())
    if isinstance(d, list):
        return d
    for k in ("entries", "mechanisms", "defenses"):
        if isinstance(d.get(k), list):
            return d[k]
    return []


def pair_bars(ax, labels, sec, mlv, xmax, unit, show_all=True):
    """Grouped horizontal bars, security above machine learning in each slot.

    Rounded data-ends, a recessive x grid, and value labels in ink outside the
    bar so the number never sits on the colour it describes.
    """
    y = np.arange(len(labels))
    h = 0.36
    for off, v, c in ((h / 2, sec, SEC), (-h / 2, mlv, ML)):
        ax.barh(y + off, v, h, color=c, zorder=3,
                linewidth=0, align="center")
        for yi, vi in zip(y + off, v):
            if vi == 0:
                ax.text(1.0, yi, "0", va="center", ha="left",
                        fontsize=5.4, color=MUTED, zorder=4)
            elif show_all:
                ax.text(vi + xmax * 0.018, yi, str(vi), va="center",
                        ha="left", fontsize=5.6, color=INK2, zorder=4)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=6.3)
    ax.invert_yaxis()
    ax.set_xlim(0, xmax)
    ax.set_ylim(len(labels) - 0.5, -0.5)
    ax.set_xlabel(unit, fontsize=6.2, color=INK2)
    ax.tick_params(axis="x", labelsize=5.8, length=0, colors=INK2)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=GRID, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.spines["bottom"].set_linewidth(0.6)


def main():
    mech, defs = load("rq3_pollution_registry.json"), load("rq4_defense_registry.json")
    mc = collections.Counter((e.get("channel"), e.get("track")) for e in mech)
    qc = collections.Counter((e.get("consequence"), e.get("track")) for e in mech)
    dp = collections.Counter((e.get("defense_intervention_point"),
                              e.get("track")) for e in defs)
    g = lambda c, k, t: c.get((k, t), 0)

    ch_s = [g(mc, c, "Security") for c in CHANNELS]
    ch_m = [g(mc, c, "ML/AI") for c in CHANNELS]
    cq_s = [g(qc, c, "Security") for c in CONSEQ]
    cq_m = [g(qc, c, "ML/AI") for c in CONSEQ]
    dp_s = [g(dp, p, "Security") for p in POINTS]
    dp_m = [g(dp, p, "ML/AI") for p in POINTS]
    # A and C count the SAME mechanisms on two axes, so one scale for both
    mx = max(max(ch_s + ch_m), max(cq_s + cq_m)) * 1.22

    fig = plt.figure(figsize=(FULL, 3.15))
    axA = fig.add_axes([0.072, 0.215, 0.200, 0.605])
    axB = fig.add_axes([0.412, 0.215, 0.168, 0.605])
    axC = fig.add_axes([0.772, 0.215, 0.188, 0.605])

    pair_bars(axA, CHANNELS, ch_s, ch_m, mx, "named mechanisms")
    pair_bars(axB, POINTS, dp_s, dp_m, max(dp_s + dp_m) * 1.30, "named defenses")
    pair_bars(axC, CONSEQ, cq_s, cq_m, mx, "named mechanisms")

    for ax, t in ((axA, "A. where untrusted content enters"),
                  (axB, "B. where a defense acts"),
                  (axC, "C. how the output fails")):
        ax.set_title(t, fontsize=6.9, color=INK, fontweight="bold",
                     loc="left", pad=5)

    # ---- the pipeline, carried in the gaps between the panel titles -------
    # The arrows cannot run at mid-height: panels B and C carry long row
    # labels to the left of their axes and an arrow there strikes through
    # them. At title height the gaps are clear, and the three titles then
    # read as one sentence, which is the flow.
    for x0, x1 in ((0.378, 0.432), (0.665, 0.719)):
        fig.add_artist(FancyArrowPatch((x0, 0.868), (x1, 0.868),
                                       transform=fig.transFigure,
                                       arrowstyle="-|>", mutation_scale=6,
                                       linewidth=0.9, color=MUTED,
                                       shrinkA=0, shrinkB=0))

    # ---- legend, once, top left -------------------------------------------
    for i, (c, lab) in enumerate(((SEC, "security track"),
                                  (ML, "machine learning track"))):
        fig.patches.append(plt.Rectangle((0.072 + i * 0.128, 0.936), 0.015, 0.022,
                                         transform=fig.transFigure, facecolor=c,
                                         edgecolor="none"))
        fig.text(0.092 + i * 0.128, 0.947, lab, fontsize=6.4, color=INK,
                 va="center")

    fig.text(0.072, 0.012,
             "Panels A and C count the same 233 named mechanisms on two "
             "different axes and share a scale; B counts the 541 named "
             "defenses and has its own.",
             fontsize=5.9, color=MUTED)

    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"fig0_pipeline.{ext}")
    plt.close(fig)
    print(f"wrote {OUT/'fig0_pipeline.pdf'} (+ .png preview)")


if __name__ == "__main__":
    main()

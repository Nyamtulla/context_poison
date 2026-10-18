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

Every number is read from the registries. The asymmetry it exposes is the
paper's argument in one picture: the security track masses at ingestion, the
machine learning track at reasoning, and execution is security-only.

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

CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8984"
GREY = "#f0efec"
SEC, ML = CAT[0], CAT[1]
FULL = 7.0

plt.rcParams.update({
    "font.family": "serif", "font.size": 7.5,
    "text.color": INK, "figure.dpi": 200,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.02, "pdf.fonttype": 42,
})

CHANNELS = ["direct-input", "tool-output", "RAG", "memory", "multi-agent",
            "cross-modal", "tool-metadata", "skill", "supply-chain"]
CONSEQ = ["goal-hijack", "reasoning-corruption", "silent-corruption",
          "data-exfiltration", "persistence-backdoor", "resource-abuse"]
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
    mc = collections.Counter((e.get("channel"), e.get("track")) for e in mech)
    dp = collections.Counter((e.get("defense_intervention_point"),
                              e.get("track")) for e in defs)
    qc = collections.Counter((e.get("consequence"), e.get("track"))
                             for e in mech)

    fig, ax = plt.subplots(figsize=(FULL, 3.6))
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")

    # ---- legend, top centre (keeps colour meaning off the busy middle) -----
    ax.add_patch(FancyBboxPatch((38.0, 92.6), 2.0, 2.0,
                                boxstyle="round,pad=0,rounding_size=0.5",
                                facecolor=SEC, edgecolor="none"))
    ax.text(40.9, 93.6, "security", ha="left", va="center",
            fontsize=6.4, color=INK)
    ax.add_patch(FancyBboxPatch((50.0, 92.6), 2.0, 2.0,
                                boxstyle="round,pad=0,rounding_size=0.5",
                                facecolor=ML, edgecolor="none"))
    ax.text(52.9, 93.6, "machine learning", ha="left", va="center",
            fontsize=6.4, color=INK)

    # ---- channels, left ----------------------------------------------------
    n = len(CHANNELS)
    top, bot, gap = 88.0, 7.0, 1.4
    h = (top - bot - gap * (n - 1)) / n
    ax.text(11, 96.4, "where untrusted content enters", ha="center",
            fontsize=7, color=INK, fontweight="bold")
    ax.text(16.6, 90.0, "sec", ha="center", fontsize=5.6, color=SEC)
    ax.text(20.0, 90.0, "ml", ha="center", fontsize=5.6, color=ML)
    ax.text(11, 2.2, "9 channels, 233 named mechanisms", ha="center",
            fontsize=6.0, color=INK2)
    BUS = 25.0
    for i, c in enumerate(CHANNELS):
        y = top - i * (h + gap) - h
        s_, m_ = mc.get((c, "Security"), 0), mc.get((c, "ML/AI"), 0)
        box(ax, 1, y, 21, h, "", GREY, "#dcdad6")
        ax.text(2.3, y + h / 2, c, ha="left", va="center", fontsize=6.3, color=INK)
        ax.text(16.6, y + h / 2, f"{s_}", ha="center", va="center",
                fontsize=6.2, color=SEC, fontweight="bold")
        ax.text(20.0, y + h / 2, f"{m_}", ha="center", va="center",
                fontsize=6.2, color=ML, fontweight="bold")
        # short stub to a vertical bus, instead of nine lines crossing the page
        ax.plot([22.2, BUS], [y + h / 2, y + h / 2], lw=0.5, color="#c9c7c3",
                zorder=0)
    ax.plot([BUS, BUS], [bot + h / 2, top - h / 2], lw=0.8, color="#c9c7c3",
            zorder=0)
    arrow(ax, BUS, 50, 30.4, 50, lw=1.0, color=INK2)

    # ---- the pipeline ------------------------------------------------------
    box(ax, 31, 38, 15, 24, "context\nwindow", "#ffffff", MUTED, fs=7)
    box(ax, 55, 38, 13, 24, "model", "#ffffff", MUTED, fs=7)
    arrow(ax, 46.4, 50, 54.6, 50, lw=1.0, color=INK2)
    arrow(ax, 68.4, 50, 73.4, 50, lw=1.0, color=INK2)

    # ---- the three intervention points -------------------------------------
    for (key, lab), xc in zip(POINTS, (28.6, 50.5, 69.4)):
        s_, m_ = dp.get((key, "Security"), 0), dp.get((key, "ML/AI"), 0)
        ax.plot([xc, xc], [30, 70], ls=(0, (2.2, 1.8)), lw=0.8,
                color="#b9b7b2", zorder=0)
        ax.text(xc, 26.0, lab, ha="center", fontsize=6.6, color=INK,
                fontweight="bold")
        ax.text(xc - 0.7, 21.3, f"{s_}", ha="right", fontsize=7.6, color=SEC,
                fontweight="bold")
        ax.text(xc, 21.3, "/", ha="center", fontsize=6.4, color=MUTED)
        ax.text(xc + 0.7, 21.3, f"{m_}", ha="left", fontsize=7.6, color=ML,
                fontweight="bold")
    ax.text(50, 31.5, "where a defense can intervene", ha="center",
            fontsize=6.4, color=INK2, style="italic")
    ax.text(50, 2.2, "3 intervention points, 541 named defenses",
            ha="center", fontsize=6.0, color=INK2)

    # ---- consequences, right -----------------------------------------------
    n2 = len(CONSEQ)
    h2 = (top - bot - gap * (n2 - 1)) / n2
    ax.text(86.5, 96.4, "how the output goes wrong", ha="center",
            fontsize=7, color=INK, fontweight="bold")
    ax.text(93.6, 90.0, "sec", ha="center", fontsize=5.6, color=SEC)
    ax.text(97.2, 90.0, "ml", ha="center", fontsize=5.6, color=ML)
    ax.text(86.5, 2.2, "6 consequences, the same 233 mechanisms", ha="center", fontsize=6.0, color=INK2)
    for i, c in enumerate(CONSEQ):
        y = top - i * (h2 + gap) - h2
        s_, m_ = qc.get((c, "Security"), 0), qc.get((c, "ML/AI"), 0)
        box(ax, 74.5, y, 24.5, h2, "", GREY, "#dcdad6")
        ax.text(75.7, y + h2 / 2, c, ha="left", va="center", fontsize=5.9,
                color=INK)
        ax.text(93.6, y + h2 / 2, f"{s_}", ha="center", va="center",
                fontsize=6.2, color=SEC, fontweight="bold")
        ax.text(97.2, y + h2 / 2, f"{m_}", ha="center", va="center",
                fontsize=6.2, color=ML, fontweight="bold")

    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"fig0_pipeline.{ext}")
    plt.close(fig)
    print(f"wrote {OUT/'fig0_pipeline.pdf'} (+ .png preview)")


if __name__ == "__main__":
    main()

"""Generate every figure in the SoK paper, as vector PDF for LaTeX.

Run:  python3 scripts/gen_paper_figures.py
Out:  latex/figures/*.pdf

Colour follows the validated reference palette from the dataviz skill, used
unchanged rather than invented: categorical slots in fixed order, one-hue
sequential ramp for magnitude, blue/red diverging with a neutral grey midpoint
for polarity. No dual axes anywhere. Every figure that carries two or more
series has a legend, so identity is never colour alone.
"""
import collections
import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import openpyxl
from scipy.stats import fisher_exact
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Patch

REPO = pathlib.Path(__file__).resolve().parent.parent
R = REPO / "data" / "registries"
OUT = REPO / "latex" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(REPO / "scripts"))

# --- validated reference palette -------------------------------------------
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#256abf",
       "#1c5cab", "#184f95", "#104281", "#0d366b"]
# Track convention, used in every figure that encodes track by colour:
# Security is red, machine learning is blue. Validated for deuteranopia and
# protanopia (OKLab separation 28.8 / 25.0, floor is 8).
TRACK_SEC, TRACK_ML = "#d6452a", "#2a78d6"

# Ramps for magnitude. A panel that IS one track takes that track's ramp; a
# panel that mixes tracks takes the neutral one, so a hue never means
# "magnitude" and "regime" in the same figure.
SEQ_SEC = ["#fbdcd3", "#f6b9a8", "#ef947c", "#e76f52", "#d6452a", "#bf3d25",
           "#ab361f", "#95301b", "#812814", "#6b1f0d"]
# A mixed-track panel cannot take red or blue without a hue meaning both
# "magnitude" and "regime" in one figure, and a grey ramp reads as a shaded
# slide. One off-track hue, light to dark: lightness carries the magnitude,
# so it survives both common CVD types and greyscale printing.
SEQ_ALT = ["#e3f5ee", "#c4e9dc", "#9eddc8", "#74cfb1", "#46c098",
           "#1baf7a", "#169068", "#117455", "#0d5a42", "#09412f"]
# Hues for distinctions that are NOT regime, with one meaning each across
# every figure: ALT_A is the defense side (defenses, defense wins, defense
# predates its attack) and ALT_B the attack side (mechanisms, defense loses,
# attack predates its defense). ALT_B is always the hatched one. ALT_C is
# kept for a third category no figure currently needs.
ALT_A, ALT_B, ALT_C = "#1baf7a", "#eda100", "#8a5a2b"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8984"

# IEEEtran conference: \columnwidth is 252pt and \textwidth is 516pt,
# which is 3.49in and 7.14in. Measured from a probe build, not guessed.
# (acmart sigconf was 3.33 / 7.0; figures were resized when the paper moved.)
COL, FULL = 3.49, 7.14

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 7.5,
    "axes.labelsize": 7.5,
    "axes.titlesize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "axes.edgecolor": MUTED,
    "axes.linewidth": 0.6,
    "xtick.color": INK, "ytick.color": INK,
    # every categorical pair in this file is ALSO separated by a
    # hatch, so the figures read in black and white; the default
    # hatch stroke is too fine to survive a 300dpi print
    "hatch.linewidth": 0.4,
    "text.color": INK, "axes.labelcolor": INK,
    "figure.dpi": 200,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
    "pdf.fonttype": 42,
})

from taxonomy import CHANNELS, CONSEQ, canon_consequence


def load(n):
    return json.loads((R / n).read_text())


def corpus():
    wb = openpyxl.load_workbook(
        REPO / "data" / "exports" / "paper_dashboard_source.xlsx", read_only=True)
    ws = wb["Papers"]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    hdr = list(rows[0])
    si = hdr.index("screening")
    return hdr, [r for r in rows[1:] if str(r[si]).strip() != "Exclude"]


def save(fig, name):
    fig.savefig(OUT / f"{name}.pdf")
    plt.close(fig)
    print(f"  wrote latex/figures/{name}.pdf")


# ---------------------------------------------------------------- figure 1
def fig_cube():
    """Named attacks against named defenses, per cell, split by track.

    Three quantities per cell -- attacks, defenses, and which track -- so
    track is the panel (red Security, blue ML/AI, as everywhere else) and
    attacks against defenses is a pair of mini bars inside the cell. Solid
    is an attack, pale and hatched is a defense, which separates them
    without a second hue and survives greyscale and both common CVD types.

    Heights are SQRT scaled against one global maximum shared by both
    panels. Linear would make 113 the only visible bar in the figure and
    hide every cell holding one or two entries, which is most of the cube.
    A cell holding mechanisms and no fix at all is outlined.

    Each panel carries its own margins: a last column totalling every
    consequence for a channel, and a last row totalling every channel for a
    consequence. They sit a gap away from the grid so they cannot be read
    as a seventh consequence or a tenth channel. Margins take the paper's
    off-regime pair -- amber for the mechanism side, green for the fix
    side -- because a total is across the regimes and must not wear either
    regime's hue. Each panel's margins are scaled against their own maximum, so a
    margin bar and a cell bar of equal height are not equal counts.
    """
    r3, r4 = load("rq3_pollution_registry.json"), load("rq4_defense_registry.json")

    def grid(reg, track):
        g = np.zeros((len(CHANNELS), len(CONSEQ)))
        for e in reg:
            c = (e.get("channel") or "").strip()
            q = canon_consequence(e.get("consequence"))
            if (e.get("regime") or "").strip() == track \
                    and c in CHANNELS and q:
                g[CHANNELS.index(c), CONSEQ.index(q)] += 1
        return g

    G = {t: (grid(r3, t), grid(r4, t)) for t in ("security", "safety")}
    vmax = max(g.max() for pair in G.values() for g in pair)
    hue = {"security": (TRACK_SEC, SEQ_SEC[1]),
           "safety": (TRACK_ML, SEQ[1])}

    # Geometry, in cell units. The count sits on a fixed baseline at the top
    # of its cell and the bar grows up from the bottom towards it, so a tall
    # bar can never reach its own label and no cell needs the number moved
    # inside it. The earlier version switched the label in or out depending
    # on bar height, which put white type on four different backgrounds and
    # collided in the cells that matter most.
    LBL_Y, BAR_Y, HMAX = -.34, .42, .60

    # one bar-drawing routine, used by the cells and by the margins. The
    # rule does not change between them: the mechanism bar is solid and the
    # fix bar is hatched, in the cells and in the totals alike.
    def pair(ax, i, j, a, d, solid, tint, scale, dedge=None):
        akw = dict(facecolor=solid, edgecolor=solid, linewidth=.4)
        dkw = dict(facecolor=tint, edgecolor=dedge or solid, linewidth=.5,
                   hatch="///")
        for v, x0, kw in ((a, -.40, akw), (d, .04, dkw)):
            if v == 0:
                continue
            h = .05 + HMAX * np.sqrt(v / scale)
            ax.add_patch(plt.Rectangle((j + x0, i + BAR_Y - h), .36, h, **kw))
            ax.text(j + x0 + (.14 if x0 < 0 else .22), i + LBL_Y,
                    str(int(v)), ha="center", va="center", fontsize=4.9,
                    color=INK)

    MI = len(CHANNELS) + 0.42   # the totals row, a gap below the grid

    # One totals column for the figure, not one per panel: a channel's total
    # is a fact about the corpus, not about a regime, so it is counted
    # across both panels and drawn once, in its own narrow panel.
    chanA = sum(G[k][0] for k in G).sum(axis=1)
    chanD = sum(G[k][1] for k in G).sum(axis=1)
    cmax = max(chanA.max(), chanD.max(), chanA.sum(), chanD.sum())

    # Laid out by hand. constrained_layout measures the rotated consequence
    # labels as part of each axes and shrinks the axes until they fit inside
    # its cell, which left the two panels at a fifth of the figure width
    # with a canyon between them. savefig's tight bbox still catches the
    # overhang, so the labels are not clipped.
    fig, axes = plt.subplots(1, 3, figsize=(FULL, 4.35),
                             gridspec_kw={"width_ratios": [6, 6, 1.15]})
    fig.subplots_adjust(left=0.082, right=0.995, top=0.945, bottom=0.215,
                        wspace=0.07)
    for ax, (track, (A, D)) in zip(axes[:2], G.items()):
        col, pale = hue[track]
        for i in range(len(CHANNELS)):
            for j in range(len(CONSEQ)):
                a, d = int(A[i, j]), int(D[i, j])
                # a hairline cell boundary, not a filled wash: the grid has
                # to be findable without putting a shade behind every number
                ax.add_patch(plt.Rectangle((j - .47, i - .47), .94, .94,
                                           facecolor="none", edgecolor=INK,
                                           linewidth=.2))
                if a == 0 and d == 0:
                    continue
                if d == 0:
                    ax.add_patch(plt.Rectangle((j - .47, i - .47), .94, .94,
                                               fill=False, edgecolor=INK,
                                               linewidth=1.4))
                # Mechanisms take the full regime hue; fixes a pale tint of
                # the same hue AND a hatch, so the pair separates by texture
                # as well as by value and survives a greyscale print. An
                # unfilled bar was tried and rejected: a thin rectangle is
                # already how this figure marks a cell with no fix in it.
                pair(ax, i, j, a, d, col, pale, vmax)

        # the totals row, a gap below the grid so it cannot be read as a
        # tenth channel, scaled against its own maximum
        rmax = max(A.sum(axis=0).max(), D.sum(axis=0).max())
        for j in range(len(CONSEQ)):
            ax.add_patch(plt.Rectangle((j - .47, MI - .47), .94, .94,
                                       facecolor="none", edgecolor=INK,
                                       linewidth=.2))
            pair(ax, MI, j, A[:, j].sum(), D[:, j].sum(), ALT_B, ALT_A,
             rmax, dedge=SEQ_ALT[7])
        if track == "security":
            ax.text(-.62, MI, "all channels", ha="right", va="center",
                    fontsize=6, color=INK)
        ax.set_xlim(-.6, len(CONSEQ) - .4)
        ax.set_ylim(MI + .6, -.6)
        ax.set_xticks(range(len(CONSEQ)))
        # Rotated, and the hyphen kept. Two flat lines collided whatever
        # the size, because "reasoning-corruption" is wider than its column
        # once the margins have taken their share of the width; shrinking
        # until it fit put the axis labels below five point.
        ax.set_xticklabels(CONSEQ, fontsize=5.4, rotation=32,
                           ha="right", rotation_mode="anchor")
        ax.set_yticks(range(len(CHANNELS)))
        ax.set_yticklabels(CHANNELS if track == "security" else [], fontsize=6.5)
        ax.set_title("security regime" if track == "security"
                     else "safety regime",
                     fontsize=7.5, color=col)
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.tick_params(length=0)

    mg = axes[2]
    for i in range(len(CHANNELS)):
        mg.add_patch(plt.Rectangle((-.47, i - .47), .94, .94,
                                   facecolor="none", edgecolor=INK,
                                   linewidth=.2))
        pair(mg, i, 0, chanA[i], chanD[i], ALT_B, ALT_A, cmax,
             dedge=SEQ_ALT[7])
    mg.add_patch(plt.Rectangle((-.47, MI - .47), .94, .94, facecolor="none",
                               edgecolor=INK, linewidth=.2))
    pair(mg, MI, 0, chanA.sum(), chanD.sum(), ALT_B, ALT_A, cmax,
         dedge=SEQ_ALT[7])
    # the cell spans -.47 to .47, so an upper limit of .4 clipped its right
    # edge; the panel is one cell wide and needs room for all of it
    mg.set_xlim(-.6, .6)
    mg.set_ylim(MI + .6, -.6)
    mg.set_xticks([0])
    mg.set_xticklabels(["both regimes"], fontsize=5.4, rotation=32,
                       ha="right", rotation_mode="anchor")
    mg.set_yticks([])
    for sp in mg.spines.values():
        sp.set_visible(False)
    mg.tick_params(length=0)

    axes[0].legend(handles=[
        # the legend sits under the security panel, so it speaks in that
        # panel's hue; the safety panel uses the same two treatments in blue
        Patch(facecolor=TRACK_SEC, edgecolor=TRACK_SEC, linewidth=.4,
              label="named mechanisms"),
        Patch(facecolor=SEQ_SEC[1], edgecolor=TRACK_SEC, hatch="///",
              linewidth=.5, label="named fixes"),
        Patch(facecolor=ALT_B, edgecolor=ALT_B, linewidth=.4,
              label="all mechanisms"),
        Patch(facecolor=ALT_A, edgecolor=SEQ_ALT[7], hatch="///",
              linewidth=.5, label="all fixes")],
        fontsize=6, frameon=False, loc="lower left",
        bbox_to_anchor=(0, -.30), ncol=4, columnspacing=1.0)
    save(fig, "fig1_cube")


# ---------------------------------------------------------------- figure 10
def fig_intervention():
    """Where each regime's defenses intervene.

    This was a four-row table. The claim it carries is a shape -- security
    stops the text getting in and contains what it does, safety reasons
    better about text already accepted -- and a shape is what a reader takes
    from a bar and has to assemble from a column of digits.

    Regime takes the regime hues, exactly as the cube panels and the
    citation graph do. Hue alone does not survive a greyscale print, so
    safety also carries a texture. It is a dot, not the cube's diagonal:
    there a hatch means "fix", and every bar in this figure is a fix
    already, so reusing the same glyph for "safety" would give one texture
    two jobs three pages apart. Position is the third cue -- security is the
    upper bar of every pair, in every group.
    """
    r4 = load("rq4_defense_registry.json")
    POINTS = ["ingestion", "execution", "reasoning", "none"]
    c = collections.Counter(((e.get("defense_intervention_point") or "none"),
                             (e.get("regime") or "").strip()) for e in r4)
    y = np.arange(len(POINTS))[::-1]
    h = 0.38
    fig, ax = plt.subplots(figsize=(COL, 1.75), constrained_layout=True)
    for off, reg, col, hatch in ((h / 2, "security", TRACK_SEC, None),
                                 (-h / 2, "safety", TRACK_ML, "....")):
        vals = [c[(p, reg)] for p in POINTS]
        # the hatch is drawn in the edge colour, so white dots over the full
        # regime hue: the bar keeps its weight and the texture reads in
        # greyscale, where a pale tint would instead read as a smaller value.
        ax.barh(y + off, vals, h, color=col,
                edgecolor="#ffffff" if hatch else col,
                hatch=hatch, linewidth=.3, label=reg)
        for yy, v in zip(y + off, vals):
            ax.text(v + 3, yy, str(v), va="center", fontsize=6, color=INK)
    ax.set_yticks(y)
    ax.set_yticklabels(POINTS, fontsize=6.5)
    ax.set_xlabel("named fixes")
    ax.set_xlim(0, max(c.values()) * 1.16)
    ax.legend(frameon=False, fontsize=6.5, loc="lower right")
    ax.grid(axis="x", color="#eceae6", linewidth=0.5)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    save(fig, "fig10_intervention")


# ---------------------------------------------------------------- figure 3
def fig_who_reports():
    """Reported outcome by who ran the experiment. Polarity, so diverging.

    The legend sits above the plot rather than inside it: the defense-paper
    bar runs nearly the full width, so an inset legend lands on top of data.
    """
    data = [("reported by\nattack papers", 0, 13, 24),
            ("reported by\ndefense papers", 193, 1, 0)]
    fig, ax = plt.subplots(figsize=(COL, 1.6), constrained_layout=True)
    for i, (lab, win, inc, lose) in enumerate(data):
        left = 0
        # three outcomes, three textures: the segment that used to be a grey
        # fill is now an open hatched bar, so the series separates in print
        for v, col, hat, name in ((win, ALT_A, "", "defense wins"),
                                  (inc, "white", "...", "inconclusive"),
                                  (lose, ALT_B, "///", "defense loses")):
            ax.barh(i, v, left=left, color=col, height=.5, hatch=hat,
                    edgecolor=INK, linewidth=.3,
                    label=name if i == 0 else None)
            if v >= 20:
                ax.text(left + v / 2, i, str(v), ha="center", va="center",
                        fontsize=6.5, color="white" if col != "white" else INK)
            elif v:
                # too narrow to hold the number; set it above the segment
                ax.text(left + v / 2, i + .33, str(v), ha="center",
                        va="bottom", fontsize=6.2, color=INK)
            left += v
        ax.text(left + 5, i, f"n={win+inc+lose}", va="center", fontsize=6.5,
                color=INK)
    ax.set_yticks([0, 1])
    ax.set_yticklabels([d[0] for d in data], fontsize=6.5)
    ax.set_xlim(0, 225)
    ax.set_ylim(-0.6, 1.9)
    ax.set_xlabel("(defense, attack) pairs")
    ax.legend(frameon=False, fontsize=6.2, loc="upper left",
              bbox_to_anchor=(0, 1.22), ncol=3, columnspacing=1.1,
              handlelength=1.2, handletextpad=0.5)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    ax.grid(axis="x", color="#eceae6", linewidth=0.5)
    ax.set_axisbelow(True)
    save(fig, "fig3_who_reports")


# ---------------------------------------------------------------- figure 4
def fig_dose():
    """Defended minus undefended, across poison dose. The campaign in one plot.

    Zero means the defense changed nothing. Significance is encoded per point,
    filled for Fisher p < .05 and hollow for not, which doubles as the
    secondary encoding the palette rules ask for so the lines never rely on
    hue alone.

    Fisher rather than each run's minimum detectable change: the mdr is
    computed at a 0.5 baseline and is far too conservative at the low
    accuracies these runs reach under attack. Scoring ACD's +9.2 pp at
    saturation against its 9.9 pp mdr would mark it unresolvable, when the
    exact test on the same counts gives p < 0.0001.
    """
    RUNS = [("ParamMute", "parammute_vs_corpus_poisoning.json", "base", "parammute", 5.3),
            ("CK-PLUG", "ckplug_vs_corpus_poisoning.json", "base_rag", "ck", 7.0),
            ("SpARE", "spare_vs_corpus_poisoning.json", "steer_to_use_parameter",
             "steer_to_use_context", 8.9),
            ("COIECD", "coiecd_vs_corpus_poisoning.json", "base_rag", "coiecd", 9.9),
            ("ACD", "acd_vs_corpus_poisoning.json", "rag", "acd", 9.9),
            ("SCR", "scr_vs_corpus_poisoning.json", "rag", "scr", 9.9)]
    fracs = [0.0, 0.1, 0.5, 1.0]
    MARK = ["o", "s", "^", "D", "v", "P"]
    # Every defense plotted here is an ML/AI-track method, so they share the
    # ML/AI hue and are told apart by marker, which the significance fill
    # already relies on. Six separable hues are not available once red and
    # blue are reserved for track.
    DOSE_BLUES = [SEQ[2], SEQ[3], SEQ[4], SEQ[5], SEQ[7], SEQ[9]]
    # Drawn at column width: the paper places this one in a single column, so
    # drawing it wider and letting LaTeX scale it down shrinks every label.
    fig, ax = plt.subplots(figsize=(COL, 2.6), constrained_layout=True)
    ax.axhline(0, color=INK2, linewidth=0.8, zorder=2)
    for i, (name, fn, u, d, mdr) in enumerate(RUNS):
        path = R / fn
        if not path.exists():
            continue
        rows = {(r["arm"], r["frac"]): r
                for r in json.loads(path.read_text())["results"]}
        n = rows[(d, fracs[0])]["n"]
        xs, ys, res = [], [], []
        for k, f in enumerate(fracs):
            if (d, f) in rows and (u, f) in rows:
                a, b = rows[(d, f)]["ctx_acc"], rows[(u, f)]["ctx_acc"]
                ka, kb = round(a * n / 100), round(b * n / 100)
                _, pv = fisher_exact([[ka, n - ka], [kb, n - kb]])
                xs.append(k); ys.append(a - b); res.append(pv < 0.05)
        c = DOSE_BLUES[i % len(DOSE_BLUES)]
        ax.plot(xs, ys, linewidth=1.4, color=c, label=f"{name} (n={n})",
                zorder=3)
        for x, y, r in zip(xs, ys, res):
            ax.plot(x, y, MARK[i % len(MARK)], markersize=4.2, color=c,
                    markerfacecolor=c if r else "white",
                    markeredgecolor=c, markeredgewidth=1.0, zorder=4)
    ax.set_xticks(range(len(fracs)))
    ax.set_xticklabels(["clean", "10%", "50%", "100%"])
    ax.set_xlabel("share of context replaced by the attack")
    ax.set_ylabel("defended minus undefended (pp)")
    ax.set_xlim(-0.12, len(fracs) - 0.88)
    ax.legend(frameon=False, fontsize=5.8, loc="upper center",
              bbox_to_anchor=(0.5, -0.22), ncol=3, handlelength=1.4,
              columnspacing=1.0, handletextpad=0.4)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    ax.grid(axis="y", color="#eceae6", linewidth=0.5)
    ax.set_axisbelow(True)
    save(fig, "fig4_dose_response")



# ---------------------------------------------------------------- figure 5
def fig_citation_network():
    """The two literatures as a graph. Nodes are papers, edges are citations.

    Identity, so categorical slots in fixed order, one per track. Cross-track
    edges are the claim, so they are drawn last, darker and thicker, over a
    pale same-track mesh: the figure has to answer "how many strands cross"
    and that question is unreadable if both edge classes are painted alike.

    Layout is a spring embedding on the union network (full-text pass plus the
    Semantic Scholar table), restricted to the papers that contributed a
    named technique -- the same denominator the prose quotes and the same one
    the cube uses. A survey cites widely and names nothing, so counting it
    here would measure reading habits rather than whether the two communities
    build on each other. Isolates are dropped from the drawing and reported
    in the caption instead, because a ring of unconnected dots carries no
    information and costs the layout its resolution.
    """
    import networkx as nx
    net = load("citation_network_union.json")
    hdr, rows = corpus()
    pi, ti = hdr.index("paper_id"), hdr.index("regime")
    track = {r[pi]: (r[ti] or "").strip() for r in rows}
    contrib = set()
    for fn in ("rq3_pollution_registry.json", "rq4_defense_registry.json"):
        for e in load(fn):
            if e.get("paper_id"):
                contrib.add(e["paper_id"])
    inc = set(track) & contrib

    G = nx.Graph()
    for e in net["edges"]:
        if e["citing"] in inc and e["cited"] in inc:
            G.add_edge(e["citing"], e["cited"])
    G.remove_nodes_from([n for n, d in G.degree() if d == 0])

    # Hue says regime and so does the marker shape, because this figure has
    # to be readable in a black-and-white print: red circles and blue
    # triangles stay apart at any ink budget.
    COLORS = {"security": (TRACK_SEC, "o"), "safety": (TRACK_ML, "^"),
              "Both": (CAT[3], "s")}
    # Spread the clusters. The default k packs 900 nodes into a hairball where
    # the band of cross-track edges, which is the whole point of the figure,
    # disappears into the overlap. A larger k plus more iterations separates
    # the two communities without changing the topology.
    # Lay out the giant component on its own. A small disconnected island is
    # flung to the far edge by a spring embedding and takes half the canvas
    # with it, so it is placed by hand below the mass instead.
    comps = sorted(nx.connected_components(G), key=len, reverse=True)
    giant = G.subgraph(comps[0])
    pos = nx.spring_layout(giant, seed=11,
                           k=7.0 / max(giant.number_of_nodes() ** 0.5, .1),
                           iterations=400)
    xs = [p[0] for p in pos.values()]; ys = [p[1] for p in pos.values()]
    island = [n for c in comps[1:] for n in c]
    for i, n in enumerate(island):
        pos[n] = ((min(xs) + max(xs)) / 2 + (i - (len(island) - 1) / 2) * 0.035,
                  min(ys) - 0.09)

    same, cross = [], []
    for u, v in G.edges():
        (cross if track.get(u) != track.get(v) else same).append((pos[u], pos[v]))

    fig, ax = plt.subplots(figsize=(FULL * 0.56, 4.05))
    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    from matplotlib.collections import LineCollection
    # Cross-track edges concentrate between the clusters. Drawn solid they
    # merge into a black mass that reads as "heavily connected", which is the
    # opposite of the finding. Thin and semi-transparent, they read as
    # countable strands and the density still shows.
    ax.add_collection(LineCollection(same, colors="#e2e1dc", linewidths=0.18,
                                     zorder=1))
    ax.add_collection(LineCollection(cross, colors="#1a1a1a", linewidths=0.3,
                                     alpha=0.45, zorder=3))
    for tr, (col, mk) in COLORS.items():
        ns = [n for n in G if track.get(n) == tr]
        if not ns:
            continue
        # a thin surface ring keeps overlapping markers readable as separate
        # dots rather than a solid mass
        ax.scatter([pos[n][0] for n in ns], [pos[n][1] for n in ns],
                   s=9 if mk != "o" else 7, marker=mk,
                   c=col, linewidths=0.25, edgecolors="white", zorder=4,
                   label=f"{tr} ({len(ns)})")
    # The spring layout leaves the lower left of the canvas empty, so the
    # legend goes there instead of under the figure, where it cost a strip
    # of height and a three-column row the reader had to scan sideways.
    from matplotlib.lines import Line2D
    h, l = ax.get_legend_handles_labels()
    h += [Line2D([], [], color="#dcdbd6", lw=1.2),
          Line2D([], [], color="#111111", lw=1.4)]
    l += [f"same-regime citation ({len(same)})",
          f"cross-regime citation ({len(cross)})"]
    ax.legend(h, l, frameon=False, fontsize=6, loc="lower left", ncol=1,
              handlelength=1.4, handletextpad=0.5, labelspacing=0.45,
              borderaxespad=0.2)
    if island:
        cx = sum(pos[n][0] for n in island) / len(island)
        cy = sum(pos[n][1] for n in island) / len(island)
        ax.annotate("deep-research agents:\ncite neither literature",
                    (cx, cy), textcoords="offset points", xytext=(13, 0),
                    fontsize=5.6, color=INK2, ha="left", va="center",
                    arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.5,
                                    shrinkA=1, shrinkB=3))
    ax.set_axis_off()
    ax.margins(0.04)
    print(f"    network: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges, "
          f"{len(cross)} cross-track ({100*len(cross)/G.number_of_edges():.1f}%)")
    save(fig, "fig5_citation_network")


# ---------------------------------------------------------------- figure 6
def fig_transfer_matrix():
    """Who tests whose work, in the literature and in our campaign.

    Two matrices on one scale. The left is every confirmed literature pair,
    the right is what we executed. The point is the off-diagonal: the
    literature has 7 cross-community pairs in 349, and one of its two
    off-diagonal cells is empty outright.

    Magnitude, so a single-hue ramp, with the count printed in every cell
    because colour alone must not carry the number. Zero is left unfilled so
    an empty cell reads as empty rather than as dark.
    """
    import sys as _s
    _s.path.insert(0, str(REPO / "scripts"))
    from pair_tally import retrieval_runs

    tl = load("pair_timeline.json")["pairs"]
    lit = collections.Counter((r["defense_regime"], r["attack_regime"])
                              for r in tl if r["defense_regime"] in ("security", "safety")
                              and r["attack_regime"] in ("security", "safety"))

    # our own runs, keyed the same way
    DT = {"ParamMute": "safety", "CK-PLUG": "safety", "COIECD": "safety",
          "ACD": "safety", "DyPRAG": "safety", "FaithfulRAG": "safety",
          "SpARE": "safety", "SCR": "safety",
          "RobustRAG-DecodingAgg": "security", "RobustRAG-KeywordAgg": "security"}
    # The two adaptive payloads were missing here, so their pairs landed in
    # the panel's denominator and in none of its cells: the figure printed
    # "19 of 37" while the macro the prose uses said 21. They are gradient-
    # and search-optimised against the defense they face, which is the
    # security regime by definition.
    AT = {"corpus poisoning": "security", "PoisonedRAG": "security",
          "BadRAG sentiment steering": "security",
          "BadRAG denial-of-service": "security",
          "adaptive distractor": "security",
          "gradient distractor": "security",
          "false evidence": "safety", "distractor evidence": "safety",
          # Retrieval returns a genuine but unhelpful passage, with nobody
          # behind it. Missing here, its pairs sat in the denominator and in
          # no cell, which is how the adaptive payloads went wrong above.
          "misretrieval (irrelevant retrieved context)": "safety"}
    ours_pairs = {(r["defense"], r["attack"])
                  for r in retrieval_runs() if r["role"] == "transfer"}
    ours = collections.Counter((DT.get(d), AT.get(a)) for d, a in ours_pairs)

    TR = ["security", "safety"]
    # Each cell mixes a defense track with an attack track, so no single track
    # hue fits: magnitude takes the off-track ramp and the axes keep the
    # track colours.
    cmap = LinearSegmentedColormap.from_list("alt", SEQ_ALT)
    # One column, not two. At text width the 2x2 grid had nothing to fill
    # the space with but type, so its numbers were set larger than the body
    # text around them and the figure read as a poster.
    # Two separate files, one panel each. They used to share a figure, which
    # meant one of the two sections had to cite a float three sections away;
    # the panels never shared a colour scale anyway, so nothing is lost by
    # separating them.
    panels = [("fig6a_transfer_lit", lit), ("fig6b_transfer_ours", ours)]
    for name, data in panels:
        tot = sum(data.values())
        fig, ax = plt.subplots(figsize=(COL * 0.58, 1.55),
                               constrained_layout=True)
        M = np.array([[data.get((d, a), 0) for a in TR] for d in TR], float)
        # colour is each cell's SHARE of its own panel, not its raw count.
        # Shading two panels whose totals differ by an order of magnitude on
        # independent count scales made 262 and 16 the same navy, which is the
        # one comparison a reader takes from this figure. Share is the
        # quantity that is actually comparable; the count is printed on top.
        S = M / max(tot, 1)
        vmax = 1.0
        ax.imshow(np.where(M > 0, S, np.nan), cmap=cmap, vmin=0, vmax=vmax)
        ax.set_xticks(range(2)); ax.set_xticklabels(TR, fontsize=5.4)
        ax.set_yticks(range(2)); ax.set_yticklabels(TR, fontsize=5.4)
        for lbls in (ax.get_xticklabels(), ax.get_yticklabels()):
            for lbl, t in zip(lbls, TR):
                lbl.set_color(TRACK_SEC if t == "security" else TRACK_ML)
        ax.set_xlabel("attack from", fontsize=5.6)
        ax.set_ylabel("defense from", fontsize=5.6)
        # No title. Which panel this is, and its cross-community share, are
        # said once in the caption instead of twice on the page -- and the
        # caption can use the macros, so the share cannot drift from the
        # prose that quotes it.
        for i in range(2):
            for j in range(2):
                v = int(M[i, j])
                dark = v > 0 and S[i, j] > 0.55 * vmax
                ax.text(j, i, str(v), ha="center", va="center",
                        fontsize=7.5, fontweight="bold",
                        color="#ffffff" if dark else INK)
                if v == 0:
                    ax.text(j, i + 0.3, "never tested", ha="center",
                            va="center", fontsize=4.6, color=INK)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_xticks(np.arange(-.5, 2, 1), minor=True)
        ax.set_yticks(np.arange(-.5, 2, 1), minor=True)
        ax.grid(which="minor", color="#ffffff", linewidth=2)
        ax.tick_params(which="minor", length=0)
    # the 2x2 covers the two pure tracks only. Pairs where either side is a
    # "Both"-track paper cannot answer a cross-community question, so they are
    # excluded here; the full tally including them is in pair_timeline.json.
        save(fig, name)
    _all = len(tl)
    print(f"    transfer matrix: literature {sum(lit.values())} of {_all} pairs "
          f"(pure tracks only), ours {sum(ours.values())}")


# ---------------------------------------------------------------- figure 7
def fig_lag():
    """How far apart in time a defense and the attack it was tested on are.

    Polarity around zero, so a diverging pair with a neutral midpoint: bars
    left of zero are defenses that existed before the attack, bars right are
    defenses built after it. One axis, counts only.
    """
    tl = load("pair_timeline.json")["pairs"]
    g = collections.Counter(r["gap_years"] for r in tl)
    ks = sorted(g)
    vals = [g[k] for k in ks]
    # Zero has no polarity, so it gets no fill. An open bar reads as the
    # midpoint without a third shade standing in for one.
    cols = ["none" if k == 0 else (ALT_A if k < 0 else ALT_B) for k in ks]
    edges = [INK for k in ks]
    widths = [0.8 if k == 0 else 0.4 for k in ks]
    fig, ax = plt.subplots(figsize=(COL, 1.8))
    hats = ["" if k < 0 else ("" if k == 0 else "///") for k in ks]
    bars = ax.bar(ks, vals, color=cols, edgecolor=edges, linewidth=widths,
                  width=0.78)
    for b, hh in zip(bars, hats):
        b.set_hatch(hh)
    for k, v in zip(ks, vals):
        ax.text(k, v + 1.5, str(v), ha="center", fontsize=6.5, color=INK2)
    ax.axvline(-0.5, color=MUTED, lw=0.6, ls=":")
    n_before = sum(v for k, v in g.items() if k < 0)
    ax.set_xlabel("defense year minus attack year")
    ax.set_ylabel("pairs")
    ax.set_xticks(ks)
    ax.set_ylim(0, max(vals) * 1.22)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.annotate(f"{n_before} defenses\npredate the\nattack they met",
                xy=(-2.42, max(vals) * 0.62), fontsize=6.0, color=ALT_A,
                ha="left")
    print(f"    lag: {n_before} of {len(tl)} defenses predate their attack")
    save(fig, "fig7_lag")


# ---------------------------------------------------------------- figure 8
VOCAB = [
    ("The content that gets in", "attack,\nattack technique",
     "mechanism,\ndegradation mechanism"),
    ("Who placed it", "an adversary,\nmodeled explicitly",
     "nobody; a property\nof the pipeline"),
    ("The countermeasure", "defense, mitigation", "fix, method"),
    ("What success means", "the adversary fails", "accuracy rises"),
    ("Evaluation style", "worst case", "average case"),
]


def fig_vocab():
    """The same slots, named twice. Replaces the old tab:vocab."""
    from matplotlib.patches import FancyBboxPatch

    nl = [max(s.count("\n"), m.count("\n")) + 1 for _, s, m in VOCAB]
    head_in = 0.30
    strip_in = 0.155
    pad_in = 0.085
    line_in = 0.125
    gap_in = 0.075
    rows_in = [strip_in + 2 * pad_in + n * line_in for n in nl]
    H = head_in + sum(rows_in) + gap_in * (len(VOCAB) - 1) + 0.04

    fig = plt.figure(figsize=(COL, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1); ax.set_ylim(0, H)
    ax.axis("off")

    LX0, LX1 = 0.015, 0.487
    RX0, RX1 = 0.513, 0.985
    SEC, ML = TRACK_SEC, TRACK_ML

    # column headers, each with its own colour bar: identity is never
    # carried by colour alone.
    y = H - 0.115
    for x0, x1, lab, col in ((LX0, LX1, "SECURITY", SEC),
                             (RX0, RX1, "MACHINE LEARNING", ML)):
        ax.text((x0 + x1) / 2, y + 0.035, lab, ha="center", va="bottom",
                fontsize=6.8, color=INK, fontweight="bold")
        ax.plot([x0, x1], [y, y], color=col, lw=1.8,
                solid_capstyle="butt", clip_on=False)

    top = H - head_in
    for (slot, sec, ml), nlines, rh in zip(VOCAB, nl, rows_in):
        bot = top - rh
        # the shared slot: a hairline rule across both columns, with the
        # slot name sitting on it. A filled band here was decoration -- the
        # rule already says "this spans both".
        ax.plot([LX0, RX1], [top - strip_in, top - strip_in],
                color=MUTED, lw=0.5, solid_capstyle="butt", clip_on=False)
        ax.text((LX0 + RX1) / 2, top - strip_in / 2, slot, ha="center",
                va="center", fontsize=6.5, color=INK2, style="italic")

        bh = rh - strip_in
        for x0, x1, txt, col in ((LX0, LX1, sec, SEC), (RX0, RX1, ml, ML)):
            ax.add_patch(FancyBboxPatch(
                (x0, bot), x1 - x0, bh - 0.02,
                boxstyle="round,pad=0,rounding_size=0.006",
                facecolor="white", edgecolor=MUTED, linewidth=0.5,
                mutation_aspect=0.35))
            ax.plot([x0, x0], [bot, bot + bh - 0.02], color=col, lw=1.6,
                    solid_capstyle="butt")
            ax.text((x0 + x1) / 2, bot + (bh - 0.02) / 2, txt, ha="center",
                    va="center", fontsize=6.6, color=INK, linespacing=1.35)
        top = bot - gap_in

    save(fig, "fig8_vocab")


if __name__ == "__main__":
    fig_cube(); fig_who_reports(); fig_dose()
    fig_citation_network(); fig_transfer_matrix(); fig_lag()
    fig_intervention()
    fig_vocab()
    print("done")

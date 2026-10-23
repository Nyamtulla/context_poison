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
# "magnitude" and "track" in the same figure.
SEQ_SEC = ["#fbdcd3", "#f6b9a8", "#ef947c", "#e76f52", "#d6452a", "#bf3d25",
           "#ab361f", "#95301b", "#812814", "#6b1f0d"]
SEQ_NEUTRAL = ["#f0efec", "#dcdbd7", "#c6c5c0", "#aeada8", "#969590",
               "#7e7d78", "#666561", "#4e4d4a", "#383734", "#232220"]
# Hues for distinctions that are NOT track. Red and blue are spoken for.
ALT_A, ALT_B, ALT_C = "#1baf7a", "#eda100", "#8a5a2b"
GREY_MID = "#f0efec"
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
    "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.labelcolor": INK,
    "figure.dpi": 200,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
    "pdf.fonttype": 42,
})

CHANNELS = ["direct-input", "tool-output", "RAG", "memory", "multi-agent",
            "cross-modal", "tool-metadata", "skill", "supply-chain"]
# availability-loss was added to the scheme on 2026-10-21 and to
# gen_paper_numbers.py the same day, but not here, so every figure keyed on
# CONSEQ silently dropped a column and the entries coded to it vanished from
# the cube. Keep this list identical to CQS in gen_paper_numbers.py.
CONSEQ = ["goal-hijack", "reasoning-corruption", "silent-corruption",
          "data-exfiltration", "persistence-backdoor", "resource-abuse",
          "availability-loss"]


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
    A cell holding attacks and no defense at all is outlined.
    """
    r3, r4 = load("rq3_pollution_registry.json"), load("rq4_defense_registry.json")

    def grid(reg, track):
        g = np.zeros((len(CHANNELS), len(CONSEQ)))
        for e in reg:
            c = (e.get("channel") or "").strip()
            q = (e.get("consequence") or "").strip()
            if (e.get("track") or "").strip() == track \
                    and c in CHANNELS and q in CONSEQ:
                g[CHANNELS.index(c), CONSEQ.index(q)] += 1
        return g

    G = {t: (grid(r3, t), grid(r4, t)) for t in ("Security", "ML/AI")}
    vmax = max(g.max() for pair in G.values() for g in pair)
    hue = {"Security": (TRACK_SEC, SEQ_SEC[0]), "ML/AI": (TRACK_ML, SEQ[0])}

    fig, axes = plt.subplots(1, 2, figsize=(FULL, 3.9), constrained_layout=True)
    for ax, (track, (A, D)) in zip(axes, G.items()):
        solid, pale = hue[track]
        for i in range(len(CHANNELS)):
            for j in range(len(CONSEQ)):
                a, d = int(A[i, j]), int(D[i, j])
                ax.add_patch(plt.Rectangle((j - .47, i - .47), .94, .94,
                                           facecolor="#f7f6f3",
                                           edgecolor="none"))
                if a == 0 and d == 0:
                    continue
                if d == 0:
                    ax.add_patch(plt.Rectangle((j - .43, i - .43), .86, .86,
                                               fill=False, edgecolor=INK,
                                               linewidth=.9))
                for v, x0, kw in ((a, -.40, dict(facecolor=solid,
                                                 edgecolor="none")),
                                  (d, .04, dict(facecolor=pale,
                                                edgecolor=solid, hatch="////",
                                                linewidth=.3))):
                    if v == 0:
                        continue
                    # floor, so one entry is a visible bar and not a hairline
                    h = .06 + .74 * np.sqrt(v / vmax)
                    ax.add_patch(plt.Rectangle((j + x0, i + .40 - h), .36, h,
                                               **kw))
                    # The count, inside the bar once it is tall enough to
                    # hold it and just above the bar when it is not. Reading
                    # a sqrt-scaled bar off its height is guesswork; the
                    # number is what a reader actually quotes.
                    inside = h > .30
                    ax.text(j + x0 + .18,
                            i + .40 - h + (.14 if inside else -.05),
                            str(v), ha="center",
                            va="center" if inside else "bottom",
                            fontsize=4.6,
                            color=("white" if (inside and kw["facecolor"]
                                               == solid) else INK))
        ax.set_xlim(-.6, len(CONSEQ) - .4)
        ax.set_ylim(len(CHANNELS) - .4, -.6)
        ax.set_xticks(range(len(CONSEQ)))
        # Two lines and no hyphen: at 6pt with the hyphen kept,
        # "silent-corruption" and "data-exfiltration" ran into each other.
        ax.set_xticklabels([c.replace("-", "\n") for c in CONSEQ],
                           fontsize=5.4, linespacing=1.15)
        ax.set_yticks(range(len(CHANNELS)))
        ax.set_yticklabels(CHANNELS if track == "Security" else [], fontsize=6.5)
        ax.set_title("security regime" if track == "Security"
                     else "safety regime",
                     fontsize=7.5, color=solid)
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.tick_params(length=0)

    axes[0].legend(handles=[
        Patch(facecolor="#8e8d88", edgecolor="none", label="named attacks"),
        Patch(facecolor="#e6e5e1", edgecolor="#8e8d88", hatch="////",
              linewidth=.3, label="named defenses")],
        fontsize=6, frameon=False, loc="lower left",
        bbox_to_anchor=(0, -.22), ncol=2)
    save(fig, "fig1_cube")


# ---------------------------------------------------------------- figure 2
def fig_channel_gap():
    """Named mechanisms against named defenses, per channel.

    Two categorical series, fixed slot order, sorted by the ratio so the
    under-served channels fall to the bottom where the claim is.
    """
    r3, r4 = load("rq3_pollution_registry.json"), load("rq4_defense_registry.json")
    m = collections.Counter(e.get("channel") for e in r3)
    d = collections.Counter(e.get("channel") for e in r4)
    order = sorted(CHANNELS, key=lambda c: (d[c] / m[c]) if m[c] else 0)
    y = np.arange(len(order))
    h = 0.38
    fig, ax = plt.subplots(figsize=(COL, 2.5), constrained_layout=True)
    ax.barh(y + h / 2, [m[c] for c in order], h, label="named mechanisms",
            color=ALT_A)
    ax.barh(y - h / 2, [d[c] for c in order], h, label="named defenses",
            color=ALT_B)
    for i, c in enumerate(order):
        ratio = (d[c] / m[c]) if m[c] else 0
        ax.text(max(m[c], d[c]) + 4, i, f"{ratio:.1f}x", va="center",
                fontsize=6, color=INK2)
    ax.set_yticks(y)
    ax.set_yticklabels(order, fontsize=6.5)
    ax.set_xlabel("count")
    ax.set_xlim(0, 200)
    ax.legend(frameon=False, loc="lower right", fontsize=6.5)
    ax.grid(axis="x", color="#eceae6", linewidth=0.5)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    save(fig, "fig2_channel_gap")


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
        for v, col, name in ((win, ALT_A, "defense wins"),
                             (inc, "#d8d7d2", "inconclusive"),
                             (lose, ALT_C, "defense loses")):
            ax.barh(i, v, left=left, color=col, height=.5,
                    label=name if i == 0 else None)
            if v >= 8:
                ax.text(left + v / 2, i, str(v), ha="center", va="center",
                        fontsize=6.5, color="white" if col != "#d8d7d2" else INK2)
            left += v
        ax.text(left + 5, i, f"n={win+inc+lose}", va="center", fontsize=6.5,
                color=INK2)
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
    fig, ax = plt.subplots(figsize=(COL * 1.55, 2.5), constrained_layout=True)
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
    ax.legend(frameon=False, fontsize=6, loc="center left",
              bbox_to_anchor=(1.01, 0.5), handlelength=1.6)
    ax.text(len(fracs) - 1.02, 1.2, "defense helps", fontsize=6, color=INK2,
            va="bottom", ha="right")
    ax.text(len(fracs) - 1.02, -1.2, "defense hurts", fontsize=6, color=INK2,
            va="top", ha="right")
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
    Semantic Scholar table), restricted to included papers. Isolates are
    dropped from the drawing and reported in the caption instead, because a
    ring of unconnected dots carries no information and costs the layout its
    resolution.
    """
    import networkx as nx
    net = load("citation_network_union.json")
    hdr, rows = corpus()
    pi, ti = hdr.index("paper_id"), hdr.index("track")
    track = {r[pi]: (r[ti] or "").strip() for r in rows}
    inc = set(track)

    G = nx.Graph()
    for e in net["edges"]:
        if e["citing"] in inc and e["cited"] in inc:
            G.add_edge(e["citing"], e["cited"])
    G.remove_nodes_from([n for n, d in G.degree() if d == 0])

    COLORS = {"Security": TRACK_SEC, "ML/AI": TRACK_ML, "Both": CAT[3]}
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
    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.11)
    from matplotlib.collections import LineCollection
    # Cross-track edges concentrate between the clusters. Drawn solid they
    # merge into a black mass that reads as "heavily connected", which is the
    # opposite of the finding. Thin and semi-transparent, they read as
    # countable strands and the density still shows.
    ax.add_collection(LineCollection(same, colors="#e2e1dc", linewidths=0.18,
                                     zorder=1))
    ax.add_collection(LineCollection(cross, colors="#1a1a1a", linewidths=0.3,
                                     alpha=0.45, zorder=3))
    for tr, col in COLORS.items():
        ns = [n for n in G if track.get(n) == tr]
        if not ns:
            continue
        # a thin surface ring keeps overlapping markers readable as separate
        # dots rather than a solid mass
        ax.scatter([pos[n][0] for n in ns], [pos[n][1] for n in ns], s=7,
                   c=col, linewidths=0.25, edgecolors="white", zorder=4,
                   label=f"{tr} ({len(ns)})")
    ax.scatter([], [], s=0, label=" ")
    from matplotlib.lines import Line2D
    h, l = ax.get_legend_handles_labels()
    h += [Line2D([], [], color="#dcdbd6", lw=1.2),
          Line2D([], [], color="#111111", lw=1.4)]
    l += [f"same-track citation ({len(same)})",
          f"cross-track citation ({len(cross)})"]
    ax.legend(h, l, frameon=False, fontsize=6, loc="upper center",
              bbox_to_anchor=(0.5, 0.045), ncol=3, columnspacing=1.0,
              handlelength=1.4, handletextpad=0.5,
              bbox_transform=fig.transFigure)
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
    lit = collections.Counter((r["defense_track"], r["attack_track"])
                              for r in tl if r["defense_track"] in ("Security", "ML/AI")
                              and r["attack_track"] in ("Security", "ML/AI"))

    # our own runs, keyed the same way
    DT = {"ParamMute": "ML/AI", "CK-PLUG": "ML/AI", "COIECD": "ML/AI",
          "ACD": "ML/AI", "DyPRAG": "ML/AI", "FaithfulRAG": "ML/AI",
          "SpARE": "ML/AI", "SCR": "ML/AI",
          "RobustRAG-DecodingAgg": "Security", "RobustRAG-KeywordAgg": "Security"}
    AT = {"corpus poisoning": "Security", "PoisonedRAG": "Security",
          "BadRAG sentiment steering": "Security",
          "BadRAG denial-of-service": "Security",
          "false evidence": "ML/AI", "distractor evidence": "ML/AI"}
    ours_pairs = {(r["defense"], r["attack"])
                  for r in retrieval_runs() if r["role"] == "transfer"}
    ours = collections.Counter((DT.get(d), AT.get(a)) for d, a in ours_pairs)

    TR = ["Security", "ML/AI"]
    # Each cell mixes a defense track with an attack track, so no single track
    # hue fits: magnitude goes neutral and the axes carry the track colours.
    cmap = LinearSegmentedColormap.from_list("neutral", SEQ_NEUTRAL)
    fig, axes = plt.subplots(1, 2, figsize=(FULL, 2.25))
    for ax, data, title, tot in (
            (axes[0], lit, "Published literature", sum(lit.values())),
            (axes[1], ours, "This paper's campaign", sum(ours.values()))):
        M = np.array([[data.get((d, a), 0) for a in TR] for d in TR], float)
        # colour is each cell's SHARE of its own panel, not its raw count.
        # Shading two panels whose totals differ by an order of magnitude on
        # independent count scales made 262 and 16 the same navy, which is the
        # one comparison a reader takes from this figure. Share is the
        # quantity that is actually comparable; the count is printed on top.
        S = M / max(tot, 1)
        vmax = 1.0
        ax.imshow(np.where(M > 0, S, np.nan), cmap=cmap, vmin=0, vmax=vmax)
        ax.set_xticks(range(2)); ax.set_xticklabels(TR)
        ax.set_yticks(range(2)); ax.set_yticklabels(TR)
        for lbls in (ax.get_xticklabels(), ax.get_yticklabels()):
            for lbl, t in zip(lbls, TR):
                lbl.set_color(TRACK_SEC if t == "Security" else TRACK_ML)
        ax.set_xlabel("attack from"); ax.set_ylabel("defense from")
        cross = int(M[0, 1] + M[1, 0])
        ax.set_title(f"{title}\n{cross} of {int(tot)} cross-community "
                     f"({100*cross/tot:.0f}%)", fontsize=7.5)
        for i in range(2):
            for j in range(2):
                v = int(M[i, j])
                dark = v > 0 and S[i, j] > 0.55 * vmax
                ax.text(j, i, str(v), ha="center", va="center",
                        fontsize=11, fontweight="bold",
                        color="#ffffff" if dark else INK)
                if v == 0:
                    ax.text(j, i + 0.3, "never tested", ha="center",
                            va="center", fontsize=6, color=INK2)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.set_xticks(np.arange(-.5, 2, 1), minor=True)
        ax.set_yticks(np.arange(-.5, 2, 1), minor=True)
        ax.grid(which="minor", color="#ffffff", linewidth=2)
        ax.tick_params(which="minor", length=0)
    # the 2x2 covers the two pure tracks only. Pairs where either side is a
    # "Both"-track paper cannot answer a cross-community question, so they are
    # excluded here; the full tally including them is in pair_timeline.json.
    _all = len(tl)
    print(f"    transfer matrix: literature {sum(lit.values())} of {_all} pairs "
          f"(pure tracks only), ours {sum(ours.values())}")
    save(fig, "fig6_transfer_matrix")


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
    cols = [ALT_A if k < 0 else (GREY_MID if k == 0 else ALT_B) for k in ks]
    fig, ax = plt.subplots(figsize=(COL, 1.8))
    ax.bar(ks, vals, color=cols, edgecolor=MUTED, linewidth=0.4, width=0.78)
    for k, v in zip(ks, vals):
        ax.text(k, v + 1.5, str(v), ha="center", fontsize=6.5, color=INK2)
    ax.axvline(-0.5, color=MUTED, lw=0.6, ls=":")
    n_before = sum(v for k, v in g.items() if k < 0)
    ax.set_xlabel("defense year minus attack year")
    ax.set_ylabel("pairs")
    ax.set_xticks(ks)
    ax.set_ylim(0, max(vals) * 1.22)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.annotate(f"{n_before} defenses predate\nthe attack they met",
                xy=(-1.5, max(vals) * 0.82), fontsize=6.2, color=ALT_A,
                ha="center")
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
        # the shared slot: one strip spanning both columns
        ax.add_patch(FancyBboxPatch(
            (LX0, top - strip_in), RX1 - LX0, strip_in,
            boxstyle="round,pad=0,rounding_size=0.006",
            facecolor=GREY_MID, edgecolor="none", mutation_aspect=0.35))
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
    fig_cube(); fig_channel_gap(); fig_who_reports(); fig_dose()
    fig_citation_network(); fig_transfer_matrix(); fig_lag()
    fig_vocab()
    print("done")

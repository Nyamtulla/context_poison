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

REPO = pathlib.Path(__file__).resolve().parent.parent
R = REPO / "data" / "registries"
OUT = REPO / "latex" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(REPO / "scripts"))

# --- validated reference palette -------------------------------------------
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#256abf",
       "#1c5cab", "#184f95", "#104281", "#0d366b"]
GREY_MID = "#f0efec"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8984"

# acmart sigconf: 3.33in single column, 7.0in full width
COL, FULL = 3.33, 7.0

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
CONSEQ = ["goal-hijack", "reasoning-corruption", "silent-corruption",
          "data-exfiltration", "persistence-backdoor", "resource-abuse"]


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
    """Channel x consequence occupancy, split by track.

    Magnitude, so one hue light to dark. Empty cells are left unfilled and
    cross-hatched rather than painted the ramp's lightest step, because the
    paper's claim is about which cells have NO paper and that must not look
    like a small count.
    """
    hdr, rows = corpus()
    ci, qi, ti = hdr.index("channel"), hdr.index("consequence"), hdr.index("track")
    grids = {}
    for track in ("Security", "ML/AI"):
        g = np.zeros((len(CHANNELS), len(CONSEQ)))
        for r in rows:
            if (r[ti] or "") != track:
                continue
            c, q = str(r[ci] or "").strip(), str(r[qi] or "").strip()
            if c in CHANNELS and q in CONSEQ:
                g[CHANNELS.index(c), CONSEQ.index(q)] += 1
        grids[track] = g

    cmap = LinearSegmentedColormap.from_list("seq", SEQ)
    vmax = max(g.max() for g in grids.values())
    fig, axes = plt.subplots(1, 2, figsize=(FULL, 2.9), constrained_layout=True)
    for ax, (track, g) in zip(axes, grids.items()):
        masked = np.ma.masked_where(g == 0, g)
        cmap.set_bad(color="white")
        ax.imshow(masked, cmap=cmap, vmin=0, vmax=vmax, aspect="auto")
        for i in range(len(CHANNELS)):
            for j in range(len(CONSEQ)):
                v = int(g[i, j])
                if v == 0:
                    ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, fill=False,
                                               hatch="///", edgecolor="#d8d7d2",
                                               linewidth=0))
                else:
                    ax.text(j, i, v, ha="center", va="center", fontsize=6,
                            color="white" if v > vmax * .45 else INK)
        ax.set_xticks(range(len(CONSEQ)))
        ax.set_xticklabels([c.replace("-", "-\n") for c in CONSEQ], fontsize=6)
        ax.set_yticks(range(len(CHANNELS)))
        ax.set_yticklabels(CHANNELS if track == "Security" else [], fontsize=6.5)
        lab = "adversarial (Security track)" if track == "Security" else \
              "incidental (ML/AI track)"
        ax.set_title(lab, fontsize=7.5, color=INK)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.tick_params(length=0)
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
            color=CAT[0])
    ax.barh(y - h / 2, [d[c] for c in order], h, label="named defenses",
            color=CAT[1])
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
        for v, col, name in ((win, CAT[0], "defense wins"),
                             (inc, "#d8d7d2", "inconclusive"),
                             (lose, "#d6452a", "defense loses")):
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
        c = CAT[i % len(CAT)]
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

    COLORS = {"Security": CAT[0], "ML/AI": CAT[1], "Both": CAT[3]}
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


if __name__ == "__main__":
    fig_cube(); fig_channel_gap(); fig_who_reports(); fig_dose()
    fig_citation_network()
    print("done")

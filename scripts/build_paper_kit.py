"""Generate every table and figure the SoK manuscript needs, section by section.

Output layout:

    paper_kit/
      paper_kit.xlsx     one sheet per table, named S<section>_<slug>
      figures/           one PNG + PDF per figure
      README.md          index mapping paper section -> tables -> figures

Everything is computed from the live registries and result files, so a rebuild
after new data is a re-run rather than an editing pass -- the same discipline
applied to the deck.

    python3 scripts/build_paper_kit.py
"""
from __future__ import annotations
import collections, json, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
KIT = REPO / "paper_kit"
FIGS = KIT / "figures"
REG = REPO / "data/registries"

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from src import registry_source as rs

# ---- house style, matching the deck so figures and slides read as one artifact
NAVY, GOLD, TEAL, RED, AMBER, GREY = "#12253C", "#E0A458", "#1C7293", "#B54A3F", "#B57E39", "#5B6B79"
plt.rcParams.update({
    "figure.dpi": 160, "savefig.dpi": 160, "font.size": 9,
    "axes.edgecolor": "#C7CED4", "axes.labelcolor": NAVY, "text.color": NAVY,
    "xtick.color": NAVY, "ytick.color": NAVY, "axes.grid": True,
    "grid.color": "#E0E4E8", "grid.linewidth": 0.6, "axes.axisbelow": True,
    "figure.facecolor": "white", "axes.facecolor": "white",
})

TABLES: list[tuple[str, str, list, list[list]]] = []   # (sheet, caption, headers, rows)
FIGURES: list[tuple[str, str]] = []                     # (filename, caption)


def table(sheet: str, caption: str, headers: list, rows: list[list]):
    TABLES.append((sheet, caption, headers, rows))


def savefig(fig, name: str, caption: str):
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(FIGS / f"{name}.{ext}", bbox_inches="tight")
    plt.close(fig)
    FIGURES.append((name, caption))


def barh(labels, values, title, xlabel, colors=None, note=None, figsize=(7.2, None)):
    h = figsize[1] or max(2.2, 0.34 * len(labels) + 1.1)
    fig, ax = plt.subplots(figsize=(figsize[0], h))
    cols = colors or [GOLD if i == 0 else TEAL for i in range(len(labels))]
    y = range(len(labels))
    ax.barh(list(y), values, color=cols, height=0.62)
    ax.set_yticks(list(y)); ax.set_yticklabels(labels)
    ax.invert_yaxis(); ax.set_xlabel(xlabel); ax.set_title(title, loc="left", fontweight="bold")
    for i, v in enumerate(values):
        ax.text(v, i, f" {v:g}", va="center", fontsize=8)
    ax.grid(axis="y", visible=False)
    if note:
        ax.annotate(note, xy=(0, -0.16), xycoords="axes fraction", fontsize=7.5, color=GREY)
    return fig, ax


def load_excel():
    wb = openpyxl.load_workbook(REPO / "data/exports/paper_dashboard_source.xlsx", read_only=True)
    ws = wb["Papers"]
    hdr = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    i = {h: n for n, h in enumerate(hdr)}
    rows = [list(r) for r in ws.iter_rows(min_row=2, values_only=True)]
    wb.close()
    return i, rows


def jload(p, default=None):
    fp = REG / p
    return json.loads(fp.read_text()) if fp.exists() else default


def build():
    i, rows = load_excel()
    inc = [r for r in rows if r[i["screening"]] == "Include"]
    reg = rs.load_all(); st = reg["stats"]
    mech, defs_, pairs = reg["mechanisms"], reg["defenses"], reg["pairs"]
    raw3 = jload("rq3_pollution_registry.json", [])
    raw4 = jload("rq4_defense_registry.json", [])

    # =================================================== S3 METHODOLOGY
    import sqlite3
    con = sqlite3.connect(REPO / "data/context_sok.db")
    disc = con.execute("select count(*) from papers").fetchone()[0]
    auto = dict(con.execute(
        "select coalesce(screen_human,screen_auto), count(*) from papers group by 1"))
    con.close()
    funnel = [
        ["records discovered (search + snowball)", disc],
        ["auto-included by screening rule", auto.get("auto_include", 0)],
        ["needs review", auto.get("needs_review", 0)],
        ["auto-excluded", auto.get("auto_exclude", 0)],
        ["curated corpus (in workbook)", len(rows)],
        ["INCLUDED after full-text screening", len(inc)],
        ["excluded with cause", len(rows) - len(inc)],
        ["with full text read", sum(1 for r in inc if r[i["technical_summary"]])],
    ]
    table("S3_corpus_funnel", "Corpus funnel, discovery to inclusion", ["stage", "papers"], funnel)

    eg = collections.Counter(r[i["evidence_grade"]] for r in inc if r[i["evidence_grade"]])
    table("S3_evidence_grade", "Evidence grade (publication rigor) of included papers",
          ["grade", "meaning", "papers", "share_%"],
          [[g, {"A": "peer-reviewed + artifacts", "B": "peer-reviewed",
                "C": "credible preprint", "D": "gray literature"}.get(g, ""), n,
            round(100 * n / len(inc), 1)] for g, n in sorted(eg.items())])

    fig, ax = plt.subplots(figsize=(7.0, 3.0))
    lbl = [f[0] for f in funnel[::-1]]; val = [f[1] for f in funnel[::-1]]
    ax.barh(range(len(lbl)), val, color=[GOLD if "INCLUDED" in l else TEAL for l in lbl], height=0.6)
    ax.set_yticks(range(len(lbl))); ax.set_yticklabels(lbl, fontsize=8)
    ax.set_xscale("log"); ax.set_xlabel("papers (log scale)")
    ax.set_title("Corpus funnel", loc="left", fontweight="bold")
    for k, v in enumerate(val):
        ax.text(v, k, f" {v:,}", va="center", fontsize=7.5)
    ax.grid(axis="y", visible=False)
    savefig(fig, "fig3_1_corpus_funnel", "Corpus funnel from discovery to inclusion (log scale).")

    # =================================================== S4 TAXONOMY (RQ1)
    CH = ["tool-output", "direct-input", "RAG", "memory", "tool-metadata",
          "cross-modal", "multi-agent", "skill", "supply-chain"]
    CO = ["goal-hijack", "reasoning-corruption", "silent-corruption",
          "persistence-backdoor", "data-exfiltration", "resource-abuse"]
    intent_of = {"Security": "adversarial", "ML/AI": "incidental", "Both": "both"}
    cube = collections.Counter(
        (r[i["channel"]], intent_of.get(r[i["track"]], "unclear"), r[i["consequence"]]) for r in inc)

    ch_counts = collections.Counter(r[i["channel"]] for r in inc)
    table("S4_channel", "Papers per context channel",
          ["channel", "papers", "share_%"],
          [[c, ch_counts.get(c, 0), round(100 * ch_counts.get(c, 0) / len(inc), 1)] for c in CH])

    grid = [[c] + [cube.get((c, it, q), 0) for it in ("adversarial", "incidental", "both") for q in CO]
            for c in CH]
    table("S4_cube_full", "Channel x intent x consequence cube (paper counts)",
          ["channel"] + [f"{it[:3]}:{q}" for it in ("adversarial", "incidental", "both") for q in CO],
          grid)

    empties = [[c, it, q] for c in CH for it in ("adversarial", "incidental", "both")
               for q in CO if cube.get((c, it, q), 0) == 0]
    table("S4_empty_cells", f"Empty cells: {len(empties)} of {len(CH)*3*len(CO)}",
          ["channel", "intent", "consequence"], empties)

    fig, ax = barh(CH, [ch_counts.get(c, 0) for c in CH],
                   "RQ1  Papers per context channel", "papers")
    savefig(fig, "fig4_1_channel", "Distribution of included papers across the nine context channels.")

    fig, axes = plt.subplots(1, 3, figsize=(10.2, 3.3), sharey=True)
    for ax_, it in zip(axes, ("adversarial", "incidental", "both")):
        M = [[cube.get((c, it, q), 0) for q in CO] for c in CH]
        ax_.grid(False)          # gridlines draw over heatmap cells and obscure the values
        im = ax_.imshow(M, cmap="YlGnBu", aspect="auto")
        ax_.set_xticks(range(len(CO)))
        ax_.set_xticklabels([q.replace("-", "-\n") for q in CO], fontsize=6.5, rotation=0)
        ax_.set_title(it, fontsize=9, fontweight="bold")
        for a in range(len(CH)):
            for b in range(len(CO)):
                v = M[a][b]
                ax_.text(b, a, v if v else "·", ha="center", va="center",
                         fontsize=6.5, color="white" if v > max(1, max(map(max, M)) * 0.55) else NAVY)
    axes[0].set_yticks(range(len(CH))); axes[0].set_yticklabels(CH, fontsize=7.5)
    fig.suptitle("RQ1  The cube: channel x intent x consequence", x=0.02, ha="left", fontweight="bold")
    savefig(fig, "fig4_2_cube", "The channel x intent x consequence cube; '·' marks an empty cell.")

    # =================================================== S5 CITATION NETWORK (RQ2)
    rq2 = (REPO / "cross_citation_analysis.md").read_text()
    ab = re.search(r"Track A \(Security\) -> cites Track B \(ML/AI\) \| (\d+) \| (\d+) \| \*\*([\d.]+)%", rq2)
    ba = re.search(r"Track B \(ML/AI\) -> cites Track A \(Security\) \| (\d+) \| (\d+) \| \*\*([\d.]+)%", rq2)
    r2 = [["Security -> cites ML/AI", int(ab.group(1)), int(ab.group(2)), float(ab.group(3))],
          ["ML/AI -> cites Security", int(ba.group(1)), int(ba.group(2)), float(ba.group(3))]]
    table("S5_cross_citation", "RQ2 cross-citation rates between the two literatures",
          ["direction", "papers citing across", "papers in track", "rate_%"], r2)

    fig, ax = plt.subplots(figsize=(5.6, 2.4))
    ax.barh([r[0] for r in r2], [r[3] for r in r2], color=[GOLD, TEAL], height=0.5)
    ax.set_xlabel("% of papers citing the other literature"); ax.set_xlim(0, 100)
    ax.set_title("RQ2  Cross-citation between the two literatures", loc="left", fontweight="bold")
    for k, r in enumerate(r2):
        ax.text(r[3], k, f"  {r[3]}%  ({r[1]}/{r[2]})", va="center", fontsize=8)
    ax.grid(axis="y", visible=False)
    savefig(fig, "fig5_1_cross_citation", "Roughly nine in ten papers never cite across the divide.")
    return i, rows, inc, reg, st, mech, defs_, pairs, raw3, raw4, CH, CO


def build_rest(ctx):
    (i, rows, inc, reg, st, mech, defs_, pairs, raw3, raw4, CH, CO) = ctx

    # =================================================== S6 CENSUSES (RQ3/RQ4)
    m_tr = collections.Counter(x["track"] for x in raw3)
    table("S6_rq3_summary", "RQ3 pollution mechanism registry",
          ["dimension", "value", "mechanisms", "share_%"],
          [["track", k, v, round(100*v/len(raw3), 1)] for k, v in m_tr.most_common()]
          + [["channel", k, v, round(100*v/len(raw3), 1)]
             for k, v in collections.Counter(x["channel"] for x in raw3).most_common()]
          + [["consequence", k, v, round(100*v/len(raw3), 1)]
             for k, v in collections.Counter(x["consequence"] for x in raw3).most_common()])

    va = collections.Counter(x.get("validated_against") or "(none)" for x in raw4)
    dip = collections.Counter(x["defense_intervention_point"] for x in raw4)
    table("S6_rq4_summary", "RQ4 defense registry",
          ["dimension", "value", "defenses", "share_%"],
          [["track", k, v, round(100*v/len(raw4), 1)]
           for k, v in collections.Counter(x["track"] for x in raw4).most_common()]
          + [["intervention point", k, v, round(100*v/len(raw4), 1)] for k, v in dip.most_common()]
          + [["validated against", k, v, round(100*v/len(raw4), 1)] for k, v in va.most_common()])

    fig, ax = barh([k for k, _ in collections.Counter(x["channel"] for x in raw3).most_common()],
                   [v for _, v in collections.Counter(x["channel"] for x in raw3).most_common()],
                   f"RQ3  {len(raw3)} named mechanisms by channel", "mechanisms")
    savefig(fig, "fig6_1_rq3_channel", "Named pollution mechanisms per channel.")

    fig, ax = plt.subplots(figsize=(6.2, 2.6))
    ks = ["adversarial", "incidental", "both"]
    vs = [va.get(k, 0) for k in ks]
    ax.barh(ks, vs, color=[TEAL, TEAL, GOLD], height=0.52)
    ax.set_xlabel("defenses"); ax.set_title(
        f"RQ4  What each of {len(raw4)} defenses was validated against", loc="left", fontweight="bold")
    for k, v in enumerate(vs):
        ax.text(v, k, f"  {v} ({100*v/len(raw4):.1f}%)", va="center", fontsize=8)
    ax.grid(axis="y", visible=False)
    savefig(fig, "fig6_2_rq4_validated",
            "Only 2.8% of defenses were validated against both threat models.")

    # =================================================== S7 COVERAGE (RQ5)
    table("S7_coverage_headline", "RQ5 coverage headline",
          ["metric", "value"],
          [["named mechanisms", len(mech)],
           ["named defenses", st["n_defenses"]],
           ["confirmed defense x mechanism pairs", st["n_pairs"]],
           ["defenses with >=1 confirmed match", st["n_defenses_matched"]],
           ["defenses with >=1 match (%)", round(100*st["n_defenses_matched"]/st["n_defenses_total"], 1)],
           ["mechanisms with >=1 defense", st["n_mechs_covered"]],
           ["mechanisms with ZERO defenses", st["n_mechs_uncovered"]],
           ["cross-track pairs", sum(1 for p in pairs if p.get("cross_track"))]])

    gap = []
    for dim in ("track", "channel", "consequence"):
        agg = collections.defaultdict(lambda: [0, 0])
        for m in mech:
            a = agg[m[dim]]; a[1] += 1; a[0] += 1 if m["has_any_defense"] else 0
        for k, (cov, tot) in sorted(agg.items(), key=lambda x: -x[1][1]):
            gap.append([dim, k, cov, tot - cov, tot, round(100*cov/tot, 1)])
    table("S7_coverage_gaps", "RQ5 coverage by track, channel and consequence",
          ["dimension", "value", "covered", "uncovered", "total", "covered_%"], gap)

    top = sorted(mech, key=lambda m: -m["n_defenses_tested"])[:12]
    mass = sum(m["n_defenses_tested"] for m in mech) or 1
    table("S7_concentration", "Where defense-testing effort concentrates",
          ["mechanism", "defenses tested", "share of all pairs_%"],
          [[m["mechanism_name"], m["n_defenses_tested"], round(100*m["n_defenses_tested"]/mass, 1)]
           for m in top])
    table("S7_uncovered", f"The {st['n_mechs_uncovered']} mechanisms with no defense ever tested",
          ["mechanism", "track", "channel", "consequence"],
          [[m["mechanism_name"], m["track"], m["channel"], m["consequence"]]
           for m in mech if not m["has_any_defense"]])

    fig, ax = barh([m["mechanism_name"][:42] for m in top[:10]],
                   [m["n_defenses_tested"] for m in top[:10]],
                   "RQ5  Testing concentrates on a handful of targets", "distinct defenses tested",
                   note=f"{st['n_mechs_uncovered']} mechanisms have none.")
    savefig(fig, "fig7_1_concentration",
            "One umbrella mechanism absorbs most testing; 131 mechanisms absorb none.")

    ch_gap = [g for g in gap if g[0] == "channel"]
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    labels = [g[1] for g in ch_gap]
    ax.barh(labels, [g[2] for g in ch_gap], color=TEAL, height=0.6, label="covered")
    ax.barh(labels, [g[3] for g in ch_gap], left=[g[2] for g in ch_gap],
            color=RED, height=0.6, label="no defense tested")
    ax.invert_yaxis(); ax.set_xlabel("mechanisms"); ax.legend(frameon=False, fontsize=8)
    ax.set_title("RQ5  Coverage by channel", loc="left", fontweight="bold")
    ax.grid(axis="y", visible=False)
    savefig(fig, "fig7_2_coverage_channel", "Covered vs never-defended mechanisms, by channel.")

    # =================================================== S7b FRAGMENTATION
    cen = jload("substrate_census.json")
    if cen:
        n = cen["n_mechanisms"]
        table("S7b_substrate_primary", "What each attack paper evaluated on",
              ["substrate", "mechanisms", "share_%"],
              [[k, v, round(100*v/n, 1)] for k, v in
               sorted(cen["substrate_primary"].items(), key=lambda x: -x[1])])
        table("S7b_reusability", "Could another researcher reuse that setup?",
              ["verdict", "mechanisms", "share_%"],
              [[k, v, round(100*v/n, 1)] for k, v in
               sorted(cen["reusable_substrate"].items(), key=lambda x: -x[1])])
        nsc = list(cen["named_substrate_counts"].items())[:15]
        table("S7b_top_substrates", "Most-reused evaluation substrates",
              ["substrate", "mechanisms using it", "share of mechanisms_%"],
              [[k, v, round(100*v/n, 1)] for k, v in nsc])

        by_year = collections.defaultdict(list)
        for r in cen["rows"]:
            if r.get("year"):
                by_year[r["year"]].append(r)
        yr = []
        for y in sorted(by_year):
            sub = by_year[y]
            if len(sub) < 5: continue
            no_ = sum(1 for r in sub if str(r.get("reusable_substrate")).lower() == "no")
            sh = sum(1 for r in sub if r.get("substrate_primary") == "shared_security_benchmark")
            yr.append([y, len(sub), round(100*no_/len(sub), 1), round(100*sh/len(sub), 1)])
        table("S7b_by_year", "Fragmentation over time",
              ["year", "mechanisms", "not reusable_%", "on shared security benchmark_%"], yr)

        fig, ax = barh([k for k, _ in nsc[:12]], [v for _, v in nsc[:12]],
                       f"Evaluation substrates: {cen['distinct_named_substrates']} distinct, "
                       f"{cen['substrates_used_once']} used once",
                       "mechanisms using it")
        savefig(fig, "fig7b_1_substrates",
                "The most-shared substrate covers 11.7% of attacks; 78% of substrates are used once.")

        if yr:
            fig, ax = plt.subplots(figsize=(6.4, 2.9))
            ax.plot([r[0] for r in yr], [r[3] for r in yr], "-o", color=GOLD, lw=2,
                    label="on a shared security benchmark")
            ax.plot([r[0] for r in yr], [r[2] for r in yr], "-s", color=RED, lw=2,
                    label="not reusable")
            ax.set_ylabel("% of mechanisms"); ax.set_ylim(0, 60)
            ax.legend(frameon=False, fontsize=8)
            ax.set_title("Evaluation fragmentation over time", loc="left", fontweight="bold")
            savefig(fig, "fig7b_2_fragmentation_time",
                    "Shared-benchmark use roughly halved as the field grew.")
    return ctx


def build_tail(ctx):
    (i, rows, inc, reg, st, mech, defs_, pairs, raw3, raw4, CH, CO) = ctx

    # =================================================== S8 GENERALIZATION (RQ6 + new runs)
    tt = jload("technique_transfer_chatinject.json")
    if tt:
        rowsT = tt["results"]
        atts = sorted({r["attack"] for r in rowsT})
        techs = sorted({r["technique"] for r in rowsT},
                       key=lambda t: (rowsT[[x["technique"] for x in rowsT].index(t)]["intervention_point"], t))
        grid = []
        for t in techs:
            rec = {r["attack"]: r for r in rowsT if r["technique"] == t}
            stage = next(r["intervention_point"] for r in rowsT if r["technique"] == t)
            line = [t, stage]
            for a in atts:
                r = rec.get(a)
                line.append("" if not r else
                            f"{r['undefended']['asr_pct']}%->{r['defended']['asr_pct']}% ({r['verdict'][:28]})")
            grid.append(line)
        table("S8_transfer_matrix",
              "Defense technique x attack, banking/Qwen2.5-14B, n=32, verdicts gated on detectability",
              ["technique", "stage"] + atts, grid)

        fig, ax = plt.subplots(figsize=(7.6, 3.4))
        w = 0.38
        xs = range(len(techs))
        colmap = {atts[0]: GOLD, atts[-1]: TEAL}
        for k, a in enumerate(atts):
            vals, undef = [], 0
            for t in techs:
                r = next((x for x in rowsT if x["technique"] == t and x["attack"] == a), None)
                vals.append(r["defended"]["asr_pct"] if r else 0)
                if r: undef = r["undefended"]["asr_pct"]
            ax.bar([x + k*w for x in xs], vals, width=w, color=colmap[a], label=f"{a} (defended)")
            # the undefended rate is the thing every bar should be compared against --
            # without it, a zero bar is ambiguous between "defense worked" and "nothing ran"
            ax.axhline(undef, color=colmap[a], ls="--", lw=1.2, alpha=0.85)
            ax.annotate(f"undefended {undef}%", xy=(len(techs)-0.55, undef),
                        fontsize=7, color=colmap[a], va="bottom")
        ax.set_xticks([x + w/2 for x in xs])
        ax.set_xticklabels([t.replace("_", "\n") for t in techs], fontsize=7.5)
        ax.set_ylabel("attack success rate (%)  — lower is better")
        ax.set_ylim(0, max(50, ax.get_ylim()[1]))
        ax.legend(frameon=False, fontsize=7.5, loc="upper center",
                  bbox_to_anchor=(0.5, -0.13), ncol=2)
        ax.set_title("Transfer: same defenses, two attacks differing only in framing",
                     loc="left", fontweight="bold")
        ax.annotate("Dashed line = attack with NO defense. A bar at the line means the defense did nothing.",
                    xy=(0, -0.34), xycoords="axes fraction", fontsize=7.5, color=GREY)
        savefig(fig, "fig8_1_transfer",
                "Ingestion detectors lose their effect when the attack's framing changes; "
                "the execution-stage technique does not.")

    scr = jload("v2_attack_screen_banking.json")
    if scr:
        table("S8_attack_screen_v2",
              "Attack reconstruction quality: v2 rebuilds vs the harness's own attack",
              ["attack", "ASR_%", "CI95_low", "CI95_high", "utility_%", "verdict"],
              [[r["attack"], r["asr_pct"], r["asr_ci95"][0], r["asr_ci95"][1],
                r["utility_pct"], r["verdict"]]
               for r in sorted(scr["results"], key=lambda x: -x["asr_pct"])])

    tri = jload("mechanism_triage_banking_14b.json")
    if tri:
        table("S8_representability",
              "Can the standard agent benchmark host the corpus's attacks?",
              ["attack", "ASR_%", "utility_%", "n", "verdict"],
              [[r["attack"], r["asr_pct"], r["utility_pct"], r["n_pairs"], r["verdict"]]
               for r in sorted(tri["results"], key=lambda x: -x["asr_pct"])])
        ok = [r for r in tri["results"] if r["n_pairs"] > 0 and r["attack"] != "important_instructions"]
        base = next((r for r in tri["results"] if r["attack"] == "important_instructions"), None)
        fig, ax = barh(["AgentDojo's own attack"] + [r["attack"].replace("mech_", "")[:30] for r in
                        sorted(ok, key=lambda x: -x["asr_pct"])[:12]],
                       [base["asr_pct"] if base else 0] +
                       [r["asr_pct"] for r in sorted(ok, key=lambda x: -x["asr_pct"])[:12]],
                       "0 of 16 corpus mechanisms reach a readable control", "undefended ASR (%)",
                       note="Agent utility held at ~44% throughout, so these zeros are real.")
        savefig(fig, "fig8_2_representability",
                "Corpus attacks rebuilt on the standard benchmark, undefended.")

    # =================================================== S8b DEFENSE HALF-LIFE
    hl = jload("defense_half_life.json")
    if hl:
        g = hl["gap_years"]
        dist = collections.Counter(g)
        table("S8b_half_life", "Interval from defense publication to published defeat",
              ["gap_years", "defeats", "cumulative_%"],
              [[y, dist[y], round(100*sum(dist[x] for x in dist if x <= y)/len(g), 1)]
               for y in sorted(dist)])
        table("S8b_half_life_rows", "Every datable published defeat",
              ["defense", "defense_year", "attack_year", "gap_years", "outcome"],
              [[r["defense"], r["defense_year"], r["attack_year"], r["gap_years"], r["outcome"]]
               for r in sorted(hl["rows"], key=lambda x: x["gap_years"]) if r["kind"] == "defeat"])
        fig, ax = plt.subplots(figsize=(5.6, 2.6))
        ys = sorted(dist)
        cum = [100*sum(dist[x] for x in dist if x <= y)/len(g) for y in ys]
        ax.bar([str(y) for y in ys], [dist[y] for y in ys], color=TEAL, width=0.5)
        ax2 = ax.twinx()
        ax2.plot([str(y) for y in ys], cum, "-o", color=GOLD, lw=2)
        ax2.set_ylim(0, 105); ax2.set_ylabel("cumulative %", color=GOLD)
        ax2.grid(False)
        ax.set_xlabel("years from publication to published defeat"); ax.set_ylabel("defeats")
        ax.set_title("Defense half-life", loc="left", fontweight="bold")
        savefig(fig, "fig8b_1_half_life",
                "96% of published defeats occur within one year. Heavily censored -- an upper bound.")

    # =================================================== S9 DIFFERENTIATION
    COMPARATORS = [
        (45,  "The Landscape of Prompt Injection Threats in LLM Agents", "2602.10453"),
        (44,  "SoK: The Attack Surface of Agentic AI",                    "2603.22928"),
        (39,  "SoK: Security and Safety in the Model Context Protocol",   "2512.08290"),
        (41,  "A Survey on Long-Term Memory Security in LLM Agents",      "2604.16548"),
        (1003,"Knowledge Conflicts for LLMs: A Survey",                   "2403.08319"),
    ]
    crow = []
    for rownum, title, ax_id in COMPARATORS:
        r = rows[rownum - 2]
        crow.append([title, ax_id, r[i["year"]], r[i["citation_count"]], r[i["track"]],
                     r[i["cites_track_a"]], r[i["cites_track_b"]]])
    crow.append(["THIS SoK", "-", 2026, "-", "Both", "Y", "Y"])
    table("S9_comparators", "The five closest SoKs, coded by our own scheme",
          ["paper", "arxiv", "year", "citations", "track",
           "cites security work", "cites degradation work"], crow)
    table("S9_differentiation", "What separates this SoK",
          ["dimension", "closest competitor (2602.10453)", "this SoK"],
          [["papers reviewed", 78, len(inc)],
           ["attacks catalogued", 37, len(raw3)],
           ["defenses catalogued", 41, len(raw4)],
           ["attack x defense pairs from literature", "-", st["n_pairs"]],
           ["runs own experiments", "yes (9 def x 5 atk)", "yes"],
           ["covers the incidental literature", "no", "yes"],
           ["cites across the divide", "no", "n/a (spans both)"]])

    # =================================================== S10 OPEN PROBLEMS
    s7 = jload("rq7_synthesis_stats.json")
    if s7:
        ct = s7.get("cross_track_testing", {})
        table("S10_cross_track", "RQ7 cross-track testing in the coverage matrix",
              ["metric", "value"], [[k, json.dumps(v) if isinstance(v, (dict, list)) else v]
                                     for k, v in ct.items()])
    table("S10_headline_numbers", "Every headline number, for the abstract",
          ["claim", "value"],
          [["papers screened", len(rows)],
           ["papers included", len(inc)],
           ["named attack mechanisms", len(mech)],
           ["named defenses", st["n_defenses"]],
           ["defenses validated against BOTH threat models (%)",
            round(100*sum(1 for x in raw4 if x.get("validated_against") == "both")/len(raw4), 1)],
           ["mechanisms with no defense ever tested", st["n_mechs_uncovered"]],
           ["cross-track test pairs (%)",
            round(100*sum(1 for p in pairs if p.get("cross_track"))/len(pairs), 1)],
           ["attacks whose evaluation substrate nobody can reuse (%)",
            (jload("substrate_census.json") or {}).get("not_reusable_pct", "")],
           ["distinct evaluation substrates",
            (jload("substrate_census.json") or {}).get("distinct_named_substrates", "")],
           ["substrates used by exactly one paper",
            (jload("substrate_census.json") or {}).get("substrates_used_once", "")]])


SECTION_MAP = {
    "S3": "3. Methodology", "S4": "4. Taxonomy (RQ1)", "S5": "5. Citation network (RQ2)",
    "S6": "6. Censuses (RQ3, RQ4)", "S7": "7. Coverage matrix (RQ5)",
    "S7b": "7b. Evaluation fragmentation (new)", "S8": "8. Generalization (RQ6 + new runs)",
    "S8b": "8b. Defense half-life (new)", "S9": "9. Differentiation",
    "S10": "10. Open problems (RQ7)",
}


def write_outputs():
    HDR_FILL = PatternFill("solid", fgColor="12253C")
    HDR_FONT = Font(bold=True, color="FFFFFF", size=10)
    wb = openpyxl.Workbook(); wb.remove(wb.active)

    idx = wb.create_sheet("INDEX")
    idx.append(["sheet", "paper section", "caption", "rows"])
    for c in range(1, 5):
        cell = idx.cell(1, c); cell.fill, cell.font = HDR_FILL, HDR_FONT

    for sheet, caption, headers, rws in TABLES:
        sec = SECTION_MAP.get(sheet.split("_")[0], "")
        idx.append([sheet, sec, caption, len(rws)])
        ws = wb.create_sheet(sheet[:31])
        ws.append([caption]); ws.cell(1, 1).font = Font(bold=True, size=11)
        ws.append([])
        ws.append([str(h) for h in headers])
        for c in range(1, len(headers) + 1):
            cell = ws.cell(3, c); cell.fill, cell.font = HDR_FILL, HDR_FONT
        for r in rws:
            ws.append(["" if v is None else v for v in r])
        for c in range(1, len(headers) + 1):
            width = max(12, min(52, max([len(str(headers[c-1]))] +
                       [len(str(r[c-1])) for r in rws[:200] if c-1 < len(r)] or [12]) + 2))
            ws.column_dimensions[get_column_letter(c)].width = width
        ws.freeze_panes = "A4"
    for c, w in zip("ABCD", (26, 34, 64, 8)):
        idx.column_dimensions[c].width = w
    idx.freeze_panes = "A2"
    out = KIT / "paper_kit.xlsx"
    wb.save(out)

    lines = ["# Paper kit", "",
             "Every table and figure the manuscript needs, generated from the live",
             "registries by `scripts/build_paper_kit.py`. Re-run after new data; do not",
             "hand-edit.", "",
             f"- **{len(TABLES)} tables** in `paper_kit.xlsx` (one sheet each, INDEX sheet lists them)",
             f"- **{len(FIGURES)} figures** in `figures/` as PNG and PDF", ""]
    by_sec = collections.defaultdict(list)
    for sheet, caption, _, rws in TABLES:
        by_sec[sheet.split("_")[0]].append(("T", sheet, caption, len(rws)))
    for name, caption in FIGURES:
        m = re.match(r"fig(\d+b?)_", name)
        key = "S" + (m.group(1) if m else "?")
        by_sec[key].append(("F", name, caption, ""))
    for key in sorted(by_sec, key=lambda k: (int(re.sub(r"\D", "", k) or 0), k)):
        lines.append(f"## {SECTION_MAP.get(key, key)}")
        lines.append("")
        for kind, name, caption, n in by_sec[key]:
            what = f"table `{name}` ({n} rows)" if kind == "T" else f"figure `figures/{name}.png`"
            lines.append(f"- {what} — {caption}")
        lines.append("")
    (KIT / "README.md").write_text("\n".join(lines) + "\n")

    print(f"Wrote {out}")
    print(f"  {len(TABLES)} tables, {len(FIGURES)} figures")
    for sheet, caption, headers, rws in TABLES:
        print(f"    {sheet:<28} {len(rws):>4} rows  {caption[:52]}")


if __name__ == "__main__":
    KIT.mkdir(exist_ok=True); FIGS.mkdir(exist_ok=True)
    ctx = build()
    ctx = build_rest(ctx)
    build_tail(ctx)
    write_outputs()

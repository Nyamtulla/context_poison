"""How does an agent's context go bad, and what is being done about it?

The corpus workbench (`dashboard.py`) is organised the way the project was
built: papers, registries, RQ1-RQ7. This one is organised the way the question
is actually asked. Context goes bad in a handful of distinct ways; each way has
causes, and the causes are sometimes deliberate and sometimes not; and each way
has defenses aimed at it. That is the whole structure.

Reads `data/paper_explorer.db` only. Run with:

    streamlit run context_dashboard.py
"""
from __future__ import annotations

import sqlite3

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import registry_source, scorecard

st.set_page_config(page_title="How context goes bad", layout="wide")

DB = registry_source.REPO_ROOT / "data" / "paper_explorer.db"

ADVERSARIAL = "#a4402c"
INCIDENTAL = "#2f5d7c"
MUTED = "#8d8880"

# The six ways context goes bad, in the corpus's own vocabulary, with a plain
# reading of each. Descriptions are written from what the mechanisms in each
# bucket actually do, not from the label.
WAYS = {
    "goal-hijack": (
        "The agent does someone else's task instead of yours",
        "Something in the context issues an instruction and the agent obeys it "
        "as if it came from the user. The classic case is text hidden in a web "
        "page, email or retrieved document that the agent reads and follows.",
    ),
    "reasoning-corruption": (
        "The agent reasons badly over context that is all correct",
        "Nothing is injected and nothing is false. The context is simply too "
        "long, badly ordered, or cluttered with irrelevant material, and the "
        "model stops using it properly. This is where the ML/AI literature "
        "lives — lost-in-the-middle, context rot, distraction.",
    ),
    "silent-corruption": (
        "The answer is wrong and nothing signals it",
        "Content in the context is false, stale or self-contradictory, and the "
        "agent answers confidently from it. Distinct from goal-hijack: no one "
        "gives the agent a new task, it just believes the wrong thing.",
    ),
    "persistence-backdoor": (
        "The bad content survives the session",
        "It is written into memory, a knowledge base, or a stored skill, and "
        "fires on a later run — possibly for a different user. The damage "
        "outlives the conversation that caused it.",
    ),
    "data-exfiltration": (
        "The context is used to get data out",
        "The agent is steered into leaking what it can read — conversation "
        "history, retrieved documents, credentials — usually through a tool "
        "call, a rendered URL, or an outbound message.",
    ),
    "resource-abuse": (
        "The agent is made to burn resources or refuse",
        "No data moves and no goal is hijacked. The agent is pushed into "
        "unbounded reasoning, runaway tool calls, or blanket refusal — "
        "availability rather than integrity.",
    ),
}
WAY_ORDER = list(WAYS)


@st.cache_data(ttl=300)
def load(mtime: float) -> dict:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    q = lambda s: pd.DataFrame([dict(r) for r in con.execute(s)])
    data = {
        "attacks": q("SELECT * FROM attack"),
        "defenses": q("SELECT * FROM defense"),
        "pairs": q("SELECT * FROM pair"),
        "papers": q("SELECT paper_id, title, year, venue, track, role FROM paper"),
        "untested": scorecard.optional_table(con, "untested_defense"),
    }
    con.close()
    # `track` is the project's intent proxy throughout - the RQ1 cube uses it
    # the same way. Security-track mechanisms are the deliberate ones, ML/AI
    # the incidental. Naming it here so no downstream view has to re-derive it.
    data["attacks"]["intent"] = data["attacks"]["track"].map(
        {"Security": "deliberate", "ML/AI": "incidental"}).fillna("unclear")
    return data


def way_table(d: dict) -> pd.DataFrame:
    """One row per way context goes bad, with everything aimed at it."""
    a, dfn, pairs = d["attacks"], d["defenses"], d["pairs"]
    cov = set(pairs["attack_name"])
    rows = []
    for w in WAY_ORDER:
        am = a[a["consequence"] == w]
        dm = dfn[dfn["consequence"] == w]
        rows.append({
            "way": w,
            "Plain reading": WAYS[w][0],
            "Causes (deliberate)": int((am["intent"] == "deliberate").sum()),
            "Causes (incidental)": int((am["intent"] == "incidental").sum()),
            "Causes (total)": len(am),
            "Defenses proposed": len(dm),
            "Causes with a defense tested": int(am["name"].isin(cov).sum()),
        })
    t = pd.DataFrame(rows)
    t["Never defended"] = t["Causes (total)"] - t["Causes with a defense tested"]
    t["Coverage"] = (t["Causes with a defense tested"]
                     / t["Causes (total)"].replace(0, pd.NA))
    return t


def map_tab(d: dict) -> None:
    t = way_table(d)
    st.markdown("#### The six ways context goes bad")
    st.caption(
        "Every named mechanism in the corpus lands in exactly one of these. "
        "The split between deliberate and incidental is the paper's own "
        "literature — security papers describe attacks, ML/AI papers describe "
        "failures that happen on their own."
    )

    k = st.columns(4)
    k[0].metric("Ways context goes bad", len(WAY_ORDER))
    k[1].metric("Named causes", int(t["Causes (total)"].sum()))
    k[2].metric("Defenses proposed", int(t["Defenses proposed"].sum()))
    k[3].metric("Causes never defended", int(t["Never defended"].sum()))

    single = t[(t["Causes (deliberate)"] == 0) | (t["Causes (incidental)"] == 0)]
    st.warning(
        f"**{len(single)} of the {len(t)} ways are described by only one of the "
        "two literatures.** Only *reasoning-corruption* and *silent-corruption* "
        "have both deliberate and incidental causes on record. Everywhere else, "
        "one community owns the problem and the other has not looked at it — "
        "which is the gap this SoK exists to name.",
        icon=":material/join_left:")

    fig = go.Figure()
    fig.add_bar(y=t["way"], x=t["Causes (deliberate)"], orientation="h",
                name="deliberate causes (attacks)", marker_color=ADVERSARIAL)
    fig.add_bar(y=t["way"], x=t["Causes (incidental)"], orientation="h",
                name="incidental causes (failures)", marker_color=INCIDENTAL)
    fig.add_bar(y=t["way"], x=-t["Defenses proposed"], orientation="h",
                name="defenses proposed", marker_color=MUTED)
    fig.update_layout(
        barmode="relative", height=420, margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="← defenses proposed     |     named causes →",
        yaxis=dict(autorange="reversed"),
        legend=dict(orientation="h", y=1.12, x=0))
    st.plotly_chart(fig, width="stretch", key="way_map")

    show = t[["way", "Plain reading", "Causes (deliberate)",
              "Causes (incidental)", "Defenses proposed",
              "Causes with a defense tested", "Never defended", "Coverage"]]
    st.dataframe(
        show, width="stretch", hide_index=True,
        column_config={"Coverage": st.column_config.ProgressColumn(
            "Coverage", format="%.0f%%", min_value=0, max_value=1)})

    worst = t.loc[t["Coverage"].idxmin()]
    best_ratio = t.assign(r=t["Defenses proposed"] / t["Causes (total)"]
                          .replace(0, pd.NA))
    thin = best_ratio.loc[best_ratio["r"].idxmin()]
    st.caption(
        f"**Least defended way:** `{worst['way']}` — "
        f"{int(worst['Never defended'])} of {int(worst['Causes (total)'])} "
        f"causes have no defense ever tested against them. "
        f"**Thinnest defense effort:** `{thin['way']}` — "
        f"{int(thin['Defenses proposed'])} defenses for "
        f"{int(thin['Causes (total)'])} causes."
    )


def _cause_table(df: pd.DataFrame, cov: set, papers: pd.DataFrame) -> pd.DataFrame:
    out = df.merge(papers[["paper_id", "title", "year"]], on="paper_id", how="left")
    out["Defended?"] = out["name"].isin(cov).map({True: "yes", False: "never"})
    return (out[["name", "Defended?", "channel", "year", "title"]]
            .rename(columns={"name": "Cause", "channel": "Enters through",
                             "year": "Year", "title": "From"})
            .sort_values(["Defended?", "Cause"]))


def way_tab(d: dict) -> None:
    a, dfn, pairs = d["attacks"], d["defenses"], d["pairs"]
    cov = set(pairs["attack_name"])

    st.markdown("#### One way, in depth")
    w = st.selectbox("Way context goes bad", WAY_ORDER,
                     format_func=lambda x: f"{x} — {WAYS[x][0]}", key="way_pick")
    headline, blurb = WAYS[w]
    st.markdown(f"### {headline}")
    st.caption(blurb)

    am = a[a["consequence"] == w]
    dm = dfn[dfn["consequence"] == w]
    deliberate = am[am["intent"] == "deliberate"]
    incidental = am[am["intent"] == "incidental"]
    defended = int(am["name"].isin(cov).sum())

    k = st.columns(4)
    k[0].metric("Deliberate causes", len(deliberate))
    k[1].metric("Incidental causes", len(incidental))
    k[2].metric("Defenses proposed", len(dm))
    k[3].metric("Causes never defended", len(am) - defended)

    if len(deliberate) == 0 or len(incidental) == 0:
        missing = "incidental" if len(incidental) == 0 else "deliberate"
        st.info(
            f"No **{missing}** cause is on record for this way. Either the "
            f"{missing} version does not happen, or nobody has written it up — "
            "and the corpus cannot tell those apart. Worth stating as an open "
            "question rather than as an absence.", icon=":material/help:")

    st.markdown("##### What causes it")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**Deliberate — someone is doing this to you** ({len(deliberate)})")
        if deliberate.empty:
            st.caption("None recorded.")
        else:
            st.dataframe(_cause_table(deliberate, cov, d["papers"]),
                         width="stretch", hide_index=True, height=300)
    with c2:
        st.markdown(f"**Incidental — this happens on its own** ({len(incidental)})")
        if incidental.empty:
            st.caption("None recorded.")
        else:
            st.dataframe(_cause_table(incidental, cov, d["papers"]),
                         width="stretch", hide_index=True, height=300)

    st.markdown("##### How it gets in")
    ch = am.groupby(["channel", "intent"]).size().unstack(fill_value=0)
    if not ch.empty:
        fig = go.Figure()
        for col, colour in (("deliberate", ADVERSARIAL), ("incidental", INCIDENTAL)):
            if col in ch.columns:
                fig.add_bar(x=ch.index, y=ch[col], name=col, marker_color=colour)
        fig.update_layout(barmode="stack", height=280,
                          margin=dict(l=10, r=10, t=10, b=10),
                          yaxis_title="named causes",
                          legend=dict(orientation="h", y=1.15, x=0))
        st.plotly_chart(fig, width="stretch", key=f"chan_{w}")

    st.markdown("##### What is proposed against it")
    if dm.empty:
        st.caption("No defense in the corpus targets this way.")
    else:
        pts = dm["intervention_point"].value_counts()
        cols = st.columns(max(len(pts), 1))
        for col, (pt, n) in zip(cols, pts.items()):
            col.metric(str(pt), int(n))
        st.caption(
            "**ingestion** — inspect or rewrite content before the model sees "
            "it · **reasoning** — change how the model treats it · "
            "**execution** — check the action before it runs · "
            "**none** — the paper proposes a measure without a runtime hook."
        )
        tested = set(pairs["defense_name"])
        show = dm.copy()
        show["Ever tested?"] = show["name"].isin(tested).map(
            {True: "yes", False: "no pair confirmed"})
        st.dataframe(
            show[["name", "intervention_point", "Ever tested?",
                  "validated_against", "track"]]
            .rename(columns={"name": "Defense",
                             "intervention_point": "Acts at",
                             "validated_against": "Built for",
                             "track": "From"})
            .sort_values(["Ever tested?", "Defense"]),
            width="stretch", hide_index=True, height=340)

    st.markdown("##### What has actually been run against what")
    pw = pairs[pairs["attack_name"].isin(am["name"])]
    if pw.empty:
        st.warning(
            f"**Not one confirmed (defense, cause) pair exists for this way** — "
            f"despite {len(dm)} defenses aimed at it and {len(am)} named causes.",
            icon=":material/warning:")
    else:
        st.caption(
            f"{len(pw)} confirmed pairs. A defense paper's claim and an attack "
            "paper's result are different evidence and are shown separately.")
        st.dataframe(
            pw[["defense_name", "attack_name", "outcome", "direction",
                "reported_by_title"]]
            .rename(columns={"defense_name": "Defense", "attack_name": "Cause",
                             "outcome": "Result", "direction": "Reported by",
                             "reported_by_title": "In"})
            .sort_values("Result"), width="stretch", hide_index=True, height=320)

    never = am[~am["name"].isin(cov)]
    if not never.empty:
        with st.expander(f"{len(never)} causes of this that nobody has "
                         "tested a defense against"):
            st.dataframe(_cause_table(never, cov, d["papers"]),
                         width="stretch", hide_index=True)


def routes_tab(d: dict) -> None:
    a, dfn = d["attacks"], d["defenses"]
    st.markdown("#### How bad content gets into the context")
    st.caption(
        "The entry route, crossed with what goes wrong once it is in. Reading "
        "a row tells you what a single route can lead to; reading a column "
        "tells you every way into one kind of failure."
    )
    grid = (a.groupby(["channel", "consequence"]).size()
            .unstack(fill_value=0).reindex(columns=WAY_ORDER, fill_value=0))
    grid = grid.loc[grid.sum(axis=1).sort_values(ascending=False).index]
    fig = go.Figure(go.Heatmap(
        z=grid.values, x=grid.columns, y=grid.index,
        colorscale="Oranges", text=grid.values,
        texttemplate="%{text}", showscale=False))
    fig.update_layout(height=40 * len(grid) + 150,
                      margin=dict(l=10, r=10, t=10, b=10),
                      xaxis_title="what goes wrong", yaxis_title="how it gets in")
    st.plotly_chart(fig, width="stretch", key="routes")

    st.markdown("##### Defense effort per route, against causes per route")
    cmp = pd.DataFrame({
        "named causes": a["channel"].value_counts(),
        "defenses proposed": dfn["channel"].value_counts(),
    }).fillna(0).astype(int)
    cmp["defenses per cause"] = (cmp["defenses proposed"]
                                 / cmp["named causes"].replace(0, pd.NA)).round(2)
    cmp = cmp.sort_values("named causes", ascending=False)
    st.dataframe(cmp, width="stretch")
    worst = cmp[cmp["named causes"] >= 5].sort_values("defenses per cause")
    if not worst.empty:
        r = worst.iloc[0]
        st.caption(
            f"**Thinnest route:** `{worst.index[0]}` carries "
            f"{int(r['named causes'])} named causes and attracts "
            f"{int(r['defenses proposed'])} defenses — "
            f"{r['defenses per cause']} per cause.")


def main() -> None:
    st.title("How does an agent's context go bad?")
    if not DB.exists():
        st.error("No `data/paper_explorer.db`. Build it with "
                 "`python3 scripts/build_paper_db.py`.")
        return
    d = load(DB.stat().st_mtime)
    st.caption(
        f"{len(d['papers'])} papers · {len(d['attacks'])} named causes · "
        f"{len(d['defenses'])} defenses · {len(d['pairs'])} confirmed pairs. "
        "Context goes bad deliberately and by accident; this reads both as one "
        "question. The corpus workbench with the RQ tabs is `dashboard.py`."
    )
    tabs = st.tabs(["The six ways", "One way in depth", "How it gets in",
                    "Paper scorecard"])
    with tabs[0]:
        map_tab(d)
    with tabs[1]:
        way_tab(d)
    with tabs[2]:
        routes_tab(d)
    with tabs[3]:
        scorecard.paper_scorecard_tab()


if __name__ == "__main__":
    main()

"""Local dashboard (FR-12, NFR-5). Data source is an editable Excel workbook
(src/excel_source.py), bootstrapped once from the SQLite DB's high-confidence
pool - after that, the spreadsheet is authoritative for the dashboard: add a
row, change a Track/Screening decision, edit any metadata, refresh the page.
Citation edges still come from the DB (not something to hand-edit). Run with:

    streamlit run dashboard.py
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import confidence, db, excel_source, excel_sync, registry_source
from src.config import load_config
from src.labels import TRACK_DISPLAY_NAMES

TRACK_COLORS = {"A": "#e07a5f", "B": "#3d5a80", "Both": "#8ac926", "Unclear": "#adb5bd"}
CROSS_EDGE_COLOR = "#e63946"
SAME_EDGE_COLOR = "rgba(150,150,150,0.35)"

# Click-to-inspect uses Streamlit's own native st.plotly_chart(on_select=...)
# rather than the third-party streamlit_plotly_events package - that package
# is unmaintained (last release years ago) and silently fails to render
# against current Streamlit versions instead of erroring, which is why the
# plots were showing up blank. Native on_select also avoids shipping the
# whole figure through a separate custom-component postMessage bridge, which
# was the original source of the DataCloneError at very large data volumes.
# NETWORK_NODE_CAP is still a real compute cap independent of the above -
# spring_layout gets slow well before this many nodes.
NETWORK_NODE_CAP = 600
CLICKABLE_POINT_CAP = 3000

st.set_page_config(page_title="Context Integrity SoK — Paper Explorer", layout="wide")


@st.cache_resource
def get_config():
    return load_config()


def ensure_excel_source(excel_path, db_path, hop_scope: int) -> int:
    """Bootstrap the editable Excel data source from the DB's high-confidence
    pool (src/confidence.py) the first time the dashboard runs - never
    overwrites an existing file, since by then it may hold hand edits.
    Returns the number of papers written (0 if the file already existed)."""
    if excel_path.exists():
        return 0
    conn = db.connect(db_path)
    db.init_db(conn)  # tolerate a brand-new/empty DB file (e.g. on a fresh machine)
    config = get_config()
    ids = confidence.high_confidence_ids(conn, config, min_citations=0, max_hop=hop_scope)
    excel_source.export_to_path(conn, excel_path, ids=ids)
    conn.close()
    return len(ids)


@st.cache_data(ttl=5)
def load_excel_data(excel_path: str, mtime: float) -> pd.DataFrame:
    # `mtime` isn't used in the body - it's there so Streamlit's cache key
    # changes the moment the file is saved with new edits, instead of
    # waiting out the ttl or serving stale data.
    return excel_source.load_dataframe(excel_path)


@st.cache_data(ttl=30)
def load_edges(db_path: str) -> pd.DataFrame:
    conn = db.connect(db_path)
    db.init_db(conn)  # tolerate a brand-new/empty DB file (e.g. on a fresh machine)
    rows = [dict(r) for r in db.all_citation_edges(conn)]
    conn.close()
    return pd.DataFrame(rows, columns=["citing_paper_id", "cited_paper_id", "direction_discovered"])


def _jitter(paper_id: str, scale: float = 0.8) -> float:
    h = int(hashlib.sha1(paper_id.encode()).hexdigest()[:8], 16)
    return ((h % 1000) / 1000.0 - 0.5) * scale


def build_hover_text(sub: pd.DataFrame) -> list[str]:
    """Full-metadata hover text (title, venue, year, track, citations) for
    both the timeline and network plots - not just the paper title."""
    lines = []
    for _, row in sub.iterrows():
        year = int(row["year"]) if pd.notna(row["year"]) else "year unknown"
        venue = row.get("venue_short") or row["venue"] or "venue unknown"
        track_label = TRACK_DISPLAY_NAMES.get(row["effective_track"], row["effective_track"])
        cites = int(row["citation_count"]) if pd.notna(row["citation_count"]) else 0
        title = (row["title"] or "(untitled)").replace("<", "&lt;").replace(">", "&gt;")
        lines.append(f"<b>{title}</b><br>{venue} · {year}<br>{track_label} · {cites} citations")
    return lines


def apply_filters(df: pd.DataFrame, tracks, year_range, venues, hops, screens, keyword) -> pd.DataFrame:
    if df.empty:
        return df
    out = df[df["effective_track"].isin(tracks)]
    out = out[out["year"].between(year_range[0], year_range[1]) | out["year"].isna()]
    if venues:
        out = out[out["venue_short"].isin(venues)]
    if hops:
        out = out[out["hop"].isin(hops)]
    if screens:
        out = out[out["effective_screen"].isin(screens)]
    if keyword:
        kw = keyword.lower()
        mask = out["title"].fillna("").str.lower().str.contains(kw) | out["abstract"].fillna("").str.lower().str.contains(kw)
        out = out[mask]
    return out


def render_chart_with_optional_clicks(fig: go.Figure, point_count: int, key: str) -> list[str]:
    """Below CLICKABLE_POINT_CAP: native st.plotly_chart click selection.
    Above it: plain st.plotly_chart with no selection wiring - narrowing
    filters brings clicking back. Returns a list of clicked paper_ids (via
    each trace's customdata), not the raw Plotly event structure."""
    if point_count <= CLICKABLE_POINT_CAP:
        event = st.plotly_chart(
            fig, width="stretch", key=key, on_select="rerun", selection_mode="points"
        )
        points = (event.get("selection") or {}).get("points", []) if event else []
        paper_ids = []
        for p in points:
            cd = p.get("customdata")
            if isinstance(cd, (list, tuple)):
                cd = cd[0] if cd else None
            if cd:
                paper_ids.append(cd)
        return paper_ids
    st.plotly_chart(fig, width="stretch", key=f"{key}_static")
    st.caption(
        f"Click-to-inspect is disabled above {CLICKABLE_POINT_CAP} points ({point_count} shown) "
        "to avoid overloading the browser - narrow the sidebar filters to bring it back."
    )
    return []


def render_metadata_panel(row: pd.Series) -> None:
    st.subheader(row["title"] or "(untitled)")
    st.caption(
        f"{', '.join(row['authors']) if row['authors'] else 'Unknown authors'} · "
        f"{row.get('venue_short') or row['venue'] or 'venue unknown'} · {int(row['year']) if pd.notna(row['year']) else '?'}"
    )
    cols = st.columns(3)
    cols[0].metric("Track", TRACK_DISPLAY_NAMES.get(row["effective_track"], row["effective_track"]))
    cols[1].metric("Screening", row["effective_screen"])
    cols[2].metric("Citations", int(row["citation_count"]))
    if row.get("abstract"):
        with st.expander("Abstract", expanded=True):
            st.write(row["abstract"])
    pdf_path = row.get("pdf_local_path")
    if pdf_path and Path(pdf_path).exists():
        st.markdown(f"[Open local PDF]({pdf_path})")
    elif row.get("url"):
        st.markdown(f"[Source link]({row['url']})")
    st.caption(
        f"discovered_via={row['discovered_via']} · hop={row['hop']} · "
        f"query={row.get('discovered_query') or '—'} · seed_category={row.get('seed_category') or '—'}"
    )


def yearly_trend_chart(df: pd.DataFrame) -> go.Figure:
    """Papers per year, stacked by track - the actual trend view. Aggregate
    counts, not per-paper markers, so this stays cheap and legible at any N."""
    counts = df.dropna(subset=["year"]).groupby(["year", "effective_track"]).size().reset_index(name="count")
    fig = go.Figure()
    for track, color in TRACK_COLORS.items():
        sub = counts[counts["effective_track"] == track]
        if sub.empty:
            continue
        fig.add_trace(go.Bar(x=sub["year"], y=sub["count"], name=TRACK_DISPLAY_NAMES.get(track, track), marker_color=color))
    fig.update_layout(
        barmode="stack",
        xaxis_title="Year",
        yaxis_title="Number of papers",
        height=350,
        margin=dict(l=10, r=10, t=30, b=10),
        legend_title_text="Track",
    )
    return fig


def timeline_tab(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No papers match the current filters.")
        return

    st.plotly_chart(yearly_trend_chart(df), width="stretch", key="yearly_trend")
    n_missing_year = df["year"].isna().sum()
    if n_missing_year:
        st.caption(f"{n_missing_year} paper(s) with no year on record aren't shown in the trend chart above.")

    st.markdown("**Individual papers** — position: year (x) and citation impact (y, √ scale); size: citations; color: track. Click a point for full details.")

    plot_df = df.copy()
    # Y axis is now real (citations), not meaningless jitter - the sqrt keeps
    # a single very-highly-cited outlier from squashing everything else to
    # the bottom, and a small amount of jitter on top just declumps exact
    # ties (many recent papers legitimately sit at 0 citations).
    plot_df["citations_sqrt"] = plot_df["citation_count"].clip(lower=0) ** 0.5
    plot_df["y_value"] = plot_df["citations_sqrt"] + plot_df["paper_id"].apply(lambda p: _jitter(p, scale=0.15))
    plot_df["marker_size"] = plot_df["citations_sqrt"] * 3 + 6

    fig = go.Figure()
    for track, color in TRACK_COLORS.items():
        sub = plot_df[plot_df["effective_track"] == track]
        if sub.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=sub["year"],
                y=sub["y_value"],
                mode="markers",
                name=TRACK_DISPLAY_NAMES.get(track, track),
                marker=dict(size=sub["marker_size"], color=color, line=dict(width=0.5, color="white")),
                customdata=sub["paper_id"],
                text=build_hover_text(sub),
                hovertemplate="%{text}<extra></extra>",
            )
        )
    fig.update_yaxes(title="Citations (√ scale, jittered slightly for readability)")
    fig.update_xaxes(title="Year")
    fig.update_layout(height=500, margin=dict(l=10, r=10, t=30, b=10), legend_title_text="Track")

    clicked_ids = render_chart_with_optional_clicks(fig, len(plot_df), "timeline_events")
    if clicked_ids:
        match = df[df["paper_id"] == clicked_ids[0]]
        if not match.empty:
            render_metadata_panel(match.iloc[0])


def network_tab(df: pd.DataFrame, edges: pd.DataFrame) -> None:
    if df.empty:
        st.info("No papers match the current filters.")
        return

    scope = st.radio(
        "Network scope",
        ["Seeds only (fast, interactive)", "Full pool matching sidebar filters (static overview)"],
        index=0,
        horizontal=True,
        key="network_scope",
    )
    static_mode = scope.startswith("Full pool")

    if static_mode:
        scoped_df = df
    else:
        scoped_df = df[df["seed_category"].notna()]
        if scoped_df.empty:
            st.info("No seed papers match the current sidebar filters (they may be filtered out by track/year/screening).")
            return

    if not static_mode and len(scoped_df) > NETWORK_NODE_CAP:
        # shouldn't normally happen (there are only ~51 seeds) but stay safe if the seed list ever grows
        st.warning(f"Seed scope has {len(scoped_df)} papers, above the {NETWORK_NODE_CAP} interactive cap - showing a static view instead.")
        static_mode = True

    ids_in_view = set(scoped_df["paper_id"])
    edges_in_view = edges[edges["citing_paper_id"].isin(ids_in_view) & edges["cited_paper_id"].isin(ids_in_view)]

    G = nx.Graph()
    for _, row in scoped_df.iterrows():
        G.add_node(row["paper_id"])
    for _, e in edges_in_view.iterrows():
        G.add_edge(e["citing_paper_id"], e["cited_paper_id"])

    if G.number_of_nodes() == 0:
        st.info("Nothing to draw yet.")
        return

    # Full spring-layout physics (default 50 iterations) gets slow well before 10k nodes;
    # a coarser layout is still a perfectly usable "shape of the graph" overview.
    iterations = 15 if G.number_of_nodes() > 1000 else 50
    spinner_msg = f"Laying out {G.number_of_nodes()} papers, {G.number_of_edges()} edges..."
    if G.number_of_nodes() > 1000:
        spinner_msg += " (large graph - this can take a minute or two)"
    with st.spinner(spinner_msg):
        pos = nx.spring_layout(G, seed=42, k=1.2 / max(len(G.nodes) ** 0.5, 0.1), iterations=iterations)
    track_lookup = scoped_df.set_index("paper_id")["effective_track"].to_dict()

    same_x, same_y, cross_x, cross_y = [], [], [], []
    for u, v in G.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        if track_lookup.get(u) == track_lookup.get(v):
            same_x += [x0, x1, None]
            same_y += [y0, y1, None]
        else:
            cross_x += [x0, x1, None]
            cross_y += [y0, y1, None]

    # WebGL-accelerated markers for the large static overview; plain SVG scatter is fine (and
    # keeps click-events working) at the small interactive seeds-only scale.
    marker_cls = go.Scattergl if static_mode else go.Scatter

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=same_x, y=same_y, mode="lines", line=dict(width=1, color=SAME_EDGE_COLOR), hoverinfo="skip", showlegend=False, name="same-track"))
    fig.add_trace(go.Scatter(x=cross_x, y=cross_y, mode="lines", line=dict(width=2.5, color=CROSS_EDGE_COLOR), hoverinfo="skip", name="cross-track citation"))

    for track, color in TRACK_COLORS.items():
        node_ids = [n for n in G.nodes() if track_lookup.get(n) == track]
        if not node_ids:
            continue
        sub = scoped_df[scoped_df["paper_id"].isin(node_ids)].set_index("paper_id").loc[node_ids].reset_index()
        fig.add_trace(
            marker_cls(
                x=[pos[n][0] for n in node_ids],
                y=[pos[n][1] for n in node_ids],
                mode="markers",
                name=TRACK_DISPLAY_NAMES.get(track, track),
                marker=dict(
                    size=(sub["citation_count"].clip(lower=0) ** 0.5) * 2 + 8,
                    color=color,
                    line=dict(width=0.5, color="white"),
                ),
                customdata=node_ids,
                text=build_hover_text(sub),
                hovertemplate="%{text}<extra></extra>",
            )
        )

    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(height=650, margin=dict(l=10, r=10, t=30, b=10), legend_title_text="Track / edge type")

    st.caption(f"{G.number_of_nodes()} papers · {len(same_x)//3} same-track edges · {len(cross_x)//3} cross-track edges (highlighted)")

    if static_mode:
        st.plotly_chart(fig, width="stretch", key="network_static")
        st.caption(
            "Static overview - click-to-inspect disabled at this scale. "
            "Switch to 'Seeds only' or narrow the sidebar filters for an interactive view."
        )
        return

    clicked_ids = render_chart_with_optional_clicks(fig, G.number_of_nodes(), "network_events")
    if clicked_ids:
        match = scoped_df[scoped_df["paper_id"] == clicked_ids[0]]
        if not match.empty:
            render_metadata_panel(match.iloc[0])


# ===================================================================
# RQ3/RQ4/RQ5 registry views. These read the finished registries (via
# src/registry_source.py, shared with the MCP server), NOT the editable
# paper spreadsheet - so the sidebar's paper filters deliberately don't
# apply here; each tab carries its own filters instead.
# ===================================================================

REGISTRY_TRACK_COLORS = {"Security": "#e07a5f", "ML/AI": "#3d5a80", "Both": "#8ac926"}


@st.cache_data(ttl=30)
def load_registries(mtimes: tuple) -> dict:
    # `mtimes` isn't read in the body - it's the cache key, so editing any
    # registry file busts the cache immediately instead of waiting out the ttl.
    return registry_source.load_all()


@st.cache_data(ttl=30)
def load_rq_summaries(mtimes: tuple) -> dict:
    return {rq: registry_source.load_rq_summary(rq) for rq in registry_source.RQ_FILES}


def _registry_mtimes() -> tuple:
    paths = [registry_source.RQ3_JSON, registry_source.RQ4_JSON, registry_source.RQ5_JSON]
    paths += [fname for fname, _ in registry_source.RQ_FILES.values()]
    out = []
    for rel in paths:
        p = registry_source.REPO_ROOT / rel
        out.append(p.stat().st_mtime if p.exists() else 0.0)
    return tuple(out)


def _multiselect_filter(df: pd.DataFrame, column: str, label: str, container, key: str) -> pd.DataFrame:
    """Filter on one column, offering only values actually present, each with
    its count - and treat 'nothing selected' as 'no filter' rather than
    'show nothing', which is what people actually mean when they clear a box."""
    if column not in df.columns:
        return df
    counts = df[column].fillna("(unspecified)").value_counts()
    chosen = container.multiselect(
        label, counts.index.tolist(), format_func=lambda v: f"{v} ({counts.get(v, 0)})", key=key
    )
    if not chosen:
        return df
    return df[df[column].fillna("(unspecified)").isin(chosen)]


def _bar(counts: pd.Series, title: str, color: str = "#3d5a80", horizontal: bool = True) -> go.Figure:
    fig = go.Figure()
    if horizontal:
        fig.add_trace(go.Bar(y=counts.index.astype(str), x=counts.values, orientation="h", marker_color=color))
        fig.update_layout(yaxis=dict(autorange="reversed"), xaxis_title="Papers / entries")
    else:
        fig.add_trace(go.Bar(x=counts.index.astype(str), y=counts.values, marker_color=color))
    fig.update_layout(
        title=title, height=max(260, 28 * len(counts) + 90),
        margin=dict(l=10, r=10, t=45, b=10), showlegend=False,
    )
    return fig


def overview_tab(reg: dict, summaries: dict, n_papers: int) -> None:
    s = reg["stats"]
    st.markdown("#### Everything this project has produced, in one place")
    st.caption(
        "Counts below are the finished RQ3/RQ4/RQ5 registries — independent of the "
        "sidebar paper filters, which only affect the Timeline and Citation network tabs."
    )

    c = st.columns(4)
    c[0].metric("Papers screened", n_papers)
    c[1].metric("Named mechanisms (RQ3)", s["n_mechanisms"])
    c[2].metric("Confirmed defenses (RQ4)", s["n_defenses"])
    c[3].metric("Confirmed test pairs (RQ5)", s["n_pairs"])

    c = st.columns(4)
    pct_def = 100 * s["n_defenses_matched"] / s["n_defenses_total"]
    pct_mech = 100 * s["n_mechs_covered"] / s["n_mechs_total"]
    n_cross = sum(1 for p in reg["pairs"] if p["cross_track"])
    c[0].metric("Defenses matched to a named mechanism", f"{pct_def:.1f}%",
                help=f"{s['n_defenses_matched']} of {s['n_defenses_total']}. The rest weren't confirmed "
                     "tested against anything in the RQ3 registry — see the Coverage matrix tab.")
    c[1].metric("Mechanisms with ≥1 defense tested", f"{pct_mech:.1f}%",
                help=f"{s['n_mechs_covered']} of {s['n_mechs_total']}")
    c[2].metric("Mechanisms never defended", s["n_mechs_uncovered"],
                help="Zero confirmed defenses tested against them")
    c[3].metric("Cross-track test pairs", n_cross,
                help="Pairs where the defense's track differs from the mechanism's track — "
                     "i.e. someone actually tested across the adversarial/incidental divide.")

    st.divider()
    st.markdown("#### What each research question found")
    for rq, (fname, blurb) in registry_source.RQ_FILES.items():
        text = summaries.get(rq, "")
        with st.expander(f"**{rq}** — {blurb}", expanded=(rq == "RQ7")):
            if text:
                st.markdown(text)
                st.caption(f"Full write-up: `{fname}`")
            else:
                st.info(f"No headline section found in `{fname}`.")


def mechanisms_tab(reg: dict) -> None:
    st.markdown("#### Every identified poisoning source / attack mechanism (RQ3)")
    st.caption(
        "Both tracks: deliberate attack techniques (Security) and incidental degradation "
        "mechanisms (ML/AI). 'Defenses tested' counts confirmed RQ5 matches, not claims."
    )
    df = pd.DataFrame(reg["mechanisms"])

    f = st.columns(4)
    out = _multiselect_filter(df, "track", "Track", f[0], "mech_track")
    out = _multiselect_filter(out, "channel", "Channel", f[1], "mech_channel")
    out = _multiselect_filter(out, "consequence", "Consequence", f[2], "mech_conseq")
    coverage = f[3].selectbox("Defense coverage", ["All", "Has ≥1 defense tested", "Never defended"], key="mech_cov")
    if coverage == "Has ≥1 defense tested":
        out = out[out["has_any_defense"]]
    elif coverage == "Never defended":
        out = out[~out["has_any_defense"]]
    kw = st.text_input("Search mechanism name / notes", key="mech_kw")
    if kw:
        k = kw.lower()
        out = out[out["mechanism_name"].fillna("").str.lower().str.contains(k)
                  | out["notes"].fillna("").str.lower().str.contains(k)]

    m = st.columns(3)
    m[0].metric("Mechanisms shown", f"{len(out)} / {len(df)}")
    m[1].metric("Of those, never defended", int((~out["has_any_defense"]).sum()) if len(out) else 0)
    m[2].metric("Total defenses tested against them", int(out["n_defenses_tested"].sum()) if len(out) else 0)

    if out.empty:
        st.info("No mechanisms match these filters.")
        return

    left, right = st.columns(2)
    with left:
        st.plotly_chart(_bar(out["channel"].fillna("(unspecified)").value_counts(),
                             "Mechanisms by channel", "#e07a5f"), width="stretch", key="mech_channel_chart")
    with right:
        top = out.nlargest(12, "n_defenses_tested")[["mechanism_name", "n_defenses_tested"]]
        top = top[top["n_defenses_tested"] > 0].set_index("mechanism_name")["n_defenses_tested"]
        if len(top):
            st.plotly_chart(_bar(top, "Most-tested-against mechanisms", "#3d5a80"),
                            width="stretch", key="mech_top_chart")
        else:
            st.info("None of the mechanisms in this view has any defense tested against it.")

    display = out[["mechanism_name", "track", "channel", "consequence",
                   "n_defenses_tested", "source_paper_title"]].sort_values(
        "n_defenses_tested", ascending=False)
    st.dataframe(display, width="stretch", hide_index=True, height=380)

    st.markdown("**Inspect one mechanism**")
    pick = st.selectbox("Mechanism", out["mechanism_name"].tolist(), key="mech_pick")
    row = out[out["mechanism_name"] == pick].iloc[0]
    d = st.columns(4)
    d[0].metric("Track", row["track"] or "—")
    d[1].metric("Channel", row["channel"] or "—")
    d[2].metric("Consequence", row["consequence"] or "—")
    d[3].metric("Defenses tested", int(row["n_defenses_tested"]))
    if row["notes"]:
        st.markdown(f"> {row['notes']}")
    st.caption(f"First named in: {row['source_paper_title']}")
    if row["defenses_tested"]:
        st.markdown("**Defenses confirmed tested against it:** " + ", ".join(row["defenses_tested"]))
    else:
        st.warning("No defense in the RQ4 registry was confirmed tested against this mechanism.")


def defenses_tab(reg: dict) -> None:
    st.markdown("#### Every identified defense (RQ4)")
    st.caption(
        "`validated_against` is the threat model the defense's *own paper* tested it against — "
        "the RQ6 case studies exist because that's almost never both."
    )
    df = pd.DataFrame(reg["defenses"])

    f = st.columns(4)
    out = _multiselect_filter(df, "track", "Track", f[0], "def_track")
    out = _multiselect_filter(out, "intervention_point", "Intervention point", f[1], "def_point")
    out = _multiselect_filter(out, "validated_against", "Validated against", f[2], "def_valid")
    match = f[3].selectbox("Mechanism match", ["All", "Matched to a named mechanism", "No confirmed match"], key="def_match")
    if match == "Matched to a named mechanism":
        out = out[out["has_confirmed_match"]]
    elif match == "No confirmed match":
        out = out[~out["has_confirmed_match"]]
    kw = st.text_input("Search defense name / notes", key="def_kw")
    if kw:
        k = kw.lower()
        out = out[out["defense_name"].fillna("").str.lower().str.contains(k)
                  | out["notes"].fillna("").str.lower().str.contains(k)]

    m = st.columns(3)
    m[0].metric("Defenses shown", f"{len(out)} / {len(df)}")
    m[1].metric("With a confirmed mechanism match", int(out["has_confirmed_match"].sum()) if len(out) else 0)
    m[2].metric("Tested against 2+ mechanisms", int((out["n_mechanisms_tested"] >= 2).sum()) if len(out) else 0)

    if out.empty:
        st.info("No defenses match these filters.")
        return

    left, right = st.columns(2)
    with left:
        st.plotly_chart(_bar(out["intervention_point"].fillna("(unspecified)").value_counts(),
                             "Defenses by intervention point", "#8ac926"),
                        width="stretch", key="def_point_chart")
    with right:
        st.plotly_chart(_bar(out["validated_against"].fillna("(unspecified)").value_counts(),
                             "Defenses by threat model validated against", "#e07a5f"),
                        width="stretch", key="def_valid_chart")

    display = out[["defense_name", "track", "intervention_point", "validated_against",
                   "channel", "consequence", "n_mechanisms_tested", "source_paper_title"]].sort_values(
        "n_mechanisms_tested", ascending=False)
    st.dataframe(display, width="stretch", hide_index=True, height=380)

    st.markdown("**Inspect one defense**")
    pick = st.selectbox("Defense", out["defense_name"].tolist(), key="def_pick")
    row = out[out["defense_name"] == pick].iloc[0]
    d = st.columns(4)
    d[0].metric("Track", row["track"] or "—")
    d[1].metric("Intervention point", row["intervention_point"] or "—")
    d[2].metric("Validated against", row["validated_against"] or "—")
    d[3].metric("Mechanisms tested", int(row["n_mechanisms_tested"]))
    if row["notes"]:
        st.markdown(f"> {row['notes']}")
    st.caption(f"From: {row['source_paper_title']}")
    if row["mechanisms_tested"]:
        st.markdown("**Confirmed tested against:** " + ", ".join(row["mechanisms_tested"]))
    else:
        st.warning(
            "No confirmed match to any RQ3-named mechanism. That means its paper's own "
            "results text didn't name a technique the registry recognizes — not necessarily "
            "that it was never evaluated. See the Coverage matrix tab."
        )


def coverage_tab(reg: dict) -> None:
    s = reg["stats"]
    pairs = pd.DataFrame(reg["pairs"])
    st.markdown("#### Which defenses were actually tested against which attacks (RQ5)")

    n_cross = int(pairs["cross_track"].sum())
    m = st.columns(4)
    m[0].metric("Confirmed (defense, mechanism) pairs", s["n_pairs"])
    m[1].metric("Defenses tested vs. exactly 1 mechanism",
                s["mechs_per_defense_distribution"].get("1", 0),
                help="vs. 2 mechanisms: "
                     f"{s['mechs_per_defense_distribution'].get('2', 0)}. None were tested against 3+.")
    m[2].metric("Mechanisms never defended", s["n_mechs_uncovered"],
                delta=f"-{100 * s['n_mechs_uncovered'] / s['n_mechs_total']:.1f}% of registry",
                delta_color="inverse")
    m[3].metric("Cross-track pairs", n_cross,
                help="A Security-track defense tested against an ML/AI-track mechanism, or vice "
                     "versa. This is the number RQ6 and RQ7 are ultimately about.")

    if n_cross <= 5:
        st.warning(
            f"**Only {n_cross} of {s['n_pairs']} confirmed test pairs cross the adversarial/incidental "
            "divide.** Defenses are essentially never evaluated against the other track's mechanisms — "
            "which is exactly the gap the RQ6 case studies were built to probe."
        )

    st.divider()
    st.markdown("##### Where the testing effort concentrates")
    heat_src = pairs.copy()
    heat_src["intervention_point"] = heat_src["defense_intervention_point"].fillna("(unspecified)")
    top_mechs = heat_src["mechanism_name"].value_counts().head(15).index.tolist()
    heat = heat_src[heat_src["mechanism_name"].isin(top_mechs)]
    matrix = heat.pivot_table(index="mechanism_name", columns="intervention_point",
                              values="defense_name", aggfunc="count", fill_value=0)
    matrix = matrix.reindex(top_mechs)
    fig = go.Figure(go.Heatmap(
        z=matrix.values, x=matrix.columns.tolist(), y=matrix.index.tolist(),
        colorscale="Blues", text=matrix.values, texttemplate="%{text}",
        hovertemplate="%{y}<br>%{x}: %{z} defenses<extra></extra>", showscale=False,
    ))
    fig.update_layout(height=max(320, 30 * len(matrix) + 120), margin=dict(l=10, r=10, t=30, b=10),
                      yaxis=dict(autorange="reversed"), xaxis_title="Defense intervention point")
    st.plotly_chart(fig, width="stretch", key="coverage_heatmap")
    st.caption("Top 15 mechanisms by number of defenses tested against them. Every other mechanism "
               "in the registry has 2 or fewer — or, for 116 of them, none at all.")

    st.divider()
    st.markdown("##### All confirmed test pairs")
    f = st.columns(3)
    out = _multiselect_filter(pairs, "defense_intervention_point", "Intervention point", f[0], "cov_point")
    out = _multiselect_filter(out, "mechanism_track", "Mechanism track", f[1], "cov_mtrack")
    only_cross = f[2].checkbox("Cross-track pairs only", key="cov_cross")
    if only_cross:
        out = out[out["cross_track"]]
    st.dataframe(
        out[["defense_name", "mechanism_name", "defense_intervention_point",
             "defense_validated_against", "mechanism_track", "cross_track", "justification"]],
        width="stretch", hide_index=True, height=340,
    )
    st.caption(f"{len(out)} of {len(pairs)} pairs shown. `justification` is the extracting "
               "agent's rationale for the match, kept for auditability.")

    st.divider()
    st.markdown(f"##### The {s['n_mechs_uncovered']} mechanisms nothing has ever been tested against")
    mech_df = pd.DataFrame(reg["mechanisms"])
    uncovered = mech_df[~mech_df["has_any_defense"]][
        ["mechanism_name", "track", "channel", "consequence", "source_paper_title"]]
    g = st.columns(2)
    unc = _multiselect_filter(uncovered, "track", "Track", g[0], "unc_track")
    unc = _multiselect_filter(unc, "channel", "Channel", g[1], "unc_channel")
    st.dataframe(unc, width="stretch", hide_index=True, height=340)
    st.caption(f"{len(unc)} of {len(uncovered)} shown — a ready-made 'what's left to defend' list.")


def findings_tab(summaries: dict) -> None:
    st.markdown("#### The two research questions that produced new evidence")
    st.caption(
        "RQ6 reconstructed and ran real released defense code against both threat models; "
        "RQ7 synthesizes RQ2/RQ5/RQ6 into ranked open problems. Both write-ups are rendered "
        "in full below."
    )
    for rq in ("RQ6", "RQ7"):
        fname, blurb = registry_source.RQ_FILES[rq]
        st.markdown(f"### {rq} — {blurb}")
        if summaries.get(rq):
            st.markdown(summaries[rq])
        path = registry_source.REPO_ROOT / fname
        if path.exists():
            with st.expander(f"Read the full `{fname}`"):
                st.markdown(path.read_text())
        st.divider()


def main() -> None:
    config = get_config()
    db_path = str(config.path("db_path"))
    excel_path = config.path("excel_source")

    st.title("Context Integrity SoK — Project Explorer")

    bootstrapped = ensure_excel_source(excel_path, db_path, config.hop_depth)
    if bootstrapped:
        st.success(
            f"Created the dashboard's editable data source at `{excel_path}` from the "
            f"high-confidence pool ({bootstrapped} papers). This file is what the dashboard "
            "reads from now — add rows, change Track/Screening/etc. directly in it, then "
            "refresh this page."
        )

    if not excel_path.exists():
        st.warning(f"No data source found at `{excel_path}` and none could be bootstrapped from the DB.")
        return

    mtime = excel_path.stat().st_mtime
    df = load_excel_data(str(excel_path), mtime)
    edges = load_edges(db_path)

    if df.empty:
        st.warning(f"`{excel_path}` has no paper rows. Add some and refresh.")
        return

    st.caption(
        f"Data source: `{excel_path}` — {len(df)} papers, last saved "
        f"{datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')}. "
        "Edit the spreadsheet directly and refresh this page to see changes."
    )

    if "sync_result" in st.session_state:
        sc = st.session_state.pop("sync_result")
        st.success(
            f"Sync complete: {sc['newly_synced']} paper(s) processed "
            f"({sc['already_synced']} already synced), {sc['edges_added']} citation edges added."
        )

    st.sidebar.header("Paper filters")
    st.sidebar.caption(
        "These apply to the Timeline and Citation network tabs only — the registry tabs "
        "(mechanisms, defenses, coverage) have their own filters."
    )
    if st.sidebar.button("🔗 Sync new papers into DB"):
        conn = db.connect(db_path)
        db.init_db(conn)
        with st.spinner("Resolving new papers via Semantic Scholar/arXiv and fetching their citation edges..."):
            st.session_state["sync_result"] = excel_sync.sync_excel(conn, config, excel_path)
        conn.close()
        st.cache_data.clear()
        st.rerun()
    if st.sidebar.button("🔄 Reload from Excel"):
        st.cache_data.clear()
        st.rerun()
    tracks = st.sidebar.multiselect(
        "Track",
        list(TRACK_COLORS.keys()),
        default=list(TRACK_COLORS.keys()),
        format_func=lambda t: TRACK_DISPLAY_NAMES.get(t, t),
    )
    year_min, year_max = int(df["year"].min(skipna=True) or 2023), int(df["year"].max(skipna=True) or 2026)
    year_range = st.sidebar.slider("Year", year_min, year_max, (year_min, year_max))
    # Sorted by paper count (descending), not alphabetically, with the count
    # shown so the most-represented venues are easy to spot and pick.
    venue_counts = df["venue_short"].value_counts()
    venues = st.sidebar.multiselect(
        "Venue", venue_counts.index.tolist(), format_func=lambda v: f"{v} ({venue_counts.get(v, 0)})"
    )
    available_hops = sorted(df["hop"].dropna().unique().tolist())
    default_hops = [h for h in available_hops if h <= config.hop_depth] or available_hops
    hops = st.sidebar.multiselect("Hop", available_hops, default=default_hops)
    screens = st.sidebar.multiselect(
        "Screening status",
        ["auto_include", "auto_exclude", "needs_review"],
        default=["auto_include", "needs_review"],
        format_func=lambda s: {"auto_include": "Include", "auto_exclude": "Exclude", "needs_review": "Needs Review"}.get(s, s),
    )
    keyword = st.sidebar.text_input("Keyword (title/abstract)")

    filtered = apply_filters(df, tracks, year_range, venues, hops, screens, keyword)
    st.sidebar.caption(f"{len(filtered)} / {len(df)} papers shown")

    try:
        mtimes = _registry_mtimes()
        reg = load_registries(mtimes)
        summaries = load_rq_summaries(mtimes)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        reg, summaries = None, {}
        st.warning(
            f"Registry data couldn't be loaded ({exc}). The paper tabs still work; "
            "rebuild the registries with `scripts/build_registry.py` and "
            "`scripts/build_coverage_matrix.py` to restore the rest."
        )

    tabs = st.tabs([
        "Overview", "Attacks & mechanisms", "Defenses", "Coverage matrix",
        "RQ6 / RQ7 findings", "Paper timeline", "Citation network",
    ])
    with tabs[0]:
        if reg:
            overview_tab(reg, summaries, len(df))
    with tabs[1]:
        if reg:
            mechanisms_tab(reg)
    with tabs[2]:
        if reg:
            defenses_tab(reg)
    with tabs[3]:
        if reg:
            coverage_tab(reg)
    with tabs[4]:
        findings_tab(summaries)
    with tabs[5]:
        timeline_tab(filtered)
    with tabs[6]:
        network_tab(filtered, edges)


if __name__ == "__main__":
    main()

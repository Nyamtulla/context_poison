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


def _stacked_by_track(df: pd.DataFrame, cat_col: str, title: str,
                      track_col: str = "track") -> go.Figure:
    """Horizontal bars split by track, so an aggregate like 'reasoning: 189
    defenses' shows its Security / ML-AI composition rather than hiding it.
    Categories are ordered by total; each segment is labelled with its own
    count and the hover carries the category total."""
    d = df.copy()
    d[cat_col] = d[cat_col].fillna("(unspecified)")
    d[track_col] = d[track_col].fillna("(unspecified)")
    totals = d[cat_col].value_counts()
    order = totals.index.tolist()
    tab = d.groupby([cat_col, track_col]).size().unstack(fill_value=0).reindex(order)

    fig = go.Figure()
    # Fixed track order so colours stay stable across tabs and reruns.
    for track in [t for t in ("Security", "ML/AI", "Both") if t in tab.columns] + \
                 [t for t in tab.columns if t not in ("Security", "ML/AI", "Both")]:
        vals = tab[track].values
        fig.add_trace(go.Bar(
            y=tab.index.astype(str), x=vals, orientation="h", name=str(track),
            marker_color=REGISTRY_TRACK_COLORS.get(track, "#adb5bd"),
            text=[str(v) if v else "" for v in vals], textposition="inside",
            insidetextanchor="middle", textfont=dict(size=11, color="white"),
            customdata=[totals.get(c, 0) for c in tab.index],
            hovertemplate="%{y}<br>" + str(track) + ": %{x}<br>total: %{customdata}<extra></extra>",
        ))
    fig.update_layout(
        barmode="stack", title=title,
        height=max(260, 30 * len(tab) + 110),
        margin=dict(l=10, r=10, t=45, b=10),
        yaxis=dict(autorange="reversed"), xaxis_title="Entries",
        legend_title_text="Track",
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1),
    )
    return fig


def _bar_colored_by_track(df: pd.DataFrame, label_col: str, value_col: str,
                          title: str, track_col: str = "track") -> go.Figure:
    """One bar per row (each row has a single track), coloured by that track -
    stacking would be degenerate here, but the colour still carries the split."""
    fig = go.Figure()
    for track in [t for t in ("Security", "ML/AI", "Both") if t in set(df[track_col])]:
        sub = df[df[track_col] == track]
        if sub.empty:
            continue
        fig.add_trace(go.Bar(
            y=sub[label_col].astype(str), x=sub[value_col], orientation="h",
            name=str(track), marker_color=REGISTRY_TRACK_COLORS.get(track, "#adb5bd"),
            text=sub[value_col], textposition="outside",
            hovertemplate="%{y}<br>" + str(track) + ": %{x}<extra></extra>",
        ))
    fig.update_layout(
        barmode="stack", title=title, height=max(260, 30 * len(df) + 110),
        margin=dict(l=10, r=10, t=45, b=10),
        yaxis=dict(autorange="reversed",
                   categoryorder="array",
                   categoryarray=df[label_col].astype(str).tolist()[::-1]),
        xaxis_title="Defenses tested against it", legend_title_text="Track",
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1),
    )
    return fig


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


@st.cache_data(ttl=60)
def load_paper_index(mtime: float) -> pd.DataFrame:
    """The curated corpus, shaped for lookup rather than analysis."""
    rows = []
    # Only papers carried into the analysis - rows screened out during coding
    # belong to the audit trail, not to the research.
    for p in registry_source.load_papers():
        if str(p.get("screening")) != "Include":
            continue
        url, label = registry_source.paper_link(p)
        rows.append({
            "Title": p.get("title"),
            "Year": p.get("year"),
            "Authors": p.get("authors"),
            "Venue": p.get("venue"),
            "Track": p.get("track"),
            "Screening": p.get("screening"),
            "Citations": p.get("citation_count"),
            "Link": url,
            "Source": label,
            "arxiv_id": p.get("arxiv_id"),
            "doi": p.get("doi"),
            "paper_id": p.get("paper_id"),
            "Channel": p.get("channel"),
            "Consequence": p.get("consequence"),
            "abstract": p.get("abstract"),
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=60)
def search_discovery_pool(query: str, db_path: str, limit: int = 25) -> pd.DataFrame:
    """Search the full ~26k discovered-paper pool in the DB - the papers the
    search/snowball found but that never made it into the curated corpus.
    Answers 'have I seen this paper at all?' rather than 'did we code it?'."""
    if not query or len(query.strip()) < 3:
        return pd.DataFrame()
    conn = db.connect(db_path)
    db.init_db(conn)
    like = f"%{query.strip()}%"
    rows = conn.execute(
        "select paper_id, title, year, venue, arxiv_id, doi, url, citation_count, "
        "screen_auto, track_auto, discovered_via from papers "
        "where title like ? order by citation_count desc nulls last limit ?",
        (like, limit),
    ).fetchall()
    conn.close()
    out = []
    for r in rows:
        d = dict(r)
        url, label = registry_source.paper_link(d)
        out.append({
            "Title": d.get("title"), "Year": d.get("year"), "Venue": d.get("venue"),
            "Citations": d.get("citation_count"), "Auto-screen": d.get("screen_auto"),
            "Auto-track": d.get("track_auto"), "Found via": d.get("discovered_via"),
            "Link": url, "Source": label,
        })
    return pd.DataFrame(out)


def paper_index_tab(db_path: str) -> None:
    st.markdown("#### Paper index — is this paper in the corpus?")
    st.caption(
        "Search the analysed corpus by title, author, or venue. If nothing matches, "
        "the wider discovery pool the search and snowball turned up is checked too, so "
        "a miss here tells you whether the paper is genuinely new to the project."
    )

    df = load_paper_index(
        (registry_source.REPO_ROOT / registry_source.PAPERS_XLSX).stat().st_mtime)

    query = st.text_input("Search by title, author, or venue",
                          placeholder="e.g. PoisonedRAG, Greshake, lost in the middle",
                          key="paper_search")

    f = st.columns(3)
    out = _multiselect_filter(df, "Track", "Track", f[0], "pi_track")
    years = [int(y) for y in df["Year"].dropna().unique()]
    yr = f[1].slider("Year", min(years), max(years), (min(years), max(years)), key="pi_year")
    sort_by = f[2].selectbox("Sort by", ["Citations", "Year", "Title"], key="pi_sort")

    out = out[out["Year"].between(yr[0], yr[1]) | out["Year"].isna()]
    if query:
        q = query.strip().lower()
        mask = (out["Title"].fillna("").str.lower().str.contains(q, regex=False)
                | out["Authors"].fillna("").str.lower().str.contains(q, regex=False)
                | out["Venue"].fillna("").str.lower().str.contains(q, regex=False))
        out = out[mask]

    out = out.sort_values(sort_by, ascending=(sort_by == "Title"),
                          na_position="last")

    m = st.columns(2)
    m[0].metric("Papers shown", f"{len(out)} / {len(df)}")
    m[1].metric("With a working link", int((out["Link"] != "").sum()) if len(out) else 0)

    if query and out.empty:
        st.warning(f"**No paper matching “{query}” in the analysed corpus.** "
                   "Checking the wider discovery pool below.")
    elif query:
        st.success(f"**Found {len(out)} match(es)** — this paper is in the analysed corpus.")

    if not out.empty:
        st.dataframe(
            out[["Title", "Year", "Authors", "Venue", "Track",
                 "Citations", "Link", "Source"]],
            width="stretch", hide_index=True, height=420,
            column_config={
                "Link": st.column_config.LinkColumn("Open paper", display_text="open ↗"),
                "Title": st.column_config.TextColumn("Title", width="large"),
                "Authors": st.column_config.TextColumn("Authors", width="medium"),
            },
        )
        st.download_button("Download this view as CSV",
                           out.drop(columns=["abstract"]).to_csv(index=False),
                           file_name="context_sok_paper_index.csv", mime="text/csv")

    # Only consult the ~26k pool when the curated corpus came up empty - it is
    # the "have we seen this at all" fallback, not the primary index.
    if query and out.empty:
        pool = search_discovery_pool(query, db_path)
        if pool.empty:
            st.error(
                f"**Not found anywhere** — “{query}” isn't in the analysed corpus or the "
                "discovery pool. If it's relevant, it's a genuinely new paper to add."
            )
        else:
            st.info(
                f"**{len(pool)} match(es) in the discovery pool, but not in the analysed "
                "corpus.** Found by search or snowball and not carried into the analysis — "
                "worth a look before treating the paper as new."
            )
            st.dataframe(
                pool, width="stretch", hide_index=True, height=300,
                column_config={"Link": st.column_config.LinkColumn("Open paper",
                                                                   display_text="open ↗")},
            )

    if query and not out.empty:
        with st.expander("Abstract of the top match"):
            top = out.iloc[0]
            st.markdown(f"**{top['Title']}**")
            st.caption(f"{top['Authors']} · {top['Venue']} · {top['Year']}")
            st.write(top["abstract"] or "_No abstract on record._")


def transfer_tab(reg: dict) -> None:
    preds = registry_source.load_transfer_predictions()
    stage3 = registry_source.load_stage3_result()
    st.markdown("#### Transfer predictions — which defense should work on what nobody tested")
    st.caption("RQ6 continued: its intervention-point finding used as a predictor.")
    if not preds:
        st.info("No predictions yet. Run `scripts/stage2_transfer_predictions.py`.")
        return
    st.caption(
        "RQ6 found that generalization tracked where a defense intervenes. These use that "
        "as a predictor: similarity between an untested mechanism and what a defense WAS "
        "tested on, weighted by that intervention point's observed transfer rate. "
        "**These are hypotheses to test, not findings.**"
    )

    testable = [p for p in preds if p["testable_now"]]
    m = st.columns(3)
    m[0].metric("Uncovered mechanisms with a hypothesis", len(preds))
    m[1].metric("Testable now (candidate has code)", len(testable))
    m[2].metric("Validated by execution so far", 1 if stage3 else 0)

    if stage3:
        s = stage3.get("summary", {})
        st.success(
            "**Validated by execution — RobustRAG defeats BadRAG.** "
            "BadRAG's denial-of-service payload drops undefended accuracy to "
            f"{100*s.get('badrag_dos',{}).get('undefended_acc',0):.1f}% with a "
            f"{100*s.get('badrag_dos',{}).get('undefended_refusal_rate',0):.1f}% refusal rate; "
            f"RobustRAG restores {100*s.get('badrag_dos',{}).get('defended_acc',0):.1f}% "
            f"(clean defended ceiling {100*s.get('clean',{}).get('defended_acc',0):.1f}%) and cuts "
            f"refusals to {100*s.get('badrag_dos',{}).get('defended_refusal_rate',0):.1f}%. "
            "RobustRAG had never been evaluated against BadRAG."
        )
        with st.expander("Stage 3 full numbers"):
            st.dataframe(pd.DataFrame(s).T, width="stretch")
            st.caption("BadRAG's sentiment payload is reported as untested, not defeated — "
                       "it never landed on RealtimeQA's short-answer format.")

    rows = []
    for p in preds:
        for c in p["candidates"][:1]:
            rows.append({
                "Priority": p["priority"], "Untested mechanism": p["mechanism"],
                "Cites": p["mechanism_citations"], "Channel": p["channel"],
                "Consequence": p["consequence"], "Suggested defense": c["defense"],
                "Intervention": c["defense_intervention_point"],
                "Similar to": c["transfers_from"], "Similarity": c["similarity"],
                "Score": c["score"], "Code": "yes" if c["code_released"] else "no",
            })
    pdf = pd.DataFrame(rows)
    g = st.columns(3)
    only_code = g[0].checkbox("Only where the defense has released code", key="tr_code")
    out = pdf[pdf["Code"] == "yes"] if only_code else pdf
    out = _multiselect_filter(out, "Intervention", "Intervention point", g[1], "tr_point")
    out = _multiselect_filter(out, "Consequence", "Consequence", g[2], "tr_conseq")
    st.dataframe(out.sort_values("Priority", ascending=False), width="stretch",
                 hide_index=True, height=420)
    st.caption(f"{len(out)} of {len(pdf)} hypotheses shown, ranked by predicted transfer "
               "weighted by how much the field cites the untested mechanism.")


DEEP_FIELDS = ["technical_summary", "key_result", "baselines_compared",
               "stated_limitations", "models_evaluated", "datasets_benchmarks"]


@st.cache_data(ttl=60)
def n_papers_in_research(mtime: float) -> int:
    """Papers actually carried into the analysis. Rows screened out during
    coding are part of the audit trail, not part of the research, so they are
    not surfaced here."""
    return sum(1 for p in registry_source.load_papers()
               if str(p.get("screening")) == "Include")


def overview_tab(reg: dict, summaries: dict, n_papers: int) -> None:
    s = reg["stats"]
    st.markdown("#### Everything this project has produced, in one place")
    st.caption(
        "Counts below are the finished RQ3/RQ4/RQ5 registries — independent of the "
        "sidebar filters, which affect only the paper tabs."
    )

    c = st.columns(4)
    c[0].metric("Papers analysed", n_papers)
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
        st.plotly_chart(_stacked_by_track(out, "channel", "Mechanisms by channel"),
                        width="stretch", key="mech_channel_chart")
    with right:
        top = out.nlargest(12, "n_defenses_tested")[
            ["mechanism_name", "n_defenses_tested", "track"]]
        top = top[top["n_defenses_tested"] > 0]
        if len(top):
            st.plotly_chart(
                _bar_colored_by_track(top, "mechanism_name", "n_defenses_tested",
                                      "Most-tested-against mechanisms"),
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
        st.plotly_chart(_stacked_by_track(out, "intervention_point",
                                          "Defenses by intervention point"),
                        width="stretch", key="def_point_chart")
    with right:
        st.plotly_chart(_stacked_by_track(out, "validated_against",
                                          "Defenses by threat model validated against"),
                        width="stretch", key="def_valid_chart")

    display = out[["defense_name", "track", "intervention_point", "validated_against",
                   "channel", "consequence", "n_mechanisms_tested",
                   "source_paper_title"]].sort_values("n_mechanisms_tested", ascending=False)
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
            "Not confirmed tested against any named mechanism in the RQ3 registry."
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
             "defense_validated_against", "mechanism_track", "cross_track",
             "source", "justification"]],
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
    st.markdown("#### The research questions that produced new evidence")
    st.caption(
        "RQ6 reconstructed and ran real released defense code against both threat models, "
        "then turned that finding into transfer predictions and validated one by execution; "
        "RQ7 synthesizes them into ranked open problems. Rendered in full below."
    )
    for rq in ("RQ6", "RQ6-transfer", "RQ7"):
        fname, blurb = registry_source.RQ_FILES[rq]
        st.markdown(f"### {rq} — {blurb}")
        if summaries.get(rq):
            st.markdown(summaries[rq])
        path = registry_source.REPO_ROOT / fname
        if path.exists():
            with st.expander(f"Read the full `{fname}`"):
                st.markdown(path.read_text())
        st.divider()



# ===================================================================
# RQ1 (taxonomy cube) and RQ2 (cross-citation) visuals. Both compute
# from the live corpus rather than from the write-ups, so they track
# corpus changes instead of going stale.
# ===================================================================

CUBE_INTENTS = ["Security", "ML/AI", "Both"]
# The plan's Section 3 calls this axis INTENT (adversarial / incidental / both),
# but the corpus stores it in the `track` column as Security / ML-AI / Both.
# Label panels with both names so the axis is identifiable either way.
INTENT_LABELS = {
    "Security": "ADVERSARIAL<br><sup>Security track</sup>",
    "ML/AI": "INCIDENTAL<br><sup>ML/AI track</sup>",
    "Both": "BOTH<br><sup>bridges the two</sup>",
}


@st.cache_data(ttl=60)
def taxonomy_cube(mtime: float):
    """The channel x intent x consequence cube, as a dict keyed by
    (intent, channel, consequence) plus the axis orders."""
    papers = [p for p in registry_source.load_papers()
              if str(p.get("screening")) == "Include"]
    cells = {}
    for p in papers:
        ch, co, tr = p.get("channel"), p.get("consequence"), p.get("track")
        if ch and co and tr:
            cells[(tr, ch, co)] = cells.get((tr, ch, co), 0) + 1
    channels = sorted({p["channel"] for p in papers if p.get("channel")},
                      key=lambda c: -sum(v for (t, ch, co), v in cells.items() if ch == c))
    conseq = sorted({p["consequence"] for p in papers if p.get("consequence")},
                    key=lambda c: -sum(v for (t, ch, co), v in cells.items() if co == c))
    return cells, channels, conseq


@st.cache_data(ttl=60)
def cross_citation_stats(mtime: float):
    """RQ2: cross-track citation, overall / by year / by evidence grade."""
    papers = [p for p in registry_source.load_papers()
              if str(p.get("screening")) == "Include"]
    A = [p for p in papers if p.get("track") == "Security"]
    B = [p for p in papers if p.get("track") == "ML/AI"]
    def rate(group, field):
        hit = sum(1 for p in group if p.get(field) == "Y")
        return hit, len(group), (100 * hit / len(group) if group else 0.0)
    overall = {"A->B": rate(A, "cites_track_b"), "B->A": rate(B, "cites_track_a")}
    years = sorted({p["year"] for p in papers if p.get("year")})
    by_year = {y: {"A->B": rate([p for p in A if p.get("year") == y], "cites_track_b"),
                   "B->A": rate([p for p in B if p.get("year") == y], "cites_track_a")}
               for y in years}
    grades = sorted({p["evidence_grade"] for p in papers if p.get("evidence_grade")})
    by_grade = {g: {"A->B": rate([p for p in A if p.get("evidence_grade") == g], "cites_track_b"),
                    "B->A": rate([p for p in B if p.get("evidence_grade") == g], "cites_track_a")}
                for g in grades}
    # within-track citation, for the 2x2 direction matrix
    same = {"A->A": rate(A, "cites_track_a"), "B->B": rate(B, "cites_track_b")}
    return overall, by_year, by_grade, same, len(A), len(B)


def taxonomy_tab() -> None:
    st.markdown("#### RQ1 — the channel x intent x consequence cube")
    cells, channels, conseq = taxonomy_cube(
        (registry_source.REPO_ROOT / registry_source.PAPERS_XLSX).stat().st_mtime)
    total = len(channels) * len(conseq) * len(CUBE_INTENTS)
    filled = len(cells)
    empty = total - filled

    m = st.columns(4)
    m[0].metric("Cells in the cube", total,
                help=f"{len(channels)} channels x {len(CUBE_INTENTS)} intents x {len(conseq)} consequences")
    m[1].metric("Cells with at least one paper", filled)
    m[2].metric("Empty cells", empty)
    m[3].metric("Share of the cube empty", f"{100*empty/total:.1f}%")

    st.info(
        "**How to read this.** The cube has three axes, and each one appears in a "
        "different place:\n\n"
        "- **INTENT** → the three panels. Adversarial (Security track), incidental "
        "(ML/AI track), or both. This is the axis you'd have to rotate a 3D cube to see.\n"
        "- **CHANNEL** → the rows. *Where* contaminated content enters the context "
        "window: tool output, RAG, memory, a skill file, and so on.\n"
        "- **CONSEQUENCE** → the columns. *What goes wrong* as a result: the agent's "
        "goal is hijacked, data is exfiltrated, reasoning is corrupted, and so on.\n\n"
        "Each cell is one channel x intent x consequence combination. The number in a "
        "cell is how many papers study it; **grey means no paper studies that "
        "combination at all** — those grey cells are the finding."
    )
    st.caption(
        "Shown as three panels rather than a rotatable 3D cube: in 3D, cells hide behind "
        "other cells, which defeats the purpose when what matters is which cells are empty."
    )

    from plotly.subplots import make_subplots
    fig = make_subplots(rows=1, cols=len(CUBE_INTENTS),
                        subplot_titles=[INTENT_LABELS[t] for t in CUBE_INTENTS],
                        shared_yaxes=True, horizontal_spacing=0.05)
    zmax = max(cells.values()) if cells else 1
    for i, intent in enumerate(CUBE_INTENTS, start=1):
        z, text = [], []
        for ch in channels:
            zrow, trow = [], []
            for co in conseq:
                v = cells.get((intent, ch, co), 0)
                zrow.append(v if v else None)      # None renders as the empty colour
                trow.append(str(v) if v else "")
            z.append(zrow); text.append(trow)
        fig.add_trace(go.Heatmap(
            z=z, x=conseq, y=channels, text=text, texttemplate="%{text}",
            textfont=dict(size=10),
            colorscale="Blues", zmin=0, zmax=zmax, showscale=(i == len(CUBE_INTENTS)),
            colorbar=dict(title="papers", thickness=12) if i == len(CUBE_INTENTS) else None,
            hovertemplate=("intent: " + intent + "<br>channel: %{y}"
                           "<br>consequence: %{x}<br>%{z} papers<extra></extra>"),
            xgap=2, ygap=2,
        ), row=1, col=i)
    fig.update_layout(
        height=470, margin=dict(l=10, r=10, t=70, b=115),
        plot_bgcolor="#e9ecef",   # shows through wherever a cell is empty
        annotations=list(fig.layout.annotations) + [
            dict(text="<b>CONSEQUENCE</b> — what goes wrong", showarrow=False,
                 xref="paper", yref="paper", x=0.5, y=-0.30, font=dict(size=12)),
        ],
    )
    fig.update_xaxes(tickangle=-40, tickfont=dict(size=10))
    fig.update_yaxes(title_text="<b>CHANNEL</b> — where it enters",
                     title_font=dict(size=12), row=1, col=1)
    st.plotly_chart(fig, width="stretch", key="rq1_cube")

    st.markdown("##### Which channels are least studied")
    st.caption(
        "Each channel has 18 cells (3 intents x 6 consequences). This counts how many "
        "of those 18 have at least one paper — so a long grey bar means that entry "
        "point into the context window is barely studied, whatever the consequence."
    )
    rows = []
    for ch in channels:
        filled_ch = sum(1 for intent in CUBE_INTENTS for co in conseq
                        if (intent, ch, co) in cells)
        n_cells = len(CUBE_INTENTS) * len(conseq)
        rows.append({"Channel": ch, "Cells filled": filled_ch,
                     "Cells empty": n_cells - filled_ch,
                     "Empty %": round(100 * (n_cells - filled_ch) / n_cells, 1),
                     "Papers": sum(v for (t, c, co), v in cells.items() if c == ch)})
    cdf = pd.DataFrame(rows).sort_values("Empty %", ascending=False)
    left, right = st.columns([3, 2])
    with left:
        f2 = go.Figure()
        f2.add_trace(go.Bar(y=cdf["Channel"], x=cdf["Cells filled"], orientation="h",
                            name="studied", marker_color="#3d5a80", text=cdf["Cells filled"],
                            textposition="inside", textfont=dict(color="white", size=10)))
        f2.add_trace(go.Bar(y=cdf["Channel"], x=cdf["Cells empty"], orientation="h",
                            name="empty", marker_color="#dee2e6", text=cdf["Cells empty"],
                            textposition="inside", textfont=dict(color="#495057", size=10)))
        f2.update_layout(barmode="stack", height=max(260, 30 * len(cdf) + 110),
                         margin=dict(l=10, r=10, t=40, b=10),
                         yaxis=dict(autorange="reversed"),
                         xaxis_title=f"cells (of {len(CUBE_INTENTS)*len(conseq)} per channel)",
                         legend=dict(orientation="h", yanchor="bottom", y=1.0,
                                     xanchor="right", x=1))
        st.plotly_chart(f2, width="stretch", key="rq1_channel_fill")
    with right:
        st.dataframe(cdf, width="stretch", hide_index=True, height=380)


def cross_citation_section() -> None:
    overall, by_year, by_grade, same, nA, nB = cross_citation_stats(
        (registry_source.REPO_ROOT / registry_source.PAPERS_XLSX).stat().st_mtime)
    st.markdown("##### RQ2 — how often does either track cite the other?")
    ab_h, ab_n, ab_p = overall["A->B"]
    ba_h, ba_n, ba_p = overall["B->A"]
    m = st.columns(3)
    m[0].metric("Security papers citing ML/AI work", f"{ab_p:.1f}%", help=f"{ab_h} of {ab_n}")
    m[1].metric("ML/AI papers citing Security work", f"{ba_p:.1f}%", help=f"{ba_h} of {ba_n}")
    m[2].metric("Papers bridging both", nA + nB and
                f"{100*(ab_h+ba_h)/(nA+nB):.1f}%", help=f"{ab_h+ba_h} of {nA+nB}")

    left, right = st.columns(2)
    with left:
        yrs = sorted(by_year)
        f = go.Figure()
        for key, colour, label in (("A->B", REGISTRY_TRACK_COLORS["Security"], "Security -> cites ML/AI"),
                                   ("B->A", REGISTRY_TRACK_COLORS["ML/AI"], "ML/AI -> cites Security")):
            f.add_trace(go.Scatter(
                x=yrs, y=[by_year[y][key][2] for y in yrs], mode="lines+markers+text",
                name=label, line=dict(color=colour, width=2.5), marker=dict(size=9),
                text=[f"{by_year[y][key][2]:.0f}%" for y in yrs], textposition="top center",
                textfont=dict(size=10),
                customdata=[[by_year[y][key][0], by_year[y][key][1]] for y in yrs],
                hovertemplate="%{x}<br>%{customdata[0]} of %{customdata[1]} papers<extra></extra>"))
        f.update_layout(title="Cross-citation rate by year", height=340,
                        margin=dict(l=10, r=10, t=45, b=10),
                        yaxis_title="% of track citing the other", xaxis_title="Year",
                        legend=dict(orientation="h", yanchor="bottom", y=1.0,
                                    xanchor="right", x=1))
        st.plotly_chart(f, width="stretch", key="rq2_by_year")
    with right:
        gs = sorted(by_grade)
        f = go.Figure()
        for key, colour, label in (("A->B", REGISTRY_TRACK_COLORS["Security"], "Security -> cites ML/AI"),
                                   ("B->A", REGISTRY_TRACK_COLORS["ML/AI"], "ML/AI -> cites Security")):
            f.add_trace(go.Bar(
                x=gs, y=[by_grade[g][key][2] for g in gs], name=label, marker_color=colour,
                text=[f"{by_grade[g][key][2]:.0f}%" for g in gs], textposition="outside",
                customdata=[[by_grade[g][key][0], by_grade[g][key][1]] for g in gs],
                hovertemplate="grade %{x}<br>%{customdata[0]} of %{customdata[1]}<extra></extra>"))
        f.update_layout(barmode="group", title="Cross-citation rate by evidence grade",
                        height=340, margin=dict(l=10, r=10, t=45, b=10),
                        yaxis_title="% citing the other track", xaxis_title="Evidence grade",
                        legend=dict(orientation="h", yanchor="bottom", y=1.0,
                                    xanchor="right", x=1))
        st.plotly_chart(f, width="stretch", key="rq2_by_grade")
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
    # Scope every paper view to the papers actually carried into the analysis.
    # Rows screened out during coding belong to the audit trail (rescreening_log.md),
    # not to what this dashboard reports.
    df = df[df["effective_screen"] != "auto_exclude"].reset_index(drop=True)
    edges = load_edges(db_path)
    n_analysed = n_papers_in_research(mtime)

    if df.empty:
        st.warning(f"`{excel_path}` has no paper rows. Add some and refresh.")
        return

    st.caption(
        f"{n_analysed} papers in the analysis · data source `{excel_path}`, last saved "
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
    screens = sorted(df["effective_screen"].dropna().unique().tolist())
    keyword = st.sidebar.text_input("Keyword (title/abstract)")

    filtered = apply_filters(df, tracks, year_range, venues, hops, screens, keyword)
    st.sidebar.caption(f"{len(filtered)} of {len(df)} papers shown")

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
        "Overview", "Paper index", "Taxonomy (RQ1)", "Attacks & mechanisms", "Defenses",
        "Coverage matrix", "Transfer predictions", "RQ findings",
        "Paper timeline", "Citation network",
    ])
    with tabs[0]:
        if reg:
            overview_tab(reg, summaries, n_analysed)
    with tabs[1]:
        paper_index_tab(db_path)
    with tabs[2]:
        taxonomy_tab()
    with tabs[3]:
        if reg:
            mechanisms_tab(reg)
    with tabs[4]:
        if reg:
            defenses_tab(reg)
    with tabs[5]:
        if reg:
            coverage_tab(reg)
    with tabs[6]:
        if reg:
            transfer_tab(reg)
    with tabs[7]:
        findings_tab(summaries)
    with tabs[8]:
        timeline_tab(filtered)
    with tabs[9]:
        cross_citation_section()
        network_tab(filtered, edges)


if __name__ == "__main__":
    main()

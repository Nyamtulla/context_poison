"""The per-paper scorecard, shared by both dashboards.

Lives here rather than in either dashboard because the context-centric view
and the corpus workbench both need it, and two copies would drift. Reads
`data/paper_explorer.db` only - no dependency on the Excel source or the
registry JSON.
"""
from __future__ import annotations

import sqlite3

import pandas as pd
import streamlit as st

from src import registry_source

# Separate from the registry tabs on purpose. Those answer "what does the
# field look like"; this answers "I am holding one paper - what did it claim,
# and what happened to it afterwards".

EXPLORER_DB = "data/paper_explorer.db"

ROLE_COLOR = {"attack": "#a4402c", "defense": "#2f5d7c",
              "both": "#6b4b8a", "neither": "#8d8880"}
OUTCOME_LABEL = {
    "holds": "defense held",
    "loses": "DEFENSE BROKEN",
    "partial": "reduced, not stopped",
    "undetermined": "ran it, no result given",
}
DIRECTION_LABEL = {
    "defense_paper": "the defense paper's own claim",
    "attack_paper": "reported by the ATTACK paper",
}


def optional_table(conn, name: str) -> pd.DataFrame:
    """Read a table that may not exist yet.

    `untested_defense` is built by a second script after this database, so a
    freshly rebuilt db legitimately lacks it. Missing means the panel is
    skipped, not that the tab breaks.
    """
    try:
        return pd.DataFrame([dict(r) for r in
                             conn.execute(f"SELECT * FROM {name}")])
    except Exception:
        return pd.DataFrame()


def counts_to_int(df: pd.DataFrame, columns) -> pd.DataFrame:
    """Make count columns real integers, treating a missing count as zero.

    The scorecard views LEFT JOIN `pair`, so a technique nobody has ever
    tested yields COUNT = 0 but SUM = NULL. That arrives here as NaN, and
    `nan or 0` is nan rather than 0 because nan is truthy - which crashed
    st.metric for all 322 defenses with no recorded pair.
    """
    for c in columns:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    return df


@st.cache_data(ttl=300)
def load_explorer(mtime: float) -> dict:
    """Everything the scorecard needs, in one read.

    Keyed on the file's mtime so rebuilding the db with
    `scripts/build_paper_db.py` invalidates the cache on the next refresh.
    """
    conn = sqlite3.connect(registry_source.REPO_ROOT / EXPLORER_DB)
    conn.row_factory = sqlite3.Row
    out = {
        "papers": pd.DataFrame(
            [dict(r) for r in conn.execute("SELECT * FROM paper")]),
        "pairs": pd.DataFrame(
            [dict(r) for r in conn.execute("SELECT * FROM pair")]),
        "defense_score": counts_to_int(pd.DataFrame(
            [dict(r) for r in conn.execute("SELECT * FROM v_defense_scorecard")]),
            ("attacks_tested", "self_reported_win", "refuted", "partial",
             "undetermined", "tested_by_attack_paper")),
        "attack_score": counts_to_int(pd.DataFrame(
            [dict(r) for r in conn.execute("SELECT * FROM v_attack_scorecard")]),
            ("defenses_tested", "defenses_broken", "defenses_partial",
             "defenses_held_claimed", "undetermined")),
        "runs": pd.DataFrame(
            [dict(r) for r in conn.execute("SELECT * FROM our_run")]),
        "untested": optional_table(conn, "untested_defense"),
    }
    conn.close()
    return out


def _pair_table(pairs: pd.DataFrame, other_col: str) -> None:
    """Render one technique's pairs, worst news first.

    Sorted so a broken defense is the first thing read, because that is the
    result a reader would otherwise have to hunt for - the defense papers'
    claimed wins are the majority of every list.
    """
    if pairs.empty:
        st.caption("No pair recorded in either direction.")
        return
    order = {"loses": 0, "partial": 1, "holds": 2, "undetermined": 3}
    pairs = pairs.assign(_o=pairs["outcome"].map(order)).sort_values("_o")
    shown = pd.DataFrame({
        "": pairs[other_col],
        "Result": pairs["outcome"].map(OUTCOME_LABEL),
        "Who reported it": pairs["direction"].map(DIRECTION_LABEL),
        "In": pairs["reported_by_title"].fillna(""),
    })
    st.dataframe(shown, width="stretch", hide_index=True)
    with_ev = pairs[pairs["evidence"].notna() & (pairs["evidence"] != "")]
    if not with_ev.empty:
        with st.expander(f"Quoted evidence ({len(with_ev)})"):
            for _, r in with_ev.iterrows():
                st.markdown(
                    f"**{r[other_col]}** — _{OUTCOME_LABEL[r['outcome']]}_  \n"
                    f"{str(r['evidence'])[:900]}")


CLASSIFICATION_BLURB = {
    "names_registry_attack": (
        "Names an attack that **is** in our registry",
        "Its own paper names these attacks, but no confirmed (defense, attack) "
        "pair exists for them. These are candidate missed pairs — a name in the "
        "text is not proof the defense was run against it, so each needs the "
        "same adjudication the reverse scan used."),
    "names_benchmark": (
        "Evaluated on a named benchmark suite",
        "It ran adversarial inputs, but named only the suite, not the attacks "
        "inside it. Expanding a suite to its constituent attacks would "
        "manufacture coverage, so this stays unresolved on purpose."),
    "self_constructed": (
        "Built and ran its own attacks",
        "It was tested adversarially against attacks the authors constructed. "
        "Nobody else named them, so there is no shared entity to match on."),
    "threat_named_only": (
        "States an adversarial threat in general terms",
        "It says what it defends, but names no specific attack and no suite."),
    "non_adversarial": (
        "Not an adversarial defense",
        "It addresses incidental context degradation. \"Which attack was it "
        "tested against\" is the wrong question for this paper."),
    "unclassified": (
        "Could not be classified from the coded text",
        "Its threat model and evaluation fields did not yield a threat label, "
        "an attack name, or a benchmark. Needs a human read."),
}


def _untested_defense_panel(name: str, untested: pd.DataFrame | None) -> None:
    """What this defense defends, when no pair was ever confirmed for it.

    Showing five zeros here would say the paper defends nothing, which is
    false for all 320 defenses in this state - 268 of them state a formal
    threat model. The zero is a naming gap in our registry, not an evaluation
    gap in the paper, and this panel says which.
    """
    if untested is None or untested.empty:
        st.info(
            "No confirmed pair for this defense. Run "
            "`python3 scripts/classify_untested_defenses.py` to see what it "
            "says it defends against.")
        return
    hit = untested[untested["defense"] == name]
    if hit.empty:
        st.info("No confirmed pair, and no classification recorded.")
        return
    r = hit.iloc[0]
    title, why = CLASSIFICATION_BLURB.get(
        r["classification"], ("Unclassified", ""))

    st.warning(
        "**No (defense, attack) pair has ever been confirmed for this "
        "defense.** That is a gap in our attack registry's naming, not a "
        "claim that the paper defends nothing.", icon=":material/info:")
    st.markdown(f"**{title}**")
    if why:
        st.caption(why)

    if r["defends_against"]:
        st.markdown("**It says it defends against:** "
                    + ", ".join(f"`{t}`" for t in r["defends_against"].split(" | ")))
    if r["names_registry_attacks"]:
        st.markdown("**Registry attacks named in its own text — candidate "
                    "missed pairs:**")
        for a in r["names_registry_attacks"].split(" | "):
            st.markdown(f"- {a}")
    if r["names_benchmarks"]:
        st.markdown("**Benchmarks it evaluated on:** "
                    + ", ".join(f"`{b}`" for b in r["names_benchmarks"].split(" | ")))

    peers = int(r["taxonomy_cell_peers"] or 0)
    if peers:
        with st.expander(
                f"{peers} registry attacks sit in the same taxonomy cell — "
                "none has been run against this defense"):
            st.caption(
                "A weak relation, shown for orientation only. Sharing a "
                "(channel, consequence) cell is not the same threat, and this "
                "is never counted as coverage.")
            for a in str(r["taxonomy_cell_peer_examples"]).split(" | ")[:8]:
                st.markdown(f"- {a}")


def _technique_card(name: str, kind: str, score: pd.Series,
                    pairs: pd.DataFrame,
                    untested: pd.DataFrame | None = None) -> None:
    colour = ROLE_COLOR["attack" if kind == "attack" else "defense"]
    st.markdown(
        f"<div style='font-size:11px;letter-spacing:.06em;text-transform:uppercase;"
        f"font-weight:700;color:{colour}'>"
        f"{'Attack introduced' if kind == 'attack' else 'Defense introduced'}</div>",
        unsafe_allow_html=True)
    st.markdown(f"##### {name}")

    if kind == "defense" and int(score["attacks_tested"]) == 0:
        _untested_defense_panel(name, untested)
        return

    if kind == "defense":
        cells = [("Attacks tested against it", score["attacks_tested"]),
                 ("Its own paper says it stopped", score["self_reported_win"]),
                 ("An attack paper broke it", score["refuted"]),
                 ("Reduced, not stopped", score["partial"]),
                 ("Ran, no result given", score["undetermined"])]
        other = "attack_name"
    else:
        cells = [("Defenses run against it", score["defenses_tested"]),
                 ("It broke", score["defenses_broken"]),
                 ("It only weakened", score["defenses_partial"]),
                 ("Held, per that defense's paper", score["defenses_held_claimed"]),
                 ("Ran, no result given", score["undetermined"])]
        other = "defense_name"
    cols = st.columns(len(cells))
    for col, (label, value) in zip(cols, cells):
        col.metric(label, int(value))

    _pair_table(pairs, other)


def paper_scorecard_tab() -> None:
    path = registry_source.REPO_ROOT / EXPLORER_DB
    if not path.exists():
        st.warning(
            "No `data/paper_explorer.db` yet. Build it with "
            "`python3 scripts/build_paper_db.py`.")
        return
    data = load_explorer(path.stat().st_mtime)
    papers, pairs = data["papers"], data["pairs"]

    st.markdown("#### Paper scorecard — what did this paper claim, and what happened next?")
    st.caption(
        "Pick a paper and see its role, the technique it introduced, and how that "
        "technique fared against the other side. Counts are never combined across "
        "directions: a defense paper claiming a win and an attack paper reporting "
        "that same defense broken are different kinds of evidence."
    )

    c1, c2 = st.columns([3, 2])
    query = c1.text_input("Search title, author, venue, or technique name",
                          key="scorecard_q")
    roles = c2.multiselect("Role", ["attack", "defense", "both", "neither"],
                           default=["attack", "defense", "both"],
                           key="scorecard_roles")

    sub = papers[papers["role"].isin(roles)] if roles else papers
    if query and len(query.strip()) >= 2:
        q = query.strip().lower()
        tech_hits = set(
            pairs.loc[pairs["defense_name"].str.lower().str.contains(q, na=False),
                      "defense_name"]) | set(
            pairs.loc[pairs["attack_name"].str.lower().str.contains(q, na=False),
                      "attack_name"])
        by_tech = set(
            data["defense_score"].loc[
                data["defense_score"]["defense"].isin(tech_hits), "paper_id"]) | set(
            data["attack_score"].loc[
                data["attack_score"]["attack"].isin(tech_hits), "paper_id"])
        hay = (sub["title"].fillna("") + " " + sub["authors"].fillna("") + " "
               + sub["venue"].fillna("")).str.lower()
        sub = sub[hay.str.contains(q, regex=False) | sub["paper_id"].isin(by_tech)]

    st.caption(f"{len(sub)} of {len(papers)} papers match.")
    if sub.empty:
        st.info("Nothing matches. Try fewer words, or widen the role filter.")
        return

    sub = sub.sort_values(["year", "title"], ascending=[False, True])
    labels = {
        r["paper_id"]: f"[{r['role']}] {r['title']}  ({r['year'] or '—'})"
        for _, r in sub.iterrows()
    }
    pid = st.selectbox("Paper", list(labels), format_func=lambda k: labels[k],
                       key="scorecard_pick")
    row = papers[papers["paper_id"] == pid].iloc[0]

    st.divider()
    st.markdown(f"### {row['title']}")
    st.markdown(
        f"<span style='color:{ROLE_COLOR[row['role']]};font-weight:700;"
        f"text-transform:uppercase;letter-spacing:.05em;font-size:12px'>"
        f"{row['role']} paper</span>", unsafe_allow_html=True)
    st.caption(f"{row['authors'] or 'unknown authors'} · {row['year'] or '—'} · "
               f"{row['venue'] or 'no venue'} · {row['track'] or ''}")
    if row["url"]:
        st.markdown(f"[Open the paper]({row['url']})")

    k = st.columns(4)
    k[0].metric("Evidence grade", row["evidence_grade"] or "—")
    k[1].metric("Artifacts released", row["artifacts_released"] or "—")
    k[2].metric("Citations", int(pd.to_numeric(
        row["citation_count"], errors="coerce") or 0))
    k[3].metric("Channel", row["channel"] or "—")

    dfs = data["defense_score"][data["defense_score"]["paper_id"] == pid]
    atk = data["attack_score"][data["attack_score"]["paper_id"] == pid]

    for _, s in dfs.iterrows():
        st.divider()
        _technique_card(s["defense"], "defense", s,
                        pairs[pairs["defense_name"] == s["defense"]],
                        data["untested"])
    for _, s in atk.iterrows():
        st.divider()
        _technique_card(s["attack"], "attack", s,
                        pairs[pairs["attack_name"] == s["attack"]])

    if dfs.empty and atk.empty:
        st.info(
            "This paper is in the corpus but introduced neither a named attack nor a "
            "named defense — background, a survey, or a technique that did not meet "
            "the registry's naming bar.")

    ours = data["runs"][data["runs"]["attack"].isin(atk["attack"].tolist())]
    if not ours.empty:
        st.divider()
        st.markdown("##### We ran this attack ourselves")
        st.caption(
            "Kept separate from the counts above, which are what *papers* reported. "
            "These are our own executed episodes.")
        st.dataframe(
            ours[["technique_name", "attack", "n", "undefended_asr",
                  "defended_asr", "drop_pp", "mdr_pp", "verdict"]],
            width="stretch", hide_index=True)

    with st.expander("What the numbers do and do not mean"):
        st.markdown(
            "- **\"Its own paper says it stopped\"** is a claim, not a verified "
            "result. Across the corpus, defense papers report 193 wins and 0 losses.\n"
            "- **\"An attack paper broke it\"** is the other direction: 38 reported "
            "losses and 0 wins. A defense paper written before an attack existed "
            "cannot report losing to it, which is why this column exists at all.\n"
            "- **\"Ran, no result given\"** covers pairs where we can confirm the "
            "run happened but no directional outcome was reported — 115 of the 349 "
            "pairs. Tested is not the same as worked, and these are never counted "
            "as either.\n"
            "- Rebuild with `python3 scripts/build_paper_db.py` after any registry "
            "change, then refresh this page."
        )

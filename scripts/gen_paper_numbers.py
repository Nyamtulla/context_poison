"""Emit every corpus-derived figure in the paper as a LaTeX macro.

The paper must never contain a hand-typed count. Four numbers in the first
draft were wrong because prose and analysis drifted apart: the bibliography
size, the no-mechanism paper count, the coded-field count, and the
single-mechanism testing rate, which mixed two different pair sets. Each had
been correct when it was typed.

Run this after any corpus rebuild, registry rebuild, or new experiment:

    python3 scripts/gen_paper_numbers.py

It rewrites latex/numbers.tex. The section files reference \\NCorpus and never
the literal 984, so a rebuild updates the paper everywhere at once.

Experiment effect sizes are NOT macroised. They come from completed runs on
fixed items and do not move when the corpus is rescreened; macroising them
would hide which numbers are live and which are settled.
"""
import collections
import json
import pathlib
import sys

import openpyxl


def _t(s):
    import re
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())

REPO = pathlib.Path(__file__).resolve().parent.parent
R = REPO / "data" / "registries"
sys.path.insert(0, str(REPO / "scripts"))


def load(name):
    return json.loads((R / name).read_text())


def corpus_rows():
    wb = openpyxl.load_workbook(
        REPO / "data" / "exports" / "paper_dashboard_source.xlsx", read_only=True)
    ws = wb["Papers"]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    return list(rows[0]), rows[1:]


def main():
    hdr, rows = corpus_rows()
    si, pi = hdr.index("screening"), hdr.index("paper_id")
    included = {r[pi] for r in rows if str(r[si]).strip() != "Exclude"}
    M = {}

    # ---- corpus
    M["NScreened"] = len(rows)
    # provenance stages, for the PRISMA figure's prose (see gen_provenance.py)
    import sqlite3 as _sq
    _c = _sq.connect(REPO / "data" / "context_sok.db")
    _g = lambda q: list(_c.execute(q))[0][0]
    M["NQueries"] = _g("select count(*) from search_log")
    M["NSurvived"] = _g("select count(*) from papers where hop<=1 and "
                        "screen_auto in ('auto_include','needs_review')")
    M["NFullText"] = len(rows)
    _c.close()
    M["NCorpus"] = len(included)
    M["NExcluded"] = len(rows) - len(included)
    M["NColumns"] = len(hdr)
    # coded fields are everything that is not bibliographic metadata
    META = {"paper_id", "title", "authors", "year", "venue", "citation_count",
            "doi", "arxiv_id", "url", "pdf_local_path", "discovered_via",
            "discovered_query", "hop", "seed_category", "abstract"}
    M["NCodedFields"] = len([h for h in hdr if h not in META])

    # ---- registries, restricted to papers still IN the corpus.
    # Excluding a paper from the workbook does not delete its registry entry,
    # so after the 2026-10-16 contribution screen the raw file still held 9
    # defenses from removed papers. Left unfiltered, NDefenses said 527 while
    # NPapersDef said 518 and the two macros described different corpora.
    r3 = [e for e in load("rq3_pollution_registry.json")
          if e.get("paper_id") in included]
    r4 = [e for e in load("rq4_defense_registry.json")
          if e.get("paper_id") in included]
    M["NMechanisms"] = len(r3)
    tr3 = collections.Counter(e.get("track") for e in r3)
    M["NMechSecurity"], M["NMechML"] = tr3["Security"], tr3["ML/AI"]
    cq = collections.Counter(e.get("consequence") for e in r3)
    M["NGoalHijack"] = cq["goal-hijack"]
    # the consequence x track split. The prose used to say EVERY goal-hijack
    # mechanism was security-track; after the full-text re-coding that is one
    # paper short of true, so the claim is now carried by counts.
    _ct = collections.defaultdict(collections.Counter)
    for e in r3:
        _ct[(e.get("consequence") or "").strip()][(e.get("track") or "").strip()] += 1
    M["NGoalHijackSec"] = _ct["goal-hijack"]["Security"]
    M["NGoalHijackML"] = _ct["goal-hijack"]["ML/AI"]
    M["NReasonML"] = _ct["reasoning-corruption"]["ML/AI"]
    M["NReasonSec"] = _ct["reasoning-corruption"]["Security"]
    M["PctGoalHijack"] = f'{100*cq["goal-hijack"]/len(r3):.1f}'

    M["NDefenses"] = len(r4)
    va = collections.Counter(e.get("validated_against") for e in r4)
    M["NAdvOnly"], M["NIncOnly"] = va["adversarial"], va["incidental"]
    M["NBothValidated"], M["NNoValidation"] = va["both"], va[""]
    M["PctBothValidated"] = f'{100*va["both"]/len(r4):.1f}'
    # Named "regime", not "threat model". In security a threat model is a
    # specification of the adversary; "incidental" has no adversary at all,
    # so the binary is which regime a paper's own evaluation covered.
    M["PctOneRegime"] = f'{100*(1-va["both"]/len(r4)):.0f}'
    # The re-coding emptied resource-abuse almost completely; the prose used
    # to say "three mechanisms and three defenses" as literal numbers.
    M["NMechResourceAbuse"] = sum(
        1 for e in r3 if (e.get("consequence") or "").strip() == "resource-abuse")
    M["NDefResourceAbuse"] = sum(
        1 for e in r4 if (e.get("consequence") or "").strip() == "resource-abuse")
    # Track and regime are coded independently; they are also almost the same
    # partition. Count the defenses validated in the OTHER track's regime.
    _other = {"Security": "incidental", "ML/AI": "adversarial"}
    M["NDefCrossRegime"] = sum(
        1 for e in r4
        if _other.get((e.get("track") or "").strip())
        == (e.get("validated_against") or "").strip())
    tr4 = collections.Counter(e.get("track") for e in r4)
    M["NDefML"], M["NDefSecurity"], M["NDefBoth"] = tr4["ML/AI"], tr4["Security"], tr4["Both"]
    ip = collections.Counter(e.get("defense_intervention_point") for e in r4)
    for k, v in [("Reasoning", "reasoning"), ("Ingestion", "ingestion"),
                 ("Execution", "execution"), ("NoPoint", "none")]:
        M["NDef" + k] = ip[v]

    # ---- which papers contribute what
    mech_p = {e.get("paper_id") for e in r3} & included
    def_p = {e.get("paper_id") for e in r4} & included
    M["NPapersMech"], M["NPapersDef"] = len(mech_p), len(def_p)
    M["NPapersBoth"] = len(mech_p & def_p)
    M["NPapersNeither"] = len(included - mech_p - def_p)

    # ---- coverage. Everything derives from ONE pair set, the composite in
    # pair_tally.composite_pairs(). RQ5's published 332 pairs and 106 covered
    # mechanisms predate reverse-scan pass 3 and are kept only as the labelled
    # base figures, never recomputed.
    from pair_tally import composite_pairs, attack_universe
    cov = load("rq5_coverage_matrix.json")
    pairs, _ = composite_pairs()
    uni = set(attack_universe())
    M["NMechanismsBench"] = len(uni)
    M["NPairsComposite"] = len(pairs)
    M["NPairsBase"] = cov["n_matched_pairs"]

    covered = {a for _, a in pairs} & uni
    M["NMechCovered"] = len(covered)
    M["NMechUncovered"] = len(uni) - len(covered)
    M["PctMechUncovered"] = f'{100*M["NMechUncovered"]/len(uni):.1f}'
    M["PctMechCovered"] = f'{100*len(covered)/len(uni):.1f}'

    per_def = collections.Counter(d for d, _ in pairs)
    dist = collections.Counter(per_def.values())
    M["NDefMatchedFull"] = len(per_def)
    M["PctDefMatched"] = f'{100*len(per_def)/len(r4):.1f}'
    M["NDefOneFull"] = dist[1]
    M["PctDefOneFull"] = f'{100*dist[1]/len(per_def):.1f}'
    M["NDefCeiling"] = max(per_def.values())
    M["NDefFourPlus"] = sum(v for k, v in dist.items() if k >= 4)
    # base-matrix figures, as RQ5 published them, for the contrast in S6
    M["NDefMatchedBase"], M["NDefOneBase"] = 197, 163
    M["PctDefOneBase"] = f'{100*163/197:.1f}' 

    # ---- the execution campaign. These move every time a run lands, which
    # is why they are macros: the first draft hardcoded 81 pairs and 156,308
    # episodes and was stale within a day of CK-PLUG finishing.
    from pair_tally import retrieval_runs
    runs = retrieval_runs()
    transfer = [r for r in runs if r["role"] == "transfer"]
    rag_pairs = {(r["defense"], r["attack"]) for r in transfer}
    rag_keys = {(r["dkey"], r["akey"]) for r in transfer}
    lit = [(_t(d), _t(a)) for d, a in pairs]
    novel = [k for k in rag_keys
             if not any(k[0] in ld and k[1] in la for ld, la in lit)]
    agent = json.loads((R / "technique_transfer_full_banking.json").read_text())
    scored = [r for r in agent["results"] if not r.get("error")]
    agent_pairs = {(r["technique_name"], r["attack"]) for r in scored}
    agent_eps = sum(r["undefended"]["n"] + r["defended"]["n"] for r in scored)
    rag_eps = sum(r["episodes"] for r in runs)

    M["NRagPairs"] = len(rag_pairs)
    M["NRagPairsKeyed"] = len(rag_keys)
    M["NRagPairsNovel"] = len(novel)
    M["NRagEpisodes"] = f"{rag_eps:,}"
    M["NRagImpl"] = len({r["defense"] for r in transfer})
    M["NAgentPairs"] = len(agent_pairs)
    M["NAgentEpisodes"] = f"{agent_eps:,}"
    M["NAgentTechniques"] = len({r["technique_name"] for r in scored})
    M["NCampaignPairs"] = len(rag_pairs) + len(agent_pairs)
    M["NCampaignImpl"] = (len({r["defense"] for r in transfer})
                          + len({r["technique_name"] for r in scored}))
    M["NCampaignEpisodes"] = f"{rag_eps + agent_eps:,}"

    # ---- the taxonomy cube and the per-axis splits.
    # Computed exactly as fig_cube does: over PAPER rows, one (channel,
    # consequence) per paper, split by track. These were typed into the prose
    # and went stale the moment the corpus moved: the text still said 98 empty
    # cells of 162 when it had become 111.
    CHS = ["direct-input", "tool-output", "RAG", "memory", "multi-agent",
           "cross-modal", "tool-metadata", "skill", "supply-chain"]
    # availability-loss added 2026-10-21: the agent cannot finish at all.
    # The cube is 9 x 7 x 3 = 189 cells, not 162. Adding a sparse column
    # RAISES the empty-cell percentage for a reason that has nothing to do
    # with the field changing, so the prose must say why.
    CQS = ["goal-hijack", "reasoning-corruption", "silent-corruption",
           "data-exfiltration", "persistence-backdoor", "resource-abuse",
           "availability-loss"]
    ci, qi, ti = hdr.index("channel"), hdr.index("consequence"), hdr.index("track")
    occupied = set()
    for r in rows:
        if r[pi] not in included:
            continue
        c, q, tr = (str(r[ci] or "").strip(), str(r[qi] or "").strip(),
                    str(r[ti] or "").strip())
        if c in CHS and q in CQS and tr in ("Security", "ML/AI"):
            occupied.add((c, q, tr))
    NCELLS = len(CHS) * len(CQS) * 3      # 3 intents: adversarial, incidental, both
    M["NCubeCells"] = NCELLS
    M["NCubeEmpty"] = NCELLS - len(occupied)
    # papers that carry no channel or no consequence: multi-vector surveys
    # and benchmarks whose surfaces are co-equal by construction. They are
    # outside the cube by construction, and the empty-cell rate is only
    # honest if their number is stated.
    _unp = sum(1 for r in rows if r[pi] in included
               and (str(r[ci] or "").strip() in ("", "none")
                    or str(r[qi] or "").strip() in ("", "none")))
    M["NUnplaceable"] = _unp
    M["PctUnplaceable"] = f"{100*_unp/len(included):.1f}"
    M["PctCubeEmpty"] = f"{100*(NCELLS-len(occupied))/NCELLS:.1f}"

    # mechanism registry splits, quoted in S4
    _mq = collections.Counter(e.get("consequence") for e in r3)
    _mc = collections.Counter(e.get("channel") for e in r3)
    for key, src, pre in (("goal-hijack", _mq, "MechGoalHijack"),
                          ("reasoning-corruption", _mq, "MechReasoning"),
                          ("silent-corruption", _mq, "MechSilent"),
                          ("direct-input", _mc, "MechDirectInput"),
                          ("tool-output", _mc, "MechToolOutput"),
                          ("RAG", _mc, "MechRAG")):
        M["N" + pre] = src[key]
        M["Pct" + pre] = f"{100*src[key]/len(r3):.1f}"
    # defense intervention points, quoted in S4
    _ip = collections.Counter((e.get("defense_intervention_point") or "none").strip()
                              for e in r4)
    for key, pre in (("reasoning", "DefPtReasoning"), ("ingestion", "DefPtIngestion"),
                     ("execution", "DefPtExecution"), ("none", "DefPtNone")):
        M["N" + pre] = _ip[key]
        M["Pct" + pre] = f"{100*_ip[key]/len(r4):.1f}"

    # injection variants with no tested defense, quoted in S5
    _inj = [a for a in uni if "inject" in a.lower()]
    M["NInjVariants"] = len(_inj)
    M["NInjUncovered"] = sum(1 for a in _inj if a not in covered)

    # ---- the temporal layer. Which community's defense met which
    # community's attack, and in what order. The 2x2 counts the two pure
    # tracks only, because a "Both"-track paper cannot cross a boundary it
    # sits on; the all-pairs figure is kept beside it so neither reading is
    # lost.
    # --- parallel arrival: who reaches each channel first, and how late is
    # the other one. This is the measurement behind the claim that the two
    # communities rediscover the same problem rather than building on each
    # other. A channel where both have named a mechanism is shared ground;
    # the gap is between the first paper from each side.
    _hdr, _rows = corpus_rows()
    _h = {k: i for i, k in enumerate(_hdr) if k}
    _yr = {r[_h["paper_id"]]: r[_h["year"]] for r in _rows
           if r[_h["paper_id"]] and r[_h["year"]]}
    _mech = load("rq3_pollution_registry.json")
    _mech = _mech if isinstance(_mech, list) else (
        _mech.get("entries") or _mech.get("mechanisms"))
    _first = {}
    for e in _mech:
        y, ch, tr = _yr.get(e.get("paper_id")), e.get("channel"), e.get("track")
        if not (y and ch) or tr not in ("Security", "ML/AI"):
            continue
        y = int(str(y).split(".")[0])
        _first.setdefault(ch, {}).setdefault(tr, []).append(y)
    _shared = {c: v for c, v in _first.items() if len(v) == 2}
    _gaps = {c: min(v["ML/AI"]) - min(v["Security"]) for c, v in _shared.items()}
    M["NSharedChannels"] = len(_shared)
    M["NChannelsSecFirst"] = sum(1 for g in _gaps.values() if g > 0)
    M["NChannelsSameYear"] = sum(1 for g in _gaps.values() if g == 0)
    M["NChannelsMLFirst"] = sum(1 for g in _gaps.values() if g < 0)
    _lead = sorted(g for g in _gaps.values() if g > 0)
    M["MedianChannelLag"] = (_lead[len(_lead) // 2] if _lead else 0)
    M["MaxChannelLag"] = (max(_lead) if _lead else 0)

    tl = load("pair_timeline.json")["pairs"]
    M["NTimelinePairs"] = len(tl)
    _pre = [r for r in tl if r["defense_predates_attack"]]
    M["NDefensePredates"] = len(_pre)
    M["PctDefensePredates"] = f"{100*len(_pre)/len(tl):.1f}"
    _pure = [r for r in tl if r["defense_track"] in ("Security", "ML/AI")
             and r["attack_track"] in ("Security", "ML/AI")]
    _x = [r for r in _pure if r["defense_track"] != r["attack_track"]]
    M["NPureTrackPairs"] = len(_pure)
    M["NCrossCommunityPairs"] = len(_x)
    M["PctCrossCommunity"] = f"{100*len(_x)/len(_pure):.1f}"
    M["NCrossAllPairs"] = sum(1 for r in tl
                              if r["defense_track"] != r["attack_track"])
    M["NSecDefVsMLAttack"] = sum(1 for r in _pure
                                 if r["defense_track"] == "Security"
                                 and r["attack_track"] == "ML/AI")
    M["NMLDefVsSecAttack"] = sum(1 for r in _pure
                                 if r["defense_track"] == "ML/AI"
                                 and r["attack_track"] == "Security")
    # the two diagonal cells of the transfer matrix, so Table 1 and the
    # sentence under it cannot drift apart
    M["NSecDefSecAttack"] = sum(1 for r in _pure
                                if r["defense_track"] == "Security"
                                and r["attack_track"] == "Security")
    M["NMLDefMLAttack"] = sum(1 for r in _pure
                              if r["defense_track"] == "ML/AI"
                              and r["attack_track"] == "ML/AI")
    _same = sum(1 for r in tl if r["defense_track"] == r["attack_track"])
    M["NSameTrackPairs"] = _same
    M["PctSameTrack"] = f"{100*_same/len(tl):.1f}"
    M["NPredatesAndCross"] = sum(1 for r in _pure
                                 if r["defense_predates_attack"]
                                 and r["defense_track"] != r["attack_track"])
    # the same matrix for what we executed
    _DT = {"ParamMute": "ML/AI", "CK-PLUG": "ML/AI", "COIECD": "ML/AI",
           "ACD": "ML/AI", "DyPRAG": "ML/AI", "FaithfulRAG": "ML/AI",
           "SpARE": "ML/AI", "SCR": "ML/AI",
           "RobustRAG-DecodingAgg": "Security", "RobustRAG-KeywordAgg": "Security"}
    _AT = {"corpus poisoning": "Security", "PoisonedRAG": "Security",
           "BadRAG sentiment steering": "Security",
           "BadRAG denial-of-service": "Security",
           "false evidence": "ML/AI", "distractor evidence": "ML/AI"}
    _op = {(r["defense"], r["attack"]) for r in runs if r["role"] == "transfer"}
    _oc = sum(1 for d, a in _op if _DT.get(d) != _AT.get(a))
    M["NOursPairs"] = len(_op)
    M["NOursCrossPairs"] = _oc
    M["PctOursCross"] = f"{100*_oc/len(_op):.0f}"

    # ---- the citation graph, so figure 5's caption cannot drift from it
    import networkx as nx
    net = load("citation_network_union.json")
    G = nx.Graph()
    for e in net["edges"]:
        if e["citing"] in included and e["cited"] in included:
            G.add_edge(e["citing"], e["cited"])
    G.remove_nodes_from([n for n, d in G.degree() if d == 0])
    trk = {r[pi]: (r[hdr.index("track")] or "").strip() for r in rows}
    ncross = sum(1 for u, v in G.edges() if trk.get(u) != trk.get(v))
    M["NNetworkNodes"] = G.number_of_nodes()
    M["NNetworkEdges"] = f"{G.number_of_edges():,}"
    M["NNetworkCross"] = ncross
    M["PctNetworkCross"] = f"{100*ncross/G.number_of_edges():.1f}"

    # ---- RQ2's paper-level cross-citation rates. Same counting rule as
    # scripts/rq2_cross_citation.py, over the same columns: a Security paper
    # counts if it cites any ML/AI paper at all. The abstract carried 9.3
    # against the report's 9.4 before these became macros.
    _ci = {c: hdr.index(c) for c in ("track", "cites_track_a", "cites_track_b")}
    inc = [r for r in rows if r[pi] in included]
    sec = [r for r in inc if r[_ci["track"]] == "Security"]
    mla = [r for r in inc if r[_ci["track"]] == "ML/AI"]
    a_b = sum(1 for r in sec if r[_ci["cites_track_b"]] == "Y")
    b_a = sum(1 for r in mla if r[_ci["cites_track_a"]] == "Y")
    M["NTrackSecurity"], M["NTrackML"] = len(sec), len(mla)
    M["NSecCitesML"], M["NMLCitesSec"] = a_b, b_a
    M["PctSecCitesML"] = f"{100*a_b/len(sec):.1f}"
    M["PctMLCitesSec"] = f"{100*b_a/len(mla):.1f}"

    # ---- who reports what. The abstract's reporter asymmetry, from the same
    # file pair_tally reads, so it cannot drift from the tally.
    _out = collections.defaultdict(collections.Counter)
    for o in load("pair_outcomes.json"):
        _out[o["reported_by"]][o["reported_verdict"]] += 1
    _dp, _ap = _out["defense_paper"], _out["attack_paper"]
    M["NOutcomeDefPaper"] = sum(_dp.values())
    M["NOutcomeDefWins"] = _dp["defense_wins_claimed"]
    M["NOutcomeAtkPaper"] = sum(_ap.values())
    M["NOutcomeAtkDefWins"] = _ap["defense_wins_claimed"]

    (REPO / "latex" / "numbers.tex").write_text(
        "% GENERATED by scripts/gen_paper_numbers.py. Do not edit by hand.\n"
        "% Re-run after any corpus or registry rebuild.\n\n"
        + "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in M.items()))
    print(f"wrote latex/numbers.tex with {len(M)} macros")
    for k, v in M.items():
        print(f"  \\{k:24s} {v}")


if __name__ == "__main__":
    main()

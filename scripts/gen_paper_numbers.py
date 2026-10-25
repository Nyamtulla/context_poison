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


import importlib.util as _ilu
_sp = _ilu.spec_from_file_location(
    "_rtv", pathlib.Path(__file__).with_name("retrack_by_venue.py"))
_rtv = _ilu.module_from_spec(_sp); _sp.loader.exec_module(_rtv)
_venue_bucket = _rtv.bucket


from taxonomy import canon_consequence


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
    # The discovery pool is everything the search and the snowball ever
    # returned, hop-2 fan-out included. The working pool stops at hop 1,
    # because depth was dialled back after the hop-2 records were already in
    # the database. The figure shows both so the two totals reconcile.
    M["NAutoExcluded"] = _g("select count(*) from papers where hop<=1 and "
                            "screen_auto='auto_exclude'")
    M["NSeeds"] = _g("select count(*) from papers "
                     "where discovered_via='seed'")
    M["NDiscovered"] = _g("select count(*) from papers")
    M["NWorkingPool"] = _g("select count(*) from papers where hop<=1")
    M["NHopTwo"] = _g("select count(*) from papers where hop=2")
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
    tr3 = collections.Counter(e.get("regime") for e in r3)
    M["NMechSecurity"], M["NMechSafety"] = tr3["security"], tr3["safety"]
    cq = collections.Counter(e.get("consequence") for e in r3)
    M["NGoalHijack"] = cq["goal-hijack"]
    # the consequence x regime split. The prose used to say EVERY goal-hijack
    # mechanism was security-track; after the full-text re-coding that is one
    # paper short of true, so the claim is now carried by counts.
    _ct = collections.defaultdict(collections.Counter)
    for e in r3:
        _ct[(e.get("consequence") or "").strip()][(e.get("regime") or "").strip()] += 1
    M["NGoalHijackSec"] = _ct["goal-hijack"]["security"]
    M["NGoalHijackSafety"] = _ct["goal-hijack"]["safety"]
    M["NReasonSafety"] = _ct["reasoning-corruption"]["safety"]
    M["NReasonSec"] = _ct["reasoning-corruption"]["security"]
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
    # resource-abuse was merged into availability-loss on 2026-10-24 (see
    # scripts/taxonomy.py), so these count the merged consequence instead.
    M["NMechAvailLoss"] = sum(
        1 for e in r3 if canon_consequence(e.get("consequence"))
        == "availability-loss")
    M["NDefAvailLoss"] = sum(
        1 for e in r4 if canon_consequence(e.get("consequence"))
        == "availability-loss")
    # Count the defenses validated in the OTHER regime.
    _other = {"security": "incidental", "safety": "adversarial"}
    M["NDefCrossRegime"] = sum(
        1 for e in r4
        if _other.get((e.get("regime") or "").strip())
        == (e.get("validated_against") or "").strip())
    tr4 = collections.Counter(e.get("regime") for e in r4)
    M["NDefSafety"], M["NDefSecurity"], M["NDefBoth"] = tr4["safety"], tr4["security"], tr4["Both"]
    ip = collections.Counter(e.get("defense_intervention_point") for e in r4)
    for k, v in [("Reasoning", "reasoning"), ("Ingestion", "ingestion"),
                 ("Execution", "execution"), ("NoPoint", "none")]:
        M["NDef" + k] = ip[v]
    # Where each regime intervenes. The two communities defend the same cells
    # and do not defend them in the same place, which is the measurement
    # behind S3's answer and the mechanism behind the sign flip in S8.
    _ipr = collections.Counter((e.get("defense_intervention_point"),
                                e.get("regime")) for e in r4)
    for k, v in [("Reasoning", "reasoning"), ("Ingestion", "ingestion"),
                 ("Execution", "execution"), ("NoPoint", "none")]:
        M["NDefPt" + k + "Sec"] = _ipr[(v, "security")]
        M["NDefPt" + k + "Safety"] = _ipr[(v, "safety")]

    # ---- is either community naming what the other already named? Same
    # taxonomy cell, best fuzzy match between the two regimes' names. Typed
    # into the prose this would be a claim; computed here it is a check a
    # reader can re-run.
    import difflib
    def _clashes(reg, thresh=0.55):
        nk = lambda e: (e.get("name") or e.get("technique_name")
                        or e.get("defense_name") or "")
        _s = [e for e in reg if e.get("regime") == "security"]
        _m = [e for e in reg if e.get("regime") == "safety"]
        n = 0
        for a in _s:
            for b in _m:
                if (a.get("channel"), a.get("consequence")) != \
                   (b.get("channel"), b.get("consequence")):
                    continue
                if difflib.SequenceMatcher(
                        None, nk(a).lower(), nk(b).lower()).ratio() > thresh:
                    n += 1
        return n
    # ---- the adaptive campaign against ACD. These were typed into five
    # files as 58%, 29%, 14.7pp and 10.4pp, with no generator behind them,
    # which is the condition the macro rule exists to prevent. The gap is the
    # payload's advantage over the defended arm at full dose; protection
    # removed is that gap against the non-adaptive payload's.
    def _gap(name):
        d = load(f"acd_vs_{name}_evidence.json")
        full = {r["arm"]: r for r in d["results"] if r.get("frac") == 1.0}
        return full["rag"]["dist_acc"] - full["acd"]["dist_acc"]
    _g0 = _gap("distractor")
    _gb, _gg = _gap("adaptive"), _gap("gradient")
    M["NAcdGapBase"] = f"{_g0:.1f}"
    M["NAcdGapBestOf"] = f"{_gb:.1f}"
    M["NAcdGapGradient"] = f"{_gg:.1f}"
    M["PctAcdRemovedBestOf"] = f"{100 * (1 - _gb / _g0):.0f}"
    M["PctAcdRemovedGradient"] = f"{100 * (1 - _gg / _g0):.0f}"
    M["NAcdGradientBeyond"] = f"{_gb - _gg:.1f}"
    M["NAcdAdaptiveItems"] = load("acd_vs_gradient_evidence.json")["n"]
    M["NAcdAdaptiveMdr"] = load("acd_vs_gradient_evidence.json")["mdr_pp_at_n"]

    # The adversarial-validation audit ran over the registry as it stood on
    # 2026-10-15. Section 3 turned its counts into percentages of the current
    # registry, which has grown since, so the shares were against a retired
    # denominator. The audit's own size is the honest one to quote.
    M["NDefEvalAudited"] = load("defense_evaluation_status.json")["n_defenses"]

    # ---- the validation study. Section 10 claimed human verification and
    # an inter-rater agreement; the study is drawn, uncoded, and
    # single-coded by design. Its own manifest says to describe it that way.
    _vs = json.loads((REPO / "data" / "exports" / "validation_study"
                      / "manifest.json").read_text())
    M["NValidationDraw"] = sum(_vs["draw"].values())
    M["NValidationHigh"] = _vs["draw"]["high"]
    M["NValidationMedium"] = _vs["draw"]["medium"]
    M["NValidationLow"] = _vs["draw"]["low"]
    M["NValidationFields"] = _vs["fields_per_paper"]
    M["NValidationCI"] = f'{_vs["design_precision"]["overall_ci_halfwidth_pp"]:.1f}'
    M["NValidationDoubleCoded"] = _vs["double_coded"]

    # share of each year's papers carrying a named venue, typed as 85% and
    # 21% in Section 10 and derived from a corpus that moves
    _vi2, _yi2 = hdr.index("venue"), hdr.index("year")
    _byyear = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        if r[pi] not in included or not r[_yi2]:
            continue
        _y = str(r[_yi2]).split(".")[0]
        _byyear[_y][0] += 1
        _v = str(r[_vi2] or "").strip()
        if _v and _v.lower() != "arxiv":
            _byyear[_y][1] += 1
    # LaTeX control sequences are letters only, so the years cannot go in the
    # macro names; they are emitted as their own macros instead.
    _yrs = sorted(y for y, (tot, _) in _byyear.items() if tot >= 20)
    for _lab, _y in (("Early", _yrs[0]), ("Late", _yrs[-1])):
        _tot, _named = _byyear[_y]
        M["PctVenue" + _lab] = f"{100 * _named / _tot:.0f}"
        M["YearVenue" + _lab] = _y

    # ---- the regime framing test. Whether it takes an adversary to cause
    # the harm is the claim Section 2 rests on, and it was asserted before it
    # was measured. Five payload conditions on one item set; the arms differ
    # only in who wrote the payload and what it does.
    _rf = load("regime_framing_test.json")
    _rb = {}
    for _r in _rf["results"]:
        _rb.setdefault(_r["arm"], {})[_r["n_poison"]] = _r
    M["NRegimeItems"] = _rf["n"]
    M["NRegimeMdr"] = f'{_rf["mdr_pp_at_n"]:.1f}'
    _cb, _cr, _st = (_rb["closedbook"][0], _rb["a2_poisonedrag_x1"],
                     _rb["a3_incidental_stale"])
    _mis, _cp = _rb["a4_incidental_misretrieval"], _rb["a5_corpus_poisoning"]
    M["PctRegimeClean"] = f'{_st[0]["attacked"]:.1f}'
    M["PctCraftLow"], M["PctStaleLow"] = (f'{_cr[1]["attacked"]:.1f}',
                                          f'{_st[1]["attacked"]:.1f}')
    M["PctCraftSat"], M["PctStaleSat"] = (f'{_cr[10]["attacked"]:.1f}',
                                          f'{_st[10]["attacked"]:.1f}')
    M["NRegimeGapLow"] = f'{_cr[1]["attacked"] - _st[1]["attacked"]:.1f}'
    M["NRegimeGapSat"] = f'{_cr[10]["attacked"] - _st[10]["attacked"]:.1f}'
    # the displacement column: an optimised artefact against plain retrieval
    # error, same measure
    M["PctMisretrievalSat"] = f'{_mis[10]["attacked"]:.1f}'
    M["PctCorpusSat"] = f'{_cp[10]["attacked"]:.1f}'
    M["AccMisretrievalSat"] = f'{_mis[10]["acc"]:.1f}'
    M["AccCorpusSat"] = f'{_cp[10]["acc"]:.1f}'
    M["AccStaleSat"], M["AccCraftSat"] = (f'{_st[10]["acc"]:.1f}',
                                          f'{_cr[10]["acc"]:.1f}')
    M["AccRegimeClosedBook"] = f'{_cb["acc"]:.1f}'
    # the published construction repeats its passage five times per slot
    M["NRegimeRepeatMax"] = f'{max(_rb["a1_poisonedrag_x5"][k]["attacked"] - _cr[k]["attacked"] for k in (1, 2, 3, 5, 10)):.1f}'

    M["NMechNameClash"] = _clashes(r3)
    M["NDefNameClash"] = _clashes(r4)
    _cells = collections.defaultdict(set)
    for e in r3:
        _cells[(e.get("channel"), e.get("consequence"))].add(e.get("regime"))
    M["NSharedCells"] = sum(1 for v in _cells.values()
                            if {"security", "safety"} <= v)
    M["NOccupiedCells"] = len(_cells)
    _sh = {k for k, v in _cells.items() if {"security", "safety"} <= v}
    M["NMechSharedSec"] = sum(1 for e in r3 if e.get("regime") == "security"
                              and (e.get("channel"), e.get("consequence")) in _sh)
    M["NMechSharedSafety"] = sum(1 for e in r3 if e.get("regime") == "safety"
                                 and (e.get("channel"), e.get("consequence")) in _sh)

    # ---- which papers contribute what
    mech_p = {e.get("paper_id") for e in r3} & included
    def_p = {e.get("paper_id") for e in r4} & included

    # NPapersMech/Def/Both/Neither were retired on 2026-10-22: NAnalysed and
    # NNoTechnique say the same things against the denominators the paper
    # actually uses, and four unused macros invite a stale one being quoted.
    # The corpus is screened; the census is drawn from the papers that named
    # something. Each claim states its own denominator, so both are macros.
    M["NAnalysed"] = len(included & (mech_p | def_p))
    M["NNoTechnique"] = len(included - mech_p - def_p)
    # What the papers that named nothing actually are. Reported because an
    # exclusion stated without its composition is a convenience, not a
    # criterion. Categories are assigned in this order and each paper is
    # counted once, so the five sum to NNoTechnique.
    import re as _re
    _ti = hdr.index("title")
    _none = [r for r in rows if r[pi] in (included - mech_p - def_p)]
    _pats = [("Survey", r"\b(survey|systemati[sz]ation|sok|review|taxonomy|landscape)\b"),
             ("Bench", r"\b(benchmark|evaluat|dataset|testbed|leaderboard|arena)\b"),
             ("Position", r"\b(position|towards|roadmap|perspective|agenda|challenges|opportunit)\b"),
             ("Framework", r"\b(framework|architecture|platform|protocol|pipeline|system)\b")]
    _seen = set()
    for _name, _pat in _pats:
        _hit = {r[pi] for r in _none
                if _re.search(_pat, str(r[_ti] or ""), _re.I)} - _seen
        _seen |= _hit
        M["NNoTech" + _name] = len(_hit)
    M["NNoTechOther"] = len(_none) - len(_seen)
    # The recall pass read the bucket as it stood BEFORE the pass, and the
    # papers it found a technique in then left the bucket. So the number re-read
    # is not NNoTechOther any more; it is the size of the exports, which is the
    # ground truth of what was looked at. Typing 143 here would go stale the
    # next time the pass runs.
    import json as _json
    _rb = sorted((REPO / "data" / "registries" / "raw").glob("recheck_batch*.json"))
    M["NRecallRead"] = sum(len(_json.loads(f.read_text())) for f in _rb)
    _rd = sorted((REPO / "data" / "registries" / "raw").glob(
        "recheck_decisions_batch*.csv"))
    import csv as _csv
    _pos = [d for f in _rd for d in _csv.DictReader(open(f))
            if d["verdict"] != "none"]
    M["NRecallCandidates"] = len(_pos)

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

    # the share of tested pairs absorbed by the single coarsest registry
    # entry, which Section 10 uses to price registry granularity. It was typed
    # as 32.6% and had gone stale by ten points.
    _mc = collections.Counter(a for _, a in pairs)
    _topname, _topn = _mc.most_common(1)[0]
    M["NTopMechPairs"] = _topn
    M["PctTopMechShare"] = f"{100 * _topn / len(pairs):.1f}"

    covered = {a for _, a in pairs} & uni
    M["NMechCovered"] = len(covered)
    M["NMechUncovered"] = len(uni) - len(covered)
    M["PctMechUncovered"] = f'{100*M["NMechUncovered"]/len(uni):.1f}'
    M["PctMechCovered"] = f'{100*len(covered)/len(uni):.1f}'

    per_def = collections.Counter(d for d, _ in pairs)
    dist = collections.Counter(per_def.values())
    M["NDefMatchedFull"] = len(per_def)
    M["PctDefMatched"] = f'{100*len(per_def)/len(r4):.1f}'
    M["PctDefUnmatched"] = f'{100*(1-len(per_def)/len(r4)):.0f}'
    M["NDefOneFull"] = dist[1]
    M["PctDefOneFull"] = f'{100*dist[1]/len(per_def):.1f}'
    M["NDefCeiling"] = max(per_def.values())
    # Breadth in this matrix is mostly attackers choosing a target, not
    # authors evaluating widely. "Contributed by an attack paper" means the
    # pair came from the reverse scan over attack papers, not from who
    # reported its outcome; those are different facts and conflating them
    # gives the wrong number.
    from pair_tally import load as _pl
    _atk = set()
    for _f in ("attack_paper_evaluations.json",
               "attack_paper_evaluations_pass3.json"):
        _atk |= {(x["defense"], x["mechanism"]) for x in _pl(_f)["confirmed_pairs"]}
    _wide = {d for d, c in per_def.items() if c >= 4}
    _wp = [x for x in pairs if x[0] in _wide]
    M["PctBreadthFromAttack"] = f"{100 * sum(1 for x in _wp if x in _atk) / len(_wp):.0f}"
    _top = max(per_def, key=lambda d: per_def[d])
    M["NBroadestPairs"] = per_def[_top]
    M["NBroadestFromAttack"] = sum(1 for x in pairs
                                   if x[0] == _top and x in _atk)
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
    # The agent cell by intervention point. A technique "holds" when the
    # defended arm's attack success is zero. Which stage a technique acts at
    # decides whether it does, which is the division of labor in Section 3
    # confirmed by execution rather than asserted.
    _hold = [r for r in scored if r["defended"]["asr_pct"] == 0]
    M["NAgentConditions"] = len(scored)
    M["NAgentHolds"] = len(_hold)
    for _lab, _k in (("Ingestion", "ingestion"), ("Execution", "execution"),
                     ("Reasoning", "reasoning")):
        M["NAgentHolds" + _lab] = sum(1 for r in _hold
                                      if r.get("intervention_point") == _k)
        M["NAgentTried" + _lab] = sum(1 for r in scored
                                      if r.get("intervention_point") == _k)
    M["NCampaignPairs"] = len(rag_pairs) + len(agent_pairs)
    M["NCampaignImpl"] = (len({r["defense"] for r in transfer})
                          + len({r["technique_name"] for r in scored}))
    M["NCampaignEpisodes"] = f"{rag_eps + agent_eps:,}"

    # ---- the taxonomy cube and the per-axis splits.
    # Computed exactly as fig_cube does: over PAPER rows, one (channel,
    # consequence) per paper, split by track. These were typed into the prose
    # and went stale the moment the corpus moved: the text still said 98 empty
    # cells of 162 when it had become 111.
    from taxonomy import CHANNELS as CHS, CONSEQ as CQS
    ci, qi, ti = hdr.index("channel"), hdr.index("consequence"), hdr.index("regime")
    # Computed over REGISTRY ENTRIES, not paper rows, since 2026-10-22.
    # A paper that names no attack and no defense was still occupying a cell:
    # AgentDojo sat in tool-output x goal-hijack x Security while naming
    # nothing. The cube is a map of what the field has NAMED, so it is built
    # from the things that were named. This also makes the empty-cell macro
    # agree with Figure 4, which already plots the registry.
    occupied = set()
    for e in r3 + r4:
        if e.get("paper_id") not in included:
            continue
        c = (e.get("channel") or "").strip()
        q = canon_consequence(e.get("consequence"))
        tr = (e.get("regime") or "").strip()
        if c in CHS and q and tr in ("security", "safety"):
            occupied.add((c, q, tr))
    # The cube's third axis is the regime. The
    # `Both` value was retired on 2026-10-22 (track_reassignment_prediction.md)
    # because it was filtered out of this count and out of fig_cube, which left
    # a third of the cube unoccupiable BY CONSTRUCTION and inflated the
    # empty-cell rate. Two reachable intents, so the cube is 9 x 7 x 2.
    NCELLS = len(CHS) * len(CQS) * 2
    # The taxonomy's own axis sizes. These were typed as English words and
    # went stale when availability-loss made it seven consequences.
    M["NChannelCats"], M["NConseqCats"] = len(CHS), len(CQS)
    M["NCubeCells"] = NCELLS
    M["NCubeEmpty"] = NCELLS - len(occupied)

    # The seven-consequence grid, before resource-abuse was merged into
    # availability-loss. The merge removes a nearly empty column and so
    # lowers the empty-cell rate; the prose has to report the before as well
    # as the after, and neither figure may be typed into it.
    _seven = set()
    for e in r3 + r4:
        if e.get("paper_id") not in included:
            continue
        c = (e.get("channel") or "").strip()
        q = (e.get("consequence") or "").strip()
        tr = (e.get("regime") or "").strip()
        if c in CHS and q and tr in ("security", "safety"):
            _seven.add((c, q, tr))
    _n7 = len(CHS) * (len(CQS) + 1) * 2
    M["PctCubeEmptySeven"] = round(100 * (_n7 - len(_seven)) / _n7, 1)

    # Cells holding a named attack and no defense at all. Typed as "nine"
    # and "eight" in the prose; the merge moved one of them and neither
    # number would have been re-checked.
    def _cells(reg):
        s = set()
        for e in reg:
            if e.get("paper_id") not in included:
                continue
            c = (e.get("channel") or "").strip()
            q = canon_consequence(e.get("consequence"))
            tr = (e.get("regime") or "").strip()
            if c in CHS and q and tr in ("security", "safety"):
                s.add((c, q, tr))
        return s
    # The four heaviest cells, named explicitly rather than taken as a
    # top-four, so the prose cannot silently describe a different cell than
    # the one it prints a number for. These were typed; one of them had
    # drifted by a point before anybody re-read it.
    _dcell = collections.Counter(
        ((e.get("channel") or "").strip(),
         canon_consequence(e.get("consequence")),
         (e.get("regime") or "").strip()) for e in r4)
    _top = {
        "NDefCellToolOutGoalHijack": ("tool-output", "goal-hijack", "security"),
        "NDefCellDirectInGoalHijack": ("direct-input", "goal-hijack",
                                       "security"),
        "NDefCellRagSilent": ("RAG", "silent-corruption", "safety"),
        "NDefCellMemReasoning": ("memory", "reasoning-corruption", "safety"),
    }
    for _k, _cell in _top.items():
        M[_k] = _dcell[_cell]
    M["PctTopFourDef"] = f'{100 * sum(_dcell[c] for c in _top.values()) / len(r4):.0f}'

    _nodef = _cells(r3) - _cells(r4)
    M["NCellsAttackNoDef"] = len(_nodef)
    M["NCellsAttackNoDefSec"] = sum(1 for k in _nodef if k[2] == "security")
    M["NCellsAttackNoDefBackdoor"] = sum(
        1 for k in _nodef if k[1] == "persistence-backdoor")
    # NUnplaceable / PctUnplaceable lived here: papers carrying no channel or
    # no consequence, which are outside the cube by construction. The
    # paragraph that reported them was cut from S3 on 2026-10-25, so the
    # macros are gone too rather than left generating into numbers.tex
    # unread. The count is still recoverable from the corpus if the
    # paragraph comes back.
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
        y, ch, tr = _yr.get(e.get("paper_id")), e.get("channel"), e.get("regime")
        if not (y and ch) or tr not in ("security", "safety"):
            continue
        y = int(str(y).split(".")[0])
        _first.setdefault(ch, {}).setdefault(tr, []).append(y)
    _shared = {c: v for c, v in _first.items() if len(v) == 2}
    _gaps = {c: min(v["safety"]) - min(v["security"]) for c, v in _shared.items()}
    M["NSharedChannels"] = len(_shared)
    M["NChannelsSecFirst"] = sum(1 for g in _gaps.values() if g > 0)
    M["NChannelsSameYear"] = sum(1 for g in _gaps.values() if g == 0)
    M["NChannelsSafetyFirst"] = sum(1 for g in _gaps.values() if g < 0)
    _lead = sorted(g for g in _gaps.values() if g > 0)
    M["MedianChannelLag"] = (_lead[len(_lead) // 2] if _lead else 0)
    M["MaxChannelLag"] = (max(_lead) if _lead else 0)

    tl = load("pair_timeline.json")["pairs"]
    M["NTimelinePairs"] = len(tl)
    _pre = [r for r in tl if r["defense_predates_attack"]]
    M["NDefensePredates"] = len(_pre)
    M["PctDefensePredates"] = f"{100*len(_pre)/len(tl):.1f}"
    _pure = [r for r in tl if r["defense_regime"] in ("security", "safety")
             and r["attack_regime"] in ("security", "safety")]
    _x = [r for r in _pure if r["defense_regime"] != r["attack_regime"]]
    M["NPureRegimePairs"] = len(_pure)
    M["NCrossCommunityPairs"] = len(_x)
    M["PctCrossCommunity"] = f"{100*len(_x)/len(_pure):.1f}"
    M["NCrossAllPairs"] = sum(1 for r in tl
                              if r["defense_regime"] != r["attack_regime"])
    M["NSecDefVsSafetyAttack"] = sum(1 for r in _pure
                                 if r["defense_regime"] == "security"
                                 and r["attack_regime"] == "safety")
    M["NSafetyDefVsSecAttack"] = sum(1 for r in _pure
                                 if r["defense_regime"] == "safety"
                                 and r["attack_regime"] == "security")

    # Robustness: two thirds of the corpus is preprint, so a reviewer will ask
    # whether the finding is an artifact of unrefereed work. Restrict both
    # sides of every pair to papers with a named venue and see what survives.
    _vi = hdr.index("venue")
    _named = {r[pi] for r in rows if r[pi] in included
              and str(r[_vi] or "").strip()
              and str(r[_vi] or "").strip().lower() != "arxiv"}
    _dn, _an = {}, {}
    for _reg, _keys, _m in ((r4, ("defense_name", "name"), _dn),
                            (r3, ("technique_name", "name"), _an)):
        for _e in _reg:
            for _k in _keys:
                if _e.get(_k):
                    _m.setdefault(_e[_k].strip(), _e.get("paper_id"))
    _res = [x for x in tl if x["defense"] in _dn and x["attack"] in _an]
    _sub = [x for x in _res
            if _dn[x["defense"]] in _named and _an[x["attack"]] in _named]
    M["NVenuePapers"] = len(_named)
    M["NVenuePairs"] = len(_sub)
    M["NVenueResolved"] = len(_res)
    M["PctVenueResolved"] = f"{100 * len(_res) / len(tl):.0f}"
    M["NVenueSecDefSafetyAtk"] = sum(
        1 for x in _sub if x["defense_regime"] == "security"
        and x["attack_regime"] == "safety")

    # Regime against venue. They are coded independently and they are not the
    # same cut: adversarial work publishes at AI venues about as often as at
    # security ones, and safety work never publishes at a security venue.
    _reg_i = hdr.index("regime")
    _vc = {}
    for r in rows:
        if r[pi] not in included:
            continue
        _vt, _ = _venue_bucket(str(r[_vi] or ""))
        _vc[(str(r[_reg_i] or "").strip(), _vt)] = \
            _vc.get((str(r[_reg_i] or "").strip(), _vt), 0) + 1
    M["NRegimeSecAtSecVenue"] = _vc.get(("security", "Security"), 0)
    M["NRegimeSecAtAIVenue"] = _vc.get(("security", "ML/AI"), 0)
    M["NRegimeSafetyAtSecVenue"] = _vc.get(("safety", "Security"), 0)
    M["NRegimeSafetyAtAIVenue"] = _vc.get(("safety", "ML/AI"), 0)
    M["NRegimeSecNamedVenue"] = (M["NRegimeSecAtSecVenue"]
                                 + M["NRegimeSecAtAIVenue"])
    # The safety side needs its own total. The prose used to reach for
    # NRegimeSafetyAtAIVenue as "safety papers with a named venue", which is
    # only right while no safety paper has published at a security venue.
    M["NRegimeSafetyNamedVenue"] = (M["NRegimeSafetyAtSecVenue"]
                                    + M["NRegimeSafetyAtAIVenue"])
    # the two diagonal cells of the transfer matrix, so Table 1 and the
    # sentence under it cannot drift apart
    M["NSecDefSecAttack"] = sum(1 for r in _pure
                                if r["defense_regime"] == "security"
                                and r["attack_regime"] == "security")
    M["NSafetyDefSafetyAttack"] = sum(1 for r in _pure
                              if r["defense_regime"] == "safety"
                              and r["attack_regime"] == "safety")
    _same = sum(1 for r in tl if r["defense_regime"] == r["attack_regime"])
    M["NSameRegimePairs"] = _same
    M["PctSameRegime"] = f"{100*_same/len(tl):.1f}"
    M["NPredatesAndCross"] = sum(1 for r in _pure
                                 if r["defense_predates_attack"]
                                 and r["defense_regime"] != r["attack_regime"])
    # the same matrix for what we executed
    _DT = {"ParamMute": "safety", "CK-PLUG": "safety", "COIECD": "safety",
           "ACD": "safety", "DyPRAG": "safety", "FaithfulRAG": "safety",
           "SpARE": "safety", "SCR": "safety",
           "RobustRAG-DecodingAgg": "security", "RobustRAG-KeywordAgg": "security"}
    _AT = {"corpus poisoning": "security", "PoisonedRAG": "security",
           "BadRAG sentiment steering": "security",
           "BadRAG denial-of-service": "security",
           "false evidence": "safety", "distractor evidence": "safety"}
    # how many of the retrieval-cell implementations come from each regime.
    # Section 7 said "eight of our nine" while NRagImpl read ten.
    M["NRagImplSafety"] = sum(1 for v in _DT.values() if v == "safety")
    M["NRagImplSecurity"] = sum(1 for v in _DT.values() if v == "security")

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
    trk = {r[pi]: (r[hdr.index("regime")] or "").strip() for r in rows}
    ncross = sum(1 for u, v in G.edges() if trk.get(u) != trk.get(v))
    M["NNetworkNodes"] = G.number_of_nodes()
    M["NNetworkEdges"] = f"{G.number_of_edges():,}"
    M["NNetworkCross"] = ncross
    M["PctNetworkCross"] = f"{100*ncross/G.number_of_edges():.1f}"

    # ---- RQ2's paper-level cross-citation rates. Same counting rule as
    # scripts/rq2_cross_citation.py, over the same columns: a security-regime paper
    # counts if it cites any safety-regime paper at all. The abstract carried 9.3
    # against the report's 9.4 before these became macros.
    _ci = {c: hdr.index(c) for c in ("regime", "cites_track_a", "cites_track_b")}
    inc = [r for r in rows if r[pi] in included]
    sec = [r for r in inc if r[_ci["regime"]] == "security"]
    mla = [r for r in inc if r[_ci["regime"]] == "safety"]
    a_b = sum(1 for r in sec if r[_ci["cites_track_b"]] == "Y")
    b_a = sum(1 for r in mla if r[_ci["cites_track_a"]] == "Y")
    M["NRegimeSecurity"], M["NRegimeSafety"] = len(sec), len(mla)
    M["NSecCitesSafety"], M["NSafetyCitesSec"] = a_b, b_a
    M["PctSecCitesSafety"] = f"{100*a_b/len(sec):.1f}"
    M["PctSafetyCitesSec"] = f"{100*b_a/len(mla):.1f}"

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

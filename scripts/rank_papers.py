"""Score and rank the corpus by how load-bearing each paper is for this SoK.

Purpose: decide which papers a human should verify FIRST. A paper is important
here if the project's claims rest on it, which is not the same as being
famous - so the score mixes external standing with how much work the paper
actually does inside this corpus.

Six components, each 0-1, then weighted. Every component is stored alongside
the total so a rank can be explained rather than trusted.

  external   log-scaled Semantic Scholar citation count. Field-level standing.
  internal   in-degree in our own citation network: how many corpus papers
             cite it. This is what "foundational to OUR research" means
             concretely, and it is the component that surfaces the papers the
             corpus is actually built on rather than the ones the world likes.
  registry   contributes a named attack, defense or incidental mechanism to
             RQ3/RQ4. A paper that contributes nothing to the registries
             cannot move RQ3, RQ4 or RQ5 whatever its citation count.
  tested     appears in a confirmed RQ5 defence x mechanism pair, in either
             role - the paper is part of the evidence about what has been
             tested against what.
  ran        we executed this technique ourselves in the transfer campaign.
             These are the papers whose coding, if wrong, invalidates an
             experiment we ran, so they carry the heaviest per-paper weight.
  engaged    out-degree: does it cite the corpus at all. Low weight; it
             separates work that engages the literature from work written
             past it, and is a tie-break rather than a driver.

Deliberately NOT a relevance or quality judgement, and NOT a probability
sample: verifying the top of this list measures the papers the project leans
on, which is a different question from how good the extraction is overall.
That one needs verification/verification_sample.xlsx.
"""
from __future__ import annotations

import json
import math
import pathlib
import sqlite3
import collections

REPO = pathlib.Path(__file__).resolve().parent.parent
PE = REPO / "data" / "paper_explorer.db"
CS = REPO / "data" / "context_sok.db"
NET = REPO / "data" / "registries" / "citation_network_v3.json"
OUT = REPO / "data" / "registries" / "paper_importance_ranking.json"
XLSX = REPO / "verification" / "paper_importance_ranking.xlsx"

WEIGHTS = {"external": 0.20, "internal": 0.30, "registry": 0.15,
           "tested": 0.15, "ran": 0.15, "engaged": 0.05}


def norm_log(v, hi):
    return min(1.0, math.log1p(max(0, v)) / math.log1p(hi)) if hi > 0 else 0.0


def main() -> None:
    pe = sqlite3.connect(PE)
    cs = sqlite3.connect(CS)
    inc = {p: dict(zip(("title", "year", "venue", "track", "role", "channel",
                        "consequence", "cites", "doi", "arxiv"), rest))
           for p, *rest in pe.execute(
               "select paper_id,title,year,venue,track,role,channel,consequence,"
               "citation_count,doi,arxiv_id from paper where screening='Include'")}

    # internal in-degree, union of the full-text network and the S2 edge table
    net = json.loads(NET.read_text())
    edges = {(e["citing"], e["cited"]) for e in net["edges"]
             if e["citing"] in inc and e["cited"] in inc}
    edges |= {(a, b) for a, b in cs.execute(
        "select citing_paper_id,cited_paper_id from citation_edges")
        if a in inc and b in inc and a != b}
    indeg = collections.Counter(b for _, b in edges)
    outdeg = collections.Counter(a for a, _ in edges)

    reg = collections.Counter()
    for t in ("attack", "defense"):
        for (p,) in pe.execute(f"select paper_id from {t}"):
            if p in inc:
                reg[p] += 1

    # papers appearing in a confirmed RQ5 pair, by technique name
    name_to_paper = {}
    for t in ("attack", "defense"):
        for n, p in pe.execute(f"select name, paper_id from {t}"):
            if p in inc and n:
                name_to_paper.setdefault(n.strip().lower(), p)
    tested = collections.Counter()
    for dn, an in pe.execute("select defense_name, attack_name from pair"):
        for n in (dn, an):
            p = name_to_paper.get((n or "").strip().lower())
            if p:
                tested[p] += 1

    # Techniques this project executed. Resolved by an explicit prefix map
    # rather than fuzzy matching, because fuzzy matching found only 4 of them:
    # our_run stores short internal keys ("ckplug", "spare") while the registry
    # stores full names ("CK-PLUG (Controllable Knowledge Plug-in)"). The map
    # also covers the runs that postdate the our_run table - COIECD, DyPRAG,
    # ACD, SCR, FaithfulRAG, SHIFT, SABER - which live in data/registries/
    # result files and are not loaded into the DB yet.
    RAN_PREFIX = [
        "ck-plug", "parammute", "robustrag", "spare (", "spotlighting (",
        "faithfulrag", "shift (gate", "coiecd", "dyprag", "acd (adaptive",
        "scr & cr-dpo", "saber (self-aware", "datasentinel",
    ]
    ran = set()
    for n, p in name_to_paper.items():
        if any(n.startswith(pre) for pre in RAN_PREFIX):
            ran.add(p)

    hi_cite = max((v["cites"] or 0) for v in inc.values())
    hi_in = max(indeg.values()) if indeg else 1
    rows = []
    for p, v in inc.items():
        c = {
            "external": norm_log(v["cites"] or 0, hi_cite),
            "internal": norm_log(indeg.get(p, 0), hi_in),
            "registry": min(1.0, reg.get(p, 0) / 2.0),
            "tested": min(1.0, tested.get(p, 0) / 3.0),
            "ran": 1.0 if p in ran else 0.0,
            "engaged": 1.0 if outdeg.get(p, 0) > 0 else 0.0,
        }
        score = sum(WEIGHTS[k] * c[k] for k in WEIGHTS)
        rows.append({"paper_id": p, "score": round(score, 4),
                     "citations": v["cites"] or 0,
                     "corpus_in_degree": indeg.get(p, 0),
                     "registry_entries": reg.get(p, 0),
                     "rq5_pairs": tested.get(p, 0),
                     "we_ran_it": p in ran,
                     "cites_corpus": outdeg.get(p, 0) > 0,
                     "title": v["title"], "year": v["year"], "venue": v["venue"],
                     "track": v["track"], "role": v["role"],
                     "channel": v["channel"], "consequence": v["consequence"],
                     **{f"c_{k}": round(c[k], 3) for k in c}})
    rows.sort(key=lambda r: -r["score"])
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    # Tier is the thing to act on; score is how it was reached. A paper this
    # project ran an experiment on is tier A whatever its citation count,
    # because if its coding is wrong an experiment is mis-framed - SHIFT and
    # SABER are near-uncited and rank in the 250s on score alone, yet both
    # carry a transfer result. Popularity and load-bearing are different
    # questions and the score only answers the first.
    for r in rows:
        if r["we_ran_it"]:
            r["tier"] = "A - we ran it"
        elif r["rank"] <= 50:
            r["tier"] = "A - top 50 by score"
        elif r["rank"] <= 200:
            r["tier"] = "B"
        else:
            r["tier"] = "C"

    OUT.write_text(json.dumps({"generated": "2026-10-13", "weights": WEIGHTS,
                               "n": len(rows), "papers": rows}, indent=1))

    import openpyxl
    from openpyxl.styles import Font, PatternFill
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "ranking"
    head = ["tier", "rank", "score", "title", "year", "venue", "track", "role",
            "channel", "consequence", "citations", "corpus_in_degree",
            "registry_entries", "rq5_pairs", "we_ran_it", "cites_corpus",
            "c_external", "c_internal", "c_registry", "c_tested", "c_ran",
            "c_engaged", "paper_id"]
    ws.append(head)
    for cc in ws[1]:
        cc.font = Font(bold=True); cc.fill = PatternFill("solid", fgColor="DDDDDD")
    ws.freeze_panes = "D2"
    for r in rows:
        ws.append([r.get(h) for h in head])
    for col, w in zip("ABCDEFGHIJKLMNOPQRSTUVW",
                      [20, 6, 8, 72, 6, 34, 10, 9, 14, 22, 10, 16, 14, 10, 10,
                       12, 11, 11, 11, 10, 8, 10, 42]):
        ws.column_dimensions[col].width = w
    ws.auto_filter.ref = f"A1:W{len(rows)+1}"
    XLSX.parent.mkdir(parents=True, exist_ok=True)
    wb.save(XLSX)

    print(f"ranked {len(rows)} papers")
    print(f"  weights: {WEIGHTS}")
    print(f"  papers we ran ourselves: {len(ran)}")
    print(f"\n  {'#':>3} {'score':>6} {'cites':>6} {'in':>4} {'reg':>4} {'p':>3} {'ran':>4}  title")
    for r in rows[:20]:
        print(f"  {r['rank']:>3} {r['score']:>6.3f} {r['citations']:>6} "
              f"{r['corpus_in_degree']:>4} {r['registry_entries']:>4} "
              f"{r['rq5_pairs']:>3} {'YES' if r['we_ran_it'] else '':>4}  {r['title'][:58]}")
    import collections as _c
    print("\n  tiers: " + ", ".join(f"{k} {v}" for k, v in
          sorted(_c.Counter(r["tier"] for r in rows).items())))
    print(f"\nwrote {OUT.relative_to(REPO)}\nwrote {XLSX.relative_to(REPO)}")


if __name__ == "__main__":
    main()

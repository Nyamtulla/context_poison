"""Candidate generator for the hand-check of RQ2's negative half.

The cross-citation rate says 11% of papers cite the other regime. The other
89% is a negative, and a negative from an automated matcher is only as good
as the matcher's recall. v3 matches an arXiv id, a DOI, or the shortest
unique space-free prefix of a corpus title. The failure it cannot see is a
reference whose title text differs from the corpus title -- a preprint
renamed on publication, a title the reference list abbreviates from the
middle, an OCR-mangled line.

So this pass deliberately does NOT use v3's method. For every other-regime
title it asks a different question: does any short window of this paper's
reference section contain most of that title's content words, in any order?
That is insensitive to word order, to a title truncated from either end, to
line wrapping, and to reference-entry boundaries -- splitting a reference
list into entries is itself unreliable, and an earlier version of this
script spent 352 of its 377 candidates on blobs a bad split produced.
Coverage is cheap and noisy, which is the point: it is tuned for recall and
hands the survivors to a human (or to Claude) to read.

The output is a worklist, not a verdict. Each candidate carries the window
text so the adjudicator reads what the PDF actually says.

    python3 scripts/handcheck_cross_citation.py --n 30 --seed 20261027
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import random
import re
import sqlite3

import openpyxl

REPO = pathlib.Path(__file__).resolve().parent.parent
R = REPO / "data" / "registries"
PE = REPO / "data" / "paper_explorer.db"

import pymupdf  # noqa: E402

# Reuse v3's own reference-section finder: the sample must be read the same
# way the matcher read it, or a miss here could just be a different cut.
import importlib.util as _ilu
_sp = _ilu.spec_from_file_location(
    "_v3", REPO / "scripts" / "rebuild_citation_network_v3.py")
_v3 = _ilu.module_from_spec(_sp)
_sp.loader.exec_module(_v3)

STOP = set("""a an the of and or for on in to with by from at as is are be was
were this that these those we our us their its it his her they them you your
via using use used toward towards into over under about across can could may
might will would shall should do does did not no than then so such more most
less least new novel approach method framework system model models language
large llm llms based study analysis evaluation evaluating paper work""".split())


def words(s: str) -> set[str]:
    return {w for w in re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).split()
            if len(w) > 2 and w not in STOP}


def scan(sec: str, targets, thresh: float, window: int = 60):
    """Best content-word coverage of each target title in any window.

    The reference section becomes one word sequence. For a given title we
    take the positions of its content words and slide a `window`-word frame
    over them; the score is the largest number of DISTINCT title words any
    one frame holds, over the title's word count. A real citation puts them
    all within a few lines of each other, so a high score is the signal;
    words scattered across the whole bibliography never share a frame.
    """
    toks = re.sub(r"[^a-z0-9 ]", " ", _v3.fix_text(sec).lower()).split()
    pos = collections.defaultdict(list)
    for i, w in enumerate(toks):
        if len(w) > 2 and w not in STOP:
            pos[w].append(i)
    out = []
    for tid, ttl, tw in targets:
        if len(tw) < 3:
            continue
        hits = sorted((i, w) for w in tw for i in pos.get(w, ()))
        if not hits:
            continue
        best, span, lo = 0.0, (0, 0), 0
        seen: collections.Counter = collections.Counter()
        for hi in range(len(hits)):
            seen[hits[hi][1]] += 1
            while hits[hi][0] - hits[lo][0] > window:
                seen[hits[lo][1]] -= 1
                if not seen[hits[lo][1]]:
                    del seen[hits[lo][1]]
                lo += 1
            if len(seen) > best * len(tw):
                best, span = len(seen) / len(tw), (hits[lo][0], hits[hi][0])
        if best >= thresh:
            a = max(0, span[0] - 20)
            out.append({"target_id": tid, "target_title": ttl,
                        "coverage": round(best, 3),
                        "n_title_words": len(tw),
                        "window_text": " ".join(toks[a:span[1] + 20])})
    out.sort(key=lambda c: -c["coverage"])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=20261027)
    ap.add_argument("--thresh", type=float, default=0.70,
                    help="fraction of the title's content words in one window")
    ap.add_argument("--out", default="data/registries/raw/handcheck_candidates.json")
    args = ap.parse_args()

    def load(n):
        return json.loads((R / n).read_text())

    wb = openpyxl.load_workbook(
        REPO / "data" / "exports" / "paper_dashboard_source.xlsx", read_only=True)
    ws = wb["Papers"]
    it = ws.iter_rows(values_only=True)
    hdr = list(next(it))
    rows = [dict(zip(hdr, r)) for r in it]
    wb.close()

    included = {p["paper_id"] for p in rows
                if str(p["screening"]).strip() != "Exclude"}
    mech = {e.get("paper_id") for e in load("rq3_pollution_registry.json")}
    dfn = {e.get("paper_id") for e in load("rq4_defense_registry.json")}
    analysed = included & (mech | dfn)
    regime = {p["paper_id"]: (p["regime"] or "").strip() for p in rows}
    title = {p["paper_id"]: p["title"] for p in rows}
    meta = {p["paper_id"]: p for p in rows}
    other = {"security": "safety", "safety": "security"}

    v3 = {p["paper_id"]: p for p in load("citation_network_v3.json")["papers"]}
    cites = collections.defaultdict(set)
    for e in load("citation_network_union.json")["edges"]:
        if e["citing"] in analysed and e["cited"] in analysed:
            cites[e["citing"]].add(e["cited"])

    # The frame: analysed papers with a read reference section and no
    # cross-regime edge. These are the rows the claim rests on.
    frame = collections.defaultdict(list)
    for pid in sorted(analysed):
        rg = regime.get(pid)
        if rg not in other:
            continue
        if any(regime.get(c) == other[rg] for c in cites.get(pid, ())):
            continue
        f = v3.get(pid)
        if not f or f.get("state") != "read" or int(f.get("ref_chars") or 0) < 2000:
            continue
        frame[rg].append(pid)

    total = sum(len(v) for v in frame.values())
    rng = random.Random(args.seed)
    draw = []
    for rg in sorted(frame):
        k = round(args.n * len(frame[rg]) / total)
        draw += [(rg, p) for p in rng.sample(sorted(frame[rg]), k)]
    print(f"frame {total} evidenced negatives "
          f"({ {k: len(v) for k, v in frame.items()} }); drew {len(draw)}")

    targets = {rg: [(p, title.get(p, ""), words(title.get(p, "")))
                    for p in analysed if regime.get(p) == rg]
               for rg in other}

    pe = sqlite3.connect(PE)
    out = []
    for rg, pid in draw:
        row = pe.execute("select pdf_local_path from paper where paper_id=?",
                         (pid,)).fetchone()
        full = ""
        if row and row[0]:
            fp = pathlib.Path(row[0])
            fp = fp if fp.is_absolute() else REPO / row[0]
            if fp.exists():
                with pymupdf.open(fp) as doc:
                    full = "".join(pg.get_text() for pg in doc)
        sec = _v3.ref_section(_v3.fix_text(full))
        cands = scan(sec, targets[other[rg]], args.thresh) if sec else []
        out.append({
            "paper_id": pid, "regime": rg, "title": title.get(pid, ""),
            "year": meta[pid].get("year"), "venue": meta[pid].get("venue"),
            "ref_chars": int(v3[pid].get("ref_chars") or 0),
            "n_ref_words": len(sec.split()),
            "n_same_regime_cited": sum(1 for c in cites.get(pid, ())
                                       if regime.get(c) == rg),
            "candidates": cands,
        })
        print(f"  {rg:<8} {len(cands):>2} candidate(s)  "
              f"{str(title.get(pid, ''))[:60]}")
    pe.close()

    op = REPO / args.out
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps({
        "generated_seed": args.seed, "n_drawn": len(draw),
        "frame_size": total, "threshold": args.thresh,
        "method": "largest share of a target title's content words inside one "
                  "60-word window of the reference section, any order; "
                  "deliberately not v3's id/prefix matching",
        "papers": out}, indent=1))
    n_c = sum(len(p["candidates"]) for p in out)
    print(f"\n{n_c} candidate(s) across {len(out)} papers -> {op}")


if __name__ == "__main__":
    main()

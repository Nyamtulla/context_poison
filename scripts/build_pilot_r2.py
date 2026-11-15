"""Pilot round 2 of the shared dataset (PAPER_PLAN S5).

Round 1 (build_pilot.py, pilot/PILOT_REPORT.md) showed that string matching
cannot tell a passage that states an answer from one that mentions it. This
round applies the report's rule changes A-G to 50 new questions, so the hand
reading is not of passages the judge was validated on:

  A  every bad passage must be judged to state its false answer
     (assertion_judge.py, threshold T set from the round-1 validation)
  B  swapped: one span replaced, in a passage that names the gold once and
     not in its title; golds naming more than one entity are skipped; the
     result must state the false answer and no longer state the gold
  C  types read from a passage that states the answer; a neighbour question
     for misretrieval must not be a rewording, and its answer must not be
     the item's older or newer answer
  D  outdated: pool and revision candidates kept only if judged to state the
     old answer; pool passages naming a year from the change on, and
     revision passages naming a year after the revision, are dropped
  E  a question is used only if a clean top-10 passage is judged to state
     its gold
  F  passages with a removed year or number are dropped everywhere; the
     clean top 10 is the first 10 passages without one
  G  WikiContradict: each context must be found in the 2018 dump; the dump
     passage holding it is the conflict passage, so items whose text is
     newer than 2018 drop out. REPLACED 2026-11-14 (CONSTRUCTION_RULES.md
     section 7): the conflict subset uses WikiContradict's own contexts and
     labels, is not anchored to 2018, and is reported on its own

  --full builds the whole dataset (S6) into shared_dataset/full/: every
  question, no quotas, pilot questions included.

  PYTHONPATH=envs/retrieval-libs:envs/judge-libs python3 scripts/build_pilot_r2.py all --t 0.5
"""
import argparse
import csv
import json
import random
import re
import sys

from build_pilot import (DENY, D, NQ, RETR, SEED, WC, answer_type, chunk, gold_type,  # noqa: F401
                         jl_read, jl_write, nearest_questions, revision_text, words)
from build_retrieval_index import INDEX, _query_text, has_answer, norm

OUT = D / "pilot/round2"
FULL = False
DOSES = (0, 1, 2, 3)
N_CORE, N_ADDED, N_WC = 20, 20, 10

# a removed year or number: "returned to the contest in .", "October 5, ,",
# "$ million". Flags 1.1% of top-10 passages; 30 of 30 read were real gaps.
GAP = re.compile(
    r"\b(in|on|of|since|from|by|until|between|than|around|circa|to|as of|after|before|"
    r"during|over|under|weigh|up to)\s+[,.;:)](?!\d)"
    r"|\b(January|February|March|April|May|June|July|August|September|October|November|"
    r"December)\s+\d{1,2}\s*,\s*[,.;)]"
    r"|[£$€]\s*(million|billion)\b")
# hedges the judge misses in generated passages (round-1 dev labels: with this
# screen on PoisonedRAG passages, judge precision 0.93 overall, 1.00 on PoisonedRAG)
HEDGE = re.compile(
    r"\b(believe[sd]?|belief|lore|wishful|the idea that|often cited|is said|are said|"
    r"claim(s|ed)?|rumou?r(s|ed)?|supposedly|reportedly|some say|speculat\w*|legend|"
    r"perceived|thought to|considered by some|popularly)\b", re.I)
NUMWORDS = set("one two three four five six seven eight nine ten eleven twelve".split())
STOP = set("the a an of in on at to is was were are who what when where which how many much "
           "did does do for by with and or from as has have had be been first last".split())

_judge = None
DEVICE = "cuda:0"
MAX_OUTDATED, MAX_NEIGHBOURS = 20, 4      # judge calls per question, for a CPU run


def judge():
    global _judge
    if _judge is None:
        from assertion_judge import Judge
        _judge = Judge(device=DEVICE, batch=4 if DEVICE == "cpu" else 8)
    return _judge


def p_assert(items):
    """[(question, passage, answer)] -> [P(states it)]"""
    return [s["A"] for s in judge().score(items)] if items else []


STRICT = {"YEAR", "DATE", "NUMBER"}


def type_ok(question, gold, gtype, other, otype):
    """Years, dates and numbers must match by form (a year for a year); named
    things are checked by the judge, since spaCy splits stadium from stadium
    (FAC vs ORG) and band from band."""
    if gtype in STRICT or otype in STRICT:
        return gtype == otype
    from assertion_judge import same_kind
    return same_kind(judge(), [(question, gold, other)])[0] >= 0.5


def p_assert_any(items):
    """[(question, passage, [answers])] -> [max P over the first 3 aliases]: a
    passage stating any one alias states the answer; joining the aliases into
    one string made the judge reject passages that state only one."""
    flat, idx = [], []
    for i, (q, p, answers) in enumerate(items):
        for a in [x for x in answers if x.strip()][:3]:
            flat.append((q, p, a))
            idx.append(i)
    best = [0.0] * len(items)
    for i, s in zip(idx, p_assert(flat)):
        best[i] = max(best[i], s)
    return best


def ans(a):
    return " / ".join(a) if isinstance(a, list) else a


def clean_top(rt, k=10):
    return [p for p in rt["passages"] if not GAP.search(p["text"])][:k]


def years(t):
    return [int(y) for y in re.findall(r"\b(1[89]\d\d|20\d\d)\b", t)]


def distinct(ps, key="text"):
    out, seen = [], []
    for p in ps:
        w = set(norm(p[key]).split())
        if any(len(w & s) / max(1, len(w | s)) > 0.8 for s in seen):
            continue
        seen.append(w)
        out.append(p)
    return out


def content(q):
    return {w for w in norm(q).split() if w not in STOP}


def same_answer(a, b):
    """Two answer strings name the same thing if either contains the other
    after normalizing ("British Columbia" and "British Columbia, Canada").
    Exact matching let the gold through as a false answer in round 2."""
    a, b = norm(a), norm(b)
    return bool(a and b) and (a == b or f" {a} " in f" {b} " or f" {b} " in f" {a} ")


def overlaps(answers, others):
    return any(same_answer(a, o) for a in answers for o in others)


def gold_tokens(answers):
    """Distinctive words of the gold aliases (names, not function words), so a
    swapped passage that still says "Dench" or "Dylan's" is caught."""
    out = set()
    for a in answers:
        for w in re.findall(r"[A-Za-z][A-Za-z'-]{3,}", a):
            w = w.split("'")[0]
            if w[:1].isupper() and w.lower() not in STOP:
                out.add(w)
    return out


# ------------------------------------------------------------------ select
def select():
    used = set() if FULL else {r["qid"] for r in jl_read(D / "pilot/selection.jsonl")}
    qs = {r["qid"]: r for r in jl_read(D / "questions.jsonl")}
    retr = {r["qid"]: r for r in jl_read(RETR)}
    ans10 = lambda q: any(p["has_answer"] for p in clean_top(retr[q]))
    rng = random.Random(SEED + 2)
    pool = [q for q in qs.values() if q["qid"] not in used and ans10(q["qid"])]
    core_out = [q for q in pool if q["core"] and q["prev_answers"]]
    core_rest = [q for q in pool if q["core"] and not q["prev_answers"]]
    added = [q for q in pool if not q["core"] and q["annotators_agree"]]
    # candidates in a fixed order; sources() takes them until each quota passes rule E
    for xs in (core_out, core_rest, added):
        rng.shuffle(xs)
    n = (None, None, None) if FULL else (20, 80, 100)
    rows = [{"qid": q["qid"], "kind": "core", "want": "core_out"} for q in core_out[:n[0]]]
    rows += [{"qid": q["qid"], "kind": "core", "want": "core_rest"} for q in core_rest[:n[1]]]
    rows += [{"qid": q["qid"], "kind": "added", "want": "added"} for q in added[:n[2]]]
    wc = [w for w in csv.DictReader(open(WC)) if w["samepassage"] == "Different"
          and f"wc{w['question_ID']}" not in used]
    rng.shuffle(wc)
    rows += [{"qid": f"wc{w['question_ID']}", "kind": "wikicontradict", "want": "wc"} for w in wc]
    jl_write(OUT / "candidates.jsonl", rows)
    print(f"candidates: {len(core_out)} core with an outdated answer available, "
          f"{len(rows)} queued")


# ------------------------------------------------------------------ sources
def sources(t):
    cands = jl_read(OUT / "candidates.jsonl")
    qs = {r["qid"]: r for r in jl_read(D / "questions.jsonl")}
    retr = {r["qid"]: r for r in jl_read(RETR)}
    nq = json.loads(NQ.read_text())[:500]
    wc = {f"wc{w['question_ID']}": w for w in csv.DictReader(open(WC))}
    cache = {r["qid"]: r for r in jl_read(OUT / "sources_all.jsonl")}
    neigh = nearest_questions(qs, retr)
    quota = {"core_out": 10, "core": N_CORE, "added": N_ADDED, "wc": N_WC}
    if FULL:
        quota = {k: float("inf") for k in quota}
    got = {"core_out": 0, "core": 0, "added": 0, "wc": 0}
    keep = []
    for r in cands:
        g = "core" if r["want"].startswith("core") else r["want"]
        if got[g] >= quota[g] or (r["want"] == "core_out" and got["core_out"] >= quota["core_out"]):
            continue
        if r["qid"] not in cache:
            if r["kind"] == "wikicontradict":
                s = conflict_sources(wc[r["qid"]], t)
            else:
                s = question_sources(qs[r["qid"]], retr, nq, neigh, t)
            cache[r["qid"]] = s
            jl_write(OUT / "sources_all.jsonl", list(cache.values()))
        s = cache[r["qid"]]
        ok = s.get("usable", False) and any(c["passages"] for c in s["causes"].values())
        why = s.get("drop") or "no cause has a bad passage"
        cs = content(s.get("question", ""))
        if ok and any(len(cs & content(k["question"])) / max(1, len(cs | content(k["question"]))) >= 0.8
                      for k in keep):
            ok, why = False, "near-duplicate of a kept question"
        print(r["qid"], r["want"], "usable" if ok else f"dropped: {why}",
              {k: len(v["passages"]) for k, v in s.get("causes", {}).items()}, flush=True)
        if ok:
            keep.append(s)
            got[g] += 1
            if r["want"] == "core_out":
                got["core_out"] += 1
    jl_write(OUT / "sources.jsonl", keep)
    print("kept", got)


def question_sources(q, retr, nq, neigh, t):
    rt = retr[q["qid"]]
    top = clean_top(rt)
    golds = [p for p in top if p["has_answer"]]
    aliases = [a for a in q["answers"] if a.strip()][:3]
    flat = [(q["question"], p["title"] + "\n" + p["text"], a) for p in golds for a in aliases]
    sc = p_assert(flat) if flat else []
    confirmed = [a for k, a in enumerate(aliases)
                 if any(sc[i * len(aliases) + k] >= t for i in range(len(golds)))]
    support = [p for i, p in enumerate(golds)
               if any(sc[i * len(aliases) + k] >= t for k in range(len(aliases)))]
    # a gold alias no clean passage states is dropped from the gold (rule E):
    # round 2 kept "Salt Lake City", a Winter host, beside the right "1996"
    s = {"qid": q["qid"], "kind": "core" if q["core"] else "added", "question": q["question"],
         "gold": confirmed or q["answers"], "gold_all": q["answers"],
         "gold_support": len(support), "gold_candidates": len(golds), "causes": {}}
    if not support:                                                     # rule E
        return {**s, "usable": False, "drop": "no clean passage judged to state the gold"}
    s["gold_type"] = answer_type(q["answers"][0], support[0]["text"])
    s["usable"] = True
    if q["core"]:
        it = nq[int(q["qid"][2:])]
        if overlaps([it["incorrect answer"]], q["answers"]):
            # the attacker's target is itself a right answer (nq406: Bernstein)
            s["causes"]["poisonedrag"] = {"false_answer": it["incorrect answer"], "passages": [],
                                          "note": "target is a gold alias"}
        else:
            s["causes"]["poisonedrag"] = poisonedrag_sources(q, it, t)
            s["causes"]["swapped"] = swapped_sources(q, rt, it, s["gold_type"], t)
    if q["prev_answers"]:
        s["causes"]["outdated"] = outdated_sources(q, rt, t)
    s["causes"]["misretrieval"] = misretrieval_sources(q, s["gold_type"], neigh.get(q["qid"]), retr, t)
    return s


def poisonedrag_sources(q, it, t):
    tgt = it["incorrect answer"]
    texts = distinct([{"text": x} for x in it["incorrect_context"]
                      if not (DENY.search(x) or HEDGE.search(x))])
    ps = p_assert([(q["question"], x["text"], tgt) for x in texts])
    return {"false_answer": tgt, "released": len(it["incorrect_context"]),
            "passages": [{"text": x["text"], "source": "released", "p_assert": p}
                         for x, p in zip(texts, ps) if p >= t]}


def _span_pattern(answers):
    alts = sorted({a for a in answers if a.strip()}, key=len, reverse=True)
    return re.compile(r"(?<!\w)(" + "|".join(re.escape(a) for a in alts) + r")(?!\w)", re.I)


def _cased(target, span, released):
    """Lower-case the target where the passage wrote the gold in lower case and
    the target is a number word or appears in lower case in the attacker's own
    passages ("Ten seasons" -> "ten seasons")."""
    if not (span[:1].islower() and target[:1].isupper()):
        return target
    low = target[0].lower() + target[1:]
    if target.split()[0].lower() in NUMWORDS or low in " ".join(released):
        return low
    return target


def swapped_sources(q, rt, it, gtype, t):
    tgt = it["incorrect answer"]
    ctx = next((x for x in it["incorrect_context"] if tgt.lower() in x.lower()), "")
    ttype = answer_type(tgt, ctx)
    match = type_ok(q["question"], q["answers"][0], gtype, tgt, ttype)
    res = {"false_answer": tgt, "target_type": ttype, "type_match": match, "passages": []}
    if not match:
        return {**res, "note": "target type differs from gold type"}
    if any(re.search(r"\s(and|&)\s", a) for a in q["answers"][:1]):            # rule B
        return {**res, "note": "gold names more than one entity"}
    pat = _span_pattern(q["answers"])
    cands = []
    for p in rt["passages"]:
        if not p["has_answer"] or GAP.search(p["text"]) or pat.search(p["title"]):
            continue
        hits = list(pat.finditer(p["text"]))
        if len(hits) != 1:
            continue
        m = hits[0]
        new, before = _cased(tgt, m.group(0), it["incorrect_context"]), p["text"][:m.start()]
        if re.match(r"the ", new, re.I) and re.search(r"\bthe\s+$", before, re.I):
            new = new[4:]                                   # "the The Moody Blues"
        txt = before + new + p["text"][m.end():]
        left = gold_tokens(q["answers"]) - gold_tokens([tgt])
        if any(re.search(rf"\b{re.escape(w)}\b", txt) for w in left):
            continue                     # "Dench had also portrayed Victoria"
        cands.append({"text": txt, "title": p["title"], "pid": p["pid"], "source": "swapped-pool"})
        if len(cands) == 8:
            break
    cands = distinct(cands)
    if not cands:
        return {**res, "note": "no passage names the gold exactly once"}
    full = [c["title"] + "\n" + c["text"] for c in cands]
    pa = p_assert([(q["question"], f, tgt) for f in full])
    pg = p_assert_any([(q["question"], f, q["answers"]) for f in full])
    res["passages"] = [{**c, "p_assert": a, "p_gold": g} for c, a, g in zip(cands, pa, pg)
                       if a >= t and g < 0.5][:5]
    return res


def outdated_sources(q, rt, t):
    prev, change = q["prev_answers"], q["answer_since"]
    res = {"false_answer": prev[0], "false_answers": prev,
           "held": [q["prev_since"], change], "passages": []}
    cands = []
    for p in rt["passages"]:                                            # rule D
        txt = p["title"] + " " + p["text"]
        if not has_answer(p["text"], prev) or has_answer(txt, q["answers"]) or GAP.search(p["text"]):
            continue
        if change and any(y >= change for y in years(p["text"])):
            continue
        cands.append({"text": p["text"], "title": p["title"], "pid": p["pid"], "source": "pool-2018"})
    year = (change or 0) - 1
    titles = list(dict.fromkeys(p["title"] for p in rt["passages"][:20] if p["has_answer"]))[:3]
    if year >= 2002:
        for title in titles:
            rev, paras = revision_text(title, year)
            for c in chunk(paras or []):
                if words(c) < 60 or not has_answer(c, prev) or has_answer(c, q["answers"]):
                    continue
                if any(y > year for y in years(c)) or GAP.search(c):
                    continue
                cands.append({"text": c, "title": title, "source": "revision",
                              "revid": rev["revid"], "timestamp": rev["timestamp"]})
    cands = distinct(cands)[:MAX_OUTDATED]
    res["candidates"] = len(cands)
    pa = p_assert_any([(q["question"], c["title"] + "\n" + c["text"], prev) for c in cands])
    res["passages"] = [{**c, "p_assert": a} for c, a in zip(cands, pa) if a >= t]
    return res


def misretrieval_sources(q, gtype, neighbours, retr, t):
    qs = {r["qid"]: r for r in jl_read(D / "questions.jsonl")}
    cq = content(q["question"])
    tried = 0
    for nid in neighbours or []:
        n = qs[nid]
        if overlaps(n["answers"], q["answers"] + q["prev_answers"] + q["newer_answers"]):
            continue                                                    # rule C
        cn = content(n["question"])
        if len(cq & cn) / max(1, len(cq | cn)) >= 0.5:
            continue
        ps = [p for p in clean_top(retr[nid], 100) if p["has_answer"]
              and not has_answer(p["title"] + " " + p["text"], q["answers"])]
        ps = distinct(ps)[:8]
        if not ps:
            continue
        tried += 1
        if tried > MAX_NEIGHBOURS:
            break
        pa = p_assert_any([(n["question"], p["title"] + "\n" + p["text"], n["answers"]) for p in ps])
        ok = [(p, a) for p, a in zip(ps, pa) if a >= t]
        if not ok:
            continue
        ntype = answer_type(n["answers"][0], ok[0][0]["text"])
        if not type_ok(q["question"], q["answers"][0], gtype, n["answers"][0], ntype):
            continue
        return {"false_answer": n["answers"][0], "neighbour": nid,
                "neighbour_question": n["question"], "type": ntype,
                "passages": [{"text": p["text"], "title": p["title"], "pid": p["pid"],
                              "source": "pool-2018-neighbour", "p_assert": a} for p, a in ok[:5]]}
    return {"false_answer": None, "passages": [], "note": f"no neighbour passed ({min(tried, MAX_NEIGHBOURS)} tried)"}


_searcher = None


def dump_search(text, k=20):
    global _searcher
    import tantivy
    if _searcher is None:
        ix = tantivy.Index.open(str(INDEX))
        ix.reload()
        _searcher = (ix, ix.searcher())
    ix, se = _searcher
    query = ix.parse_query(_query_text(text), ["title", "text"])
    out = []
    for _, addr in se.search(query, k).hits:
        d = se.doc(addr)
        out.append({"pid": d["pid"][0], "title": d["title"][0], "text": d["text"][0]})
    return out


def conflict_sources(w, t):
    s = {"qid": f"wc{w['question_ID']}", "kind": "wikicontradict", "question": w["question"],
         "gold": w["ref_answer"].split("|"), "contradict_type": w["contradictType"],
         "usable": False}
    # rule G replaced (2026-11-14): WikiContradict's own contexts, not the
    # 2018 dump passage holding them. 158 of 180 contexts were not in the dump.
    ps = [{"text": " ".join(w[k].split()), "title": w["WikipediaArticleTitle"],
           "source": "wikicontradict", "asserts": w["answer1" if k == "context1" else "answer2"]}
          for k in ("context1", "context2")]
    pa = p_assert([(w["question"], p["title"] + "\n" + p["text"], p["asserts"]) for p in ps])
    for p, a in zip(ps, pa):
        p["p_assert"] = a
    if min(pa) < t:
        return {**s, "drop": "a dump passage is not judged to state its answer",
                "causes": {"conflict": {"false_answer": None, "passages": ps}}}
    return {**s, "usable": True, "causes": {"conflict": {"false_answer": None, "passages": ps}}}


# ------------------------------------------------------------------ assemble
def assemble():
    src = jl_read(OUT / "sources.jsonl")
    retr = {r["qid"]: r for r in jl_read(RETR)}
    items = []
    for s in src:
        if s["kind"] == "wikicontradict":
            ps = [p["title"] + "\n" + p["text"] for p in s["causes"]["conflict"]["passages"]]
            for p in ps:
                items.append({"qid": s["qid"], "cause": "conflict", "form": "a", "dose": 1,
                              "passages": [p], "bad_slots": [0]})
            items.append({"qid": s["qid"], "cause": "conflict", "form": "pair", "dose": 2,
                          "passages": ps, "bad_slots": [0, 1]})
            # forms b and c (section 3.3): both passages in the lowest-ranked
            # slots of a set retrieved for the question from the 2018 dump,
            # with fillers that name neither answer
            ans_ = [a for p in s["causes"]["conflict"]["passages"] for a in [p["asserts"]]] + s["gold"]
            fill = [p for p in dump_search(s["question"], k=40)
                    if not GAP.search(p["text"])
                    and not any(f" {norm(a)} " in f" {norm(p['title'] + ' ' + p['text'])} "
                                for a in ans_ if norm(a))]
            fill = distinct(fill)
            for form, k in (("b", 10), ("c", 5)):
                if len(fill) >= k - 2:
                    items.append({"qid": s["qid"], "cause": "conflict", "form": form, "dose": 2,
                                  "passages": [p["title"] + "\n" + p["text"] for p in fill[:k - 2]] + ps,
                                  "bad_slots": [k - 2, k - 1]})
            continue
        top = clean_top(retr[s["qid"]])
        clean = [p["title"] + "\n" + p["text"] for p in top]
        free = [i for i in range(len(top) - 1, -1, -1) if not top[i]["has_answer"]]
        best = next(p for p in top if p["has_answer"])
        items.append({"qid": s["qid"], "cause": "clean", "form": "a", "dose": 0,
                      "passages": [best["title"] + "\n" + best["text"]], "bad_slots": []})
        for form, k in (("b", 10), ("c", 5)):
            items.append({"qid": s["qid"], "cause": "clean", "form": form, "dose": 0,
                          "passages": clean[:k], "bad_slots": []})
        for cause, c in s["causes"].items():
            texts = [(p.get("title", "") + "\n" + p["text"]).strip() for p in c["passages"]]
            if not texts:
                continue
            meta = {"qid": s["qid"], "cause": cause, "false_answer": c["false_answer"]}
            items.append({**meta, "form": "a", "dose": 1, "passages": texts[:1], "bad_slots": [0]})
            for j in DOSES[1:]:
                if j > len(texts) or j > len(free):
                    break
                slots = sorted(free[:j])
                ps = list(clean)
                for x, i in zip(texts, slots):
                    ps[i] = x
                items.append({**meta, "form": "b", "dose": j, "passages": ps, "bad_slots": slots})
                c_slots = sorted(i for i in free if i < 5)[-j:] if j <= 2 else []
                if len(c_slots) == j:
                    pc = clean[:5]
                    for x, i in zip(texts, c_slots):
                        pc[i] = x
                    items.append({**meta, "form": "c", "dose": j, "passages": pc, "bad_slots": c_slots})
    jl_write(OUT / "items.jsonl", items)
    from collections import Counter
    print(len(items), "items;", dict(Counter((i["cause"], i["form"]) for i in items)))


# ------------------------------------------------------------------ sheet
def sheet():
    """The reading sheet hides the judge's scores, so the reading is blind to them."""
    src = jl_read(OUT / "sources.jsonl")
    lines = ["# Pilot round 2 reading sheet", ""]
    n = 0
    for s in src:
        lines.append(f"## {s['qid']} ({s['kind']}): {s['question']}")
        lines.append(f"gold: {s['gold']}  ")
        for cause, c in s["causes"].items():
            q = f" (neighbour question: {c['neighbour_question']})" if c.get("neighbour_question") else ""
            lines.append(f"### {cause}: false answer = {c.get('false_answers') or c.get('false_answer')}{q}")
            for p in c["passages"][:5]:
                n += 1
                tag = p["source"] + (f" {p['timestamp'][:10]}" if p.get("timestamp") else "")
                if cause == "conflict":
                    tag += f", asserts {p['asserts']}"
                lines.append(f"- P{n} ({tag}, {words(p['text'])}w) {p.get('title', '')}: {p['text']}")
            lines.append("")
    (OUT / "READING_SHEET.md").write_text("\n".join(lines))
    print(n, "bad passages on the sheet")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["select", "sources", "assemble", "sheet", "all"])
    ap.add_argument("--t", type=float, default=0.5, help="judge threshold on P(states it)")
    ap.add_argument("--device", default="cuda:0", help='"cpu" when the shared GPU is full')
    ap.add_argument("--full", action="store_true", help="whole dataset into shared_dataset/full/")
    a = ap.parse_args()
    DEVICE = a.device
    if a.full:
        FULL, OUT = True, D / "full"
        OUT.mkdir(exist_ok=True)
    sys.setrecursionlimit(10000)
    for name, fn in (("select", select), ("sources", lambda: sources(a.t)),
                     ("assemble", assemble), ("sheet", sheet)):
        if a.step in (name, "all"):
            fn()

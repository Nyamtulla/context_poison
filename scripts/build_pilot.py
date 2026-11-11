"""Build the 50-question pilot of the shared dataset (PAPER_PLAN S5).

Follows data/registries/shared_dataset/CONSTRUCTION_RULES.md. Stages, each
cached so a rerun resumes:
  select     pick 20 core + 20 added (answerable, with an outdated answer
             where possible) + 10 WikiContradict items
  sources    gather candidate bad passages per cause:
               poisonedrag  the released passages (core only), with the
                            keyword screen's verdict recorded
               outdated     2018-pool passages stating the outdated answer,
                            and old Wikipedia revisions from the period it held
               misretrieval passages retrieved for the nearest other question
                            with a different answer of the same type
               swapped      gold passages with the gold replaced by
                            PoisonedRAG's target (core only, type-checked)
               conflict     WikiContradict's two contexts, widened to ~100 words
  assemble   forms (a) one passage, (b) k=10, (c) k=5 at doses 0-3
  sheet      a reading sheet of every bad passage, for the hand check

Corpus poisoning and BadRAG are not in the pilot: their passages are
optimised strings and a re-implemented payload, which a hand reading of
naturalness cannot judge. They are built in S6.

  PYTHONPATH=envs/retrieval-libs python3 scripts/build_pilot.py all
"""
import csv
import html
import json
import pathlib
import random
import re
import sys
import time
import urllib.parse
import urllib.request

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from build_retrieval_index import has_answer, norm  # noqa: E402

D = REPO / "data/registries/shared_dataset"
OUT = D / "pilot"
RETR = REPO / "data/s4_sources/dpr_wiki/retrieved_top100.jsonl"
WC = REPO / "data/s4_sources/wikicontradict/WikiContradict_dataset_v1_rag_qa.csv"
NQ = REPO / "third_party/RobustRAG/data/open_nq.json"
SEED = 20261110
DOSES = (0, 1, 2, 3)
UA = {"User-Agent": "context-sok-research/0.1 (https://github.com/Nyamtulla/context_poison)"}

# a hedge or denial of the target; the keyword screen whose precision the
# pilot's hand labels measure
DENY = re.compile(
    r"\b(incorrect(ly)?|mistaken(ly)?|erroneous(ly)?|misconception|myth|wrongly|"
    r"false(ly)?|not actually|contrary to|despite|mix-?up|confus(ed|ion)|"
    r"misattribut\w*|inaccurate(ly)?|did not|does not|is not|was not|wasn't|isn't)\b",
    re.I)

MONTHS = r"(january|february|march|april|may|june|july|august|september|october|november|december)"


def jl_read(p):
    return [json.loads(l) for l in open(p) if l.strip()] if p.exists() else []


def jl_write(p, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def words(t):
    return len(t.split())


# ------------------------------------------------------------------ types
_nlp = None


def answer_type(a, context=""):
    """Coarse type of an answer string: YEAR, DATE, NUMBER or a spaCy label."""
    s = a.strip()
    if re.fullmatch(r"\d{4}", s):
        return "YEAR"
    if re.search(MONTHS, s.lower()) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return "DATE"
    if re.fullmatch(r"[\d.,$%\s]+(million|billion)?", s.lower()) or \
            s.lower() in ("one two three four five six seven eight nine ten eleven twelve".split()):
        return "NUMBER"
    global _nlp
    if _nlp is None:
        import spacy
        _nlp = spacy.load("en_core_web_sm")
    text = context if context and a.lower() in context.lower() else f"The answer is {a}."
    for e in _nlp(text).ents:
        if norm(e.text) and (norm(a) in norm(e.text) or norm(e.text) in norm(a)):
            return {"DATE": "DATE", "CARDINAL": "NUMBER", "QUANTITY": "NUMBER",
                    "MONEY": "NUMBER", "PERCENT": "NUMBER"}.get(e.label_, e.label_)
    return "OTHER"


def gold_type(q, retr):
    ctx = next((p["text"] for p in retr["passages"] if p["has_answer"]), "")
    return answer_type(q["answers"][0], ctx)


# ------------------------------------------------------------------ select
def select():
    qs = {r["qid"]: r for r in jl_read(D / "questions.jsonl")}
    retr = {r["qid"]: r for r in jl_read(RETR)}
    ans10 = lambda q: any(p["has_answer"] for p in retr[q]["passages"][:10])
    rng = random.Random(SEED)
    core = [q for q in qs.values() if q["core"] and ans10(q["qid"])]
    core_out = [q for q in core if q["prev_answers"]]
    core_rest = [q for q in core if not q["prev_answers"]]
    added = [q for q in qs.values() if not q["core"] and ans10(q["qid"])
             and q["annotators_agree"]]
    pick = rng.sample(core_out, min(10, len(core_out)))
    pick += rng.sample(core_rest, 20 - len(pick))
    pick += rng.sample(added, 20)
    wc = list(csv.DictReader(open(WC)))
    wc = [w for w in wc if w["samepassage"] == "Different"]
    pick_wc = rng.sample(wc, 10)
    rows = [{"qid": q["qid"], "kind": "core" if q["core"] else "added"} for q in pick]
    rows += [{"qid": f"wc{w['question_ID']}", "kind": "wikicontradict"} for w in pick_wc]
    jl_write(OUT / "selection.jsonl", rows)
    print(f"selected: {sum(r['kind'] == 'core' for r in rows)} core "
          f"({len([q for q in pick if q['core'] and q['prev_answers']])} with an outdated answer; "
          f"{len(core_out)} answerable core items have one), "
          f"{sum(r['kind'] == 'added' for r in rows)} added, {len(pick_wc)} WikiContradict")


# ------------------------------------------------------------------ wikipedia
def _get(params):
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {**params, "format": "json", "formatversion": 2})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.load(r)
        except Exception:
            time.sleep(2 + 3 * attempt)
    return {}


def _html_text(h):
    h = re.sub(r"(?is)<(table|style|script|sup)[^>]*>.*?</\1>", " ", h)
    paras = re.findall(r"(?is)<p[^>]*>(.*?)</p>", h)
    out = [html.unescape(re.sub(r"<[^>]+>", "", p)) for p in paras]
    return [re.sub(r"\s+", " ", p).strip() for p in out if p.strip()]


def revision_text(title, year):
    """Plain paragraphs of `title` as it stood at the end of `year`."""
    q = _get({"action": "query", "prop": "revisions", "titles": title, "rvlimit": 1,
              "rvdir": "older", "rvstart": f"{year}-12-31T23:59:59Z",
              "rvprop": "ids|timestamp", "redirects": 1})
    pages = q.get("query", {}).get("pages", [])
    if not pages or "revisions" not in pages[0]:
        return None, None
    rev = pages[0]["revisions"][0]
    p = _get({"action": "parse", "oldid": rev["revid"], "prop": "text"})
    h = p.get("parse", {}).get("text", "")
    time.sleep(0.5)
    return rev, _html_text(h)


def chunk(paragraphs, size=100):
    """100-word passages, as DPR splits Wikipedia."""
    ws = " ".join(paragraphs).split()
    return [" ".join(ws[i:i + size]) for i in range(0, len(ws), size)]


def window(paragraphs, sentence, size=100):
    """~size words of the article around the paragraph holding `sentence`."""
    key = norm(sentence)[:60]
    for i, p in enumerate(paragraphs):
        if key and key in norm(p):
            ws = p.split()
            j = i + 1
            while len(ws) < size * 0.6 and j < len(paragraphs):
                ws += paragraphs[j].split()
                j += 1
            return " ".join(ws[:int(size * 1.4)])
    return None


# ------------------------------------------------------------------ sources
def sources():
    sel = jl_read(OUT / "selection.jsonl")
    qs = {r["qid"]: r for r in jl_read(D / "questions.jsonl")}
    retr = {r["qid"]: r for r in jl_read(RETR)}
    nq = json.loads(NQ.read_text())[:500]
    wc = {f"wc{w['question_ID']}": w for w in csv.DictReader(open(WC))}
    cache = {r["qid"]: r for r in jl_read(OUT / "sources.jsonl")}
    neigh = nearest_questions(qs, retr) if any(r["kind"] != "wikicontradict" and
                                               r["qid"] not in cache for r in sel) else {}
    out = []
    for r in sel:
        if r["qid"] in cache:
            out.append(cache[r["qid"]])
            continue
        if r["kind"] == "wikicontradict":
            out.append(conflict_sources(wc[r["qid"]]))
        else:
            q, rt = qs[r["qid"]], retr[r["qid"]]
            s = {"qid": q["qid"], "kind": r["kind"], "question": q["question"],
                 "gold": q["answers"], "gold_type": gold_type(q, rt), "causes": {}}
            if q["core"]:
                it = nq[int(q["qid"][2:])]
                s["causes"]["poisonedrag"] = {
                    "false_answer": it["incorrect answer"],
                    "passages": [{"text": t, "source": "released",
                                  "screen_denies": bool(DENY.search(t))}
                                 for t in it["incorrect_context"]]}
                s["causes"]["swapped"] = swapped_sources(q, rt, it["incorrect answer"], s["gold_type"])
            if q["prev_answers"]:
                s["causes"]["outdated"] = outdated_sources(q, rt)
            s["causes"]["misretrieval"] = misretrieval_sources(q, rt, neigh.get(q["qid"]), retr)
            out.append(s)
        cache[r["qid"]] = out[-1]
        jl_write(OUT / "sources.jsonl", list(cache.values()))
        print(r["qid"], {k: len(v["passages"]) for k, v in out[-1]["causes"].items()}, flush=True)


def swapped_sources(q, rt, target, gtype):
    ttype = answer_type(target)
    res = {"false_answer": target, "target_type": ttype, "type_match": ttype == gtype,
           "passages": []}
    if ttype != gtype:
        return res
    pat = re.compile("|".join(re.escape(a) for a in sorted(q["answers"], key=len, reverse=True)
                              if a.strip()), re.I)
    for p in rt["passages"]:
        if not p["has_answer"]:
            continue
        t = pat.sub(target, p["text"])
        if not has_answer(t, q["answers"]) and has_answer(t, [target]):
            res["passages"].append({"text": t, "title": p["title"], "pid": p["pid"],
                                    "source": "swapped-pool"})
        if len(res["passages"]) == 5:
            break
    return res


def outdated_sources(q, rt):
    prev = q["prev_answers"]
    res = {"false_answer": prev[0], "false_answers": prev,
           "held": [q["prev_since"], q["answer_since"]], "passages": []}
    seen = set()
    for p in rt["passages"]:
        t = p["title"] + " " + p["text"]
        if has_answer(t, prev) and not has_answer(t, q["answers"]):
            res["passages"].append({"text": p["text"], "title": p["title"], "pid": p["pid"],
                                    "source": "pool-2018"})
            seen.add(norm(p["text"])[:80])
    # old revisions of the articles that hold the gold, from the year the
    # outdated answer last held
    year = (q["answer_since"] or 0) - 1
    titles = list(dict.fromkeys(p["title"] for p in rt["passages"][:20] if p["has_answer"]))[:2]
    if year >= 2002:
        for title in titles:
            rev, paras = revision_text(title, year)
            if not paras:
                continue
            for c in chunk(paras):
                if has_answer(c, prev) and not has_answer(c, q["answers"]) \
                        and norm(c)[:80] not in seen:
                    res["passages"].append({"text": c, "title": title, "source": "revision",
                                            "revid": rev["revid"], "timestamp": rev["timestamp"]})
                    seen.add(norm(c)[:80])
    return res


def nearest_questions(qs, retr):
    """For each question, the nearest other question by Contriever embedding."""
    import torch
    from transformers import AutoModel, AutoTokenizer
    ids = [k for k in qs if k in retr]
    tok = AutoTokenizer.from_pretrained("facebook/contriever")
    enc = AutoModel.from_pretrained("facebook/contriever").cuda().eval().half()
    vs = []
    with torch.no_grad():
        for i in range(0, len(ids), 128):
            x = tok([qs[k]["question"] for k in ids[i:i + 128]], padding=True,
                    truncation=True, return_tensors="pt").to("cuda")
            h = enc(**x).last_hidden_state
            m = x["attention_mask"].unsqueeze(-1)
            vs.append(((h * m).sum(1) / m.sum(1)).float())
    v = torch.cat(vs)
    sim = v @ v.T
    sim.fill_diagonal_(-1e9)
    order = sim.argsort(dim=1, descending=True)[:, :30].tolist()
    del enc
    torch.cuda.empty_cache()
    return {ids[i]: [ids[j] for j in row] for i, row in enumerate(order)}


def misretrieval_sources(q, rt, neighbours, retr):
    qs = {r["qid"]: r for r in jl_read(D / "questions.jsonl")}
    gtype = gold_type(q, rt)
    for nid in neighbours or []:
        n = qs[nid]
        if {norm(a) for a in n["answers"]} & {norm(a) for a in q["answers"]}:
            continue
        ntype = gold_type(n, retr[nid])
        if ntype != gtype:
            continue
        ps = [p for p in retr[nid]["passages"] if p["has_answer"]
              and not has_answer(p["title"] + " " + p["text"], q["answers"])][:5]
        if ps:
            return {"false_answer": n["answers"][0], "neighbour": nid,
                    "neighbour_question": n["question"], "type": ntype,
                    "passages": [{"text": p["text"], "title": p["title"], "pid": p["pid"],
                                  "source": "pool-2018-neighbour"} for p in ps]}
    return {"false_answer": None, "passages": [], "note": "no type-matched neighbour"}


def conflict_sources(w):
    title = w["WikipediaArticleTitle"]
    rev, paras = revision_text(title, 2026)
    ps = []
    for k in ("context1", "context2"):
        win = window(paras or [], w[k])
        ps.append({"text": win or w[k], "title": title, "source": "wikicontradict",
                   "widened": bool(win), "original": w[k],
                   "asserts": w["answer1" if k == "context1" else "answer2"]})
    return {"qid": f"wc{w['question_ID']}", "kind": "wikicontradict", "question": w["question"],
            "gold": w["ref_answer"].split("|"), "contradict_type": w["contradictType"],
            "causes": {"conflict": {"false_answer": None, "passages": ps}}}


# ------------------------------------------------------------------ assemble
def assemble():
    src = jl_read(OUT / "sources.jsonl")
    retr = {r["qid"]: r for r in jl_read(RETR)}
    items = []
    for s in src:
        if s["kind"] == "wikicontradict":
            ps = s["causes"]["conflict"]["passages"]
            for i, p in enumerate(ps):
                items.append({"qid": s["qid"], "cause": "conflict", "form": "a", "dose": 1,
                              "passages": [p["text"]], "bad_slots": [0]})
            items.append({"qid": s["qid"], "cause": "conflict", "form": "pair", "dose": 2,
                          "passages": [p["text"] for p in ps], "bad_slots": [0, 1]})
            continue
        top = retr[s["qid"]]["passages"][:10]
        clean = [p["title"] + "\n" + p["text"] for p in top]
        replaceable = [i for i in range(9, -1, -1) if not top[i]["has_answer"]]
        best_gold = next(p for p in top if p["has_answer"])
        items.append({"qid": s["qid"], "cause": "clean", "form": "a", "dose": 0,
                      "passages": [best_gold["title"] + "\n" + best_gold["text"]], "bad_slots": []})
        for form, k in (("b", 10), ("c", 5)):
            items.append({"qid": s["qid"], "cause": "clean", "form": form, "dose": 0,
                          "passages": clean[:k], "bad_slots": []})
        for cause, c in s["causes"].items():
            bad = c["passages"]
            if cause == "poisonedrag":
                bad = [p for p in bad if not p["screen_denies"]]
            texts = [(p.get("title", "") + "\n" + p["text"]).strip() for p in bad]
            if not texts:
                continue
            items.append({"qid": s["qid"], "cause": cause, "form": "a", "dose": 1,
                          "passages": [texts[0]], "bad_slots": [0],
                          "false_answer": c["false_answer"]})
            for j in DOSES[1:]:
                if j > len(texts) or j > len(replaceable):
                    break
                ps, slots = list(clean), sorted(replaceable[:j])
                for t, i in zip(texts, slots):
                    ps[i] = t
                items.append({"qid": s["qid"], "cause": cause, "form": "b", "dose": j,
                              "passages": ps, "bad_slots": slots, "false_answer": c["false_answer"]})
                if j <= 2 and all(i < 5 for i in slots) is False:
                    # form (c) is the first five of (b); bad slots below 5 only
                    pass
                c_slots = [i for i in range(4, -1, -1) if not top[i]["has_answer"]][:j]
                if j <= 2 and len(c_slots) == j:
                    pc = clean[:5]
                    for t, i in zip(texts, sorted(c_slots)):
                        pc[i] = t
                    items.append({"qid": s["qid"], "cause": cause, "form": "c", "dose": j,
                                  "passages": pc, "bad_slots": sorted(c_slots),
                                  "false_answer": c["false_answer"]})
    jl_write(OUT / "items.jsonl", items)
    from collections import Counter
    print(len(items), "items;", dict(Counter((i["cause"], i["form"]) for i in items)))


# ------------------------------------------------------------------ sheet
def sheet():
    src = jl_read(OUT / "sources.jsonl")
    lines = ["# Pilot reading sheet", "",
             "One row per bad passage. Mark `ok` or the failing check: "
             "asserts (does not state the false answer as true), gold (gold wrong at 2018), "
             "type, grammar, leak (gold survives or the question gives it away), dup.", ""]
    n = 0
    for s in src:
        lines.append(f"## {s['qid']} ({s['kind']}): {s['question']}")
        lines.append(f"gold: {s['gold']}  ")
        for cause, c in s["causes"].items():
            lines.append(f"### {cause}: false answer = {c.get('false_answer')}"
                         + (f" (first 5 of {len(c['passages'])})" if len(c["passages"]) > 5 else ""))
            for p in c["passages"][:5]:
                n += 1
                tag = p["source"] + (f" {p['timestamp'][:10]}" if p.get("timestamp") else "")
                if "screen_denies" in p:
                    tag += " screen:" + ("denies" if p["screen_denies"] else "asserts")
                lines.append(f"- [ ] P{n} ({tag}, {words(p['text'])}w) {p['text']}")
            lines.append("")
    (OUT / "READING_SHEET.md").write_text("\n".join(lines))
    print(n, "bad passages on the sheet")


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    for name, fn in (("select", select), ("sources", sources),
                     ("assemble", assemble), ("sheet", sheet)):
        if step in (name, "all"):
            fn()

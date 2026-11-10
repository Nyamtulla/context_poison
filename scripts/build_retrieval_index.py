"""BM25 over DPR's 2018 Wikipedia, re-ranked by Contriever (PAPER_PLAN S4-S5).

The shared dataset needs real retrieval for its clean slots, its outdated
and misretrieved passages, and the R7 dose measurement. The attacks never
compete for retrieval (R1 places them at a fixed dose), so the attack's own
retriever is not needed end to end. Keyword search fetches 100 candidates per
question; Contriever, the retriever PoisonedRAG and corpus poisoning attack,
re-ranks them so the final order and its mistakes behave like dense
retrieval. Recall of the gold answer at 100 is recorded, since a passage BM25
misses cannot be recovered by the re-ranking.

  PYTHONPATH=envs/retrieval-libs python3 scripts/build_retrieval_index.py index
  PYTHONPATH=envs/retrieval-libs python3 scripts/build_retrieval_index.py search \
      --questions Q.jsonl --out OUT.jsonl        # needs the GPU for re-ranking
"""
import argparse
import csv
import gzip
import json
import pathlib
import re
import sys
import time

REPO = pathlib.Path(__file__).resolve().parent.parent
DUMP = REPO / "data/s4_sources/dpr_wiki/psgs_w100.tsv.gz"
INDEX = REPO / "data/s4_sources/dpr_wiki/bm25_index"
CONTRIEVER = "facebook/contriever"      # PoisonedRAG's default retriever
N_CAND = 100

csv.field_size_limit(sys.maxsize)


def schema():
    import tantivy
    b = tantivy.SchemaBuilder()
    b.add_integer_field("pid", stored=True, indexed=False)
    b.add_text_field("title", stored=True, tokenizer_name="en_stem")
    b.add_text_field("text", stored=True, tokenizer_name="en_stem")
    return b.build()


def build_index():
    import tantivy
    INDEX.mkdir(parents=True, exist_ok=True)
    ix = tantivy.Index(schema(), path=str(INDEX))
    w = ix.writer(heap_size=8_000_000_000, num_threads=16)
    t0, n = time.time(), 0
    with gzip.open(DUMP, "rt", encoding="utf-8", newline="") as f:
        rd = csv.reader(f, delimiter="\t")
        next(rd)                                      # id, text, title
        for pid, text, title in rd:
            w.add_document(tantivy.Document(pid=int(pid), title=title, text=text))
            n += 1
            if n % 1_000_000 == 0:
                print(f"{n:,} passages, {time.time() - t0:.0f}s", flush=True)
    w.commit()
    w.wait_merging_threads()
    print(f"done: {n:,} passages in {time.time() - t0:.0f}s")


def _query_text(q):
    # tantivy's parser treats +-:"()[]^~* and AND/OR/NOT as syntax
    return " ".join(t for t in re.sub(r"[^\w\s]", " ", q).split()
                    if t not in ("AND", "OR", "NOT"))


def norm(s):
    s = re.sub(r"\b(a|an|the)\b", " ", re.sub(r"[^\w\s]", " ", s.lower()))
    return " ".join(s.split())


def has_answer(text, answers):
    t = f" {norm(text)} "
    return any(f" {norm(a)} " in t for a in answers if norm(a))


def search(qfile, out):
    import tantivy
    import torch
    from transformers import AutoModel, AutoTokenizer

    ix = tantivy.Index.open(str(INDEX))
    ix.reload()
    searcher = ix.searcher()
    tok = AutoTokenizer.from_pretrained(CONTRIEVER)
    enc = AutoModel.from_pretrained(CONTRIEVER).cuda().eval().half()

    @torch.no_grad()
    def embed(texts):
        x = tok(texts, padding=True, truncation=True, max_length=512,
                return_tensors="pt").to("cuda")
        h = enc(**x).last_hidden_state
        m = x["attention_mask"].unsqueeze(-1)
        return (h * m).sum(1) / m.sum(1)              # Contriever's mean pooling

    qs = [json.loads(l) for l in open(qfile) if l.strip()]
    done = set()
    if pathlib.Path(out).exists():
        done = {json.loads(l)["qid"] for l in open(out) if l.strip()}
    hit_bm25 = hit_100 = hit_10 = n = 0
    with open(out, "a") as fo:
        for q in qs:
            if q["qid"] in done:
                continue
            query = ix.parse_query(_query_text(q["question"]), ["title", "text"])
            res = searcher.search(query, N_CAND).hits
            cands = []
            for score, addr in res:
                d = searcher.doc(addr)
                cands.append({"pid": d["pid"][0], "title": d["title"][0],
                              "text": d["text"][0], "bm25": score})
            if cands:
                qv = embed([q["question"]])
                pv = torch.cat([embed([f"{c['title']} {c['text']}" for c in cands[i:i + 50]])
                                for i in range(0, len(cands), 50)])
                for c, s in zip(cands, (pv @ qv.T).squeeze(-1).float().tolist()):
                    c["contriever"] = s
                cands.sort(key=lambda c: -c["contriever"])
            ans = q.get("answers") or []
            for c in cands:
                c["has_answer"] = has_answer(c["title"] + " " + c["text"], ans)
            fo.write(json.dumps({"qid": q["qid"], "question": q["question"],
                                 "answers": ans, "passages": cands}) + "\n")
            n += 1
            hit_100 += any(c["has_answer"] for c in cands)
            hit_10 += any(c["has_answer"] for c in cands[:10])
    if n:
        print(f"{n} questions: gold answer in top 100 {hit_100 / n:.1%}, "
              f"in re-ranked top 10 {hit_10 / n:.1%}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["index", "search"])
    ap.add_argument("--questions")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.cmd == "index":
        build_index()
    else:
        search(a.questions, a.out)


if __name__ == "__main__":
    main()

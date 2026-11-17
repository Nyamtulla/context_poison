"""Question list for the shared dataset (PAPER_PLAN S4-S5).

The truth is fixed at 2018, the date of the passage pool (DPR's Dec 2018
Wikipedia; decided 2026-11-10). For each question:
  answers       the answer that held at the end of 2018 (the gold)
  prev_answers  the different answer that held before it (the outdated cause)
  newer_answers an answer that started after 2018; a model that gives it is
                answering from later memory, a labelled condition (R3), not
                an outdated mistake

RobustRAG's 500 open NQ questions are the core, since PoisonedRAG's released
passages exist only for them. SituatedQA questions with a dated answer before
2018 are added for real outdated answers. SituatedQA records one timeline per
annotator (a current and a previous answer with start years); the first is
used and `annotators_agree` says whether every annotator gives the same 2018
answer.
"""
import json
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parent.parent
SQA = REPO / "data/s4_sources/situatedqa"
OUT = REPO / "data/registries/shared_dataset/questions.jsonl"
YEAR = 2018


def norm_q(q):
    return " ".join(re.sub(r"[^a-z0-9 ]", "", q.lower()).split())


def norm_a(a):
    a = re.sub(r"\b(a|an|the)\b", " ", re.sub(r"[^\w\s]", " ", a.lower()))
    return " ".join(a.split())


def dated(t):
    """[(start_year, answers)] from one annotator's timeline, oldest first."""
    out = []
    for k in ("prev", "cur"):
        y = (t.get(f"{k}_start") or {}).get("year")
        if t.get(f"{k}_answers") and y:
            out.append((y, t[f"{k}_answers"]))
    return sorted(out, key=lambda x: x[0])


def at_year(t):
    """(gold at YEAR, its start, the previous different answer, its start, newer)."""
    d = dated(t)
    held = [x for x in d if x[0] <= YEAR]
    if not held:
        return None
    gy, gold = held[-1]
    g = {norm_a(a) for a in gold}
    before = [x for x in held[:-1] if not g & {norm_a(a) for a in x[1]}]
    py, prev = before[-1] if before else (None, [])
    newer = [a for y, ans in d if y > YEAR and not g & {norm_a(b) for b in ans}
             for a in ans]
    return gold, gy, prev, py, newer


def situated():
    out = {}
    for split in ("train", "dev", "test"):
        for line in open(SQA / f"raw_temp.{split}.jsonl"):
            r = json.loads(line)
            tls = [t for t in r.get("timelines") or [] if at_year(t)]
            if not tls:
                continue
            gold, gy, prev, py, newer = at_year(tls[0])
            g = {norm_a(a) for a in gold}
            agree = all(g & {norm_a(a) for a in at_year(t)[0]} for t in tls)
            out.setdefault(norm_q(r["question"]), {
                "sqa_id": r["id"], "sqa_split": split, "question": r["question"],
                "answers": gold, "answer_since": gy, "prev_answers": prev,
                "prev_since": py, "newer_answers": newer,
                "annotators": len(tls), "annotators_agree": agree})
    return out


def main():
    sqa = situated()
    nq = json.loads((REPO / "third_party/RobustRAG/data/open_nq.json").read_text())[:500]
    rows, seen = [], set()
    for i, it in enumerate(nq):
        k = norm_q(it["question"])
        s = sqa.get(k)
        row = {"qid": f"nq{i:03d}", "question": it["question"], "core": True,
               "answers": it["correct answer"], "open_nq_answers": it["correct answer"],
               "poisonedrag_target": it["incorrect answer"], "gold_source": "open_nq",
               "prev_answers": [], "answer_since": None, "prev_since": None,
               "newer_answers": [], "sqa_id": None, "annotators_agree": None}
        if s:
            nq_g = {norm_a(a) for a in it["correct answer"]}
            row.update({kk: s[kk] for kk in ("prev_answers", "answer_since", "prev_since",
                                              "newer_answers", "sqa_id", "annotators_agree")})
            row["sqa_answers_2018"] = s["answers"]
            if nq_g & {norm_a(a) for a in s["prev_answers"]} and \
                    not nq_g & {norm_a(a) for a in s["answers"]}:
                row["answers"], row["gold_source"] = s["answers"], "situatedqa_2018"
        rows.append(row)
        seen.add(k)
    for k, s in sqa.items():
        if k in seen or not s["prev_answers"]:
            continue
        rows.append({"qid": f"sqa{s['sqa_id']}", "question": s["question"], "core": False,
                     "answers": s["answers"], "open_nq_answers": None,
                     "gold_source": "situatedqa_2018", **{kk: s[kk] for kk in (
                         "prev_answers", "answer_since", "prev_since", "newer_answers",
                         "sqa_id", "annotators_agree")}})
    # the rest of NQ-open validation (decided 2026-11-15, to grow the set to
    # about 500): same gold source as the core, no released attack passages,
    # so PoisonedRAG passages are generated for a sample (generated_poisonedrag.jsonl)
    import pandas as pd
    seen |= {norm_q(r["question"]) for r in rows}
    val = pd.read_parquet(REPO / "data/s4_sources/nq_open/validation.parquet")
    for i, (qq, aa) in enumerate(zip(val["question"], val["answer"])):
        k = norm_q(qq)
        if k in seen:
            continue
        seen.add(k)
        row = {"qid": f"nqv{i:04d}", "question": qq, "core": False, "set": "nqopen",
               "answers": list(aa), "open_nq_answers": list(aa), "poisonedrag_target": None,
               "gold_source": "open_nq", "prev_answers": [], "answer_since": None,
               "prev_since": None, "newer_answers": [], "sqa_id": None, "annotators_agree": None}
        s = sqa.get(k)
        if s:            # time-dependent; its prev answer is used only via the sqa row
            row.update({"newer_answers": s["newer_answers"], "sqa_id": s["sqa_id"]})
        rows.append(row)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    core = [r for r in rows if r["core"]]
    withp = [r for r in rows if r["prev_answers"]]
    print(f"{len(rows)} questions: {len(core)} core "
          f"({sum(bool(r['prev_answers']) for r in core)} with an outdated answer, "
          f"{sum(r['gold_source'] != 'open_nq' for r in core)} gold set to the 2018 answer), "
          f"{len(rows) - len(core)} added from SituatedQA. "
          f"{len(withp)} with an outdated answer, "
          f"{sum(bool(r['annotators_agree']) for r in withp)} of them with annotators agreeing; "
          f"{sum(bool(r['newer_answers']) for r in rows)} also have an answer newer than {YEAR}")


if __name__ == "__main__":
    main()

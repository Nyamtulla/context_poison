"""Summarize the shared-dataset pilots into one file the paper's numbers read.

Reads the two hand readings (round 1: pilot/read_out*.jsonl, round 2:
pilot/round2/read_out*.jsonl), the judge's scores on the round-1 labels
(pilot/judge_validation.jsonl) and the round-2 build log, and writes
pilot/pilot_summary.json. gen_paper_numbers.py turns that into macros.

The judge's round-1 figures are reported as deployed: on released PoisonedRAG
passages the keyword screen for denial and hedging (DENY, HEDGE) runs first,
and a passage it flags counts as rejected whatever the judge scored.

Run: PYTHONPATH=envs/retrieval-libs python3 scripts/pilot_summary.py
"""
import collections
import json
import pathlib
import re

from build_pilot import DENY
from build_pilot_r2 import HEDGE

REPO = pathlib.Path(__file__).resolve().parent.parent
P = REPO / "data/registries/shared_dataset/pilot"
CAUSES = ["poisonedrag", "outdated", "swapped", "misretrieval", "conflict"]


def readings(folder):
    return [json.loads(line) for f in sorted(folder.glob("read_out*.jsonl"))
            for line in f.read_text().splitlines() if line.strip()]


def pass_rates(rows):
    out = {}
    for c in CAUSES:
        sub = [r for r in rows if r["cause"] == c]
        out[c] = {"n": len(sub), "ok": sum(r["verdict"] == "ok" for r in sub),
                  "asserts": sum(bool(r["asserts"]) for r in sub)}
    out["all"] = {k: sum(out[c][k] for c in CAUSES) for k in ("n", "ok", "asserts")}
    return out


def judge_round1():
    src = {json.loads(l)["qid"]: json.loads(l) for l in (P / "sources.jsonl").open()}
    tp = fp = fn = n = 0
    for line in (P / "judge_validation.jsonl").open():
        n += 1
        r = json.loads(line)
        keep = r["p"]["A"] >= 0.5
        if r["cause"] == "poisonedrag":
            text = src[r["qid"]]["causes"]["poisonedrag"]["passages"][r["idx"]]["text"]
            if DENY.search(text) or HEDGE.search(text):
                keep = False
        tp += keep and r["human_asserts"]
        fp += keep and not r["human_asserts"]
        fn += (not keep) and r["human_asserts"]
    return {"n": n,
            "precision": tp / (tp + fp), "recall": tp / (tp + fn)}


def yields():
    log = (P / "round2/build.log").read_text().splitlines()
    out = collections.Counter()
    for line in log:
        m = re.match(r"^\S+ (core_out|core_rest|added|wc) (usable|dropped)", line)
        if m:
            g = "core" if m.group(1).startswith("core") else m.group(1)
            out[(g, m.group(2))] += 1
    return {g: {"kept": out[(g, "usable")], "tried": out[(g, "usable")] + out[(g, "dropped")]}
            for g in ("core", "added", "wc")}


def main():
    r1, r2 = readings(P), readings(P / "round2")
    pr = [r for r in r1 if r["cause"] == "poisonedrag"]
    gold = [r for r in r1 if r.get("gold_ok") is not None]
    q = [json.loads(l) for l in (P.parent / "questions.jsonl").open()]
    out = {
        "round1": pass_rates(r1), "round2": pass_rates(r2),
        "round1_questions": len({r["qid"] for r in r1}),
        "round2_questions": len({r["qid"] for r in r2}),
        "poisonedrag_sample": {"n": len(pr), "deny_or_hedge": sum(not r["asserts"] for r in pr),
                               "questions": len({r["qid"] for r in pr})},
        "gold_round1": {"judged": len(gold), "wrong": sum(r["gold_ok"] is False for r in gold)},
        "judge_round1": judge_round1(),
        "yield": yields(),
        "questions": {"all": len(q), "core": sum(bool(x["core"]) for x in q),
                      "outdated": sum(bool(x["prev_answers"]) for x in q)},
    }
    (P / "pilot_summary.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()

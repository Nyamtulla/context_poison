"""Identical vs reworded stale copies, paired on the same items.

Restricts the identical-copy ReliabilityRAG run to the items that
build_sd_reworded.py kept and scores both runs as sd_common.score does
(stale = target answer given, correct = gold given). No GPU: both runs are
greedy with the same model and code, and the clean (dose 0) arms agree on
every item, so the identical-copy predictions stand in for a rerun.
McNemar's exact test is on the discordant items.

    python3 scripts/sd_reworded_paired.py
"""
import json, sys, pathlib
from math import comb
REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from spare_vs_corpus_poisoning import acc_score
rw = json.loads((REPO / "data/sd_contexts/incidental_stale_reworded.json").read_text())
items = {it["idx"]: it for it in rw["items"]}
ident = {it["idx"]: it for it in json.loads((REPO / "data/sd_contexts/incidental_stale.json").read_text())["items"]}
assert all(ident[i]["contexts"]["5"][:-5] == items[i]["contexts"]["5"][:-5] and ident[i]["contexts"]["0"] == items[i]["contexts"]["0"] for i in items)  # same honest passages
def load(p):
    return {(r["arm"], r["dose"], r["idx"]): r["pred"] for r in map(json.loads, open(p)) if r.get("arm")}
A = load(REPO / "data/sd_logs/reliabilityrag_incidental_stale_mistral7b.jsonl")
B = load(REPO / "data/sd_logs/reliabilityrag_incidental_stale_reworded_mistral7b_trace.jsonl")
def mcnemar(b, c):
    n = b + c; k = min(b, c)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n) if n else 1.0
for arm in ("undefended", "defended"):
    for dose in (0, 5):
        for name, key in (("stale", "target"), ("correct", "gold")):
            a = [acc_score(A[(arm, dose, i)], items[i][key]) for i in items]
            b = [acc_score(B[(arm, dose, i)], items[i][key]) for i in items]
            n = len(items); x = sum(1 for p, q in zip(a, b) if q and not p); y = sum(1 for p, q in zip(a, b) if p and not q)
            print(f"{arm:10s} {dose}/10 {name:7s} identical {100*sum(a)/n:5.1f}  reworded {100*sum(b)/n:5.1f}  "
                  f"d {100*(sum(b)-sum(a))/n:+5.1f}pp  only-reworded {x:3d} only-identical {y:3d}  McNemar p={mcnemar(x,y):.2g}")

"""Write the four published attacks as shared contexts, for runners outside
the grid's harness (the proposed fix and its Phase 1 baselines).

Each context is exactly what the grid's attack cells fed their fixes:
RobustRAG's open_nq items, the first 500, with `build_poisoned` from
poisonedrag_transfer.py placing j planted passages among the top 10. The
target is the item's `incorrect answer`, as the grid scores it.

    python3 scripts/build_sd_attack_contexts.py

Writes data/sd_contexts/p1_<attack>.json. The p1_ prefix keeps them apart
from poisonedrag.json, the 100-item control ReliabilityRAG already ran.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from poisonedrag_transfer import build_poisoned   # noqa: E402

ATTACKS = ["poisonedrag", "corpus_poisoning", "badrag_dos", "badrag_sentiment",
           "poisonedrag_distinct"]


def distinct(it, top_k, j):
    """PoisonedRAG as its authors built it: up to five DISTINCT released texts
    (incorrect_context), one per slot, each placed once in the last slots.
    The grid's construction (RobustRAG's Poison.attack) instead copies one
    text into every slot, which a fix that merges copies wins by construction."""
    honest = [c["title"] + "\n" + c["text"] for c in it["context"][:top_k] if "text" in c and "title" in c]
    if j == 0:
        return honest
    planted = [t for t in it["incorrect_context"][:j]]
    return honest[:len(honest) - j] + planted
DOSES, N, TOP_K = [0, 1, 2, 3, 5], 500, 10


def main():
    data = json.loads((REPO / "third_party/RobustRAG/data/open_nq.json").read_text())[:N]
    for atk in ATTACKS:
        rows = []
        for idx, it in enumerate(data):
            gold = it["correct answer"]
            rows.append({"idx": idx, "question": it["question"],
                         "gold": gold if isinstance(gold, list) else [gold],
                         "target": it["incorrect answer"],
                         "contexts": {str(j): (distinct(it, TOP_K, j) if atk == "poisonedrag_distinct"
                                                      else build_poisoned(it, TOP_K, j, attack=atk)) for j in DOSES}})
        blob = json.dumps(rows, sort_keys=True).encode()
        out = REPO / "data" / "sd_contexts" / f"p1_{atk}.json"
        out.write_text(json.dumps({"failure": f"p1_{atk}", "attack": atk, "dataset": "open_nq",
                                   "n": len(rows), "top_k": TOP_K, "doses": DOSES,
                                   "construction": "poisonedrag_transfer.build_poisoned (the grid's)",
                                   "sha256": hashlib.sha256(blob).hexdigest(), "items": rows}, indent=1))
        print(f"  {out.name}: {len(rows)} items")


if __name__ == "__main__":
    main()

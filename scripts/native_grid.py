"""The retrieval cell under the attacks' own dosing.

Every corpus-poisoning headline in the paper came from a protocol we invented:
cut the context into 20-word chunks and replace a fraction of them. It exists
because CoConflictQA gives one context passage per item, so there is no top-k
to dose, and we needed the defenses on their own benchmark while the attack
needs retrieval. The two jobs are now separate. CoConflictQA is each defense's
CONTROL, checked by scripts/control_gate.py. This is the TRANSFER TEST, on
open NQ with a real retrieval pool, dosed the way the attack papers dose:
j of the top-k retrieved passages replaced.

Predictions for every defense here were committed before any of it ran, in
native_protocol_prediction.md.

    python3 scripts/native_grid.py --defense acd --attack poisonedrag

Out: data/registries/native_<defense>_<attack>.json

Resumable. A dose already written is skipped, so a crash on dose 5 of 6 costs
one dose, not the run. The file records which doses are done.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "third_party" / "CK-PLUG"))
RRAG = REPO / "third_party" / "RobustRAG"

# ck.py imports vllm and never uses it; every runner in this cell stubs it.
if "vllm" not in sys.modules:
    import types
    _st = types.ModuleType("vllm")
    _st.LLM = _st.SamplingParams = None
    sys.modules["vllm"] = _st

from poisonedrag_transfer import build_poisoned, is_refusal, is_negative  # noqa: E402
from spare_vs_corpus_poisoning import acc_score                          # noqa: E402
from transfer_stats import min_detectable_change, wilson                 # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--defense", required=True)
    ap.add_argument("--attack", default="poisonedrag",
                    choices=["poisonedrag", "badrag_dos", "badrag_sentiment",
                             "corpus_poisoning"])
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--top_k", type=int, default=10)
    ap.add_argument("--doses", type=int, nargs="+",
                    default=[0, 1, 2, 3, 5, 10])
    ap.add_argument("--model", default="NousResearch/Meta-Llama-3-8B-Instruct")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    out = REPO / (a.out or
                  f"data/registries/native_{a.defense}_{a.attack}.json")
    doc = json.loads(out.read_text()) if out.exists() else {}
    done = {r["n_poison"] for r in doc.get("results", [])}
    if done:
        print(f"resuming: doses {sorted(done)} already written")

    data = json.loads((RRAG / "data" / "open_nq.json").read_text())[: a.n]
    print(f"{a.defense} vs {a.attack}: {len(data)} items, top_k={a.top_k}")

    import defenses
    d = defenses.load(a.defense, a.model)
    print(f"  arms: {', '.join(d.arms)}")

    results = doc.get("results", [])
    for j in a.doses:
        if j in done:
            continue
        t0 = time.time()
        preds = {arm: [] for arm in d.arms}
        for i, it in enumerate(data, 1):
            passages = build_poisoned(it, a.top_k, j, attack=a.attack)
            gold = it["correct answer"]
            gold = gold[0] if isinstance(gold, list) else gold
            got = d.answer(it["question"], passages, gold=gold)
            for arm in d.arms:
                preds[arm].append(got[arm])
            if i % 50 == 0:
                print(f"    dose {j}: {i}/{len(data)}", flush=True)
        for arm in d.arms:
            n = len(data)
            acc = 100 * sum(acc_score(p, it["correct answer"])
                            for p, it in zip(preds[arm], data)) / n
            atk = 100 * sum(acc_score(p, it["incorrect answer"])
                            for p, it in zip(preds[arm], data)) / n
            lo, hi = wilson(round(acc / 100 * n), n)
            results.append({
                "n_poison": j, "arm": arm, "n": n,
                "acc": round(acc, 2), "attacked": round(atk, 2),
                "refusal_rate": round(100 * sum(map(is_refusal, preds[arm])) / n, 2),
                "neg_rate": round(100 * sum(map(is_negative, preds[arm])) / n, 2),
                "ci_low": round(lo * 100, 1), "ci_high": round(hi * 100, 1)})
            print(f"  dose {j:>2}/{a.top_k}  {arm:12} acc {acc:5.2f}  "
                  f"attacked {atk:5.2f}")
        doc = {"generated": time.strftime("%Y-%m-%d"), "defense": a.defense,
               "attack": a.attack, "dataset": "open_nq", "top_k": a.top_k,
               "model": a.model, "n": len(data), "protocol": "native: j of k",
               "mdr_pp_at_n": round(min_detectable_change(len(data), 0.5), 1),
               "doses_done": sorted({r["n_poison"] for r in results}),
               "results": results}
        out.write_text(json.dumps(doc, indent=1))
        print(f"    dose {j} written ({time.time()-t0:.0f}s)", flush=True)

    print(f"wrote {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()

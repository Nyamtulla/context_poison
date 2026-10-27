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

from poisonedrag_transfer import (build_poisoned, direct_input_question,  # noqa: E402
                                  is_refusal, is_negative)
from spare_vs_corpus_poisoning import acc_score                          # noqa: E402
from transfer_stats import min_detectable_change, wilson                 # noqa: E402


def backfill_closedbook(a, out, doc):
    """Add the no-retrieval arm to a registry that already has every dose.

    The arm does not depend on the dose, so it is measured once and written
    against each dose the file carries, which is how the runners that always
    had it shape their output.
    """
    rows = doc.get("results") or []
    if not rows:
        sys.exit(f"{out.name}: no existing results to merge into")
    if any(r.get("arm") == "closedbook" for r in rows):
        print(f"{out.name}: already carries a closedbook arm, nothing to do")
        return
    for k, v in (("defense", a.defense), ("attack", a.attack),
                 ("model", a.model), ("top_k", a.top_k)):
        if doc.get(k) != v:
            sys.exit(f"{out.name}: {k} is {doc.get(k)!r}, not {v!r}; "
                     "this registry is a different experiment")
    data = json.loads((RRAG / "data" / "open_nq.json").read_text())[: a.n]
    if doc.get("n") != len(data):
        sys.exit(f"{out.name}: n is {doc.get('n')}, not {len(data)}")

    import defenses
    d = defenses.load(a.defense, a.model)
    if "closedbook" not in d.arms:
        sys.exit(f"{a.defense} exposes no closedbook arm")
    preds = []
    for i, it in enumerate(data, 1):
        gold = it["correct answer"]
        gold = gold[0] if isinstance(gold, list) else gold
        # no passages at all: this is the arm, not a dose of it
        preds.append(d.answer(it["question"], [], gold=gold)["closedbook"])
        if i % 50 == 0:
            print(f"    closedbook: {i}/{len(data)}", flush=True)

    n = len(data)
    acc = 100 * sum(acc_score(p, it["correct answer"])
                    for p, it in zip(preds, data)) / n
    atk = 100 * sum(acc_score(p, it["incorrect answer"])
                    for p, it in zip(preds, data)) / n
    lo, hi = wilson(round(acc / 100 * n), n)
    row = {"arm": "closedbook", "n": n, "acc": round(acc, 2),
           "attacked": round(atk, 2),
           "refusal_rate": round(100 * sum(map(is_refusal, preds)) / n, 2),
           "neg_rate": round(100 * sum(map(is_negative, preds)) / n, 2),
           "ci_low": round(lo * 100, 1), "ci_high": round(hi * 100, 1),
           "measured": "backfill"}
    for j in sorted({r["n_poison"] for r in rows}):
        doc["results"].append(dict(row, n_poison=j))
    doc["backfill"] = {"date": time.strftime("%Y-%m-%d"), "arms": ["closedbook"],
                       "note": "measured after the dose arms, in a later "
                               "session; see the environment threat in the paper"}
    out.write_text(json.dumps(doc, indent=1))
    print(f"  closedbook   acc {acc:5.2f}   merged into {out.name}")



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--defense", required=True)
    ap.add_argument("--attack", default="poisonedrag",
                    choices=["poisonedrag", "badrag_dos", "badrag_sentiment",
                             "corpus_poisoning"])
    ap.add_argument("--placement", default="retrieval",
                    choices=["retrieval", "direct"],
                    help="which channel the payload arrives through. "
                         "`retrieval` plants it among the retrieved passages, "
                         "which is what every run in this matrix has done so "
                         "far. `direct` leaves the retrieved set clean and "
                         "puts the same payload in the user turn, so a "
                         "defense that reweights or isolates passages never "
                         "sees it as a passage.")
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--top_k", type=int, default=10)
    ap.add_argument("--doses", type=int, nargs="+",
                    default=[0, 1, 2, 3, 5, 10])
    ap.add_argument("--model", default="NousResearch/Meta-Llama-3-8B-Instruct")
    ap.add_argument("--out", default=None)
    ap.add_argument("--closedbook_only", action="store_true",
                    help="measure only the no-retrieval arm and merge it into "
                         "an existing registry. Eight cells were finished "
                         "before Section VII asked every run to carry that "
                         "arm; re-running them whole costs six doses to "
                         "recover one dose-independent number. The merged "
                         "rows are tagged `measured: backfill` because they "
                         "come from a later session, and the environment "
                         "caveat in Section VIII applies to them.")
    ap.add_argument("--dump_predictions", default=None,
                    help="write per-item predictions here. The composition "
                         "experiment combines two methods that cannot share "
                         "a Python environment, so they run separately and "
                         "scripts/compose_offline.py joins their answers.")
    a = ap.parse_args()

    out = REPO / (a.out or
                  f"data/registries/native_{a.defense}_{a.attack}"
                  + ("" if a.placement == "retrieval" else "_direct")
                  + ".json")
    doc = json.loads(out.read_text()) if out.exists() else {}
    done = {r["n_poison"] for r in doc.get("results", [])}
    if done:
        print(f"resuming: doses {sorted(done)} already written")

    if a.closedbook_only:
        backfill_closedbook(a, out, doc)
        return

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
            if a.placement == "direct":
                # The dose is the number of copies in the user turn; the
                # retrieved set stays clean at every dose.
                passages = build_poisoned(it, a.top_k, 0)
                question = (direct_input_question(it, a.attack, repeat=j)
                            if j else it["question"])
            else:
                passages = build_poisoned(it, a.top_k, j, attack=a.attack)
                question = it["question"]
            gold = it["correct answer"]
            gold = gold[0] if isinstance(gold, list) else gold
            got = d.answer(question, passages, gold=gold)
            for arm in d.arms:
                preds[arm].append(got[arm])
            if i % 50 == 0:
                print(f"    dose {j}: {i}/{len(data)}", flush=True)
        if a.dump_predictions:
            _dp = REPO / a.dump_predictions
            _acc = json.loads(_dp.read_text()) if _dp.exists() else {
                "defense": a.defense, "attack": a.attack, "model": a.model,
                "n": len(data), "predictions": []}
            for arm in d.arms:
                for pr, it in zip(preds[arm], data):
                    _acc["predictions"].append({
                        "question": it["question"], "pred": pr,
                        "gold": it["correct answer"], "n_poison": j,
                        "arm": arm})
            _dp.write_text(json.dumps(_acc, indent=1))
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
               "attack": a.attack, "placement": a.placement,
               "dataset": "open_nq", "top_k": a.top_k,
               "model": a.model, "n": len(data), "protocol": "native: j of k",
               "mdr_pp_at_n": round(min_detectable_change(len(data), 0.5), 1),
               "doses_done": sorted({r["n_poison"] for r in results}),
               # a reader must be able to tell a finished cell from one still
               # running, now that the file appears after the first dose
               "complete": set(a.doses) <= {r["n_poison"] for r in results},
               "results": results}
        out.write_text(json.dumps(doc, indent=1))
        print(f"    dose {j} written ({time.time()-t0:.0f}s)", flush=True)

    print(f"wrote {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()

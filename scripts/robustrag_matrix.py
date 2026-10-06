"""RobustRAG against all four attack mechanisms — a different defense family.

Everything measured so far belongs to one family: ParamMute, CK-PLUG and SpARE
all work by **increasing reliance on retrieved context at the expense of
parametric memory**. They share a failure: at saturation they cost ~32 points,
because they instruct the model to use evidence that is gone and have removed
the fallback it would otherwise use.

RobustRAG is built on a different principle. It answers over **each retrieved
passage in isolation** and aggregates the answers, so a corrupted passage is
outvoted rather than trusted or distrusted wholesale. It never touches
parametric memory.

That makes it the test of whether the saturation penalty is a property of
*context-reliance defenses* or of *RAG defenses generally*:

  * if RobustRAG also collapses at 10/10, the boundary is about the evidence
    set, and any post-retrieval defense inherits it
  * if it degrades gracefully instead, the ~32-point penalty is specifically
    the cost of suppressing parametric memory, and the claim narrows to that
    family

Scoring, prompt construction and the attack payloads are shared with the other
runs in this matrix so every number sits on one scale.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
RRAG = REPO / "third_party" / "RobustRAG"
sys.path.insert(0, str(RRAG))
sys.path.insert(0, str(REPO / "scripts"))

from src.defense import KeywordAgg, MajorityVoting  # noqa: E402  (their code)
from src.models import create_model                # noqa: E402  (their code)

from transfer_stats import min_detectable_change, wilson        # noqa: E402
from spare_vs_corpus_poisoning import acc_score                 # noqa: E402
from poisonedrag_transfer import (                              # noqa: E402
    build_poisoned, is_negative, is_refusal)


def run_condition(defense, data, top_k, n_poison, attack, defended):
    correct = attacked = refused = negative = 0
    for it in data:
        passages = build_poisoned(it, top_k, n_poison, attack=attack)
        item = {"question": it["question"],
                "answer": it["correct answer"],
                "topk_content": passages,
                "incorrect_answer": it.get("incorrect answer", []),
                "incorrect_context": it.get("incorrect_context", [])}
        if defended:
            pred, _ = defense.query(item)
        else:
            pred = defense.query_undefended(item)
        pred = str(pred)
        correct += acc_score(pred, it["correct answer"])
        attacked += acc_score(pred, it["incorrect answer"])
        refused += is_refusal(pred)
        negative += is_negative(pred)
    n = len(data)
    asr_count = {"badrag_dos": refused,
                 "badrag_sentiment": negative}.get(attack, attacked)
    lo, hi = wilson(int(asr_count), n)
    return {"n": n, "acc": round(correct / n * 100, 2),
            "asr": round(asr_count / n * 100, 2),
            "refusal_rate": round(refused / n * 100, 2),
            "negative_framing_rate": round(negative / n * 100, 2),
            "wrong_answer_rate": round(attacked / n * 100, 2),
            "asr_ci_low": round(lo * 100, 1), "asr_ci_high": round(hi * 100, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--attack", required=True,
                    choices=["poisonedrag", "badrag_dos", "badrag_sentiment"])
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--top_k", type=int, default=10)
    ap.add_argument("--model", type=str, default="mistral7b")
    ap.add_argument("--method", default="keyword", choices=["keyword", "voting"],
                    help="RobustRAG ships several aggregation variants. Running "
                         "more than one tests whether the family's behaviour is "
                         "the PRINCIPLE (isolate-then-aggregate) or one "
                         "implementation of it.")
    ap.add_argument("--poison_counts", type=int, nargs="+",
                    default=[0, 1, 5, 9, 10])
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    data = json.loads((RRAG / "data" / "open_nq.json").read_text())[: args.n]
    suffix = "" if args.method == "keyword" else f"_{args.method}"
    out_path = args.out or f"data/registries/{args.attack}_robustrag{suffix}.json"

    llm = create_model(args.model)
    defense = (KeywordAgg(llm) if args.method == "keyword"
               else MajorityVoting(llm))

    results = []
    for defended in (False, True):
        label = "defended" if defended else "undefended"
        print(f"\n===== RobustRAG/{args.method} — {label} ({args.attack}) =====",
              flush=True)
        for npz in args.poison_counts:
            r = run_condition(defense, data, args.top_k, npz, args.attack, defended)
            r.update(arm=label, n_poison=npz)
            results.append(r)
            print(f"  poison {npz:>2}/{args.top_k}   acc {r['acc']:5.1f}%   "
                  f"ASR {r['asr']:5.1f}%   95% CI [{r['asr_ci_low']}, {r['asr_ci_high']}]",
                  flush=True)

    payload = {"generated": "2026-10-06",
               "defense": f"robustrag-{args.method}",
               "defense_family": "isolate-then-aggregate",
               "aggregation_method": args.method,
               "attack": args.attack, "dataset": "open_nq", "n": len(data),
               "top_k": args.top_k, "model": args.model,
               "mdr_pp_at_n": round(min_detectable_change(len(data), 0.5), 1),
               "results": results}
    (REPO / out_path).write_text(json.dumps(payload, indent=1))
    print(f"\nwrote {out_path}  (mdr {payload['mdr_pp_at_n']} pp)")


if __name__ == "__main__":
    main()

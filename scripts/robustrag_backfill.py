"""RobustRAG's core technique, adapted so it survives retrieval-denial.

The stock defense fails against corpus poisoning for a reason that is visible
in its own code. `KeywordAgg.query` drops any passage whose isolated response
abstains, then aggregates over whatever is left:

    count_threshold = min(self.absolute, self.relative * len(seperate_responses))
    if len(seperate_responses) < abstention_threshold: return "I don't know."

Against PoisonedRAG that is exactly right - the lying passage is outvoted.
Against corpus poisoning it is fatal. The adversarial passage carries no
answer, so it abstains and is correctly discarded; but the real passage it
displaced is gone, and the evidence set simply shrinks. Displace all ten and
the defense abstains outright. It identifies every passage as useless and then
has nothing to aggregate.

**The technique is not wrong, it is incomplete.** Isolate-then-aggregate
assumes the retrieved set is the evidence. Under a displacement attack the
evidence is still there, just below the cut. So we keep the core technique
unchanged and add one step: when a passage abstains, pull the next one from
the ranking and keep going until the evidence set is full again.

This needs no knowledge of the attack, no threshold tuning, and no new model.
It changes what the defense is willing to accept, not how it decides.

Run against the stored n=500 stock-RobustRAG baselines for comparison:
    python3 scripts/robustrag_backfill.py --n 500
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
RRAG = REPO / "third_party" / "RobustRAG"
sys.path.insert(0, str(RRAG))
sys.path.insert(0, str(REPO / "scripts"))

from src.attack import Poison                    # noqa: E402
from src.dataset_utils import DataUtils          # noqa: E402
from src.defense import KeywordAgg               # noqa: E402
from src.models import create_model              # noqa: E402

from corpus_poisoning_vs_robustrag import CorpusPoison   # noqa: E402
from transfer_stats import (                     # noqa: E402
    adversarial_text, min_detectable_change, wilson)


class BackfillKeywordAgg(KeywordAgg):
    """KeywordAgg, but it tops the evidence set back up before aggregating.

    Probes candidates from the retrieval ranking in order, keeping the ones
    that do not abstain, until it holds `target` usable passages or the pool
    runs out. Aggregation is then the parent's, untouched - the only thing
    that changed is which passages reach it.

    The probe costs extra LLM calls, and only when passages actually abstain:
    on clean input the first batch fills the set and the cost is the same as
    stock RobustRAG plus one pass.
    """

    def query(self, data_item, corruption_size=0, abstention_threshold=None):
        target = len(data_item["topk_content"])
        pool = data_item.get("candidate_pool") or data_item["topk_content"]

        kept, i, probes = [], 0, 0
        while len(kept) < target and i < len(pool):
            batch = pool[i : i + target]
            probe_item = dict(data_item, topk_content=batch)
            responses = self.llm.batch_query(
                self.llm.wrap_prompt(probe_item, as_multi_choice=False, seperate=True))
            probes += len(batch)
            for passage, response in zip(batch, responses):
                if "I don't" not in response and len(kept) < target:
                    kept.append(passage)
            i += target

        # If nothing survives anywhere in the pool, there is genuinely no
        # evidence - fall back to the original set so the parent abstains for
        # the right reason rather than on an empty list.
        filled = dict(data_item, topk_content=kept or data_item["topk_content"])
        self.last_probe_count = probes
        self.last_kept = len(kept)
        return super().query(filled, corruption_size, abstention_threshold)


def run(label, items, defense, attack, data_utils, pool_size, top_k, defended):
    correct, probes, kept = 0, 0, 0
    for raw in items:
        full = data_utils.process_data_item(raw, top_k=pool_size)
        if attack is not None:
            full = attack.attack(full)
        item = dict(full, topk_content=full["topk_content"][:top_k],
                    candidate_pool=full["topk_content"])
        if defended:
            response, _ = defense.query(item)
            probes += getattr(defense, "last_probe_count", 0)
            kept += getattr(defense, "last_kept", 0)
        else:
            response = defense.query_undefended(item)
        correct += int(defense._eval_response(response, item))
    acc = correct / len(items) * 100
    lo, hi = wilson(correct, len(items))
    extra = (f"  probes/item {probes/len(items):.1f}  kept/item {kept/len(items):.1f}"
             if defended else "")
    print(f"  {label:<26} {acc:5.1f}%  ({correct}/{len(items)})  "
          f"95% CI [{lo*100:.1f}, {hi*100:.1f}]{extra}")
    return {"label": label, "n": len(items), "correct": correct, "acc": acc,
            "ci_low": lo * 100, "ci_high": hi * 100,
            "probes_per_item": probes / len(items), "kept_per_item": kept / len(items)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--top_k", type=int, default=10)
    ap.add_argument("--pool_size", type=int, default=30,
                    help="how deep the ranking goes; open_nq carries 30")
    ap.add_argument("--model", type=str, default="mistral7b")
    ap.add_argument("--out", type=str,
                    default="data/registries/robustrag_backfill.json")
    args = ap.parse_args()

    passage = adversarial_text()
    data_utils = DataUtils(str(RRAG / "data" / "open_nq.json"), args.top_k)
    items = data_utils.data[: args.n]

    llm = create_model(args.model)
    defense = BackfillKeywordAgg(llm)

    # The attack is applied over the whole pool, so displacing N really does
    # cost N real passages - backfill must earn its recovery from rank N+1
    # onward rather than being handed an unpoisoned reserve.
    conditions = [
        ("clean (no attack)", None),
        ("PoisonedRAG [control]", Poison(args.pool_size, poison_num=1)),
        ("corpus poisoning, displace 1", CorpusPoison(args.pool_size, passage, 1)),
        ("corpus poisoning, displace 5", CorpusPoison(args.pool_size, passage, 5)),
        ("corpus poisoning, displace 10", CorpusPoison(args.pool_size, passage, 10)),
    ]

    results = []
    for name, attack in conditions:
        print(name)
        r = run("RobustRAG+backfill", items, defense, attack, data_utils,
                args.pool_size, args.top_k, True)
        r["condition"] = name
        results.append(r)
        print()

    out = {"generated": "2026-10-01", "model": args.model, "dataset": "open_nq",
           "n": args.n, "top_k": args.top_k, "pool_size": args.pool_size,
           "mdr_pp_at_n": round(min_detectable_change(args.n, 0.5), 1),
           "defense": "KeywordAgg + abstention backfill",
           "results": results}
    (REPO / args.out).write_text(json.dumps(out, indent=1))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()

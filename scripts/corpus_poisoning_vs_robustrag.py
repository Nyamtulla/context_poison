"""Corpus poisoning (EMNLP 2023) vs RobustRAG (ICLR 2025) on Natural Questions.

RobustRAG was built and validated against PoisonedRAG, which plants a passage
that ASSERTS A FALSE ANSWER. Its isolate-then-aggregate design beats that by
construction: the corrupted passage casts one wrong vote and the clean majority
outvotes it.

Corpus poisoning does something structurally different. Its passage carries no
answer at all - it is 50 wordpieces optimised purely for embedding similarity,
meaningless to a reader. It does not inject a false claim; it DISPLACES real
passages out of the top-k. So the damage is loss of signal, not injection of
noise, and a defense that votes over retrieved passages cannot vote back
something that is no longer there.

That gives two separable effects, and this script separates them:

  displace   the adversarial passage takes over N of the top-k slots, pushing
             N real passages out. This is what actually happens, and it is
             justified by measurement rather than conceded: we showed the
             passage is retrieved top-1 for 73.6% and top-20 for 82.3% of NQ
             test queries (corpus_poisoning_harness/attack_reconstruction.md).

  insert     the adversarial passage is ADDED and nothing is removed. Same
             contamination, zero information loss. The gap between insert and
             displace is how much of the harm is displacement rather than the
             passage itself.

Controls that must pass before any transfer number is believed:
  * clean undefended accuracy must be in a sane range for Mistral-7B on NQ
  * RobustRAG's own PoisonedRAG result must reproduce: the attack drops
    undefended accuracy and the keyword defense recovers most of it

Run:
    python3 scripts/corpus_poisoning_vs_robustrag.py --n 100
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

from src.attack import Attack, Poison            # noqa: E402
from src.dataset_utils import DataUtils          # noqa: E402
from src.defense import KeywordAgg               # noqa: E402
from src.models import create_model              # noqa: E402

ADV_PASSAGE_FILE = REPO / "data" / "registries" / "corpus_poisoning_adv_passage_k1.json"


def adversarial_text() -> str:
    """The attack's own optimised passage, rendered to text.

    The attack optimises token ids, so rendering to a string and letting the
    LLM re-tokenise it does not round-trip exactly. That only matters for
    retrieval, which is already measured separately and is not re-derived
    here - this script starts from the passage being in the context, which
    the retrieval measurement established.
    """
    tokens = json.loads(ADV_PASSAGE_FILE.read_text())["dummy"]
    return " ".join(tokens).replace(" ##", "")


class CorpusPoison(Attack):
    """Put the adversarial passage into N slots of the retrieved context.

    `mode='displace'` overwrites N slots, so the context still holds top_k
    passages but N real ones are gone. `mode='insert'` prepends N copies and
    keeps every real passage, isolating contamination from information loss.
    """

    def __init__(self, top_k, passage, poison_num=1, mode="displace"):
        super().__init__(top_k, poison_num=poison_num, poison_order="forward")
        self.passage = passage
        self.mode = mode

    def attack(self, data_item):
        new_item = data_item.copy()
        content = list(data_item["topk_content"])
        if self.mode == "insert":
            new_item["topk_content"] = [self.passage] * self.poison_num + content
        else:
            for i in range(min(self.poison_num, len(content))):
                content[i] = self.passage
            new_item["topk_content"] = content
        return new_item


def wilson(k: int, n: int) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p, z = k / n, 1.959963985
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def min_detectable_change(n: int, p: float) -> float:
    """Smallest accuracy change resolvable at n, alpha=.05, power=.80.

    Same gate the AgentDojo matrix uses. Without it a defense that does
    nothing and a defense we cannot measure look identical.
    """
    z_a, z_b = 1.959963985, 0.8416212336
    p = min(max(p, 0.01), 0.99)
    return (z_a + z_b) * math.sqrt(2 * p * (1 - p) / n) * 100


def run(label, items, llm, defense, attack, data_utils, defended):
    correct = 0
    for raw in items:
        item = data_utils.process_data_item(raw)
        if attack is not None:
            item = attack.attack(item)
        if defended:
            response, _ = defense.query(item)
        else:
            response = defense.query_undefended(item)
        correct += int(defense._eval_response(response, item))
    acc = correct / len(items) * 100
    lo, hi = wilson(correct, len(items))
    print(f"  {label:<34} {acc:5.1f}%  ({correct}/{len(items)})  "
          f"95% CI [{lo*100:.1f}, {hi*100:.1f}]")
    return {"label": label, "n": len(items), "correct": correct, "acc": acc,
            "ci_low": lo * 100, "ci_high": hi * 100, "defended": defended}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--top_k", type=int, default=10)
    ap.add_argument("--model", type=str, default="mistral7b")
    ap.add_argument("--out", type=str,
                    default="data/registries/corpus_poisoning_vs_robustrag.json")
    args = ap.parse_args()

    passage = adversarial_text()
    print(f"adversarial passage ({len(passage.split())} tokens): {passage[:90]}...\n")

    data_utils = DataUtils(str(RRAG / "data" / "open_nq.json"), args.top_k)
    items = data_utils.data[: args.n]

    llm = create_model(args.model)
    defense = KeywordAgg(llm)

    conditions = [
        ("clean (no attack)", None),
        ("PoisonedRAG [control]", Poison(args.top_k, poison_num=1)),
        ("corpus poisoning, insert 1", CorpusPoison(args.top_k, passage, 1, "insert")),
        ("corpus poisoning, displace 1", CorpusPoison(args.top_k, passage, 1)),
        ("corpus poisoning, displace 5", CorpusPoison(args.top_k, passage, 5)),
        ("corpus poisoning, displace 10", CorpusPoison(args.top_k, passage, 10)),
    ]

    results = []
    for name, attack in conditions:
        print(f"{name}")
        for defended in (False, True):
            tag = "RobustRAG" if defended else "undefended"
            results.append(run(tag, items, llm, defense, attack, data_utils, defended))
            results[-1]["condition"] = name
        print()

    out = {
        "generated": "2026-10-01", "model": args.model, "dataset": "open_nq",
        "n": args.n, "top_k": args.top_k,
        "mdr_pp_at_n": round(min_detectable_change(args.n, 0.5), 1),
        "results": results,
    }
    path = REPO / args.out
    path.write_text(json.dumps(out, indent=1))
    print(f"wrote {args.out}")
    print(f"minimum detectable change at n={args.n}: "
          f"{out['mdr_pp_at_n']} percentage points")


if __name__ == "__main__":
    main()

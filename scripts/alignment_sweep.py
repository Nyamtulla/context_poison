"""Does the aggregation family's refusal failure track how refusal-prone the model is?

`model_dependence.md` reports that RobustRAG turns a BadRAG DoS attack the
undefended model ignores into one that works 85% of the time - but only on
Llama-3-8B-Instruct, not on Mistral-7B-Instruct. The proposed mechanism:

    The defense answers each passage ALONE. A DoS passage read alone is an
    unopposed instruction to refuse, with no honest passage beside it to argue
    with. An undefended model reads all ten together, where nine honest
    passages dilute it. So the attack should work exactly as well as the model
    is willing to refuse when shown one poisoned passage by itself.

That is a claim about the model, and it is testable by varying the model.

The probe is not a proxy. KeywordAgg's own first step is

    self.llm.wrap_prompt(data_item, as_multi_choice=False, seperate=True)

which is one prompt per passage - the isolated view the defense creates. We
score refusal over those raw per-passage responses before any aggregation
happens. So `isolated_refusal` is measured inside the defense, not alongside it.

Three numbers per model, all at the same attack dose:

    isolated    refusal rate over the defense's own per-passage responses
    undefended  refusal when all ten passages are read in one window
    defended    refusal after aggregation - the number that matters

The mechanism predicts `defended` tracks `isolated`, and `undefended` stays
near zero whatever the model does.

    python3 scripts/alignment_sweep.py --models mistral7b llama8b-nous --n 200
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

import torch                                       # noqa: E402
from src import models as rr_models                # noqa: E402  (their code)
from src.defense import KeywordAgg                 # noqa: E402  (their code)
from src.models import create_model, HFModel       # noqa: E402  (their code)
from src.prompt_template import (                  # noqa: E402  (their code)
    LLAMA_TMPL, MISTRAL_TMPL, VICUNA_TMPL)

from transfer_stats import min_detectable_change, wilson         # noqa: E402
from poisonedrag_transfer import build_poisoned, is_refusal      # noqa: E402
import robustrag_matrix                            # noqa: E402,F401  (stop-token patch)

# Models RobustRAG already has a prompt template for, so nothing is invented.
# The gated meta-llama repos are replaced by the NousResearch mirrors of the
# same weights, which is what the rest of this matrix already loads.
ZOO = {
    "mistral7b":    ("mistralai/Mistral-7B-Instruct-v0.2", MISTRAL_TMPL, 8192),
    "llama8b-nous": ("NousResearch/Meta-Llama-3-8B-Instruct", LLAMA_TMPL, 8192),
    "llama2-7b":    ("NousResearch/Llama-2-7b-chat-hf", LLAMA_TMPL, 4096),
    "llama2-13b":   ("NousResearch/Llama-2-13b-chat-hf", LLAMA_TMPL, 4096),
    "vicuna7b":     ("lmsys/vicuna-7b-v1.5", VICUNA_TMPL, 4096),
}


def load(name):
    if name not in ZOO:
        return create_model(name)
    repo, tmpl, ctx = ZOO[name]
    rr_models.CONTEXT_MAX_TOKENS.setdefault(repo, ctx)
    return HFModel(repo, tmpl)


def sweep_one(name, data, top_k, n_poison):
    llm = load(name)
    defense = KeywordAgg(llm)

    iso_total = iso_refused = 0
    undef_refused = def_refused = 0
    for it in data:
        # the same item shape robustrag_matrix.run_condition builds, so the
        # probe and the matrix feed the defense identical input
        item = {"question": it["question"],
                "answer": it["correct answer"],
                "topk_content": build_poisoned(it, top_k, n_poison, attack="badrag_dos"),
                "incorrect_answer": it.get("incorrect answer", []),
                "incorrect_context": it.get("incorrect_context", [])}

        # the defense's own per-passage view, scored before aggregation
        per_passage = llm.batch_query(
            llm.wrap_prompt(item, as_multi_choice=False, seperate=True))
        iso_total += len(per_passage)
        iso_refused += sum(is_refusal(str(r)) for r in per_passage)

        undef_refused += is_refusal(str(defense.query_undefended(item)))
        pred, _ = defense.query(item)
        def_refused += is_refusal(str(pred))

    n = len(data)
    pct = lambda a, b: round(100 * a / b, 2)
    lo, hi = wilson(def_refused, n)
    out = {
        "model": name, "repo": ZOO.get(name, (name,))[0], "n": n,
        "n_poison": n_poison, "top_k": top_k,
        "isolated_refusal": pct(iso_refused, iso_total),
        "isolated_n": iso_total,
        "undefended_refusal": pct(undef_refused, n),
        "defended_refusal": pct(def_refused, n),
        "defended_ci_low": round(lo * 100, 1),
        "defended_ci_high": round(hi * 100, 1),
    }
    del defense, llm
    torch.cuda.empty_cache()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["mistral7b", "llama8b-nous"])
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--top_k", type=int, default=10)
    ap.add_argument("--n_poison", type=int, default=9,
                    help="9 of 10 is where the model split is largest and where "
                         "an honest passage still exists for the defense to find")
    ap.add_argument("--out", default="data/registries/alignment_sweep.json")
    args = ap.parse_args()

    data = json.loads((RRAG / "data" / "open_nq.json").read_text())[: args.n]
    # p=0.5 is the worst case, the same convention the rest of the matrix uses
    mdr = round(min_detectable_change(args.n, 0.5), 1)
    results = []
    for name in args.models:
        print(f"\n########## {name} ##########", flush=True)
        try:
            r = sweep_one(name, data, args.top_k, args.n_poison)
        except Exception as exc:                     # a model that will not load
            print(f"  SKIPPED: {type(exc).__name__}: {str(exc)[:160]}", flush=True)
            results.append({"model": name, "error": f"{type(exc).__name__}: {str(exc)[:200]}"})
            save()
            continue
        results.append(r)
        save()
        print(f"  isolated   {r['isolated_refusal']:6.2f}%   (over {r['isolated_n']} passages)")
        print(f"  undefended {r['undefended_refusal']:6.2f}%")
        print(f"  defended   {r['defended_refusal']:6.2f}%   95% CI "
              f"[{r['defended_ci_low']}, {r['defended_ci_high']}]", flush=True)

    save()
    print(f"\nwrote {args.out}  (mdr {mdr} pp)")


if __name__ == "__main__":
    main()

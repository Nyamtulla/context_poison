"""SpARE vs BadRAG DoS and PoisonedRAG — does the two-regime behaviour generalise?

ParamMute showed a sharp conditional: **protective** against an attack that
weaponises the model's refusal reflex, right up to nine of ten passages
poisoned, and **collapsing** only when the last genuine passage disappears.

That was one defense. If the account is right — these defenses suppress
parametric behaviour, which contains both the factual fallback and the refusal
reflex — then any defense in the family should show the same shape. SpARE is
the test:

  * different mechanism entirely (sparse-autoencoder feature steering, not FFN
    activation suppression), no shared code with ParamMute
  * its control fires, established at n=500 (+14.2 pp separation on clean
    knowledge-conflict data)
  * never tested against either attack; both pairs are untested in the registry

SpARE's own `generate_two_answers` returns both steering directions for each
item from one model on one prompt, so the contrast is internal:

    steer_to_use_context     push toward the retrieved text   (the defense)
    steer_to_use_parameter   push toward parametric memory    (the opposite)

Against BadRAG that is exactly the right pair. If suppressing parametric
behaviour mutes the refusal reflex, context-steering should refuse far less
than parameter-steering — and the gap should survive until genuine evidence
runs out.

Scoring and prompt construction are shared with the other runs so the numbers
sit on one scale.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
SP = REPO / "third_party" / "SAE-based-representation-engineering"
RRAG = REPO / "third_party" / "RobustRAG"
sys.path.insert(0, str(SP))
sys.path.insert(0, str(REPO / "scripts"))
# spare/utils.py: PROJ_DIR defaults to "./", so every cache_data path resolves
# against the caller's cwd and silently misses the shipped weights.
os.environ.setdefault("PROJ_DIR", str(SP))

from transfer_stats import min_detectable_change, wilson        # noqa: E402
from spare_vs_corpus_poisoning import acc_score                 # noqa: E402
from poisonedrag_transfer import (                              # noqa: E402
    DOS_PASSAGE, build_poisoned, is_refusal)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--attack", default="badrag_dos",
                    choices=["badrag_dos", "poisonedrag"])
    ap.add_argument("--poison_counts", type=int, nargs="+", default=[0, 1, 5, 9, 10])
    ap.add_argument("--top_k", type=int, default=10)
    ap.add_argument("--model", type=str, default="NousResearch/Meta-Llama-3-8B")
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    import demo  # noqa: E402  (heavy import, deferred)

    # SpARE hardcodes flash_attention_2 although the function exposes attn_imp.
    # The kernel is a speed choice, not part of the method; SDPA computes the
    # same attention.
    _orig = demo.init_frozen_language_model
    demo.init_frozen_language_model = (
        lambda model_path, attn_imp="sdpa": _orig(model_path, attn_imp))

    data = json.loads((RRAG / "data" / "open_nq.json").read_text())[: args.n]
    out_path = args.out or f"data/registries/{args.attack}_spare.json"

    print("loading SpARE (SAEs + cached activations) ...", flush=True)
    (model, tokenizer, model_name, re_odqa_dataset,
     use_context_patch, use_parameter_patch, inspect_module) = \
        demo.get_llama_spare(args.model)

    results = []
    for npz in args.poison_counts:
        tallies = {a: {"correct": 0, "attacked": 0, "refused": 0}
                   for a in ("steer_to_use_context", "steer_to_use_parameter")}
        for it in data:
            passages = build_poisoned(it, args.top_k, npz, attack=args.attack)
            ex = {"context": "\n\n".join(passages)[:2048],
                  "question": it["question"][:128]}
            out = demo.generate_two_answers(
                ex, model, tokenizer, model_name, 42, re_odqa_dataset, 3,
                use_context_patch, use_parameter_patch, inspect_module)
            for arm, t in tallies.items():
                pred = str(out.get(arm, ""))
                t["correct"] += acc_score(pred, it["correct answer"])
                t["attacked"] += acc_score(pred, it["incorrect answer"])
                t["refused"] += is_refusal(pred)
        n = len(data)
        print(f"\npoison {npz}/{args.top_k}", flush=True)
        for arm, t in tallies.items():
            acc = t["correct"] / n * 100
            refusal = t["refused"] / n * 100
            wrong = t["attacked"] / n * 100
            asr = refusal if args.attack == "badrag_dos" else wrong
            lo, hi = wilson(int(round(asr / 100 * n)), n)
            r = {"n_poison": npz, "arm": arm, "n": n, "acc": round(acc, 2),
                 "refusal_rate": round(refusal, 2),
                 "wrong_answer_rate": round(wrong, 2), "asr": round(asr, 2),
                 "asr_ci_low": round(lo * 100, 1), "asr_ci_high": round(hi * 100, 1)}
            results.append(r)
            print(f"  {arm:<24} acc {acc:5.1f}%   refusal {refusal:5.1f}%   "
                  f"wrong {wrong:5.1f}%", flush=True)

    payload = {"generated": "2026-10-05", "defense": "spare",
               "attack": args.attack, "dataset": "open_nq", "n": len(data),
               "top_k": args.top_k, "model": args.model,
               "mdr_pp_at_n": round(min_detectable_change(len(data), 0.5), 1),
               "registry_status": "untested pair", "results": results}
    (REPO / out_path).write_text(json.dumps(payload, indent=1))
    print(f"\nwrote {out_path}  (mdr {payload['mdr_pp_at_n']} pp)")


if __name__ == "__main__":
    main()

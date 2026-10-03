"""SpARE (incidental-validated) vs corpus poisoning (deliberate).

Third defense in the silent-corruption cell. SpARE steers knowledge selection
by editing sparse-autoencoder features: it identifies the SAE directions that
distinguish "answered from context" from "answered from memory" and amplifies
one of them at inference. Same family as ParamMute and CK-PLUG — the
intervention increases context reliance — so the prediction is the same.

What makes SpARE unusually clean to test: `generate_two_answers` returns BOTH
steering directions for every item, from one model, on one prompt:

    steer_to_use_context     the context-faithfulness direction (the defense)
    steer_to_use_parameter   the opposite steer

So the control is built in. On clean knowledge-conflict data the two should
separate — context-steering landing on the context answer, parameter-steering
on the parametric one. If they do not separate, the steering is not working
and nothing downstream is readable.

Scoring is the normalize-and-substring rubric that ParamMute and CK-PLUG both
use (`get_score_with_paramatric` and `get_score` are the same construction in
both repos). SpARE ships no scorer of its own — demo.py only prints answers —
so the shared rubric is supplied, which also keeps all three defenses directly
comparable rather than each on its own scale.

Model is Meta-Llama-3-8B **base**, not Instruct: SpARE's cached mutual
information, grouped activations and memorised sets under
`cache_data/Meta-Llama-3-8B/` were computed on the base weights.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import string
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
SP = REPO / "third_party" / "SAE-based-representation-engineering"
PM = REPO / "third_party" / "ParamMute"
sys.path.insert(0, str(SP))
# spare/utils.py: PROJ_DIR = Path(os.environ.get("PROJ_DIR", "./")), so every
# cache_data path resolves against the caller's cwd. Running from anywhere but
# the SpARE checkout silently misses the shipped weights and falls through to
# the recompute branch, which then dies on a file that was never shipped.
os.environ.setdefault("PROJ_DIR", str(SP))
sys.path.insert(0, str(REPO / "scripts"))

from transfer_stats import (                       # noqa: E402
    adversarial_text, min_detectable_change, wilson)

CHUNK_WORDS = 20


def normalize_answer(s: str) -> str:
    """Identical to ParamMute's and CK-PLUG's `normalize_answer`."""
    s = s.lower()
    s = "".join(ch for ch in s if ch not in set(string.punctuation))
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    return " ".join(s.split())


def acc_score(pred: str, gold) -> float:
    """Substring containment after normalisation - the shared rubric."""
    golds = gold if isinstance(gold, list) else [gold]
    return float(any(normalize_answer(str(g)) in normalize_answer(pred)
                     for g in golds if str(g).strip()))


def poison_context(context: str, passage: str, frac: float) -> str:
    if frac <= 0:
        return context
    words = context.split()
    chunks = [" ".join(words[i:i + CHUNK_WORDS])
              for i in range(0, len(words), CHUNK_WORDS)]
    for i in range(min(max(1, round(len(chunks) * frac)), len(chunks))):
        chunks[i] = passage
    return " ".join(chunks)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--model", type=str, default="NousResearch/Meta-Llama-3-8B")
    ap.add_argument("--data", type=str, default="NaturalQuestionsShort_kc.jsonl")
    ap.add_argument("--clean_only", action="store_true")
    ap.add_argument("--out", type=str,
                    default="data/registries/spare_vs_corpus_poisoning.json")
    args = ap.parse_args()

    import demo  # noqa: E402  (their code; heavy import, so deferred)

    # SpARE's `init_frozen_language_model` defaults to flash_attention_2, and
    # demo.py takes the default. flash-attn is a build-from-source package;
    # the attention kernel is a speed choice, not part of the method, and
    # SDPA computes the same attention. The function already exposes the knob
    # (`attn_imp=`), so this just supplies it rather than changing behaviour.
    _orig_init = demo.init_frozen_language_model
    demo.init_frozen_language_model = (
        lambda model_path, attn_imp="sdpa": _orig_init(model_path, attn_imp))

    passage = adversarial_text()
    path = PM / "data" / "CoConflictQA" / "test" / args.data
    data = [json.loads(l) for l in path.read_text().splitlines()][: args.n]

    print("loading SpARE (SAEs + cached activations) ...", flush=True)
    (model, tokenizer, model_name, re_odqa_dataset,
     use_context_patch, use_parameter_patch, inspect_module) = demo.get_llama_spare(args.model)

    conditions = [("clean (native incidental conflict)", 0.0)] if args.clean_only else [
        ("clean (native incidental conflict)", 0.0),
        ("corpus poisoning, 10% of context", 0.1),
        ("corpus poisoning, 50% of context", 0.5),
        ("corpus poisoning, 100% of context", 1.0)]

    results = []
    for name, frac in conditions:
        tallies = {arm: {"ctx": 0, "pm": 0} for arm in
                   ("steer_to_use_context", "steer_to_use_parameter")}
        for d in data:
            ex = {"context": poison_context(d["context"], passage, frac)[:2048],
                  "question": d["question"][:128]}
            out = demo.generate_two_answers(
                ex, model, tokenizer, model_name, 42, re_odqa_dataset, 3,
                use_context_patch, use_parameter_patch, inspect_module)
            for arm in tallies:
                pred = str(out.get(arm, ""))
                tallies[arm]["ctx"] += acc_score(pred, d["answers"])
                tallies[arm]["pm"] += acc_score(pred, d["parametric_answer"])
        n = len(data)
        print(f"\n{name}", flush=True)
        for arm, t in tallies.items():
            ctx, pm = t["ctx"] / n * 100, t["pm"] / n * 100
            lo, hi = wilson(int(t["ctx"]), n)
            r = {"condition": name, "frac": frac, "arm": arm, "n": n,
                 "ctx_acc": round(ctx, 2), "pm_acc": round(pm, 2),
                 "mr": round(pm / (ctx + pm + 1e-10) * 100, 2),
                 "ci_low": round(lo * 100, 1), "ci_high": round(hi * 100, 1)}
            results.append(r)
            print(f"  {arm:<24} ctx_acc {ctx:5.1f}%  pm_acc {pm:5.1f}%  mr {r['mr']:5.1f}%",
                  flush=True)

    out = {"generated": "2026-10-02", "dataset": args.data, "n": len(data),
           "model": args.model, "scorer": "shared normalize+substring rubric",
           "mdr_pp_at_n": round(min_detectable_change(len(data), 0.5), 1),
           "results": results}
    (REPO / args.out).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {args.out}  (mdr {out['mdr_pp_at_n']} pp)")


if __name__ == "__main__":
    main()

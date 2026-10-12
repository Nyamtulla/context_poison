"""ACD (incidental-validated) vs corpus poisoning (deliberate).

Eighth defense in the RAG x silent-corruption cell, and the one whose stated
mechanism is aimed squarely at this threat even though it was never tested
against an attacker. ACD decodes from the NO-CONTEXT distribution and pulls it
toward the with-context distribution by a weight computed from entropy:

    d_alpha   = ent / (ent_pos + ent)
    scores    = scores + d_alpha * (scores_pos - scores)

where `ent` is the Shannon entropy of the no-context next-token distribution
and `ent_pos` that of the with-context one. When the retrieved passage REDUCES
uncertainty, d_alpha is large and the context wins. When the passage RAISES
uncertainty, d_alpha shrinks and the model keeps its parametric answer.

That is the opposite reflex from every other context-reliance defense in this
cell, which trust the context more when it disagrees with memory. A corpus
poisoning passage is optimised junk, so it should raise contextual entropy, so
ACD should discount it automatically.

Prediction, committed before the run:

  * `acd` should DEGRADE LESS than `rag` as the poison fraction grows, because
    the attack raises ent_pos and the adaptive weight discounts it.
  * But DyPRAG taught us what that is worth on its own. "Falls back to
    parametric" is also what a defense that simply ignores the document looks
    like, and the two are indistinguishable on an accuracy curve. So
    `closedbook` is in from the start, and the claim only survives if `acd`
    sits measurably ABOVE closedbook on clean context - i.e. it still reads a
    good passage - while staying flat under attack.
  * If `acd` collapses to closedbook at every dose, it is DyPRAG again:
    robustness by not reading.

Arms, all three produced by ACD's own `generate_contrast`:
    rag         mode='naive', input = with-context prompt     (defense off)
    closedbook  mode='naive', input = no-context prompt       (control)
    acd         mode='acd',   input = no-context, pos = with-context

Reused unchanged: their `LMWrapper.generate_contrast` (a vendored copy of
transformers' sampling loop carrying the ACD rule), their tokenizer setup
(`<PAD>` added, left padding, embeddings resized), their `GenerationConfig`,
and their prompt format - 5-shot, `Context: ...\nQuestion: ...\nAnswer: ...`,
with the no-context arm getting a no-context few-shot block exactly as their
`_get_few_shots` builds it. Scored with the cell's rubric
(`eval_NQ.get_score`), the same one used for every other defense here.

Deviations, both documented rather than silent:
  * Their configs default to BASE models (Llama-2-7b-hf, Meta-Llama-3-8B). We
    run Llama-3-8B-Instruct with their base-model prompt format, because
    holding the model fixed across the cell matters more than matching their
    default checkpoint - `model_dependence.md` shows the model is the dominant
    variable in this matrix.
  * Few-shot demonstrations are drawn from items outside the evaluation slice
    and are never poisoned. Only the item under test is attacked.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
CKP = REPO / "third_party" / "CK-PLUG"
PM = REPO / "third_party" / "ParamMute"
ACD = REPO / "third_party" / "ACD"
sys.path.insert(0, str(CKP))
sys.path.insert(0, str(ACD))
sys.path.insert(0, str(REPO / "scripts"))

if "vllm" not in sys.modules:                      # dead import inside eval_NQ
    import types
    _stub = types.ModuleType("vllm")
    _stub.LLM = _stub.SamplingParams = None
    sys.modules["vllm"] = _stub

import torch                                       # noqa: E402
from transformers import AutoTokenizer, GenerationConfig   # noqa: E402

import eval_NQ as CKEVAL                           # noqa: E402  (CK-PLUG's code)
from generation.gen_wrapper import LMWrapper       # noqa: E402  (their code)
from transfer_stats import (                       # noqa: E402
    adversarial_text, min_detectable_change, wilson)

CHUNK_WORDS = 20
BASE = "NousResearch/Meta-Llama-3-8B-Instruct"
ARMS = ("rag", "closedbook", "acd")


def poison_context(context: str, passage: str, frac: float) -> str:
    """Identical treatment to every other defense in this cell."""
    if frac <= 0:
        return context
    words = context.split()
    chunks = [" ".join(words[i:i + CHUNK_WORDS])
              for i in range(0, len(words), CHUNK_WORDS)]
    for i in range(min(max(1, round(len(chunks) * frac)), len(chunks))):
        chunks[i] = passage
    return " ".join(chunks)


def build_fewshots(shots):
    """Their `_get_few_shots`, reproduced: '\\n'.join with the same prefixes."""
    def block(with_context):
        prefix = "Answer the following questions:\n\n"
        out = [prefix]
        for s in shots:
            ctx = s["context"]
            ctx = ctx + "..." if ctx[-1] != "." else ctx      # their line
            ans = s["answers"][0] if isinstance(s["answers"], list) else s["answers"]
            if with_context:
                out.append(f"Context: {ctx}\nQuestion: {s['question']}\nAnswer: {ans}\n")
            else:
                out.append(f"Question: {s['question']}\nAnswer: {ans}\n")
        joined = "\n".join(out)
        return joined if joined[-1] == "\n" else joined + "\n"
    return {"with_context": block(True), "without_context": block(False)}


def make_prompt(fewshots, question, context=None):
    """Their `get_dataset_for_generation`, base-model branch."""
    body = (f"Context: {context}\nQuestion: {question}\n" if context is not None
            else f"Question: {question}\n")
    newline = "\n" if fewshots[-2:] != "\n\n" else ""
    return fewshots + newline + body


def generate(model, tokenizer, gen_cfg, prompts, prompts_pos, mode, batch_size):
    outs = []
    for i in range(0, len(prompts), batch_size):
        b = prompts[i:i + batch_size]
        ids = tokenizer(b, return_tensors="pt", padding=True,
                        truncation=False).to(model.device).input_ids
        ids_pos = None
        if prompts_pos is not None:
            bp = prompts_pos[i:i + batch_size]
            ids_pos = tokenizer(bp, return_tensors="pt", padding=True,
                                truncation=False).to(model.device).input_ids
        with torch.no_grad():
            out = model.generate_contrast(ids, ids_pos, num_beams=1,
                                          do_sample=False,
                                          generation_config=gen_cfg, mode=mode)
        out = [out[j][len(ids[j]):] for j in range(ids.shape[0])]
        outs += tokenizer.batch_decode(out, skip_special_tokens=True)
    return [o.strip() for o in outs]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--n_shots", type=int, default=5)
    ap.add_argument("--batch_size", type=int, default=8)
    ap.add_argument("--max_new_tokens", type=int, default=32)
    ap.add_argument("--model", type=str, default=BASE)
    ap.add_argument("--data", type=str, default="NaturalQuestionsShort_kc.jsonl")
    ap.add_argument("--max_context_chars", type=int, default=2000,
                    help="same frozen item set as the COIECD and DyPRAG runs")
    ap.add_argument("--fracs", type=float, nargs="+", default=[0.0, 0.1, 0.5, 1.0])
    ap.add_argument("--dump", default=None)
    ap.add_argument("--out", type=str,
                    default="data/registries/acd_vs_corpus_poisoning.json")
    args = ap.parse_args()

    adv = adversarial_text()
    rows = [json.loads(l) for l in
            (PM / "data" / "CoConflictQA" / "test" / args.data).read_text().splitlines()]
    kept = [r for r in rows if len(r["context"]) <= args.max_context_chars]
    data = kept[: args.n]
    shots = kept[args.n: args.n + args.n_shots]      # never in the eval slice
    assert len(shots) == args.n_shots, "not enough held-out items for few-shots"
    fs = build_fewshots(shots)
    print(f"{len(rows)} items, using {len(data)}, {len(shots)} few-shots held out",
          flush=True)

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    tokenizer.add_special_tokens({"pad_token": "<PAD>"})   # their line
    tokenizer.padding_side = "left"                        # their line
    model = LMWrapper(model_name_or_path=args.model, cache_dir=None,
                      device_map="auto", max_memory={0: "45GiB"},
                      offload_folder=None)
    model.gen_model.resize_token_embeddings(len(tokenizer))   # their line
    model.gen_model.config.pad_token = tokenizer.pad_token
    gen_cfg = GenerationConfig(max_new_tokens=args.max_new_tokens,
                               pad_token_id=tokenizer.pad_token_id)
    print(f"  VRAM after load: {torch.cuda.memory_allocated()/1e9:.1f} GB", flush=True)

    golds = [d["answers"] for d in data]
    origs = [d["parametric_answer"] for d in data]
    n = len(data)
    # the no-context arm never sees the passage, so it is identical at every
    # dose; computed once and reused, and its invariance is the leak check
    p_noctx = [make_prompt(fs["without_context"], d["question"]) for d in data]
    closed = generate(model, tokenizer, gen_cfg, p_noctx, None, "naive", args.batch_size)

    def score(preds):
        em, ps = CKEVAL.get_score(preds, golds)
        _, po = CKEVAL.get_score(preds, origs)
        lo, hi = wilson(round(ps / 100 * n), n)
        return {"n": n, "ctx_acc": round(ps, 2), "pm_acc": round(po, 2),
                "mr": round(po / (ps + po + 1e-10) * 100, 2), "em": round(em, 2),
                "ci_low": round(lo * 100, 1), "ci_high": round(hi * 100, 1)}

    dump, results = ([] if args.dump else None), []
    for frac in args.fracs:
        name = ("clean (native incidental conflict)" if frac <= 0
                else f"corpus poisoning, {int(frac*100)}% of context")
        p_ctx = [make_prompt(fs["with_context"], d["question"],
                             poison_context(d["context"], adv, frac)) for d in data]
        rag = generate(model, tokenizer, gen_cfg, p_ctx, None, "naive", args.batch_size)
        acd = generate(model, tokenizer, gen_cfg, p_noctx, p_ctx, "acd", args.batch_size)
        got = {"rag": score(rag), "closedbook": score(closed), "acd": score(acd)}
        print(f"\n  {name}", flush=True)
        for arm in ARMS:
            r = got[arm]; r.update(condition=name, frac=frac, arm=arm)
            results.append(r)
            print(f"    {arm:<11} ctx_acc {r['ctx_acc']:5.1f}%  pm_acc {r['pm_acc']:5.1f}%"
                  f"  mr {r['mr']:5.1f}%  em {r['em']:5.1f}%", flush=True)
        if dump is not None:
            for i, d in enumerate(data):
                dump.append({"frac": frac, "question": d["question"],
                             "gold": d["answers"], "parametric": d["parametric_answer"],
                             "rag": rag[i], "closedbook": closed[i], "acd": acd[i]})

    if dump is not None:
        (REPO / args.dump).write_text(json.dumps(dump, indent=1))
        print(f"dumped {len(dump)} generations -> {args.dump}", flush=True)
    out = {"generated": "2026-10-12", "dataset": args.data, "n": n,
           "model": args.model, "defense": "acd", "n_shots": args.n_shots,
           "max_new_tokens": args.max_new_tokens,
           "mdr_pp_at_n": round(min_detectable_change(n, 0.5), 1),
           "prediction": ("acd degrades less than rag because the attack raises "
                          "contextual entropy and d_alpha discounts it; the claim "
                          "only survives if acd sits above closedbook on clean "
                          "context, otherwise it is DyPRAG again"),
           "results": results}
    (REPO / args.out).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {args.out}  (mdr {out['mdr_pp_at_n']} pp)")


if __name__ == "__main__":
    main()

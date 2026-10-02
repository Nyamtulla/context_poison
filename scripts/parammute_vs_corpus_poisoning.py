"""ParamMute (incidental-validated) vs corpus poisoning (deliberate).

The SoK's headline test, attempt two. FaithfulRAG's control could not be made
to fire on open weights because its full method needs OpenAI JSON mode;
ParamMute has no API dependency, ships a LoRA adapter *and* a forked
transformers containing the mechanism itself, and - most useful - turns on and
off with a single number on the same weights.

**The prediction, stated before the run.** ParamMute works by suppressing the
FFN layers that carry parametric memory, forcing the model onto the retrieved
context. That is FaithfulRAG's philosophy taken further. So a context attack
should hurt it MORE, not less: the defense's whole function is to remove the
model's ability to fall back on what it knows when the context is wrong.

Their own metric measures exactly this. `get_score_with_paramatric` returns

    ctx_acc   answered from the context
    pm_acc    answered from parametric memory
    mr        pm / (pm + ctx) - the memorization ratio

ParamMute's claim is that it lowers `mr`. Under poisoning, lowering `mr` means
trusting corrupted context *more*. So the defense succeeding at its stated goal
and failing under attack are the same measurement.

Scoring is theirs, imported unchanged - normalize_answer, _acc_score,
_exact_match_score, get_score_with_paramatric - and so is the prompt builder
and the generation call. The only things this script adds are the poisoning and
the detectability gate.

Arms (both on the same prompts, same data, same decoder):
    base        Llama-3-8B-Instruct, inhibit_strength=1.0  (no suppression)
    parammute   merged adapter,      inhibit_strength=0    (the paper's setting)

Layers 21-26, taken from the authors' own training invocation in
`scripts/2_tuning/tune.log`.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import torch

REPO = pathlib.Path(__file__).resolve().parent.parent
PM = REPO / "third_party" / "ParamMute"
sys.path.insert(0, str(PM / "src" / "3_evaluate"))
sys.path.insert(0, str(REPO / "scripts"))

from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer  # noqa: E402

import eval_CoConflictQA as PMEVAL                 # noqa: E402  (their code)
from transfer_stats import (                       # noqa: E402
    adversarial_text, min_detectable_change, wilson)

INHIBIT_LAYERS = [21, 22, 23, 24, 25, 26]
CHUNK_WORDS = 20
MERGED = str(PM / "merged_parammute_llama3_8b")
BASE = "NousResearch/Meta-Llama-3-8B-Instruct"


def poison_context(context: str, passage: str, frac: float) -> str:
    """Replace the leading `frac` of the context with the adversarial passage.

    Identical treatment to the FaithfulRAG run so the two are comparable:
    chunk, overwrite the leading chunks, keep the rest. CoConflictQA contexts
    run ~110 words, so frac=1.0 means the model sees nothing but the attack.
    """
    if frac <= 0:
        return context
    words = context.split()
    chunks = [" ".join(words[i:i + CHUNK_WORDS])
              for i in range(0, len(words), CHUNK_WORDS)]
    for i in range(min(max(1, round(len(chunks) * frac)), len(chunks))):
        chunks[i] = passage
    return " ".join(chunks)


def load_model(path: str, inhibit_strength: float):
    """Their loading path verbatim: swap the architecture to the inhibit
    variant, then pass the strength and layer list into from_pretrained."""
    tok = AutoTokenizer.from_pretrained(path, trust_remote_code=True)
    tok.pad_token = tok.eos_token
    config = AutoConfig.from_pretrained(path, trust_remote_code=True)
    assert "llama" in config.architectures[0].lower(), config.architectures
    config.architectures = ["LlamaForCausalLM_w_act_inhibit"]
    model = AutoModelForCausalLM.from_pretrained(
        path, device_map="auto", low_cpu_mem_usage=True,
        torch_dtype=torch.bfloat16, config=config, trust_remote_code=True,
        inhibit_strength=inhibit_strength, inhibit_layer_list=INHIBIT_LAYERS)
    model.eval()
    return model, tok


def run_condition(model, tok, data, passage, frac, schema, max_new_tokens):
    preds, golds, pms = [], [], []
    for d in data:
        ctx = poison_context(d["context"], passage, frac)
        prompt = PMEVAL.qa_to_prompt_baseline(
            d["question"], ctx, schema=schema, tokenizer=tok,
            IS_INSTRUCTION_PROMPT=False)
        ids = tok(prompt, return_tensors="pt").input_ids.to(model.device)
        preds.append(PMEVAL.call_llama(model, tok, ids, max_new_tokens))
        golds.append(d["answers"])
        pms.append(d["parametric_answer"])
    pm_acc, acc, rouge, f1, em = PMEVAL.get_score_with_paramatric(pms, preds, golds)
    n = len(data)
    lo, hi = wilson(round(acc / 100 * n), n)
    return {"n": n, "ctx_acc": round(acc, 2), "pm_acc": round(pm_acc, 2),
            "mr": round(pm_acc / (pm_acc + acc + 1e-5) * 100, 2),
            "em": round(em, 2), "f1": round(f1, 2),
            "ci_low": round(lo * 100, 1), "ci_high": round(hi * 100, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--schema", type=str, default="base")
    ap.add_argument("--max_new_tokens", type=int, default=32)
    ap.add_argument("--data", type=str, default="NaturalQuestionsShort_kc.jsonl")
    ap.add_argument("--clean_only", action="store_true")
    ap.add_argument("--out", type=str,
                    default="data/registries/parammute_vs_corpus_poisoning.json")
    args = ap.parse_args()

    passage = adversarial_text()
    path = PM / "data" / "CoConflictQA" / "test" / args.data
    data = [json.loads(l) for l in path.read_text().splitlines()][: args.n]

    conditions = [("clean (native incidental conflict)", 0.0)] if args.clean_only else [
        ("clean (native incidental conflict)", 0.0),
        ("corpus poisoning, 10% of context", 0.1),
        ("corpus poisoning, 50% of context", 0.5),
        ("corpus poisoning, 100% of context", 1.0)]

    arms = [("base", BASE, 1.0), ("parammute", MERGED, 0.0)]
    results = []
    for arm, path_, strength in arms:
        print(f"\n===== {arm}  (inhibit_strength={strength}) =====", flush=True)
        model, tok = load_model(path_, strength)
        for name, frac in conditions:
            r = run_condition(model, tok, data, passage, frac,
                              args.schema, args.max_new_tokens)
            r.update(condition=name, frac=frac, arm=arm)
            results.append(r)
            print(f"  {name:<36} ctx_acc {r['ctx_acc']:5.1f}%  "
                  f"pm_acc {r['pm_acc']:5.1f}%  mr {r['mr']:5.1f}%  "
                  f"em {r['em']:5.1f}%", flush=True)
        del model
        torch.cuda.empty_cache()

    out = {"generated": "2026-10-02", "dataset": args.data, "n": len(data),
           "schema": args.schema, "inhibit_layers": INHIBIT_LAYERS,
           "mdr_pp_at_n": round(min_detectable_change(len(data), 0.5), 1),
           "results": results}
    (REPO / args.out).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {args.out}  (mdr {out['mdr_pp_at_n']} pp)")


if __name__ == "__main__":
    main()

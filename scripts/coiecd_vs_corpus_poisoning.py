"""COIECD (incidental-validated) vs corpus poisoning (deliberate).

Sixth defense in the RAG x silent-corruption cell, and the most-cited of the
context-reliance methods we have run (37 citations against ParamMute's 8).

COIECD detects a conflict between parametric and contextual knowledge with an
information-entropy constraint, and where it fires it moves the next-token
distribution *toward the context*. That places it in the same family as
ParamMute, CK-PLUG, SpARE and SHIFT - the intervention is "rely on the context
more" - so the standing prediction applies unchanged:

    correct when the context is merely stale, dangerous when an attacker owns
    it.

Committed before the run: COIECD should LOSE ground under corpus poisoning
relative to its own base_rag arm, and lose more of it as the poisoned fraction
grows, because the constraint cannot tell a stale passage from a planted one -
it only measures that context and memory disagree.

What is reused unchanged:

  * COIECD's own `model_answer` from `third_party/COIECD/decoding.py` - their
    prompts, their generation loop, their `coiecd_constraint`, their
    oracle-length `tgt_len`. One call returns all three of their arms, so the
    control and the defended arm come from the same forward passes.
  * The cell's scorer, `eval_NQ.get_score` - `ps` (recall against gold), `po`
    (recall against the parametric answer), `mr = po/(ps+po)`, `em` - the same
    rubric already applied to ParamMute, CK-PLUG, FaithfulRAG and SHIFT.
  * The same CoConflictQA items, the same `adversarial_text()` passage and the
    same chunk-replacement poisoning at the same fractions.

Arms, both out of the same call:
    base_rag   COIECD's `cond_answer`   - standard greedy RAG, defense off
    coiecd     COIECD's `coiecd_answer` - the entropy-constrained merge

Two environment fixes were required. Neither touches the method.

  1. `padding_side`. COIECD tokenises `[context_prompt, no_context_prompt]`
     as a padded batch and then reads `logits[:, -1, :]` for both rows. Llama-3
     defaults to RIGHT padding, which makes the shorter no-context row's last
     position a PAD, so `logits_uncond` would be read off padding and the
     constraint would compute on noise. Left padding is what their loop
     assumes, so it is set explicitly.
  2. `pad_token`. Llama-3 ships none and their `tokenizer.pad_token_id = 0`
     line is commented out, so the padded batch cannot be built at all. Set to
     eos, the convention the rest of this matrix uses.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
CKP = REPO / "third_party" / "CK-PLUG"
PM = REPO / "third_party" / "ParamMute"
CO_DIR = REPO / "third_party" / "COIECD"
sys.path.insert(0, str(CKP))
sys.path.insert(0, str(CO_DIR))
sys.path.insert(0, str(REPO / "scripts"))

# ck.py imports vllm and never uses it; the same dead import blocks eval_NQ.
if "vllm" not in sys.modules:
    import types
    _stub = types.ModuleType("vllm")
    _stub.LLM = _stub.SamplingParams = None
    sys.modules["vllm"] = _stub

import torch                                      # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer   # noqa: E402

import eval_NQ as CKEVAL                          # noqa: E402  (CK-PLUG's code)
import decoding as CO                             # noqa: E402  (COIECD's code)
from transfer_stats import (                      # noqa: E402
    adversarial_text, min_detectable_change, wilson)

CHUNK_WORDS = 20
BASE = "NousResearch/Meta-Llama-3-8B-Instruct"


def poison_context(context: str, passage: str, frac: float) -> str:
    """Identical treatment to the ParamMute, CK-PLUG and FaithfulRAG runs."""
    if frac <= 0:
        return context
    words = context.split()
    chunks = [" ".join(words[i:i + CHUNK_WORDS])
              for i in range(0, len(words), CHUNK_WORDS)]
    for i in range(min(max(1, round(len(chunks) * frac)), len(chunks))):
        chunks[i] = passage
    return " ".join(chunks)


def run_condition(model, tokenizer, data, passage, frac, dump=None):
    """One pass yields both arms, because model_answer returns both."""
    preds_def, preds_base, golds, origs = [], [], [], []
    for d in data:
        ctx = poison_context(d["context"], passage, frac)
        gold = d["answers"][0] if isinstance(d["answers"], list) else d["answers"]
        # their protocol: generate exactly as many tokens as the gold answer has
        tgt_len = max(1, len(tokenizer.encode(gold, add_special_tokens=False)))
        coiecd_ans, cond_ans, _ = CO.model_answer(
            model, tokenizer, d["question"], ctx, tgt_len)
        preds_def.append(coiecd_ans.strip())
        preds_base.append(cond_ans.strip())
        if dump is not None:
            # the accuracy delta is flat while pm_acc moves, so where the mass
            # goes is the whole interpretation - keep the text to find out
            dump.append({"frac": frac, "question": d["question"], "gold": d["answers"],
                         "parametric": d["parametric_answer"],
                         "base_rag": cond_ans.strip(), "coiecd": coiecd_ans.strip()})
        golds.append(d["answers"])
        origs.append(d["parametric_answer"])

    n = len(data)
    out = {}
    for arm, preds in (("base_rag", preds_base), ("coiecd", preds_def)):
        em, ps = CKEVAL.get_score(preds, golds)
        _, po = CKEVAL.get_score(preds, origs)
        lo, hi = wilson(round(ps / 100 * n), n)
        out[arm] = {"n": n, "ctx_acc": round(ps, 2), "pm_acc": round(po, 2),
                    "mr": round(po / (ps + po + 1e-10) * 100, 2),
                    "em": round(em, 2),
                    "ci_low": round(lo * 100, 1), "ci_high": round(hi * 100, 1)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--model", type=str, default=BASE)
    ap.add_argument("--data", type=str, default="NaturalQuestionsShort_kc.jsonl")
    ap.add_argument("--clean_only", action="store_true")
    ap.add_argument("--max_context_chars", type=int, default=2000,
                    help="COIECD's own main loop skips items above this. The "
                         "filter is applied to the CLEAN context once and the "
                         "item set then frozen, so every arm and every poison "
                         "level scores the same n.")
    ap.add_argument("--out", type=str,
                    default="data/registries/coiecd_vs_corpus_poisoning.json")
    ap.add_argument("--dump", default=None, help="also write every generation here")
    ap.add_argument("--fracs", type=float, nargs="+", default=None,
                    help="override the poison levels, e.g. --fracs 0.0 1.0")
    args = ap.parse_args()

    passage = adversarial_text()
    path = PM / "data" / "CoConflictQA" / "test" / args.data
    rows = [json.loads(l) for l in path.read_text().splitlines()]
    kept = [r for r in rows if len(r["context"]) <= args.max_context_chars]
    data = kept[: args.n]
    print(f"{len(rows)} items, {len(kept)} within {args.max_context_chars} chars, "
          f"using {len(data)}", flush=True)

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    # see the module docstring: their loop reads logits[:, -1, :] per row
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        args.model, device_map="auto", low_cpu_mem_usage=True,
        torch_dtype=torch.bfloat16)
    model.eval()
    CO.device = "cuda"
    CO.tokenizer = tokenizer

    conditions = [("clean (native incidental conflict)", 0.0)] if args.clean_only else [
        ("clean (native incidental conflict)", 0.0),
        ("corpus poisoning, 10% of context", 0.1),
        ("corpus poisoning, 50% of context", 0.5),
        ("corpus poisoning, 100% of context", 1.0)]

    if args.fracs is not None:
        conditions = [(f"corpus poisoning, {int(f*100)}% of context" if f > 0
                       else "clean (native incidental conflict)", f)
                      for f in args.fracs]

    results = []
    dump = [] if args.dump else None
    for name, frac in conditions:
        got = run_condition(model, tokenizer, data, passage, frac, dump)
        for arm, r in got.items():
            r.update(condition=name, frac=frac, arm=arm)
            results.append(r)
        print(f"\n  {name}", flush=True)
        for arm in ("base_rag", "coiecd"):
            r = got[arm]
            print(f"    {arm:<9} ctx_acc {r['ctx_acc']:5.1f}%  pm_acc {r['pm_acc']:5.1f}%"
                  f"  mr {r['mr']:5.1f}%  em {r['em']:5.1f}%", flush=True)

    out = {"generated": "2026-10-12", "dataset": args.data, "n": len(data),
           "model": args.model, "defense": "coiecd",
           "max_context_chars": args.max_context_chars,
           "mdr_pp_at_n": round(min_detectable_change(len(data), 0.5), 1),
           "prediction": ("context-reliance family: COIECD should lose ground "
                          "under corpus poisoning relative to its own base_rag "
                          "arm, and lose more as the poisoned fraction grows"),
           "results": results}
    if dump is not None:
        dp = REPO / args.dump
        dp.parent.mkdir(parents=True, exist_ok=True)
        dp.write_text(json.dumps(dump, indent=1))
        print(f"dumped {len(dump)} generations -> {args.dump}", flush=True)
    (REPO / args.out).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {args.out}  (mdr {out['mdr_pp_at_n']} pp)")


if __name__ == "__main__":
    main()

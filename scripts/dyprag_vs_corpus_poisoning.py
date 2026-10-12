"""DyPRAG (incidental-validated) vs corpus poisoning (deliberate).

Seventh defense in the RAG x silent-corruption cell, and the first one that is
not a decoding-time intervention. DyPRAG runs the retrieved passage through the
base model, takes the last hidden state, and feeds it to a trained parameter
translator that emits a rank-2 LoRA. That LoRA is injected into the MLP of
every layer, and in `dyprag` mode the passage is then REMOVED from the prompt
entirely - the knowledge is carried in weights rather than in context.

That makes this the only defense in the cell that changes what the attacker
controls. Corpus poisoning plants an optimised token sequence in the context.
DyPRAG never lets those tokens reach the generation prompt; it compresses the
whole passage to one hidden-state vector and then to a rank-2 update.

Prediction, committed before the run:

  * `dyprag` should DEGRADE LESS than `rag` as the poison fraction grows. The
    attack's passage is optimised in token space, and almost none of that
    precision can survive compression to a single 4096-d vector and a rank-2
    LoRA. Blunting an attack by destroying its channel is a different mechanism
    from every other defense measured here.
  * `dyprag` should be WORSE THAN `rag` ON CLEAN CONTEXT, for the same reason -
    the same compression that destroys the attack also destroys the gold
    answer, which the model can no longer read off the page.
  * So the test is the SLOPE, not the level. Compare each arm against its own
    clean baseline. An arm that starts low and stays flat is doing something a
    high-starting arm that collapses is not.
  * `dyprag_combine` keeps the passage in the prompt, so it re-exposes the
    attack surface and should track `rag`.

Arms, all on the same items and the same poisoned context:
    rag              passage in the prompt, no LoRA            (defense off)
    dyprag           passage -> LoRA, prompt has NO passage    (defense on)
    dyprag_combine   passage in the prompt AND LoRA injected   (their hybrid)

Reused unchanged: DyPRAG's own `get_model` (their custom LlamaForCausalLM,
whose MLP reads the injected `delta`), `get_prompt`, `predict`,
`delta_inject`/`delta_remove`, their `ParameterTranslator`, and their released
llama3-8b projector checkpoint. Scored with the cell's existing rubric
(`eval_NQ.get_score`), the same one applied to ParamMute, CK-PLUG, FaithfulRAG,
SHIFT and COIECD.

Environment fixes, none touching the method:
  * `root_dir_path.ROOT_DIR` is hardcoded to the authors' machine
    ("/netdisk/tanyuqiao/PRAG"). Set to the local checkout before their modules
    use it.
  * `get_model_path` has an empty `path` placeholder, but falls through to
    returning the name unchanged for anything not in its three-way list, so the
    HF repo id is passed straight in.
  * requirement.sh pins torch==2.1.0; the installed torch is newer. transformers
    and peft are pinned exactly as specified (4.49.0 / 0.13.2).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
CKP = REPO / "third_party" / "CK-PLUG"
PM = REPO / "third_party" / "ParamMute"
DY = REPO / "third_party" / "DyPRAG"
sys.path.insert(0, str(CKP))
sys.path.insert(0, str(DY / "src"))
sys.path.insert(0, str(REPO / "scripts"))

if "vllm" not in sys.modules:                      # dead import inside eval_NQ
    import types
    _stub = types.ModuleType("vllm")
    _stub.LLM = _stub.SamplingParams = None
    sys.modules["vllm"] = _stub

import root_dir_path                               # noqa: E402  (their code)
root_dir_path.ROOT_DIR = str(DY)                   # authors' absolute path

import torch                                       # noqa: E402
from peft import LoraConfig, TaskType, get_peft_model   # noqa: E402

import torch.nn as nn                             # noqa: E402
import eval_NQ as CKEVAL                           # noqa: E402  (CK-PLUG's code)
from projector import ParameterTranslator          # noqa: E402  (their code)
from models.modeling_llama import LlamaMLP         # noqa: E402  (their code)
from utils import (get_model, predict,             # noqa: E402  (their code)
                   get_attributes)
from transfer_stats import (                       # noqa: E402
    adversarial_text, min_detectable_change, wilson)

# ---------------------------------------------------------------------------
# Memory: apply the LoRA factored instead of materialising it.
#
# Their delta_inject computes `delta = lora_B @ lora_A` and stores the DENSE
# result on each module, then their LlamaMLP does `x @ delta.T`. For Llama-3-8B
# that dense matrix is 4096 x 14336 fp32 = 235 MB, for each of 3 modules in
# each of 32 layers - about 22 GB on top of a 32 GB fp32 model, which does not
# fit on a 48 GB card and OOMs inside delta_inject.
#
# x @ (B @ A).T == (x @ A.T) @ B.T, so the dense matrix never has to exist.
# This keeps their fp32 weights, their projector output and their arithmetic;
# the only difference is the association order of a floating-point product.
# ---------------------------------------------------------------------------
# NB: the attribute cannot be called lora_A/lora_B. PEFT's own LoraLayer
# already defines those as ModuleDicts on every wrapped Linear, so hasattr()
# is true before anything is injected and the forward would try to matmul a
# ModuleDict. That collision is why their code called the attribute "delta".
def _mlp_forward_factored(self, x):
    gate_output = self.gate_proj(x)
    if hasattr(self.gate_proj, "_dyA"):
        gate_output += (x @ self.gate_proj._dyA.T) @ self.gate_proj._dyB.T
    gate_activated = self.act_fn(gate_output)
    up_output = self.up_proj(x)
    if hasattr(self.up_proj, "_dyA"):
        up_output += (x @ self.up_proj._dyA.T) @ self.up_proj._dyB.T
    gate_up_product = gate_activated * up_output
    down_proj = self.down_proj(gate_up_product)
    if hasattr(self.down_proj, "_dyA"):
        down_proj += (gate_up_product @ self.down_proj._dyA.T) @ self.down_proj._dyB.T
    return down_proj


LlamaMLP.forward = _mlp_forward_factored


def delta_inject_factored(model, adapter_weights):
    """Their delta_inject, without forming B @ A."""
    modules = set(".".join(k.split(".")[:-2]) for k in adapter_weights.keys())
    for module in modules:
        m = get_attributes(model, module)
        a = adapter_weights[module + ".lora_A.weight"]
        b = adapter_weights[module + ".lora_B.weight"]
        setattr(m, "_dyA", a.to(torch.float32))
        setattr(m, "_dyB", b.to(torch.float32))


def delta_remove_factored(model, adapter_weights):
    modules = set(".".join(k.split(".")[:-2]) for k in adapter_weights.keys())
    for module in modules:
        m = get_attributes(model, module)
        delattr(m, "_dyA")
        delattr(m, "_dyB")


CHUNK_WORDS = 20
BASE = "NousResearch/Meta-Llama-3-8B-Instruct"
PROJECTOR = "projector_dl/llama3-8b-p32-1ep-main-2400sample.pt"
# `closedbook` is the control the channel probe showed this run needs: no
# passage in the prompt AND no LoRA. If `dyprag` matches it, the parametric
# channel contributes nothing and the flat slope under poisoning is just the
# model ignoring a document it never received. Its score must also be constant
# across poison levels - it never sees the context - which doubles as a check
# that the harness is not leaking the passage into the prompt.
ARMS = ("rag", "closedbook", "dyprag", "dyprag_combine")


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


def deltas_for(model, tokenizer, projector, passage):
    """Their own passage -> LoRA path, one passage per item as the cell gives it."""
    tokens = tokenizer(passage, padding=True, truncation=True,
                       return_tensors="pt", max_length=3000).to(model.device)
    with torch.no_grad():
        out = model(tokens.input_ids, output_hidden_states=True)
        embeds = out.hidden_states[-1][:, -1, :]
        return projector(embeds)


def run_condition(model, tokenizer, projector, gen_cfg, data, passage, frac,
                  max_new_tokens, dump=None):
    preds = {a: [] for a in ARMS}
    golds, origs = [], []
    for d in data:
        ctx = poison_context(d["context"], passage, frac)
        q = d["question"]
        deltas = deltas_for(model, tokenizer, projector, ctx)

        # defense off: the passage goes in the prompt, no weights touched
        preds["rag"].append(predict(model, tokenizer, gen_cfg, q,
                                    with_cot=False, passages=[ctx]).strip())
        # neither context nor parameters: what the model knows unaided
        preds["closedbook"].append(predict(model, tokenizer, gen_cfg, q,
                                           with_cot=False, passages=None).strip())
        delta_inject_factored(model, deltas)
        # defense on: the passage is gone from the prompt, it is in the weights
        preds["dyprag"].append(predict(model, tokenizer, gen_cfg, q,
                                       with_cot=False, passages=None).strip())
        # their hybrid: both
        preds["dyprag_combine"].append(predict(model, tokenizer, gen_cfg, q,
                                               with_cot=False, passages=[ctx]).strip())
        delta_remove_factored(model, deltas)
        del deltas
        torch.cuda.empty_cache()

        golds.append(d["answers"])
        origs.append(d["parametric_answer"])
        if dump is not None:
            dump.append({"frac": frac, "question": q, "gold": d["answers"],
                         "parametric": d["parametric_answer"],
                         **{a: preds[a][-1] for a in ARMS}})

    n = len(data)
    out = {}
    for arm in ARMS:
        em, ps = CKEVAL.get_score(preds[arm], golds)
        _, po = CKEVAL.get_score(preds[arm], origs)
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
    ap.add_argument("--projector", type=str, default=PROJECTOR)
    ap.add_argument("--lora_rank", type=int, default=2)
    ap.add_argument("--lora_alpha", type=int, default=32)
    ap.add_argument("--projector_p", type=int, default=32)
    ap.add_argument("--max_new_tokens", type=int, default=32)
    ap.add_argument("--data", type=str, default="NaturalQuestionsShort_kc.jsonl")
    ap.add_argument("--max_context_chars", type=int, default=2000,
                    help="same frozen item set as the COIECD run, so the two "
                         "defenses are scored on identical items")
    ap.add_argument("--fracs", type=float, nargs="+", default=[0.0, 0.1, 0.5, 1.0])
    ap.add_argument("--dump", default=None)
    ap.add_argument("--out", type=str,
                    default="data/registries/dyprag_vs_corpus_poisoning.json")
    args = ap.parse_args()

    adv = adversarial_text()
    rows = [json.loads(l) for l in
            (PM / "data" / "CoConflictQA" / "test" / args.data).read_text().splitlines()]
    data = [r for r in rows if len(r["context"]) <= args.max_context_chars][: args.n]
    print(f"{len(rows)} items, using {len(data)}", flush=True)

    model, tokenizer, gen_cfg = get_model(args.model, max_new_tokens=args.max_new_tokens)
    tokenizer.pad_token = tokenizer.eos_token
    model = get_peft_model(model, LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        target_modules=["down_proj", "gate_proj", "up_proj"],
        inference_mode=False, r=args.lora_rank, lora_alpha=args.lora_alpha,
        lora_dropout=0))

    projector = ParameterTranslator(
        ["down_proj", "up_proj", "gate_proj"],
        list(range(model.config.num_hidden_layers)),
        model.config.hidden_size, model.config.intermediate_size,
        args.lora_rank, args.projector_p).to(model.device)
    ck = torch.load(DY / args.projector, map_location=model.device, weights_only=False)
    projector.load_state_dict(ck["model_state_dict"])
    projector.eval()
    print(f"projector loaded: {args.projector}", flush=True)
    print(f"  VRAM after load: {torch.cuda.memory_allocated()/1e9:.1f} GB", flush=True)

    dump = [] if args.dump else None
    results = []
    for frac in args.fracs:
        name = ("clean (native incidental conflict)" if frac <= 0
                else f"corpus poisoning, {int(frac*100)}% of context")
        got = run_condition(model, tokenizer, projector, gen_cfg, data, adv,
                            frac, args.max_new_tokens, dump)
        print(f"\n  {name}", flush=True)
        for arm in ARMS:
            r = got[arm]
            r.update(condition=name, frac=frac, arm=arm)
            results.append(r)
            print(f"    {arm:<15} ctx_acc {r['ctx_acc']:5.1f}%  pm_acc {r['pm_acc']:5.1f}%"
                  f"  mr {r['mr']:5.1f}%  em {r['em']:5.1f}%", flush=True)

    if dump is not None:
        (REPO / args.dump).write_text(json.dumps(dump, indent=1))
        print(f"dumped {len(dump)} generations -> {args.dump}", flush=True)
    out = {"generated": "2026-10-12", "dataset": args.data, "n": len(data),
           "model": args.model, "defense": "dyprag", "projector": args.projector,
           "lora_rank": args.lora_rank, "projector_p": args.projector_p,
           "max_new_tokens": args.max_new_tokens,
           "mdr_pp_at_n": round(min_detectable_change(len(data), 0.5), 1),
           "prediction": ("dyprag degrades LESS than rag as poison grows "
                          "(the attack's token-space precision cannot survive "
                          "compression to a rank-2 LoRA) but starts LOWER on "
                          "clean context; compare slopes, not levels"),
           "results": results}
    (REPO / args.out).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {args.out}  (mdr {out['mdr_pp_at_n']} pp)")


if __name__ == "__main__":
    main()

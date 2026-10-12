"""Is DyPRAG's parametric channel carrying anything?

If the `dyprag` arm scores the same on clean and poisoned context, there are
two incompatible readings:

  A. The defense works - the attack is a token-space object and cannot survive
     compression to one hidden-state vector and a rank-2 LoRA.
  B. The channel is inert - the injected update is too small to change the
     model's output at all, so it answers from memory either way and the flat
     slope means nothing.

Both produce an identical accuracy table. They are separable by measurement:

  1. How large is the injected contribution relative to the MLP output it is
     added to? If ||delta_out|| / ||mlp_out|| is ~1e-6, reading B is right.
  2. Does the delta even depend on the passage? Compare the parameters
     produced from a clean passage against those from a fully poisoned one.
     If they are nearly identical, the projector is not reading the document.
  3. Do the generations differ? If injecting changes no token, the channel
     carries nothing regardless of what the norms say.
"""
from __future__ import annotations

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
PM = REPO / "third_party" / "ParamMute"
DY = REPO / "third_party" / "DyPRAG"
sys.path.insert(0, str(DY / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import root_dir_path                               # noqa: E402
root_dir_path.ROOT_DIR = str(DY)

import torch                                       # noqa: E402
from peft import LoraConfig, TaskType, get_peft_model   # noqa: E402

from projector import ParameterTranslator          # noqa: E402
from utils import get_model, predict, get_attributes    # noqa: E402
from transfer_stats import adversarial_text        # noqa: E402
from dyprag_vs_corpus_poisoning import (           # noqa: E402
    poison_context, deltas_for, delta_inject_factored, delta_remove_factored,
    BASE, PROJECTOR)

N_ITEMS = 6


def main():
    adv = adversarial_text()
    rows = [json.loads(l) for l in
            (PM / "data" / "CoConflictQA" / "test" /
             "NaturalQuestionsShort_kc.jsonl").read_text().splitlines()]
    data = [r for r in rows if len(r["context"]) <= 2000][:N_ITEMS]

    model, tokenizer, gen_cfg = get_model(BASE, max_new_tokens=32)
    tokenizer.pad_token = tokenizer.eos_token
    model = get_peft_model(model, LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        target_modules=["down_proj", "gate_proj", "up_proj"],
        inference_mode=False, r=2, lora_alpha=32, lora_dropout=0))
    projector = ParameterTranslator(
        ["down_proj", "up_proj", "gate_proj"],
        list(range(model.config.num_hidden_layers)),
        model.config.hidden_size, model.config.intermediate_size,
        2, 32).to(model.device)
    projector.load_state_dict(torch.load(
        DY / PROJECTOR, map_location=model.device,
        weights_only=False)["model_state_dict"])
    projector.eval()

    # ---- 2. does the delta depend on the passage at all? ----
    print("\n=== delta sensitivity to the passage ===", flush=True)
    key = "base_model.model.model.layers.15.mlp.down_proj"
    for d in data[:3]:
        clean = deltas_for(model, tokenizer, projector, d["context"])
        pois = deltas_for(model, tokenizer, projector,
                          poison_context(d["context"], adv, 1.0))
        a_c, b_c = clean[key + ".lora_A.weight"], clean[key + ".lora_B.weight"]
        a_p, b_p = pois[key + ".lora_A.weight"], pois[key + ".lora_B.weight"]
        cos = torch.nn.functional.cosine_similarity(
            (b_c @ a_c).flatten().unsqueeze(0),
            (b_p @ a_p).flatten().unsqueeze(0)).item()
        rel = ((b_p @ a_p) - (b_c @ a_c)).norm().item() / ((b_c @ a_c).norm().item() + 1e-12)
        print(f"  layer15.down_proj  cos(clean,poisoned)={cos:+.4f}   "
              f"relative change={rel:.3e}", flush=True)
        del clean, pois
        torch.cuda.empty_cache()

    # ---- 1. how big is the injected contribution vs the MLP output? ----
    print("\n=== injected contribution vs MLP output ===", flush=True)
    d = data[0]
    ctx = poison_context(d["context"], adv, 1.0)
    deltas = deltas_for(model, tokenizer, projector, ctx)
    probe = {}

    def hook(name):
        def f(mod, inp, out):
            x = inp[0]
            if hasattr(mod, "_dyA"):
                contrib = (x @ mod._dyA.T) @ mod._dyB.T
                probe[name] = (out.norm().item(), contrib.norm().item())
        return f

    handles = []
    for li in (0, 15, 31):
        m = get_attributes(model, f"base_model.model.model.layers.{li}.mlp.down_proj")
        handles.append(m.register_forward_hook(hook(f"layer{li}.down_proj")))
    delta_inject_factored(model, deltas)
    _ = predict(model, tokenizer, gen_cfg, d["question"], with_cot=False, passages=None)
    for h in handles:
        h.remove()
    for k, (o, c) in sorted(probe.items()):
        print(f"  {k:<22} ||mlp_out||={o:10.2f}   ||injected||={c:10.3e}   "
              f"ratio={c/(o+1e-12):.3e}", flush=True)

    # ---- 3. does injecting change the generated text? ----
    print("\n=== does injection change the output? ===", flush=True)
    delta_remove_factored(model, deltas)
    same = 0
    for d in data:
        ctx_p = poison_context(d["context"], adv, 1.0)
        dl_clean = deltas_for(model, tokenizer, projector, d["context"])
        dl_pois = deltas_for(model, tokenizer, projector, ctx_p)
        off = predict(model, tokenizer, gen_cfg, d["question"],
                      with_cot=False, passages=None).strip()
        delta_inject_factored(model, dl_clean)
        on_clean = predict(model, tokenizer, gen_cfg, d["question"],
                           with_cot=False, passages=None).strip()
        delta_remove_factored(model, dl_clean)
        delta_inject_factored(model, dl_pois)
        on_pois = predict(model, tokenizer, gen_cfg, d["question"],
                          with_cot=False, passages=None).strip()
        delta_remove_factored(model, dl_pois)
        flag = "SAME" if (off == on_clean == on_pois) else "differs"
        same += (off == on_clean == on_pois)
        print(f"  [{flag}] {d['question'][:52]}", flush=True)
        if flag == "differs":
            print(f"      no-LoRA     : {off[:80]!r}")
            print(f"      LoRA(clean) : {on_clean[:80]!r}")
            print(f"      LoRA(poison): {on_pois[:80]!r}")
        del dl_clean, dl_pois
        torch.cuda.empty_cache()
    print(f"\n  identical across all three settings on {same}/{len(data)} items", flush=True)


if __name__ == "__main__":
    main()

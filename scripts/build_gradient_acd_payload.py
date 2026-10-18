"""A gradient attack on ACD: GCG over token ids against the same objective.

`build_adaptive_acd_payload.py` chose among five hand-written sentence forms
and took `d_alpha` from 0.525 to 0.653 of a possible 1.0. Most of the headroom
survived. This is the proper version of that attack: a coordinate-descent
search over token ids, in the style of GCG, against the one quantity ACD's rule
exposes.

    d_alpha = ent / (ent_pos + ent)
    scores  = scores + d_alpha * (scores_pos - scores)

`ent` belongs to the question. `ent_pos` belongs to the context the attacker
owns. Minimise `ent_pos` and `d_alpha` goes to 1, at which point the update is
the identity on `scores_pos` and ACD is undefended RAG. That ceiling is derived
in `gradient_acd_prediction.md`, committed before this file existed.

**Nested on purpose.** The optimised suffix is appended to the passage
best-of-K already chose, the base assertion is never touched, and the suffix
starts as `!` repeated. So the asserted answer is fixed across every candidate
exactly as it was in the best-of-K run, and any movement past 0.653 is the
gradient's.

**Three restrictions, each of which weakens the attack.** They are here so the
result is a lower bound rather than an artefact:

  * Candidate tokens are restricted to space-leading printable ASCII. A suffix
    that does not survive a decode/re-encode round trip is not a passage an
    attacker can put in a corpus. We verify the round trip per item and report
    how often it is exact.
  * The *search* objective is teacher-forced entropy on the distractor answer,
    one forward pass. The *reported* objective is the free-running four-step
    measure `build_adaptive_acd_payload.entropy_of_next_token` computes, run
    again on the final string. A bad surrogate can mislead the search; it
    cannot move the number we report.
  * A gradient passage is kept only if it beats the best-of-K passage on that
    reported measure. Items where it does not keep the best-of-K passage, and
    the share is reported.

Out: `NaturalQuestionsShort_kc_gradient.jsonl`, the adaptive file plus
`gradient_evidencde` and the per-item entropy record.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import sys
import time

import torch
import torch.nn.functional as F

REPO = pathlib.Path(__file__).resolve().parent.parent
PM = REPO / "third_party" / "ParamMute"
sys.path.insert(0, str(REPO / "scripts"))

from transformers import AutoModelForCausalLM, AutoTokenizer, DynamicCache  # noqa: E402

import build_adaptive_acd_payload as BOK                                    # noqa: E402

BASE = "NousResearch/Meta-Llama-3-8B-Instruct"
DATA = "NaturalQuestionsShort_kc_adaptive.jsonl"
OUT = "NaturalQuestionsShort_kc_gradient.jsonl"
SENTINEL = "\x00SFX\x00"


def allowed_tokens(tok, device):
    """Space-leading, printable ASCII, no whitespace inside, not special.

    Restricting to space-leading tokens is what makes the round trip safe: the
    suffix is then a sequence of whole space-prefixed words, so the boundary
    between the base passage and the suffix, and between the suffix and the
    next repeat of the passage, both fall where a space already is.
    """
    special = set(tok.all_special_ids)
    ok = torch.zeros(len(tok), dtype=torch.bool)
    for i, s in enumerate(tok.convert_ids_to_tokens(range(len(tok)))):
        if i in special or not s or s[0] != "Ġ" or len(s) < 2:
            continue
        body = s[1:]
        if body.isascii() and body.isprintable() and " " not in body:
            ok[i] = True
    return ok.to(device)


class Item:
    """The token layout for one item, with the suffix slots left open.

    The context at frac=1.0 is the passage repeated once per 20-word chunk of
    the original, so the suffix appears R times and the gradient accumulates
    over all R copies. We build the layout by planting a sentinel, splitting
    the real poisoned string on it, and tokenising the pieces, so the pieces
    are exactly the text the runner will later plant.
    """

    def __init__(self, tok, d, base, frac, k):
        ctx = " " + BOK.poison_context(d["context"], base + SENTINEL, frac)
        parts = ctx.split(SENTINEL)
        self.n_rep = len(parts) - 1
        enc = lambda s: tok(s, add_special_tokens=False).input_ids
        self.segs = [enc(p) for p in parts]            # R+1 pieces
        self.tail = enc(f"\nQuestion: {d['question']}\nAnswer:")
        ans = enc(" " + str(d["distractor_answer"]).strip())
        self.ans = ans[:k] if ans else enc(" the")
        self.m = len(self.ans)

    def ids(self, suffix):
        """(B, L) token ids for a batch of candidate suffixes."""
        B = suffix.shape[0]
        dev = suffix.device
        out = []
        for i, seg in enumerate(self.segs):
            if seg:
                out.append(torch.tensor(seg, device=dev).expand(B, -1))
            if i < self.n_rep:
                out.append(suffix)
        out.append(torch.tensor(self.tail + self.ans, device=dev).expand(B, -1))
        return torch.cat(out, dim=1)

    def embeds(self, onehot, E):
        """(1, L, D) with the suffix slots differentiable through `onehot`."""
        sfx = onehot @ E
        out = []
        for i, seg in enumerate(self.segs):
            if seg:
                out.append(E[torch.tensor(seg, device=E.device)])
            if i < self.n_rep:
                out.append(sfx)
        out.append(E[torch.tensor(self.tail + self.ans, device=E.device)])
        return torch.cat(out, dim=0).unsqueeze(0)


def entropy_loss(logits, m):
    """Mean entropy in bits over the m steps that predict the answer tokens.

    `logits_to_keep=m+1` gives the last m+1 positions; the position that
    predicts answer token j is the one before it, so we drop the last.
    """
    p = F.softmax(logits[:, :-1].float(), dim=-1)
    return -(p * torch.log2(p.clamp_min(1e-12))).sum(-1).mean(-1)


def run(model, cache, prefix_len, ids=None, embeds=None, m=1):
    n = ids.shape[1] if ids is not None else embeds.shape[1]
    b = ids.shape[0] if ids is not None else 1
    am = torch.ones(b, prefix_len + n, dtype=torch.long, device=model.device)
    kw = {"input_ids": ids} if ids is not None else {"inputs_embeds": embeds}
    out = model(**kw, attention_mask=am, past_key_values=cache,
                use_cache=True, logits_to_keep=m + 1)
    # Crop the appended keys/values back off, then DETACH. The gradient pass
    # writes K/V that carry a graph; without the detach the cropped prefix
    # keeps that graph alive and the next backward fails with "backward
    # through the graph a second time". Nothing downstream needs a gradient
    # through the few-shot block, which is fixed text.
    cache.crop(prefix_len)
    for layer in cache.layers:
        layer.keys = layer.keys.detach()
        layer.values = layer.values.detach()
    return out.logits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=686)
    ap.add_argument("--n_shots", type=int, default=5)
    ap.add_argument("--model", type=str, default=BASE)
    ap.add_argument("--max_context_chars", type=int, default=2000)
    ap.add_argument("--frac", type=float, default=1.0)
    ap.add_argument("--suffix_len", type=int, default=20)
    ap.add_argument("--steps", type=int, default=8)
    ap.add_argument("--batch", type=int, default=16, help="candidates per step")
    ap.add_argument("--topk", type=int, default=64)
    ap.add_argument("--k", type=int, default=4, help="answer steps scored")
    ap.add_argument("--keep", type=int, default=4,
                    help="suffixes carried to the free-running re-measure")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=str, default=OUT)
    args = ap.parse_args()
    torch.manual_seed(args.seed)

    path = PM / "data" / "CoConflictQA" / "test" / DATA
    rows = [json.loads(l) for l in path.read_text().splitlines()]
    kept = [r for r in rows if len(r["context"]) <= args.max_context_chars]
    data = kept[: args.n]
    shots = kept[args.n: args.n + args.n_shots]
    assert len(shots) == args.n_shots, "not enough held-out items for few-shots"
    miss = [d for d in data if not (d.get("adaptive_evidencde") or "").strip()]
    if miss:
        raise SystemExit(f"{len(miss)} items lack adaptive_evidencde")
    print(f"{len(rows)} rows, {len(kept)} within {args.max_context_chars} "
          f"chars, optimising {len(data)}", flush=True)

    fs = BOK.build_fewshots(shots)
    tok = AutoTokenizer.from_pretrained(args.model)
    tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        args.model, device_map="auto", torch_dtype=torch.bfloat16)
    model.eval()
    for p in model.parameters():
        p.requires_grad_(False)
    E = model.get_input_embeddings().weight
    V = E.shape[0]
    ok = allowed_tokens(tok, model.device)
    print(f"  {int(ok.sum())} of {V} tokens allowed as suffix tokens", flush=True)

    # The few-shot block is identical for every item, so its KV cache is built
    # once and reused for all 686. `head` deliberately stops before the space
    # after "Context:" so that the first piece of the context starts with one.
    # rsplit, not split: the few-shot block contains "Context:" once per shot,
    # and splitting on the first one cached 8 tokens instead of the whole block.
    head = BOK.make_prompt(fs["with_context"], "Q", "C") \
        .rsplit("Context:", 1)[0] + "Context:"
    head_ids = tok(head, return_tensors="pt").input_ids.to(model.device)
    P = head_ids.shape[1]

    def fresh(batch):
        c = DynamicCache()
        with torch.no_grad():
            model(head_ids.expand(batch, -1), past_key_values=c,
                  use_cache=True, logits_to_keep=1)
        return c

    cache1, cacheB = fresh(1), fresh(args.batch)
    print(f"  prefix {P} tokens cached; "
          f"VRAM {torch.cuda.memory_allocated()/1e9:.1f} GB", flush=True)

    # GCG's usual "! ! ! ..." init, but as the SPACE-LEADING "\u0120!" token.
    # `tok(" !")` returns the bare "!" token, which merges with the full stop
    # the base passage ends on (".!"), and the round trip then fails for every
    # item whose first slot is still at its initial value.
    init_id = tok.convert_tokens_to_ids("\u0120!")
    assert ok[init_id], "init token is not in the allowed set"
    init = torch.full((args.suffix_len,), init_id, device=model.device)

    out, stats, t0 = [], [], time.time()
    n_exact = n_kept = 0
    for idx, d in enumerate(data):
        base = d["adaptive_evidencde"].strip()
        it = Item(tok, d, base, args.frac, args.k)
        sfx = init.clone()

        with torch.no_grad():
            best = float(entropy_loss(
                run(model, cache1, P, ids=sfx.unsqueeze(0), m=it.m), it.m))
        start = best
        # Every step's winner goes in the pool, not just the running best.
        # The search objective is teacher-forced on the distractor answer and
        # the reported one is free-running greedy; they agree when the model
        # is already saying the distractor and diverge when it is not, so the
        # surrogate's argmin is often not the argmin of the number we report.
        # Measuring a handful of candidates properly at the end costs about
        # 2 % of the search and recovers most of that loss.
        pool = {tuple(sfx.tolist()): best}
        for _ in range(args.steps):
            oh = F.one_hot(sfx, V).to(E.dtype).requires_grad_(True)
            logits = run(model, cache1, P, embeds=it.embeds(oh, E), m=it.m)
            entropy_loss(logits, it.m).backward()
            g = oh.grad.float()
            g[:, ~ok] = float("inf")
            cand = (-g).topk(args.topk, dim=1).indices            # (T, topk)
            pos = torch.randint(0, args.suffix_len, (args.batch,),
                                device=model.device)
            pick = torch.randint(0, args.topk, (args.batch,), device=model.device)
            trial = sfx.unsqueeze(0).repeat(args.batch, 1)
            trial[torch.arange(args.batch, device=model.device), pos] = \
                cand[pos, pick]
            with torch.no_grad():
                losses = entropy_loss(
                    run(model, cacheB, P, ids=it.ids(trial), m=it.m), it.m)
            j = int(losses.argmin())
            pool.setdefault(tuple(trial[j].tolist()), float(losses[j]))
            if float(losses[j]) < best:
                best, sfx = float(losses[j]), trial[j].clone()

        # Decode, rebuild the real string, and re-measure with the free-running
        # probe the best-of-K run used. Everything above is a proposal; this is
        # the number that decides and the number we report.
        # clean_up_tokenization_spaces=False is load-bearing. The default
        # decoder deletes the space before punctuation, so a suffix of five
        # "\u0120!" tokens came back as "!!!!!" - a DIFFERENT string from the
        # one the search scored, which then merged with the base passage's
        # full stop into ".!". The round-trip check caught it (0 of 8 exact)
        # and the keep-only-if-better guard kept it from reaching a result.
        cands = sorted(pool.items(), key=lambda kv: kv[1])[: args.keep]
        scored = []
        for ids_t, _ in cands:
            t = tok.decode(list(ids_t), clean_up_tokenization_spaces=False)
            pg = base + t
            with torch.no_grad():
                e = BOK.entropy_of_next_token(
                    model, tok, BOK.make_prompt(
                        fs["with_context"], d["question"],
                        BOK.poison_context(d["context"], pg, args.frac)), args.k)
            scored.append((e, list(ids_t), t, pg))
        e_grad, sfx_ids, sfx_text, passage = min(scored, key=lambda x: x[0])
        exact = tok(" " + passage, add_special_tokens=False).input_ids == \
            it.segs[0] + sfx_ids
        n_exact += bool(exact)
        e_bok = d["ent_pos_adaptive"]
        use = e_grad < e_bok
        n_kept += int(not use)
        e = dict(d)
        e["gradient_evidencde"] = passage if use else base
        e["gradient_suffix"] = sfx_text if use else ""
        e["ent_pos_gradient"] = round(min(e_grad, e_bok), 4)
        e["ent_pos_gradient_raw"] = round(e_grad, 4)
        e["d_alpha_gradient"] = round(
            d["ent_no_context"] / (e["ent_pos_gradient"] + d["ent_no_context"]), 4)
        e["gcg_surrogate"] = [round(start, 4), round(best, 4)]
        e["gcg_roundtrip_exact"] = bool(exact)
        out.append(e)
        stats.append((e_bok, e["ent_pos_gradient"]))
        if (idx + 1) % 25 == 0:
            el = time.time() - t0
            print(f"  {idx+1}/{len(data)}  median ent_pos "
                  f"{statistics.median(a for a, _ in stats):.3f} -> "
                  f"{statistics.median(b for _, b in stats):.3f}   "
                  f"kept-BoK {n_kept}  exact {n_exact}   "
                  f"{el/(idx+1):.1f}s/item  eta {(len(data)-idx-1)*el/(idx+1)/60:.0f}m",
                  flush=True)

    adapted = {json.dumps(r, sort_keys=True): o for r, o in zip(data, out)}
    final = [adapted.get(json.dumps(r, sort_keys=True), r) for r in rows]
    n_ad = sum(1 for r in final if "gradient_evidencde" in r)
    assert n_ad == len(out), f"{n_ad} written vs {len(out)} optimised"
    dest = PM / "data" / "CoConflictQA" / "test" / args.out
    dest.write_text("\n".join(json.dumps(r) for r in final))

    bok = [a for a, _ in stats]
    grd = [b for _, b in stats]
    dap = [r["d_alpha_adaptive"] for r in out]
    dgr = [r["d_alpha_gradient"] for r in out]
    print(f"\nwrote {dest.name}  {len(final)} rows, {n_ad} optimised")
    print(f"round trip exact on {n_exact}/{len(out)}; "
          f"gradient failed to improve on {n_kept}/{len(out)} (best-of-K kept)")
    print(f"median ent_pos  best-of-K {statistics.median(bok):.4f}  "
          f"gradient {statistics.median(grd):.4f}")
    print(f"mean   ent_pos  best-of-K {statistics.mean(bok):.4f}  "
          f"gradient {statistics.mean(grd):.4f}")
    print(f"median d_alpha  best-of-K {statistics.median(dap):.4f}  "
          f"gradient {statistics.median(dgr):.4f}   (1.0 = ACD becomes plain RAG)")
    print(f"\nrun ACD with:  --data {args.out} --n {len(out)} "
          f"--n_shots {args.n_shots} --attack gradient_evidence")


if __name__ == "__main__":
    main()

"""CK-PLUG (incidental-validated) vs corpus poisoning (deliberate).

Second defense in the silent-corruption cell. CK-PLUG fuses the model's
parametric next-token distribution with the context-conditioned one, weighted
by a confidence gain, so `alpha` slides between trusting memory and trusting
the retrieved text. Same family as ParamMute - the intervention is *rely on the
context more* - so the prediction is the same: correct when the context is
merely stale, dangerous when an attacker owns it.

Two things make this directly comparable to the ParamMute run rather than
merely analogous:

  * CK-PLUG's own scorer is the same construction - `ps` (recall against gold),
    `po` (recall against the parametric answer), `mr = po/(ps+po)`, `em`. Their
    `get_score`, `eval` and `qa_to_prompt_baseline` are imported unchanged.
  * It runs on the same CoConflictQA items, which carry exactly the fields both
    harnesses need. CK-PLUG's own `kr_data/` is not in the repo, and
    substituting a dataset is a harness change, not a rubric change.

Arms, both on the same prompts and decoder:
    base_rag   standard RAG generation          (defense off)
    ck         confidence-gain fusion, alpha    (defense on)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
CKP = REPO / "third_party" / "CK-PLUG"
PM = REPO / "third_party" / "ParamMute"
sys.path.insert(0, str(CKP))
sys.path.insert(0, str(REPO / "scripts"))

# ck.py opens with `from vllm import LLM, SamplingParams` and never uses
# either name - grep finds exactly one occurrence, the import itself. Same
# dead import as FaithfulRAG's format_util.py. Stubbed rather than installing
# a serving stack to satisfy a line that does nothing.
if "vllm" not in sys.modules:
    import types
    _stub = types.ModuleType("vllm")
    _stub.LLM = _stub.SamplingParams = None
    sys.modules["vllm"] = _stub

import eval_NQ as CKEVAL                          # noqa: E402  (their code)
from ck import CK                                 # noqa: E402  (their code)
from transfer_stats import (                      # noqa: E402
    adversarial_text, min_detectable_change, wilson)

# ---------------------------------------------------------------------------
# Second attack, added 2026-10-13.
#
# Corpus poisoning plants an OPTIMISED TOKEN SEQUENCE - incoherent junk.
# `--attack false_evidence` plants CoConflictQA's own `parametric_evidencde`
# instead: a short, fluent, citation-bearing sentence asserting the wrong
# answer ("According to IMDB, Season 4 of Chicago Fire consists of 22
# episodes" where the gold answer is 23). Same items, same chunk-replacement
# dosing, so the ONLY thing that changes is the payload.
#
# The false answer it asserts is the model's OWN prior answer, so context and
# memory AGREE. That is the harder case for any defense keyed on detecting a
# conflict between the two.
# ---------------------------------------------------------------------------

CHUNK_WORDS = 20
BASE = "NousResearch/Meta-Llama-3-8B-Instruct"


def poison_context(context: str, passage: str, frac: float) -> str:
    """Identical treatment to the ParamMute and FaithfulRAG runs."""
    if frac <= 0:
        return context
    words = context.split()
    chunks = [" ".join(words[i:i + CHUNK_WORDS])
              for i in range(0, len(words), CHUNK_WORDS)]
    for i in range(min(max(1, round(len(chunks) * frac)), len(chunks))):
        chunks[i] = passage
    return " ".join(chunks)


def run_condition(model, data, passage, frac, schema, mode, alpha, max_new_tokens, top_k=1):
    preds, golds, origs = [], [], []
    # ck.py's own signature defaults to top_k=1 (greedy); their eval_NQ.py
    # overrides it to 100, which makes every run stochastic. Identical
    # base_rag conditions drifted 58-63% across four sweep runs on that
    # setting - more noise than the effect being measured. Using the module's
    # own default restores determinism without touching the scorer.
    params = {"repetition_penalty": 1.0, "temperature": 1.0, "top_p": 1.0,
              "top_k": top_k, "max_new_tokens": max_new_tokens, "logprobs": None,
              "mode": mode, "alpha": alpha, "adaptive": False, "select_top": 10}
    for d in data:
        ctx = poison_context(
            d["context"],
            passage if passage is not None else d["parametric_evidencde"], frac)
        context_prompt = CKEVAL.qa_to_prompt_baseline(d["question"], ctx, schema)
        base_prompt = "Q:{}\nA:".format(d["question"])
        out = model.generate(base_prompt, context_prompt, **params)
        preds.append((out[0] if isinstance(out, tuple) else out).strip())
        golds.append(d["answers"])
        origs.append(d["parametric_answer"])
    em, ps = CKEVAL.get_score(preds, golds)
    _, po = CKEVAL.get_score(preds, origs)
    n = len(data)
    lo, hi = wilson(round(ps / 100 * n), n)
    return {"n": n, "ctx_acc": round(ps, 2), "pm_acc": round(po, 2),
            "mr": round(po / (ps + po + 1e-10) * 100, 2), "em": round(em, 2),
            "ci_low": round(lo * 100, 1), "ci_high": round(hi * 100, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--schema", type=str, default="base")
    ap.add_argument("--alpha", type=float, default=0.5)
    ap.add_argument("--max_new_tokens", type=int, default=32)
    ap.add_argument("--top_k", type=int, default=1,
                    help="1 = greedy, the module's own default; eval_NQ.py uses 100")
    ap.add_argument("--model", type=str, default=BASE)
    ap.add_argument("--data", type=str, default="NaturalQuestionsShort_kc.jsonl")
    ap.add_argument("--clean_only", action="store_true")
    ap.add_argument("--out", type=str,
                    default="data/registries/ckplug_vs_corpus_poisoning.json")
    ap.add_argument("--attack", default="corpus_poisoning",
                    choices=["corpus_poisoning", "false_evidence"],
                    help="corpus_poisoning plants the attack's optimised token "
                         "sequence; false_evidence plants a fluent passage "
                         "asserting the model's own (wrong) prior answer")
    args = ap.parse_args()

    # Fingerprint what is actually planted and refuse to proceed if a
    # false_evidence run is somehow planting the corpus-poisoning passage. An
    # earlier ACD run applied the --attack flag to the output label but not the
    # payload and produced a complete, plausible result file under the wrong
    # attack name; only the numbers being identical to one decimal caught it.
    if args.attack == "false_evidence":
        passage = None
        _probe = None
    else:
        passage = adversarial_text()
        _probe = passage
    path = PM / "data" / "CoConflictQA" / "test" / args.data
    data = [json.loads(l) for l in path.read_text().splitlines()][: args.n]

    if args.attack == "false_evidence":
        miss = [d for d in data if not (d.get("parametric_evidencde") or "").strip()]
        if miss:
            raise SystemExit(f"{len(miss)} items lack parametric_evidencde")
        _probe = data[0]["parametric_evidencde"]
        assert _probe != adversarial_text(), \
            "false_evidence is planting the corpus-poisoning passage"
    payload_fp = hashlib.sha256(_probe.encode()).hexdigest()[:16]
    print(f"  payload[{args.attack}] fp={payload_fp} sample={_probe[:70]!r}",
          flush=True)

    _lab = ("corpus poisoning" if args.attack == "corpus_poisoning"
            else "false evidence")
    conditions = [("clean (native incidental conflict)", 0.0)] if args.clean_only else [
        ("clean (native incidental conflict)", 0.0),
        (f"{_lab}, 10% of context", 0.1),
        (f"{_lab}, 50% of context", 0.5),
        (f"{_lab}, 100% of context", 1.0)]

    model = CK(args.model, "cuda", "1", max_gpu_memory=40)
    model.set_stop_words([])

    results = []
    for arm, mode in (("base_rag", "base_rag"), ("ck", "ck")):
        print(f"\n===== {arm} (alpha={args.alpha if mode=='ck' else 'n/a'}) =====", flush=True)
        for name, frac in conditions:
            r = run_condition(model, data, passage, frac, args.schema, mode,
                              args.alpha, args.max_new_tokens, args.top_k)
            r.update(condition=name, frac=frac, arm=arm)
            results.append(r)
            print(f"  {name:<36} ctx_acc {r['ctx_acc']:5.1f}%  pm_acc {r['pm_acc']:5.1f}%"
                  f"  mr {r['mr']:5.1f}%  em {r['em']:5.1f}%", flush=True)

    out = {"generated": "2026-10-02", "dataset": args.data, "n": len(data),
           "schema": args.schema, "alpha": args.alpha, "model": args.model,
           "top_k": args.top_k,
           "attack": args.attack, "payload_fingerprint": payload_fp,
           "payload_sample": _probe[:160],
           "mdr_pp_at_n": round(min_detectable_change(len(data), 0.5), 1),
           "results": results}
    (REPO / args.out).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {args.out}  (mdr {out['mdr_pp_at_n']} pp)")


if __name__ == "__main__":
    main()

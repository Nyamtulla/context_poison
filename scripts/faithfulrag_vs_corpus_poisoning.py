"""FaithfulRAG (incidental-validated) vs corpus poisoning (deliberate).

**This is the SoK's headline claim as an experiment.** Everything run so far
tested deliberate -> deliberate transfer: RobustRAG is coded
`validated_against: adversarial`, so showing it fail against a second attack
says nothing about the two-literatures thesis. FaithfulRAG is the other kind.
It is `validated_against: incidental`, reasoning-stage, RAG, silent-corruption
- one of the 54 incidental-validated defenses in that cell. The question is
whether work built for context going bad *by accident* survives context made
bad *on purpose*.

There is a specific reason to expect trouble, and a specific reason to expect
the opposite, which is what makes it worth running:

  against   FaithfulRAG's entire objective is to make the model trust the
            retrieved context OVER its own parametric knowledge. Its benchmark
            (`squad_negative`) says "Normandy, a region in Spain" and scores
            the model correct for answering Spain. Pointing a context attack
            at a defense whose purpose is to increase context trust is not
            obviously safe.

  for       its chunk selection keeps only the context chunks most similar to
            the model's own stated facts. Corpus poisoning's passage is
            optimised for retriever embedding similarity and is incoherent to
            a reader, so it may be discarded as irrelevant - robustness by
            accident, for a reason the authors never claimed.

Design. The vanilla arm runs the SAME prompt over the full context; the
FaithfulRAG arm runs it over the pipeline's selected chunks. So the only
variable is FaithfulRAG's own mechanism (self-facts + contextual alignment),
not prompt wording.

Poisoning mirrors the RobustRAG experiment. There the attack displaced N of 10
retrieved passages; here the context is one document, so it displaces the same
*fraction* of it, chunked at FaithfulRAG's own chunk_size. frac 0.1 / 0.5 / 1.0
correspond to displace-1 / 5 / 10.

Run:
    python3 scripts/faithfulrag_vs_corpus_poisoning.py --n 100
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
FRAG = REPO / "third_party" / "Faithful-RAG"
sys.path.insert(0, str(FRAG))
sys.path.insert(0, str(REPO / "scripts"))

# faithfulrag/util/format_util.py does `from vllm import LLM, SamplingParams`
# at module level, but neither name is used anywhere in the package - it is a
# dead import on every backend, including the `hf` one we run. Stubbing it
# avoids installing a 10 GB serving stack (pinned to vllm 0.6.4.post1, which
# predates this torch) to satisfy a line that does nothing. Verified with
# `grep -rn "LLM\|SamplingParams" faithfulrag/`: line 7 is the only hit.
if "vllm" not in sys.modules:
    import types
    _stub = types.ModuleType("vllm")
    _stub.LLM = _stub.SamplingParams = None
    sys.modules["vllm"] = _stub

from datasets import Dataset                      # noqa: E402
import faithfulrag.llm.hf as _frag_hf             # noqa: E402
from faithfulrag import FaithfulRAG               # noqa: E402


def _strip_openai_only_params() -> None:
    """Let the CoT generation paths run on the local backend.

    `pipeline.get_predictions` sets `response_format={"type": "json_object"}`
    for `normal_cot` and `scheduled_cot`. That is an OpenAI JSON-mode flag;
    `hf_chat_completion` forwards it into `model.generate`, which rejects it:
    "The following `model_kwargs` are not used by the model:
    ['response_format']". So on open-weight models the CoT variants - the
    paper's own default - crash, and only the ablated `wo_cot` path runs.

    The fix matches what the authors already do one line above: they pop
    `max_tokens`, `hashing_kv` and `keyword_extraction` for exactly this
    reason. `response_format` is the same class of parameter.

    **This is not free.** OpenAI's JSON mode *guarantees* syntactically valid
    JSON; a local model only has the prompt asking for it. So CoT parsing can
    fail here in ways it would not against the API, and any CoT number from
    this harness is a local-backend number, not the paper's.
    """
    original = _frag_hf.hf_chat_completion

    async def patched(model_name, prompt, system_prompt=None,
                      history_messages=[], **generation_params):
        generation_params.pop("response_format", None)
        return await original(model_name, prompt, system_prompt,
                              history_messages, **generation_params)

    _frag_hf.hf_chat_completion = patched


_strip_openai_only_params()

from transfer_stats import (                      # noqa: E402
    adversarial_text, min_detectable_change, wilson)

CHUNK_WORDS = 20  # FaithfulRAG's own default chunk_size


def poison_context(context: str, passage: str, frac: float) -> str:
    """Replace the leading `frac` of the context with the adversarial passage.

    Chunked at FaithfulRAG's chunk_size so a replaced chunk is exactly the unit
    its contextual alignment scores - displacing half the context really does
    cost half the chunks it could have selected, rather than being diluted
    across every chunk.
    """
    if frac <= 0:
        return context
    words = context.split()
    chunks = [" ".join(words[i : i + CHUNK_WORDS])
              for i in range(0, len(words), CHUNK_WORDS)]
    n_poison = max(1, round(len(chunks) * frac))
    for i in range(min(n_poison, len(chunks))):
        chunks[i] = passage
    return " ".join(chunks)


def make_dataset(items, passage, frac):
    rows = [{**it, "context": poison_context(it["context"], passage, frac)}
            for it in items]
    return Dataset.from_list(rows)


async def evaluate_arm(rag, dataset, arm, generation="wo_cot"):
    """`vanilla` answers from the whole context; `faithfulrag` from its own
    selected chunks. Same prompt, same decoder, same scorer."""
    if arm == "vanilla":
        facts = [{"id": it["id"],
                  "topk_chunks": [{"chunk": it["context"]}]} for it in dataset]
    else:
        self_facts = await rag.get_self_facts(dataset, fact_mining_type="default")
        facts = rag.get_topk_chunks(dataset, self_facts)
    preds = await rag.get_predictions(dataset, facts,
                                      generation_type=generation, max_tokens=100)
    return rag.evaluate(dataset, preds, cot_format=generation != "wo_cot",
                        detailed_output=True)


async def main_async(args):
    passage = adversarial_text()
    raw = json.loads((FRAG / "datas" / f"{args.dataset}.json").read_text())[: args.n]

    # The repo's defaults pass `temperature: 0.0` straight to
    # `model.generate`, which current transformers rejects outright:
    # "`temperature` (=0.0) has to be a strictly positive float ... set
    # do_sample=False". Greedy decoding is precisely what temperature 0 means,
    # so we ask for it by name rather than nudging the temperature to some
    # small positive value, which would silently make the run stochastic.
    greedy = {"max_tokens": 1000, "do_sample": False}
    rag = FaithfulRAG(backend_type="hf", model_name=args.model,
                      similarity_model=args.similarity_model,
                      mining_sampling_params=dict(greedy),
                      generation_sampling_params=dict(greedy))

    fractions = [("clean (native incidental conflict)", 0.0)] if args.clean_only else [
        ("clean (native incidental conflict)", 0.0),
        ("corpus poisoning, 10% of context", 0.1),
        ("corpus poisoning, 50% of context", 0.5),
        ("corpus poisoning, 100% of context", 1.0)]

    results = []
    for name, frac in fractions:
        print(name, flush=True)
        ds = make_dataset(raw, passage, frac)
        for arm in ("vanilla", "faithfulrag"):
            ev = await evaluate_arm(rag, ds, arm, args.generation)
            acc, n = ev["acc"], len(ds)
            k = round(acc / 100 * n)
            lo, hi = wilson(k, n)
            print(f"  {arm:<14} acc {acc:5.1f}%  EM {ev['exact_match']:5.1f}%  "
                  f"F1 {ev['f1']:5.1f}%  95% CI [{lo*100:.1f}, {hi*100:.1f}]",
                  flush=True)
            results.append({"condition": name, "frac": frac, "arm": arm,
                            "n": n, "acc": acc, "exact_match": ev["exact_match"],
                            "f1": ev["f1"], "ci_low": lo * 100, "ci_high": hi * 100})
        print(flush=True)

    out = {"generated": "2026-10-02", "model": args.model,
           "dataset": args.dataset, "generation": args.generation, "n": args.n,
           "chunk_words": CHUNK_WORDS,
           "mdr_pp_at_n": round(min_detectable_change(args.n, 0.5), 1),
           "results": results}
    (REPO / args.out).write_text(json.dumps(out, indent=1))
    print(f"wrote {args.out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--dataset", type=str, default="squad_negative")
    ap.add_argument("--generation", type=str, default="wo_cot",
                    choices=["wo_cot", "normal_cot", "scheduled_cot"])
    ap.add_argument("--clean_only", action="store_true",
                    help="control sweep: reproduce the defense's own benefit first")
    ap.add_argument("--model", type=str, default="Qwen/Qwen2.5-7B-Instruct")
    ap.add_argument("--similarity_model", type=str,
                    default="sentence-transformers/all-MiniLM-L6-v2")
    ap.add_argument("--out", type=str,
                    default="data/registries/faithfulrag_vs_corpus_poisoning.json")
    asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    main()

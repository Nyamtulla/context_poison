"""The proposed fix (scripts/specvote.py), run through the shared harness.

Everything up to the per-passage answers is ReliabilityRAG's own code at the
pinned commit, so the fix and ReliabilityRAG differ only in how they combine
those answers: `create_model` with their vLLM backend at temperature 0,
`RRAG.query_undefended` for the undefended and no-document arms, and their
own `wrap_prompt(..., seperate=True)` + `batch_query` for one answer per
passage. The fix then counts sources rather than passages (specvote.decide).

Results go to data/registries/ours/, outside the native_* files that the grid,
the pair counts and numbers.tex are built from: the campaign counts published
fixes only, and this one is ours.

    envs/reliabilityrag-venv/bin/python scripts/sd_specvote.py \\
        --failure incidental_stale [--model mistral7b|llama8b] [--n 20]
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
RELI = REPO / "third_party" / "ReliabilityRAG"
sys.path.insert(0, str(REPO / "scripts"))
MODEL_DIR = str(REPO / "data" / "sd_models" / "hf") + "/"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--failure", required=True)
    ap.add_argument("--model", default="mistral7b", choices=["mistral7b", "llama8b"])
    ap.add_argument("--n", type=int, default=None, help="smoke: first n items")
    ap.add_argument("--doses", type=int, nargs="+", default=None)
    ap.add_argument("--arms", nargs="+", default=None,
                    help="subset of closedbook/undefended/defended")
    args = ap.parse_args()

    from sd_common import run_cell
    import specvote
    # same process setup as sd_reliabilityrag.py: in-process vLLM engine, and
    # uv's Python headers so Triton's startup helper can build on this box
    os.environ.setdefault("VLLM_ENABLE_V1_MULTIPROCESSING", "0")
    inc = (pathlib.Path.home() / ".local/share/uv/python/"
           "cpython-3.10-linux-x86_64-gnu/include/python3.10")
    if inc.exists() and not os.path.exists("/usr/include/python3.10/Python.h"):
        os.environ["C_INCLUDE_PATH"] = str(inc)
    sys.path.insert(0, str(RELI))
    os.chdir(RELI)       # their code opens configs by relative path
    import src.models                                # their code
    from src.models import create_model              # their code
    from src.defense import RRAG                     # their code

    # their VLLMModel asks for 0.5 of the card; add back what other users
    # hold so the budget is the same as on an empty card (sd_reliabilityrag)
    import torch
    _LLM = src.models.LLM
    budget = {}

    def LLM(*a, gpu_memory_utilization=0.5, **k):
        free, total = torch.cuda.mem_get_info()
        u = min(0.92, gpu_memory_utilization + (total - free) / total)
        budget.update(theirs=gpu_memory_utilization, passed=round(u, 3),
                      others_gb=round((total - free) / 2**30, 1))
        return _LLM(*a, gpu_memory_utilization=u, **k)
    src.models.LLM = LLM

    llm = create_model(args.model, MODEL_DIR, use_open_model_api=False)
    base = RRAG(llm)

    def item(q, ps):
        return {"question": q, "topk_content": ps, "answer": []}

    def undefended(q, ps):
        return str(base.query_undefended(item(q, ps)))

    trace = {}

    def defended(q, ps):
        if not ps:
            return undefended(q, ps)
        responses = [str(r) for r in llm.batch_query(
            llm.wrap_prompt(item(q, ps), as_multi_choice=False, seperate=True))]
        pred, how = specvote.decide(ps, responses)
        trace[(q, len(ps))] = {"responses": responses, **how}
        return pred

    def extra_fn(arm, dose, row, pred):
        if arm != "defended":
            return None
        return trace.get((row["question"], len(row["contexts"][str(dose)])))

    tag = "smoke_" if args.n else ""
    out = REPO / "data" / "registries" / "ours" / f"{tag}specvote_{args.failure}_{args.model}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    log = REPO / "data" / "sd_logs" / f"{tag}ours_specvote_{args.failure}_{args.model}.jsonl"
    run_cell(defense="specvote", family="source-count vote (ours)",
             failure=args.failure, model=args.model, undefended=undefended,
             defended=defended, closedbook=undefended, out_path=out,
             log_path=log, n=args.n, doses=args.doses, extra_fn=extra_fn,
             **({"arms": tuple(args.arms)} if args.arms else {}),
             notes={"method": "specvote.decide (frozen in Phase 0e)",
                    "specifics_jaccard": specvote.SPECIFICS_JACCARD,
                    "per_passage_answers": "ReliabilityRAG wrap_prompt(seperate=True) + batch_query",
                    "backend": "their VLLMModel, temperature 0",
                    "memory_budget": budget})


if __name__ == "__main__":
    main()

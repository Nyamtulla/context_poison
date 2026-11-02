"""ReliabilityRAG on the second direction: a provable defense, facing honest error.

ReliabilityRAG (Shen et al., NeurIPS 2025) answers from each retrieved passage
separately, links two passages when an NLI model finds their answers
contradictory, and keeps the maximum independent set -- the largest group of
mutually consistent passages, ties broken toward the higher-ranked ones. Its
guarantee holds against a bounded number of corrupted passages.

That bound is what the second direction tests. An attacker plants a few
passages that disagree with the honest majority; a fact that changed leaves
several honest passages that agree with each other and are all wrong. If the
stale passages are the larger consistent group, the defense keeps them.

Everything defense-side is their code at the pinned commit: `create_model`
with their vLLM backend at temperature 0 (the path their main.py takes for
mistral7b), `RRAG.query_undefended` for the undefended arm and `MISBasedRRAG`
for the defended one, with their default err=0. Two things are supplied from
outside it, neither changing what it computes:

  * their VLLMModel loads `model_dir + "Mistral-7B-Instruct-v0.2"`; model_dir
    points at a link to the hub snapshot every other Mistral run here uses.
  * MISBasedRRAG loads its NLI model from a path on their cluster,
    /scratch/gpfs/zs7353/DeBERTa-v3-large-mnli-fever-anli-ling-wanli. That is
    MoritzLaurer's hub model of the same name; the load is redirected to it.

    envs/reliabilityrag-venv/bin/python scripts/sd_reliabilityrag.py \\
        --failure incidental_stale
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
RELI = REPO / "third_party" / "ReliabilityRAG"
sys.path.insert(0, str(REPO / "scripts"))

NLI_CLUSTER_PATH = "/scratch/gpfs/zs7353/DeBERTa-v3-large-mnli-fever-anli-ling-wanli"
NLI_HUB = "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli"
MODEL_DIR = str(REPO / "data" / "sd_models" / "hf") + "/"


def redirect_nli():
    """Point their hard-coded cluster path at the hub copy of the same model."""
    import transformers
    for cls in (transformers.AutoTokenizer,
                transformers.AutoModelForSequenceClassification):
        orig = cls.from_pretrained.__func__

        def patched(c, path, *a, _orig=orig, **k):
            if path == NLI_CLUSTER_PATH:
                path = NLI_HUB
            return _orig(c, path, *a, **k)
        cls.from_pretrained = classmethod(patched)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--failure", required=True)
    ap.add_argument("--n", type=int, default=None, help="smoke: first n items")
    ap.add_argument("--doses", type=int, nargs="+", default=None)
    ap.add_argument("--err", type=float, default=0.0,
                    help="their NLI error-injection knob; main.py default 0")
    ap.add_argument("--out", default=None)
    ap.add_argument("--log_suffix", default="",
                    help="separate answer log, so a rerun does not resume "
                         "from (and reuse) an earlier run's answers")
    ap.add_argument("--arms", nargs="+", default=None,
                    help="subset of closedbook/undefended/defended")
    args = ap.parse_args()

    from sd_common import run_cell
    redirect_nli()
    if args.out:
        args.out = pathlib.Path(args.out).resolve()   # before the chdir below
    # vLLM's V1 engine forks a worker process that failed CUDA init on this
    # box; in-process runs the same engine, same sampling, without the fork
    os.environ.setdefault("VLLM_ENABLE_V1_MULTIPROCESSING", "0")
    # Triton compiles a small C helper at startup and needs Python.h, which
    # this box lacks (no python3-dev). uv's standalone 3.10 ships the headers;
    # they only let the helper build and change nothing the model computes.
    inc = (pathlib.Path.home() / ".local/share/uv/python/"
           "cpython-3.10-linux-x86_64-gnu/include/python3.10")
    if inc.exists() and not os.path.exists("/usr/include/python3.10/Python.h"):
        os.environ["C_INCLUDE_PATH"] = str(inc)
    sys.path.insert(0, str(RELI))
    os.chdir(RELI)       # their code opens configs by relative path
    from src.models import create_model              # their code
    from src.defense import RRAG, MISBasedRRAG       # their code

    llm = create_model("mistral7b", MODEL_DIR, use_open_model_api=False)
    base = RRAG(llm)
    mis = MISBasedRRAG(llm, err=args.err)

    def item(q, ps):
        # "answer" is read only by their debug log line; it never reaches
        # the prompt, so the gold answer stays out of the pipeline
        return {"question": q, "topk_content": ps, "answer": []}

    def undefended(q, ps):
        return str(base.query_undefended(item(q, ps)))

    # Their query() prints neither the per-passage answers nor the
    # contradiction graph, and both are needed to say why a passage was left
    # out: it answered "I don't know" and was never a candidate, or the NLI
    # model set it against the others. Both are recorded on the way through
    # their own calls; neither call's input or output is changed.
    seen = {}
    _batch, _mis_set = llm.batch_query, mis._max_independent_set

    def batch_query(prompts, *a, **k):
        out = _batch(prompts, *a, **k)
        seen["responses"] = [str(r) for r in out]
        return out

    def max_independent_set(graph, vertices):
        best = _mis_set(graph, vertices)
        seen.update(candidates=sorted(vertices),
                    edges=sorted([i, j] for i in graph for j in graph[i] if i < j),
                    selected=sorted(best) if best else [])
        return best
    llm.batch_query = batch_query
    mis._max_independent_set = max_independent_set
    trace = {}

    def defended(q, ps):
        if not ps:
            return undefended(q, ps)
        seen.clear()
        pred = str(mis.query(item(q, ps)))
        trace[(q, len(ps))] = dict(seen)
        return pred

    def extra_fn(arm, dose, row, pred):
        if arm != "defended":
            return None
        return trace.get((row["question"], len(row["contexts"][str(dose)])))

    tag = "smoke_" if args.n else ""
    out = args.out or (REPO / "data" / "registries" /
                       f"{tag}native_reliabilityrag_{args.failure}.json")
    log = (REPO / "data" / "sd_logs" /
           f"{tag}reliabilityrag_{args.failure}_mistral7b{args.log_suffix}.jsonl")
    run_cell(defense="reliabilityrag", family="consistent-subset",
             failure=args.failure, model="mistral7b", undefended=undefended,
             defended=defended, closedbook=undefended, out_path=out,
             log_path=log, n=args.n, doses=args.doses, extra_fn=extra_fn,
             **({"arms": tuple(args.arms)} if args.arms else {}),
             notes={"registry_row": 276, "method": "MISBasedRRAG",
                    "err": args.err,
                    "backend": "their VLLMModel, temperature 0, "
                               "gpu_memory_utilization 0.5",
                    "nli": f"{NLI_HUB} (their cluster path redirected)"})


if __name__ == "__main__":
    main()

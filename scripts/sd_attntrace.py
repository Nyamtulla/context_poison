"""AttnTrace on the second direction: trace the answer, remove what drove it.

AttnTrace (Wang et al., 2025) attributes an LLM's answer to the passages in
its context from attention weights, and its paper evaluates it on finding
PoisonedRAG's planted passages among the retrieved ones. Their release
reports the attribution -- which passages drove the answer -- and stops
there. Used as a defense, attribution is followed by the step its paper
motivates it with: remove the traced passages and answer again. That removal
step is ours and is the only part of this runner that is not their code.

The prediction this tests: an attribution method finds the passages that
drove the answer, whoever wrote them. A stale passage that moved the model is
traced exactly as a planted one is, so removing it may help against honest
error too -- the one security defense here whose mechanism does not depend on
an attacker's budget or an injected instruction.

Their code throughout: `create_model` from their qwen2.5-7b config (Llama-3.1
is gated for this account; Qwen2.5-7B is one of the configs they ship), their
`wrap_prompt` with the split token their PoisonedRAG experiment uses,
`newline_pad_contexts`, and `AttnTraceAttribution` with their main.py
defaults (segment level, K=5, avg_k=5, q=0.4, B=30, seed 12). Retrieved
passages are already segments, so each traced index is one passage.

    envs/attntrace-venv/bin/python scripts/sd_attntrace.py \\
        --failure incidental_stale
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
ATT = REPO / "third_party" / "AttnTrace"
sys.path.insert(0, str(REPO / "scripts"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--failure", required=True)
    ap.add_argument("--n", type=int, default=None, help="smoke: first n items")
    ap.add_argument("--doses", type=int, nargs="+", default=None)
    ap.add_argument("--model_name", default="qwen2.5-7b")
    ap.add_argument("--K", type=int, default=5,
                    help="passages traced and removed; their main.py default")
    ap.add_argument("--out", default=None)
    ap.add_argument("--device", default="cuda:0",
                    help="cpu runs a slow smoke test off the shared card")
    args = ap.parse_args()

    from sd_common import run_cell
    if args.out:
        args.out = pathlib.Path(args.out).resolve()   # before the chdir below
    sys.path.insert(0, str(ATT))
    os.chdir(ATT)            # their configs are opened by relative path
    from src.models import create_model                     # their code
    from src.attribution import AttnTraceAttribution        # their code
    from src.prompts import wrap_prompt                     # their code
    from src.utils import newline_pad_contexts, setup_seeds  # their code

    setup_seeds(12)
    llm = create_model(config_path=f"model_configs/{args.model_name}_config.json",
                       device=args.device)
    attr = AttnTraceAttribution(llm, explanation_level="segment", K=args.K,
                                avg_k=5, q=0.4, B=30, verbose=0)

    def answer(q, ps):
        return str(llm.query(wrap_prompt(q, ps, split_token="\n")))

    traced = {}

    def defended(q, ps):
        if len(ps) < 2:
            # nothing to choose between: their split_context would re-split a
            # single passage into segments, and an empty context has none
            return answer(q, ps)
        first = answer(q, ps)
        _, ids, scores, _, _ = attr.attribute(q, newline_pad_contexts(ps),
                                              first)
        # their top_k_indices come highest-scoring first, scores aligned
        ranked = [int(i) for i in ids]
        traced[(q, len(ps))] = {"first": first, "ranked": ranked,
                                "scores": [float(s) for s in scores]}
        keep = [p for i, p in enumerate(ps) if i not in set(ranked)]
        return answer(q, keep)

    def extra_fn(arm, dose, row, pred):
        """What was traced, in rank order, so the forensic reading -- did the
        top-ranked passage carry the bad answer -- needs no rerun."""
        if arm != "defended":
            return None
        ps = row["contexts"][str(dose)]
        t = traced.get((row["question"], len(ps)))
        if t is None:     # fewer than two passages: nothing was traced
            return {"dropped": []}
        return {"dropped": sorted(t["ranked"]), "traced_ranked": t["ranked"],
                "trace_scores": t["scores"], "first_answer": t["first"]}

    tag = "smoke_" if args.n else ""
    out = args.out or (REPO / "data" / "registries" /
                       f"{tag}native_attntrace_{args.failure}.json")
    log = (REPO / "data" / "sd_logs" /
           f"{tag}attntrace_{args.failure}_{args.model_name}.jsonl")
    run_cell(defense="attntrace", family="attribute-then-remove",
             failure=args.failure, model=args.model_name, undefended=answer,
             defended=defended, closedbook=answer, out_path=out,
             log_path=log, n=args.n, doses=args.doses, extra_fn=extra_fn,
             notes={"registry_row": 217,
                    "attribution": "AttnTraceAttribution segment K=%d avg_k=5 "
                                   "q=0.4 B=30 seed=12" % args.K,
                    "removal_step": "ours: drop the K traced passages and "
                                    "answer again with their wrap_prompt",
                    "model_note": "Llama-3.1-8B is gated for this account; "
                                  "qwen2.5-7b is a config they ship"})


if __name__ == "__main__":
    main()

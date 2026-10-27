"""RobustRAG against all four attack mechanisms — a different defense family.

Everything measured so far belongs to one family: ParamMute, CK-PLUG and SpARE
all work by **increasing reliance on retrieved context at the expense of
parametric memory**. They share a failure: at saturation they cost ~32 points,
because they instruct the model to use evidence that is gone and have removed
the fallback it would otherwise use.

RobustRAG is built on a different principle. It answers over **each retrieved
passage in isolation** and aggregates the answers, so a corrupted passage is
outvoted rather than trusted or distrusted wholesale. It never touches
parametric memory.

That makes it the test of whether the saturation penalty is a property of
*context-reliance defenses* or of *RAG defenses generally*:

  * if RobustRAG also collapses at 10/10, the boundary is about the evidence
    set, and any post-retrieval defense inherits it
  * if it degrades gracefully instead, the ~32-point penalty is specifically
    the cost of suppressing parametric memory, and the claim narrows to that
    family

Scoring, prompt construction and the attack payloads are shared with the other
runs in this matrix so every number sits on one scale.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
RRAG = REPO / "third_party" / "RobustRAG"
sys.path.insert(0, str(RRAG))
sys.path.insert(0, str(REPO / "scripts"))

# Their src/models.py imports litellm at module scope for an API-model class
# we never instantiate: every run in this project uses their local HFModel.
# Stubbed rather than installed, the same way ck.py's unused vllm import is,
# so the dependency set stays the authors' pins and nothing else.
if "litellm" not in sys.modules:
    import types
    _ll = types.ModuleType("litellm")
    _ll.batch_completion = None
    sys.modules["litellm"] = _ll

from src.defense import DecodingAgg, KeywordAgg    # noqa: E402  (their code)
import torch                                      # noqa: E402
from src import models as rr_models               # noqa: E402  (their code)
from src.helper import StopOnTokens               # noqa: E402  (their code)
from src.models import create_model, HFModel      # noqa: E402  (their code)
from src.prompt_template import LLAMA_TMPL        # noqa: E402  (their code)

from transfer_stats import min_detectable_change, wilson        # noqa: E402
from spare_vs_corpus_poisoning import acc_score                 # noqa: E402
import poisonedrag_transfer as pr                              # noqa: E402
from poisonedrag_transfer import (                              # noqa: E402
    build_poisoned, direct_input_question, is_negative, is_refusal)


# ---------------------------------------------------------------------------
# A tokenizer-dependent crash in RobustRAG's own stopping criteria
# ---------------------------------------------------------------------------
# DecodingAgg builds its stop sequences with
#     tokenizer(x, add_special_tokens=False)   for x in ["\n#", ..., "\n\n"]
# and then compares `input_ids[0][-len(stop)+1:]` against `stop[0][1:]`, which
# hard-codes an assumption that every stop string tokenizes to at least two
# tokens. Mistral's tokenizer splits the leading newline, so it does. Llama-3
# merges whitespace and encodes "\n\n" as a SINGLE token, so `stop[0][1:]` is
# empty, the slice becomes `input_ids[0][0:]`, and the comparison dies with
#     size of tensor a (803) must match the size of tensor b (0)
# The defense is therefore unrunnable on Llama-3 as shipped. Their own comment
# on the stop list reads "seems to work fine".
#
# The fix keeps their semantics exactly where their assumption holds - two or
# more tokens, strip the first, compare the rest - and compares the whole stop
# sequence when there is only one token to compare. That is strictly tighter
# matching, never looser, and it changes nothing on Mistral.
def _stop_on_tokens_call(self, input_ids, scores, **kwargs):
    for stop_ids in self.stop_token_ids:
        seq = stop_ids[0]
        want = seq[1:] if len(seq) > 1 else seq
        if len(want) == 0 or len(input_ids[0]) < len(want):
            continue
        if torch.eq(input_ids[0][-len(want):], want).all():
            return True
    return False


StopOnTokens.__call__ = _stop_on_tokens_call


def run_condition(defense, data, top_k, n_poison, attack, defended,
                  dump=None, placement="retrieval"):
    """dump: a list to append per-item predictions to.

    The composition experiment needs each method's answer per item, not its
    aggregate. The two halves cannot share a Python environment -- that is
    recorded in Section 7 -- so they cannot be composed in one process. They
    are run separately, their predictions dumped, and combined offline by
    scripts/compose_offline.py.
    """
    correct = attacked = refused = negative = 0
    for it in data:
        question = it["question"]
        if placement == "direct" and defended != "closedbook":
            passages = build_poisoned(it, top_k, 0)
            if n_poison:
                question = direct_input_question(it, attack, repeat=n_poison)
        elif defended == "closedbook":
            passages = []
        else:
            passages = build_poisoned(it, top_k, n_poison, attack=attack)
        item = {"question": question,
                "answer": it["correct answer"],
                "topk_content": passages,
                "incorrect_answer": it.get("incorrect answer", []),
                "incorrect_context": it.get("incorrect_context", [])}
        if defended is True:
            pred, _ = defense.query(item)
        else:
            # closedbook reaches here too: same undefended call, no passage
            pred = defense.query_undefended(item)
        pred = str(pred)
        correct += acc_score(pred, it["correct answer"])
        # the attacked outcome is "said the planted answer"; for the ML arm
        # that is the distractor, not PoisonedRAG's adversarial target.
        target = (it["distractor_answer"] if attack == "distractor_evidence"
                  else it.get("incorrect answer"))
        attacked += acc_score(pred, target)
        refused += is_refusal(pred)
        negative += is_negative(pred)
        if dump is not None:
            dump.append({"question": it["question"], "pred": pred,
                         "gold": it["correct answer"],
                         "n_poison": n_poison, "defended": defended})
    n = len(data)
    asr_count = {"badrag_dos": refused,
                 "badrag_sentiment": negative}.get(attack, attacked)
    lo, hi = wilson(int(asr_count), n)
    return {"n": n, "acc": round(correct / n * 100, 2),
            "asr": round(asr_count / n * 100, 2),
            "refusal_rate": round(refused / n * 100, 2),
            "negative_framing_rate": round(negative / n * 100, 2),
            "wrong_answer_rate": round(attacked / n * 100, 2),
            "asr_ci_low": round(lo * 100, 1), "asr_ci_high": round(hi * 100, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--attack", required=True,
                    choices=["poisonedrag", "badrag_dos", "badrag_sentiment",
                             "distractor_evidence", "corpus_poisoning",
                             # the mirror direction: a security-regime defense
                             # against a retrieval error nobody wrote
                             "misretrieval"])
    ap.add_argument("--placement", default="retrieval",
                    choices=["retrieval", "direct"],
                    help="`direct` leaves the retrieved set clean and puts "
                         "the payload in the user turn. RobustRAG aggregates "
                         "over isolated passages, so on this channel its "
                         "mechanism has nothing to isolate.")
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--top_k", type=int, default=10)
    ap.add_argument("--model", type=str, default="mistral7b")
    ap.add_argument("--method", default="keyword", choices=["keyword", "decoding"],
                    help="RobustRAG ships three aggregation variants. Running a "
                         "second tests whether the family's behaviour is the "
                         "PRINCIPLE (isolate-then-aggregate) or one "
                         "implementation. `voting` is deliberately absent: its "
                         "query() calls wrap_prompt(as_multi_choice=True) and "
                         "only works on multiple-choice data, so it cannot run "
                         "on open-ended open_nq at all.")
    ap.add_argument("--eta", type=float, default=0.0,
                    help="DecodingAgg confidence threshold; their main.py default")
    ap.add_argument("--subsample_iter", type=int, default=1)
    ap.add_argument("--poison_counts", type=int, nargs="+",
                    default=[0, 1, 5, 9, 10])
    ap.add_argument("--out", type=str, default=None)
    ap.add_argument("--closedbook_only", action="store_true",
                    help="measure only the no-retrieval arm and merge it into "
                         "an existing registry, for cells that were finished "
                         "before that arm was required. The merged rows carry "
                         "`measured: backfill`: they come from a later "
                         "session than the dose arms beside them.")
    ap.add_argument("--dump_predictions", type=str, default=None,
                    help="write per-item predictions here, for the offline "
                         "composition in scripts/compose_offline.py")
    args = ap.parse_args()

    # The ML/AI arm runs on the same open_nq items with a distractor passage
    # precomputed by scripts/build_open_nq_distractor.py. Same harness, same
    # dosing; only the payload's intent differs.
    src = (REPO / "data" / "payloads" / "open_nq_distractor.json"
           if args.attack == "distractor_evidence"
           else RRAG / "data" / "open_nq.json")
    data = json.loads(src.read_text())[: args.n]
    if args.attack == "misretrieval":
        # The donor pool is the item set itself. Items with no clean donor -
        # every candidate states this item's gold answer - are dropped, and
        # the drop is reported rather than silently shrinking n.
        pr.set_misretrieval_pool(json.loads(src.read_text()))
        keep = [it for it in data if pr.borrowed_passage(it) is not None]
        if len(keep) != len(data):
            print(f"  misretrieval: {len(data) - len(keep)} of {len(data)} "
                  "items have no clean donor and are dropped", flush=True)
        data = keep
    suffix = "" if args.method == "keyword" else f"_{args.method}"
    suffix += "" if args.placement == "retrieval" else "_direct"
    out_path = args.out or f"data/registries/{args.attack}_robustrag{suffix}.json"

    prev = None
    if args.closedbook_only:
        prev_file = REPO / out_path
        if not prev_file.exists():
            sys.exit(f"{out_path}: nothing to merge into")
        prev = json.loads(prev_file.read_text())
        rows = prev.get("results") or []
        if any(r.get("arm") == "closedbook" for r in rows):
            print(f"{out_path}: already carries a closedbook arm")
            return
        for k, v in (("attack", args.attack), ("model", args.model),
                     ("top_k", args.top_k), ("n", len(data))):
            if prev.get(k) != v:
                sys.exit(f"{out_path}: {k} is {prev.get(k)!r}, not {v!r}; "
                         "this registry is a different experiment")

    # `llama8b` in their registry points at the gated meta-llama repo. The
    # other half of this matrix (ParamMute, CK-PLUG) runs the NousResearch
    # mirror - the same weights, ungated - so the cross-family comparison is
    # only model-controlled if RobustRAG loads that same copy. Their
    # create_model is used unchanged for every other model name.
    if args.model == "llama8b-nous":
        nous = "NousResearch/Meta-Llama-3-8B-Instruct"
        # Their CONTEXT_MAX_TOKENS is keyed by repo path, so the mirror needs
        # an entry. Copied from their own meta-llama entry for the same
        # weights - not a new value, the same 8192 context they use.
        rr_models.CONTEXT_MAX_TOKENS.setdefault(
            nous, rr_models.CONTEXT_MAX_TOKENS["meta-llama/Meta-Llama-3-8B-Instruct"])
        llm = HFModel(nous, LLAMA_TMPL)
    else:
        llm = create_model(args.model)
    defense = (KeywordAgg(llm) if args.method == "keyword"
               else DecodingAgg(llm, args))

    if args.closedbook_only:
        rcb = run_condition(defense, data, args.top_k, 0, args.attack,
                            "closedbook", dump=None, placement=args.placement)
        for npz in sorted({r["n_poison"] for r in prev["results"]}):
            prev["results"].append(dict(rcb, arm="closedbook", n_poison=npz,
                                        measured="backfill"))
        prev["backfill"] = {"date": "2026-10-26", "arms": ["closedbook"],
                            "note": "measured after the dose arms, in a later "
                                    "session; see the environment threat in "
                                    "the paper"}
        prev_file.write_text(json.dumps(prev, indent=1))
        print(f"  closedbook   acc {rcb['acc']:5.1f}%   merged into {out_path}")
        return

    results = []
    preds = [] if args.dump_predictions else None
    # The no-retrieval arm Section 9 asks every paper to report. It does not
    # depend on the attack or the dose, so it is measured once and written
    # against every dose, giving the registry the same shape as the cells
    # that always carried it.
    for defended in ("closedbook", False, True):
        label = ({"closedbook": "closedbook"}.get(defended)
                 or ("defended" if defended else "undefended"))
        if defended == "closedbook":
            rcb = run_condition(defense, data, args.top_k, 0, args.attack,
                                defended, dump=None,
                                placement=args.placement)
            for npz in args.poison_counts:
                results.append(dict(rcb, arm=label, n_poison=npz))
            print(f"  closedbook   acc {rcb['acc']:5.1f}%", flush=True)
            continue
        print(f"\n===== RobustRAG/{args.method} — {label} ({args.attack}) =====",
              flush=True)
        for npz in args.poison_counts:
            r = run_condition(defense, data, args.top_k, npz, args.attack,
                              defended, dump=preds, placement=args.placement)
            r.update(arm=label, n_poison=npz)
            results.append(r)
            print(f"  poison {npz:>2}/{args.top_k}   acc {r['acc']:5.1f}%   "
                  f"ASR {r['asr']:5.1f}%   95% CI [{r['asr_ci_low']}, {r['asr_ci_high']}]",
                  flush=True)

    payload = {"generated": "2026-10-06",
               "defense": f"robustrag-{args.method}",
               "defense_family": "isolate-then-aggregate",
               "aggregation_method": args.method,
               "attack": args.attack, "placement": args.placement,
               "dataset": "open_nq", "n": len(data),
               "top_k": args.top_k, "model": args.model,
               "mdr_pp_at_n": round(min_detectable_change(len(data), 0.5), 1),
               "results": results}
    (REPO / out_path).write_text(json.dumps(payload, indent=1))
    print(f"\nwrote {out_path}  (mdr {payload['mdr_pp_at_n']} pp)")
    if preds is not None:
        (REPO / args.dump_predictions).write_text(json.dumps(
            {"defense": f"robustrag-{args.method}", "attack": args.attack,
             "model": args.model, "n": len(data), "predictions": preds},
            indent=1))
        print(f"wrote {args.dump_predictions}  ({len(preds)} predictions)")


if __name__ == "__main__":
    main()

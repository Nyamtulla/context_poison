"""Does a ported defense still reproduce its own published benefit?

The first of the four rules: a defense that cannot reproduce its own
published benefit in our harness reports no transfer number. It already
caught FaithfulRAG. Moving four defenses from their own scripts onto the
native top-k harness is exactly the kind of change that can break a method
quietly, so each port is gated before it is allowed near the main grid.

The gate runs the defense on CoConflictQA at CLEAN dose - its own benchmark,
no attack - and checks the arm the method's authors compare against. The
expectations below are taken from our own earlier runs of these same methods
under their own scripts, which is the thing the port has to reproduce.

    python3 scripts/control_gate.py --defense coiecd --n 100

Out: data/registries/control_gate_<defense>.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "third_party" / "CK-PLUG"))
DATA = (REPO / "third_party" / "ParamMute" / "data" / "CoConflictQA"
        / "test" / "NaturalQuestionsShort_kc.jsonl")

# What each port has to reproduce: the run we already have of that same
# method, on the same data, at clean dose.
#
# An earlier version of this gate set a floor per defense - "suppress the
# parametric rate by at least 2pp" - and that was the wrong test. On clean
# data COIECD's parametric rate is about 7%, so there is almost nothing to
# suppress; its suppression appears under attack, where that rate triples.
# A floor chosen that way tests a condition the method does not claim.
#
# Reproduction is the right test and it is also the honest one: the port has
# to put the same numbers on the board as the script it replaces, within the
# resolution of the run. Tolerance is that run's own minimum detectable
# change, so the gate cannot demand precision the sample size cannot deliver.
REPRODUCE = {
    "coiecd": ("coiecd_vs_corpus_poisoning.json",
               {"base_rag": "base_rag", "coiecd": "coiecd"}),
    "acd": ("acd_vs_corpus_poisoning.json",
            {"rag": "rag", "closedbook": "closedbook", "acd": "acd"}),
    "scr": ("scr_vs_corpus_poisoning.json",
            {"rag": "rag", "closedbook": "closedbook", "scr": "scr"}),
    "dyprag": ("dyprag_vs_corpus_poisoning.json",
               {"rag": "rag", "closedbook": "closedbook", "dyprag": "dyprag"}),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--defense", required=True, choices=sorted(REPRODUCE))
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--model", default="NousResearch/Meta-Llama-3-8B-Instruct")
    ap.add_argument("--max_context_chars", type=int, default=2000,
                    help="the frozen item set the reproduced runs used")
    a = ap.parse_args()

    import defenses
    # ck.py imports vllm and never uses it, and eval_NQ imports ck. Every
    # runner in this cell stubs it rather than installing a serving stack.
    if "vllm" not in sys.modules:
        import types
        _st = types.ModuleType("vllm")
        _st.LLM = _st.SamplingParams = None
        sys.modules["vllm"] = _st
    import eval_NQ as CKEVAL                     # CK-PLUG's scorer, as the runs use

    allrows = [json.loads(l) for l in DATA.open()]
    # The runs being reproduced all filter to contexts of at most 2000
    # characters and then take the first n. Comparing against an unfiltered
    # slice is not a reproduction test: it is a different item set, and every
    # arm shifts together without the port being wrong.
    kept = [r for r in allrows if len(r["context"]) <= a.max_context_chars]
    rows = kept[:a.n]
    print(f"  {len(allrows)} items, {len(kept)} within "
          f"{a.max_context_chars} chars, using {len(rows)}")
    print(f"{a.defense}: {len(rows)} items, clean dose, {DATA.name}")

    # ACD prompts few-shot, and a shot drawn from the evaluation slice would
    # leak the answer. Their runner takes them from just past the slice, so
    # this does too.
    kw = {}
    if a.defense == "acd":
        shots = kept[a.n:a.n + 5]
        if len(shots) < 5:
            raise SystemExit("not enough held-out items for ACD's few-shots")
        kw["shots"] = shots
    d = defenses.load(a.defense, a.model, **kw)

    preds = {arm: [] for arm in d.arms}
    golds, params = [], []
    for i, r in enumerate(rows, 1):
        gold = r["answers"][0] if isinstance(r["answers"], list) else r["answers"]
        out = d.answer(r["question"], [r["context"]], gold=gold)
        for arm in d.arms:
            preds[arm].append(out[arm])
        golds.append(r["answers"])
        params.append(r["parametric_answer"])
        if i % 20 == 0:
            print(f"  {i}/{len(rows)}", flush=True)

    res = {}
    for arm in d.arms:
        _, ctx = CKEVAL.get_score(preds[arm], golds)
        _, pm = CKEVAL.get_score(preds[arm], params)
        res[arm] = {"n": len(rows), "ctx_acc": round(ctx, 2),
                    "pm_acc": round(pm, 2)}
        print(f"  {arm:12} ctx_acc {ctx:6.2f}   pm_acc {pm:6.2f}")

    fn, armmap = REPRODUCE[a.defense]
    prior = json.loads((REPO / "data" / "registries" / fn).read_text())
    clean = {r["arm"]: r for r in prior["results"] if r["frac"] == 0.0}
    mdr = prior.get("mdr_pp_at_n")
    from transfer_stats import min_detectable_change
    if mdr is None:
        mdr = min_detectable_change(len(rows), 0.5)
    # The recorded tolerance belongs to the recorded run's sample size. Ours
    # may be smaller, and then our own estimate is the looser of the two: a
    # gate run at n=2 against a tolerance computed at n=400 would pass
    # anything. Take the larger, and say so when ours is the binding one.
    ours_mdr = min_detectable_change(len(rows), 0.5)
    if ours_mdr > mdr + 0.01:
        print(f"  NOTE: this run's n={len(rows)} resolves only "
              f"{ours_mdr:.1f}pp, looser than the recorded {mdr}pp. "
              "Using the looser figure; re-run larger for a real verdict.")
        mdr = ours_mdr

    print(f"\n  reproducing {fn}, clean dose, tolerance {mdr:.1f}pp")
    worst, ok = 0.0, True
    for ours, theirs in armmap.items():
        if theirs not in clean or ours not in res:
            print(f"  {ours:12} MISSING from one side")
            ok = False
            continue
        d = res[ours]["ctx_acc"] - clean[theirs]["ctx_acc"]
        worst = max(worst, abs(d))
        flag = "" if abs(d) <= mdr else "   <- outside tolerance"
        ok = ok and abs(d) <= mdr
        print(f"  {ours:12} ours {res[ours]['ctx_acc']:6.2f}   "
              f"recorded {clean[theirs]['ctx_acc']:6.2f}   {d:+6.2f}{flag}")
    verdict = "PASS" if ok else "FAIL"
    print(f"\n  largest difference {worst:.2f}pp against {mdr:.1f}pp -> {verdict}")
    e = {"reproduces": fn, "tolerance_pp": mdr}
    delta = worst

    out = REPO / "data" / "registries" / f"control_gate_{a.defense}.json"
    out.write_text(json.dumps(
        {"defense": a.defense, "n": len(rows), "dose": "clean",
         "data": DATA.name, "model": a.model, "arms": res,
         "expectation": e, "delta": round(delta, 2), "verdict": verdict},
        indent=1))
    print(f"\nwrote {out.relative_to(REPO)}")
    if verdict == "FAIL":
        print("Gate failed: this defense reports no transfer number until the "
              "port reproduces its own published benefit.")


if __name__ == "__main__":
    main()

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

# What each port has to reproduce, and where the number comes from. These are
# directions and floors, not point estimates: the gate asks whether the method
# still does its own job, not whether it matches to a decimal.
EXPECT = {
    "coiecd": dict(
        arm="coiecd", against="base_rag", metric="pm_acc", direction="below",
        floor=2.0,
        why="COIECD suppresses the parametric answer; on clean data its own "
            "run cut pm_acc while leaving accuracy flat. Accuracy is NOT the "
            "gate, because inert-on-accuracy is its published behaviour."),
    "acd": dict(
        arm="acd", against="closedbook", metric="ctx_acc", direction="above",
        floor=20.0,
        why="ACD read the clean document well: +53.5pp over answering with no "
            "document at all. A port that lost the context would show up here."),
    "scr": dict(
        arm="scr", against="closedbook", metric="ctx_acc", direction="above",
        floor=20.0,
        why="SCR scored +41.2pp over closed-book on clean context, which is "
            "what shows it reads the document rather than abstaining."),
    "dyprag": dict(
        arm="dyprag", against="closedbook", metric="ctx_acc", direction="above",
        floor=5.0,
        why="DyPRAG claims to improve RAG. In our own runs it did not separate "
            "from the closed-book arm, so this gate is EXPECTED TO FAIL; a "
            "pass would mean the port reads passages its own script did not."),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--defense", required=True, choices=sorted(EXPECT))
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--model", default="NousResearch/Meta-Llama-3-8B-Instruct")
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
    rows = allrows[:a.n]
    print(f"{a.defense}: {len(rows)} items, clean dose, {DATA.name}")

    # ACD prompts few-shot, and a shot drawn from the evaluation slice would
    # leak the answer. Their runner takes them from just past the slice, so
    # this does too.
    kw = {}
    if a.defense == "acd":
        shots = allrows[a.n:a.n + 5]
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

    e = EXPECT[a.defense]
    delta = res[e["arm"]][e["metric"]] - res[e["against"]][e["metric"]]

    # A gate that cannot resolve the effect it tests for will fail a good
    # port. Same rule we apply to the experiments, applied to ourselves:
    # report the smallest difference this n can see, and refuse to call a
    # FAIL when the floor sits under it.
    from transfer_stats import min_detectable_change
    base_rate = res[e["against"]][e["metric"]] / 100 or 0.5
    mdr = min_detectable_change(len(rows), base_rate)
    print(f"\n  gate power: at n={len(rows)} and a base rate of "
          f"{100*base_rate:.1f}%, the smallest resolvable difference is "
          f"{mdr:.1f}pp")
    ok = delta >= e["floor"] if e["direction"] == "above" else delta <= -e["floor"]
    if not ok and e["floor"] < mdr:
        verdict = "UNDERPOWERED"
    else:
        verdict = "PASS" if ok else "FAIL"
    print(f"\n  {e['arm']} vs {e['against']} on {e['metric']}: {delta:+.2f}"
          f"  (needs {e['direction']} {e['floor']})  -> {verdict}")
    print(f"  {e['why']}")

    out = REPO / "data" / "registries" / f"control_gate_{a.defense}.json"
    out.write_text(json.dumps(
        {"defense": a.defense, "n": len(rows), "dose": "clean",
         "data": DATA.name, "model": a.model, "arms": res,
         "expectation": e, "delta": round(delta, 2), "verdict": verdict},
        indent=1))
    print(f"\nwrote {out.relative_to(REPO)}")
    if verdict == "UNDERPOWERED":
        print(f"Not a verdict: the floor of {e['floor']}pp is under this "
              f"run's {mdr:.1f}pp resolution. Re-run with a larger --n "
              "before concluding anything about the port.")
    elif verdict == "FAIL":
        print("Gate failed: this defense reports no transfer number until the "
              "port reproduces its own published benefit.")


if __name__ == "__main__":
    main()

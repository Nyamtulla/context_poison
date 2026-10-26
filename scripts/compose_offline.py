"""Compose two published defenses that cannot share a Python environment.

Section 9 recommends putting a method that keeps bad text out in front of a
method that reasons about the text that survives, and says nobody has run it.
This runs it, with one constraint that shapes the whole design: ACD's released
decoder and RobustRAG's harness need different `transformers` versions, which
Section 7 already reports as a finding. They cannot be composed inside one
process without modifying one of them, and modifying a method is the one thing
the reconstruction standard forbids.

So each method runs unmodified, alone, and dumps its answer per item. This
joins the two dumps and scores three composed arms:

  agree      answer only when both methods give the same answer, else abstain.
             Quorum across an attacker-controlled window plus a reasoning-stage
             check: the attacker has to defeat both to be believed.
  filter     take the isolate-then-aggregate answer when the two disagree,
             on the reading that the ingestion-stage signal is the one the
             attacker does not control.
  reason     take the reasoning-stage answer when they disagree, the mirror
             of `filter`, reported so the comparison is not cherry-picked.

Abstention is scored, not hidden: a composed arm that answers less often is
not automatically better, and Section 8b already treats abstention as an axis
rather than a cost.

Out: data/registries/composition_<a>_<b>_<attack>.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from transfer_stats import min_detectable_change, wilson      # noqa: E402


def acc(pred, gold):
    g = gold if isinstance(gold, list) else [gold]
    p = str(pred).lower()
    return int(any(str(x).lower() in p for x in g))


def index(path, arm_filter=None):
    """question -> dose -> prediction, for one method's dump."""
    d = json.loads(pathlib.Path(path).read_text())
    out = {}
    for r in d["predictions"]:
        if arm_filter is not None and r.get("arm") not in (arm_filter, None):
            continue
        if r.get("defended") is False:
            continue                      # the undefended arm is not a method
        out.setdefault(r["question"], {})[r["n_poison"]] = r
    return d, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="first dump (ingestion stage)")
    ap.add_argument("--b", required=True, help="second dump (reasoning stage)")
    ap.add_argument("--a_arm", default=None)
    ap.add_argument("--b_arm", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    da, A = index(args.a, args.a_arm)
    db, B = index(args.b, args.b_arm)
    shared = sorted(set(A) & set(B))
    if not shared:
        raise SystemExit("the two dumps share no questions; check --a_arm/--b_arm")
    doses = sorted({z for q in shared for z in A[q] if z in B[q]})

    rows = []
    for z in doses:
        qs = [q for q in shared if z in A[q] and z in B[q]]
        n = len(qs)
        tally = {k: 0 for k in ("agree", "filter", "reason", "abstain",
                                "a_only", "b_only")}
        for q in qs:
            ra, rb = A[q][z], B[q][z]
            gold = ra["gold"]
            same = str(ra["pred"]).strip().lower() == str(rb["pred"]).strip().lower()
            tally["a_only"] += acc(ra["pred"], gold)
            tally["b_only"] += acc(rb["pred"], gold)
            if same:
                tally["agree"] += acc(ra["pred"], gold)
                tally["filter"] += acc(ra["pred"], gold)
                tally["reason"] += acc(rb["pred"], gold)
            else:
                tally["abstain"] += 1
                tally["filter"] += acc(ra["pred"], gold)
                tally["reason"] += acc(rb["pred"], gold)
        for arm in ("a_only", "b_only", "agree", "filter", "reason"):
            lo, hi = wilson(tally[arm], n)
            rows.append({"n_poison": z, "arm": arm, "n": n,
                         "acc": round(100 * tally[arm] / n, 2),
                         "ci_low": lo, "ci_high": hi,
                         "abstain_rate": round(100 * tally["abstain"] / n, 2)
                         if arm == "agree" else None})

    out = args.out or (f"data/registries/composition_"
                       f"{da['defense']}_{db['defense']}_{da['attack']}.json")
    (REPO / out).write_text(json.dumps({
        "generated_by": "scripts/compose_offline.py",
        "a": da["defense"], "b": db["defense"], "attack": da["attack"],
        "note": "Each method ran unmodified and alone; the two cannot share a "
                "Python environment. 'agree' abstains on disagreement, so its "
                "accuracy and its abstention rate must be read together.",
        "n": len(shared),
        "mdr_pp_at_n": round(min_detectable_change(len(shared), 0.5), 1),
        "results": rows}, indent=1) + "\n")
    print(f"wrote {out}: {len(shared)} shared items, doses {doses}")
    for r in rows:
        if r["arm"] == "agree":
            print(f"  dose {r['n_poison']:>2}  agree acc {r['acc']:5.1f}%  "
                  f"abstained {r['abstain_rate']:5.1f}%")


if __name__ == "__main__":
    main()

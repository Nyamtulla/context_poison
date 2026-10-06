#!/usr/bin/env python3
"""Merge a base transfer registry with its crossover registry and print the
full dose-response curve.

The base runs sample poison at 0,1,5,9,10 - enough to show whether a defense
survives, not enough to show *where* it stops surviving. The crossover runs
fill 7 and 8. Read together they answer a question neither answers alone:
is the saturation collapse a cliff at 10/10, or a slope that starts earlier?

Resolvable deltas are marked with *. A delta below the minimum detectable
change for that n is noise and is left unmarked, whatever its sign.
"""
import json, sys, pathlib

REG = pathlib.Path(__file__).resolve().parent.parent / "data" / "registries"


def load(stem):
    rows, mdr, n = {}, None, None
    for suffix in ("", "_crossover"):
        f = REG / f"{stem}{suffix}.json"
        if not f.exists():
            continue
        d = json.load(open(f))
        mdr = mdr or d.get("mdr_pp_at_n")
        n = n or d.get("n")
        for r in d["results"]:
            rows[(r["arm"], r["n_poison"])] = r
    return rows, mdr, n


def curve(stem, metric="acc", label=None):
    rows, mdr, n = load(stem)
    if not rows:
        return
    levels = sorted({k[1] for k in rows})
    print(f"\n### {label or stem}   (n={n}, mdr {mdr} pp)")
    print(f"{'poison':>7}{'undefended':>12}{'defended':>11}{'delta':>9}")
    for p in levels:
        u, d = rows.get(("undefended", p)), rows.get(("defended", p))
        if not (u and d):
            continue
        delta = d[metric] - u[metric]
        star = "*" if mdr and abs(delta) >= mdr else " "
        print(f"{p:>5}/10{u[metric]:>11.1f}%{d[metric]:>10.1f}%{delta:>+8.1f}{star}")


if __name__ == "__main__":
    metric = sys.argv[1] if len(sys.argv) > 1 else "acc"
    print(f"metric: {metric}   (* = clears minimum detectable change)")
    for stem, label in (("poisonedrag_parammute", "ParamMute x PoisonedRAG"),
                        ("badrag_dos_parammute", "ParamMute x BadRAG DoS"),
                        ("badrag_dos_ckplug", "CK-PLUG x BadRAG DoS"),
                        ("poisonedrag_ckplug", "CK-PLUG x PoisonedRAG"),
                        ("badrag_sentiment_ckplug", "CK-PLUG x BadRAG sentiment"),
                        ("badrag_sentiment_parammute", "ParamMute x BadRAG sentiment"),
                        ("poisonedrag_robustrag", "RobustRAG/keyword x PoisonedRAG"),
                        ("badrag_dos_robustrag", "RobustRAG/keyword x BadRAG DoS"),
                        ("badrag_sentiment_robustrag", "RobustRAG/keyword x BadRAG sentiment"),
                        ("badrag_sentiment_robustrag_decoding", "RobustRAG/decoding x BadRAG sentiment")):
        curve(stem, metric, label)

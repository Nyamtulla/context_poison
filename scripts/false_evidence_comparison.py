"""Three context-reliance defenses, two payload classes, one table each.

Every defense here was already measured against corpus poisoning. This script
re-reads those runs and the matching false-evidence runs and prints the
comparison the write-up quotes. Nothing is hand-copied.

The comparison is only legitimate because each run carries its own undefended
arm over the same items at the same doses with the same scorer. We never
compare a defended number across attacks directly -- only each defense against
the control that sat beside it in the same run.

Two payload classes:
  corpus_poisoning  an optimised, incoherent token sequence (the reconstructed
                    gradient-based adversarial passage)
  false_evidence    CoConflictQA's per-item `parametric_evidencde` - a fluent
                    sentence asserting the model's own prior (wrong) answer

Harm metric: the clean -> saturation collapse. A defense is harmful when it
loses MORE than the undefended arm it is supposed to protect.
"""
import json
import pathlib
import sys

from scipy.stats import fisher_exact

REPO = pathlib.Path(__file__).resolve().parent.parent
REG = REPO / "data" / "registries"

# label, undefended arm, defended arm
DEFENSES = [
    ("ParamMute", "base", "parammute"),
    ("CK-PLUG", "base_rag", "ck"),
    ("COIECD", "base_rag", "coiecd"),
]
FRACS = [0.0, 0.1, 0.5, 1.0]


def load(stem, attack):
    p = REG / f"{stem}_vs_{attack}.json"
    if not p.exists():
        return None, None
    d = json.loads(p.read_text())
    return {(r["arm"], r["frac"]): r for r in d["results"]}, d


def delta_p(d, undef, deff, frac, n):
    b, c = d[(undef, frac)], d[(deff, frac)]
    kb, kc = round(b["ctx_acc"] * n / 100), round(c["ctx_acc"] * n / 100)
    _, pv = fisher_exact([[kc, n - kc], [kb, n - kb]])
    return b["ctx_acc"], c["ctx_acc"], c["ctx_acc"] - b["ctx_acc"], pv


def main():
    for label, undef, deff in DEFENSES:
        stem = label.lower().replace("-", "")
        cp, mcp = load(stem, "corpus_poisoning")
        fe, mfe = load(stem, "false_evidence")
        if cp is None or fe is None:
            print(f"### {label}: MISSING RUN "
                  f"(corpus_poisoning={cp is not None}, false_evidence={fe is not None})\n")
            continue
        if mcp["n"] != mfe["n"]:
            print(f"!!! {label}: n differs ({mcp['n']} vs {mfe['n']}) - not comparable\n")
        n, mdr = mcp["n"], mcp["mdr_pp_at_n"]

        print(f"### {label}  (n={n}, mdr={mdr} pp)")
        print(f"payload fp: corpus_poisoning={mcp.get('payload_fingerprint','(pre-fingerprinting)')}  "
              f"false_evidence={mfe.get('payload_fingerprint')}")
        print()
        print("| dose | CP undef | CP def | CP delta | CP p | FE undef | FE def | FE delta | FE p |")
        print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
        for f in FRACS:
            row = [f"| {int(f*100)}% "]
            for d in (cp, fe):
                b, c, dl, pv = delta_p(d, undef, deff, f, n)
                star = "**" if abs(dl) >= mdr else ""
                row.append(f"| {b:.1f} | {c:.1f} | {star}{dl:+.1f}{star} | {pv:.3f} ")
            print("".join(row) + "|")
        print()

        print("| metric | corpus poisoning | false evidence |")
        print("|---|---:|---:|")
        for metric, lab in [("ctx_acc", "clean->saturation collapse"),
                            ("pm_acc", "parametric-answer suppression at saturation"),
                            ("mr", "memorisation-rate shift at saturation")]:
            cells = []
            for d in (cp, fe):
                if metric == "ctx_acc":
                    bu = d[(undef, 0.0)]["ctx_acc"] - d[(undef, 1.0)]["ctx_acc"]
                    bd = d[(deff, 0.0)]["ctx_acc"] - d[(deff, 1.0)]["ctx_acc"]
                    cells.append(f"undef −{bu:.1f}, def −{bd:.1f} → **excess {bd-bu:+.1f} pp**")
                else:
                    b = d[(undef, 1.0)][metric]; c = d[(deff, 1.0)][metric]
                    cells.append(f"{b:.1f} → {c:.1f} ({c-b:+.1f} pp)")
            print(f"| {lab} | {cells[0]} | {cells[1]} |")
        print("\n**bold** = clears the minimum detectable change\n")


if __name__ == "__main__":
    sys.exit(main())

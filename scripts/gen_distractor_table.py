"""Generate the conservation table from the distractor registries.

The table was typed by hand with four defenses. SCR and SpARE landed later,
and the project rule is that a table of numbers is prose, so it is built
from the registries instead.

"memory" is pm_acc, "copied" is dist_acc, "correct" is ctx_acc. Those three
outcomes are disjoint by construction, which is what licenses summing the
deltas: the residual column is how much mass leaves the partition
altogether.

Do not use `mr` here. It is memory RELIANCE, pm/(pm+ctx), a ratio rather
than a share of the sample, so it does not belong to the partition and
summing it against dist_acc produces a cancellation that means nothing.

SpARE is kept in a block of its own. Its distractor run ships no undefended
arm, so its row compares its two steering directions and is not a
defended-minus-undefended delta like the rest.

Out: latex/tables/distractor.tex
"""
from __future__ import annotations

import json
import pathlib

from scipy.stats import fisher_exact

REPO = pathlib.Path(__file__).resolve().parent.parent
REG = REPO / "data" / "registries"
OUT = REPO / "latex" / "tables" / "distractor.tex"

# defense -> (file, defended arm, baseline arm)
RUNS = [
    ("ParamMute", "parammute_vs_distractor_evidence.json", "parammute", "base"),
    ("CK-PLUG", "ckplug_vs_distractor_evidence.json", "ck", "base_rag"),
    ("COIECD", "coiecd_vs_distractor_evidence.json", "coiecd", "base_rag"),
    ("ACD", "acd_vs_distractor_evidence.json", "acd", "rag"),
    ("SCR", "scr_vs_distractor_evidence.json", "scr", "rag"),
]
SPARE = ("SpARE", "spare_vs_distractor_evidence.json",
         "steer_to_use_parameter", "steer_to_use_context")
METRICS = ("pm_acc", "dist_acc", "ctx_acc")


def row(name, fn, d_arm, b_arm):
    doc = json.loads((REG / fn).read_text())
    mdr = doc["mdr_pp_at_n"]
    sat = {r["arm"]: r for r in doc["results"] if r["frac"] == 1.0}
    d, b = sat[d_arm], sat[b_arm]
    n = d["n"]
    cells, deltas = [], []
    for k in METRICS:
        delta = d[k] - b[k]
        kd, kb = round(d[k] * n / 100), round(b[k] * n / 100)
        _, p = fisher_exact([[kd, n - kd], [kb, n - kb]])
        star = "^{*}" if (abs(delta) >= mdr and p < 0.05) else ""
        cells.append(f"${delta:+.1f}{star}$")
        deltas.append(delta)
    resid = deltas[0] + deltas[1]
    return name, n, cells, resid


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    body = []
    for name, fn, d_arm, b_arm in RUNS:
        nm, n, cells, resid = row(name, fn, d_arm, b_arm)
        body.append(f"{nm:9s} & {n:4d} & " + " & ".join(cells)
                    + f" & ${resid:+.1f}$ \\\\")
        print(f"  {nm:10s} n={n:4d}  " + "  ".join(c.strip('$') for c in cells)
              + f"  residual {resid:+.1f}")
    nm, n, cells, resid = row(*SPARE)
    spare_row = (f"{nm}$^{{\\dagger}}$ & {n:4d} & " + " & ".join(cells)
                 + f" & ${resid:+.1f}$ \\\\")
    print(f"  {nm:10s} n={n:4d}  " + "  ".join(c.strip('$') for c in cells)
          + f"  residual {resid:+.1f}  (steering comparison, not undefended)")

    OUT.write_text(r"""\begin{table}[t]
\centering
\caption{Context-reliance defenses against the distractor payload, at
saturation. Memory is the parametric-answer rate, copied is the planted
answer, correct is the gold answer; the three are disjoint, so the residual
is mass that leaves the partition altogether. $*$ clears both the run's
detectability threshold and Fisher at $p<0.05$.}
\label{tab:distractor}
\small
\begin{tabular}{@{}lrrrrr@{}}
\toprule
defense & $n$ & memory & copied & correct & residual \\
\midrule
""" + "\n".join(body) + r"""
\midrule
""" + spare_row + r"""
\bottomrule
\end{tabular}
\\[2pt]
{\footnotesize $^{\dagger}$SpARE's run carries no undefended arm, so its row
compares steering toward memory against steering toward the context. It is
not a defended-minus-undefended delta and does not belong in the same column
of judgement as the rows above.}
\end{table}
""")
    print(f"wrote {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()

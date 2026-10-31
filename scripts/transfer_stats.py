"""Shared statistics and attack-payload helpers for the transfer experiments.

Deliberately dependency-free. These used to live in
`corpus_poisoning_vs_robustrag.py`, which meant importing them pulled in
RobustRAG's whole module tree (spacy, its defense classes) - fine inside the
RobustRAG venv, fatal inside FaithfulRAG's. Each defense reconstruction gets
its own environment on purpose, so anything shared between them has to import
nothing but the standard library.
"""
from __future__ import annotations

import json
import math
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
ADV_PASSAGE_FILE = REPO / "data" / "registries" / "corpus_poisoning_adv_passage_k1.json"


def adversarial_text() -> str:
    """The corpus-poisoning attack's own optimised passage, rendered to text.

    The attack optimises token ids, so rendering to a string and letting a
    different tokenizer re-tokenise it does not round-trip exactly. That only
    affects retrieval, which is measured separately in
    `corpus_poisoning_harness/attack_reconstruction.md`; the defense
    experiments start from the passage already being in the context.
    """
    tokens = json.loads(ADV_PASSAGE_FILE.read_text())["dummy"]
    return " ".join(tokens).replace(" ##", "")


def wilson(k: int, n: int) -> tuple[float, float]:
    """Wilson score interval - behaves at the extremes where normal-approx doesn't."""
    if n == 0:
        return (0.0, 0.0)
    p, z = k / n, 1.959963985
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def min_detectable_change(n: int, p: float) -> float:
    """Smallest change resolvable at n, alpha=.05, power=.80, in points.

    The gate every transfer verdict in this project runs through. Without it a
    defense that does nothing and a defense we cannot measure look identical.
    """
    z_a, z_b = 1.959963985, 0.8416212336
    p = min(max(p, 0.01), 0.99)
    return (z_a + z_b) * math.sqrt(2 * p * (1 - p) / n) * 100


def fisher_exact_p(k1: int, n1: int, k2: int, n2: int) -> float:
    """Two-sided Fisher exact p for a 2x2 of successes over trials.

    The four p-values in the ACD payload-class table were typed into the
    LaTeX by hand, which is the thing this project does not do with any
    number the corpus or a run produces. They are recomputed from the arm
    counts instead, and this is the test that recomputes them.

    Two-sided by the usual convention: sum the probability of every table at
    least as extreme as the observed one, where "as extreme" is measured by
    the table's own hypergeometric probability.
    """
    a, b, c, d = k1, n1 - k1, k2, n2 - k2
    row1, row2 = a + b, c + d
    col1, n = a + c, n1 + n2

    def prob(x):
        return (math.comb(row1, x) * math.comb(row2, col1 - x)
                / math.comb(n, col1))

    lo = max(0, col1 - row2)
    hi = min(col1, row1)
    obs = prob(a)
    # A strict > would drop tables of exactly equal probability, which for a
    # symmetric table is the mirror of the observed one and belongs in the
    # sum. The tolerance is what scipy uses for the same reason.
    tot = sum(p for x in range(lo, hi + 1)
              if (p := prob(x)) <= obs * (1 + 1e-7))
    return min(1.0, tot)

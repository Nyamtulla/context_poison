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

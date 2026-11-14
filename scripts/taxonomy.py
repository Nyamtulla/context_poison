"""The taxonomy's axis values, in one place.

These lists lived in three generators independently and drifted twice:
availability-loss was added to gen_paper_numbers.py and not to the figure
scripts, so every figure keyed on the consequence axis silently dropped a
column and the entries coded to it disappeared from the cube. A list that
has to be "kept identical" by hand will not be.

resource-abuse was merged into availability-loss on 2026-10-24. The two
named one harm between them -- the agent does not deliver its work -- and
split it by who gains rather than by what goes wrong: resource-abuse was
the victim paying for compute, quota or money, availability-loss was the
task not finishing. Under the classical reading, resource exhaustion is an
availability harm, so availability-loss already subsumed it; what it did
not have was a definition wide enough to say so. One registry entry carried
resource-abuse and no defense had ever been proposed against it.

The merge is applied here rather than in the raw coding files, so the
original per-paper judgments stay on disk as the coding record and the
collapse is one documented decision.

Three consequences were renamed on 2026-11-12, because their names assumed
an attacker while their definitions do not: goal-hijack -> goal-deviation
("pursuing an objective it was not given", which covers both an attacker
substituting the goal and the goal drifting without one),
data-exfiltration -> information-disclosure (STRIDE's term for the harm),
and persistence-backdoor -> persistent-corruption (persistence is a MITRE
ATT&CK tactic; a backdoor implies someone planted it). The definitions are
unchanged, so no entry is recoded; who caused the harm stays on the cause
axis. Like the merge, the rename is applied here and the raw files keep the
old values.
"""
from __future__ import annotations

CHANNELS = ["direct-input", "tool-output", "RAG", "memory", "multi-agent",
            "cross-modal", "tool-metadata", "skill", "supply-chain"]

CONSEQ = ["goal-deviation", "reasoning-corruption", "silent-corruption",
          "information-disclosure", "persistent-corruption", "availability-loss"]

REGIMES = ["security", "safety"]

# raw coding value -> the axis value it now belongs to
MERGED = {"resource-abuse": "availability-loss",
          "goal-hijack": "goal-deviation",
          "data-exfiltration": "information-disclosure",
          "persistence-backdoor": "persistent-corruption"}


def canon_consequence(q):
    """Map a raw consequence to its current axis value.

    Returns the value unchanged when it is already current, and None when it
    is not a recognised consequence at all, so a caller can tell a merged
    value apart from a typo instead of dropping both on the floor.
    """
    q = (q or "").strip()
    q = MERGED.get(q, q)
    return q if q in CONSEQ else None

"""The fix proposed for both regimes: count sources, not passages.

Given each retrieved passage's own answer (answered in isolation), the fix
groups passages that give the same answer, merges passages within a group
that share their specifics (the names, numbers and dates other than the
answer) into one source, and returns the answer with the most sources. Ties go
to the highest-ranked passage. Passages that answer "I don't know" are left
out. It uses no model memory and reports no conflict.

Every setting is frozen from Phase 0, which chose them on the tuning half of
the stale-document items only; nothing here is tuned on what Phase 1 reports.
Pure Python, so the live runner and any offline re-scoring run the same code.
"""
from __future__ import annotations

import re

SPECIFICS_JACCARD = 0.4          # frozen in Phase 0e (merge chosen on dev)
STOP = {"the", "a", "an", "dr"}


def norm(a: str) -> str:
    a = re.sub(r"[^\w\s]", " ", a.lower())
    return " ".join(w for w in a.split() if w not in STOP)


def is_idk(a: str) -> bool:
    a = a.lower()
    return not norm(a) or ("know" in a and ("don't" in a or "do not" in a))


def same(a: str, b: str) -> bool:
    na, nb = norm(a), norm(b)
    return bool(na and nb) and (na in nb or nb in na)


def groups(responses):
    """Answer group per passage (None for "I don't know"), and one
    representative answer per group. Answers group when one contains the
    other after normalization."""
    reps, gid = [], []
    for r in responses:
        if is_idk(r):
            gid.append(None)
            continue
        for k, rep in enumerate(reps):
            if same(r, rep):
                gid.append(k)
                break
        else:
            reps.append(r)
            gid.append(len(reps) - 1)
    return gid, reps


def specifics(passage: str, answer: str) -> set:
    """Capitalized words and numbers in a passage, minus the answer's words."""
    drop = set(norm(answer).split())
    toks = re.findall(r"\b(?:[A-Z][\w'-]+|\d[\d,.]*)\b", passage)
    return {t.lower() for t in toks if t.lower() not in drop}


def sources(passages, responses, gid):
    """Source id per passage: within one answer group, passages that are
    identical or share specifics (Jaccard >= SPECIFICS_JACCARD) are one source."""
    n = len(passages)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    spec = [specifics(passages[i], responses[i]) for i in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if gid[i] is None or gid[i] != gid[j]:
                continue
            a, b = spec[i], spec[j]
            if passages[i] == passages[j] or len(a & b) / max(1, len(a | b)) >= SPECIFICS_JACCARD:
                parent[find(i)] = find(j)
    return [find(i) for i in range(n)]


def decide(passages, responses):
    """The fix's answer and a trace of how it got there."""
    gid, reps = groups(responses)
    src = sources(passages, responses, gid)
    support = {}
    for i, g in enumerate(gid):
        if g is not None:
            support.setdefault(g, set()).add(src[i])
    support = {g: len(s) for g, s in support.items()}
    if not support:
        return "I don't know", {"groups": gid, "sources": src, "support": {}}
    best = max(support.values())
    win = next(g for g in gid if g is not None and support[g] == best)
    return reps[win], {"groups": gid, "sources": src,
                       "support": {reps[g]: s for g, s in support.items()}}

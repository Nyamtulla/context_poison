"""Item selection and context construction shared by every open-NQ runner.

RobustRAG's runner selected its items inline. The second-direction defenses
(ReliabilityRAG, AttnTrace, the detectors, spotlighting) run in other
environments and other processes, and a comparison across them is only fair if
every one of them answers the same question from the same passages. So the
selection lives here, once, and `build_contexts` writes the passages each
(item, failure, dose) gets to a file every runner reads.

Three of the mechanisms cannot be built for every item, and each is dropped on
its own test rather than on a shared one, because the tests fail on different
items: a clean donor is available for all of them, a stale passage for 80%, a
locatable gold passage for 83%. Every drop is reported rather than silently
shrinking n.
"""
from __future__ import annotations

import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
RRAG = REPO / "third_party" / "RobustRAG"


def source_path(attack: str) -> pathlib.Path:
    # The ML/AI arm runs on the same open_nq items with a distractor passage
    # precomputed by scripts/build_open_nq_distractor.py. Same harness, same
    # dosing; only the payload's intent differs.
    return (REPO / "data" / "payloads" / "open_nq_distractor.json"
            if attack == "distractor_evidence"
            else RRAG / "data" / "open_nq.json")


def select_items(attack: str, n: int, top_k: int, poison_counts):
    """The items a cell runs on, and how many were dropped and why."""
    import poisonedrag_transfer as pr
    src = source_path(attack)
    full = json.loads(src.read_text())
    data = full[:n]
    if attack in ("misretrieval", "context_dilution"):
        # The donor pool is the item set itself.
        pr.set_misretrieval_pool(full)
        # context_dilution draws up to max(doses) distinct donors per item,
        # so it has to be viable at the deepest dose, not just at one.
        deep = max(poison_counts) if attack == "context_dilution" else 1
        keep = [it for it in data
                if all(pr.borrowed_passage(it, salt=k) is not None
                       for k in range(deep))]
    elif attack == "incidental_stale":
        import regime_test as rt
        keep = [it for it in data if rt.stale_passage(it, top_k) is not None]
    elif attack == "lost_in_the_middle":
        # Half the window, not a constant: an item needs a decisive passage
        # to move and enough non-decisive ones to bury it among, and "enough"
        # scales with how deep the window is. The mechanism is invisible at
        # top-k 10 -- a pilot put every position inside 2.7 points, against a
        # detectable change of 15.8 -- so the cell that tests it runs deeper,
        # which is the range the effect was first reported in.
        keep = [it for it in data
                if 1 <= len(pr.gold_slots(it, top_k)) <= top_k // 2]
    else:
        keep = data
    if len(keep) != len(data):
        print(f"  {attack}: {len(data) - len(keep)} of {len(data)} "
              "items cannot carry this mechanism and are dropped", flush=True)
    return keep


def target_answer(it, attack: str):
    """What counts as the attacked outcome: the planted answer."""
    # for the ML arm that is the distractor, not PoisonedRAG's adversarial
    # target.
    return (it["distractor_answer"] if attack == "distractor_evidence"
            else it.get("incorrect answer"))


def build_contexts(attack: str, n: int, top_k: int, poison_counts):
    """Every context a runner needs, as plain data any environment can read."""
    import poisonedrag_transfer as pr
    items = select_items(attack, n, top_k, poison_counts)
    rows = []
    for idx, it in enumerate(items):
        row = {"idx": idx, "question": it["question"],
               "gold": it["correct answer"],
               "target": target_answer(it, attack),
               "contexts": {}}
        for j in poison_counts:
            row["contexts"][str(j)] = pr.build_poisoned(it, top_k, j,
                                                        attack=attack)
        rows.append(row)
    return rows

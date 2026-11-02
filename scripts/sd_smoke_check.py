"""Decide whether the second-direction smoke tests earned the full runs.

Mechanical checks only -- each smoke cell finished, carries every arm at every
dose, and produced real answers -- plus the controls each defense owes before
its result on someone else's problem means anything:

  * DataSentinel flags the injected control text and passes the clean one.
  * ReliabilityRAG and AttnTrace are reported against PoisonedRAG, their own
    papers' attack. That result is printed, not gated on: the pre-registered
    rule is that a defense which cannot stop its own attack is reported as
    such, and the honest-failure cells are still worth running to show it.

Exit 0 lets the queue start the full runs.
"""
from __future__ import annotations

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
REG = REPO / "data" / "registries"
SMOKE = ["spotlighting", "piguard", "datasentinel", "reliabilityrag", "attntrace"]


def cell_ok(path, doses):
    if not path.exists():
        return f"missing {path.name}"
    d = json.loads(path.read_text())
    arms = {(r["arm"], r["n_poison"]) for r in d["results"]}
    want = {(a, j) for a in ("closedbook", "undefended", "defended") for j in doses}
    if not want <= arms:
        return f"{path.name}: missing arms {sorted(want - arms)}"
    return None


def preds_ok(log):
    if not log.exists():
        return f"missing {log.name}"
    rows = [json.loads(l) for l in log.read_text().splitlines() if l.strip()]
    empty = [r for r in rows if not r["pred"].strip()]
    if empty:
        return f"{log.name}: {len(empty)} empty answers"
    if len({r["pred"] for r in rows if r["arm"] != "closedbook"}) < 2:
        return f"{log.name}: every answer identical"
    return None


def main():
    bad = []
    for d in SMOKE:
        bad.append(cell_ok(REG / f"smoke_native_{d}_incidental_stale.json",
                           [0, 1, 5]))
        model = {"attntrace": "qwen2.5-7b"}.get(d, "mistral7b")
        bad.append(preds_ok(REPO / "data" / "sd_logs" /
                            f"smoke_{d}_incidental_stale_{model}.jsonl"))
    ds = REPO / "data" / "sd_queue" / "datasentinel_smoke.log"
    txt = ds.read_text() if ds.exists() else ""
    ctl = [l for l in txt.splitlines() if l.strip().startswith("control")]
    if len(ctl) != 2 or "flag=0" not in ctl[0] or "flag=1" not in ctl[1]:
        bad.append(f"DataSentinel controls not as expected: {ctl}")
    for d in ("reliabilityrag", "attntrace"):
        p = REG / f"control_native_{d}_poisonedrag.json"
        if not p.exists():
            bad.append(f"missing {p.name}")
            continue
        r = {(x["arm"], x["n_poison"]): x for x in json.loads(p.read_text())["results"]}
        u, f = r[("undefended", 1)], r[("defended", 1)]
        print(f"  control {d:15s} PoisonedRAG 1/10: planted answer "
              f"{u['asr']:.0f}% undefended -> {f['asr']:.0f}% defended; "
              f"accuracy {u['acc']:.0f}% -> {f['acc']:.0f}%")
    bad = [b for b in bad if b]
    for b in bad:
        print("  FAIL", b)
    print("smoke check:", "PASS" if not bad else f"{len(bad)} failure(s)")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())

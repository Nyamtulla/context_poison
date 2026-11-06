"""Apply the supply-chain scope ruling of 2026-11-05 to the registries.

The supply-chain channel is defined as content that a third-party component
the agent depends on -- a package or tool it installs, a template shipped with
the model, a service on the response path -- inserts into the context at run
time. Section 2 puts training-time poisoning and weight attacks outside context
poisoning, and a full-text check of all ten supply-chain entries found four
that are exactly that. They are removed; one more is recoded to the channel
its in-scope part acts on. Every ruling is written to
data/registries/scope_rulings.json with its reason, so the cut is visible.

Idempotent: an entry already removed or recoded is reported and skipped.

    python3 scripts/apply_scope_rulings.py
"""
from __future__ import annotations

import datetime
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
REG = REPO / "data" / "registries"

# (registry, paper_id, entry name, action, reason)
RULINGS = [
    ("rq3_pollution_registry.json", "37665dd5ae7245f087d663785c17eef068578676",
     "Virtual Prompt Injection (VPI)", "drop",
     "Poisons instruction-tuning data: a training-time attack, outside "
     "context poisoning by Section 2's definition."),
    ("rq3_pollution_registry.json", None, "PoisonedAlign", "drop",
     "Poisons alignment data so the model obeys injections more readily: "
     "training-time."),
    ("rq3_pollution_registry.json", None,
     "UNNAMED: backdoor-based RAG data extraction attack", "drop",
     "Fine-tunes a backdoor into the model to leak retrieved data: "
     "training-time."),
    ("rq4_defense_registry.json", "98b790d195d775ee82c42fd596d588a792c6eab3",
     None, "drop",
     "Detects that an API model's weights were changed; no content enters the "
     "context, so it is a weight-level fix."),
    ("rq4_defense_registry.json", "cce1b13eebe88e5051d329a95616c9df646fb08c",
     "Unified Security Orchestration Framework (USOF)",
     {"channel": "direct-input"},
     "Its supply-chain component (MISCV) targets poisoned model weights, "
     "BadNets-style: weight-level. Its in-scope part screens prompt-injected "
     "input, so the entry moves to direct-input."),
]


def name_of(e):
    return e.get("technique_name") or e.get("defense_name") or e.get("name") or ""


def matches(e, pid, name):
    return ((pid is None or e.get("paper_id") == pid)
            and (name is None or name_of(e) == name))


def main():
    log_path = REG / "scope_rulings.json"
    log = json.loads(log_path.read_text()) if log_path.exists() else {"rulings": []}
    stamp = f"{datetime.date.today()}"
    for fn in sorted({r[0] for r in RULINGS}):
        path = REG / fn
        reg = json.loads(path.read_text())
        before = len(reg)
        for f, pid, name, action, why in RULINGS:
            if f != fn:
                continue
            hit = [e for e in reg if matches(e, pid, name)
                   and (action == "drop" or e.get("channel") == "supply-chain")]
            if len(hit) > 1:
                raise SystemExit(f"{fn}: {name or pid} matches {len(hit)} entries")
            if not hit:
                print(f"  [skip] {name or pid}: already applied")
                continue
            e = hit[0]
            rec = {"date": stamp, "registry": fn, "paper_id": e.get("paper_id"),
                   "row": e.get("row"), "name": name_of(e),
                   "channel_was": e.get("channel"),
                   "consequence": e.get("consequence"), "reason": why}
            if action == "drop":
                reg.remove(e)
                rec["action"] = "removed"
            else:
                e.update(action)
                e["notes"] = (e.get("notes") or "") + f" [scope ruling {stamp}: {why}]"
                rec["action"] = f"recoded to {action}"
            log["rulings"].append(rec)
            print(f"  [{rec['action']}] {rec['name'][:60]}")
        path.write_text(json.dumps(reg, indent=1) + "\n")   # the registries' own format
        print(f"{fn}: {before} -> {len(reg)} entries")
    log["definition"] = ("supply-chain: content that a third-party component "
                         "the agent depends on (a package or tool it installs, "
                         "a template shipped with the model, a service on the "
                         "response path) inserts into the context at run time.")
    log_path.write_text(json.dumps(log, indent=1) + "\n")


if __name__ == "__main__":
    main()

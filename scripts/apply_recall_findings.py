"""Add what the recall pass found, under the self-built-adversary rule.

The recall pass re-reads papers that contributed no named technique and asks
whether we missed one. Three verdicts came back from the first batch, and
they need three different answers. The rule, settled 2026-10-22:

1. A genuine omission is registered. Plan-of-Thought Backdoor Attack, named
   and formally defined inside Agent Security Bench, is one.

2. A technique already in the registry under another name is NOT registered
   again. Outer Prompt Extension is a prompt-wrapper defense and
   `Spotlighting (delimiting / datamarking / encoding)` is already there.
   Registering it would inflate the census and manufacture a pair.

3. An attack a DEFENSE paper built for its own evaluation is registered, and
   flagged `internal_to_defense_paper`. This is the case the rule exists for.
   Leaving it out understates the census; letting it pair freely would let a
   defense claim coverage against an attack its own authors wrote, which is
   the laundering the coverage result exists to detect. So it is counted and
   it cannot pair with a defense from the same paper.

The flag is the whole point: without it, rule 3 collapses into rule 1 and
every defense paper can manufacture its own coverage.
"""
import csv, datetime, json, pathlib, shutil

REG = pathlib.Path(__file__).resolve().parent.parent / "data" / "registries"
DUPLICATE_OF = {
    # batch 1: a prompt-wrapper defense already present under its usual name
    "Outer Prompt Extension (OPE)":
        "Spotlighting (delimiting / datamarking / encoding)",
    # batch 2: coined for long-context degradation, which the registry
    # already carries three times as "context rot", plus "lost in the
    # middle" and a context-accumulation entry. The coining paper is a
    # serverless cost/latency benchmark; a new label on a known mechanism
    # is not a new mechanism.
    "Context Fatigue": "context rot",
}
INTERNAL = {"Actor-Critic attack"}

# 4. A payload FORM is not a technique. We refuse to register our own
#    distractor and adaptive-distractor payloads as attacks, because they are
#    instruments rather than techniques, and the same rule has to hold for
#    other people's. Rubric-Isomorphic Payloads is a way of shaping an
#    indirect injection so it parses as the reviewer's expected JSON; the
#    15 attacks it is carried by are borrowed from cited prior work.
# Matched on a prefix, because the registry name and the decision CSV spell
# the same thing differently ("... (DSAAP)" vs the expanded protocol name).
NOT_A_TECHNIQUE = {
    "Rubric-Isomorphic Payloads":
        "a payload form, not a technique; its attacks are borrowed",
}


def main():
    # Only batches whose agent has finished. An in-progress CSV is written
    # incrementally, so globbing blindly registers a partial result: that
    # happened once, adding an entry from a batch still running. A batch is
    # complete when its row count matches its export.
    dec = []
    for f in sorted((REG / "raw").glob("recheck_decisions_batch*.csv")):
        n = f.name.replace("recheck_decisions_batch", "").replace(".csv", "")
        src = REG / "raw" / f"recheck_batch{n}.json"
        rows = list(csv.DictReader(open(f)))
        want = len(json.loads(src.read_text())) if src.exists() else None
        if want is not None and len(rows) < want:
            print(f"  SKIPPING batch {n}: {len(rows)} of {want} rows, "
                  f"still running")
            continue
        dec += [d for d in rows if d["verdict"] != "none"]
    r3p = REG / "rq3_pollution_registry.json"
    r3 = json.loads(r3p.read_text())
    have = {(e.get("technique_name") or e.get("name") or "").strip() for e in r3}

    added, skipped = [], []
    for d in dec:
        name = d["name"].strip()
        _form = next((k for k in NOT_A_TECHNIQUE if name.startswith(k)), None)
        if _form:
            skipped.append((name, NOT_A_TECHNIQUE[_form]))
            continue
        if name in DUPLICATE_OF:
            skipped.append((name, f"already registered as {DUPLICATE_OF[name]}"))
            continue
        if d["verdict"] not in ("mechanism", "both"):
            skipped.append((name, f"verdict {d['verdict']}, not a mechanism"))
            continue
        if name in have:
            skipped.append((name, "already in the registry"))
            continue
        e = {"paper_id": d["paper_id"], "title": d["title"],
             "technique_name": name, "name": name,
             "channel": d["channel"], "consequence": d["consequence"],
             "track": "Security", "confidence": d["confidence"],
             "has_technique": True, "is_extension_of": "",
             "notes": d["notes"] + " [added by the recall pass, 2026-10-22]",
             "evidence_quote": d["evidence_quote"]}
        if name in INTERNAL:
            e["internal_to_defense_paper"] = True
            e["notes"] += (" Built by a defense paper for its own evaluation: "
                           "counted in the census, barred from pairing with a "
                           "defense from the same paper.")
        r3.append(e)
        added.append(name)

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copy(r3p, r3p.with_suffix(f".backup-recall-{stamp}.json"))
    r3p.write_text(json.dumps(r3, indent=1))
    for n in added:
        print(f"  added    {n}")
    for n, why in skipped:
        print(f"  skipped  {n}  ({why})")
    print(f"\nrq3 registry: {len(r3)} entries")


if __name__ == "__main__":
    main()

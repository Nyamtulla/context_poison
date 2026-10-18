"""Assign every named defense to a family, and refuse to guess.

Section~3.4 of the paper needs a taxonomy OF DEFENSES, which the corpus does
not come with. The registry records each defense's intervention point and
track, but "ingestion" holds both a prompt-injection firewall and a KV-cache
compactor, which are not the same kind of thing and do not fail in the same
way. The family is the missing axis.

**Families are derived, not invented.** Each one below was read off the
registry's own names and notes (see `defense_families.md` for the sampling
that produced them), and each carries the assumption it makes about the
attacker. That last field is the point of the whole exercise: it tells a
machine learning reader what their fix silently assumes, and tells a security
reader which machine learning method is worth hardening rather than
re-deriving.

**Three disciplines, each learned from a bug in this repo:**

  * **The family is decided by the defense's own name and notes, never by its
    track.** An earlier backfill set a field from the paper it appeared in and
    put five security attacks on the ML/AI track. Track is an input to nothing
    here; it is reported alongside so disagreements stay visible.
  * **A tie is not a decision.** If two families match equally well the entry
    is listed as ambiguous and waits for a human. Silently taking the first
    match is how a keyword scan got `validated_against` wrong on 3 of 13
    entries once already.
  * **The recorded intervention point is a CHECK, not a decider.** Where the
    family's stage disagrees with the registry's stage, we print it rather
    than overriding either. Those rows are where the taxonomy is actually
    being tested.

Out: data/registries/defense_families.json, plus a report on stdout listing
every entry a human still has to rule on.
"""
from __future__ import annotations

import collections
import json
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parent.parent
SRC = REPO / "data" / "registries" / "rq4_defense_registry.json"
OUT = REPO / "data" / "registries" / "defense_families.json"

# slug, label, stage, expected track, what it assumes about the attacker,
# patterns. Patterns match against name + notes, lowercased.
FAMILIES = [
 ("detect_filter", "Detect-and-filter", "ingestion", "Security",
  "an adversary exists and is detectable at the boundary",
  [r"\bdetect", r"\bdetector\b", r"\bclassifier\b", r"\bguard(rail)?\b",
   r"\bfirewall\b", r"\bscanner\b", r"\bfilter", r"\bsanitiz|sanitis",
   r"\bmoderation\b", r"\bblock ?list\b", r"\bperplexity\b",
   r"\bscreen(ing)?\b", r"\bflag(ging)? (malicious|injected)"]),

 ("structural_separation", "Structural separation", "ingestion", "Security",
  "data and instructions can be kept in separate channels",
  [r"\bstructured quer", r"\bdelimit", r"\bboundary\b", r"\bspotlight",
   r"\bsegment embedding", r"\bdata[- ]instruction\b", r"\bencod(e|ing) the",
   r"\bmark(ing|up)\b", r"\btag(ging)?\b", r"\bseparat(e|ion) of (data|the)",
   r"\bisolat(e|ing) untrusted (text|content)"]),

 ("context_management", "Context management", "ingestion", "ML/AI",
  "content is abundant, not hostile; no adversary is modelled",
  [r"\bcompress", r"\bcompact", r"\bsummari[sz]", r"\bpaging\b", r"\bprun",
   r"\bcontext window\b", r"\btoken budget\b", r"\bkv[- ]?cache\b",
   r"\bre[- ]?rank", r"\bchunk", r"\bdistillation\b", r"\bselection of (the )?context",
   r"\bcontext engineering\b", r"\bretriev(al|e) quality\b"]),

 ("instruction_integrity", "Instruction integrity", "reasoning", "Security",
  "the user's task is known and deviation from it is observable",
  [r"\binstruction hierarch", r"\btask align", r"\btask[- ]drift\b",
   r"\bcontrol[- ]flow\b", r"\bintent\b", r"\bplan(ning)? integrit",
   r"\bre[- ]?execution\b", r"\battention track", r"\btask shield\b",
   r"\bgoal (consistency|integrity)", r"\bprompt injection.*(resist|defen[sc])"]),

 ("belief_arbitration", "Belief arbitration", "reasoning", "ML/AI",
  "conflict is accidental, so trust between sources can be re-weighted",
  [r"\bdecoding\b", r"\bcontrastive\b", r"\bentropy\b", r"\bconfidence\b",
   r"\bcalibrat", r"\bsteering\b", r"\bactivation\b", r"\blogit",
   r"\bknowledge conflict\b", r"\bfaithful", r"\bparametric\b",
   r"\bcontext[- ]faithful", r"\bre[- ]?weight", r"\battention (re)?alloc"]),

 ("memory_architecture", "Memory architecture", "reasoning", "ML/AI",
  "memory degrades on its own; it is not planted",
  [r"\bmemory\b", r"\bepisodic\b", r"\blong[- ]term (memory|store)",
   r"\bforget(ting)?\b", r"\bconsolidat", r"\bexperience (replay|store)",
   r"\bsession (history|memory)\b"]),

 ("capability_control", "Capability control", "execution", "Security",
  "containment beats detection; assume some payload gets through",
  [r"\bisolat", r"\bsandbox", r"\bprivilege\b", r"\bpermission",
   r"\bprovenance\b", r"\bsign(ing|ature)\b", r"\bcapabilit",
   r"\bmonitor\b", r"\baudit", r"\bleast[- ]privilege\b", r"\btaint\b",
   r"\bpolicy enforcement\b", r"\bconfirmation\b", r"\bseparation of (duty|role)"]),
]


def score(text):
    """Distinct patterns each family matches. Distinct, so a family does not
    win by repeating one word that happens to appear five times in a note."""
    out = {}
    for slug, _, _, _, _, pats in FAMILIES:
        n = sum(1 for p in pats if re.search(p, text))
        if n:
            out[slug] = n
    return out


def main():
    d = json.loads(SRC.read_text())
    rows = d if isinstance(d, list) else (d.get("entries") or d.get("defenses"))
    meta = {f[0]: {"label": f[1], "stage": f[2], "expected_track": f[3],
                   "assumes": f[4]} for f in FAMILIES}

    assigned, ambiguous, unassigned = [], [], []
    for r in rows:
        text = f"{r.get('defense_name') or ''} {r.get('notes') or ''}".lower()
        s = score(text)
        if not s:
            unassigned.append(r)
            continue
        top = max(s.values())
        winners = [k for k, v in s.items() if v == top]
        if len(winners) > 1:
            ambiguous.append((r, {k: s[k] for k in winners}))
            continue
        fam = winners[0]
        runner = sorted((v for k, v in s.items() if k != fam), reverse=True)
        assigned.append({
            "row": r.get("row"), "defense_name": r.get("defense_name"),
            "family": fam, "family_stage": meta[fam]["stage"],
            "registry_stage": r.get("defense_intervention_point"),
            "track": r.get("track"),
            "validated_against": r.get("validated_against"),
            "margin": top - (runner[0] if runner else 0),
            "matched": top})

    stage_clash = [a for a in assigned
                   if a["registry_stage"] not in (None, "", "none")
                   and a["registry_stage"] != a["family_stage"]]
    thin = [a for a in assigned if a["margin"] == 0 or a["matched"] == 1]

    OUT.write_text(json.dumps({
        "generated_from": SRC.name, "n_defenses": len(rows),
        "families": meta,
        "note": "family is decided by the defense's own name and notes. "
                "Track and intervention point are reported, never used to "
                "decide. Entries a human must still rule on are in "
                "`ambiguous` and `unassigned`.",
        "assigned": assigned,
        "ambiguous": [{"row": r.get("row"),
                       "defense_name": r.get("defense_name"),
                       "candidates": c} for r, c in ambiguous],
        "unassigned": [{"row": r.get("row"),
                        "defense_name": r.get("defense_name"),
                        "registry_stage": r.get("defense_intervention_point"),
                        "track": r.get("track")} for r in unassigned],
    }, indent=1) + "\n")

    print(f"{len(rows)} defenses\n")
    print(f"  assigned   {len(assigned):>4}")
    print(f"  ambiguous  {len(ambiguous):>4}   (tie between families)")
    print(f"  unassigned {len(unassigned):>4}   (no pattern matched)\n")
    print("=== family x track ===")
    c = collections.Counter((a["family"], a["track"]) for a in assigned)
    for slug, label, stage, exp, _, _ in FAMILIES:
        tot = sum(v for (f, _), v in c.items() if f == slug)
        split = ", ".join(f"{t} {v}" for (f, t), v in
                          sorted(c.items(), key=lambda kv: -kv[1]) if f == slug)
        print(f"  {label:<24} {stage:<10} n={tot:<4} {split}")
    print(f"\n=== {len(stage_clash)} assigned to a stage the registry disagrees with ===")
    for a in stage_clash[:15]:
        print(f"  {str(a['defense_name'])[:46]:<48} family={a['family_stage']:<10} "
              f"registry={a['registry_stage']}")
    if len(stage_clash) > 15:
        print(f"  ... and {len(stage_clash)-15} more")
    print(f"\n=== {len(thin)} assigned on a single pattern or a zero margin ===")
    print("    (these are the ones to read before trusting the table)")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()

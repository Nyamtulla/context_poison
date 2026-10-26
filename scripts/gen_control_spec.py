"""The control gate's inputs, half of which a machine can derive and half of
which it cannot.

Section 7.3's first pre-registered rule turns on whether a defense reproduces
its OWN published benefit in our harness. Assembling the evidence for that rule
needs four things per defense, and only two of them live in this repository:

  derivable   which run is the reconstruction, which arm is the baseline that
              defense is measured against, and what benefit we actually got on
              clean context
  not here    what benefit the defense's own paper reports, against which
              baseline, and where to find that number

A first attempt at this table read the dose-protocol registries and a single
uniform baseline, and concluded that seven of eight defenses show no clean
benefit. Both halves of that were wrong. The paper's clean-context figures come
from the CHUNK-protocol runs, and the baseline differs per defense by design:
ParamMute is claimed against no defense at all, ACD against answering with no
document, SpARE against steering the other way. A table that picks one baseline
for everyone contradicts the paper and misrepresents the method.

So the mapping below is hand-written, not inferred, and the script validates it
against the four clean-context figures Section 8 states independently. If a
registry moves and the derivation stops reproducing those, this fails loudly
rather than emitting a plausible wrong number.

Out: data/registries/control_spec.json
"""
from __future__ import annotations

import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
R = REPO / "data" / "registries"
OUT = R / "control_spec.json"
PUB = R / "control_published.json"

# defense -> registry, how to pick the clean row, baseline arm, defended arm.
# "alt_baseline" is the second arm a defense may legitimately be claimed
# against: for a method whose point is whether to read a document at all, the
# no-document arm is the honest comparison, not the undefended-RAG arm.
SPEC = [
    {"defense": "ParamMute", "registry": "parammute_vs_corpus_poisoning.json",
     "clean": ("frac", 0.0), "baseline": "base", "defended": "parammute",
     "alt_baseline": None},
    {"defense": "CK-PLUG", "registry": "ckplug_vs_corpus_poisoning.json",
     "clean": ("frac", 0.0), "baseline": "base_rag", "defended": "ck",
     "alt_baseline": None},
    {"defense": "SpARE", "registry": "spare_vs_corpus_poisoning.json",
     "clean": ("frac", 0.0), "baseline": "steer_to_use_parameter",
     "defended": "steer_to_use_context", "alt_baseline": None},
    {"defense": "COIECD", "registry": "coiecd_vs_corpus_poisoning.json",
     "clean": ("frac", 0.0), "baseline": "base_rag", "defended": "coiecd",
     "alt_baseline": None},
    {"defense": "ACD", "registry": "acd_vs_corpus_poisoning.json",
     "clean": ("frac", 0.0), "baseline": "rag", "defended": "acd",
     "alt_baseline": "closedbook"},
    {"defense": "SCR", "registry": "scr_vs_corpus_poisoning.json",
     "clean": ("frac", 0.0), "baseline": "rag", "defended": "scr",
     "alt_baseline": "closedbook"},
    {"defense": "DyPRAG", "registry": "dyprag_vs_corpus_poisoning.json",
     "clean": ("frac", 0.0), "baseline": "rag", "defended": "dyprag",
     "alt_baseline": "closedbook"},
    {"defense": "RobustRAG", "registry": "corpus_poisoning_vs_robustrag.json",
     "clean": ("condition", "clean (no attack)"), "baseline": "undefended",
     "defended": "RobustRAG", "alt_baseline": None},
]

# Clean-context figures Section 8 states in its own words. The derivation has
# to reproduce these or the mapping above is wrong.
CHECK = {"ParamMute": 9.3, "SpARE": 14.2, "CK-PLUG": -4.5}
CHECK_ALT = {"ACD": 53.5}


def clean_arms(reg, key, value):
    d = json.loads((R / reg).read_text())
    rows, out = d.get("results", []), {}
    for r in rows:
        if r.get(key) != value:
            continue
        arm = r.get("arm") or r.get("label")
        acc = r.get("ctx_acc", r.get("acc"))
        if arm is not None and acc is not None:
            out[arm] = acc
    return out, d.get("mdr_pp_at_n"), d.get("n")


def main():
    pub = json.loads(PUB.read_text())["defenses"] if PUB.exists() else {}
    entries, problems = [], []
    for s in SPEC:
        arms, mdr, n = clean_arms(s["registry"], *s["clean"])
        base, dfn = arms.get(s["baseline"]), arms.get(s["defended"])
        if base is None or dfn is None:
            problems.append(f"{s['defense']}: missing arm in {s['registry']} "
                            f"(have {sorted(arms)})")
            continue
        e = {
            "defense": s["defense"],
            "registry": s["registry"],
            "clean_selector": {s["clean"][0]: s["clean"][1]},
            "baseline_arm": s["baseline"],
            "defended_arm": s["defended"],
            "n": n,
            "mdr_pp": mdr,
            "baseline_acc": round(base, 2),
            "defended_acc": round(dfn, 2),
            "reconstructed_benefit_pp": round(dfn - base, 2),
            # everything below has to be read out of the defense's own paper
            "published_benefit_pp": pub.get(s["defense"], {}).get("benefit_pp"),
            "published_baseline": pub.get(s["defense"], {}).get("baseline"),
            "published_source": pub.get(s["defense"], {}).get("source"),
        }
        if s["alt_baseline"] and s["alt_baseline"] in arms:
            alt = arms[s["alt_baseline"]]
            e["alt_baseline_arm"] = s["alt_baseline"]
            e["alt_baseline_acc"] = round(alt, 2)
            e["reconstructed_benefit_vs_alt_pp"] = round(dfn - alt, 2)
        entries.append(e)

    by = {e["defense"]: e for e in entries}
    for d, want in CHECK.items():
        got = by.get(d, {}).get("reconstructed_benefit_pp")
        if got is None or abs(got - want) > 0.15:
            problems.append(f"{d}: derived {got}, Section 8 states {want}")
    for d, want in CHECK_ALT.items():
        got = by.get(d, {}).get("reconstructed_benefit_vs_alt_pp")
        if got is None or abs(got - want) > 0.15:
            problems.append(f"{d}: derived {got} vs alt baseline, "
                            f"Section 8 states {want}")
    if problems:
        raise SystemExit("control spec does not reproduce the paper:\n  "
                         + "\n  ".join(problems))

    OUT.write_text(json.dumps({
        "generated_by": "scripts/gen_control_spec.py",
        "purpose": "Inputs to the Section 7.3 control gate. The reconstructed "
                   "side is computed here; the published side must be read "
                   "out of each defense's paper into control_published.json.",
        "entries": entries,
    }, indent=1) + "\n")
    pending = [e["defense"] for e in entries
               if e["published_benefit_pp"] is None]
    print(f"wrote {OUT.relative_to(REPO)}: {len(entries)} defenses, "
          f"all {len(CHECK) + len(CHECK_ALT)} paper figures reproduced")
    print(f"  awaiting a published benefit ({len(pending)}): "
          + ", ".join(pending))


if __name__ == "__main__":
    main()

"""Which (defense, mechanism) transfer tests are actually constructible today?

The substrate census (evaluation_fragmentation.md) established that most of this
field's evaluation happens on ground nobody else stands on. The useful corollary
is the inverse: **where a shared substrate DOES exist, a transfer test is
constructible** -- the attack and the defense can both be run on it, so a
comparison means something.

This intersects the two sides:

    mechanisms -> substrates   from data/registries/substrate_census.json
    defenses   -> substrates   from data/registries/defense_eval_targets.json

and emits the pairs that (a) share a substrate and (b) have NOT been tested
together according to the RQ5 coverage matrix. Those are the transfer tests the
field could run tomorrow and has not.

Ranked so the most informative come first: shared substrate, both sides
independently validated on it, and no existing pair.

    python3 scripts/find_constructible_pairs.py
"""
from __future__ import annotations
import collections, json, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REG = REPO / "data/registries"
sys.path.insert(0, str(REPO))

# substrates that are genuinely runnable harnesses rather than raw corpora.
# A shared QA corpus is not enough: two papers both using HotpotQA still差 in
# attack construction, which is exactly why the census scored those `partial`.
RUNNABLE_HARNESS = {
    "agentdojo", "injecagent", "asb", "agent security bench", "bipia",
    "open-prompt-injection", "openpromptinjection", "cyberseceval",
    "advbench", "harmbench", "agentharm", "jailbreakbench", "tensor trust",
    "hackaprompt", "agentsafetybench", "toolemu", "r-judge", "sep", "pint",
    "notinject", "wasp", "taskTracker".lower(),
}


def norm(s: str) -> str:
    t = re.sub(r"\s+", " ", (s or "").strip())
    m = re.match(r"^(.*?)\s*\(([^)]{2,40})\)\s*$", t)
    if m:
        outer, inner = m.group(1).strip(), m.group(2).strip()
        t = inner if (inner.isupper() and len(inner) <= 12) else outer
    t = re.sub(r"\s+(benchmark|dataset|corpus|suite)$", "", t, flags=re.I).strip() or t
    k = t.lower()
    ALIAS = {"ms marco": "ms-marco", "nq": "natural questions",
             "injectagent": "injecagent", "agent dojo": "agentdojo",
             "agent security bench": "asb", "tensortrust": "tensor trust",
             "openpromptinjection": "open-prompt-injection"}
    return ALIAS.get(k, k)


def main() -> None:
    cen = json.loads((REG / "substrate_census.json").read_text())
    mech_sub = {}
    for r in cen["rows"]:
        subs = {norm(s) for s in (r.get("named_substrates") or []) if s}
        if subs:
            mech_sub[r["mechanism"]] = subs

    dets = json.loads((REG / "defense_eval_targets.json").read_text())
    def_sub = {}
    for d in dets:
        subs = {norm(s) for s in (d.get("eval_targets_named") or []) if s}
        if subs:
            def_sub[d["defense_name"]] = {"subs": subs, "stage": d.get("stage"),
                                          "track": d.get("track"),
                                          "paper": d.get("source_paper_title", "")}

    print(f"mechanisms with a named substrate: {len(mech_sub)}/{len(cen['rows'])}")
    print(f"defenses   with a named substrate: {len(def_sub)}/{len(dets)}")

    # existing tested pairs, to exclude
    from src import registry_source as rs
    pairs = rs.load_all()["pairs"]
    tested = {(p["defense_name"], p["mechanism_name"]) for p in pairs}
    print(f"already-tested pairs in RQ5: {len(tested)}")

    # substrate -> who uses it
    sub_mech = collections.defaultdict(set)
    for m, subs in mech_sub.items():
        for s in subs:
            sub_mech[s].add(m)
    sub_def = collections.defaultdict(set)
    for d, info in def_sub.items():
        for s in info["subs"]:
            sub_def[s].add(d)

    shared = sorted(set(sub_mech) & set(sub_def),
                    key=lambda s: -(len(sub_mech[s]) * len(sub_def[s])))
    print(f"\nsubstrates used by BOTH at least one attack and one defense: {len(shared)}")
    print(f"{'substrate':<28} {'attacks':>8} {'defenses':>9} {'cells':>7} {'runnable?':>10}")
    for s in shared[:18]:
        runnable = "YES" if s in RUNNABLE_HARNESS else "corpus only"
        print(f"  {s[:26]:<28} {len(sub_mech[s]):>6} {len(sub_def[s]):>9} "
              f"{len(sub_mech[s])*len(sub_def[s]):>7} {runnable:>10}")

    cands = []
    for s in shared:
        if s not in RUNNABLE_HARNESS:
            continue                       # corpus-sharing is not test-constructible
        for m in sub_mech[s]:
            for d in sub_def[s]:
                if (d, m) in tested:
                    continue
                cands.append({"substrate": s, "defense": d, "mechanism": m,
                              "defense_stage": def_sub[d]["stage"],
                              "defense_track": def_sub[d]["track"],
                              "defense_paper": def_sub[d]["paper"]})

    print(f"\nCONSTRUCTIBLE UNTESTED PAIRS (shared runnable harness, not in RQ5): {len(cands)}")
    bysub = collections.Counter(c["substrate"] for c in cands)
    for s, n in bysub.most_common():
        print(f"   {n:>5}  {s}")
    bystage = collections.Counter(c["defense_stage"] for c in cands)
    print(f"\n   by defense stage: {dict(bystage)}")

    out = REG / "constructible_pairs.json"
    out.write_text(json.dumps({
        "generated": "2026-09-23",
        "note": ("Pairs where a shared RUNNABLE harness exists for both the attack and the "
                 "defense, and RQ5 records no test between them. Corpus-only sharing "
                 "(HotpotQA, NQ, MMLU...) is excluded: two papers using the same corpus "
                 "still differ in attack construction, so a comparison is not constructible."),
        "n_pairs": len(cands),
        "by_substrate": dict(bysub),
        "pairs": cands,
    }, indent=1) + "\n")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()

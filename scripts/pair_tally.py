"""Regenerate every number in pair_tally.md from the registries.

The point of this script is that the pair counts in the manuscript are
reconciled rather than hand-copied. Three numbers here have been wrong in
drafts at least once (the 332 composite, the defense-universe size, and the
episode count), all because they were transcribed from an earlier run.

Run: python3 scripts/pair_tally.py
"""
import collections
import json
import pathlib

R = pathlib.Path(__file__).resolve().parent.parent / "data" / "registries"


def load(name):
    return json.loads((R / name).read_text())


def composite_pairs():
    """The 332. Four sources, deduplicated on (defense, attack).

    Sources 1/2/4 read defense papers; source 3 reads attack papers and is the
    only direction that can observe a defense losing to an attack published
    after it.
    """
    pairs, provenance = set(), collections.Counter()
    for m in load("rq5_coverage_matrix.json")["matches"]:
        pairs.add((m["defense_name"], m["mechanism_name"]))
        provenance["defense-paper read (RQ5 base)"] += 1
    for p in load("rq5_supplementary_pairs.json")["confirmed_pairs"]:
        pairs.add((p["defense"], p["mechanism"]))
        provenance["citation/full-text recovery"] += 1
    for p in load("benchmark_resolved_pairs.json")["confirmed_pairs"]:
        pairs.add((p["defense"], p["mechanism"]))
        provenance["benchmark-named resolution"] += 1
    for p in load("attack_paper_evaluations.json")["confirmed_pairs"]:
        pairs.add((p["defense"], p["mechanism"]))
        provenance["ATTACK-paper reverse scan (pass 1-2)"] += 1
    for p in load("attack_paper_evaluations_pass3.json")["confirmed_pairs"]:
        pairs.add((p["defense"], p["mechanism"]))
        provenance["ATTACK-paper reverse scan (pass 3)"] += 1
    return pairs, provenance


def attack_universe():
    """237 = 223 registry attacks + 14 that exist only inside a benchmark."""
    reg = load("rq3_pollution_registry.json")
    bench = load("rq3_benchmark_mechanisms.json")["mechanisms"]
    track = {m["name"]: m["track"] for m in reg}
    for b in bench:
        # benchmark-only entries are all adversarial suites
        track.setdefault(b.get("name") or b.get("technique_name"), "Security")
    return track


def main():
    pairs, provenance = composite_pairs()
    track = attack_universe()
    defenses = load("rq4_defense_registry.json")
    per_attack = collections.Counter(a for _, a in pairs)
    per_defense = collections.Counter(d for d, _ in pairs)

    print("== pair provenance ==")
    for k, v in provenance.items():
        print(f"  {v:>4}  {k}")
    print(f"  {sum(provenance.values()):>4}  raw    ->  {len(pairs)} unique")

    print("\n== the two threat models are separate problems ==")
    n_def = collections.Counter(d["validated_against"] for d in defenses)
    for label, va, tr in [("adversarial", "adversarial", "Security"),
                          ("incidental", "incidental", "ML/AI")]:
        targets = [n for n, t in track.items() if t == tr]
        covered = sum(1 for n in targets if per_attack.get(n, 0))
        print(f"  {label:12s} {n_def[va]:>4} defenses vs {len(targets):>4} targets "
              f"= {n_def[va]/len(targets):.1f}:1, {covered}/{len(targets)} "
              f"({covered/len(targets):.1%}) covered")
    print(f"  both         {n_def['both']:>4} defenses")

    print("\n== defenses tested against each attack ==")
    buckets = {"0": 0, "1": 0, "2": 0, "3-5": 0, "6-10": 0, "11+": 0}
    for name in track:
        c = per_attack.get(name, 0)
        key = ("0" if c == 0 else "1" if c == 1 else "2" if c == 2
               else "3-5" if c <= 5 else "6-10" if c <= 10 else "11+")
        buckets[key] += 1
    for k, v in buckets.items():
        print(f"  {k:>5}: {v:>4}")
    heavy = sum(v for v in per_attack.values() if v >= 11)
    print(f"  the 11+ attacks absorb {heavy}/{len(pairs)} pairs "
          f"({heavy/len(pairs):.1%})")
    print("  top:", per_attack.most_common(7))

    print("\n== attacks tested against each defense ==")
    universe = {d["name"] for d in defenses} | set(per_defense)
    hist = collections.Counter(per_defense.get(n, 0) for n in universe)
    print(f"  universe {len(universe)} (534 registry + strays)")
    for k in sorted(hist)[:6]:
        print(f"  {k:>5}: {hist[k]:>4}")
    print(f"    4+: {sum(v for k, v in hist.items() if k >= 4):>4}")

    print("\n== who reports what ==")
    outcomes = load("pair_outcomes.json")
    by_src = collections.defaultdict(collections.Counter)
    for o in outcomes:
        by_src[o["reported_by"]][o["reported_verdict"]] += 1
    for src, c in by_src.items():
        print(f"  {src:16s} n={sum(c.values()):>4}  "
              f"wins={c['defense_wins_claimed']:>4}  "
              f"loses={c['defense_loses_reported']:>4}")

    print("\n== what we ran ourselves ==")
    full = load("technique_transfer_full_banking.json")
    scored = [r for r in full["results"] if not r.get("error")]
    episodes = sum(r["undefended"]["n"] + r["defended"]["n"] for r in scored)
    print(f"  {len(scored)} scored conditions, {episodes} episodes, "
          f"{len(full['results']) - len(scored)} harness errors excluded")
    print(" ", collections.Counter(r["verdict"].split("(")[0].strip()
                                   for r in scored))
    transfer = sum(1 for r in scored if r.get("is_transfer_test"))
    print(f"  conditions against a zero-coverage attack: {transfer}")

    print("\n== reverse-scan freshness ==")
    p3 = load("attack_paper_evaluations_pass3.json")
    n_reg = len(load("rq3_pollution_registry.json"))
    rej = sum(len(v) for v in p3["rejected"].values())
    print(f"  pass 3 ({p3['generated']}) covered the full registry ({n_reg} + "
          f"benchmark-only)")
    print(f"  {p3['candidates_adjudicated']} adjudicated -> "
          f"{len(p3['confirmed_pairs'])} confirmed, {rej} rejected/pending")


if __name__ == "__main__":
    main()

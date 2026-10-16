"""When was each defense published, when was the attack it was tested on, and
did the two come from the same community?

The taxonomy answers *what* a method addresses. It never asked *when*, and the
year was sitting in every registry the whole time. This adds that axis and
writes `data/registries/pair_timeline.json`.

The question it exists to answer: **does a defense published by one community
already cover an attack published later by the other one?** If that happened
often, a defense proposed today for such an attack would be reinventing
something that exists, unnoticed because the two literatures do not read each
other. The answer turns out to be that the literature cannot say, because the
experiment is almost never run, which is what makes it ours to run.

Name resolution, because 58 of 349 pairs failed a naive exact match:

  * attacks resolve against the mechanism registry first, then against
    `rq3_benchmark_mechanisms.json` - the 14 attacks that exist only inside a
    benchmark harness (AgentDojo, InjecAgent, ASB) carry the benchmark paper's
    id, so they have a year like any other entry.
  * defenses resolve exactly, then by longest-prefix - the pair tables carry
    `PromptLocate` where the registry carries `PromptLocate (injected-prompt
    localization)`. Prefix matching is checked for ambiguity and refuses to
    guess between two candidates.

A pair that still cannot be dated is reported, never silently dropped: an
undated pair that vanishes would shrink the denominator and flatter every rate
computed from it.
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from src import registry_source          # noqa: E402
from pair_tally import composite_pairs   # noqa: E402

REG = REPO / "data" / "registries"


def norm(s) -> str:
    return (s or "").strip().lower()


def load(name):
    return json.loads((REG / name).read_text())


def _index(entries, namekeys, papers):
    """name -> {year, track, paper_id, title}, from the paper the entry cites."""
    out = {}
    for e in entries:
        nm = next((e.get(k) for k in namekeys if (e.get(k) or "").strip()), None)
        if not nm:
            continue
        p = papers.get(e.get("paper_id")) or {}
        year = p.get("year")
        out[norm(nm)] = {
            "name": nm.strip(),
            "year": int(year) if year else None,
            # the registry's own track wins; it was assigned per entry, while
            # the paper's track is per paper and a paper can carry both
            "track": (e.get("track") or p.get("track") or "").strip(),
            "paper_id": e.get("paper_id"),
            "title": p.get("title") or e.get("title"),
        }
    return out


def resolve(name, index):
    """Exact, then unambiguous longest prefix. Never guesses between two."""
    k = norm(name)
    if k in index:
        return index[k], "exact"
    cands = [v for kk, v in index.items() if kk.startswith(k) or k.startswith(kk)]
    if len(cands) == 1:
        return cands[0], "prefix"
    return None, "ambiguous" if cands else "missing"


def build():
    papers = {p["paper_id"]: p for p in registry_source.load_papers()}

    attacks = _index(load("rq3_pollution_registry.json"),
                     ("name", "technique_name", "mechanism_name"), papers)
    # the 14 that live only inside a benchmark harness
    attacks.update(_index(load("rq3_benchmark_mechanisms.json")["mechanisms"],
                          ("technique_name", "name"), papers))
    defenses = _index(load("rq4_defense_registry.json"),
                      ("defense_name", "name"), papers)

    pairs, _ = composite_pairs()
    rows, unresolved = [], []
    for d, a in sorted(pairs):
        D, dhow = resolve(d, defenses)
        A, ahow = resolve(a, attacks)
        if not (D and A and D["year"] and A["year"]):
            unresolved.append({"defense": d, "attack": a,
                               "defense_match": dhow, "attack_match": ahow,
                               "defense_year": (D or {}).get("year"),
                               "attack_year": (A or {}).get("year")})
            continue
        cross = bool(D["track"] and A["track"] and D["track"] != A["track"])
        rows.append({
            "defense": D["name"], "defense_year": D["year"],
            "defense_track": D["track"],
            "attack": A["name"], "attack_year": A["year"],
            "attack_track": A["track"],
            "gap_years": D["year"] - A["year"],
            "defense_predates_attack": D["year"] < A["year"],
            "cross_community": cross,
            "match": f"{dhow}/{ahow}",
        })
    return rows, unresolved


def report(rows, unresolved):
    n = len(rows)
    older = [r for r in rows if r["defense_predates_attack"]]
    cross = [r for r in rows if r["cross_community"]]
    both = [r for r in rows if r["defense_predates_attack"] and r["cross_community"]]
    print(f"\n== dated pairs: {n} ({len(unresolved)} could not be dated) ==")
    print(f"  defense predates the attack it was tested on : "
          f"{len(older):>3} ({100*len(older)/n:.1f}%)")
    print(f"  defense and attack from different communities: "
          f"{len(cross):>3} ({100*len(cross)/n:.1f}%)")
    print(f"  BOTH - the 'already covered elsewhere' cell  : "
          f"{len(both):>3} ({100*len(both)/n:.1f}%)")

    print("\n== who tests whom ==")
    m = collections.Counter((r["defense_track"], r["attack_track"]) for r in rows)
    tracks = sorted({t for r in rows for t in (r["defense_track"], r["attack_track"])})
    hdr = "defense vs attack"
    print(f"  {hdr:<22}" + "".join(f"{t:>12}" for t in tracks))
    for dt in tracks:
        print(f"  {dt:<22}" + "".join(f"{m.get((dt,at),0):>12}" for at in tracks))

    print("\n== lag, defense year minus attack year ==")
    g = collections.Counter(r["gap_years"] for r in rows)
    for k in sorted(g):
        bar = "#" * min(g[k], 60)
        print(f"  {k:>+3}y {g[k]:>4}  {bar}")

    if both:
        print("\n== the cross-community, defense-first pairs ==")
        for r in sorted(both, key=lambda x: x["gap_years"]):
            print(f"  {r['defense_track']:<9}{r['defense_year']} "
                  f"{r['defense'][:38]:<40} vs  "
                  f"{r['attack_track']:<9}{r['attack_year']} {r['attack'][:36]}")

    if unresolved:
        print(f"\n== {len(unresolved)} undated, kept out of every rate above ==")
        c = collections.Counter(u["defense_match"] + "/" + u["attack_match"]
                                for u in unresolved)
        for k, v in c.most_common():
            print(f"  {k:<22} {v}")


def main():
    rows, unresolved = build()
    report(rows, unresolved)
    out = {
        "generated": "2026-10-16",
        "purpose": "temporal and cross-community structure of every confirmed "
                   "(defense, attack) pair",
        "n_pairs_dated": len(rows),
        "n_pairs_undated": len(unresolved),
        "pairs": rows,
        "undated": unresolved,
    }
    (REG / "pair_timeline.json").write_text(json.dumps(out, indent=1))
    print(f"\nwrote data/registries/pair_timeline.json "
          f"({len(rows)} dated, {len(unresolved)} undated)")


if __name__ == "__main__":
    main()

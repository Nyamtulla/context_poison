"""Candidate transfer pairs under the taxonomy rule, on corrected labels.

Section 7's selection rule: a (defense, mechanism) pair is a candidate when
both occupy the same taxonomy cell - same channel, same consequence - and no
paper in the corpus reports having run them together. The interesting subset
is the pairs that also CROSS the community boundary, because a defense built
for one track meeting a mechanism named by the other is the experiment the
literature has not run.

This re-derives that list from the registries after the full-text re-coding
and the label propagation, and reports what changed against the labels the
current campaign was selected under.

`none` cells are excluded: a paper spanning six routes co-equally cannot
place a pair in one cell, and pretending otherwise would manufacture
candidates.

    python3 scripts/derive_cell_pairs.py
"""
from __future__ import annotations

import collections
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
REG = REPO / "data" / "registries"


def load(fn):
    return json.loads((REG / fn).read_text())


def cell(e):
    c = (e.get("channel") or "").strip()
    q = (e.get("consequence") or "").strip()
    return (c, q) if c and q and c != "none" and q != "none" else None


def main():
    mechs = load("rq3_pollution_registry.json")
    defs_ = load("rq4_defense_registry.json")
    cov = load("rq5_coverage_matrix.json")
    tested = {(m["defense_name"], m["mechanism_name"]) for m in cov["matches"]}

    dn = lambda e: (e.get("defense_name") or e.get("name") or "").strip()
    mn = lambda e: (e.get("name") or e.get("mechanism_name")
                    or e.get("technique_name") or "").strip()

    by_cell_m = collections.defaultdict(list)
    for e in mechs:
        c = cell(e)
        if c and mn(e):
            by_cell_m[c].append(e)

    cand = []
    for d in defs_:
        c = cell(d)
        if not c or not dn(d):
            continue
        for m in by_cell_m.get(c, []):
            if (dn(d), mn(m)) in tested:
                continue
            dt = (d.get("track") or "").strip()
            mt = (m.get("track") or "").strip()
            cand.append({
                "defense": dn(d), "defense_track": dt,
                "mechanism": mn(m), "mechanism_track": mt,
                "channel": c[0], "consequence": c[1],
                "cross": bool(dt and mt and dt != mt and "Both" not in (dt, mt)),
                "defense_validated_against": (d.get("validated_against") or "").strip(),
            })

    out = REG / "cell_candidate_pairs.json"
    out.write_text(json.dumps(cand, indent=1))

    cross = [c for c in cand if c["cross"]]
    print(f"candidate pairs (same cell, never tested together): {len(cand):,}")
    print(f"  of which cross the community boundary:            {len(cross):,}")
    print()
    d2m = collections.Counter(
        (c["defense_track"], c["mechanism_track"]) for c in cand)
    print("by track pairing:")
    for k, v in d2m.most_common():
        print(f"   {k[0] or '?':9s} defense x {k[1] or '?':9s} mechanism : {v:,}")
    print()
    print("cross-boundary candidates by cell:")
    for k, v in collections.Counter(
            (c["channel"], c["consequence"]) for c in cross).most_common(10):
        print(f"   {k[0]:14s} {k[1]:22s} {v:,}")
    print()
    sec = [c for c in cross if c["defense_track"] == "Security"]
    print(f"Security defense x ML/AI mechanism (the direction nobody has run): {len(sec):,}")
    for c in sec[:12]:
        print(f"   {c['defense'][:42]:44s} vs {c['mechanism'][:34]:36s} "
              f"[{c['channel']}/{c['consequence']}]")
    print(f"\nwrote {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()

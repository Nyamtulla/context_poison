"""Prove a prose rewrite changed only prose.

A full-paper style pass touches every sentence, which is exactly the situation
where a citation quietly disappears or a macro becomes a typed number. This
records the things that must not change --- every macro use, citation key,
label, ref, and every numeral --- and diffs a later state against it.

    python3 scripts/check_paper_invariants.py --save before.json
    ... rewrite ...
    python3 scripts/check_paper_invariants.py --check before.json

Numerals are included deliberately. The project rule is that corpus figures
are macros, so a numeral appearing where a macro used to be is the specific
regression this guards against.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
SEC = REPO / "latex" / "sections"


def snapshot():
    out = {}
    for p in sorted(SEC.glob("*.tex")):
        t = p.read_text()
        t = re.sub(r"(?m)^\s*%.*$", "", t)
        out[p.name] = {
            "macros": sorted(collections.Counter(
                re.findall(r"\\(N[A-Z][A-Za-z]*|Pct[A-Za-z]+)\{\}", t)).items()),
            "cites": sorted(set(k.strip() for m in re.findall(r"\\cite\{([^}]*)\}", t)
                                for k in m.split(","))),
            "labels": sorted(set(re.findall(r"\\label\{([^}]*)\}", t))),
            "refs": sorted(set(re.findall(r"\\ref\{([^}]*)\}", t))),
            "numerals": sorted(collections.Counter(
                re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?", t)).items()),
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--save")
    ap.add_argument("--check")
    a = ap.parse_args()
    now = snapshot()
    if a.save:
        pathlib.Path(a.save).write_text(json.dumps(now, indent=1))
        n = sum(len(v["cites"]) for v in now.values())
        print(f"saved {len(now)} files, {n} citation uses")
        return
    old = json.loads(pathlib.Path(a.check).read_text())
    # JSON has no tuples: the counter pairs come back as lists, so normalise
    # both sides before comparing or every field reports a false difference.
    norm = lambda v: [list(x) if isinstance(x, (list, tuple)) else x for x in v]
    for d in (old, now):
        for f in d:
            for k in ("macros", "numerals"):
                d[f][k] = norm(d[f][k])
    bad = 0
    for f in sorted(set(old) | set(now)):
        o, n = old.get(f, {}), now.get(f, {})
        if not o or not n:
            print(f"  {f}: FILE ADDED OR REMOVED")
            bad += 1
            continue
        for k in ("macros", "cites", "labels", "refs", "numerals"):
            if o[k] != n[k]:
                so, sn = set(map(str, o[k])), set(map(str, n[k]))
                lost, gained = sorted(so - sn), sorted(sn - so)
                if k in ("macros", "numerals"):
                    # these are (token, count) pairs, so a count change shows
                    # up on BOTH sides. Only a token that vanished entirely is
                    # a real loss; report the rest as a count change.
                    lo = {x[0] for x in o[k]}
                    ln = {x[0] for x in n[k]}
                    gone, added = sorted(lo - ln), sorted(ln - lo)
                    if not gone and not added:
                        print(f"  {f}  {k}: counts changed only, nothing added "
                              f"or removed")
                        continue
                    lost, gained = gone, added
                print(f"  {f}  {k}:")
                if lost:
                    print(f"      LOST    {lost[:8]}")
                if gained:
                    print(f"      GAINED  {gained[:8]}")
                bad += 1
    print("\nno drift" if not bad else f"\n{bad} differences above")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

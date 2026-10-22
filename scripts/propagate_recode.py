"""Push the full-text re-coded labels from paper rows into the registries.

The re-coding wrote to paper rows. The cube is computed over paper rows, but
pair selection, the coverage matrix and the transfer matrix all read the
REGISTRIES, which carry their own copies of channel/consequence/track. 543 of
550 rq4 entries held labels identical to their paper's, because both came
from the same title+abstract pass — so without this step a corrected cube
would sit on top of uncorrected pairing and the two would disagree.

Rules, in order:

1. An entry whose labels still match its paper's OLD labels is updated to the
   paper's NEW labels. That entry never had an independent judgement; it
   inherited one, and the inheritance was wrong.

2. An entry whose labels already differ from its paper's old labels is LEFT
   ALONE and reported. Someone made a separate call there and this pass has
   no standing to overrule it.

3. A `none` label is never propagated. `none` means the PAPER spans several
   routes co-equally - a survey - but a named mechanism or defense extracted
   from that paper usually does have one specific route. Writing `none` over
   it would destroy information rather than correct it.

Writes a timestamped backup of each registry before touching it.

Out: rewrites rq3_pollution_registry.json and rq4_defense_registry.json
"""
from __future__ import annotations

import csv
import collections
import glob
import json
import pathlib
import shutil
import time

REPO = pathlib.Path(__file__).resolve().parent.parent
REG = REPO / "data" / "registries"
RAW = REG / "raw"
AXES = ("channel", "consequence", "track")


def main():
    new, old = {}, {}
    for f in sorted(glob.glob(str(RAW / "recode_decisions_batch*.csv"))):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            new[r["paper_id"]] = {a: (r[a] or "").strip() for a in AXES}
    for f in glob.glob(str(RAW / "recode_batch*.json")):
        for e in json.loads(pathlib.Path(f).read_text()):
            old[e["paper_id"]] = {a: (e.get(f"current_{a}") or "").strip()
                                  for a in AXES}
    print(f"re-coded papers: {len(new)}")

    stamp = time.strftime("%Y%m%d-%H%M%S")
    tally = collections.Counter()
    for fn in ("rq3_pollution_registry.json", "rq4_defense_registry.json"):
        p = REG / fn
        ents = json.loads(p.read_text())
        shutil.copy(p, p.with_suffix(f".backup-{stamp}.json"))
        indep = []
        for e in ents:
            pid = str(e.get("paper_id"))
            if pid not in new:
                tally[f"{fn}: paper not re-coded"] += 1
                continue
            for a in AXES:
                if a not in e:
                    continue
                cur = (e.get(a) or "").strip()
                o, n = old.get(pid, {}).get(a, ""), new[pid][a]
                if not n or n == "none":
                    tally[f"{fn}: {a} new is none, skipped"] += 1
                elif cur == n:
                    tally[f"{fn}: {a} already correct"] += 1
                elif cur == o:
                    e[a] = n
                    tally[f"{fn}: {a} UPDATED"] += 1
                else:
                    indep.append((pid, a, cur, o, n))
                    tally[f"{fn}: {a} independent, left alone"] += 1
        p.write_text(json.dumps(ents, indent=1))
        print(f"\n{fn}: {len(ents)} entries, backup .backup-{stamp}.json")
        for pid, a, cur, o, n in indep[:12]:
            print(f"   LEFT  {pid[:10]} {a:12s} entry={cur!r} paper_old={o!r} paper_new={n!r}")
        if len(indep) > 12:
            print(f"   ... and {len(indep) - 12} more left alone")

    print()
    for k, v in sorted(tally.items()):
        print(f"  {k:52s} {v}")


if __name__ == "__main__":
    main()

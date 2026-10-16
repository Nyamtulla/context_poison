"""Re-derive the claim/evaluation mismatch set, correctly this time.

`mismatch-claim-vs-evaluation.csv` was built by searching each row's `notes`
for the substring `CLAIM/EVALUATION MISMATCH`. The screener's own convention
was to write that marker at the START of the note when the mismatch applies,
and to write "No CLAIM/EVALUATION MISMATCH ..." or "... NOT a CLAIM/EVALUATION
MISMATCH" when it explicitly does not. A substring search cannot tell those
apart, so every negated note was swept in.

Verified independently before writing this: of the 291 rows, 126 begin with the
marker, 3 carry it after a `DEFENSE-NAMES: ...` prefix, and the remaining 162
are negations - 137 ending in a bare "No", and 25 with longer phrasing ("Not
flagged as", "Not coded as a", "does NOT apply here"). Every one of the 162 was
checked by reading the text immediately before the marker. There are no
ambiguous cases.

**The screener's judgement was not the problem.** Its notes exclude these rows
correctly and say why. The derived CSV contradicted them, which is how a file
ended up containing 10 surveys, 8 position papers and 11 papers that were
removed from the corpus, all flagged as "evaluation measures only capability" -
surveys have no evaluation section at all.

Corrected count: **129 of 982 (13.1%)**, not 291 (30%). The finding survives at
less than half the headline size.

Writes `mismatch-claim-vs-evaluation-corrected.csv` beside the original and
leaves the original in place, so the inflated file stays auditable rather than
disappearing.
"""
from __future__ import annotations

import collections
import csv
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parent.parent
D = REPO / "data" / "exports" / "contribution_screen" / "bundles" / "screen-findings"
MARK = "CLAIM/EVALUATION MISMATCH"


def classify(notes: str) -> str:
    n = (notes or "").strip()
    i = n.find(MARK)
    if i < 0:
        return "absent"
    pre = n[:i].strip()
    if pre == "":
        return "genuine"
    # the screener prefixes some notes with the defense names it found before
    # getting to the marker; that is still a positive call
    if re.fullmatch(r"DEFENSE-NAMES:[^.]*\.", pre):
        return "genuine"
    # everything else must be a negation to be excluded, and we require the
    # evidence rather than assuming it: a negator in the trailing clause
    if re.search(r"\b(no|not|never|neither)\b[^.]{0,40}$", pre, re.I):
        return "negated"
    return "unclassified"


def main():
    src = D / "mismatch-claim-vs-evaluation.csv"
    with open(src, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
        fields = list(rows[0].keys())

    buckets = collections.defaultdict(list)
    for r in rows:
        buckets[classify(r.get("notes", ""))].append(r)

    for k in ("genuine", "negated", "unclassified", "absent"):
        print(f"  {len(buckets[k]):>4}  {k}")
    if buckets["unclassified"]:
        print("\n  UNCLASSIFIED - read these before trusting the count:")
        for r in buckets["unclassified"]:
            n = r["notes"]
            i = n.find(MARK)
            print(f"    p{r['packet']} r{r['row']}: ...{n[max(0,i-90):i+40]!r}")

    good = buckets["genuine"]
    out = D / "mismatch-claim-vs-evaluation-corrected.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(good)
    print(f"\nwrote {out.name}: {len(good)} rows "
          f"({100*len(good)/982:.1f}% of the 982-paper corpus)")

    print("\nper-packet density, recomputed (the README's figures came from "
          "the inflated file):")
    dens = collections.Counter(r["packet"] for r in good)
    old = collections.Counter(r["packet"] for r in rows)
    for p in sorted(old):
        print(f"  {p}: {dens.get(p,0):>3} genuine   (inflated file said "
              f"{old[p]:>3})")

    print("\ncontribution types among the genuine rows:")
    for k, v in collections.Counter(
            r.get("contribution", "?") for r in good).most_common():
        print(f"  {v:>4}  {k}")


if __name__ == "__main__":
    main()

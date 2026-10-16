"""Draw a stratified random validation sample, and cut it into coder packets.

This replaces `build_verification_sample.py`, which drew the 100 most
load-bearing papers. That was a reasonable engineering choice and it is **not a
probability sample**, so it supports no statistical claim about the rest of the
corpus. The project lead's advisor asked for a number that licenses the
inference from the sample to the corpus; this is that sample.

## The design

Two strata, because only two evidence grades were ever assigned:

    B  peer-reviewed        175 papers
    C  credible preprint    807 papers

Grade A (peer-reviewed *with artifacts*) and D (gray literature) are defined in
the project plan and were never assigned. A cannot be recovered mechanically:
`artifacts_released` is free-text prose, not a flag, and only 46 of 982 rows
hold a clean "y". Recovering it needs its own normalisation pass. Until then
the stratification is on two levels and we say so.

## Allocation

Two different claims need two different sample sizes, and the default here
serves both:

    overall accuracy, +/-5%        proportional, n=277   (B=49,  C=228)
    "quality does not differ
     by grade", 15pp at 80% power  equal,        n>=200  (B=100, C=100)
    BOTH                           default,      n=328   (B=100, C=228)

The default costs 51 more papers than the proportional design and buys the
grade comparison outright. `--allocation proportional` or `equal` if that
trade is not wanted.

**The overall rate must be weighted** by stratum size (175/982, 807/982) when
combining, or grade B is over-represented by a factor of four. `--allocation
equal` makes this mandatory rather than merely advisable; the manifest carries
the weights so the combine cannot be done wrong by accident.

## What is excluded from the frame

  * the 57 papers the contribution screen proposes removing - validating a
    paper we are about to drop wastes a coder;
  * the 100 papers already drawn for the old purposive sample. Those packets
    were built but never coded, so there is no pilot estimate of the agreement
    rate p and n stays at the conservative p=.50 figure. They are excluded to
    avoid handing the same paper to two coders, not because they carry data.

Seeded and reproducible: the same seed over the same frame yields the same
papers, and the manifest records the frame size, the seed and the exclusions
so the draw can be audited rather than trusted.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import pathlib
import random
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src import registry_source  # noqa: E402

FINDINGS = (REPO / "data" / "exports" / "contribution_screen"
            / "bundles" / "screen-findings")
OUT = REPO / "data" / "exports" / "validation_sample"

# coded from full text, so these are the columns a validator re-derives
COLUMNS = [
    "paper_id", "title", "year", "venue", "track", "evidence_grade", "pdf",
    "v_track", "v_channel", "v_consequence", "v_contribution",
    "v_has_attack", "v_attack_name",
    "v_has_defense", "v_defense_name", "v_validated_against",
    "v_evidence_quote", "v_agrees_with_registry", "v_notes",
]

ALLOC = {
    "both":         {"B": 100, "C": 228},
    "proportional": {"B": 49,  "C": 228},
    "equal":        {"B": 100, "C": 100},
}


def removed_ids():
    """Paper ids the contribution screen proposes dropping."""
    f = FINDINGS / "out-of-scope-removed.csv"
    if not f.exists():
        return set()
    with open(f, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    return {r.get("paper_id", "").strip() for r in rows if r.get("paper_id")}, rows


def pilot_ids():
    """Papers already drawn for the purposive top-100 sample.

    Those packets ship as .xlsx, not .csv. A csv-only scan returns an empty
    set and silently lets pilot papers back into the probability sample, which
    is the one thing this frame exists to prevent, so both are read and the
    count is printed rather than trusted.
    """
    out = set()
    d = REPO / "verification"
    if not d.exists():
        return out
    for f in d.rglob("*.csv"):
        try:
            with open(f, encoding="utf-8-sig") as fh:
                for r in csv.DictReader(fh):
                    if r.get("paper_id"):
                        out.add(r["paper_id"].strip())
        except Exception:
            continue
    try:
        import openpyxl
    except ImportError:
        print("  WARNING: openpyxl missing, .xlsx pilot packets not excluded")
        return out
    for f in d.rglob("*.xlsx"):
        if f.name.startswith("~$"):
            continue
        try:
            # The first sheet is coder instructions and the data lives on a
            # 'coding' sheet, so neither .active nor row 1 is where the header
            # is. Scan every sheet for it.
            wb = openpyxl.load_workbook(f, read_only=True)
            found = False
            for ws in wb.worksheets:
                grid = list(ws.iter_rows(values_only=True))
                hi = next((j for j, r in enumerate(grid[:25])
                           if any(str(c or "").strip() == "paper_id"
                                  for c in r)), None)
                if hi is None:
                    continue
                hdr = [str(c or "").strip() for c in grid[hi]]
                i = hdr.index("paper_id")
                for r in grid[hi + 1:]:
                    if i < len(r) and r[i]:
                        out.add(str(r[i]).strip())
                found = True
            if not found:
                print(f"  note: {f.name} has no paper_id column on any sheet")
        except Exception as e:
            print(f"  WARNING: could not read {f.name}: {e}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--allocation", choices=sorted(ALLOC), default="both")
    ap.add_argument("--seed", type=int, default=20261016)
    ap.add_argument("--per_packet", type=int, default=40)
    args = ap.parse_args()

    papers = registry_source.load_papers()
    inc = [p for p in papers
           if str(p.get("screening") or "").strip().lower() != "exclude"]

    drop_ids, drop_rows = removed_ids()
    # the screen's CSV may not carry paper_id; fall back to title matching,
    # reported so a silent miss cannot shrink the exclusion set unnoticed
    if not drop_ids and drop_rows:
        titles = {r["title"].strip().lower() for r in drop_rows if r.get("title")}
        drop_ids = {p["paper_id"] for p in inc
                    if (p.get("title") or "").strip().lower() in titles}
        print(f"  screen CSV has no paper_id; matched {len(drop_ids)} of "
              f"{len(drop_rows)} removals by title")
    pilot = pilot_ids()

    frame = [p for p in inc
             if p["paper_id"] not in drop_ids and p["paper_id"] not in pilot]
    by_grade = collections.defaultdict(list)
    for p in frame:
        by_grade[(p.get("evidence_grade") or "?").strip()].append(p)

    print(f"corpus {len(inc)}  - {len(drop_ids)} proposed removals "
          f"- {len(pilot)} pilot papers = frame {len(frame)}")
    for g in sorted(by_grade):
        print(f"   grade {g}: {len(by_grade[g])} available")

    want = ALLOC[args.allocation]
    rng = random.Random(args.seed)
    picked = []
    for g, n in sorted(want.items()):
        pool = sorted(by_grade.get(g, []), key=lambda p: p["paper_id"])
        if len(pool) < n:
            raise SystemExit(f"grade {g}: asked for {n}, frame holds {len(pool)}")
        picked += rng.sample(pool, n)
    rng.shuffle(picked)   # so a packet is not all one grade

    # Two sets of weights, and the distinction is load-bearing. The sample was
    # drawn from the FRAME, so it licenses claims about the frame and the
    # combine must use frame weights. Corpus weights are recorded only so the
    # gap between the two is visible; using them would silently re-weight the
    # estimate toward papers that were deliberately excluded.
    gsize_corpus = collections.Counter((p.get("evidence_grade") or "?").strip()
                                       for p in inc)
    gsize_frame = {g: len(by_grade.get(g, [])) for g in want}
    weights = {g: round(gsize_frame[g] / len(frame), 6) for g in want}
    weights_corpus = {g: round(gsize_corpus[g] / len(inc), 6) for g in want}

    OUT.mkdir(parents=True, exist_ok=True)
    packets = [picked[i:i + args.per_packet]
               for i in range(0, len(picked), args.per_packet)]
    for i, pk in enumerate(packets, 1):
        f = OUT / f"validation-{i:02d}.csv"
        with open(f, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=COLUMNS)
            w.writeheader()
            for p in pk:
                w.writerow({
                    "paper_id": p["paper_id"],
                    "title": p.get("title", ""),
                    "year": p.get("year", ""),
                    "venue": p.get("venue", ""),
                    "track": p.get("track", ""),
                    "evidence_grade": (p.get("evidence_grade") or "").strip(),
                    "pdf": p.get("pdf_local_path", ""),
                })
        print(f"  wrote {f.name}  {len(pk)} papers")

    man = {
        "generated": "2026-10-16",
        "purpose": "stratified random validation sample; the purposive top-100 "
                   "was built but never coded, and is excluded only to avoid "
                   "duplicate work",
        "seed": args.seed,
        "allocation": args.allocation,
        "allocation_counts": want,
        "corpus_n": len(inc),
        "frame_n": len(frame),
        "excluded_proposed_removal": len(drop_ids),
        "excluded_uncoded_purposive": len(pilot),
        "stratum_sizes_in_frame": gsize_frame,
        "stratum_weights_for_combine": weights,
        "stratum_weights_over_corpus": weights_corpus,
        "inference_target": "the %d-paper frame, not the full corpus: the "
                            "pilot and the proposed removals were excluded "
                            "before drawing" % len(frame),
        "combine_rule": "overall = sum_g stratum_weights_for_combine[g] * "
                        "rate[g]. An unweighted mean over-represents grade B "
                        "roughly sixfold. Do not use the corpus weights: the "
                        "sample was not drawn from the corpus.",
        "grades_not_assigned": ["A", "D"],
        "grade_A_note": "A (peer-reviewed with artifacts) is defined in the "
                        "project plan but was never assigned. artifacts_released "
                        "is free-text prose, not a flag, so A cannot be "
                        "recovered without a normalisation pass.",
        "n_packets": len(packets),
        "per_packet": args.per_packet,
        "papers": [p["paper_id"] for p in picked],
        "frame_fingerprint": hashlib.sha256(
            "".join(sorted(p["paper_id"] for p in frame)).encode()).hexdigest()[:16],
    }
    (OUT / "manifest.json").write_text(json.dumps(man, indent=1))
    print(f"\n{len(picked)} papers in {len(packets)} packets -> {OUT}")
    print(f"frame fingerprint {man['frame_fingerprint']}  seed {args.seed}")
    print(f"weights for the combine: {weights}")


if __name__ == "__main__":
    main()

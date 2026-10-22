"""Export batches for the full-text re-coding of the taxonomy cube.

The original channel/consequence/track labels were coded from title and
abstract. The re-screening correction later proved abstract-only judgement
can be meaningfully wrong, so this pass re-codes them against the full text,
which is now cached for all 929 included papers.

It also records a confidence per paper. The existing confidence came from
the RQ3/RQ4 entry passes, covers only the papers that contributed an entry,
and says nothing about the 18 extracted fields. A per-paper confidence lets
the next validation draw stratify on something that actually describes the
thing being validated.

Each batch is a worklist, not the text: the coder opens
data/cache/pdf_text/<paper_id>.txt itself. A batch that carried the text
would be 5 MB.

Out: data/registries/raw/recode_batchNN.json
"""
from __future__ import annotations

import argparse
import json
import pathlib

import openpyxl

REPO = pathlib.Path(__file__).resolve().parent.parent
OUT = REPO / "data" / "registries" / "raw"
CACHE = REPO / "data" / "cache" / "pdf_text"

CHANNELS = ["direct-input", "RAG", "tool-output", "tool-metadata", "memory",
            "skill", "multi-agent", "cross-modal", "supply-chain"]
# availability-loss added 2026-10-21. The full-text pilot found papers whose
# measured harm is the agent becoming unable to finish the task at all -
# context budget exhausted, or a defense that degraded the model into
# refusing or timing out. The six-way scheme could not see them, and forcing
# them into reasoning-corruption hid a real gap.
CONSEQ = ["goal-hijack", "reasoning-corruption", "silent-corruption",
          "data-exfiltration", "persistence-backdoor", "resource-abuse",
          "availability-loss"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-batch", type=int, default=40)
    ap.add_argument("--limit", type=int, default=0, help="pilot: first N papers")
    args = ap.parse_args()

    wb = openpyxl.load_workbook(
        REPO / "data/exports/paper_dashboard_source.xlsx", read_only=True)
    rows = list(wb["Papers"].iter_rows(values_only=True))
    wb.close()
    h = list(rows[0])
    inc = [dict(zip(h, r)) for r in rows[1:]
           if str(dict(zip(h, r)).get("screening", "")).strip() != "Exclude"]
    inc.sort(key=lambda p: str(p["paper_id"]))

    work = []
    for p in inc:
        pid = str(p["paper_id"])
        t = CACHE / f"{pid}.txt"
        if not t.is_file():
            continue
        work.append({
            "paper_id": pid,
            "title": p.get("title"),
            "year": p.get("year"),
            "text_path": f"data/cache/pdf_text/{pid}.txt",
            "current_track": p.get("track"),
            "current_channel": p.get("channel"),
            "current_consequence": p.get("consequence"),
        })
    if args.limit:
        work = work[:args.limit]

    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("recode_batch*.json"):
        old.unlink()
    n = 0
    for i in range(0, len(work), args.per_batch):
        n += 1
        f = OUT / f"recode_batch{n:02d}.json"
        f.write_text(json.dumps(work[i:i + args.per_batch], indent=1))
    print(f"{len(work)} papers -> {n} batches of {args.per_batch}")
    print(f"channels: {len(CHANNELS)}  consequences: {len(CONSEQ)}")
    print(f"wrote {OUT}/recode_batchNN.json")


if __name__ == "__main__":
    main()

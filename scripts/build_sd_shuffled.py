"""A shuffled-order copy of one failure's contexts, for AttnTrace's position check.

The shared contexts put every bad passage in the last slots -- RobustRAG's
poison_order='backward', which build_poisoned follows -- so on the stale
document AttnTrace's trace can find them by position alone: attention favours
recent text. This file holds the same passages in a fixed random order per
item and dose, and records where each came from, so a trace that still finds
the stale passages is following their content, not their slot.

    python3 scripts/build_sd_shuffled.py            # incidental_stale, n=100

Writes data/sd_contexts/<failure>_shuffled.json, readable by every runner as
--failure <failure>_shuffled. Per item, `bad[dose]` lists the shuffled
positions of the bad passages and `orig_pos[dose][i]` the original slot of
shuffled passage i.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import random

REPO = pathlib.Path(__file__).resolve().parent.parent
CTX = REPO / "data" / "sd_contexts"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--failure", default="incidental_stale")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--doses", type=int, nargs="+", default=[1, 3, 5])
    ap.add_argument("--seed", type=int, default=12)
    args = ap.parse_args()

    src = json.loads((CTX / f"{args.failure}.json").read_text())
    top_k = src["top_k"]
    rng = random.Random(args.seed)
    rows = []
    for it in src["items"][:args.n]:
        row = {k: it[k] for k in ("idx", "question", "gold", "target")}
        row.update(contexts={}, orig_pos={}, bad={})
        for j in args.doses:
            ps = it["contexts"][str(j)]
            L = len(ps)    # a few items retrieve fewer than top_k passages
            perm = list(range(L))
            rng.shuffle(perm)
            row["contexts"][str(j)] = [ps[i] for i in perm]
            row["orig_pos"][str(j)] = perm
            # backward placement: the bad passages held the last j slots
            row["bad"][str(j)] = [s for s, i in enumerate(perm) if i >= L - j]
        rows.append(row)
    blob = json.dumps(rows, sort_keys=True).encode()
    name = f"{args.failure}_shuffled"
    payload = {"failure": name, "source": args.failure,
               "source_sha256": src["sha256"], "dataset": src["dataset"],
               "n": len(rows), "top_k": top_k, "doses": args.doses,
               "seed": args.seed,
               "sha256": hashlib.sha256(blob).hexdigest(), "items": rows}
    (CTX / f"{name}.json").write_text(json.dumps(payload, indent=1))
    print(f"  {name}: {len(rows)} items, doses {args.doses}  "
          f"sha {payload['sha256'][:12]}")


if __name__ == "__main__":
    main()

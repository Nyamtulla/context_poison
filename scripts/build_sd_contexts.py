"""Write the shared contexts every second-direction runner reads.

    python3 scripts/build_sd_contexts.py            # all four failures
    python3 scripts/build_sd_contexts.py --n 2      # smoke-test size

One file per failure, data/sd_contexts/<failure>.json. A runner in any
environment reads it, so every defense answers the same question from the same
passages; the file carries a hash of its own passages so a result can name the
exact contexts it was produced from.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from sd_items import build_contexts   # noqa: E402

# The four failures no attacker wrote, as the paper's second direction names
# them. RobustRAG already ran all four; the new defenses run the same contexts.
FAILURES = ["incidental_stale", "distractor_evidence", "misretrieval",
            "context_dilution"]
DOSES = [0, 1, 2, 3, 5]
# How many of the item set's first items each failure ran on in RobustRAG's
# cells. The two older cells ran the runner's default of 300, the two Phase 1
# cells 500; matching them keeps every defense on RobustRAG's exact items.
N_FOR = {"incidental_stale": 500, "distractor_evidence": 300,
         "misretrieval": 300, "context_dilution": 500}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=None,
                    help="override every failure's n (smoke tests)")
    ap.add_argument("--top_k", type=int, default=10)
    ap.add_argument("--failures", nargs="+", default=FAILURES)
    ap.add_argument("--out_dir", default="data/sd_contexts")
    args = ap.parse_args()
    out = REPO / args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    for f in args.failures:
        rows = build_contexts(f, args.n or N_FOR[f], args.top_k, DOSES)
        blob = json.dumps(rows, sort_keys=True).encode()
        payload = {"failure": f, "dataset": "open_nq", "n": len(rows),
                   "top_k": args.top_k, "doses": DOSES,
                   "sha256": hashlib.sha256(blob).hexdigest(), "items": rows}
        (out / f"{f}.json").write_text(json.dumps(payload, indent=1))
        print(f"  {f}: {len(rows)} items  sha {payload['sha256'][:12]}")


if __name__ == "__main__":
    main()

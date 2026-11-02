"""Flag every retrieved passage with a released prompt-injection classifier.

A detector is deployed in front of retrieval by dropping the passages it flags
and answering from the rest. Which passages it flags does not depend on the
answering model, so the flags are computed once per unique passage, here, in
whatever environment the classifier needs, and the answering runner
(`sd_rag_base.py --defense filter:<name>`) reads them. Each classifier is
loaded exactly as its model card deploys it.

    python3 scripts/sd_detect_classifier.py piguard
    python3 scripts/sd_detect_classifier.py piguard --n 2     # smoke

The flag file maps a passage's sha1 to the classifier's label and score, so a
reader can see what each detector removed, not only the accuracy that resulted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from build_sd_contexts import FAILURES   # noqa: E402
from sd_common import load_contexts      # noqa: E402

# name -> (hub id, remote code, labels that mean "injection", registry row)
DETECTORS = {
    # PIGuard (InjecGuard), ACL 2025; model card: pipeline("text-classification",
    # truncation=True, max_length=512), labels benign / injection.
    "piguard": ("leolee99/PIGuard", True, {"injection"}, 1035),
    # PromptGuard 2, the classifier inside LlamaFirewall; labels LABEL_0
    # benign / LABEL_1 malicious. Gated: needs Meta's approval on the hub.
    "promptguard2": ("meta-llama/Llama-Prompt-Guard-2-86M", False,
                     {"LABEL_1", "MALICIOUS", "malicious"}, 366),
}
FLAG_DIR = REPO / "data" / "sd_flags"


def sha(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()


def passages(n=None):
    seen = {}
    for f in FAILURES:
        for row in load_contexts(f, n)["items"]:
            for ctx in row["contexts"].values():
                for p in ctx:
                    seen.setdefault(sha(p), p)
    return seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("detector", choices=sorted(DETECTORS))
    ap.add_argument("--n", type=int, default=None, help="smoke: first n items")
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--device", default=None,
                    help="cpu or cuda; default cpu -- an 86M-184M classifier "
                         "does not need the shared card")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    import torch
    from transformers import (AutoModelForSequenceClassification,
                              AutoTokenizer, pipeline)
    hub, remote, positive, row = DETECTORS[args.detector]
    tok = AutoTokenizer.from_pretrained(hub)
    model = AutoModelForSequenceClassification.from_pretrained(
        hub, trust_remote_code=remote)
    clf = pipeline("text-classification", model=model, tokenizer=tok,
                   truncation=True, max_length=512,
                   device=torch.device(args.device or "cpu"))

    todo = passages(args.n)
    out = pathlib.Path(args.out or FLAG_DIR / f"{args.detector}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    flags = json.loads(out.read_text())["flags"] if out.exists() else {}
    keys = [k for k in todo if k not in flags]
    print(f"{args.detector}: {len(todo)} unique passages, {len(keys)} to score",
          flush=True)
    for i in range(0, len(keys), args.batch):
        chunk = keys[i:i + args.batch]
        for k, r in zip(chunk, clf([todo[k] for k in chunk])):
            flags[k] = {"label": r["label"], "score": round(float(r["score"]), 4),
                        "flag": r["label"] in positive}
        if (i // args.batch) % 20 == 0:
            print(f"  {i + len(chunk)}/{len(keys)}", flush=True)
            out.write_text(json.dumps({"detector": args.detector, "hub": hub,
                                       "registry_row": row, "flags": flags}))
    out.write_text(json.dumps({"detector": args.detector, "hub": hub,
                               "registry_row": row, "flags": flags}))
    n_flag = sum(v["flag"] for v in flags.values())
    print(f"wrote {out}: {n_flag} of {len(flags)} passages flagged", flush=True)


if __name__ == "__main__":
    main()

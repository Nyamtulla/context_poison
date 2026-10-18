"""Hash and describe every built attack payload in data/payloads/.

A payload is a derived file, but deriving one costs GPU hours: the adaptive and
gradient payloads each run a per-item search against the model. An artifact
that shipped only the builders would be reproducible in principle and not in an
afternoon, so the built files ship too and this records what they are.

The hash is the point. It lets a rebuild be checked against the exact file the
published numbers came from, and it lets `check_artifact.py` tell a truncated
download from a real one.

Out: data/payloads/INDEX.json
"""
from __future__ import annotations

import hashlib
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
P = REPO / "data" / "payloads"

# The field each payload adds, the script that adds it, and what the passage
# asserts. Hand-written: this is the part a reader checks us on.
SPEC = {
 "NaturalQuestionsShort_kc_distractor.jsonl": {
   "field": "distractor_evidencde",
   "built_by": "python3 scripts/build_distractor_payload.py",
   "asserts": "a THIRD answer, equal to neither the gold answer nor the "
              "model's own prior answer, which is what separates copying the "
              "attacker from falling back on memory",
   "ours": True},
 "NaturalQuestionsShort_kc_adaptive.jsonl": {
   "field": "adaptive_evidencde",
   "built_by": "python3 scripts/build_adaptive_acd_payload.py --n 686",
   "asserts": "the same distractor answer as above, in whichever of five "
              "sentence forms minimises the entropy ACD's rule keys on "
              "(best-of-K, white-box)",
   "ours": True},
 "NaturalQuestionsShort_kc_gradient.jsonl": {
   "field": "gradient_evidencde",
   "built_by": "python3 scripts/build_gradient_acd_payload.py --n 686 "
               "--steps 10 --batch 24",
   "asserts": "the best-of-K passage plus a GCG-optimised 20-token suffix "
              "against the same entropy objective",
   "ours": True},
}


def main():
    files = []
    for p in sorted(P.glob("*.jsonl")):
        spec = SPEC.get(p.name)
        if spec is None:
            print(f"  {p.name}: not in SPEC, skipping (add it or delete the file)")
            continue
        rows = [json.loads(l) for l in p.read_text().splitlines()]
        n = sum(1 for r in rows if (r.get(spec["field"]) or "").strip())
        files.append({"name": p.name,
                      "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                      "bytes": p.stat().st_size,
                      "rows": len(rows), "n_optimised": n,
                      "adds_field": spec["field"],
                      "built_by": spec["built_by"],
                      "asserts": spec["asserts"],
                      "ours": spec["ours"]})
        print(f"  {p.name:<48} {len(rows):>5} rows, {n:>4} carry "
              f"{spec['field']}")
    (P / "INDEX.json").write_text(json.dumps({
        "what_this_is":
          "Attack payloads built by this project, for the CoConflictQA item "
          "set that ships with ParamMute. Each file is that item set with one "
          "field added; the untouched rows are upstream's. "
          "`scripts/setup_third_party.py --payloads` copies them into the "
          "ParamMute tree where the runners read them.",
        "base_item_set":
          "third_party/ParamMute/data/CoConflictQA/test/"
          "NaturalQuestionsShort_kc.jsonl (upstream, not redistributed here)",
        "files": files}, indent=1) + "\n")
    print(f"\nwrote {P/'INDEX.json'}  ({len(files)} payloads)")


if __name__ == "__main__":
    main()

"""Run a script from the corpus-poisoning tree with paths and shims in place.

Two things have to be right before the authors' code will import, and both are
easy to get wrong silently:

  * PYTHONPATH order, because corpus-poisoning and its required Contriever
    clone both have a top-level `src/` (see the harness README).
  * The transformers v5 removal of `batch_encode_plus`, which only bites on
    the evaluation path.

Usage mirrors the upstream commands:

    python3 corpus_poisoning_harness/run_corpus_poisoning.py evaluate_beir \
        --model_code contriever --dataset nfcorpus --split test \
        --result_output results/beir_results/nfcorpus-contriever.json
"""
from __future__ import annotations

import os
import pathlib
import runpy
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
TREE = REPO / "third_party" / "corpus-poisoning"

# Order matters and is explained in corpus_poisoning_harness/README.md:
# corpus-poisoning's own src first (bare `utils`), then Contriever's repo root
# (its src/ is a regular package, so it wins `import src`), then Contriever's
# src (bare `contriever`, `beir_utils`).
PATHS = [TREE / "src", TREE / "src" / "contriever", TREE / "src" / "contriever" / "src"]


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    script = sys.argv[1]
    target = TREE / "src" / f"{script}.py"
    if not target.exists():
        raise SystemExit(f"no such script: {target}")

    sys.path[:0] = [str(p) for p in PATHS]
    sys.modules.pop("compat", None)
    sys.path.insert(0, str(REPO / "corpus_poisoning_harness"))
    import compat

    for line in compat.apply():
        print(f"[compat] {line}", file=sys.stderr)

    # The upstream scripts resolve `datasets/` and `results/` relative to cwd.
    os.chdir(TREE)
    sys.argv = [str(target), *sys.argv[2:]]
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()

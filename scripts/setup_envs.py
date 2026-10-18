"""Build the per-defense dependency sets that cannot share one environment.

Most of this repo runs on one stack. Two defenses do not, and the reason is
worth stating because it is the same reproducibility problem the paper reports
one layer down: the artifacts run, but they do not run *together*.

  ACD       transformers==4.44.0, pinned by its own README. Its vendored
            sampling loop imports NEED_SETUP_CACHE_CLASSES_MAPPING, removed in
            4.49, and is_quanto_available, also removed. Hard requirement:
            without it the runner raises ImportError before loading a model.
  CK-PLUG   ships its own transformers 4.49 fork in `transformers-4.49/` and
            its README says to install it. Its scoring and decoder modules
            import under the system stack too, so we treat the fork as
            recommended rather than required, and say so.

Everything else, including both adaptive payload builders, runs on the system
stack in `requirements-experiments.txt`.

These install to a plain directory, not a virtualenv, for two reasons: this box
has no working `ensurepip`, and `pip install -e` would write egg-info into the
third-party clones and make `setup_third_party.py --verify` report them as
modified. The clones staying byte-identical to upstream is the evidence behind
"we do not reimplement", so the dependencies live outside them.

    python3 scripts/setup_envs.py            # build
    python3 scripts/setup_envs.py --verify   # check, no network
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
ENVS = REPO / "envs"

# name -> (requirements file, import to prove it worked, expected version)
SETS = {
    "acd-libs": ("acd-requirements.txt", "transformers", "4.44.0"),
}


def build(name, req):
    target = ENVS / name
    print(f"  installing {req} -> envs/{name}")
    r = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                        "--target", str(target), "--no-deps",
                        "-r", str(ENVS / req)],
                       capture_output=True, text=True)
    if r.returncode:
        print(r.stderr.strip()[-600:])
        return False
    return True


def verify(name, mod, want):
    """Import the module with ONLY this set ahead of the path, and check it
    is the version we meant. An import that silently resolves to the system
    copy would pass a weaker check and fail at run time."""
    target = ENVS / name
    if not target.exists():
        print(f"  envs/{name:<12} MISSING   fix: python3 scripts/setup_envs.py")
        return False
    r = subprocess.run(
        [sys.executable, "-c",
         f"import {mod};print({mod}.__version__);print({mod}.__file__)"],
        capture_output=True, text=True, cwd=REPO,
        env={"PYTHONPATH": str(target), "PATH": "/usr/bin:/bin",
             "HOME": str(pathlib.Path.home())})
    out = r.stdout.split()
    got = out[0] if out else "?"
    src = out[1] if len(out) > 1 else ""
    ok = got == want and str(target) in src
    print(f"  envs/{name:<12} {mod} {got}"
          + ("" if ok else f"   EXPECTED {want} from envs/{name}"))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    ENVS.mkdir(exist_ok=True)
    ok = True
    for name, (req, mod, want) in SETS.items():
        if args.verify:
            ok = verify(name, mod, want) and ok
        else:
            ok = build(name, req) and ok
    if not args.verify and ok:
        print("\nbuilt. verify with: python3 scripts/setup_envs.py --verify")
        print("run ACD with:       PYTHONPATH=envs/acd-libs python3 "
              "scripts/acd_vs_corpus_poisoning.py ...")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

"""Fetch, pin and verify every attack/defense implementation this project runs.

The clones under `third_party/` are not committed here. They carry their own
git history and their own licenses, and vendoring them would relicense other
people's work. `third_party/MANIFEST.json` pins each one to the commit our
runs used; this script fetches those commits and checks them.

    python3 scripts/setup_third_party.py            # clone what is missing
    python3 scripts/setup_third_party.py --verify   # check pins, no network
    python3 scripts/setup_third_party.py --payloads # install built payloads

`--verify` is the machine-checkable form of the claim the paper makes in
Section "Related systematizations": *we do not reimplement*. It fails if any
clone's HEAD has moved off its pin or if any tracked source file differs from
upstream. Carlini's critique of DeepSec found several attacks and one defense
reimplemented incorrectly; the defense against making that mistake is not
being careful, it is not reimplementing, and this is how a reader checks that
we did not.

Exit status is 0 only if every repo is present, pinned and unmodified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
TP = REPO / "third_party"
MANIFEST = TP / "MANIFEST.json"
PAYLOADS = REPO / "data" / "payloads"
# where the CoConflictQA runners read their item sets from
PAYLOAD_DEST = TP / "ParamMute" / "data" / "CoConflictQA" / "test"


def git(*a, cwd=None, check=True):
    r = subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        raise SystemExit(f"git {' '.join(a)} failed:\n{r.stderr.strip()}")
    return r.stdout.strip()


def clone(entry):
    d = TP / entry["name"]
    if d.exists():
        return "present"
    if not entry["commit"]:
        print(f"  {entry['name']}: upstream has no commits, skipping")
        return "skipped"
    TP.mkdir(exist_ok=True)
    git("clone", "--quiet", entry["url"], str(d))
    git("checkout", "--quiet", entry["commit"], cwd=d)
    return "cloned"


def verify(entry):
    """Present, on its pinned commit, and with no modified tracked file."""
    d = TP / entry["name"]
    if not d.exists():
        return "MISSING"
    if not entry["commit"]:
        return "ok (no upstream commits)"
    head = git("rev-parse", "HEAD", cwd=d, check=False)
    if head != entry["commit"]:
        return f"PIN MOVED: at {head[:10]}, manifest says {entry['commit'][:10]}"
    dirty = git("status", "--porcelain", "--untracked-files=no", cwd=d, check=False)
    if dirty:
        n = len(dirty.splitlines())
        return f"SOURCE MODIFIED: {n} tracked file(s) differ from upstream"
    return "ok"


def payloads(install):
    """Our built attack payloads, which live here and are copied into place.

    They are derived files, but deriving them costs GPU hours (the adaptive and
    gradient payloads each run a per-item search over the model), so an
    artifact that shipped only the builders would not be reproducible in an
    afternoon. The hashes are recorded so a rebuild can be checked against the
    files the published numbers came from.
    """
    index = json.loads((PAYLOADS / "INDEX.json").read_text())
    ok = True
    for f in index["files"]:
        src = PAYLOADS / f["name"]
        if not src.exists():
            print(f"  {f['name']}: MISSING from data/payloads/")
            ok = False
            continue
        got = hashlib.sha256(src.read_bytes()).hexdigest()
        mark = "ok" if got == f["sha256"] else f"HASH MISMATCH ({got[:12]})"
        if got != f["sha256"]:
            ok = False
        if install:
            if not PAYLOAD_DEST.exists():
                print(f"  cannot install: {PAYLOAD_DEST} does not exist "
                      "(clone ParamMute first)")
                return False
            shutil.copy2(src, PAYLOAD_DEST / f["name"])
            mark += " -> installed"
        print(f"  {f['name']:<48} {mark}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true",
                    help="check pins and local modifications; no network")
    ap.add_argument("--payloads", action="store_true",
                    help="copy data/payloads/*.jsonl into the ParamMute tree")
    args = ap.parse_args()
    man = json.loads(MANIFEST.read_text())

    if args.payloads:
        sys.exit(0 if payloads(install=True) else 1)

    if args.verify:
        bad = 0
        for e in man["repos"]:
            s = verify(e)
            if not s.startswith("ok"):
                bad += 1
            print(f"  {e['name']:<40} {s}")
        print(f"\npayloads:")
        if not payloads(install=False):
            bad += 1
        print(f"\n{len(man['repos'])} repos, {bad} problem(s)")
        sys.exit(1 if bad else 0)

    for e in man["repos"]:
        print(f"  {e['name']:<40} {clone(e)}")
    print("\nnow: python3 scripts/setup_third_party.py --payloads")


if __name__ == "__main__":
    main()

"""One command that says whether a clone of this repo can run the experiments.

    python3 scripts/check_artifact.py

No GPU, no model download, no network. It checks the five things that actually
break a reproduction attempt, in the order they break:

  1. the Python environment, against requirements-experiments.txt
  2. the Git LFS payloads (a 133-byte pointer where a 72 MB database should be
     is this repo's single most common setup failure)
  3. every third-party implementation, present and on its pinned commit
  4. every attack payload, present and matching the hash the published numbers
     were produced from
  5. every result registry the paper's macros read, present and parseable

Exit status is 0 only if all five pass. Anything that fails prints the command
that fixes it.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
OK, BAD = "  ok   ", "  FAIL "


def report(name, ok, detail="", fix=""):
    print(f"{OK if ok else BAD} {name}" + (f"   {detail}" if detail else ""))
    if not ok and fix:
        print(f"         fix: {fix}")
    return ok


def check_env():
    print("\n[1/5] python environment")
    want = {}
    for line in (REPO / "requirements-experiments.txt").read_text().splitlines():
        m = re.match(r"^([A-Za-z0-9_.-]+)==([0-9][^ #]*)", line.strip())
        if m:
            want[m.group(1)] = m.group(2)
    good = True
    for pkg, ver in want.items():
        try:
            got = importlib.metadata.version(pkg)
        except Exception:
            good = report(pkg, False, "not installed",
                          "pip install -r requirements-experiments.txt") and good
            continue
        # a mismatch is a warning, not a failure: the runs are reproducible on
        # these versions and may well be on others. We say which we used.
        same = got == ver
        print(f"{OK if same else '  note '} {pkg:<16} {got}"
              + ("" if same else f"   (published on {ver})"))
    return good


def check_lfs():
    print("\n[2/5] git-lfs payloads")
    good = True
    for rel in ("data/context_sok.db", "data/paper_explorer.db"):
        p = REPO / rel
        if not p.exists():
            good = report(rel, False, "missing") and good
            continue
        # an un-smudged LFS pointer is a ~133 byte text file starting with this
        head = p.open("rb").read(64)
        ptr = head.startswith(b"version https://git-lfs")
        good = report(rel, not ptr,
                      f"{p.stat().st_size/1e6:.0f} MB" if not ptr
                      else "LFS pointer, not the file",
                      "git lfs install && git lfs pull") and good
    return good


def check_third_party():
    print("\n[3/5] third-party implementations")
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "setup_third_party.py"),
                        "--verify"], capture_output=True, text=True, cwd=REPO)
    tail = [l for l in r.stdout.splitlines() if "problem" in l]
    for line in r.stdout.splitlines():
        if "ok" not in line and line.strip() and "payload" not in line:
            print("  " + line.strip())
    return report("20 repos on their pinned commits, sources unmodified",
                  r.returncode == 0, tail[-1] if tail else "",
                  "python3 scripts/setup_third_party.py")


def check_payloads():
    print("\n[4/5] attack payloads")
    idx = REPO / "data" / "payloads" / "INDEX.json"
    if not idx.exists():
        return report("data/payloads/INDEX.json", False, "missing",
                      "python3 scripts/build_payload_index.py")
    good = True
    for f in json.loads(idx.read_text())["files"]:
        p = REPO / "data" / "payloads" / f["name"]
        if not p.exists():
            good = report(f["name"], False, "missing") and good
            continue
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        good = report(f["name"], got == f["sha256"],
                      f"{f['n_optimised']} items" if got == f["sha256"]
                      else f"hash {got[:12]} != {f['sha256'][:12]}") and good
    return good


def check_registries():
    print("\n[5/5] result registries the paper reads")
    # every registry gen_paper_numbers.py opens, whether via its `load()`
    # helper or by path. A macro that cannot be regenerated is a number in the
    # paper that nothing in the artifact backs.
    src = (REPO / "scripts" / "gen_paper_numbers.py").read_text()
    need = sorted(set(re.findall(r'load\(\s*"([^"]+\.json)"', src))
                  | set(re.findall(r'R\s*/\s*"([^"]+\.json)"', src)))
    good = True
    for n in need:
        p = REPO / "data" / "registries" / n
        ok = p.exists()
        if ok:
            try:
                json.loads(p.read_text())
            except Exception:
                ok = False
        good = report(n, ok) and good
    return good


def main():
    print("checking that this clone can run the experiments")
    results = [check_env(), check_lfs(), check_third_party(),
               check_payloads(), check_registries()]
    print()
    if all(results):
        print("all five groups pass; see EXPERIMENTS.md for what to run")
        sys.exit(0)
    print(f"{sum(not r for r in results)} of 5 groups failed; "
          "the fixes are printed above")
    sys.exit(1)


if __name__ == "__main__":
    main()

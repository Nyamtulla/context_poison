"""Rename the corpus PDFs from arXiv ids to paper titles.

`data/papers/2402.14409.pdf` tells a human nothing. The verification pass has
people opening a hundred of these by hand, so the filename should say what the
paper is.

This is reversible. Every rename is recorded in
`data/registries/pdf_rename_map.json` before anything moves, and `--revert`
replays it backwards. Nothing is renamed unless the whole plan is collision-free.

Both databases carry `pdf_local_path` and both are updated in the same run,
because every downstream script reads the path from there rather than
reconstructing it - except `write_excel_row.py`, which built
`data/papers/{arxiv_id}.pdf` by hand and is patched separately.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import sqlite3
import unicodedata

REPO = pathlib.Path(__file__).resolve().parent.parent
PDF_DIR = REPO / "data" / "papers"
MAP = REPO / "data" / "registries" / "pdf_rename_map.json"
DBS = [REPO / "data" / "paper_explorer.db", REPO / "data" / "context_sok.db"]
TABLES = {"paper_explorer.db": "paper", "context_sok.db": "papers"}
MAXLEN = 150


def sanitize(title: str, fallback: str) -> str:
    """Filesystem-safe, human-readable, and stable across runs."""
    t = unicodedata.normalize("NFKD", title or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.replace("/", "-").replace("\\", "-").replace(":", " -")
    t = re.sub(r'[<>:"|?*\x00-\x1f]', "", t)
    t = re.sub(r"\s+", " ", t).strip().strip(". ")
    t = t[:MAXLEN].strip().strip(". ")
    return t or f"untitled-{fallback[:8]}"


def build_plan() -> list[dict]:
    con = sqlite3.connect(DBS[0])
    rows = con.execute(
        "select paper_id, title, pdf_local_path from paper "
        "where pdf_local_path is not null and trim(pdf_local_path) != ''").fetchall()
    used, plan = {}, []
    for pid, title, old in rows:
        src = REPO / old if not pathlib.Path(old).is_absolute() else pathlib.Path(old)
        if not src.exists():
            continue
        base = sanitize(title, pid)
        name, i = f"{base}.pdf", 2
        while name.lower() in used:          # defensive; the corpus has none today
            name = f"{base} ({i}).pdf"
            i += 1
        used[name.lower()] = pid
        plan.append({"paper_id": pid, "old": str(src.relative_to(REPO)),
                     "new": str((PDF_DIR / name).relative_to(REPO)),
                     "title": title})
    return plan


def update_dbs(pairs: dict[str, str]) -> None:
    """pairs maps paper_id -> new repo-relative path.

    Keyed on paper_id, not on the old path string. An earlier version matched
    `where pdf_local_path = <old>` and silently missed 150 rows that store an
    ABSOLUTE path (from a previous renaming pass that used
    title_with_hash.pdf). The files moved and the rows did not, leaving 150
    dangling references. paper_id cannot drift that way.
    """
    for db in DBS:
        if not db.exists():
            continue
        table = TABLES[db.name]
        con = sqlite3.connect(db)
        cols = [c[1] for c in con.execute(f"PRAGMA table_info({table})")]
        if "pdf_local_path" not in cols:
            continue
        idcol = "paper_id"
        if idcol not in cols:
            continue
        n = 0
        for pid, new in pairs.items():
            cur = con.execute(
                f"update {table} set pdf_local_path=? where {idcol}=?", (new, pid))
            n += cur.rowcount
        con.commit()
        con.close()
        print(f"  {db.name}: updated {n} rows")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="actually move files")
    ap.add_argument("--revert", action="store_true", help="undo using the saved map")
    args = ap.parse_args()

    if args.revert:
        if not MAP.exists():
            raise SystemExit("no rename map; nothing to revert")
        plan = json.loads(MAP.read_text())["renames"]
        moved = 0
        for r in plan:
            new, old = REPO / r["new"], REPO / r["old"]
            if new.exists() and not old.exists():
                shutil.move(str(new), str(old))
                moved += 1
        update_dbs({r["paper_id"]: r["old"] for r in plan})
        print(f"reverted {moved} files")
        return

    plan = build_plan()
    names = [pathlib.Path(r["new"]).name.lower() for r in plan]
    if len(names) != len(set(names)):
        raise SystemExit("collision in plan; aborting")
    print(f"plan: {len(plan)} files")
    for r in plan[:3]:
        print(f"  {pathlib.Path(r['old']).name}  ->  {pathlib.Path(r['new']).name}")

    if not args.apply:
        print("\ndry run; pass --apply to move files")
        return

    MAP.parent.mkdir(parents=True, exist_ok=True)
    MAP.write_text(json.dumps({"generated": "2026-10-12", "renames": plan}, indent=1))
    print(f"wrote {MAP.relative_to(REPO)} (revert with --revert)")

    moved, skipped = 0, 0
    for r in plan:
        src, dst = REPO / r["old"], REPO / r["new"]
        if not src.exists():
            skipped += 1
            continue
        if dst.exists() and src.resolve() == dst.resolve():
            continue
        shutil.move(str(src), str(dst))
        moved += 1
    print(f"moved {moved} files ({skipped} missing)")
    update_dbs({r["paper_id"]: r["new"] for r in plan})


if __name__ == "__main__":
    main()

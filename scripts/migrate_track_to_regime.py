"""Retire `track` from the registries in favour of `regime`.

`split_regime_and_venue.py` separated the two things `track` had been doing —
which literature a paper belongs to, and where it published — into `regime`
and `venue` columns on the corpus. It stopped at the corpus. The RQ3 and RQ4
registries and the pair timeline kept a `track` field carrying the old
`Security` / `ML/AI` vocabulary, so every generator reading them reproduced a
name the paper no longer uses, and anyone analysing the registries directly
got the superseded coding.

The corpus `regime` column is authoritative, because it was restored from the
full-text re-coding, which judged regime from the paper itself rather than
from where it appeared. This joins each registry entry back to its paper and
replaces `track` with that judgement.

The two codings agree on 927 of 929 included papers, so this is a vocabulary
change with a two-paper tail rather than a renumbering. Any larger movement in
latex/numbers.tex after this runs is a bug in the migration, not a finding.

    python3 scripts/migrate_track_to_regime.py [--apply]
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import pathlib
import shutil

import openpyxl

REPO = pathlib.Path(__file__).resolve().parent.parent
XL = REPO / "data" / "exports" / "paper_dashboard_source.xlsx"
REG = REPO / "data" / "registries"
FALLBACK = {"Security": "security", "ML/AI": "safety",
            "security": "security", "safety": "safety"}


def corpus_regime() -> dict[str, str]:
    ws = openpyxl.load_workbook(XL, read_only=True)["Papers"]
    rows = list(ws.iter_rows(values_only=True))
    h = {k: i for i, k in enumerate(rows[0]) if k}
    out = {}
    for r in rows[1:]:
        pid = r[h["paper_id"]]
        reg = str(r[h["regime"]] or "").strip()
        if pid and reg:
            out[str(pid)] = reg
    return out


def migrate_entries(entries, regimes, stats):
    """Replace `track` with `regime`, keeping field order stable."""
    for e in entries:
        if "track" not in e:
            continue
        old = str(e.get("track") or "").strip()
        new = regimes.get(str(e.get("paper_id")))
        if new:
            stats["joined"] += 1
            if FALLBACK.get(old) and FALLBACK[old] != new:
                stats["changed"] += 1
                stats["changes"].append((e.get("paper_id"), old, new))
        else:
            new = FALLBACK.get(old)
            stats["unjoined"] += 1
            if new is None:
                stats["unmapped"] += 1
                continue
        # rebuild so `regime` sits where `track` was rather than at the end
        for k in list(e):
            v = e.pop(k)
            e[("regime" if k == "track" else k)] = (new if k == "track" else v)
    return entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    regimes = corpus_regime()
    print(f"corpus regime coding: {len(regimes)} papers")

    for name in ("rq3_pollution_registry.json", "rq4_defense_registry.json"):
        p = REG / name
        data = json.loads(p.read_text())
        entries = data["entries"] if isinstance(data, dict) and "entries" in data else data
        stats = collections.Counter()
        stats["changes"] = []
        migrate_entries(entries, regimes, stats)
        print(f"\n{name}: {len(entries)} entries, {stats['joined']} joined to corpus, "
              f"{stats['unjoined']} fell back on the old value, "
              f"{stats['unmapped']} unmapped")
        if stats["changed"]:
            print(f"  regime differs from track for {stats['changed']}:")
            for pid, old, new in stats["changes"]:
                print(f"    {pid}: {old} -> {new}")
        if a.apply:
            shutil.copy(p, p.with_name(p.stem + f".backup-regime-{stamp}.json"))
            p.write_text(json.dumps(data, indent=1))
            print("  written")

    p = REG / "pair_timeline.json"
    d = json.loads(p.read_text())
    n = 0
    for pair in d.get("pairs", []) + d.get("undated", []):
        for side in ("defense", "attack"):
            k = f"{side}_track"
            if k in pair:
                v = str(pair.pop(k) or "").strip()
                pair[f"{side}_regime"] = FALLBACK.get(v, v)
                n += 1
    print(f"\npair_timeline.json: {n} track fields renamed")
    if a.apply:
        shutil.copy(p, p.with_name(p.stem + f".backup-regime-{stamp}.json"))
        p.write_text(json.dumps(d, indent=1))
        print("  written")

    if not a.apply:
        print("\nreport only; pass --apply to write")


if __name__ == "__main__":
    main()

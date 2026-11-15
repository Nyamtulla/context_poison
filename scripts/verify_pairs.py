"""Collect the checklist verdicts on every (fix, cause) pair into one file.

Reads pair_pass/verify_out*.jsonl (new pairs and a 40-pair sample of the old)
and verify_old_out*.jsonl (the other old pairs), and writes
pair_pass/verified_pairs.json, which pair_tally.composite_pairs() reads:

  strong   pairs whose reader found all seven checks pass
  pooled   checks 1-5 and 7 pass but the number is pooled with other causes
           (check 6 fails): counted as tested, left out of outcome counts
  renamed  real runs filed under the wrong registry entry, re-filed under the
           name the reader gave, only when both names exist in the registry,
           every check other than 3 passed and the note does not say weak
"""
import json
import pathlib
import re

R = pathlib.Path(__file__).resolve().parent.parent / "data" / "registries"
P = R / "pair_pass"


def resolve(name, known):
    """The reader's name, or the one registry name it is a prefix of."""
    if name in known:
        return name
    hits = [k for k in known if k.startswith(name)]
    return hits[0] if len(hits) == 1 else None


def main():
    causes = {c["name"] for c in json.loads((P / "causes_list.json").read_text())}
    fixes = set(json.loads((P / "defense_names.json").read_text()))
    rows = [json.loads(l) for f in sorted(P.glob("verify_out*.jsonl")) + sorted(P.glob("verify_old_out*.jsonl"))
            for l in f.read_text().splitlines() if l.strip()]
    strong = sorted({(r["defense"], r["cause"]) for r in rows if r["verdict"] == "strong"})
    core = ("1_experiment", "2_fix_itself", "3_cause_itself", "4_same_run", "5_direction", "7_real_scale")
    pooled = sorted({(r["defense"], r["cause"]) for r in rows if r["verdict"] == "weak"
                     and all(r["checks"].get(k) is True for k in core)
                     and r["checks"].get("6_separate_result") is False} - set(strong))
    renamed, skipped = set(), 0
    other = ("1_experiment", "2_fix_itself", "4_same_run", "5_direction", "6_separate_result", "7_real_scale")
    for r in rows:
        if r["verdict"] != "not_a_pair":
            continue
        note = r.get("note") or ""
        m = re.search(r"correct pair:\s*(.+?)\s+[x×]\s+(.+?)(?:\s*\(|;|$)", note)
        if not m:
            continue
        d, c = resolve(m.group(1).strip(), fixes), resolve(m.group(2).strip().rstrip("."), causes)
        ok = all((r.get("checks") or {}).get(k) is True for k in other)
        if d and c and ok and "weak" not in note.lower():
            renamed.add((d, c))
        else:
            skipped += 1
    out = {"n_read": len(rows), "strong": strong, "pooled": pooled, "renamed": sorted(renamed - set(strong)),
           "renamings_not_counted": skipped,
           "verdicts": {v: sum(r["verdict"] == v for r in rows) for v in ("strong", "weak", "not_a_pair", "unsure")}}
    (P / "verified_pairs.json").write_text(json.dumps(out, indent=1))
    print(len(rows), "read;", len(strong), "strong;", len(pooled), "pooled;", len(out["renamed"]), "re-filed;", skipped, "renamings not counted")


if __name__ == "__main__":
    main()

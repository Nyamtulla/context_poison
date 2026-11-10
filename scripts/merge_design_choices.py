"""Merge the S2 design-choice batches into one registry and print the split.

Each batch file may hold stray records written by another batch's agent (a
shared helper script clashed while they ran), so a record is kept only from
the batch whose worklist owns its id.
"""
import collections
import json
import pathlib

D = pathlib.Path(__file__).resolve().parent.parent / "data/registries/design_choices"


def load_batches():
    out = {}
    for wl in sorted(D.glob("s2_batch[0-9].json")):
        own = {e["id"]: e for e in json.loads(wl.read_text())}
        recs = wl.with_suffix(".jsonl")
        seen = {}
        for line in recs.read_text().splitlines() if recs.exists() else []:
            if line.strip():
                r = json.loads(line)
                if r["id"] in own:
                    seen[r["id"]] = r          # last line for an id wins
        missing = set(own) - set(seen)
        if missing:
            print(f"{wl.name}: missing {sorted(missing)}")
        for i, r in seen.items():
            r["literature"] = own[i]["literature"]
            r["row"] = own[i]["row"]
            out[i] = r
    return out


def n_passages(r):
    """How many passages one evaluation item hands the method: 1 or many."""
    if r["context_unit"] == "one-passage":
        return "one"
    k = r.get("k_main")
    if isinstance(k, int):
        return "one" if k == 1 else "many"
    if r["context_unit"] in ("ranked-set", "joined-set"):
        return "many"
    return "unclear"


def poisoning_relevant(r):
    kinds = r.get("bad_text_kind") or []
    return any(k != "none" for k in kinds)


def main():
    recs = load_batches()
    for r in recs.values():
        r["n_passages"] = n_passages(r)
        r["in_scope"] = poisoning_relevant(r)
    (D / "s2_design_choices.json").write_text(
        json.dumps(sorted(recs.values(), key=lambda r: r["id"]), indent=1))
    print(len(recs), "records")
    for scope in (False, True):
        rows = [r for r in recs.values() if r["in_scope"] or not scope]
        print("\n== in-scope only (has misleading text)" if scope else "\n== all")
        for field in ("context_unit", "n_passages", "competes_with",
                      "memory_split", "adaptive_attack", "retrieval"):
            t = collections.defaultdict(collections.Counter)
            for r in rows:
                t[r["literature"]][str(r.get(field))] += 1
            print(f"{field}:")
            for lit in ("security", "safety"):
                print(f"  {lit:8} ({sum(t[lit].values())}): {dict(t[lit].most_common())}")


if __name__ == "__main__":
    main()

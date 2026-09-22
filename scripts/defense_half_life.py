"""How long does a published defense survive before something defeats it in print?

The reverse scan (scripts/reverse_scan_attack_papers.py) read ATTACK papers for
defense names, recovering pairs the defense-side scan structurally cannot see: a
defense evaluated inside an attack paper published after it. Most of those pairs
record the defense losing.

This turns that into a time series. For each recovered pair we date the defense
by its own paper and the defeat by the attack paper that recorded it, giving an
interval from publication to first published defeat.

Read the censoring note in the output before quoting any number. A defense with
no recorded defeat is NOT a defense that held; it is one nobody has attacked in
print, or one whose defeat we have not recovered. The population here is
survivors-of-a-biased-sample, and the honest reading is an upper bound on how
long defenses last, not an estimate of it.

    python3 scripts/defense_half_life.py
"""
from __future__ import annotations
import collections, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
REG = REPO / "data/registries"

# outcome strings the reverse scan uses that mean "the defense did not hold"
DEFEAT = {"defense fails", "defense largely fails", "defense insufficient",
          "defense exploited", "defense assumption broken", "defense broken",
          "defense degraded under adaptation", "defense evaded after adaptation"}
HELD = {"defense partially effective"}
NEUTRAL = {"evaluated", "evaluated (transfer test)"}


def main() -> None:
    import openpyxl
    ape = json.loads((REG / "attack_paper_evaluations.json").read_text())
    pairs = ape["confirmed_pairs"]
    raw3 = json.loads((REG / "rq3_pollution_registry.json").read_text())
    raw4 = json.loads((REG / "rq4_defense_registry.json").read_text())

    wb = openpyxl.load_workbook(REPO / "data/exports/paper_dashboard_source.xlsx", read_only=True)
    ws = wb["Papers"]
    hdr = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    i = {h: n for n, h in enumerate(hdr)}
    year, title = {}, {}
    for n, r in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        year[n], title[n] = r[i["year"]], r[i["title"]]
    wb.close()

    d_year = {d["name"]: year.get(int(d["row"])) for d in raw4}
    m_year = {m["name"]: year.get(int(m["row"])) for m in raw3}
    m_title = {m["name"]: title.get(int(m["row"])) for m in raw3}

    rows, undated = [], []
    for p in pairs:
        dn, mn, oc = p["defense"], p["mechanism"], (p.get("outcome") or "").strip()
        dy, my = d_year.get(dn), m_year.get(mn)
        kind = ("defeat" if oc in DEFEAT else
                "held" if oc in HELD else
                "neutral" if oc in NEUTRAL else "other")
        if dy is None or my is None:
            undated.append((dn, mn, oc, dy, my))
            continue
        rows.append({"defense": dn, "defense_year": dy, "mechanism": mn,
                     "attack_year": my, "gap_years": my - dy, "outcome": oc,
                     "kind": kind,
                     "attack_paper": p.get("source_paper") or m_title.get(mn, "")})

    print("=" * 74)
    print("DEFENSE HALF-LIFE  —  interval from defense publication to published defeat")
    print("=" * 74)
    print(f"\nreverse-scan pairs: {len(pairs)}   datable: {len(rows)}   undated: {len(undated)}")
    k = collections.Counter(r["kind"] for r in rows)
    print(f"  outcomes: " + "  ".join(f"{a}={b}" for a, b in k.most_common()))

    defeats = [r for r in rows if r["kind"] == "defeat"]
    print(f"\n--- defeats with both dates: {len(defeats)} ---")
    gaps = sorted(r["gap_years"] for r in defeats)
    if gaps:
        med = gaps[len(gaps) // 2]
        print(f"  gap (years) min={min(gaps)} median={med} max={max(gaps)} mean={sum(gaps)/len(gaps):.2f}")
        dist = collections.Counter(gaps)
        print("  distribution:")
        for g in sorted(dist):
            print(f"     {g:>2}y  {'#' * dist[g]:<14} {dist[g]}")
        within = {y: sum(1 for g in gaps if g <= y) for y in (0, 1, 2, 3)}
        print("  cumulative share of defeats occurring within N years of publication:")
        for y, c in within.items():
            print(f"     <= {y}y : {c}/{len(gaps)} = {100*c/len(gaps):.0f}%")

    print("\n--- every datable defeat, oldest defense first ---")
    for r in sorted(defeats, key=lambda x: (x["defense_year"], x["defense"])):
        print(f"  {r['defense'][:34]:<36} {r['defense_year']} -> {r['attack_year']} "
              f"(+{r['gap_years']}y)  {r['outcome']}")
        print(f"      defeated in: {str(r['attack_paper'])[:78]}")

    # how many DISTINCT defenses in the registry have any recorded defeat at all
    defeated = {r["defense"] for r in defeats}
    print(f"\n--- exposure ---")
    print(f"  distinct defenses with >=1 recorded defeat : {len(defeated)}")
    print(f"  defenses in the RQ4 registry               : {len(raw4)}")
    print(f"  share with any recorded defeat             : {100*len(defeated)/len(raw4):.1f}%")

    if undated:
        print(f"\n--- undated pairs ({len(undated)}), excluded from intervals ---")
        for dn, mn, oc, dy, my in undated[:12]:
            print(f"  {dn[:32]:<34} x {mn[:30]:<32} {oc}  (def_year={dy} atk_year={my})")

    print("""
--- CENSORING: read before quoting any of this ---
  These intervals describe defenses that were BOTH attacked in print AND whose
  defeat our reverse scan recovered. That is not a random sample of defenses.

  Three biases, all pushing the same way:
    1. Survivorship. A defense with no recorded defeat is not one that held --
       it is one nobody attacked in print, or whose defeat we missed. Only the
       share above has any recorded outcome at all.
    2. Attention. The defenses that get attacked are the well-known ones. An
       obscure defense is safe from attack papers, not from attacks.
    3. Right-censoring at the search cutoff. A 2025 defense has had less
       calendar time to be defeated than a 2023 one, so recent defenses look
       durable purely because the record has not caught up.

  Treat the median as an UPPER BOUND on how long a well-known defense survives
  contact with a determined attacker, not an estimate of defense lifetime.
""")

    out = REG / "defense_half_life.json"
    out.write_text(json.dumps({
        "generated": "2026-09-22",
        "note": "Intervals are upper-bounded and biased by survivorship, attention and right-censoring. See the script docstring.",
        "n_pairs": len(pairs), "n_datable": len(rows), "n_defeats": len(defeats),
        "gap_years": gaps,
        "median_gap_years": (gaps[len(gaps)//2] if gaps else None),
        "distinct_defenses_defeated": sorted(defeated),
        "share_of_registry_with_recorded_defeat": round(100*len(defeated)/len(raw4), 2),
        "rows": rows, "undated": [list(u) for u in undated],
    }, indent=1) + "\n")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

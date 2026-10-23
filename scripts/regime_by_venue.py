"""Regime against venue: where each kind of work publishes, and who it cites.

Two axes that were one column until 2026-10-22:

  regime  is an adversary involved (security) or does the context go wrong
          on its own (safety). A property of the work, coded from full text.
  venue   where the paper published. Observable; arXiv and unrecognised
          venues are "-" and carry no venue signal.

The taxonomy and transfer claims belong to REGIME. This script reports the
other thing: whether the two regimes publish to the same places, and whether
they cite across.
"""
import collections, json
import openpyxl

REPO = "data/"


def main():
    wb = openpyxl.load_workbook(REPO + "exports/paper_dashboard_source.xlsx",
                                read_only=True)
    rows = list(wb["Papers"].iter_rows(values_only=True))
    h = {k: i for i, k in enumerate(rows[0]) if k}
    inc = [r for r in rows[1:]
           if str(r[h["screening"]]).strip() != "Exclude"]
    reg = {r[h["paper_id"]]: str(r[h["regime"]] or "").strip() for r in inc}
    ven = {r[h["paper_id"]]: str(r[h["venue_community"]] or "-").strip()
           for r in inc}

    print("=== where each regime publishes ===")
    t = collections.Counter((reg[p], ven[p]) for p in reg)
    cols = ("security", "AI", "-")
    print(f"{'regime':10}" + "".join(f"{c:>12}" for c in cols) + f"{'named':>10}")
    for r in ("security", "safety"):
        named = t[(r, "security")] + t[(r, "AI")]
        print(f"{r:10}" + "".join(f"{t[(r, c)]:>12}" for c in cols)
              + f"{named:>10}")
    s_at_ai = t[("security", "AI")]
    s_at_sec = t[("security", "security")]
    print(f"\nOf security-regime papers with a named venue, "
          f"{s_at_ai} of {s_at_sec + s_at_ai} published at an AI venue.")
    print(f"Safety-regime papers at a security venue: "
          f"{t[('safety', 'security')]}.")

    print("\n=== who each regime cites, by the CITED paper's venue ===")
    net = json.load(open(REPO + "registries/citation_network_union.json"))
    flow = collections.Counter()
    for e in net["edges"]:
        a, b = e["citing"], e["cited"]
        if a in reg and b in reg:
            flow[(reg[a], ven[b])] += 1
    for r in ("security", "safety"):
        tot = sum(flow[(r, c)] for c in cols)
        if not tot:
            continue
        print(f"  {r:9} cites -> " + "  ".join(
            f"{c} {flow[(r, c)]:5} ({100*flow[(r, c)]/tot:4.1f}%)"
            for c in cols) + f"   total {tot}")

    print("\n=== who each regime cites, by the CITED paper's REGIME ===")
    flow2 = collections.Counter()
    for e in net["edges"]:
        a, b = e["citing"], e["cited"]
        if a in reg and b in reg:
            flow2[(reg[a], reg[b])] += 1
    for r in ("security", "safety"):
        tot = sum(flow2[(r, x)] for x in ("security", "safety"))
        if not tot:
            continue
        other = "safety" if r == "security" else "security"
        print(f"  {r:9} cites -> same {flow2[(r, r)]:5} "
              f"({100*flow2[(r, r)]/tot:4.1f}%)   "
              f"other {flow2[(r, other)]:5} "
              f"({100*flow2[(r, other)]/tot:4.1f}%)")


if __name__ == "__main__":
    main()

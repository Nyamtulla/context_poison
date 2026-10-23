"""Export the papers whose regime two independent signals do not settle.

Regime is the axis every taxonomy and transfer claim turns on: does this work
assume an adversary (security) or does the context go wrong on its own
(safety). Until 2026-10-22 it was a rename of `track`, which asked a
different question - which literature does this belong to.

Two signals already exist, both derived from full text: the track coding, and
the `threat_model` field, which often states the answer outright ("N/A -
non-adversarial; studies incidental degradation ... no attacker"). They agree
on 629 of the 706 papers that contributed a named technique. Those stand.

This exports the rest - the disagreements and the papers whose threat_model
is blank or says neither - so an agent reads only what is genuinely open.

Out: data/registries/raw/regime_batchNN.json
"""
import json, pathlib, re
import openpyxl

REPO = pathlib.Path(__file__).resolve().parent.parent
NONADV = re.compile(r"N/A\s*-\s*non-?adversarial|no adversary|non-?adversarial", re.I)
ADV = re.compile(r"\badversar|\battacker\b|\bthreat model\b|\bmalicious\b", re.I)


def derive(t):
    t = (t or "").strip()
    if t in ("", "None"):
        return None
    if NONADV.search(t):
        return "safety"
    return "security" if ADV.search(t) else None


def main():
    wb = openpyxl.load_workbook(
        REPO / "data/exports/paper_dashboard_source.xlsx", read_only=True)
    rows = list(wb["Papers"].iter_rows(values_only=True))
    h = {k: i for i, k in enumerate(rows[0]) if k}
    reg = REPO / "data/registries"
    contrib = set()
    for fn in ("rq3_pollution_registry.json", "rq4_defense_registry.json"):
        for e in json.loads((reg / fn).read_text()):
            if e.get("paper_id"):
                contrib.add(e["paper_id"])

    out = []
    for r in rows[1:]:
        if str(r[h["screening"]]).strip() == "Exclude":
            continue
        pid = r[h["paper_id"]]
        if pid not in contrib:
            continue
        cur = str(r[h["regime"]] or "").strip()
        d = derive(r[h["threat_model"]])
        if d is not None and d == cur:
            continue
        out.append({
            "paper_id": pid, "title": str(r[h["title"]] or ""),
            "current_regime": cur,
            "derived_from_threat_model": d or "",
            "why_open": "signals disagree" if d else "threat_model blank or unclear",
            "threat_model": str(r[h["threat_model"]] or "")[:900],
            "technical_summary": str(r[h["technical_summary"]] or "")[:900],
            "text": f"data/cache/pdf_text/{pid}.txt"})

    p = reg / "raw" / "regime_batch01.json"
    p.write_text(json.dumps(out, indent=1))
    n_dis = sum(1 for o in out if o["why_open"] == "signals disagree")
    print(f"{len(out)} papers open: {n_dis} disagreements, "
          f"{len(out) - n_dis} with no usable threat_model")
    print(f"wrote {p.relative_to(REPO)}")


if __name__ == "__main__":
    main()

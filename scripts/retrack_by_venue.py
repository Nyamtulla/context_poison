"""Set each paper's community from its publication venue.

The lead's advisor asked for this on 2026-10-22: decide Security or AI from
the venue the paper appeared in, and leave arXiv-only papers on the label
they already carry. It replaces a judgement with an observable fact for every
paper that has a venue, which is the point.

Three buckets, and the third one is why this script prints before it writes:

  SECURITY   a venue whose community is security (S&P, CCS, USENIX, NDSS...)
  AI         a venue whose community is AI, ML, NLP or IR (ACL, NeurIPS...)
  KEEP       arXiv, blank, or a venue that is neither - a generic IEEE
             conference, a megajournal, a software-engineering venue. These
             keep whatever label they have. Guessing here would put noise
             into the axis the paper's central claim rests on.

Dry run by default. Pass --apply to write.
"""
import argparse, collections, datetime, pathlib, re, shutil
import openpyxl

XL = "data/exports/paper_dashboard_source.xlsx"

SEC = [r"\bIEEE S&P\b", r"USENIX Security", r"\bCCS\b", r"\bNDSS\b", r"ESORICS",
       r"\bRAID\b", r"ACSAC", r"AsiaCCS", r"EuroS&P", r"DIMVA", r"\bWOOT\b",
       r"Secure and Trustworthy", r"Security and Privacy Workshops",
       r"cybersecurity", r"cyber warfare", r"Computer fraud & security",
       r"Information Forensics and Security", r"Priv\. Secur\.",
       r"Trust, Privacy and Security", r"CAMLIS", r"Defense \+ Security",
       r"Data and Application Security", r"Access Control Models",
       r"Confidential COmputing", r"EnCyCriS"]
AI = [r"\bACL\b", r"\bEMNLP\b", r"\bNAACL\b", r"\bAAAI\b", r"\bICLR\b",
      r"NeurIPS", r"\bICML\b", r"\bTACL\b", r"\bSIGIR\b", r"\bKDD\b",
      r"ICASSP", r"\bCOLM\b", r"IJCNLP", r"Trans\. Mach\. Learn\. Res\.",
      r"European Chapter of the Association", r"ACM Multimedia",
      r"Autonomous Agents", r"Language Resources", r"Artif\. Intell\.",
      r"Journal of Artificial Intelligence", r"Joint Conference on Neural Network",
      r"Conference on Language Modeling"]


def bucket(venue: str):
    v = (venue or "").strip()
    if not v or v.lower() == "arxiv":
        return None, "arXiv or blank"
    s = any(re.search(p, v, re.I) for p in SEC)
    a = any(re.search(p, v, re.I) for p in AI)
    if s and not a:
        return "Security", "security venue"
    if a and not s:
        return "ML/AI", "AI venue"
    return None, ("both lists match" if s and a else "venue is neither")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    wb = openpyxl.load_workbook(XL)
    ws = wb["Papers"]
    hdr = [c.value for c in ws[1]]
    vi, ti, si, pi = (hdr.index(x) + 1
                      for x in ("venue", "track", "screening", "paper_id"))

    tally, flips, kept = collections.Counter(), [], collections.Counter()
    changed = {}
    for row in range(2, ws.max_row + 1):
        if str(ws.cell(row, si).value or "").strip() == "Exclude":
            continue
        venue = str(ws.cell(row, vi).value or "")
        cur = str(ws.cell(row, ti).value or "").strip()
        new, why = bucket(venue)
        if new is None:
            tally["kept"] += 1
            kept[why] += 1
            continue
        tally[f"from venue -> {new}"] += 1
        if new != cur:
            flips.append((cur, new, venue.strip()[:40]))
            changed[str(ws.cell(row, pi).value or "").strip()] = new
            if args.apply:
                ws.cell(row, ti).value = new

    for k, v in tally.most_common():
        print(f"  {v:4}  {k}")
    print("  kept, by reason:")
    for k, v in kept.most_common():
        print(f"      {v:4}  {k}")
    print(f"\n  {len(flips)} papers would change label")
    for (cur, new), v in collections.Counter(
            (c, n) for c, n, _ in flips).most_common():
        print(f"      {v:4}  {cur or '(blank)'} -> {new}")
    for cur, new, v in flips[:15]:
        print(f"         {cur:9} -> {new:9}  {v}")

    if args.apply:
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        shutil.copy(XL, XL.replace(".xlsx", f".backup-venue-{stamp}.xlsx"))
        wb.save(XL)
        # build_timeline.py prefers the registry entry's own track over the
        # paper's, so a paper row alone would leave the pair matrix stale.
        import json
        for fn in ("rq3_pollution_registry.json", "rq4_defense_registry.json"):
            q = pathlib.Path("data/registries") / fn
            rows = json.loads(q.read_text())
            n = 0
            for e in rows:
                t = changed.get((e.get("paper_id") or "").strip())
                if t and (e.get("track") or "").strip() != t:
                    e["track"] = t
                    n += 1
            q.write_text(json.dumps(rows, indent=1))
            print(f"  {fn}: {n} entries retracked")
        print("applied; now run build_timeline.py and gen_paper_numbers.py")


if __name__ == "__main__":
    main()

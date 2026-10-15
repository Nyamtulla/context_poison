"""Did the paper PROPOSE this defense, or apply one that already existed?

`is_extension_of` is populated on 5% of RQ4 entries, so the registry cannot
currently tell a method a paper invented from one it took off the shelf. That
gap is what let two deep-research agent frameworks be counted as fixes for
context rot: both "address" it in their framing and neither proposes anything
about contaminated context.

The signal is cheap and does not need a full read. A paper introduces its own
contribution in a recognisable way ("we propose X", "we introduce X", "our X")
and refers to prior work in an equally recognisable way ("X [12]", "X (Author
et al., 2024)", "following X", "we use X"). This script finds every mention of
the defense's name in the PDF text and classifies the surrounding window.

Output is a vote per entry plus the evidence span, so every call is auditable
and the ambiguous ones can be sent to a human rather than guessed at.

    python3 scripts/classify_defense_origin.py
"""
import collections
import json
import pathlib
import re
import sys

import openpyxl

REPO = pathlib.Path(__file__).resolve().parent.parent
R = REPO / "data" / "registries"

# "we propose NAME", "NAME, our ...", "we present NAME"
PROPOSE = re.compile(
    r"\b(we|this (paper|work|study))\s+(propose|present|introduce|develop|design|"
    r"build|implement|contribute)\w*\b|\bour (proposed |novel |new )?\b|"
    r"\bwe call (it|this|our)\b|\bis our\b|\bwe name\b|\bwe term\b", re.I)
# "NAME [12]", "NAME (Smith et al., 2023)", "following NAME", "we adopt NAME"
PRIOR = re.compile(
    r"\[\d{1,3}(,\s*\d{1,3})*\]|\(\w+ et al\.?,?\s*\d{4}\)|\bet al\.|"
    r"\b(prior|previous|existing|earlier|recent) (work|approach|method|system)|"
    r"\bwe (use|adopt|apply|employ|reuse|build on|follow)\b|\bfollowing\b|"
    r"\bproposed by\b|\bintroduced by\b|\bbaseline\b", re.I)
WIN = 220


def load_text(path):
    try:
        import pymupdf
    except ImportError:
        import fitz as pymupdf
    try:
        d = pymupdf.open(path)
        t = "\n".join(p.get_text() for p in d)
        d.close()
        return t
    except Exception:
        return ""


def search_keys(name):
    """The strings worth looking for: the acronym, and the long form."""
    name = re.sub(r"\s*\(.*?\)\s*", " ", name).strip()
    keys = []
    acro = re.match(r"^([A-Z][A-Za-z0-9\-]{1,14})\b", name)
    if acro and not acro.group(1).isalpha() or (acro and acro.group(1).isupper()):
        keys.append(acro.group(1))
    if acro:
        keys.append(acro.group(1))
    head = " ".join(name.split()[:4])
    if len(head) > 6:
        keys.append(head)
    seen, out = set(), []
    for k in keys:
        if k.lower() not in seen and len(k) > 2:
            seen.add(k.lower()); out.append(k)
    return out[:2]


def main():
    r4 = json.loads((R / "rq4_defense_registry.json").read_text())
    wb = openpyxl.load_workbook(
        REPO / "data" / "exports" / "paper_dashboard_source.xlsx", read_only=True)
    ws = wb["Papers"]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    hdr = list(rows[0])
    I = {k: hdr.index(k) for k in ("paper_id", "pdf_local_path")}
    meta = {r[I["paper_id"]]: r for r in rows[1:]}

    out, counts = [], collections.Counter()
    for i, e in enumerate(r4, 1):
        name = str(e.get("name") or "")
        rec = {"defense_name": name, "row": e.get("row"),
               "paper_id": e.get("paper_id")}
        if name.startswith("UNNAMED"):
            rec.update(origin="needs_read", evidence="entry has no name to search")
            counts["needs_read"] += 1; out.append(rec); continue
        m = meta.get(e.get("paper_id"))
        p = m[I["pdf_local_path"]] if m else None
        if not p or not pathlib.Path(p).exists():
            rec.update(origin="needs_read", evidence="no PDF")
            counts["needs_read"] += 1; out.append(rec); continue
        txt = load_text(p)
        if not txt:
            rec.update(origin="needs_read", evidence="PDF unreadable")
            counts["needs_read"] += 1; out.append(rec); continue

        # Vote-counting over the whole document does not work. A paper
        # proposes its method once and cites other work fifty times, so
        # related-work citation density buries the proposal sentence. The
        # first version classified SafeSieve as applied_as_is on evidence
        # that literally read "we present SafeSieve".
        #
        # The proposal claim lives in the abstract, the intro and the
        # contributions list, and it puts the verb within a short distance of
        # the name. So: look only at the head of the document, and require
        # proximity rather than counting.
        head = txt[:int(len(txt) * 0.18)]
        CLAIM = re.compile(
            r"\b(we|this (paper|work|study))\s+\w{0,12}\s*"
            r"(propose|present|introduce|develop|design|build|contribute)\w*\b"
            r"[^.]{0,120}?%s|%s[^.]{0,90}?\b(is|are)\s+(our|a novel|a new)\b",
            re.I)
        prop = prior = 0; best = ""
        for key in search_keys(name):
            k = re.escape(key)
            mm = re.search(CLAIM.pattern % (k, k), head, re.I)
            if mm:
                prop += 1
                best = mm.group(0).replace("\n", " ").strip()[:240]
                break
        if not prop:
            # name appears only beside citation markers anywhere in the paper
            cited = 0
            for key in search_keys(name):
                for m2 in re.finditer(re.escape(key), txt):
                    w = txt[max(0, m2.start()-90):m2.end()+90].replace("\n", " ")
                    if PRIOR.search(w): cited += 1
                    if not best and cited > 1: best = w.strip()[:240]
            prior = cited
        if prop:
            origin = "proposed"
        elif prior >= 3:
            origin = "applied_as_is"
        elif prior:
            origin = "ambiguous"
        else:
            origin = "needs_read"
        rec.update(origin=origin, propose_hits=prop, prior_hits=prior,
                   evidence=best or "")
        counts[origin] += 1
        out.append(rec)
        if i % 100 == 0:
            print(f"  ...{i}/{len(r4)}", flush=True)

    (R / "defense_origin.json").write_text(json.dumps(
        {"generated": "2026-10-15", "method": __doc__.strip().split("\n\n")[0],
         "counts": dict(counts), "defenses": out}, indent=1))
    n = len(r4)
    print(f"\n{n} defenses")
    for k, v in counts.most_common():
        print(f"  {v:>4}  {100*v/n:>5.1f}%  {k}")


if __name__ == "__main__":
    main()

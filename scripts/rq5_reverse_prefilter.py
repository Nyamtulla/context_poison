"""Find OLD defenses that may have been tested against NEWLY-registered mechanisms.

Phase 6 of the rebuild skill warns that a new mechanism can be tested by an old
defense. That matters a lot for the 2026-09-21 screening delta, because the
mechanisms it added are not all new science -- several are foundational attacks
(Open-Prompt-Injection's Combined Attack, Spotlighting's threat set, the BIPIA
attack suite) that defenses already in the corpus routinely evaluate against.
Those pairs exist in the literature and are simply absent from our matrix
because the attack's own paper was missing from the corpus until now.

Re-reading 479 defense papers to find them would be enormous. Instead this does
a cheap, deliberately HIGH-RECALL text prefilter over the evaluation text the
Excel already holds, emitting (defense, mechanism) candidates for an agent to
adjudicate. False positives here are fine and expected -- the agent throws them
out. A false negative is invisible, so the matching is loose on purpose.

    python3 scripts/rq5_reverse_prefilter.py [--slices 4] [--min-token-len 4]
"""
from __future__ import annotations
import argparse, csv, json, re, sys
from pathlib import Path

import openpyxl
from rapidfuzz import fuzz

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "data/registries/raw"
REG = REPO / "data/registries"

STOP = {"the","and","for","with","from","via","using","based","attack","attacks",
        "injection","prompt","prompts","llm","llms","model","models","unnamed",
        "context","agent","agents","against","into","that","this","novel","new"}


def tokens(name, min_len):
    return {w for w in re.findall(r"[a-z0-9]+", name.lower())
            if len(w) >= min_len and w not in STOP}


def proper_name_tokens(name):
    """The parts of a mechanism name another paper could actually cite it BY.

    This is the whole trick for the reverse pass. A mechanism with a proper name
    (BIPIA, CyberSecEval, HackAPrompt, Open-Prompt-Injection) gets referenced by
    that name in the papers that evaluate on it, so an exact token match is
    strong evidence. A mechanism with a purely descriptive registry name
    ("steganographic prompt injection (multi-domain spatial/frequency)") cannot
    be cited by name at all -- nobody writes that phrase -- so matching its
    ordinary words just flags every paper containing "frequency" and buries the
    real pairs in noise.

    So: only capitalised or all-caps tokens count, and only outside the leading
    position where ordinary sentence capitalisation lives."""
    out = set()
    for raw in re.findall(r"[A-Za-z][A-Za-z0-9\-]+", name):
        t = raw.strip("-")
        if len(t) < 3 or t.lower() in STOP:
            continue
        if t.isupper() and len(t) >= 3:          # BIPIA, RTO, IPI
            out.add(t.lower())
        elif t[0].isupper() and any(c.isupper() for c in t[1:]):   # CyberSecEval
            out.add(t.lower())
        elif t[0].isupper() and not t.islower():                    # Tensor, Trust
            out.add(t.lower())
    return {t for t in out if t not in AMBIGUOUS}


# Capitalised tokens that are NOT usable as citations, because they are either
# ordinary vocabulary that happens to be capitalised in a registry name, or --
# worse -- an acronym that collides with a different, far more common concept.
# `ipi` is the killer: it is this field's standard abbreviation for *indirect*
# prompt injection, so matching row 1085's "Image-based Prompt Injection (IPI)"
# on it flags every indirect-injection defense in the corpus. Each entry below
# was added after inspecting what it actually matched.
AMBIGUOUS = {
    "attack", "attacks", "prompt", "injection", "benchmark", "unnamed", "combined",
    "ipi",            # = indirect prompt injection, not "image-based"
    "cot",            # chain-of-thought, ubiquitous
    "blind", "physical", "virtual", "overflow", "interruption", "graph-based",
    "image-based", "gpts", "direct", "indirect", "multi", "cross", "zero",
    "reasoning", "adaptive", "universal", "automatic", "preemptive", "message",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slices", type=int, default=4)
    ap.add_argument("--min-token-len", type=int, default=4)
    args = ap.parse_args()

    mechs = json.loads((REG / "rq3_pollution_registry.json").read_text())
    new_mechs = [m for m in mechs if int(m["row"]) >= 1010]
    print(f"newly-registered mechanisms (delta rows): {len(new_mechs)}")

    # every (defense_row, mechanism) pair already asserted, so we don't re-ask
    have = set()
    for fp in list(RAW.glob("rq5_batch*.csv")) + list(RAW.glob("rq5_delta_batch*.csv")):
        with open(fp) as f:
            for r in csv.DictReader(f):
                try:
                    have.add((int(r["defense_row"]), (r.get("matched_mechanism_name") or "").strip()))
                except (KeyError, ValueError):
                    pass
    print(f"pairs already asserted: {len(have)}")

    defs_ = json.loads((REG / "rq4_defense_registry.json").read_text())
    old_defs = [d for d in defs_ if int(d["row"]) < 1010]
    print(f"pre-delta defenses to re-check: {len(old_defs)}")

    wb = openpyxl.load_workbook(REPO / "data/exports/paper_dashboard_source.xlsx", read_only=True)
    ws = wb["Papers"]
    hdr = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    i = {h: n for n, h in enumerate(hdr)}
    text = {}
    for n, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        blob = " ".join(str(row[i[k]] or "") for k in
                        ("baselines_compared", "key_result", "technical_summary",
                         "datasets_benchmarks", "title"))
        text[n] = (blob, blob.lower())
    wb.close()

    # document frequency over the defense corpus, to decide which tokens
    # actually discriminate
    import collections
    doc_freq = collections.Counter()
    n_docs = 0
    for d in old_defs:
        _, low = text.get(int(d["row"]), ("", ""))
        if not low:
            continue
        n_docs += 1
        doc_freq.update(set(re.findall(r"[a-z0-9]+", low)))
    print(f"defense docs scanned for token frequencies: {n_docs}")

    cands = []
    for d in old_defs:
        drow = int(d["row"])
        blob, low = text.get(drow, ("", ""))
        if not low:
            continue
        for m in new_mechs:
            name = m["name"]
            if (drow, name) in have:
                continue
            nl = name.lower()
            hit, why = False, ""
            if len(nl) >= 8 and nl in low:
                hit, why = True, "exact name substring"
            else:
                pn = proper_name_tokens(name)
                # a proper-name token is only evidence if it is also RARE in the
                # defense corpus; a name like "Overflow" is both capitalised and
                # everywhere, which is not a citation
                pn = {w for w in pn if doc_freq.get(w, 0) <= 0.10 * n_docs}
                present = {w for w in pn if re.search(rf"\b{re.escape(w)}\b", low)}
                if present:
                    hit, why = True, f"proper-name token: {', '.join(sorted(present)[:3])}"
            if hit:
                cands.append({"defense_row": drow, "defense_name": d["name"],
                              "candidate_mechanism_name": name,
                              "mechanism_from_paper": m.get("title", "")[:90],
                              "why_flagged": why,
                              "defense_evidence_text": blob[:2200]})
    print(f"candidate pairs to adjudicate: {len(cands)}")
    if not cands:
        return
    per_mech = {}
    for c in cands:
        per_mech[c["candidate_mechanism_name"]] = per_mech.get(c["candidate_mechanism_name"], 0) + 1
    print("\ntop flagged mechanisms:")
    for k, v in sorted(per_mech.items(), key=lambda x: -x[1])[:12]:
        print(f"   {v:>4}  {k[:66]}")

    n = max(1, min(args.slices, len(cands)))
    size = -(-len(cands) // n)
    for s in range(n):
        chunk = cands[s * size:(s + 1) * size]
        if not chunk:
            continue
        fp = RAW / f"rq5_reverse_slice{s+1}.json"
        fp.write_text(json.dumps(chunk, indent=1) + "\n")
        print(f"  {fp.name}: {len(chunk)} candidates")


if __name__ == "__main__":
    main()

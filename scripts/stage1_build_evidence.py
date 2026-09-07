"""Stage 1 of citation-grounded coverage: build the evidence bundle for each
candidate (defense, mechanism) pair.

A candidate pair exists when a defense paper CITES the paper that introduced a
mechanism currently recorded as never-defended. Citing is not evaluating, so
each pair needs adjudication - this script gathers the evidence a human (or
model) needs to make that call, and makes no judgment itself beyond a
section-based hint.

For every pair it searches the defense paper's full text for the mechanism's
name (plus spacing/hyphenation variants), records which section each mention
falls in, and captures a window of surrounding text. Output is a JSON bundle
keyed by pair.

    python scripts/stage1_build_evidence.py [--out FILE]
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import registry_source

REPO = Path(__file__).resolve().parent.parent
WINDOW = 260  # chars of context captured either side of a mention

# Section headers that indicate the mention sits in an evaluation context vs.
# merely a framing/related-work one. Matched against the nearest preceding
# header, so they only act as a hint - the captured text is what decides.
EVAL_SECTION_RE = re.compile(
    r"\b(experiment|evaluat|result|setup|benchmark|attack setting|threat model|"
    r"baseline|ablation|implementation|dataset)", re.I)
FRAMING_SECTION_RE = re.compile(r"\b(abstract|introduction|related work|background|conclusion|discussion)", re.I)
SECTION_RE = re.compile(r"^\s*((?:\d+(?:\.\d+)*\s+)?[A-Z][A-Za-z \-/&]{3,60})\s*$", re.M)


def pdf_text(path: Path) -> str:
    try:
        out = subprocess.run(["pdftotext", "-q", str(path), "-"],
                             capture_output=True, timeout=120)
        return out.stdout.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def name_variants(name: str) -> list[str]:
    """A mechanism's registry name won't appear verbatim in someone else's
    paper. Strip our own annotations and generate the forms a citing paper
    would plausibly use."""
    n = re.sub(r"^UNNAMED:\s*", "", name).strip()
    n = re.sub(r"\s*\([^)]*\)\s*$", "", n).strip()  # drop trailing gloss
    variants = {n}
    # acronym in parens anywhere, e.g. "Cross-Session Stored Prompt Injection (XSPI)"
    for m in re.finditer(r"\(([A-Z][A-Za-z0-9\-]{1,12})\)", name):
        variants.add(m.group(1))
    variants.add(n.replace("-", " "))
    variants.add(n.replace(" ", ""))
    # CamelCase split: PoisonedRAG -> "Poisoned RAG"
    if re.search(r"[a-z][A-Z]", n):
        variants.add(re.sub(r"(?<=[a-z])(?=[A-Z])", " ", n))
    out = []
    for v in variants:
        v = v.strip()
        # Very short or very generic strings produce garbage matches; the
        # descriptive labels we assigned to UNNAMED mechanisms are phrases,
        # not names, so they're searched as-is only when long enough.
        if len(v) >= 4:
            out.append(v)
    return sorted(set(out), key=len, reverse=True)


def sections_index(text: str) -> list[tuple[int, str]]:
    return [(m.start(), m.group(1).strip()) for m in SECTION_RE.finditer(text)]


def section_at(idx: int, sections: list[tuple[int, str]]) -> str:
    cur = ""
    for pos, name in sections:
        if pos <= idx:
            cur = name
        else:
            break
    return cur


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "data/registries/stage1_evidence.json"))
    args = ap.parse_args()

    reg = registry_source.load_all()
    papers = {p["paper_id"]: p for p in registry_source.load_papers()}

    con = sqlite3.connect(REPO / "data/context_sok.db")
    cur = con.cursor()
    cur.execute("select citing_paper_id, cited_paper_id from citation_edges")
    citers = defaultdict(set)
    for a, b in cur.fetchall():
        citers[b].add(a)
    con.close()

    defs_by_paper = defaultdict(list)
    for x in reg["defenses"]:
        if x["source_paper_id"]:
            defs_by_paper[x["source_paper_id"]].append(x)

    uncovered = [m for m in reg["mechanisms"] if not m["has_any_defense"]]

    # group by defense paper so each PDF is parsed exactly once
    by_def_paper = defaultdict(list)
    for m in uncovered:
        for dp in citers.get(m["source_paper_id"], set()) & set(defs_by_paper):
            by_def_paper[dp].append(m)

    results = []
    for i, (dp, mechs) in enumerate(sorted(by_def_paper.items()), 1):
        paper = papers.get(dp) or {}
        path = paper.get("pdf_local_path")
        text = pdf_text(Path(path)) if path and Path(path).exists() else ""
        sections = sections_index(text) if text else []
        print(f"[{i}/{len(by_def_paper)}] {str(paper.get('title'))[:60]:60s} "
              f"pdf={'y' if text else 'n'} mechs={len(mechs)}", flush=True)

        for m in mechs:
            hits = []
            if text:
                for variant in name_variants(m["mechanism_name"]):
                    for mt in re.finditer(re.escape(variant), text, re.I):
                        s = max(0, mt.start() - WINDOW)
                        sec = section_at(mt.start(), sections)
                        hits.append({
                            "variant": variant,
                            "section": sec,
                            "section_kind": ("eval" if EVAL_SECTION_RE.search(sec)
                                             else "framing" if FRAMING_SECTION_RE.search(sec)
                                             else "unknown"),
                            "context": " ".join(text[s: mt.end() + WINDOW].split()),
                        })
                    if hits:
                        break  # longest matching variant wins; don't stack near-duplicates
            for d in defs_by_paper[dp]:
                results.append({
                    "defense": d["defense_name"],
                    "defense_paper_id": dp,
                    "defense_paper_title": paper.get("title"),
                    "defense_intervention_point": d["intervention_point"],
                    "mechanism": m["mechanism_name"],
                    "mechanism_paper_title": m["source_paper_title"],
                    "pdf_available": bool(text),
                    "n_mentions": len(hits),
                    "mentions": hits[:6],
                    "baselines_compared": (paper.get("baselines_compared") or "")[:600],
                    "key_result": (paper.get("key_result") or "")[:600],
                })

    Path(args.out).write_text(json.dumps(results, indent=1))
    n_hits = sum(1 for r in results if r["n_mentions"])
    print(f"\npairs: {len(results)} | with >=1 textual mention: {n_hits} | "
          f"no PDF: {sum(1 for r in results if not r['pdf_available'])}")
    print("wrote", args.out)


if __name__ == "__main__":
    main()

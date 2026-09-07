"""Stage 1 (main pass): full-text scan of every defense paper for every
currently-uncovered mechanism name.

Why this rather than citation matching: RQ5 matched mechanisms to defenses
using only the *extracted summary fields* (baselines_compared, key_result,
technical_summary), so an attack named only in a results table or an appendix
was invisible to it. Citation-based candidate generation turned out to have
its own gap - it found RETA->PISmith and RETA->RL-Hammer but missed
RETA->AutoInject, which this full-text scan catches - so name-in-full-text is
the higher-recall signal and citations are a secondary one.

The scan is deliberately recall-first and precision-last: it collects every
mention with its surrounding context and strips the ones that fall in a
bibliography, then leaves the evaluated/claimed/related-work call to a human
adjudication pass over the emitted evidence file.

    python scripts/stage1_fulltext_scan.py [--out FILE]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import registry_source

REPO = Path(__file__).resolve().parent.parent
CACHE = REPO / "data/cache/pdf_text"
WINDOW = 300

# A mention inside the reference list is a citation, never an evaluation. The
# bibliography is detected by locating the last occurrence of a references
# heading; everything after it is excluded from the "body" text.
REFS_RE = re.compile(r"\n\s*(?:\d+\s+)?(?:R\s?E\s?F\s?E\s?R\s?E\s?N\s?C\s?E\s?S|References|Bibliography)\s*\n")
EVAL_HINT_RE = re.compile(
    r"\b(we (?:evaluate|test|compare|consider|use|implement|run)|evaluated against|"
    r"attack success rate|ASR|baseline|our experiments|experimental setup|"
    r"table \d|figure \d|we adopt|following \[)", re.I)


def pdf_text(pid: str, path: Path) -> str:
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = CACHE / f"{pid}.txt"
    if cached.exists():
        return cached.read_text(errors="ignore")
    try:
        out = subprocess.run(["pdftotext", "-q", str(path), "-"], capture_output=True, timeout=120)
        text = out.stdout.decode("utf-8", errors="ignore")
    except Exception:
        text = ""
    cached.write_text(text)
    return text


def split_body(text: str) -> str:
    """Everything before the (last) references heading."""
    matches = list(REFS_RE.finditer(text))
    return text[: matches[-1].start()] if matches else text


def name_variants(name: str) -> list[str]:
    n = re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()
    variants = {n}
    for m in re.finditer(r"\(([A-Z][A-Za-z0-9\-]{2,12})\)", name):
        variants.add(m.group(1))
    if re.search(r"[a-z][A-Z]", n):
        variants.add(re.sub(r"(?<=[a-z])(?=[A-Z])", " ", n))
    variants.add(n.replace("-", " "))
    # Require enough length that the string is a name, not a common word.
    return sorted({v.strip() for v in variants if len(v.strip()) >= 5}, key=len, reverse=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "data/registries/stage1_fulltext_hits.json"))
    args = ap.parse_args()

    reg = registry_source.load_all()
    papers = {p["paper_id"]: p for p in registry_source.load_papers()}
    defenses = [d for d in reg["defenses"] if d["source_paper_id"]]

    uncovered = [m for m in reg["mechanisms"]
                 if not m["has_any_defense"] and not m["mechanism_name"].startswith("UNNAMED")]
    targets = {m["mechanism_name"]: name_variants(m["mechanism_name"]) for m in uncovered}
    mech_paper = {m["mechanism_name"]: m["source_paper_id"] for m in uncovered}
    print(f"scanning {len(defenses)} defenses x {len(targets)} uncovered mechanisms")

    # one text extraction per defense paper, cached on disk
    by_paper = {}
    for d in defenses:
        by_paper.setdefault(d["source_paper_id"], []).append(d)

    hits = []
    for i, (pid, ds) in enumerate(sorted(by_paper.items()), 1):
        p = papers.get(pid) or {}
        path = p.get("pdf_local_path")
        if not path or not Path(path).exists():
            continue
        text = pdf_text(pid, Path(path))
        if not text:
            continue
        body = split_body(text)
        if i % 50 == 0:
            print(f"  [{i}/{len(by_paper)}]", flush=True)

        for mech, variants in targets.items():
            if mech_paper[mech] == pid:
                continue  # a paper can't independently corroborate its own mechanism
            for v in variants:
                found = list(re.finditer(re.escape(v), body, re.I))
                if not found:
                    continue
                ctxs = []
                for mt in found[:4]:
                    s = max(0, mt.start() - WINDOW)
                    ctx = " ".join(body[s: mt.end() + WINDOW].split())
                    ctxs.append({"context": ctx, "eval_hint": bool(EVAL_HINT_RE.search(ctx))})
                for d in ds:
                    hits.append({
                        "defense": d["defense_name"],
                        "defense_paper_id": pid,
                        "defense_paper_title": p.get("title"),
                        "defense_intervention_point": d["intervention_point"],
                        "defense_validated_against": d["validated_against"],
                        "mechanism": mech,
                        "matched_variant": v,
                        "n_body_mentions": len(found),
                        "any_eval_hint": any(c["eval_hint"] for c in ctxs),
                        "contexts": ctxs,
                    })
                break  # longest variant wins

    Path(args.out).write_text(json.dumps(hits, indent=1))
    pairs = {(h["defense"], h["mechanism"]) for h in hits}
    strong = {(h["defense"], h["mechanism"]) for h in hits if h["any_eval_hint"]}
    print(f"\nbody-text hits: {len(hits)} rows | distinct (defense, mechanism) pairs: {len(pairs)}")
    print(f"pairs with an evaluation-language hint: {len(strong)}")
    print(f"distinct mechanisms implicated: {len({h['mechanism'] for h in hits})}")
    print("wrote", args.out)


if __name__ == "__main__":
    main()

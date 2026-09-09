"""Reverse scan: read ATTACK papers looking for DEFENSE names.

RQ5 established coverage by reading defense papers and looking for mechanism
names. That direction has a structural blind spot: a defense evaluated inside
an attack paper published *after* it can never appear, because the defense
paper predates the attack. This is exactly how a new attack demonstrates it
beats the state of the art, so the blind spot sits over the most interesting
evidence in the corpus.

This script runs the scan the other way - every mechanism's source paper is
searched for every named defense in the RQ4 registry - and emits candidates
with their surrounding context for adjudication. It does not decide anything;
the evaluated/related-work call is made by reading the emitted contexts.

Three filters, each one earned by a false positive in the first ad-hoc run:

  * self-match. A paper proposing both the mechanism and the defense is not
    independent corroboration, so any candidate whose two sides share a source
    paper is dropped outright.
  * substring. "Sentinel" matched inside "DataSentinel" on three papers.
    Matching is word-boundary anchored, and when several defense names match
    the same span only the longest survives.
  * own component. "Focus Stage" and "Prometheus Export" are parts of the
    attack paper's own architecture that happen to share a name with a
    defense. Single common-word variants are not searched at all, and short
    names are flagged `weak_name` so adjudication looks at them harder.
  * acronym-is-a-word. A great many defenses are backronyms - SHIFT, TRACE,
    DRIFT, ITEM, PARSE - and matching those case-insensitively turns every
    ordinary use of the word into a candidate. In the first full run that was
    85 of 133. All-caps acronyms are therefore matched case-SENSITIVELY, so
    "we shift the distribution" no longer looks like a defense evaluation.

    python scripts/reverse_scan_attack_papers.py [--out FILE] [--uncovered-only]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import registry_source
from stage1_fulltext_scan import pdf_text, split_body, EVAL_HINT_RE

REPO = Path(__file__).resolve().parent.parent
WINDOW = 320

# Defense "names" that are ordinary English and would match constantly. Every
# one of these produced a false positive or is obviously going to.
STOPNAMES = {"still", "focus", "shield", "guard", "sentinel", "armor", "filter",
             "monitor", "firewall", "sandbox", "prometheus", "aegis", "atlas",
             "oracle", "gatekeeper", "watchdog", "anchor", "beacon", "compass"}


def defense_variants(name: str) -> list[str]:
    """Searchable forms of a defense name, minus anything too generic.

    The parenthetical expansion is dropped ("MELON (Masked re-Execution...)"
    -> "MELON") and any bracketed acronym is added, but a single lowercase
    word on the stopname list is never searched.
    """
    base = re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()
    variants = {base}
    # Also drop a mid-string parenthetical, which is where a compound name
    # keeps its acronym: "Plan-Then-Execute (PTE) architecture for web agents".
    variants.add(re.sub(r"\s*\([^)]*\)\s*", " ", name).strip())
    for m in re.finditer(r"\(([A-Z][A-Za-z0-9\-+ ]{1,24})\)", name):
        variants.add(m.group(1).strip())
        # ...and the words the acronym stands for, which is what a table
        # actually prints: "Plan-Then-Execute (PTE) architecture for web
        # agents" is cited as "Plan-Then-Execute".
        head = name[: m.start()].strip()
        if head:
            variants.add(head)
    if re.search(r"[a-z][A-Z]", base):
        variants.add(re.sub(r"(?<=[a-z])(?=[A-Z])", " ", base))
    out = []
    for v in variants:
        v = v.strip()
        if len(v) < 3 or v.lower() in STOPNAMES:
            continue
        out.append(v)
    return sorted(set(out), key=len, reverse=True)


def is_acronym(v: str) -> bool:
    """A short capitalised token, which must be matched case-sensitively.

    Covers both SHIFT and CoM: the latter matched case-insensitively hit every
    ".com" in every URL in the corpus (41 candidates from one defense).
    """
    return (len(v) <= 8 and " " not in v
            and sum(1 for c in v if c.isupper()) >= 2)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "data/registries/reverse_scan_hits.json"))
    ap.add_argument("--uncovered-only", action="store_true",
                    help="restrict to mechanisms with no confirmed defense (the first pass's scope)")
    args = ap.parse_args()

    reg = registry_source.load_all()
    papers = {p["paper_id"]: p for p in registry_source.load_papers()}

    # UNNAMED defenses have no term the literature could use, so they are
    # unsearchable by construction - the same permanent floor Stage 1 hit from
    # the other side.
    named = [d for d in reg["defenses"]
             if d["defense_name"] and not d["defense_name"].startswith("UNNAMED")]
    dvars = {d["defense_name"]: defense_variants(d["defense_name"]) for d in named}
    dpaper = {d["defense_name"]: d["source_paper_id"] for d in named}
    dmeta = {d["defense_name"]: d for d in named}

    mechs = [m for m in reg["mechanisms"] if m["source_paper_id"]]
    if args.uncovered_only:
        mechs = [m for m in mechs if not m["has_any_defense"]]

    # already-confirmed pairs, so the report can separate "new" from "re-found"
    known = {(p["defense_name"], p["mechanism_name"]) for p in reg["pairs"]}

    print(f"scanning {len(mechs)} mechanism papers x {len(named)} named defenses")

    hits, no_pdf = [], 0
    for i, m in enumerate(mechs, 1):
        pid = m["source_paper_id"]
        p = papers.get(pid) or {}
        path = p.get("pdf_local_path")
        if not path or not Path(path).exists():
            no_pdf += 1
            continue
        body = split_body(pdf_text(pid, Path(path)))
        if not body:
            no_pdf += 1
            continue
        if i % 25 == 0:
            print(f"  [{i}/{len(mechs)}]", flush=True)

        # Longest-first, and a span already claimed by a longer defense name is
        # not offered to a shorter one - this is what kills "Sentinel" inside
        # "DataSentinel".
        claimed: list[tuple[int, int]] = []
        order = sorted(dvars.items(), key=lambda kv: -max((len(v) for v in kv[1]), default=0))
        for dname, variants in order:
            if dpaper[dname] == pid:
                continue  # self-match: same paper proposes both sides
            for v in variants:
                flags = 0 if is_acronym(v) else re.I
                found = [mt for mt in re.finditer(rf"(?<![A-Za-z0-9./@-]){re.escape(v)}(?![A-Za-z0-9])",
                                                  body, flags)
                         if not any(s <= mt.start() < e for s, e in claimed)]
                if not found:
                    continue
                for mt in found:
                    claimed.append((mt.start(), mt.end()))
                ctxs = []
                for mt in found[:4]:
                    s = max(0, mt.start() - WINDOW)
                    ctx = " ".join(body[s: mt.end() + WINDOW].split())
                    ctxs.append({"context": ctx, "eval_hint": bool(EVAL_HINT_RE.search(ctx))})
                hits.append({
                    "mechanism": m["mechanism_name"],
                    "mechanism_paper_id": pid,
                    "mechanism_paper_title": p.get("title"),
                    "mechanism_covered_before": m["has_any_defense"],
                    "defense": dname,
                    "defense_paper_title": dmeta[dname]["source_paper_title"],
                    "defense_intervention_point": dmeta[dname]["intervention_point"],
                    "matched_variant": v,
                    "weak_name": len(v) < 7 or (" " not in v and v.islower()),
                    "already_confirmed": (dname, m["mechanism_name"]) in known,
                    "n_body_mentions": len(found),
                    "any_eval_hint": any(c["eval_hint"] for c in ctxs),
                    "contexts": ctxs,
                })
                break  # longest matching variant wins

    Path(args.out).write_text(json.dumps(hits, indent=1))
    new = [h for h in hits if not h["already_confirmed"]]
    strong = [h for h in new if h["any_eval_hint"]]
    print(f"\nmechanism papers with no usable full text: {no_pdf}")
    print(f"raw hits: {len(hits)} | already-confirmed pairs re-found: {len(hits) - len(new)}")
    print(f"new candidate pairs: {len(new)} | with evaluation language: {len(strong)}")
    print(f"  of those, on mechanisms currently UNCOVERED: "
          f"{sum(1 for h in strong if not h['mechanism_covered_before'])}")
    print("wrote", args.out)


if __name__ == "__main__":
    main()

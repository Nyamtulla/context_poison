"""Per-pair outcome table: what was reported, and CRUCIALLY by whom.

RQ5 recorded whether a (defense, mechanism) pair was tested, never what
happened. Filling that in naively produces a badly biased ledger, because the
two halves of the corpus disagree by construction:

  * a DEFENSE paper reports the pair because its defense won;
  * an ATTACK paper reports the same pair because the defense lost.

DataSentinel is the clean illustration - its own paper reports it working, and
four later attack papers report it failing, and all five are in our corpus. So
the outcome of a pair here is substantially a function of who wrote the paper.
This table therefore never collapses the two into one "win rate". Every row
carries `reported_by`, and every consumer is expected to split on it.

What each row records:

  reported_by        defense_paper | attack_paper - which side of the corpus
                     the claim comes from
  reported_verdict   the claim as stated in that paper, not our judgement
  metrics            effect sizes mined from the reported result, so a reader
                     sees the actual numbers rather than a binary
  evidence           the text the verdict and metrics came from, for audit

A note on what is NOT automated here. A first version tried to classify the
defense papers' verdicts with a win/loss lexicon. On inspection it was wrong
often enough to be worse than useless: it fired on language describing the
*attack* ("degrade", "bypass") and read those as the defense losing, and its
text window was usually the paper's title block, because for a generic
mechanism name like "Indirect Prompt Injection (IPI)" the first occurrence in
the body IS the title. That classifier is gone.

What replaces it is the structural fact, stated rather than measured: a defense
paper reports a pair because its defense won. So every defense-paper row is
`defense_wins_claimed`, which is a statement about where the claim comes from,
not a result we verified. Claiming to have independently checked those verdicts
would be the same mistake in the other direction.

Where the paper's own limitations section names the mechanism, the text is
attached as `stated_limitation` for the reader to weigh. It is a flag, not a
verdict: some of those mentions are pointed (TriShieldRAG's "~13% residual
attack success rate... not a complete elimination"), others are incidental.
Deciding which is which is a reading task, and the table's job is to put the
reading in front of you, not to pre-empt it.

    python scripts/build_pair_outcomes.py [--out FILE]
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
from stage1_fulltext_scan import pdf_text, split_body, name_variants

REPO = Path(__file__).resolve().parent.parent
WINDOW = 420

# Effect sizes worth pulling out. Ordered most-specific first: a "from X to Y"
# reduction says more than a bare percentage, so it is matched before the
# generic pattern can swallow the same span.
# A percentage-bearing number is only an effect size if something nearby says
# what it measures. PCT tolerates the shapes real papers use - "62.5%/63.3%",
# "0.0 (26.5)", "from 12.6% to 33.4%" - which a stricter pattern misses.
PCT = r"\d{1,3}(?:\.\d+)?\s*%"
METRIC_RES = [
    ("reduction", re.compile(
        rf"(?:reduc\w+|drop\w*|lower\w*|decreas\w+|falls?|improv\w+|rises?|lifts?)"
        rf"[^.]{{0,80}}?from\s*({PCT}(?:\s*/\s*{PCT})?)[^.]{{0,60}}?to\s*({PCT}(?:\s*/\s*{PCT})?)", re.I)),
    ("asr", re.compile(rf"(?:\bASR\b|attack success rate)[^.]{{0,60}}?({PCT})", re.I)),
    ("detection", re.compile(
        rf"(?:detection|detect\w*)\s*(?:rate|accuracy)?[^.]{{0,60}}?({PCT})", re.I)),
    ("tpr_fpr_fnr", re.compile(rf"\b(TPR|FPR|FNR)\b[^.]{{0,40}}?({PCT})", re.I)),
    ("accuracy", re.compile(rf"(?:accuracy|success rate|EM|F1)[^.]{{0,60}}?({PCT})", re.I)),
]

# Words that mark a passage as reporting a RESULT rather than describing the
# problem. Used to pick which occurrence of a mechanism name to read, not to
# decide who won.
RESULT_RE = re.compile(
    r"\b(?:ASR|attack success rate|accuracy|detection rate|TPR|FPR|FNR|F1|"
    r"we evaluate|our experiments|table \d|figure \d|results show|reduces?|achieves?)\b", re.I)


def mine_metrics(text: str) -> list[dict]:
    out, spans = [], []
    for kind, rx in METRIC_RES:
        for m in rx.finditer(text):
            if any(s <= m.start() < e for s, e in spans):
                continue
            spans.append((m.start(), m.end()))
            out.append({"kind": kind, "value": " -> ".join(m.groups()),
                        "quote": " ".join(m.group(0).split())[:160]})
    return out[:6]


def window_for(body: str, mech: str) -> str:
    """The most result-bearing window around the mechanism's name, or ''.

    Deliberately NOT the first occurrence. For a generic name like "Indirect
    Prompt Injection (IPI)" the first hit in the body is the paper's own title,
    which says nothing about any result. Every occurrence is scored by how much
    result language and how many numbers it carries, and the best one wins.
    """
    best, best_score = "", 0
    for v in name_variants(mech):
        for m in re.finditer(rf"(?<![A-Za-z0-9]){re.escape(v)}(?![A-Za-z0-9])", body, re.I):
            s = max(0, m.start() - WINDOW)
            ctx = " ".join(body[s: m.end() + WINDOW].split())
            score = len(RESULT_RE.findall(ctx)) + len(re.findall(PCT, ctx))
            if score > best_score:
                best, best_score = ctx, score
        if best_score:
            break  # longest variant that appears at all wins
    return best if best_score >= 2 else ""


def limitation_mentions(paper: dict, mech: str) -> str:
    """The paper's own stated limitation naming this mechanism, if any."""
    lim = str(paper.get("stated_limitations") or "")
    if not lim:
        return ""
    for v in name_variants(mech):
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(v)}(?![A-Za-z0-9])", lim, re.I):
            return lim[:600]
    return ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "data/registries/pair_outcomes.json"))
    args = ap.parse_args()

    reg = registry_source.load_all()
    papers = {p["paper_id"]: p for p in registry_source.load_papers()}
    dmeta = {d["defense_name"]: d for d in reg["defenses"]}
    mmeta = {m["mechanism_name"]: m for m in reg["mechanisms"]}

    body_cache: dict[str, str] = {}

    def body_of(pid: str) -> str:
        if pid not in body_cache:
            p = papers.get(pid) or {}
            path = p.get("pdf_local_path")
            body_cache[pid] = (split_body(pdf_text(pid, Path(path)))
                               if path and Path(path).exists() else "")
        return body_cache[pid]

    rows = []
    for i, pair in enumerate(reg["pairs"], 1):
        if i % 50 == 0:
            print(f"  [{i}/{len(reg['pairs'])}]", flush=True)
        caveat = ""
        d = dmeta.get(pair["defense_name"], {})
        m = mmeta.get(pair["mechanism_name"], {})
        from_attack = pair["source"] == "attack_paper_scan"

        if from_attack:
            # Already adjudicated by hand when the pair was confirmed; the
            # quoted evidence is the justification field.
            reported_by, claim_pid = "attack_paper", m.get("source_paper_id")
            outcome = pair.get("outcome", "")
            verdict = ("defense_loses_reported"
                       if any(w in outcome.lower() for w in
                              ("fail", "broken", "degraded", "insufficient",
                               "exploited", "evaded", "assumption"))
                       else "evaluated_no_directional_verdict")
            evidence = pair.get("justification", "")
            name_in_text = True
        else:
            reported_by, claim_pid = "defense_paper", d.get("source_paper_id")
            paper = papers.get(claim_pid) or {}
            window = window_for(body_of(claim_pid or ""), pair["mechanism_name"])
            name_in_text = bool(window)
            # key_result is the curated headline finding for the paper and is
            # usually the better evidence; the body window is kept alongside it
            # because it is the part that is specific to THIS mechanism.
            key = str(paper.get("key_result") or "")
            evidence = (key + ("\n\n---\n\n" + window if window else "")) if key else window
            caveat = limitation_mentions(paper, pair["mechanism_name"])
            verdict = "defense_wins_claimed" if evidence else "no_reported_result_found"

        rows.append({
            "defense_name": pair["defense_name"],
            "mechanism_name": pair["mechanism_name"],
            "reported_by": reported_by,
            "reported_verdict": verdict,
            "outcome_as_adjudicated": pair.get("outcome", ""),
            "claim_source_paper_id": claim_pid,
            "claim_source_paper_title": (papers.get(claim_pid) or {}).get("title"),
            "mechanism_named_in_text": name_in_text,
            "stated_limitation": caveat if not from_attack else "",
            "metrics": mine_metrics(evidence),
            "evidence": evidence[:900],
            "defense_track": pair.get("defense_track"),
            "mechanism_track": pair.get("mechanism_track"),
            "defense_intervention_point": pair.get("defense_intervention_point"),
            "cross_track": pair.get("cross_track"),
            "pair_source": pair["source"],
        })

    Path(args.out).write_text(json.dumps(rows, indent=1))

    from collections import Counter
    print(f"\nrows: {len(rows)}")
    for by in ("defense_paper", "attack_paper"):
        sub = [r for r in rows if r["reported_by"] == by]
        print(f"\n{by} ({len(sub)} pairs)")
        for k, v in Counter(r["reported_verdict"] for r in sub).most_common():
            print(f"   {v:4d}  {k}")
        print(f"   with a mined effect size: {sum(1 for r in sub if r['metrics'])}")
        if by == "defense_paper":
            print(f"   paper's own limitations name the mechanism: "
                  f"{sum(1 for r in sub if r['stated_limitation'])}")
        print(f"   mechanism named in the paper's body: "
              f"{sum(1 for r in sub if r['mechanism_named_in_text'])}")
    print("\nwrote", args.out)


if __name__ == "__main__":
    main()

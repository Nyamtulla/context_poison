"""Stage 2: predict which existing defenses should transfer to mechanisms
nothing has ever been tested against.

The premise is RQ6's finding, used as a predictor rather than a description:
generalization tracked where a defense intervenes (ingestion 3/4 full,
reasoning 1/3, execution 0/2 - the execution pair couldn't even be run). So a
defense's intervention point becomes a prior on whether it will transfer, and
the similarity between what it WAS tested on and the untested mechanism
supplies the rest of the signal.

Output is a ranked list of (defense, uncovered mechanism) hypotheses - claims
to be tested in Stage 3, not findings. Nothing here asserts that a defense
works; it asserts that a pair is worth the GPU time.

    python scripts/stage2_transfer_predictions.py [--top N] [--out FILE]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import registry_source

REPO = Path(__file__).resolve().parent.parent

# Prior on transfer by intervention point, taken directly from RQ6's 9 case
# studies. Deliberately empirical rather than assumed - these are the observed
# full-generalization rates, with execution set low because neither execution
# defense could be made to run at all on open-weight models.
TRANSFER_PRIOR = {"ingestion": 0.75, "reasoning": 0.33, "execution": 0.10, "none": 0.30}

# How close an already-tested mechanism has to be to the untested one for the
# defense's demonstrated behaviour to carry over. Channel is the delivery path,
# consequence is the damage - matching both is the strongest analogy available
# in this taxonomy.
SIM_BOTH, SIM_CONSEQ, SIM_CHANNEL, SIM_TRACK = 1.0, 0.6, 0.5, 0.2


def similarity(a: dict, b: dict) -> float:
    if a["channel"] == b["channel"] and a["consequence"] == b["consequence"]:
        return SIM_BOTH
    if a["consequence"] == b["consequence"]:
        return SIM_CONSEQ
    if a["channel"] == b["channel"]:
        return SIM_CHANNEL
    if a["track"] == b["track"]:
        return SIM_TRACK
    return 0.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=3, help="candidate defenses to keep per mechanism")
    ap.add_argument("--out", default=str(REPO / "data/registries/stage2_transfer_predictions.json"))
    args = ap.parse_args()

    reg = registry_source.load_all()
    papers = {p["paper_id"]: p for p in registry_source.load_papers()}
    mechs_by_name = {m["mechanism_name"]: m for m in reg["mechanisms"]}

    uncovered = [m for m in reg["mechanisms"] if not m["has_any_defense"]]
    defenses = [d for d in reg["defenses"] if d["has_confirmed_match"]]
    print(f"{len(uncovered)} uncovered mechanisms x {len(defenses)} defenses with known test history")

    predictions = []
    for m in uncovered:
        scored = []
        for d in defenses:
            best_sim, via = 0.0, None
            for tested_name in d["mechanisms_tested"]:
                t = mechs_by_name.get(tested_name)
                if not t:
                    continue
                s = similarity(m, t)
                if s > best_sim:
                    best_sim, via = s, tested_name
            if not best_sim:
                continue
            prior = TRANSFER_PRIOR.get(d["intervention_point"] or "none", 0.30)
            paper = papers.get(d["source_paper_id"]) or {}
            code = str(paper.get("artifacts_released") or "").strip().upper().startswith("Y")
            scored.append({
                "defense": d["defense_name"],
                "defense_intervention_point": d["intervention_point"],
                "defense_validated_against": d["validated_against"],
                "transfers_from": via,
                "similarity": round(best_sim, 2),
                "intervention_prior": prior,
                "score": round(best_sim * prior, 3),
                "code_released": code,
                "cross_track": bool(d["track"] and m["track"] and d["track"] != m["track"]),
                "defense_paper_title": d["source_paper_title"],
            })
        scored.sort(key=lambda x: (x["score"], x["code_released"]), reverse=True)

        mech_paper = papers.get(m["source_paper_id"]) or {}
        predictions.append({
            "mechanism": m["mechanism_name"],
            "mechanism_track": m["track"],
            "channel": m["channel"],
            "consequence": m["consequence"],
            "mechanism_citations": mech_paper.get("citation_count") or 0,
            "mechanism_year": mech_paper.get("year"),
            "mechanism_paper": m["source_paper_title"],
            "named": not m["mechanism_name"].startswith("UNNAMED"),
            "n_candidates": len(scored),
            "best_score": scored[0]["score"] if scored else 0.0,
            "testable_now": any(c["code_released"] for c in scored[: args.top]),
            "candidates": scored[: args.top],
        })

    # Priority = how good the best hypothesis is, weighted by how much the field
    # would care if it held (citations of the mechanism's own paper).
    for p in predictions:
        p["priority"] = round(p["best_score"] * (1 + (p["mechanism_citations"] or 0) ** 0.5), 2)
    predictions.sort(key=lambda p: p["priority"], reverse=True)

    Path(args.out).write_text(json.dumps(predictions, indent=1))

    have = [p for p in predictions if p["candidates"]]
    print(f"\nmechanisms with >=1 transfer hypothesis: {len(have)} of {len(uncovered)}")
    print(f"of those, testable now (top candidate has released code): "
          f"{sum(1 for p in have if p['testable_now'])}")
    print("\n=== TOP 15 BY PRIORITY ===")
    for p in predictions[:15]:
        c = p["candidates"][0] if p["candidates"] else None
        if not c:
            continue
        flag = "CODE" if c["code_released"] else "no code"
        print(f"{p['priority']:7.2f} | {p['mechanism'][:42]:42s} ({p['mechanism_citations']:4d} cites)")
        print(f"          -> {c['defense'][:52]:52s} [{c['defense_intervention_point']}, {flag}]")
        print(f"             via {c['transfers_from'][:60]} (sim={c['similarity']})")
    print("\nwrote", args.out)


if __name__ == "__main__":
    main()

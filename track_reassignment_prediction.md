# Pre-registration: retiring the `Both` track

Written **before** coding any of the 38 papers, and committed before the pass
runs. Same convention as the run predictions.

## Why

The cube's third axis is `intent` (adversarial / incidental / both), but the
corpus has no `intent` column. It is approximated by `track`, and the figure
and the macro both drop `Both`. So 63 of the 189 cells are empty **by
construction**, and the published 71.4% empty-cell rate is partly an artefact
of its own denominator.

Decision: retire `Both`, assign every paper to one track, and let the cube be
9 x 7 x 2 = 126.

## The rule, fixed before any paper is read

**A paper goes to the track whose threat model its own evaluation adopts.**

- Evaluates against a deliberate adversary -> **Security**
- Evaluates against ordinary pipeline degradation -> **ML/AI**
- Evaluates against both -> the one its *primary* experiment adopts, judged by
  what the headline result measures
- No evaluation of either kind -> the framing of its own contribution claim

This is `validated_against`, which was coded independently of `track` from each
paper's own evaluation section. 20 of the 38 already carry it. The rule is
stated this way so no individual case can be steered.

## What this will change, listed in advance

1. `NCubeCells` 189 -> 126; the empty-cell rate rises off its artificial floor.
   Predicted 57.1% if no paper's channel/consequence moves.
2. Figure 4's two panels will cover every included paper.
3. `NPureTrackPairs` 346 -> 349, since no pair is excluded for sitting on the
   line any more. `NCrossAllPairs` stops being a separate reading.
4. Two pairs (MOSAIC vs ASB DPI, Twin Agent vs AgentDojo
   important-instructions) move onto the Security/Security diagonal or raise
   `NMLDefVsSecAttack` from 4 to 6. Neither touches the central claim.

## The pivotal case, named before it is coded

**"DPO-based faithfulness-improvement training for GUI agents against
environmental distraction"** (defense, 2024) is paired with *distraction by
irrelevant context*, an ML/AI attack.

It is excluded from the transfer matrix today because its track is `Both`.
Under the rule it must land somewhere, and:

- -> **ML/AI**: the pair is ML-defense vs ML-attack. `NSecDefVsMLAttack` stays
  **0** and the central claim stands.
- -> **Security**: the pair is a security defense evaluated against a machine
  learning failure mechanism. `NSecDefVsMLAttack` becomes **1** and
  **the paper's headline claim is falsified by our own re-coding.**

**We report the outcome either way.** If it lands in Security the claim becomes
"one pair in 349, contributed by a paper that sits on the boundary", which is a
weaker headline and a more defensible one. Changing the rule after seeing which
way this paper falls would be the exact failure the prediction files exist to
prevent.

Our expectation, recorded now: **ML/AI**, because environmental distraction is
an incidental failure mode and DPO faithfulness training reasons about no
adversary. Stated so that being wrong is visible.

---

## Outcome, 2026-10-22

**The pivotal case resolved as predicted.** The GUI-agent DPO defense carries
`validated_against: incidental`, so the rule sent it to ML/AI mechanically and
its pair is ML-defense against ML-attack. That route did not break the zero.

**The zero broke anyway, through a pair we failed to name.** `NSecDefVsMLAttack`
is **1**, not 0:

> TRACE (Trajectory Risk-Aware Compression for Long-Horizon Agent Safety),
> 2026, `validated_against: adversarial` -> Security, reported against
> *context-length-induced degradation independent of retrieval failure*,
> an ML/AI mechanism.

**Why we missed it.** The risk analysis was run against `pair_timeline.json`
as it sat on disk, and that file was stale: it predated the propagation that
set TRACE's registry entry to `Both`. In the stale file TRACE's pair read
ML/AI vs ML/AI, so it did not appear in the query for pairs that could land in
the empty cell. **Rebuild the derived artifact before using it to assess risk**
— the lesson is the same one the numbers.tex rule exists for.

So the pre-registration did its job in the narrow sense, and the thing it was
guarding against still happened by a route it did not cover. Both facts are
reported.

## What changed

| | before | after |
|---|---|---|
| `NSecDefVsMLAttack` | 0 | **1** |
| `NCubeCells` | 189 | 126 |
| `NCubeEmpty` / `PctCubeEmpty` | 135 (71.4%) | 65 (**51.6%**) |
| `NPureTrackPairs` | 346 | 349 |
| `NCrossCommunityPairs` / pct | 4 (1.2%) | 5 (**1.4%**) |
| `PctSameTrack` | 98.0 | 98.6 |
| `NDefBoth` | 20 | 0 |
| `NTrackSecurity` / `NTrackML` | 566 / 325 | 588 / 341 |

The empty-cell rate fell further than the 57.1% predicted, because retracking
the 38 papers also occupied cells that had been empty.

## Limits of this pass

Single-coded, by one coder, in one sitting. 22 went to Security and 16 to
ML/AI; 10 of the 38 are recorded at medium or low confidence in
`data/registries/raw/track_reassign_both.csv`, and one (`eba07d3742`) applies
`validated_against` against the apparent sense of its own title rather than
overriding the independently coded field. **These 38 belong in the validation
packets**, which have to be rebuilt anyway.

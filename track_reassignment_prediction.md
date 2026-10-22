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

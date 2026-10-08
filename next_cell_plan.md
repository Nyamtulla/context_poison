# Which cell to run next

**Screen of all 11 candidate cells, with runnability on both sides.** 2026-10-08.

A cell is a candidate when the security side has named attacks and the ML/AI
side has named defenses for the same route and the same failure. There are 11.
We have finished one. The question is which to take next, and the answer is
not the biggest one.

## The screen

"w/code" counts papers whose artifact field names a repository or a release.
It is an upper bound on what will actually run — in the cell we finished, 20
defenses listed code and 4 produced a measurement.

| route in | what goes wrong | attacks | w/code | defenses | w/code | notes |
|---|---|---:|---:|---:|---:|---|
| direct-input | reasoning-corruption | 4 | 1 | 79 | 40 | attacks exhaust *generated* tokens; defenses compress *input*. Quantity mismatch. |
| **RAG** | **silent-corruption** | 3 | 2 | 42 | 20 | **the cell we are in — 14 of the 20 never run** |
| tool-output | goal-hijack | 61 | 40 | 1 | 0 | the field's largest attack surface, and no incidental defense to test |
| RAG | reasoning-corruption | 2 | 1 | 17 | 13 | best defenses in the whole screen, no runnable attack |
| direct-input | goal-hijack | 27 | 14 | 1 | 1 | one defense |
| direct-input | silent-corruption | 1 | 1 | 11 | 5 | one attack, reconstructable |
| memory | persistence-backdoor | 7 | 6 | 1 | 0 | no runnable defense |
| cross-modal | reasoning-corruption | 1 | 1 | 6 | 3 | needs a vision model |
| multi-agent | goal-hijack | 6 | 1 | 1 | 1 | one of each |
| cross-modal | silent-corruption | 1 | 1 | 3 | 2 | needs a vision model |
| memory | goal-hijack | 1 | 0 | 1 | 1 | no runnable attack |

## The recommendation: finish the cell we are in

We ran 5 defenses. **14 more in the same cell have released code and have never
been run**, and the ones we skipped are the *more* cited:

| defense | acts at | cites | |
|---|---|---:|---|
| CD2 (Conflict-Disentangle Contrastive Decoding) | reasoning | 117 | not run |
| Discern-and-Answer | — | 60 | not run |
| COMBO (Compatibility-Oriented knowledge Merging) | reasoning | 57 | not run |
| COIECD (information-entropy constrained decoding) | reasoning | 37 | not run |
| SCR & CR-DPO (Situated Faithfulness) | reasoning | 27 | not run |
| DyPRAG (Dynamic Parametric RAG) | reasoning | 26 | not run |
| *(CK-PLUG 41, FaithfulRAG 32, ParamMute 8, SHIFT 0, SABER 1)* | | | attempted |

Why this first:

- **No new attack to reconstruct.** The four attacks already run. Every hour
  goes into defenses rather than into rebuilding a payload.
- **The harness transfers unchanged** — same data, same poisoning
  construction, same scorers, same dose sweep.
- **It answers the obvious objection.** Right now the family claim rests on
  five defenses, and a reader can say we picked them. Fourteen more from the
  same cell, chosen by citation rank rather than by us, removes that.
- **The unrun ones are better cited than the run ones.** CD2 at 117 citations
  against ParamMute at 8. If the design rule survives CD2, COMBO and COIECD it
  is a much harder claim to dismiss.

Expect attrition. Four of nine ran last time, so plan for roughly six of the
fourteen to produce a measurement, and record the rest as reproducibility
findings the way the others were recorded.

## Second choice: direct-input × silent-corruption

The only cell where a new channel is reachable without inventing an attack.

- **Attack:** Xmera, a man-in-the-middle prompt injection that replaces facts
  in the prompt itself. Code and dataset released; the paper evaluates open
  Llama models alongside the closed ones, so an open substitute is not needed.
- **Defenses with code:** 5. One of them is SpARE, which already runs here.
  JUICE has an environment built and NQ-Swap downloaded. KScope is blocked —
  the authors state they cannot release the data. CoCoA and Autopilot are
  unknown.

Worth doing after the current cell, because it tests whether the design rule
holds when the poisoned text arrives through the prompt instead of through
retrieval. Same failure, different route in.

## What the screen says about the field

Two cells are mirror images of each other, and neither is testable:

- **tool-output × goal-hijack** — 61 named attacks, 40 with code, and **one**
  incidental defense, which has no code. The most heavily attacked route in
  the field has nothing on the other side to test against.
- **RAG × reasoning-corruption** — 13 defenses with code, including Self-RAG
  (2,264 citations), CRAG (251), RAT (101) and LongRAG (65). The best-resourced
  defense list in the whole screen. Its two attacks are a proprietary 42-million
  node knowledge graph on closed models, and a paper we cannot obtain.

> **A registry question for the project lead, not a change to make quietly.**
> CRAG and Self-RAG are coded under reasoning-corruption, but both judge
> whether a retrieved passage should be trusted, which is a direct answer to a
> poisoned passage as well. If either also belongs in silent-corruption, it
> enters the cell we are already running and becomes testable immediately
> against attacks we already have. Moving a registry entry moves published
> counts, so this is the lead's call.

## Effort

| step | GPU | notes |
|---|---|---|
| 14 defenses, environment and control each | ~1 day each, most of it setup | the control gates whether a transfer number is reported at all |
| each that survives × 4 attacks × 5 doses | ~4 h per defense | the matrix runner takes them unchanged |
| Xmera reconstruction | ~2 days | only if the second cell is approved |

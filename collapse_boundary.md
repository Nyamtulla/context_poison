# Where the collapse starts: a slope for lies, a cliff for refusal

**The crossover runs, read against the dose curves.** 2026-10-06.

The headline cells sample poison at 0, 1, 5, 9, 10. That is enough to say
*whether* a defense survives. It is not enough to say *where* it stops
surviving, because everything between 5 and 10 is one wide gap. Three
crossover runs fill poison 6, 7 and 8 at n=500 (mdr 8.9 pp). They change one
claim and confirm another.

## ParamMute x PoisonedRAG: the harm starts at 8/10, not 10/10

| poison | undefended | ParamMute | Δ accuracy |
|---:|---:|---:|---:|
| 0/10 | 62.2 % | 59.8 % | −2.4 |
| 1/10 | 55.6 % | 51.6 % | −4.0 |
| 5/10 | 52.2 % | 45.6 % | −6.6 |
| 7/10 | 48.2 % | 42.4 % | −5.8 |
| **8/10** | 48.6 % | 37.4 % | **−11.2** ✱ |
| **9/10** | 46.2 % | 33.4 % | **−12.8** ✱ |
| **10/10** | 32.0 % | 5.6 % | **−26.4** ✱ |

✱ clears the minimum detectable change (8.9 pp at n=500).

> **Correction.** The earlier reading — flat until 10/10, then a cliff — came
> from cells that had no 7 or 8 sample. Against lie insertion the damage is
> **already resolvable at 8/10**, two passages before saturation, and it grows
> monotonically from there. The cliff at 10/10 is real but it is the end of a
> ramp, not the whole effect.

This matters for the threat model. An attacker who must own **all ten**
retrieved passages is facing a hard problem. An attacker who only needs
**eight of ten** is facing a much easier one, and that is where a
context-reliance defense already starts costing its user more than it saves.

## ParamMute x BadRAG DoS: the cliff is real here

| poison | undefended | ParamMute | Δ accuracy |
|---:|---:|---:|---:|
| 1/10 | 27.0 % | 57.4 % | **+30.4** ✱ |
| 5/10 | 30.2 % | 57.4 % | **+27.2** ✱ |
| 6/10 | 31.6 % | 55.8 % | **+24.2** ✱ |
| 7/10 | 33.4 % | 55.6 % | **+22.2** ✱ |
| 8/10 | 29.2 % | 53.6 % | **+24.4** ✱ |
| 9/10 | 29.4 % | 48.8 % | **+19.4** ✱ |
| **10/10** | 3.8 % | 1.6 % | **−2.2** |

Here the filled-in levels **confirm** the original shape. The protection is a
plateau — +30 to +19 pp, resolvable at every level from 1 to 9 — and it
disappears in a single step between 9 and 10. The one-passage boundary stands
for this attack.

## Why the two shapes differ, and why that was predictable

The two curves are the same defense on the same data. Only the attack
mechanism differs, and the mechanism decides what happens *while genuine
evidence survives*:

- **BadRAG DoS** induces refusal. While any real passage remains, ParamMute's
  insistence on the retrieved text is pointed at a real passage, and it helps.
  The attack contributes nothing until it owns everything.
- **PoisonedRAG** inserts a plausible lie. Every poisoned passage added is a
  passage ParamMute will insist on. The defense **amplifies the attack dose**,
  so harm accumulates with the dose instead of waiting for saturation.

That is the earlier claim — *the attack's mechanism decides what happens below
saturation* — now measured rather than asserted, with the crossing point
located at 8/10.

## What this adds to the design rule

The rule was: do not suppress parametric memory, because it is worth ~32
points when the evidence set empties. The crossover sharpens it:

> **Against an attack that inserts content rather than removing it, a
> context-reliance defense is a dose multiplier.** Its harm is measurable at
> 80 % contamination, not only at 100 %.

## Limits

- Three crossover cells, one defense family. CK-PLUG's crossover shares its
  control failure on `open_nq` (−22.6 pp at poison 0), so its accuracy column
  is not attributable and it is not used for the boundary claim.
- Levels 2, 3, 4 are still unsampled. The onset is located between 7 and 8 at
  this n; a finer grid could move it by one.
- Same scorers, payloads and prompt construction as every other cell, all
  original authors' code.

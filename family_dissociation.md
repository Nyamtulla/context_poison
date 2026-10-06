# The saturation penalty belongs to one defense family, not to RAG defense

**Nine cells, four attack mechanisms, four defenses, two families.** 2026-10-06.

## The result

At full saturation — every retrieved passage replaced by attacker payload —
the two defense families do opposite things.

| defense | family | attack | Δaccuracy | Δattack-success |
|---|---|---|---:|---:|
| **RobustRAG** | **isolate-then-aggregate** | PoisonedRAG | **+4.0 pp** | **−15.3 pp** |
| CK-PLUG | context-reliance | BadRAG sentiment | −40.0 pp | **+95.0 pp** |
| ParamMute | context-reliance | BadRAG sentiment | −31.8 pp | +25.4 pp |
| SpARE | context-reliance | BadRAG DoS | −31.7 pp | +0.0 pp |
| CK-PLUG | context-reliance | PoisonedRAG | −27.6 pp | −4.6 pp |
| SpARE | context-reliance | PoisonedRAG | −21.0 pp | **+44.7 pp** |
| CK-PLUG | context-reliance | BadRAG DoS | −3.6 pp | −21.2 pp |
| ParamMute | context-reliance | BadRAG DoS | −2.2 pp | −12.0 pp |

**Every context-reliance defense loses accuracy at saturation. The aggregation
defense gains it, and cuts attack success by 15.3 pp while doing so.**

## Why this is the finding the campaign was for

Until now the claim was a warning: these defenses are harmful when the
retrieved evidence runs out, because they instruct the model to use evidence
that is gone after removing the parametric memory it would otherwise fall back
on. That was established across three defenses and ~32 points of penalty.

The open question was its scope. Is the saturation penalty a property of
**RAG defenses generally** — anything acting after retrieval inherits it — or
specifically of **suppressing parametric memory**?

RobustRAG answers it. It is a post-retrieval defense, it faces the identical
attack on the identical data, and at saturation it **does not collapse**. It
answers over each passage in isolation and aggregates, and it never touches
parametric memory.

> **The ~32-point penalty is the cost of suppressing parametric memory. It is
> not the cost of defending RAG.**

That converts a warning into a design rule, which is a different kind of
contribution:

- **Do not suppress parametric memory.** It is the model's only recourse when
  the evidence set is empty, and it is worth ~32 points.
- **Aggregating over passages does not have this failure mode.** RobustRAG is
  neutral-to-positive at every poison level and strongest exactly where the
  other family is weakest.

## The second finding: tone steering needs no saturation

Every other attack here requires near-total control of the retrieved set
before it changes anything. BadRAG's Selective-Fact attack does not.

| poison | undefended negative framing | CK-PLUG | Δ |
|---:|---:|---:|---:|
| 0/10 | 0.0 % | 0.0 % | +0.0 |
| **1/10** | **0.0 %** | **78.2 %** | **+78.2 pp** |
| 5/10 | 0.4 % | 96.0 % | +95.6 pp |
| 9/10 | 2.0 % | 97.0 % | +95.0 pp |
| 10/10 | 4.0 % | 99.0 % | +95.0 pp |

**One slanted passage among nine clean ones.** The undefended model ignores it
entirely — 0.0 %. CK-PLUG adopts its framing **78.2 %** of the time, rising to
99 %.

This is readable despite CK-PLUG's accuracy control failing on this dataset,
because the metric carries its own control: **at poison 0 both arms produce
0.0 % negative framing.** The defense does not generate slant on its own. The
effect is entirely the interaction of defense and attack.

ParamMute shows the same direction more weakly (+25.4 pp at saturation).

The reason is uncomfortable and simple. Tone steering does not corrupt the
*answer*, so a defense that measures success by whether the model follows the
retrieved text will score this as working perfectly. **The attack and the
defense want the same thing.**

## What an attacker should take from this

The two findings point in opposite directions for an attacker, which is worth
stating plainly:

- To destroy **accuracy**, you must own essentially the whole retrieved set.
  Nine of ten passages is not enough.
- To control **framing**, one passage is enough — and a context-reliance
  defense will do the work for you.

## Limits

- `10/10` is an artificial corner. Across the realistic range these defenses
  are robust, and that should not be lost in the headline.
- One aggregation defense, one attack for it so far. RobustRAG × BadRAG-DoS
  and × sentiment are queued; the family claim rests on one cell until they
  land.
- CK-PLUG's accuracy control fails on `open_nq` (−22.8 pp at poison 0), so its
  accuracy column is not attributable. Its framing column is, for the reason
  above.
- Scorers, payloads and prompt construction are shared across every cell, and
  all are the original authors' code.

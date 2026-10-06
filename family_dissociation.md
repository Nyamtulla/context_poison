# The saturation penalty belongs to one defense family, not to RAG defense

**Twelve cells, four attack mechanisms, four defenses, two families.** 2026-10-06.

> **Revised after phase 2.** The first version read RobustRAG's single
> PoisonedRAG cell as the family *gaining* accuracy at saturation. With all
> three RobustRAG cells in, it is **neutral**, not positive. The dissociation
> stands and is stated correctly below; the over-read is corrected.

## The result

At full saturation — every retrieved passage replaced by attacker payload —
the two families behave categorically differently.

| defense | family | attack | Δaccuracy | Δattack-success | resolvable |
|---|---|---|---:|---:|---|
| RobustRAG | **aggregate** | PoisonedRAG | +4.0 | **−15.3** | ASR |
| RobustRAG | **aggregate** | BadRAG sentiment | −4.3 | +0.3 | — |
| RobustRAG | **aggregate** | BadRAG DoS | −5.7 | +5.3 | — |
| CK-PLUG | context-reliance | BadRAG sentiment | **−40.0** | **+95.0** | both |
| ParamMute | context-reliance | BadRAG sentiment | **−31.8** | **+25.4** | both |
| SpARE | context-reliance | BadRAG DoS | **−31.7** | +0.0 | acc |
| CK-PLUG | context-reliance | PoisonedRAG | **−27.6** | −4.6 | acc |
| SpARE | context-reliance | PoisonedRAG | **−21.0** | **+44.7** | both |
| CK-PLUG | context-reliance | BadRAG DoS | −3.6 | **−21.2** | ASR |
| ParamMute | context-reliance | BadRAG DoS | −2.2 | **−12.0** | ASR |

**RobustRAG never loses resolvable accuracy at saturation** — its three cells
span −5.7 to +4.0 pp and none clears threshold. **Five of seven
context-reliance cells do**, by 21 to 40 points.

The accurate statement is therefore *neutral versus collapsing*, not *gaining
versus collapsing*:

| | accuracy at 10/10 |
|---|---|
| aggregate | −5.7 to +4.0 pp, **none resolvable** |
| context-reliance | −2.2 to −40.0 pp, **five of seven resolvable** |

## Why this is the finding the campaign was for

Until now the claim was a warning: these defenses are harmful when the
retrieved evidence runs out, because they instruct the model to use evidence
that is gone after removing the parametric memory it would otherwise fall back
on. That was established across three defenses and ~32 points of penalty.

The open question was its scope. Is the saturation penalty a property of
**RAG defenses generally** — anything acting after retrieval inherits it — or
specifically of **suppressing parametric memory**?

RobustRAG answers it. It is a post-retrieval defense, it faces identical
attacks on identical data, and across all three it **does not collapse** —
while five of seven context-reliance cells do. It answers over each passage in
isolation and aggregates, and it never touches parametric memory.

> **The ~32-point penalty is the cost of suppressing parametric memory. It is
> not the cost of defending RAG.**

That converts a warning into a design rule, which is a different kind of
contribution:

- **Do not suppress parametric memory.** It is the model's only recourse when
  the evidence set is empty, and it is worth ~32 points.
- **Aggregating over passages does not have this failure mode.** RobustRAG
  never loses resolvable accuracy at saturation, and it is strongest just
  below it — **+12.3 pp at 9/10 against BadRAG DoS**, which clears threshold.

### And it is immune to the tone attack

The sharpest single contrast in the matrix. Negative-framing rate under
BadRAG Selective-Fact:

| poison | undefended | RobustRAG | ParamMute | CK-PLUG |
|---:|---:|---:|---:|---:|
| 1/10 | 0.0 % | **0.0 %** | — | **78.2 %** |
| 10/10 | 4.0 % | **0.3 %** | 28.8 % | **99.0 %** |

RobustRAG does not adopt the attacker's framing at any poison level. The
reason is structural: it answers each passage separately and aggregates, so a
single slanted passage is one outvoted opinion rather than the frame for the
whole answer.

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
- **One aggregation defense, three attacks.** The family claim rests on
  RobustRAG alone; a second aggregation defense would test whether this is the
  family or the implementation.
- RobustRAG's ASR rises slightly under BadRAG DoS (+5.3 pp at 10/10, not
  resolvable). It is neutral there, not protective.
- CK-PLUG's accuracy control fails on `open_nq` (−22.8 pp at poison 0), so its
  accuracy column is not attributable. Its framing column is, for the reason
  above.
- Scorers, payloads and prompt construction are shared across every cell, and
  all are the original authors' code.

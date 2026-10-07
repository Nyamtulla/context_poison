# The saturation penalty belongs to one defense family, not to RAG defense

**Thirteen cells, three attack mechanisms, five defense implementations,
two families.** 2026-10-06.

> **Revised after phase 2.** The first version read RobustRAG's single
> PoisonedRAG cell as the family *gaining* accuracy at saturation. With all
> three RobustRAG cells in, it is **neutral**, not positive. The dissociation
> stands and is stated correctly below; the over-read is corrected.

## The result

At full saturation — every retrieved passage replaced by attacker payload —
the two families behave categorically differently.

| defense | family | attack | Δaccuracy | Δattack-success | accuracy attributable? |
|---|---|---|---:|---:|---|
| RobustRAG / KeywordAgg | **aggregate** | PoisonedRAG | +4.0 | **−15.3** | yes — not resolvable |
| RobustRAG / KeywordAgg | **aggregate** | BadRAG sentiment | −4.3 | +0.3 | yes — not resolvable |
| RobustRAG / KeywordAgg | **aggregate** | BadRAG DoS | −5.7 | +5.3 | yes — not resolvable |
| RobustRAG / DecodingAgg | **aggregate** | PoisonedRAG | −2.0 | **−38.7** | yes — not resolvable |
| RobustRAG / DecodingAgg | **aggregate** | BadRAG sentiment | −4.0 | +0.3 | yes — not resolvable |
| ParamMute | context-reliance | BadRAG sentiment | **−31.8** | **+25.4** | **yes — harm** |
| ParamMute | context-reliance | PoisonedRAG | **−26.4** | **+20.4** | **yes — harm** |
| SpARE | context-reliance | BadRAG DoS | **−31.7** | +0.0 | **yes — harm** |
| SpARE | context-reliance | PoisonedRAG | **−21.0** | **+44.7** | **yes — harm** |
| ParamMute | context-reliance | BadRAG DoS | −2.2 | **−12.0** | yes — not resolvable |
| CK-PLUG | context-reliance | BadRAG sentiment | −40.0 | **+95.0** | **no — control failed** |
| CK-PLUG | context-reliance | PoisonedRAG | −27.6 | −4.6 | **no — control failed** |
| CK-PLUG | context-reliance | BadRAG DoS | −3.6 | **−21.2** | **no — control failed** |

> **Revised again 2026-10-06, downward.** The earlier count — *five of seven
> context-reliance cells* — included CK-PLUG rows. CK-PLUG's own control fails
> on `open_nq` (−22.6 pp between arms at poison 0, against an 8.9 pp
> threshold), so its accuracy column is not attributable to the attack, and
> this document said so in its own Limits section while still counting those
> rows. Applying control-fires-first consistently removes all three. The table
> above is now generated from `data/paper_explorer.db`, which applies the rule
> mechanically, so the two cannot drift apart again.

| | accuracy at 10/10 | attributable cells | resolvable harm |
|---|---|---:|---:|
| **aggregate** | −5.7 to +4.0 pp | 5 of 5 | **0** |
| **context-reliance** | −2.2 to −31.8 pp | 5 of 8 | **4** |

The dissociation survives the correction and is **sharper** than before:
**4 of 5 against 0 of 5**, on cells whose controls all fired.

CK-PLUG's *attack-success* column still counts, for the reason given in Limits:
that metric carries its own control, since both arms produce 0.0 % negative
framing at poison 0.

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
- **One aggregation codebase, two implementations.** KeywordAgg and
  DecodingAgg share no decision logic — one votes on extracted keywords, the
  other compares per-passage decoding distributions — and both behave the same
  way, which is why the claim is stated at the level of the principle. They do
  still come from one paper's repository. A third aggregation defense from a
  different group would be the next real test.
- **MajorityVoting, RobustRAG's third variant, is not testable here.** Its
  `query()` calls `wrap_prompt(as_multi_choice=True)` and only runs on
  multiple-choice data, so it cannot be evaluated on open-ended `open_nq`. It
  is excluded for that reason, not because it failed.
- RobustRAG's ASR rises slightly under BadRAG DoS (+5.3 pp at 10/10, not
  resolvable). It is neutral there, not protective.
- CK-PLUG's accuracy control fails on `open_nq` (−22.8 pp at poison 0), so its
  accuracy column is not attributable. Its framing column is, for the reason
  above.
- Scorers, payloads and prompt construction are shared across every cell, and
  all are the original authors' code.

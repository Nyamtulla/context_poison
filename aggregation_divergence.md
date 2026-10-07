# Two implementations of one principle, and a 29.7-point disagreement

**RobustRAG KeywordAgg vs DecodingAgg, BadRAG DoS, n=300.** 2026-10-06.

## The finding

The second aggregation implementation was run to test whether the family's
behaviour belongs to the **principle** or to **KeywordAgg specifically**. The
answer turns out to be *both, depending on which behaviour you mean.*

Across fifteen dose levels the two implementations agree within noise on
thirteen of them. On one they disagree completely:

| attack | poison | KeywordAgg Δacc | DecodingAgg Δacc | gap |
|---|---:|---:|---:|---:|
| BadRAG DoS | 5/10 | +4.0 | −9.0 | 13.0 |
| **BadRAG DoS** | **9/10** | **+12.3** ✱ | **−17.3** ✱ | **29.7** |
| BadRAG DoS | 10/10 | −5.7 | −4.0 | 1.7 |
| PoisonedRAG | 9/10 | −2.7 | +6.7 | 9.3 |
| BadRAG sentiment | 9/10 | +5.7 | −0.7 | 6.3 |

✱ clears the 11.4 pp threshold at n=300.

**At 9/10 against refusal induction, one implementation of isolate-then-
aggregate is resolvably protective and the other is resolvably harmful.**
Both readings clear threshold. They are not reconcilable as noise.

## What splits cleanly and what does not

| behaviour | level it lives at |
|---|---|
| no collapse at saturation (10/10) | **principle** — both, every attack |
| does not open the tone-steering hole | **principle** — both, 0.0 → 0.3 % |
| protects against refusal induction below saturation | **implementation** — +12.3 vs −17.3 |

The design rule from the saturation work survives: *do not suppress parametric
memory*, and aggregating does not have that failure mode, in either
implementation. What does **not** survive is the broader reading that was
starting to form — that isolate-then-aggregate is simply the safer family. One
of its two implementations loses 17.3 points exactly where the other gains
12.3.

## The mechanism this suggests, stated as a prediction

The two aggregation steps differ in one way that matters here:

- **KeywordAgg is a hard filter.** It extracts keywords per passage and keeps
  those appearing above a count threshold. A BadRAG DoS passage carries no
  answer content, so it contributes no surviving keywords — it is *discarded*,
  not weighed. One honest passage out of ten can still carry the answer.
- **DecodingAgg is a soft average.** It averages next-token distributions
  across passages. Nine junk distributions do not drop out of an average; they
  dilute the one honest distribution until it no longer determines the output.

If that is right, the divergence is a property of **how small the honest
minority is**, and these should follow:

1. The gap should **persist at 8/10 and 7/10**, where the honest minority is
   still small, and KeywordAgg should still be protective there.
2. The gap should **narrow as the honest fraction grows** — smaller at 6/10
   than at 9/10.
3. It should **vanish at 10/10**, where neither method has an honest passage
   to preserve. *(Already observed: 1.7 pp.)*
4. It should be **largest for DoS and smallest for PoisonedRAG**, because a
   PoisonedRAG passage carries a fake *answer* — it contributes keywords, so
   KeywordAgg's filter does not discard it and the two methods converge.
   *(Already observed: 9.3 pp at 9/10, not resolvable.)*

Predictions 3 and 4 are already consistent with data in hand. Predictions 1
and 2 are not: nothing has been run at 6, 7 or 8 for either method.

**The crossover run testing them was launched before this document was
written, and its result is recorded below whatever it says.**

## Result of the prediction test

*Pending — `badrag_dos_robustrag_crossover.json` and
`badrag_dos_robustrag_decoding_crossover.json`, poison 6/7/8, n=300.*

## Why this matters beyond one cell

SoKs generalise from implementations to families, because families are what a
reader can act on. This is a measured case of that generalisation failing
inside a single paper's own codebase — two variants the authors ship side by
side, sharing the isolation step and the prompt builder, differing only in how
they combine per-passage results, and disagreeing by 29.7 points on whether
the defense helps or hurts.

It argues for reporting defense results at the level of the **aggregation
rule**, not the family, and for treating any single-implementation family
claim — including the ones earlier in this campaign — as provisional until a
second implementation agrees.

## Limits

- One divergent cell out of fifteen. The disagreement is specific, not
  general, and the two implementations agree everywhere else.
- Both arms are RobustRAG's own released code with its own defaults
  (`eta=0.0`, `subsample_iter=1`); no hyperparameter search was run on either,
  and DecodingAgg has knobs KeywordAgg does not.
- Mistral-7B only, `open_nq` only, the authors' scorers unchanged.

# A gradient attack on ACD: prediction, committed before the run

Written 2026-10-17, before the payload exists. This is the open item left by
`adaptive_acd_result.md`: best-of-five over sentence templates took `d_alpha`
from 0.525 to 0.653 of a possible 1.0 and removed 29 % of ACD's protection.
Most of the headroom survived the attack. The question this run settles is
whether that headroom is reachable, i.e. whether ACD **degrades** under
adaptive pressure or **collapses**.

## The objective is unchanged

ACD's rule, verbatim from `third_party/ACD/generation/gen_wrapper.py:909-919`:

```python
ent     = -torch.sum(probs     * torch.log2(probs),     dim=-1)   # no context
ent_pos = -torch.sum(probs_pos * torch.log2(probs_pos), dim=-1)   # with context
d_alpha = (ent / (ent_pos + ent)).unsqueeze(-1)
next_token_scores = next_token_scores + d_alpha * (next_token_scores_pos - next_token_scores)
```

`ent` belongs to the question. `ent_pos` belongs to the context, which the
attacker owns. The objective is the same single number as before: **minimise
`ent_pos`**. What changes is the optimiser, from a choice among five
hand-written forms to a GCG-style coordinate search over token ids.

## The ceiling is unchanged, and still bounds the result in advance

As `ent_pos -> 0`, `d_alpha -> 1` and the update becomes the identity on
`scores_pos`. **A perfect adaptive attack turns ACD into undefended RAG and can
do no better.** An ACD arm below the `rag` arm would mean something other than
`d_alpha` is moving, and our account of the mechanism would be wrong.

## The design is nested, on purpose

The gradient suffix is appended to **the passage best-of-K already chose**, not
to the plain distractor sentence. The base assertion is untouched, the suffix
is initialised to `!` repeated, and the search only ever adds. So:

* the asserted answer is still fixed across every candidate, which is what made
  the best-of-K comparison clean and keeps this one clean;
* any movement past 0.653 is attributable to the gradient and to nothing else;
* the result is monotone by construction on the search objective, and we keep
  the best-of-K passage for any item the gradient fails to improve. The share
  of items where that happens is itself a reported number.

Two honest restrictions, both stated because they weaken the attack:

* **Candidate tokens are restricted to printable ASCII.** A suffix that does
  not survive a decode/re-encode round trip is not a passage an attacker can
  put in a corpus. This costs the optimiser some of the vocabulary.
* **The search objective is teacher-forced entropy on the distractor answer**,
  a single forward pass, rather than the free-running four-step measure. The
  free-running measure is what we *report*, recomputed from the final string,
  so the surrogate can only mislead the search, never the result.

## Predictions

Measured against `adaptive_acd_result.md`, same 686 items, same few-shots, same
doses, same scorer.

1. **`ent_pos` falls further.** Median below the best-of-K's 0.783. If this
   fails the search found nothing and the rest is void.
2. **`d_alpha` rises past 0.653**, toward 1.
3. **ACD's copy rate at saturation rises past 64.0 %.**
4. **The defensive gap shrinks below 25.1 pp.** This is the headline, and the
   only prediction that distinguishes degradation from collapse. Under 10 pp we
   would call ACD neutralised; between 10 and 25 pp it degrades further but
   holds something back.
5. **ACD does not fall below the `rag` arm** on copy rate, by the ceiling above.
6. **Parametric recall falls further**, from 22.2 % toward the undefended arm.

## What each outcome licenses

If 1-4 hold, the paper says ACD's resistance does not survive an attacker who
reads the method, and reports how much of it an attacker with gradients can
take. The future-work line in the conclusion becomes a result.

If 1 and 2 hold but 3 and 4 do not, that is the more interesting outcome and
the one we would have to report against our own expectation: `d_alpha` would be
moving without the copy rate following, which would mean the entropy rule is
not the whole of what protects ACD, and our mechanism account needs a term we
do not currently have.

If 1 fails, best-of-K already found what form can do, and the remaining
headroom is not reachable while the asserted answer is held fixed. That is a
real finding about the attack surface and bounds adaptive strength from below
rather than leaving it open.

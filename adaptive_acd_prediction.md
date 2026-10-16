# Adaptive attack on ACD: prediction, committed before the run

Written 2026-10-16, before the payload exists. This closes the one place where
our design repeats DeepSec's actual error (`carlini_audit.md` §1): ACD's
resistance was measured only against payloads that were not built for it.

## ACD's rule, and what the attacker controls

From `third_party/ACD/generation/gen_wrapper.py:909-919`, verbatim:

```python
probs      = F.softmax(next_token_scores, dim=-1)       # no context
probs_pos  = F.softmax(next_token_scores_pos, dim=-1)   # with context
ent        = -torch.sum(probs     * torch.log2(probs),     dim=-1)
ent_pos    = -torch.sum(probs_pos * torch.log2(probs_pos), dim=-1)
d_alpha    = (ent / (ent_pos + ent)).unsqueeze(-1)
next_token_scores = next_token_scores + d_alpha * (next_token_scores_pos - next_token_scores)
```

`ent` is a property of the question alone and the attacker cannot touch it.
`ent_pos` is computed from a distribution conditioned on the context, which the
attacker owns outright. **The attack objective is therefore exactly one
quantity: minimise `ent_pos`.**

## The ceiling, which follows from the rule rather than from any experiment

As `ent_pos -> 0`, `d_alpha -> ent/(0 + ent) = 1`, and the update becomes

```
next_token_scores  ->  next_token_scores + 1 * (next_token_scores_pos - next_token_scores)
                    =  next_token_scores_pos
```

which is the with-context distribution unchanged. **A perfect adaptive attack
turns ACD into undefended RAG and can do no better.** ACD cannot be driven
*below* its own undefended arm by this route, because `d_alpha` is bounded in
(0, 1) and the two endpoints are closed-book and plain RAG.

This is worth stating because it bounds the result in advance and makes the
experiment falsifiable in both directions: if the adaptive arm lands below the
`rag` arm, something other than `d_alpha` is moving and our account of the
mechanism is wrong.

## The attack

White-box, query-based, per item. The attacker holds the model and knows the
rule, which is the setting Carlini asks for.

For each item we build K candidate passages that **all assert the same
distractor answer**, differing only in form, measure `ent_pos` for each under
the defense's own prompt construction, and keep the argmin. Nothing about the
asserted answer changes, so any movement is attributable to the form of the
passage and not to a different claim being made.

Candidate forms are chosen to span the entropy range: the plain distractor
sentence we already use, a repetition variant, a question-restating variant
that makes the answer token maximally predictable, a multi-source
corroboration variant, and a terse declarative. The search is best-of-K rather
than gradient descent on token ids; it is weaker than a full GCG-style
optimisation, so whatever it achieves is a **lower bound** on an adaptive
attacker's strength, in the same sense our non-adaptive results already are.

## Predictions

Measured on the distractor payload, because only that arm separates copying
from remembering, and because it has the most headroom (ACD copies 40.8 %
against the undefended arm's 76.0 %).

1. **`ent_pos` falls.** Median selected `ent_pos` is below the median for the
   standard distractor passage. If this fails, the search found nothing and
   the rest of the predictions are void.
2. **`d_alpha` rises** toward 1.
3. **ACD's copy rate rises** from 40.8 % toward the undefended 76.0 %. This is
   the headline. We expect to close a substantial part of that 35.2 pp gap but
   not all of it, because best-of-K is a weak optimiser.
4. **ACD's gold accuracy falls** from 5.0 % toward the undefended 2.3 %.
5. **ACD does not fall below the `rag` arm** on copy rate. The ceiling above
   says it cannot, by construction. If it does, our reading of the mechanism
   is wrong and that is the more interesting result.
6. **Parametric recall falls** from 32.5 % toward 14.1 %, because the mass ACD
   was returning to memory is exactly the mass `d_alpha` was withholding from
   the context.

## What the outcome licenses

If predictions 1-4 hold, the paper can say ACD's resistance is an artefact of
the payloads it was tested against and does not survive an attacker who reads
the method, and the `acd_result.md` scope note becomes a measurement instead of
a caveat.

If the copy rate does **not** move, ACD's resistance is real against a
white-box attacker of this strength, which is a materially stronger claim than
anything we can make now, and it should be reported as such rather than buried.

Either outcome is publishable. That is the point of committing this first.

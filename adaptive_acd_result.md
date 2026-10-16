# An adaptive attack on ACD: the entropy rule is the vulnerability

**ACD vs an entropy-minimising distractor, n=686, Llama-3-8B-Instruct,
CoConflictQA.** Run 2026-10-16. Predictions committed in
`adaptive_acd_prediction.md` (`315b88e`) before the payload existed.

This closes the one place where our design repeated DeepSec's actual error
(`carlini_audit.md` §1): ACD's resistance had only ever been measured against
payloads that were not built for it.

## The attack

ACD mixes the no-context and with-context distributions by

    d_alpha = ent / (ent_pos + ent)
    scores  = scores + d_alpha * (scores_pos - scores)

`ent` is a property of the question. `ent_pos` is conditioned on the context,
which an attacker who owns the corpus controls outright. So the objective is
one number: minimise `ent_pos`.

White-box best-of-K. Five candidate passages per item, **all asserting the same
distractor answer**, differing only in form; each scored by the `ent_pos` ACD
itself would compute; argmin kept. Holding the asserted answer fixed is what
makes any movement attributable to form rather than to a different claim.

| form chosen | items |
|---|---:|
| multi-source corroboration | 207 |
| question restated before the answer | 186 |
| terse declarative | 121 |
| the plain distractor sentence | 102 |
| threefold repetition | 70 |

The plain sentence already minimises entropy for 102 of 686 items, so the
search is not merely relabelling everything.

## The ceiling, derived before the run

As `ent_pos -> 0`, `d_alpha -> 1` and the update collapses to `scores_pos`
unchanged. **A perfect adaptive attack turns ACD into undefended RAG and can do
no better.** ACD cannot be driven below its own undefended arm by this route.
The run is therefore falsifiable in both directions: an ACD arm below the `rag`
arm would mean something other than `d_alpha` is moving.

## What the attack did to the statistic it targets

| | median | mean |
|---|---:|---:|
| `ent_pos`, plain | 1.348 | 1.382 |
| `ent_pos`, adaptive | **0.783** | 0.826 |
| `d_alpha`, plain | 0.525 | 0.540 |
| `d_alpha`, adaptive | **0.653** | 0.653 |

## Result

Same items, same few-shots, same doses, same scorer. Left of each arrow is the
standard distractor payload, right is the adaptive one.

| dose | arm | answered correctly | recalled from memory | copied the attacker |
|---:|---|---|---|---|
| clean | rag | 68.2 -> 68.2 | 12.7 -> 12.7 | 0.7 -> 0.7 |
| | acd | 61.4 -> 61.4 | 17.8 -> 17.8 | 0.4 -> 0.4 |
| 10 % | rag | 27.4 -> 26.1 | 14.3 -> 12.4 | 46.6 -> **53.9** |
| | acd | 27.3 -> 25.8 | 28.4 -> 24.5 | 25.7 -> **32.6** |
| 50 % | rag | 15.2 -> 12.5 | 13.6 -> 11.4 | 60.4 -> **73.0** |
| | acd | 17.2 -> 14.6 | 30.8 -> 23.8 | 32.4 -> **48.8** |
| 100 % | rag | 2.3 -> 3.2 | 14.1 -> 12.4 | 76.0 -> **89.1** |
| | acd | 5.0 -> 3.2 | 32.5 -> **22.2** | 40.8 -> **64.0** |

Clean-dose rows are identical by construction: at `frac=0` no passage is
planted, so the two runs share that arm exactly. That is the control.

## All six predictions hold

1. **`ent_pos` falls.** 1.348 -> 0.783 median, a 42 % reduction.
2. **`d_alpha` rises** toward 1: 0.525 -> 0.653.
3. **ACD's copy rate rises**, 40.8 % -> **64.0 %** at saturation
   (+23.2 pp, $p = 9.5\times10^{-18}$), clearing the 7.6 pp threshold at every
   attacked dose.
4. **ACD's gold accuracy falls**, 5.0 % -> 3.2 %, landing exactly on the
   undefended arm's 3.2 % and below the no-retrieval floor of 8.2 %.
5. **ACD does not fall below the `rag` arm.** 64.0 % against 89.1 %. The
   ceiling derived from the rule holds.
6. **Parametric recall falls**, 32.5 % -> 22.2 %, toward the undefended 12.4 %.
   The mass ACD was returning to memory is the mass `d_alpha` was withholding
   from the context, and the attack takes it back.

## How much protection was removed, stated honestly

The adaptive payload is stronger against the **undefended** arm too: `rag`
copying rises 76.0 % -> 89.1 %. Reporting only ACD's rise would credit the
defense's collapse with damage the attack does to everyone.

The quantity that isolates the defense is the gap between the arms:

| | rag copies | acd copies | defensive gap |
|---|---:|---:|---:|
| standard distractor | 76.0 | 40.8 | **35.1 pp** |
| adaptive distractor | 89.1 | 64.0 | **25.1 pp** |

**29 % of ACD's protection is removed by a best-of-five search over sentence
templates.** Not all of it. `d_alpha` reached 0.653 of a possible 1.0, so most
of the headroom is still there.

## What this licenses, and what it does not

**The claim that ACD's resistance is an artefact of the payloads it met is now
measured rather than suspected.** An attacker who reads the method and spends
five forward passes per item removes nearly a third of the protection, moves
the exact statistic the method keys on, and drives accuracy onto the undefended
arm and below a no-retrieval baseline. The scope note in `acd_result.md` can
cite this run instead of hedging.

**It does not establish that ACD is broken.** A 29 % reduction from a weak
optimiser is a lower bound, and the honest reading is that the defense degrades
under adaptive pressure rather than that it collapses. Best-of-K over five
hand-written templates is the cheapest adaptive attack that exists. A
GCG-style search over token ids, optimising `ent_pos` directly rather than
choosing among five phrasings, has the whole remaining 0.35 of `d_alpha` to
work with.

**The direction is what matters for the paper.** Every published evaluation of
a context-reliance defense in our corpus is non-adaptive. This run shows the
gap between non-adaptive and adaptive is large enough to change the verdict on
the one defense that looked like a counterexample.

## Open

A gradient-based optimiser on `ent_pos`, which is the proper version of this
attack. Also: ACD leaks 16.8 pp out of the three-way partition under the
standard payload and that is unexplained; under the adaptive payload the leak
is smaller, which is worth a look but was not predicted and should not be read
as a result.

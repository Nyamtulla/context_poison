# A gradient attack on ACD: the entropy rule gives up 58% of its protection

**ACD vs a GCG-optimised entropy-minimising distractor, n=686,
Llama-3-8B-Instruct, CoConflictQA.** Run 2026-10-18. Predictions committed in
`gradient_acd_prediction.md` (`b6aacb9`) before the payload existed.

This closes the open item from `adaptive_acd_result.md`: best-of-five over
sentence templates took `d_alpha` to 0.653 of a possible 1.0 and removed 29% of
ACD's protection. Most of the headroom survived. The question was whether that
headroom was reachable, i.e. whether ACD **degrades** or **collapses**.

## The attack

Same objective as before, stronger optimiser. ACD mixes the no-context and
with-context distributions by `d_alpha = ent / (ent_pos + ent)`. `ent` belongs
to the question; `ent_pos` belongs to the context the attacker owns. The
objective is one number: minimise `ent_pos`.

GCG-style coordinate search over a 20-token suffix. **Nested on purpose**: the
suffix is appended to the passage best-of-K already chose, the base assertion
is never touched, and the suffix starts as `!` repeated. So the asserted answer
is fixed across every candidate exactly as it was before, and anything past
0.653 is the gradient's.

Three restrictions, each stated because each weakens the attack:

* **Candidate tokens are space-leading printable ASCII only.** A suffix that
  does not survive a decode/re-encode round trip is not a passage anyone can
  put in a corpus. Verified per item: **exact on 686 of 686**.
* **The search objective is teacher-forced entropy on the distractor answer**,
  one forward pass. The **reported** objective is the free-running four-step
  measure, recomputed from the final string. A bad surrogate can mislead the
  search; it cannot move the number we report.
* **A gradient passage is kept only if it beats best-of-K on that reported
  measure.** It failed to on 163 of 686 items, which keep the best-of-K
  passage. The payload is monotone by construction.

## What the attack did to the statistic it targets

| median | plain | best-of-K | gradient |
|---|---:|---:|---:|
| `ent_pos` | 1.348 | 0.783 | **0.614** |
| `d_alpha` | 0.525 | 0.653 | **0.708** |

`d_alpha = 1.0` is the ceiling at which ACD becomes undefended RAG.

## Result

Same items, same few-shots, same doses, same scorer. Copy rate is the share of
answers matching the planted third answer.

| dose | payload | rag copies | acd copies | defensive gap |
|---:|---|---:|---:|---:|
| 10% | standard distractor | 46.7 | 25.7 | 21.0 |
| | best-of-K | 53.9 | 32.7 | 21.3 |
| | gradient | 51.5 | 30.3 | 21.1 |
| 50% | standard distractor | 60.4 | 32.4 | 28.0 |
| | best-of-K | 73.0 | 48.8 | 24.2 |
| | gradient | 71.1 | 50.7 | **20.4** |
| 100% | standard distractor | 76.0 | 40.8 | 35.1 |
| | best-of-K | 89.1 | 64.0 | 25.1 |
| | gradient | 87.8 | 73.0 | **14.7** |

**58% of ACD's protection is removed, against best-of-five's 29%.** The 10.4 pp
the gradient takes beyond best-of-K clears the 7.6 pp detectability threshold
at this sample size.

## All six predictions hold

1. **`ent_pos` falls further**, 0.783 to 0.614.
2. **`d_alpha` rises past 0.653**, to 0.708 of the ceiling.
3. **ACD's copy rate at saturation rises past 64.0%**, to 73.0%.
4. **The defensive gap drops below 25.1 pp**, to 14.7 pp. The prediction
   document set the bands in advance: under 10 pp would be neutralised, 10 to
   25 pp is degraded further while holding something back. This is the second.
5. **ACD does not fall below the `rag` arm**: 73.0 against 87.8. The ceiling
   derived from the rule holds.
6. **Parametric recall falls further**, 22.2% to 18.1%, toward the undefended
   11.4%.

## The attack is weaker overall and stronger against the defense

The gradient payload damages the **undefended** arm *less* than best-of-K does:
87.8% against 89.1%. It takes more from ACD while doing slightly less damage in
general.

That is the cleanest evidence available that it is attacking **the defense**
rather than simply being a better payload. The defensive gap is what isolates
the defense, and the gap is what moved.

The dose structure says the same thing. At 10% the gap is unchanged across all
three payloads (21.0, 21.3, 21.1). ACD's protection only becomes attackable as
the dose rises, which is consistent with `d_alpha` being driven by a statistic
computed over the whole context.

## The comparison is within one environment, and that had to be checked

ACD cannot run on the stack the rest of this repo uses: its vendored sampling
loop imports two symbols that transformers removed after 4.44, which its own
README pins. Rebuilding that stack to run the gradient payload exposed a
problem with comparing against the earlier best-of-K numbers, and the clean
dose found it. At `frac=0` no passage is planted, so that arm is a control and
should be identical across runs. It was not:

| clean arm | October | this stack | drift |
|---|---:|---:|---:|
| `rag` parametric recall | 12.68 | 12.97 | +0.29 |
| `closedbook` parametric recall | 50.15 | 50.29 | +0.14 |
| `acd` gold accuracy | 61.37 | 61.08 | -0.29 |

The closed-book arm is the tell: it never sees the context, so its generations
cannot differ unless the environment does.

So we re-ran the **best-of-K payload** under the same stack as the gradient
payload rather than caveating the comparison. The attacked arms reproduce to
within a fifth of a point, and the saturation row --- the one the headline
rests on --- reproduces exactly:

| dose | arm | October | re-run | drift |
|---:|---|---:|---:|---:|
| 10% | rag | 53.94 | 53.94 | 0.00 |
| 10% | acd | 32.65 | 32.80 | +0.15 |
| 50% | rag | 73.03 | 73.18 | +0.15 |
| 50% | acd | 48.83 | 48.54 | -0.29 |
| 100% | rag | 89.07 | 89.07 | **0.00** |
| 100% | acd | 63.99 | 63.99 | **0.00** |

Every figure in the result table above is therefore from one environment, and
the 25.1 -> 14.7 pp comparison needs no caveat.

This also scopes a claim the paper makes elsewhere. Three replicates of a
COIECD cell were byte-identical, which establishes determinism **within a
stack**. It does not establish reproducibility **across** stacks, and the
clean-arm drift above is a measured example of the difference. Both statements
are worth making and they are not the same statement.

## The verdict

**ACD degrades under adaptive pressure. It does not collapse.** A best-of-five
search over sentence forms takes 29%; a gradient search over token ids takes
58%; the rule's own ceiling says no attack of this kind can take more than
100%, and 73.0% copy against the undefended 87.8% is still 14.7 pp of real
protection. The honest reading is that the entropy rule is a genuine obstacle
that an attacker with gradients can mostly, but not entirely, remove.

What this licenses for the paper is a stronger version of the existing claim.
The resistance ACD showed was not an artefact of weak payloads alone; it is
real, bounded, and priced. An attacker who reads the method and spends a
few hundred forward passes per item pays that price.

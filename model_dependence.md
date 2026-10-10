# The safer family is the one that breaks the attack open

**Model-controlled rerun: RobustRAG on the other family's model.** 2026-10-07.

## Why this run exists

Two claims rested on a comparison that was not model-controlled. RobustRAG ran
on Mistral-7B; ParamMute, CK-PLUG and SpARE ran on Llama-3-8B-Instruct, because
those are the models each paper released. Both the tone finding and the
KeywordAgg/DecodingAgg divergence were measured across that split.

RobustRAG's own registry already carries a `llama8b` entry for exactly the
model the other family uses, so the rerun needed no new method — only the right
weights. Four cells, n=300, everything else unchanged.

## Result 1 — the tone finding survives the control, unchanged

Negative-framing rate at full dose:

| model | KeywordAgg | DecodingAgg |
|---|---|---|
| Mistral-7B-Instruct | 0.0 % → 0.3 % | 0.0 % → 0.3 % |
| Llama-3-8B-Instruct | 0.0 % → 0.0 % | 0.0 % → 0.0 % |

Two models, two implementations, four cells, all at or below 0.3 %. Against
CK-PLUG's 99.0 % on the same attack and the same model. **The claim that
aggregation does not open the tone-steering hole is now model-controlled and
holds.**

## Result 2 — and the refusal result inverts on the other model

Refusal rate under BadRAG DoS, the undefended arm against the defended arm:

| model | implementation | 5/10 | 7/10 | 9/10 | 10/10 |
|---|---|---:|---:|---:|---:|
| Mistral | KeywordAgg | 4.7 % | 4.0 % | 5.7 % | 5.3 % |
| Mistral | DecodingAgg | 4.0 % | 4.3 % | 3.7 % | 3.0 % |
| **Llama-3** | **KeywordAgg** | **62.3 %** | **74.3 %** | **85.0 %** | **84.0 %** |
| **Llama-3** | **DecodingAgg** | **43.0 %** | **76.3 %** | **85.3 %** | **87.3 %** |

**The undefended arm never refuses. Not once, at any dose, on either model.**
Every number above is produced by switching the defense on.

So the aggregation family does to refusal induction exactly what CK-PLUG does
to tone steering: it converts an attack the base model ignores into one that
works most of the time. Eight resolvable increases in attack success, 43 to 87
points, across both implementations.

## What this does to the earlier reading

> **Correction.** `aggregation_divergence.md` reported KeywordAgg and
> DecodingAgg disagreeing by 29.6 points at 9/10 and read that as
> implementation mattering more than family. The accuracy numbers behind it are
> unchanged and the hard-filter/soft-average mechanism still predicts them. But
> that divergence exists **only on Mistral**. On Llama-3 the two implementations
> agree closely — 85.0 % and 85.3 % — and both fail. The dominant variable is
> the model, not the implementation.

The campaign has now produced three claims at three different scopes, and they
should not be stated at the same confidence:

| claim | scope | evidence |
|---|---|---|
| Aggregation does not lose accuracy at saturation | **family** | 0 of 10 usable cells, 2 models, 2 implementations |
| Aggregation does not open the tone-steering hole | **family** | 4 cells, 2 models, 2 implementations |
| Hard filtering beats soft averaging below saturation | **one model** | Mistral only; the gap closes on Llama-3 |
| Aggregation is safe against refusal induction | **false** | 0 % → 87 % on Llama-3, both implementations |

## The mechanism, and why it is model-dependent

Isolation is the thing that helps against tone steering, and it is the same
thing that hurts here.

RobustRAG answers each passage **alone**. A BadRAG DoS passage, read alone,
is an unopposed instruction to refuse — there is no honest passage beside it to
argue with. On a model that is willing to refuse, every poisoned passage
produces a refusal, and the aggregation step then sees mostly refusals. The
undefended model reads all ten passages in one window, where nine honest
passages dilute the instruction, and it never refuses at all.

That predicts the effect needs a refusal-prone target, which is what the two
models show: Llama-3-8B-Instruct refuses readily, Mistral-7B-Instruct-v0.2 does
not. It also matches the earlier finding that BadRAG's DoS attack scores 0 % on
the **base** (non-instruct) Llama-3-8B.

**Isolate-then-aggregate trades dilution for exposure.** Dilution is what
protects an undefended model from a minority of poisoned passages. Removing it
is exactly why the family resists tone steering, and exactly why it collapses
under refusal induction.

## What an attacker should take from this

- Against a context-reliance defense, steer tone. One passage in ten is enough.
- Against an isolate-then-aggregate defense, induce refusal. Five passages in
  ten already gives 43 to 62 %, and the undefended model would have ignored it.
- Both routes need the defense to be present. Neither works on the bare model.

## Limits

- Two models. The split tracks refusal-proneness, which is a plausible
  mechanism but is not itself measured here — an alignment-strength sweep
  would test it directly.
- `open_nq` only, RobustRAG's released configuration, authors' scorers
  unchanged.
- The accuracy column on the Llama cells is attributable: both controls fire
  (−8.7 and −6.0 pp at poison 0, against an 11.4 pp threshold).

---

## Addendum, 2026-10-08: the other family moves too, but not as far

The obvious follow-up was whether context-reliance's tone failure is also
model-dependent. Only CK-PLUG could answer it — ParamMute ships as a merged
Llama-3-8B checkpoint, so moving it would mean retraining it rather than
running it.

Negative-framing rate, CK-PLUG, same attack and same data on both models:

| poison | Llama-3-8B undefended | Llama-3-8B CK-PLUG | Mistral-7B undefended | Mistral-7B CK-PLUG |
|---:|---:|---:|---:|---:|
| 0/10 | 0.0 % | 0.0 % | 0.0 % | 0.4 % |
| 1/10 | 0.0 % | **78.2 %** | 0.0 % | **9.8 %** |
| 10/10 | 4.0 % | **99.0 %** | 1.2 % | **21.6 %** |

Both increases clear the 8.9 pp threshold at n=500. So the two families are
model-dependent in **different ways**, and the difference matters:

| | Llama-3-8B | Mistral-7B | reading |
|---|---|---|---|
| context-reliance, tone steering | +95.0 pp | +20.4 pp | **present on both.** The model scales it, about five times over. |
| isolate-then-aggregate, refusal | +85.0 pp | +5.7 pp, not resolvable | **present on one.** The model decides whether it happens at all. |

> **The direction of the context-reliance failure is a property of the
> defense. Its size is a property of the model. The aggregation failure is a
> property of the pair.**

That is the sharper statement, and it is only available because both families
were run on both models. Neither cell alone supports it.

A caution that comes with it: CK-PLUG's control fails worse on Mistral than on
Llama — 59.4 % against 25.4 % at poison 0, a 34-point gap against an 8.9-point
threshold. Nothing in its accuracy column is attributable on either model. The
framing column is readable for the usual reason: both arms sit at 0.0 % when no
passage is poisoned, so the defense does not generate slant on its own.

**Incomplete.** CK-PLUG × PoisonedRAG on Mistral was running when another job
on the shared GPU took 33 GB and the run died of memory exhaustion partway
through the undefended arm. That cell is unmeasured and is not counted
anywhere above.

---

## Addendum, 2026-10-10: the direction flips too

The PoisonedRAG half of the CK-PLUG run finally completed, on the third
attempt. It overturns the statement in the previous addendum.

CK-PLUG against lie insertion, attack success:

| poison | Llama-3 undef. | Llama-3 CK-PLUG | Δ | Mistral undef. | Mistral CK-PLUG | Δ |
|---:|---:|---:|---:|---:|---:|---:|
| 1/10 | 23.2 % | 32.6 % | **+9.4** ✱ | 32.8 % | 22.2 % | **−10.6** ✱ |
| 5/10 | 35.6 % | 36.2 % | +0.6 | 43.0 % | 32.0 % | **−11.0** ✱ |
| 10/10 | 68.2 % | 63.6 % | −4.6 | 71.4 % | 61.8 % | **−9.6** ✱ |

✱ clears the 8.9 pp threshold at n=500.

**The same defense, against the same attack, on the same data: it makes the
attack work better on one model and stops it on the other.** On Mistral it is
protective at every dose. On Llama it is harmful at one poisoned passage and
not readable after that. At 1/10 the two models are 20 points apart, across
zero.

> **Correction.** The previous addendum concluded: *"the direction of the
> context-reliance failure is a property of the defense, its size is a property
> of the model."* That was drawn from tone steering alone, where CK-PLUG is
> harmful on both models and only the magnitude moves — 95.0 pp against
> 20.4 pp. Against lie insertion the sign itself moves. **Direction is not a
> property of the defense either.**

What survives is weaker and, now, better supported:

| what moves with the model | evidence |
|---|---|
| **the size** of a defense's effect | CK-PLUG, tone steering: +95.0 vs +20.4 pp |
| **whether the effect happens at all** | RobustRAG, refusal: +85.0 vs +5.7 pp, not resolvable |
| **the sign of the effect** | CK-PLUG, lie insertion: +9.4 vs −10.6 pp |

> **Nothing about a defense's effect on an attack is a property of the defense
> on its own.** The model is not a nuisance parameter to be averaged over. It
> is part of the result, and a paper reporting one model has reported one
> point, not a finding.

The accuracy column stays unreadable on both models — CK-PLUG's control fails
by 22.6 pp on Llama and 34.0 pp on Mistral. The attack-success column carries
its own control: with no poisoned passage both arms sit near zero on both
models, 3.8/2.8 % and 3.0/1.4 %.

**Three attempts.** Two died of CUDA OOM at the same dose when another user's
job on the shared card grew to 33 GB mid-run — their 33 GB plus our 15 GB
against a 47.5 GB card. Waiting for free memory before starting does not help
when the other job expands into whatever is free; what worked was requiring
30 GB of headroom, enabling expandable segments, and retrying.

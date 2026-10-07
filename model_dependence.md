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

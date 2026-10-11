# The mechanism holds. The reason I gave for it does not.

**Five models, RobustRAG KeywordAgg against BadRAG DoS, n=200 each.**
2026-10-10.

## What was being tested

`model_dependence.md` claimed the aggregation family's refusal failure is
caused by **isolation**: the defense answers each retrieved passage alone, so a
passage saying "refuse" gets an unopposed hearing, while an undefended model
reads all ten together where nine honest passages drown it out.

That is a claim about the model, so varying the model tests it. The probe is
not a proxy — KeywordAgg's own first step is
`wrap_prompt(as_multi_choice=False, seperate=True)`, one prompt per passage, and
refusal was scored over those raw per-passage responses **before** aggregation.
Three numbers per model at nine poisoned passages of ten.

## Result

| model | isolated | undefended | defended | defended − isolated |
|---|---:|---:|---:|---:|
| Llama-3-8B-Instruct | **78.95 %** | 0.00 % | **85.00 %** | +6.05 |
| Mistral-7B-Instruct | 5.41 % | 0.00 % | 6.50 % | +1.09 |
| Vicuna-7B | 0.45 % | 0.00 % | 0.00 % | −0.45 |
| Llama-2-13B-chat | 0.00 % | 0.00 % | 0.00 % | +0.00 |
| Llama-2-7B-chat | 0.00 % | 0.00 % | 0.00 % | +0.00 |

Nearly 2,000 isolated passages per model, about 10,000 in all.

**The mechanism is confirmed, and about as cleanly as this kind of thing comes.**

- **Defended tracks isolated almost exactly.** Pearson r = 0.9999 across the
  five models, and the largest gap between the two columns is 6 points. What
  the model does with one poisoned passage shown alone is what the defense
  then does overall.
- **The undefended arm is 0.00 % on every model.** Not low — zero, on all five,
  at this dose. The attack does nothing to any of these models when the ten
  passages are read together. Every bit of its success comes through the
  defense.

## But the explanation for *which* models was wrong

The prediction attached to that mechanism was that the effect needs a
refusal-prone target, and the test was built with that in mind:
**Llama-2-chat was included because it is the most refusal-trained model in the
set**, so it should have been the worst case.

It scores **0.00 %**. Both sizes of it. It is the furthest thing from the worst
case.

> **So "alignment strength" or general refusal-proneness does not predict this
> at all.** The one model that breaks is Llama-3-8B-Instruct. Llama-2-chat,
> trained hard to refuse, never refuses here — because what it was trained to
> refuse is harmful requests, and a passage asking it to decline to answer a
> trivia question is not one.

What separates Llama-3-8B-Instruct from the other four is more plausibly
**instruction-following**: it treats text in a retrieved passage as an
instruction and complies. The others do not follow the embedded instruction at
all — Vicuna and both Llama-2-chats sit at or below 0.45 %.

That is a hypothesis, not a result. It is testable, with an
instruction-following benchmark rather than a safety one, and that test has not
been run.

## What this is worth

The design rule stands and is now mechanistic rather than observational: an
isolate-then-aggregate defense inherits whatever the model does to a single
poisoned passage, multiplied across the retrieved set. You can predict the
defense's behaviour from a one-passage probe, which costs a fraction of a full
evaluation.

The corollary is the uncomfortable half. **The probe says nothing about whether
a model is safe.** It says whether the model will follow an instruction it
finds in retrieved text. The most safety-tuned model in this set is the one
that ignores the attack completely, and the most capable instruction-follower
is the one that falls for it 85 % of the time.

## Limits

- Five models, one attack, one dose, one dataset.
- The instruction-following explanation is untested.
- RobustRAG KeywordAgg only; DecodingAgg was not swept, though it matched
  KeywordAgg on both models where both were run.
- Three attempts were needed to get this file written at all. The first two
  sweeps ran the full measurement on all five models and then died on a
  `NameError` in the save path, discarding roughly five hours of GPU time.

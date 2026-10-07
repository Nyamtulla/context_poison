# Principle or implementation? A second aggregation defense answers it

**RobustRAG DecodingAgg vs KeywordAgg, three attacks, n=300.** 2026-10-06.

## The question this run exists to answer

The campaign's strongest claim is a design rule: *do not suppress parametric
memory; isolate-then-aggregate does not have this failure mode.* Every
aggregation number behind it came from **one defense** — RobustRAG's
KeywordAgg. A single implementation cannot tell you whether you have found a
property of the **principle** or a quirk of the **code**.

So: run a second aggregation implementation that shares the principle and
shares no decision logic.

| | KeywordAgg | DecodingAgg |
|---|---|---|
| per-passage step | answer each passage separately | answer each passage separately |
| aggregation | extract keywords, keep those appearing above a count threshold, re-prompt | average the next-token distributions, decode from the aggregate |
| operates on | text | logits |
| shared code | the isolation loop and the prompt builder | — |

They agree on the principle and disagree on everything downstream of it. If
the behaviour is the principle's, both show it. If it is KeywordAgg's, only one
does.

MajorityVoting, the third variant, is not in this comparison and cannot be:
its `query()` calls `wrap_prompt(data_item, as_multi_choice=True)` and only
works on multiple-choice data, so it cannot run on open-ended `open_nq`. It is
excluded for being inapplicable, not for failing.

## Result 1 — aggregation does not open the hole; context-reliance does

Negative-framing rate under BadRAG Selective-Fact. **Read the undefended
column first**, because it changes what the rest of the table means:

| poison | undefended (Mistral-7B) | **KeywordAgg** | **DecodingAgg** |
|---:|---:|---:|---:|
| 0/10 | 0.0 % | 0.0 % | 0.0 % |
| 1/10 | 0.0 % | 0.0 % | 0.0 % |
| 5/10 | 0.0 % | 0.3 % | 0.0 % |
| 9/10 | 0.0 % | 0.3 % | 0.3 % |
| 10/10 | 0.0 % | 0.3 % | 0.3 % |

| poison | undefended (Llama-3-8B-Instruct) | ParamMute | **CK-PLUG** |
|---:|---:|---:|---:|
| 0/10 | 0.0 % | 0.4 % | 0.0 % |
| 1/10 | 0.0 % | 0.0 % | **78.2 %** |
| 5/10 | 0.4 % | 0.2 % | **96.0 %** |
| 9/10 | 2.0 % | 4.2 % | **97.0 %** |
| 10/10 | 4.0 % | **28.8 %** | **99.0 %** |

> **This corrects an over-read carried in `family_dissociation.md`.** Those
> numbers were described as RobustRAG being *immune* to the tone attack. The
> undefended model is also at 0.0 %. **The attack does not work on an
> undefended model in this setup at all.** It only works *through* a
> context-reliance defense. Aggregation is therefore not providing protection
> the baseline lacks — it is declining to create a vulnerability the baseline
> does not have. That is a real and useful property, but it is a different
> claim and the weaker word is the correct one.

So the finding is about what each family *costs*, not what it saves:

- **Context-reliance converts a no-op into a 99 % attack.** CK-PLUG takes an
  attack the base model ignores entirely and makes it work almost every time,
  with **one poisoned passage out of ten**. ParamMute does the same thing more
  weakly (0.0 % → 28.8 %).
- **Both aggregation implementations leave the base model's behaviour
  intact** — 0.0 % → 0.3 %, at every dose, with no shared aggregation logic
  between them.

The mechanism is the same one in both directions, which is why it is
predictable rather than lucky: tone steering does not corrupt the *answer*, so
a defense that pushes the model to follow the retrieved text will faithfully
follow the slant and score itself as working perfectly. **The attack and the
defense want the same thing.** A defense that answers each passage separately
and aggregates has no such lever to pull.

**One confound, stated plainly.** The two families were run on different
models — RobustRAG on Mistral-7B (its own released configuration), ParamMute
and CK-PLUG on Llama-3-8B-Instruct (theirs). The comparison across families
is therefore not model-controlled. It survives anyway for this metric, because
**both undefended arms sit at or near 0.0 %**: whatever the model, the base
behaviour is the same, and the 99 % is produced by the defense. A
model-controlled rerun would still be worth having.

## Result 2 — and DecodingAgg is markedly stronger against lie insertion

This was not predicted. Against PoisonedRAG, attack success:

| poison | undefended | **DecodingAgg** | Δ | KeywordAgg Δ |
|---:|---:|---:|---:|---:|
| 1/10 | 32.3 % | **6.0 %** | **−26.3** | — |
| 5/10 | 45.3 % | 34.7 % | −10.6 | — |
| 9/10 | 58.3 % | **37.7 %** | **−20.6** | — |
| **10/10** | 76.0 % | **37.3 %** | **−38.7** | **−15.3** |

Bold clears the 11.4 pp threshold at n=300.

DecodingAgg halves attack success at full saturation — **−38.7 pp against
KeywordAgg's −15.3 pp on the identical cell** — and it does so without paying
for it: accuracy at 10/10 is −2.0 pp, not resolvable, the same neutral
saturation behaviour as every other aggregation cell.

Note what that number means. At 10/10 *every* passage is a PoisonedRAG lie, so
there is no honest passage to outvote with. DecodingAgg still refuses the lie
37.3 % less often than the undefended model. Averaging logits across ten
copies of a lie does not reproduce the lie as confidently as reading them in
one window does — the attack's advantage comes partly from **accumulated
textual weight**, and aggregation removes that even when it cannot remove the
content.

## What this does to the design rule

Before: *isolate-then-aggregate does not collapse at saturation* — one
implementation, three attacks.

After: *isolate-then-aggregate does not collapse at saturation, and does not
open the tone-steering hole that context-reliance opens* — **two
implementations with no shared decision logic, five cells, zero resolvable
accuracy losses.** And the stronger of the two
implementations is also the one that reduces attack success the most, so the
rule does not trade robustness for utility.

| family | attributable cells at 10/10 | resolvable accuracy loss |
|---|---:|---:|
| isolate-then-aggregate | 5 of 5 | **0** |
| context-reliance | 5 of 8 | **4** |

## Limits

- **Two implementations, one repository.** KeywordAgg and DecodingAgg share no
  aggregation logic but do come from one paper and one codebase. An
  aggregation defense from a different group is the next real test.
- The DecodingAgg × BadRAG-DoS cell is still running; the family claim at
  saturation currently rests on five cells, not six.
- `10/10` remains an artificial corner, and these defenses are robust across
  the realistic range. That should not be lost in the headline.
- Same scorers, payloads, prompts and data as every other cell in the matrix,
  all the original authors' code.

# A distractor answer separates copying from remembering, and both defenses fail it

**ParamMute vs distractor evidence, n=781, Llama-3-8B-Instruct, CoConflictQA.**
2026-10-15. Regenerate the payload with
`python3 scripts/build_distractor_payload.py`.

## Why this run exists

`false_evidence_result.md` ends on a limitation it could not resolve. Under
false evidence the planted passage asserts the same string the model would have
recalled, so the parametric-answer rate cannot distinguish a model that
**remembered** from one that **copied**. They produce identical output.
ParamMute's residual 58.8 % at saturation could have been either.

The paper's own future-work section proposed planting the **gold** answer to
separate them. That does not work: gold is already in the real context, so an
output of gold stays two-ways ambiguous.

A **third** answer works. Plant a fluent sentence asserting something that is
neither the gold nor the model's prior, built by substituting a distractor into
the item's own evidence sentence so the register is unchanged:

| the model outputs | what it did |
|---|---|
| gold | read the real context |
| the parametric answer | recalled from memory |
| **the distractor** | **copied the planted passage** |

Three disjoint outcomes, checked per item at build time.

## The control that licenses everything below

**At clean dose the distractor rate is 0.8 % undefended and 0.6 % defended.**
The distractor answer essentially never appears unless it is planted. Any
distractor rate under attack is therefore copying, not coincidence.

## Result

n=781, mdr 7.1 pp. Fisher exact, `*` clears both.

| dose | gold undef | gold PM | memory undef | memory PM | copied undef | copied PM |
|---:|---:|---:|---:|---:|---:|---:|
| clean | 49.5 | **59.5** (+10.0*) | 23.4 | **12.6** (−10.9*) | 0.8 | 0.6 |
| 10 % | 22.3 | 21.2 (−1.0) | 28.0 | **10.9** (−17.2*) | 38.4 | **54.3** (+15.9*) |
| 50 % | 13.3 | 9.3 (−4.0) | 30.2 | **5.6** (−24.6*) | 44.2 | **71.5** (+27.3*) |
| 100 % | 5.4 | 1.5 (−3.8) | 39.0 | **2.9** (−36.1*) | 43.9 | **81.4** (+37.5*) |

## What it says

**ParamMute is not failing at its job. It is succeeding.** Its stated purpose
is to suppress the model's parametric memory, and it does so emphatically: at
saturation the memory rate falls from 39.0 % to 2.9 %, a 36.1 point
suppression, resolvable at every dose.

**The freed probability mass does not go to the truth.** Accuracy against the
gold answer moves from 5.4 % to 1.5 %, a 3.8 point fall that does not clear the
7.1 pp threshold. Suppressing memory did not make the model read the real
context better.

**It goes to the attacker, almost one for one.** The copy rate rises from
43.9 % to 81.4 %, a 37.5 point gain against the 36.1 points removed from
memory. ParamMute nearly doubles the rate at which the model repeats the
planted falsehood.

> A defense that suppresses parametric memory does not create accuracy. It
> creates a vacancy, and under attack the attacker fills it.

That is a sharper claim than anything the corpus-poisoning or false-evidence
runs could support, and it is only sayable because the three outcomes are
disjoint here.

## What it resolves

The open question in `false_evidence_result.md` was whether ParamMute's
residual parametric rate under false evidence was surviving memory or copying.
**It was copying.** When the planted answer is distinguishable from memory,
the memory rate collapses to 2.9 % while the copy rate reaches 81.4 %. The
earlier number was a measurement artefact of the two paths producing the same
string, exactly as that document warned.

## Scope

Restricted to the 781 of 1409 CoConflictQA items whose parametric answer
appears verbatim in their own evidence sentence, since those are the ones a
substitution can be made in without rewriting the sentence. Every arm is
measured on that subset, so all comparisons are internal to the run.

Distractors are drawn from another item's parametric answer, matched on the
question's wh-word and on digit count for numerics, so a person replaces a
person and a year replaces a year. Two earlier builds were discarded for
producing implausible payloads: "Season 4 of Chicago Fire consists of 1978
episodes" and "The Prime Minister, Shri dura mater". A payload a reader would
dismiss tests the attack at its weakest.

## ACD, on the same payload

ACD is the second defense run on this payload, for the reason the previous
version of this section gave: it is the one defense in the cell that resisted
corpus poisoning, and its rule keys on entropy, which a fluent sentence lowers.
n=686, mdr 7.6 pp (ACD holds out 5 few-shot items and filters to <=2000
characters, so 686 of the 781 survive). Three arms in one run: `rag`
(undefended), `closedbook` (no document at all), `acd`.

| dose | gold rag | gold ACD | memory rag | memory ACD | copied rag | copied ACD |
|---:|---:|---:|---:|---:|---:|---:|
| clean | 68.2 | 61.4 | 12.7 | 17.8 | 0.7 | 0.4 |
| 10 % | 27.4 | 27.3 | 14.3 | **28.4*** | 46.6 | **25.7*** |
| 50 % | 15.2 | 17.2 | 13.6 | **30.8*** | 60.4 | **32.4*** |
| 100 % | 2.3 | 5.0 | 14.1 | **32.5*** | 76.0 | **40.8*** |

`closedbook` is flat at gold 8.2 / memory 50.1 / copied 1.0 by construction:
no document, so the dose cannot reach it. Its copy rate of 1.0 % is the second
control - a model that never sees the passage never emits the distractor.

**ACD really does refuse the passage.** The copy rate at saturation is 40.8 %
against 76.0 % undefended, a 35.2 point reduction, p=2e-40. That is the
largest defensive effect anywhere in this campaign, and it is in the direction
a defense is supposed to move.

**The refused mass goes to memory, not to the document.** Parametric recall
rises 14.1 -> 32.5 (p=7e-16) while gold accuracy moves 2.3 -> 5.0, which clears
Fisher (p=0.014) but not the 7.6 pp detectability threshold. ACD is not
recovering the real passage that is still sitting in the unpoisoned 0 % of the
context. It is falling back on what the model already knew.

**And what it knew is worse than not retrieving at all.** The `closedbook` arm
answers 8.2 % correctly with no document. ACD under saturation answers 5.0 %.
A defended retrieval pipeline under this attack is below the baseline of
switching retrieval off, so the defense's resistance does not translate into
usable accuracy.

This is the same shape as ParamMute, read from the other end. ParamMute
suppresses memory and the attacker fills the vacancy; ACD suppresses the
attacker and memory fills it. Neither defense moves probability mass toward
the real document, because neither mechanism can tell the real document from
the planted one - both only arbitrate between *context* and *parameters*, and
the attack lives inside the context.

## Open

CK-PLUG and COIECD on this payload would complete the family. Both were run on
false evidence already, so the item set and the dosing carry over unchanged.

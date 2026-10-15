# ParamMute works, and hands the freed probability mass to the attacker

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

## Open

Only ParamMute has been run. ACD is the obvious second, because its entropy
rule should treat a fluent distractor the way it treats fluent false evidence,
and because it is the one defense that resisted corpus poisoning. CK-PLUG and
COIECD would complete the family.

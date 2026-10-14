# Three defenses, two payloads: what the context-reliance family keys on

**ParamMute, CK-PLUG and COIECD against false evidence.** Predictions committed
in `2c33139` before any of the three ran. 2026-10-15.

Every defense here was already measured against corpus poisoning. These runs
change one thing: the planted passage. Same items, same doses, same scorer,
same undefended arm in the same run, same released code and weights.

| payload | what it is | how it attacks |
|---|---|---|
| **corpus poisoning** | a gradient-optimised token sequence, incoherent to read | displaces honest documents out of the retrieved window |
| **false evidence** | a fluent sentence asserting the model's own prior wrong answer | agrees with what the model already believed |

Regenerate every table below with `python3 scripts/false_evidence_comparison.py`.

---

## The result in one line

**The harm these defenses do is not a property of "being attacked". It is a
property of what the attack takes away.**

| defense | excess damage, corpus poisoning | excess damage, false evidence |
|---|---:|---:|
| ParamMute | **+13.5 pp** | **+12.3 pp** |
| CK-PLUG | **+5.4 pp** | +0.4 pp |
| COIECD | +1.0 pp | −1.2 pp |

Excess damage is the clean-to-saturation collapse of the defended arm minus
the same collapse in its own undefended arm. Positive means the defense lost
more accuracy than doing nothing would have.

---

## ParamMute: the prediction holds, and the mechanism is visible

Committed prediction: *"should be harmful, and for a new reason. ParamMute
suppresses the model's memory of the right answer and the context re-supplies
the same wrong answer. Both paths now lead to the planted answer."*

n=1409, mdr 5.3 pp. Control fires identically in both runs, so the defense is
working as published before the attack starts.

| dose | corpus poisoning | false evidence |
|---|---:|---:|
| clean | **+9.3** (p<0.001) | **+9.7** (p<0.001) |
| 10% | +0.2 | +0.8 |
| 50% | −2.3 | −0.5 |
| 100% | **−4.2** (p<0.001) | **−2.6** (p<0.001) |

The harm reproduces: +13.5 pp excess under corpus poisoning, +12.3 pp under
false evidence. A defense worth +9.7 pp on honest context costs more than it
is worth as soon as an adversary writes the context, and it does not matter
whether the adversary writes gibberish or prose.

**The mechanism signature is the interesting part.** ParamMute's whole job is
to suppress the parametric answer. Measure how well it does that job:

| dose | suppression, corpus poisoning | false evidence |
|---|---:|---:|
| 10% | −16.8 pp | −10.3 pp |
| 50% | −25.7 pp | −9.0 pp |
| 100% | **−42.5 pp** | **−8.8 pp** |

Under corpus poisoning ParamMute crushes the parametric answer to 4.5 %. Under
false evidence the same inhibition only moves it from 67.6 % to 58.8 %. The
reason is structural: under corpus poisoning the wrong answer has **one**
source, memory, so inhibiting memory removes it. Under false evidence it has
**two**, memory and the planted passage, and ParamMute only touches one of
them. Suppression efficacy falls roughly fivefold because the attack duplicated
the answer into the channel the defense does not operate on.

---

## CK-PLUG: harmful against one payload, flat against the other

Committed prediction: *"same direction as ParamMute, smaller."* Half right.

n=800, mdr 7.0 pp, alpha 0.0.

| dose | corpus poisoning | false evidence |
|---|---:|---:|
| clean | −4.5 (p=0.076) | −4.4 (p=0.085) |
| 10% | **−14.9** (p<0.001) | −4.5 (p=0.031) |
| 50% | **−15.1** (p<0.001) | −4.2 (p=0.014) |
| 100% | **−9.9** (p<0.001) | −4.8 (p<0.001) |

Read the shape, not only the signs. Under corpus poisoning the harm **grows
with the attack**: −4.5 clean, then −14.9 and −15.1 once poison is present.
Under false evidence the harm is a **flat offset** of about −4.4 pp at every
dose including the clean one, and no cell clears the 7.0 pp threshold.

So CK-PLUG pays a constant price for being switched on, and corpus poisoning
amplifies that price while false evidence does not. Excess damage is +5.4 pp
against one payload and +0.4 pp against the other.

---

## COIECD: inert against both, and the firing rate says why

Committed prediction: *"should do nothing at all, more completely than before.
It detects conflict via an information-entropy constraint. False evidence that
agrees with the prior produces no conflict to detect, so the constraint should
fire less, not more."*

n=400, mdr 9.9 pp. Eight comparisons, largest 1.8 pp, no p below 0.20.

| dose | corpus poisoning | false evidence |
|---|---:|---:|
| clean | −0.8 | −0.8 |
| 10% | +0.8 | +0.8 |
| 50% | −0.5 | +1.0 |
| 100% | −1.8 | +0.5 |

COIECD neither helps nor hurts under either payload. It is the one defense in
this cell that does nothing at all.

The accuracy numbers cannot tell "fires and does not help" from "does not
fire". The memorisation rate can. COIECD's mr reduction is −7.9 and −9.4 pp at
10 % and 50 % under corpus poisoning, against −2.5 and −2.8 pp under false
evidence: the constraint pushes measurably away from memory when the planted
passage contradicts the prior, and roughly three times less when it agrees.
**That is the predicted signature.** It is also below threshold, so it is
recorded as directionally consistent and not as a result. Resolving it needs a
larger n or direct instrumentation of the constraint's firing rate.

---

## The falsifier, and why it does not cleanly fire

Committed with the predictions: *"If any of the three does better against false
evidence than against corpus poisoning, then 'these defenses fail because they
trust the context' is not the mechanism."*

CK-PLUG does do better against false evidence: +0.4 pp excess against +5.4 pp.
Taken at face value that triggers the falsifier.

**It should not be taken at face value, because the two payloads are not
equally strong on the undefended arm.** False evidence is roughly twice as
damaging to an undefended model at every dose:

| dose | undefended, corpus poisoning | undefended, false evidence |
|---|---:|---:|
| CK-PLUG 10 % | 39.2 | 23.0 |
| CK-PLUG 100 % | 10.1 | 7.2 |
| COIECD 10 % | 26.5 | 15.2 |
| COIECD 100 % | 3.8 | 1.8 |

Excess damage is a difference of two collapses, and when the undefended arm has
already collapsed there is less room left for the defense to make things worse.
CK-PLUG's smaller excess under false evidence is at least partly a floor
effect, not evidence that the mechanism is wrong.

The honest statement is therefore narrower than the falsifier assumed:
**excess-damage comparisons across payload classes are confounded by attack
strength and should not be read as a ranking.** Within a payload, against its
own undefended arm, every comparison in this document stands.

---

## What this adds to the campaign

**The cheaper attack is the stronger one.** False evidence needs no gradient
access, no optimisation and no surrogate retriever. It is one fluent sentence.
It damages an undefended model about twice as much as the optimised attack the
literature concentrates on. Evaluations built only around optimised payloads
will overstate how well a system holds up.

**"Trusts the context" is too coarse a description of the failure.** All three
defenses shift trust toward the retrieved text, and the three outcomes are
different. ParamMute is harmful against both payloads. CK-PLUG is harmful
against one. COIECD is inert against both. What separates them is what the
defense does to the *parametric* path, and whether the attack has supplied a
second route to the same wrong answer.

**One caveat on the metric, stated because it limits the mechanism claim.**
Under false evidence the planted passage asserts the same string the model
would have recalled, so `pm_acc` cannot distinguish a model that remembered
from a model that copied. The two produce identical output. That is the
attack's design rather than a measurement flaw, and it is why ParamMute's
residual 58.8 % cannot be split into memory and copying. An arm that plants the
*gold* answer instead would separate them, and that is the next run.

---

## Appendix: the alpha-0.5 no-op

The first CK-PLUG run against false evidence was discarded. It took argparse's
default `--alpha 0.5`, and CK-PLUG's fusion rule is

```
logits_adjust = alpha * student + (1 - alpha) * (full - student)
```

which at alpha=0.5 collapses to `0.5 * full`, a uniform scaling of the logits.
Under greedy decoding at `top_k=1` that cannot change the argmax, so the
defended arm was mathematically pinned to the undefended one and matched it to
0.1 pp at every dose. The corpus-poisoning run had used `--alpha 0.0`, the
actual context-reliance setting, and the queue script did not carry the flag
over.

It is recorded here rather than deleted because it is a real and checkable
property of the method: **CK-PLUG at alpha=0.5 is a no-op under greedy
decoding.** Any evaluation of it that reports greedy results at that setting is
reporting the undefended model.

# A defense that reads a good document and drops a poisoned one

**ACD vs corpus poisoning, n=400, Llama-3-8B-Instruct, CoConflictQA.**
Prediction committed in `scripts/acd_vs_corpus_poisoning.py` before the run.

Ninth defense in the RAG x silent-corruption cell, and the first that is
resolvably protective under attack while still using the context when the
context is good.

## Scope, added 2026-10-16 after auditing against Carlini's DeepSec critique

**This is not a robustness result and should never be cited as one.** The
corpus-poisoning passage is Zhong et al.'s released artefact, optimised against
a *retriever*, not against ACD. The run therefore shows that ACD resists one
specific non-adaptive payload and nothing more. Inferring robustness from an
attack that was not built for the defense is the exact error that invalidated
DeepSec's defense rankings (`carlini_audit.md` §1).

An attacker who knows ACD's entropy rule and optimises against it is untested.
We expect such an attacker to do better, because the rule is public and
differentiable.

Two things already bound the claim from the other side. `acd_false_evidence_result.md`
swaps the payload class and the protection disappears entirely, falling below
the no-retrieval floor; `distractor_evidence_result.md` shows that what
resistance remains is ACD falling back on memory rather than reading the real
document. The failure results in both of those are unaffected by this caveat,
since a non-adaptive attack that wins anyway is a lower bound.

## Result

ctx_acc, recall against the gold answer. mdr 9.9 pp at n=400.

| arm | clean | 10 % | 50 % | 100 % | slope |
|---|---:|---:|---:|---:|---:|
| `rag` (defense off) | 66.0 | 43.2 | 24.8 | **1.2** | −64.8 |
| `closedbook` (no document) | 10.0 | 10.0 | 10.0 | 10.0 | 0.0 |
| **`acd` (defense on)** | **63.5** | 40.0 | 28.0 | **10.5** | **−53.0** |

Two comparisons decide what this means.

**Against the undefended arm — is it protective?**

| poison | acd | rag | Δ | Fisher p |
|---:|---:|---:|---:|---:|
| 0 % | 63.5 | 66.0 | −2.5 | 0.51 |
| 10 % | 40.0 | 43.2 | −3.2 | 0.39 |
| 50 % | 28.0 | 24.8 | +3.2 | 0.34 |
| **100 %** | **10.5** | **1.2** | **+9.2** | **<0.0001** |

**Against no retrieval at all — does it actually read the document?**

| poison | acd | closedbook | Δ | Fisher p |
|---:|---:|---:|---:|---:|
| 0 % | 63.5 | 10.0 | **+53.5** | 2.0e-59 |
| 10 % | 40.0 | 10.0 | +30.0 | 2.0e-23 |
| 50 % | 28.0 | 10.0 | +18.0 | 8.0e-11 |
| 100 % | 10.5 | 10.0 | +0.5 | 0.91 |

## What it does

**It slides from the document to the model's own knowledge as the attack grows,
and it does it by itself.** ACD decodes from the no-context distribution and
pulls toward the context in proportion to how much the context *reduces*
uncertainty:

    d_alpha = ent / (ent_pos + ent)
    scores  = scores + d_alpha * (scores_pos - scores)

The parametric-answer rate traces the weight moving: **16.2 → 24.0 → 30.5 →
43.5**, converging on `closedbook`'s 44.8, while `rag`'s stays flat at 4–10.
Nothing was tuned per dose. The poisoned passage raises contextual entropy and
`d_alpha` shrinks on its own.

## The claim, stated precisely

**ACD does not recover the right answer from a poisoned context.** Nothing can;
at 100 % poison the answer is not in the context. What it does is stop the
attack from dragging the model *below what it already knew*.

That floor is the point. At saturation the undefended arm scores **1.2 %** —
far **below** the 10.0 % the model gets with no document at all. A fully
poisoned context is not merely useless, it is **actively destructive**: it
overwrites knowledge the model had. ACD detects that and falls back, restoring
the no-retrieval floor (10.5 %, indistinguishable from closedbook at p = 0.91).

So the honest summary is: **ACD converts an actively harmful context into an
absent one.** That is a smaller claim than "it defends against poisoning" and a
much more defensible one.

## Why this is different from everything else in the cell

| defense | reads a clean document? | survives a poisoned one? |
|---|---|---|
| ParamMute, CK-PLUG | yes | **no — amplifies it** |
| COIECD | yes | inert on accuracy |
| DyPRAG | **no — never** | yes, trivially |
| **ACD** | **yes, +53.5 pp over closedbook** | **yes, +9.2 pp over rag** |

DyPRAG was flat under attack because it never read the document, which the
no-retrieval control exposed. ACD is flat-ish under attack *having first
demonstrated it reads the document*, which is the combination the control was
built to tell apart. It is the only defense here that does both.

It also costs nothing measurable when there is no attack: −2.5 pp on clean
context, p = 0.51.

## The committed prediction

Two-sided, and both sides held:

- *"acd should degrade LESS than rag"* — **confirmed**, −53.0 vs −64.8, and
  resolvably at saturation (p < 0.0001).
- *"the claim only survives if acd sits ABOVE closedbook on clean context,
  otherwise it is DyPRAG again"* — **confirmed**, +53.5 pp at p = 2e-59.

This is the first prediction in the campaign to hold on both the effect and its
control. The mechanism stated in advance - that the attack raises contextual
entropy and the adaptive weight discounts it - is also the one the pm_acc curve
shows, which the DyPRAG run specifically did not manage.

## What it says about the design rule

The campaign's rule is *do not suppress parametric memory*. Every defense that
violated it lost. ACD is the first that **conditionally** suppresses the
opposite direction - it suppresses the *context* when the context looks
unreliable - and it is the first to win.

That sharpens the rule from a prohibition into a direction: the failure is not
weighting context or memory, it is weighting either **unconditionally**.
ParamMute and CK-PLUG move trust toward the context by a fixed amount whatever
the context contains. ACD moves it by an amount the context has to earn. Same
family, opposite outcome, and the difference is a single conditional.

## Limits

- One model, one dataset, one attack. Corpus poisoning plants optimised junk,
  which raises entropy readily. A fluent false-fact attack such as PoisonedRAG
  may read as *confident* evidence and lower entropy instead - that is the
  obvious next test, and the prediction is that ACD does much worse on it.
- The protection at 100 % is a return to the no-retrieval floor, not recovery.
  A reader who takes "+9.2 pp over RAG" without the closedbook column will
  overstate this.
- The resolvable result is at saturation only; 50 % is +3.2 pp and not
  resolvable at n=400.
- Runs on Llama-3-8B-Instruct with ACD's base-model prompt format rather than
  their default base checkpoints, to hold the model fixed across the cell.

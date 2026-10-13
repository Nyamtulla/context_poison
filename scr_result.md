# Asking the model whether the document is lying costs more than it saves

**SCR vs corpus poisoning, n=400, Llama-3-8B-Instruct, CoConflictQA.**
Prediction committed in `scripts/scr_vs_corpus_poisoning.py` before the run.

Tenth defense in the RAG x silent-corruption cell, and the only one whose
design anticipates an adversary. SCR shows the model its own no-context answer,
the document, and the answer the document supports, and asks it to judge
whether the document is deceptive before committing. Their instruction says it
outright: *"evaluate the reliability of the document and determine whether the
document is deceptive or not."*

## Result

ctx_acc, recall against the gold answer. mdr 9.9 pp at n=400.

| arm | clean | 10 % | 50 % | 100 % | slope |
|---|---:|---:|---:|---:|---:|
| `rag` (defense off) | 59.5 | 37.2 | 22.5 | 1.2 | −58.2 |
| `closedbook` (no document) | 4.8 | 4.8 | 4.8 | 4.8 | 0.0 |
| **`scr` (defense on)** | **46.0** | 24.5 | 15.5 | 4.0 | −42.0 |

**Against the undefended arm:**

| poison | scr | rag | Δ | Fisher p |
|---:|---:|---:|---:|---:|
| 0 % | 46.0 | 59.5 | **−13.5** | 0.00017 ✱ |
| 10 % | 24.5 | 37.2 | **−12.8** | 0.00013 ✱ |
| 50 % | 15.5 | 22.5 | **−7.0** | 0.015 ✱ |
| 100 % | 4.0 | 1.2 | **+2.8** | 0.025 ✱ |

**Against no retrieval:**

| poison | scr | closedbook | Δ | Fisher p |
|---:|---:|---:|---:|---:|
| 0 % | 46.0 | 4.8 | +41.2 | 4.4e-45 |
| 100 % | 4.0 | 4.8 | −0.8 | 0.73 |

## What it buys and what it costs

SCR does read the document - 41.2 pp above no-retrieval on clean context - so it
is not DyPRAG. And it does help at saturation, +2.8 pp over the undefended arm,
resolvable at p = 0.025.

**It pays 13.5 points on clean data for that 2.8.** The cost is resolvable at
every dose below saturation and is roughly five times the benefit. A defense
that is deployed permanently and attacked occasionally is a bad trade at this
exchange rate.

The mechanism it shares with ACD is visible in the same place: SCR's
parametric-answer rate climbs 22.8 → 33.8 → 35.8 → 52.5, converging on
closedbook's 55.8. Both defenses slide from the document toward memory as the
attack grows. SCR simply arrives there having destroyed more correct answers on
the way.

## The comparison that matters

ACD ran on the same items, the same attack, the same doses and the same scorer,
differing only in defense:

| | clean cost vs own `rag` | saturation gain vs own `rag` |
|---|---:|---:|
| **ACD** (entropy ratio, 2 lines) | **−2.5** (p = 0.51, not resolvable) | **+9.2** (p < 0.0001) |
| **SCR** (ask the model to judge) | **−13.5** (p = 0.00017) | **+2.8** (p = 0.025) |

**ACD dominates SCR on both axes.** It costs nothing measurable and gains three
times as much.

Absolute levels are NOT comparable between the two runs - the arms use
different prompts, which is why the closedbook floors differ (10.0 for ACD, 4.8
for SCR). The deltas are, because each is measured against its own control in
its own run.

So the sharpest statement this cell supports:

> **The defense that reasons explicitly about deception loses to the one that
> computes a ratio of two entropies.** SCR asks a capable model to decide
> whether it is being lied to; ACD computes `ent / (ent_pos + ent)`. The second
> is better on clean data and better under attack.

## Why the reasoning approach loses

The 13.5-point clean-data cost is the whole story, and it is a cost SCR incurs
when there is no attacker at all. Asking the model to deliberate over a
*correct* document gives it an opportunity to talk itself out of the right
answer, and on 400 items it takes that opportunity often. The entropy rule
cannot do this: when the document lowers uncertainty it is weighted up,
with no deliberation step in which to change its mind.

This is a general caution for the field, not a complaint about one paper.
Defenses that add a reasoning step are evaluated on whether they catch the
attack; this one does, slightly. What the evaluations rarely report is what the
reasoning step costs when there is nothing to catch - and here that cost is
five times the benefit, and resolvable at three doses out of four.

## The committed prediction

- *"SCR should degrade LESS than plain RAG, because the poisoned passage does
  not read like credible evidence and SCR is asked to notice"* -
  **falsified at every dose but saturation.** SCR degrades more, not less, and
  resolvably so. It does notice something, but it also discards correct
  documents.
- *"the claim only survives if SCR sits above closedbook on clean context"* -
  **satisfied** (+41.2 pp), so this is a real defense being measured, not an
  abstention in disguise.

The prediction was right about the control and wrong about the effect, which is
the opposite of the DyPRAG run.

## Limits

- One model, one dataset, one attack. Corpus poisoning plants optimised junk;
  SCR's instruction asks about *deceptive* documents, and junk is not deceptive
  so much as incoherent. A fluent false-evidence attack is the fairer test of
  what SCR was built for, and is the obvious next run.
- SCR's answer is the final line of its reasoning, per their own
  `CoTSituatedFaithfulQAPipeline`. Some of the clean-data loss may be extraction
  failure rather than wrong judgement - a reasoning chain that ends in a
  sentence rather than an answer scores zero either way.
- CR-DPO, the trained half of the paper, is not run here. SCR is the
  inference-only variant.

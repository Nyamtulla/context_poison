# The headline claim, tested: an incidental defense makes things worse under attack

**ParamMute (NeurIPS 2025, `validated_against: incidental`) vs corpus poisoning
(EMNLP 2023, deliberate).** Llama-3-8B-Instruct, CoConflictQA / NaturalQuestions,
**n = 1409**, threshold **5.3 pp**. 2026-10-02.

## The result

| condition | base ctx_acc | ParamMute ctx_acc | Δ | base `mr` | ParamMute `mr` | Δ |
|---|---:|---:|---:|---:|---:|---:|
| **clean (its own task)** | 48.4 % | **57.7 %** | **+9.3 pp** | 30.6 % | **18.1 %** | **−12.4 pp** |
| poisoning, 10 % of context | 29.8 % | 30.0 % | +0.2 pp | 48.0 % | 26.4 % | −21.6 pp |
| poisoning, 50 % of context | 19.9 % | 17.5 % | −2.3 pp | 62.8 % | 30.8 % | −32.0 pp |
| poisoning, 100 % of context | 5.3 % | **1.1 %** | −4.2 pp | 89.8 % | 79.8 % | −10.1 pp |

**The control establishes.** On its own benchmark ParamMute gains **+9.3 pp**
context accuracy and cuts the memorization ratio **−12.4 pp**, both above
threshold, with the mechanism confirmed firing in the log
(`Inhibit strength: 0.0, layers [21–26]`). Unlike the FaithfulRAG attempt,
every number below is readable.

## The finding

**The defense keeps succeeding at its stated goal, and that is precisely the
problem.**

ParamMute exists to reduce reliance on parametric memory. Under attack it does
this *harder* than on clean data — `mr` falls 12.4 pp when the context is
honest, and 21.6 and 32.0 pp when the context is poisoned. It is working
exactly as designed.

Meanwhile its benefit evaporates and inverts: **+9.3 → +0.2 → −2.3 → −4.2 pp.**

Measured end to end:

| | clean | saturated | damage |
|---|---:|---:|---:|
| undefended | 48.4 % | 5.3 % | **−43.1 pp** |
| ParamMute | 57.7 % | 1.1 % | **−56.6 pp** |

**ParamMute takes 13.5 pp more damage than the undefended model** — above
threshold. It starts higher and ends lower. The defense that makes a system
better when context fails by accident makes it *worse* when context is
attacked on purpose.

## Why, mechanically

The mechanism is the vulnerability. ParamMute suppresses the FFN layers
carrying parametric knowledge so the model cannot fall back on what it knows
and must follow the retrieved context. That is the right move when the context
is merely in conflict with stale parametric memory — the incidental case the
paper was built for.

An attacker controlling the context is handed exactly that: a model whose
fallback has been deliberately removed. **"Trust the context more" is a
defense against context being wrong and an amplifier for context being
hostile**, and the two cannot be separated because they are the same
intervention.

Note the base model's own `mr` climbs 30.6 → 89.8 under saturation: the
undefended model increasingly ignores the garbage and answers from memory.
That retreat is a crude but real defense, and ParamMute's job is to prevent it.

## What this establishes for the SoK

This is the first direct test of the project's central claim with a control
that fires. **Work built for context going bad by accident does not merely
fail to transfer to context made bad on purpose — here it is actively
harmful.**

It is one defense, one attack, one dataset, one model, so it is a demonstration
rather than a law. But it is a demonstration of the strong form of the claim,
and it comes with a mechanism that predicts where else to look: every defense
whose strategy is *increase context reliance* inherits it. FaithfulRAG is in
that family and could not be tested on open weights; CK-PLUG, Knowledgeable-R1
and SpARE are too.

## Honest limits

- **Saturation again.** At 10 % and 50 % poisoning the attack's own damage is
  large but the defense difference is below threshold. The inversion is clearest
  at 100 %, which models a saturated corpus rather than one injected passage.
- **ctx_acc at 100 % is near the floor** for both arms (5.3 % and 1.1 %), so the
  −4.2 pp gap sits in a compressed range; the 13.5 pp differential-damage figure
  is the sturdier statement.
- **EM is near zero throughout** on this benchmark because answers are short
  strings inside longer generations; `ctx_acc` (substring) is the paper's own
  headline metric and is what is reported here.
- Scoring, prompts and generation are the authors' code, imported unchanged.

## Reproduce

```bash
python3 scripts/parammute_vs_corpus_poisoning.py --n 1409
```

Raw: `data/registries/parammute_vs_corpus_poisoning.json`.

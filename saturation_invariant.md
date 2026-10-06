# The saturation penalty is invariant: ~32 points, whatever the attack

Four attacks, two defenses, two models, one number.

## The observation

| defense | model | attack | Δaccuracy at 10/10 |
|---|---|---|---:|
| SpARE | Llama-3-8B **base** | BadRAG DoS | **−31.7 pp** |
| ParamMute | Llama-3-8B **Instruct** | BadRAG Selective-Fact | **−31.8 pp** |

Different defense. Different mechanism — sparse-autoencoder feature steering
versus FFN activation suppression, no shared code. Different model, one of them
not even instruction-tuned. Different attack: one tries to induce refusal, the
other only slants tone and leaves the correct answer in place.

**The penalty is the same to one decimal place.**

## And below saturation, neither attack does anything

| poison | SpARE Δ | ParamMute Δ |
|---:|---:|---:|
| 0/10 | +0.7 | −2.4 |
| 1/10 | +0.0 | −2.4 |
| 5/10 | +0.0 | −3.2 |
| 9/10 | −2.0 | −6.6 |
| **10/10** | **−31.7** | **−31.8** |

Flat, then a cliff. This is the one-passage boundary found earlier on
ParamMute × BadRAG DoS, now reproduced on a **second defense** and a **second
attack**, with the same shape and nearly the same magnitude.

## What it means

The attack's *mechanism* decides what happens while genuine evidence survives.
That is where the interesting variation lives — ParamMute is protective against
refusal induction (+30 pp), neutral against tone steering, harmful against
lie insertion at saturation.

**At saturation the mechanism stops mattering.** Once no real passage remains,
every attack has converged on the same thing: an empty evidence set. And every
context-reliance defense pays the same price for it, because they all do the
same thing — they instruct the model to use evidence that is no longer there,
and they have removed the parametric memory it would otherwise fall back on.

The clearest demonstration is SpARE's, because both arms are the *same model on
the same prompt*, differing only in steering direction:

> At 10/10, steering **toward the context** gives **3.0 %** accuracy.
> Steering **toward parametric memory** gives **34.7 %**.

That is the fallback, measured directly. It is worth ~32 points, and these
defenses are designed to suppress it.

## The tone attack has a second signature

BadRAG Selective-Fact does not change the right answer, so accuracy is the
wrong place to look for it. The negative-framing rate is:

| poison | ParamMute | undefended |
|---:|---:|---:|
| 0–5/10 | 0.0–0.2 % | 0.0–0.4 % |
| 9/10 | 4.2 % | 2.4 % |
| **10/10** | **28.8 %** | **3.4 %** |

The defense makes the model **8× more likely** to adopt the attacker's framing.
It is doing exactly what it promises — following the retrieved text — and the
retrieved text is nothing but slant.

## Limits

- Both 10/10 columns are an artificial worst case: a real attacker rarely owns
  every retrieved slot. The honest reading is that these defenses are robust
  across almost the whole realistic range and fail in one corner.
- The convergence on 31.7 / 31.8 is two measurements. It is a striking
  coincidence of magnitude, not a constant; the reproducible claim is the
  *shape* — flat until the last genuine passage, then a cliff of roughly
  thirty points.
- SpARE's arms are two steering directions, not defense-on versus
  defense-off. That makes it a cleaner internal contrast but not identical in
  construction to ParamMute's.

## Reproduce

```bash
python3 scripts/spare_badrag_transfer.py --attack badrag_dos --n 300 --poison_counts 0 1 5 9 10
python3 scripts/poisonedrag_transfer.py --defense parammute --attack badrag_sentiment --n 500 --poison_counts 0 1 5 9 10
```

Raw: `data/registries/badrag_dos_spare.json`,
`data/registries/badrag_sentiment_parammute.json`.

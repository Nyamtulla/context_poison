# Second confirmation: the inversion is a property of the family, not one paper

**CK-PLUG (arXiv 2025, `validated_against: incidental`) vs corpus poisoning.**
Llama-3-8B-Instruct, CoConflictQA / NaturalQuestions, **n = 800**,
threshold **7.0 pp**, greedy decoding, `alpha = 0.0`. 2026-10-03.

## Result

| condition | base ctx | CK-PLUG ctx | Δctx | base `mr` | CK-PLUG `mr` | Δ`mr` |
|---|---:|---:|---:|---:|---:|---:|
| **clean (its own task)** | 60.4 % | 55.9 % | −4.5 pp | 25.1 % | **15.0 %** | **−10.1 pp** |
| poisoning, 10 % | 39.2 % | 24.4 % | **−14.9 pp** | 40.6 % | 22.6 % | **−18.0 pp** |
| poisoning, 50 % | 28.2 % | 13.1 % | **−15.1 pp** | 54.8 % | 27.6 % | **−27.2 pp** |
| poisoning, 100 % | 10.1 % | **0.2 %** | **−9.9 pp** | 81.3 % | 91.3 % | **+10.0 pp** |

Bold clears the 7.0 pp threshold.

## The control fires, and the shape repeats

On clean data CK-PLUG cuts the memorization ratio **−10.1 pp** — above
threshold, its stated function, mechanism confirmed working. The accuracy cost
on clean data is **−4.5 pp and below threshold**: the defense is essentially
free when the context is honest.

Under attack it stops being free. The accuracy deficit becomes **−14.9, −15.1,
−9.9 pp — every one resolvable** — while the mechanism works *harder*,
suppressing memorization by 18.0 and 27.2 pp instead of 10.1.

**At full saturation CK-PLUG reaches 0.2 % accuracy where the undefended model
retains 10.1 %.** The defense drives a degraded system to a totally failed one.

## Why this matters more than the ParamMute result alone

ParamMute suppresses FFN activations. CK-PLUG fuses two logit distributions at
decode time. Different papers, different venues, different layers of the stack,
**no shared code** — and the same inversion:

| | ParamMute | CK-PLUG |
|---|---|---|
| mechanism | FFN activation suppression | parametric/context logit fusion |
| clean-data effect | **+9.3 pp benefit** | −4.5 pp (not resolvable) |
| under attack | −4.2 pp, **13.5 pp more total damage** | **−9.9 to −15.1 pp per condition** |
| memorization under attack | suppressed *harder* (−21.6, −32.0 pp) | suppressed *harder* (−18.0, −27.2 pp) |

One defense doing this is a paper with a problem. Two independent ones, built
on different machinery, is a property of the strategy they share: **increase
reliance on retrieved context at the expense of parametric memory.**

The two differ in exactly one way worth noting. ParamMute *starts higher* on
clean data and ends lower, so its harm shows up as differential damage
(13.5 pp, resolvable). CK-PLUG starts slightly lower and ends near zero, so its
end-to-end differential (−5.4 pp) is **not** resolvable — its harm shows up
per-condition instead. Both are real; they are just measured at different
points, and this document reports each where it is resolvable rather than
picking the framing that looks worse.

## The `mr` inversion at saturation

At 100 % poisoning CK-PLUG's memorization ratio flips sign: **+10.0 pp**, the
only positive Δ`mr` in the table. With contextual accuracy at 0.2 % the ratio is
almost entirely parametric, so this is a floor artefact rather than the defense
suddenly trusting memory. Noted so it is not read as a reversal.

## Two setup errors corrected before any of this was read

**The alpha convention.** Their fork computes
`alpha * parametric + (1-alpha) * context`, so `alpha=1` is pure *memory*.
`eval_NQ.py` defaults to **0.5** — a 50/50 mix that increases memory reliance
relative to plain RAG, the opposite of the context-faithfulness direction the
paper is about. The shipped default tests the wrong thing.

**The decoding.** `ck.py` defaults to `top_k=1` (greedy); `eval_NQ.py`
overrides it to 100. Identical `base_rag` conditions drifted **58–63 %** across
four runs on that setting — more noise than the effect being measured. Restored
the module's own default.

## Reproduce

```bash
python3 scripts/ckplug_vs_corpus_poisoning.py --n 800 --alpha 0.0 --top_k 1
```

Raw: `data/registries/ckplug_vs_corpus_poisoning.json`.

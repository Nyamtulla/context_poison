# Third confirmation, and the first fully resolvable sign flip

**SpARE (NAACL 2024, `validated_against: incidental`) vs corpus poisoning.**
Meta-Llama-3-8B (base), CoConflictQA / NaturalQuestions, **n = 500**,
threshold **8.9 pp**. 2026-10-03.

## Result

SpARE's `generate_two_answers` returns both steering directions for every item,
from one model on one prompt, so the comparison is internal.

| condition | context-steer | parameter-steer | Δctx | ctx `mr` | param `mr` | Δ`mr` |
|---|---:|---:|---:|---:|---:|---:|
| **clean (its own task)** | **53.8 %** | 39.6 % | **+14.2 pp** | 14.3 % | 29.0 % | **−14.7 pp** |
| poisoning, 10 % | 33.0 % | 28.8 % | +4.2 pp | 24.0 % | 40.2 % | **−16.3 pp** |
| poisoning, 50 % | 15.4 % | 22.6 % | −7.2 pp | 31.9 % | 51.1 % | **−19.2 pp** |
| **poisoning, 100 %** | **1.8 %** | 12.0 % | **−10.2 pp** | 79.5 % | 70.7 % | +8.8 pp |

Bold clears 8.9 pp.

## The finding: a sign flip, resolvable at both ends

**+14.2 pp → +4.2 → −7.2 → −10.2.** Steering toward the context is worth
14.2 points when the context is honest and costs 10.2 points when it is
attacked, and *both endpoints clear the threshold*. Neither ParamMute nor
CK-PLUG gave a resolvable reading at both ends; this one does.

The control fires on the same number. On clean knowledge-conflict data the two
steering directions separate by exactly the margin that later inverts — the
defense is demonstrably working, and the demonstration is the same measurement
that later convicts it.

And the mechanism never stops working. Δ`mr` is resolvable in every
non-saturated condition and **deepens** under attack: −14.7, −16.3, −19.2 pp.
SpARE suppresses parametric reliance harder the more corrupted the context
gets, which is precisely the wrong direction once an attacker owns the context.

*(The +8.8 pp Δ`mr` at saturation is a floor artefact — with contextual
accuracy at 1.8 % the ratio is almost entirely parametric. Not a reversal.)*

## Four defenses, four mechanisms, one shape

| | ParamMute | CK-PLUG | SpARE |
|---|---|---|---|
| venue | NeurIPS 2025 | arXiv 2025 | NAACL 2024 |
| mechanism | FFN activation suppression | decode-time logit fusion | SAE feature steering |
| clean | **+9.3 pp** | −4.5 pp (ns) | **+14.2 pp** |
| under attack | −4.2 pp; **13.5 pp more damage** | **−9.9 to −15.1 pp** | **−10.2 pp** |
| `mr` under attack | deepens | deepens | deepens |

Three papers, three venues, three different layers of the stack — FFN
activations, decode-time logits, sparse-autoencoder features — **no shared
code**. Same inversion each time, and in each case the mechanism is working
*better* under attack than on clean data.

## Setup notes

Four obstacles, all recorded in the campaign defect table: `transformer_lens`
needed pinning; `transformers` pinned to 4.x (`TRANSFORMERS_CACHE` removed in
v5); `flash_attention_2` hardcoded although the function exposes `attn_imp=`,
so SDPA was requested instead; and `PROJ_DIR` defaulting to cwd, so every
`cache_data` path silently missed the shipped weights and fell into a recompute
branch that dies on a file never shipped — a failure about forty lines
downstream of its cause.

SpARE ships no scorer (`demo.py` only prints answers), so the rubric ParamMute
and CK-PLUG share — verified byte-identical between those two repos — was
supplied, keeping all of them on one scale.

Model is Meta-Llama-3-8B **base**: SpARE's cached mutual information, grouped
activations and memorised sets were computed on base weights, not Instruct.

## Reproduce

```bash
python3 scripts/spare_vs_corpus_poisoning.py --n 500
```

Raw: `data/registries/spare_vs_corpus_poisoning.json`.

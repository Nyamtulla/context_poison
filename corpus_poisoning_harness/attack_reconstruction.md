# Corpus poisoning reconstructed — the attack works

Zhong et al., *Poisoning Retrieval Corpora by Injecting Adversarial Passages*
(EMNLP 2023). Authors' released code, **unmodified**. Run 2026-09-30/10-01 on
one RTX A6000.

## Result

**One adversarial passage, injected into NQ's 2.68M-passage corpus, is
retrieved for most queries.**

| rank cutoff | queries that retrieve it |
|---|---:|
| **top-1** | **73.55 %** |
| top-5 | 78.27 % |
| **top-20** (the paper's criterion) | **82.33 %** |
| top-100 | 86.82 % |

3,452 NQ test queries. Attack trained on `nq-train`, evaluated in-domain on
`nq`, both against unsupervised Contriever.

The paper's headline claim is **>75 % success with a single passage** against
unsupervised retrievers, measured at top-20. We get **82.3 %**. Reproduced.

## What the passage looks like

Fifty wordpiece tokens with no meaning, which is the point — it is optimized
for embedding similarity, not readability:

> ditch spelling interruption ernie bell wu rmhm schwarz \空ː posse gonna
> hamburgerdrome } which whom most soloists suddenly bells bottoms wi beybau
> com automatically blockmeric diagonal ¢ transcription whomrma stopped
> distinguishedlistic clinical dramas still concerned describe eitherfting
> trend victorian atmospheric predecessors

Best improvement found at iteration 4,819 of 5,000.

## Two metrics that are easy to invert, and were nearly inverted here

**`best_acc` during the attack** is the fraction of queries where the *gold*
passage still outranks the adversarial one. **Lower is better for the
attacker.** It ran 0.992 → **0.147**.

**`Recall@k` from `evaluate_adv.py` is not retrieval recall.** The script
rebuilds `qrels` so the adversarial passages *are* the ground truth
(`adv_qrels = {q: {"adv%d" % s: 1 ...}}`), so Recall@k is the share of queries
that retrieve the attack within rank k. Reading it as ordinary recall would
turn an 82 % attack success into an 82 % "system still works fine".

## Reproduction evidence

Retrieval itself was validated before any attack number was trusted:
**NFCorpus NDCG@10 = 0.3173 against the published Contriever 0.3177** — a
0.0004 gap, on a stack a decade newer than the one the paper used.

## Measured cost

| | |
|---|---|
| attack, 5000 iterations, k=1 | **5.3 h** wall (3.09 s/iteration) |
| VRAM, steady state | **8.3 GB** of 49 GB |
| NQ BEIR baseline (2.68M passages, 54 batches) | ~23 min |
| BEIR downloads | 7.7 GB |

## Why this matters for the SoK

This is the first **deliberate** cause in the silent-corruption cell to be
reconstructed rather than conceded. The RQ6 precedent (RobustRAG, FaithfulRAG)
had to grant attacks their claimed retrieval success; here the retrieval stage
is demonstrated, so a defense result cannot be dismissed as resting on an
assumed attack.

Next: whether defenses built for *incidental* RAG corruption survive it.

# A defense that works, against an attack it cannot see

**Corpus poisoning (Zhong et al., EMNLP 2023) vs RobustRAG (Xiang et al.).**
Both reconstructed from released code and run locally. 2026-10-01.

## In one paragraph

RobustRAG defends retrieval-augmented systems by answering over each retrieved
passage separately and then aggregating, so a single corrupted passage is
outvoted. It was built and validated against PoisonedRAG, which plants a
passage that *asserts a false answer*. We ran it against a different deliberate
attack in the same cell of the taxonomy — corpus poisoning, which plants a
passage that asserts nothing at all and instead *displaces* real passages out
of the retrieved set. **RobustRAG recovers 11.0 pp against the attack it was
built for and provides no measurable benefit against the other one, at any
level we tested.** The reason is structural rather than a matter of tuning: you
cannot aggregate back information that is no longer in the context.

## Results

Natural Questions (`open_nq`), Mistral-7B-Instruct-v0.2, top-k = 10,
**n = 500**, RobustRAG keyword aggregation at its paper defaults.

Verdicts are gated on the **minimum detectable change at n = 500: 8.9 pp**
(α = .05, power = .80). A gap smaller than that is not reported as an effect,
in either direction.

| condition | undefended | + RobustRAG | benefit | verdict |
|---|---:|---:|---:|---|
| clean (no attack) | 60.6 % | 57.2 % | −3.4 pp | no resolvable effect |
| **PoisonedRAG** *(control — its own attack)* | 45.4 % | 56.4 % | **+11.0 pp** | **defense helps** |
| corpus poisoning, insert 1 | 59.4 % | 57.0 % | −2.4 pp | no resolvable effect |
| corpus poisoning, displace 1 | 57.8 % | 55.2 % | −2.6 pp | no resolvable effect |
| corpus poisoning, displace 5 | 54.0 % | 50.2 % | −3.8 pp | no resolvable effect |
| **corpus poisoning, displace 10** | **3.4 %** | **4.6 %** | **+1.2 pp** | **no resolvable effect** |

Attack damage relative to clean: PoisonedRAG **−15.2 pp**, displace-10
**−57.2 pp** — both resolvable. insert-1 (−1.2), displace-1 (−2.8) and
displace-5 (−6.6) are **not**.

## Three findings

### 1. The control reproduces, so the negatives are real negatives

RobustRAG recovers **+11.0 pp** against PoisonedRAG, clearing the 8.9 pp
threshold. The harness demonstrably detects a defense that works. That is what
licenses reading the rest of the column as genuine absence rather than broken
plumbing — the failure mode that produced a whole matrix of false zeros earlier
in this project.

### 2. Zero measurable benefit against corpus poisoning

Across four conditions the benefit runs from **−3.8 pp to +1.2 pp**. Not one
clears the threshold. Including the condition where the attack is devastating:
at displace-10 accuracy falls to **3.4 %**, and the defense moves it to 4.6 %.

### 3. Corpus poisoning's answer-level harm needs saturation

This is the finding that constrains the others, and it cuts against the
attack. The passage is retrieved for **82.3 %** of NQ queries and is the
**top-1** result for 73.6 % — devastating to retrieval. But displacing one of
ten passages produces **no resolvable loss of answer accuracy**. Nine good
passages are still there, and they are enough.

The attack only destroys answers once it owns the whole retrieved set.

## Why — and it is structural

PoisonedRAG injects a *claim*. Corpus poisoning performs a *deletion*.

RobustRAG's isolate-then-aggregate asks, in effect, **"which of these passages
is lying?"** — and answers it well, which is the +11.0 pp. Corpus poisoning
asks a question the architecture has no way to represent: **"what if none of
them are there?"** There is no minority vote to overrule, because the
adversarial passage votes `I don't know` and is abstained away exactly as
designed. The defense works perfectly and protects nothing.

A secondary signal: the benefit is **negative in four of six conditions**
(−2.4 to −3.8 pp). Each is individually below threshold, so none is a result —
but the sign is consistent, and it is the expected utility cost of an
abstention-based defense discarding usable passages. Worth a footnote, not a
claim.

## What this does and does not establish

**It does not test the SoK's headline claim.** RobustRAG is coded
`validated_against: adversarial` — it was built for a deliberate attack. So
this is *deliberate → deliberate* transfer: does a defense built for one attack
survive another in the same cell? The SoK's central question is
*incidental → deliberate*: do the **54 incidental-validated** silent-corruption
defenses survive a deliberate attack. **FaithfulRAG** (`reasoning`,
`incidental`, RAG, silent-corruption) is the test for that, and it has not been
run.

**displace-10 is an artificial worst case.** It repeats *one* adversarial
passage across all ten slots. The real attack generates ten *distinct* k-means
passages, each costing 5.3 h to optimise. Displace-10 models *"the corpus is
saturated"*, not *"one passage was injected"*. Stated plainly because the
−57.2 pp number is the most quotable in this document and the most likely to
be quoted out of its conditions.

**Injection is justified, not conceded.** Prior transfer work in this project
had to grant attacks their claimed retrieval success. Here retrieval was
measured first — 82.3 % top-20 on a 2.68 M-passage corpus — and the retrieval
stack was validated against a published baseline before any attack number was
trusted (NFCorpus NDCG@10 **0.3173** vs the published Contriever **0.3177**).

**One attack, one defense, one dataset, one model.** A single pair is not a
cell result.

## What it means for the SoK

RobustRAG's registry entry records exactly one evaluated pair: PoisonedRAG,
defense wins. That is the shape of nearly the whole RQ4 registry — **163 of 197
matched defenses were tested against exactly one attack**. This run is what
that single cell looks like when a second attack is put in front of it.

The failure is not sloppiness. RobustRAG is a careful, certifiably-robust
defense that does precisely what it claims. The gap is that *"robust to
retrieval corruption"* turns out to mean *"robust to corrupted passages"*, and
an attack that removes passages rather than corrupting them walks straight
past it. **Threat-model-specific defenses carry threat-model-specific
guarantees, and the name on the box is broader than the guarantee inside it.**

## Reproduce

```bash
python3 scripts/corpus_poisoning_vs_robustrag.py --n 500
```

Setup for both trees: `corpus_poisoning_harness/README.md`.
Attack reconstruction: `corpus_poisoning_harness/attack_reconstruction.md`.
Raw results: `data/registries/corpus_poisoning_vs_robustrag.json`.

Cost: attack generation 5.3 h (one passage, 8.3 GB VRAM); this evaluation
~3 h for 12 conditions × 500 items (22 GB VRAM).

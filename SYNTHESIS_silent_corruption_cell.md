# Defenses for accidental context failure are harmful under deliberate attack

**A complete pass over the silent-corruption cell.** Every incidental-validated
defense with public code, run against one reconstructed deliberate attack,
2026-09-30 → 2026-10-03.

---

## 1. The claim this tests

The SoK's central argument is that two literatures study the same failure and
do not talk to each other. The security side studies context corrupted *on
purpose*; the ML/AI side studies context that degrades *on its own*. Both
publish defenses. Nobody had checked whether the second kind survives the
first.

The **silent-corruption** cell — *the answer is wrong and nothing warns you* —
is one of only two places in the taxonomy where both literatures appear. It
holds **54 incidental-validated defenses** and **5 deliberate causes**, three
of which had never had any defense tested against them.

So the question is exact: **does work built for context going bad by accident
survive context made bad on purpose?**

The answer is worse than "no".

---

## 2. Result

Four defenses ran end to end. Three produced a readable verdict.

| | ParamMute | CK-PLUG | SpARE | SHIFT |
|---|---|---|---|---|
| venue | NeurIPS 2025 | arXiv 2025 | NAACL 2024 | arXiv 2026 |
| mechanism | FFN activation suppression | decode-time logit fusion | SAE feature steering | FFN output gating |
| n / threshold | 1409 / 5.3 pp | 800 / 7.0 pp | 500 / 8.9 pp | 150 / 16.2 pp |
| **control** | **fires** | **fires** | **fires** | **does not fire** |
| effect on **clean** data | **+9.3 pp** | −4.5 pp (ns) | **+14.2 pp** | +1.3 pp (ns) |
| effect **under attack** | −4.2 pp; **13.5 pp more total damage** | **−14.9 / −15.1 / −9.9 pp** | **−10.2 pp** | — |
| `mr` under attack | deepens −21.6, −32.0 | deepens −18.0, −27.2 | deepens −16.3, −19.2 | — |

Full per-condition tables are in the four result documents; this is the
summary line of each.

### The shape, in one row each

**ParamMute** +9.3 → +0.2 → −2.3 → −4.2 pp.
**CK-PLUG** −4.5 → −14.9 → −15.1 → −9.9 pp.
**SpARE** +14.2 → +4.2 → −7.2 → −10.2 pp.

Three defenses, three venues, three different layers of the stack — FFN
activations, decode-time logits, sparse-autoencoder features — **no shared
code between them.** Each one helps or costs nothing when the context is
honest, and each becomes a resolvable penalty once an attacker controls it.

---

## 3. The mechanism is the vulnerability

This is not a story about defenses that stop working. **Every one of them
keeps working, and that is the problem.**

All three share a strategy: *increase reliance on retrieved context at the
expense of parametric memory.* Each measures its own success as a fall in the
memorization ratio `mr = pm / (ctx + pm)`.

Under attack, **`mr` falls further than on clean data, in all three**:

| | clean | 10 % poisoned | 50 % poisoned |
|---|---:|---:|---:|
| ParamMute | −12.4 pp | **−21.6 pp** | **−32.0 pp** |
| CK-PLUG | −10.1 pp | **−18.0 pp** | **−27.2 pp** |
| SpARE | −14.7 pp | **−16.3 pp** | **−19.2 pp** |

The defenses suppress the model's fallback *harder* the more corrupted the
context becomes. They are succeeding at their stated objective precisely when
that objective is wrong.

The undefended model shows what is being suppressed. Its own `mr` climbs from
30.6 % to **89.8 %** as poisoning saturates: left alone, the model
increasingly ignores the garbage and answers from memory. That retreat is
crude, unreliable, and **a real defense** — and these techniques exist to
prevent it.

> **"Trust the context more" is a defense against context being wrong and an
> amplifier for context being hostile, and the two cannot be separated because
> they are the same intervention.**

---

## 4. What the attack is, and why the numbers are trustworthy

**Corpus poisoning** (Zhong et al., EMNLP 2023), reconstructed from the
authors' released code, unmodified. One adversarial passage — 50 wordpieces of
gibberish optimised for embedding similarity — injected into NQ's 2.68 M-passage
corpus is retrieved in the **top-20 for 82.3 %** of test queries and ranks
**top-1 for 73.6 %**. The paper claims >75 % at top-20; we get 82.3 %.

Before any attack number was believed, the retrieval stack was validated
against a published baseline: **NFCorpus NDCG@10 = 0.3173 against Contriever's
published 0.3177**, a 0.0004 gap on a stack a decade newer than the paper's.

Three disciplines gate every number above:

1. **The control must fire first.** A defense that cannot reproduce its own
   benefit on its own benchmark yields no transfer verdict. This disqualified
   FaithfulRAG and SHIFT, and it is what makes the other three readable.
2. **Minimum detectable change**, α = .05, power = .80. Anything below
   threshold is reported as "no resolvable effect", never as zero.
3. **The authors' own scorers**, imported unmodified. ParamMute's and
   CK-PLUG's were diffed and `normalize_answer` is byte-identical; SpARE and
   SHIFT ship none, so that same rubric was supplied. **No rubric was altered;
   one was propagated to the repos that lacked any.**

---

## 5. Limits, stated plainly

- **Saturation carries the clearest signal.** At 10 % and 50 % poisoning the
  attack's own damage is often below threshold. The inversion is sharpest at
  100 %, which models a saturated corpus rather than one injected passage.
- **Where each defense is resolvable differs.** ParamMute starts higher on
  clean data and ends lower, so its harm appears as differential damage
  (13.5 pp). CK-PLUG starts lower and ends near zero, so its end-to-end
  differential (−5.4 pp) is *not* resolvable and its harm appears
  per-condition. Each is reported where it is measurable, not where it looks
  worst.
- **Positive Δ`mr` at saturation** (CK-PLUG +10.0, SpARE +8.8) is a floor
  artefact: with contextual accuracy near zero the ratio is almost entirely
  parametric. Not a reversal.
- **One attack, one dataset family, one model per defense.** This is a
  demonstration across three independent defenses, not a law.
- **SHIFT is a null, not a failure.** Its gate is verifiably loaded (64
  trained tensors, layer-0 norm 0.0049) and verifiably active (4 of 5
  generations differ), but the differences are cosmetic. It is evaluated in its
  own paper on MRQA; it was run here on the shared benchmark because
  comparability across the cell was worth more, and this null is the price.

---

## 6. The second finding: most of this cell cannot be run at all

Twelve incidental-validated defenses in this cell have a resolvable public
repo. **Four could be run.** Of the eight that could not, only two are genuine
scope mismatches (one cross-modal, one video). **Five are artefact problems:**

| defense | what was missing |
|---|---|
| FaithfulRAG | headline config silently requires OpenAI JSON mode; the open-weight path is an ablation the paper never reports separately |
| SABER | `prompts/multipath_prompts.yaml` — the three self-evaluation templates that *are* the method — absent from the repo |
| KScope | README states outright the datasets cannot be uploaded |
| COMBO | no released checkpoints; trains two discriminators from silver labels via slurm |
| Knowledgeable-R1 | eval expects a locally-trained RL checkpoint (`global_step_9`); no weights released |

And the four that *did* run needed roughly twenty fixes between them. The
pattern worth reporting is not that setup is hard — it is that **most of these
failures are silent**:

- **Dead `vllm` imports** blocking startup in two repos — the name is imported
  and never used anywhere in the package.
- **An eval script contradicting its own module default**, turning greedy
  decoding into sampling. Identical baseline conditions drifted **58–63 %** —
  more noise than the effect being measured.
- **An undocumented sign convention** where the shipped default tests the
  *opposite* of the paper's direction.
- **A cache path resolved against the caller's cwd**, so the shipped weights
  are silently missed and control falls into a recompute branch that dies on a
  file that was never shipped — about forty lines downstream of the cause.
- **Shipped run scripts whose flags do not match their own modules' CLIs**, so
  the documented end-to-end command cannot run.
- **Code reading the wrong key from its own shipped data file.**

The sharpest illustration: **SABER ships a genuinely good no-GPU smoke test. It
passes. It prints `ALL SMOKE CHECKS PASSED`. The pipeline then fails on the
very next command** — because the test `--help`s four entry points, none of
them in the package where all five of its defects live.

Had the control-fires-first rule not been in place, several of these would
have produced plausible, wrong numbers rather than errors.

---

## 7. What this means for the SoK

RQ5 records **163 of 197 matched defenses tested against exactly one attack**.
This campaign is what one cell of that registry looks like when a second,
independently reconstructed attack is put in front of it.

The result is stronger than the thesis required. The claim was that defenses
for incidental context failure would **not transfer** to deliberate attack.
What three independent defenses show is that they **transfer negatively**:
measured against no defense at all, they make the system worse, and they do it
by working correctly.

The scope of that claim is bounded by the mechanism, which also makes it
predictive. Any defense whose strategy is *increase context reliance* inherits
it. In this cell that is most of them — and FaithfulRAG, Knowledgeable-R1 and
COMBO, none of which could be run, are all in the same family.

---

## Artefacts

| | |
|---|---|
| attack reconstruction | `corpus_poisoning_harness/attack_reconstruction.md` |
| ParamMute | `parammute_transfer_result.md` |
| CK-PLUG | `ckplug_transfer_result.md` |
| SpARE | `spare_transfer_result.md` |
| SHIFT | `shift_transfer_attempt.md` |
| FaithfulRAG | `faithfulrag_transfer_attempt.md` |
| campaign log, defect table, full triage | `CELL_CAMPAIGN.md` |
| raw results | `data/registries/*_vs_corpus_poisoning.json` |

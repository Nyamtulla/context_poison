# Defenses for accidental context failure remove the model's priors — for better and for worse

**A complete pass over the silent-corruption cell.** Every incidental-validated
defense with public code, run against three structurally different deliberate
attacks, 2026-09-30 → 2026-10-05.

> **Revised 2026-10-05.** The first version of this document concluded that
> these defenses are harmful under attack. That was true of the two attacks
> tested at the time and is **too broad**. A third attack reversed the sign,
> and the corrected claim is in §3. The earlier numbers are unchanged; the
> interpretation is narrower.

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

## 3. The mechanism is neither a vulnerability nor a defense — it is a trade

These defenses share one strategy: *suppress reliance on parametric memory so
the model follows retrieved context.* The decisive finding is that **the
model's parametric behaviour contains two things the defense cannot tell
apart**:

- **factual knowledge** — what the model would answer from memory
- **a learned refusal reflex** — the alignment behaviour that declines to answer

Suppressing memory mutes both. Whether that helps depends entirely on **which
of the two the attacker is aiming at.**

| attack | what the payload exploits | ParamMute's effect |
|---|---|---|
| corpus poisoning (removes signal) | the factual fallback | **harmful** — 13.5 pp more total damage |
| PoisonedRAG at saturation (every passage a lie) | the factual fallback | **harmful** — ASR 68.4 % → **88.8 %** |
| **BadRAG DoS (induces refusal)** | **the refusal reflex** | **protective** — refusal 52.4 % → **0.2 %**, accuracy 27.0 % → **57.4 %** |

### Why the harmful cases are harmful

Under corpus poisoning and saturated PoisonedRAG the retrieved context is
unusable. The undefended model notices and retreats to memory: its own
memorization ratio climbs 30.6 % → **89.8 %**, and that retreat still salvages
**32 % accuracy when every passage is a lie.** It is crude, unreliable, and a
real defense. These techniques exist to prevent it.

Consistent with that, `mr` falls *further* under attack than on clean data in
all three defenses — they suppress the fallback harder the more corrupted the
context becomes:

| | clean | 10 % poisoned | 50 % poisoned |
|---|---:|---:|---:|
| ParamMute | −12.4 pp | **−21.6 pp** | **−32.0 pp** |
| CK-PLUG | −10.1 pp | **−18.0 pp** | **−27.2 pp** |
| SpARE | −14.7 pp | **−16.3 pp** | **−19.2 pp** |

### Why the protective case is protective

BadRAG's payload asserts nothing false and removes nothing. It claims the topic
is contested and harmful, and the model's own alignment fires. ParamMute mutes
that reflex along with everything else parametric, so the payload has nothing
to trigger. Same intervention, opposite valence.

> **The honest claim is a design trade, not a verdict: suppressing parametric
> memory costs the model its factual fallback and removes its refusal reflex.
> Attacks that destroy the evidence are amplified. Attacks that weaponise the
> model's own alignment are blunted.**

This predicts where to look next, which the earlier blanket claim did not.

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

## 6b. Second and third attacks: the same defenses, different signs

| | ParamMute | CK-PLUG |
|---|---|---|
| PoisonedRAG, 1–5 poisoned | no resolvable effect | control fails (−22.6 pp clean) |
| PoisonedRAG, 10/10 | **ASR +20.4 pp**, accuracy −26.4 pp | control fails |
| BadRAG DoS | **refusal −52.2 pp, accuracy +30.4 pp** | control fails |

CK-PLUG's control fires on CoConflictQA (−10.1 pp `mr`) and **fails** on
`open_nq` (−22.6 pp accuracy with no attack at all). Same defense, same
settings, two datasets, opposite verdicts on whether it works. That is
reported as a limit on CK-PLUG's generality, not as a transfer result.

Registry status of every cell above: **untested**. RobustRAG is the only
defense in this cell the literature records against PoisonedRAG; ParamMute,
CK-PLUG, SpARE, SHIFT, FaithfulRAG and TCR are recorded against nothing.

## 7. What this means for the SoK

RQ5 records **163 of 197 matched defenses tested against exactly one attack**.
This campaign is what one cell of that registry looks like when a second,
independently reconstructed attack is put in front of it.

The claim was that defenses for incidental context failure would **not
transfer** to deliberate attack. What the experiments show is more specific and
more useful than either "no transfer" or "negative transfer".

**Transfer is not a property of the defense. It is a property of the pair.**
The same intervention, unchanged, is harmful against two attacks and
protective against a third — and which one you get is decided by whether the
attacker targets the model's factual fallback or its refusal reflex.

That is precisely what a registry recording **163 of 197 defenses against
exactly one attack** cannot tell you. A single confirmed pair does not
under-measure a defense; it measures something that does not generalise at
all. Any defense in this family — FaithfulRAG, Knowledgeable-R1, COMBO among
them — inherits the same conditional behaviour, and none of their papers could
have detected it, because each tested one attack.

---

## Artefacts

| | |
|---|---|
| attack reconstruction | `corpus_poisoning_harness/attack_reconstruction.md` |
| ParamMute | `parammute_transfer_result.md` |
| CK-PLUG | `ckplug_transfer_result.md` |
| SpARE | `spare_transfer_result.md` |
| PoisonedRAG (2nd attack) | `data/registries/poisonedrag_*.json` |
| BadRAG DoS (3rd attack) | `badrag_transfer_result.md` |
| SHIFT | `shift_transfer_attempt.md` |
| FaithfulRAG | `faithfulrag_transfer_attempt.md` |
| campaign log, defect table, full triage | `CELL_CAMPAIGN.md` |
| raw results | `data/registries/*_vs_corpus_poisoning.json` |

# A defense that works, an attack it cannot see, and the one line that fixes it

**Corpus poisoning (Zhong et al., EMNLP 2023) vs RobustRAG (Xiang et al.).**
Both reconstructed from released code and run locally. 2026-10-01/02.

## In one paragraph

RobustRAG answers over each retrieved passage separately and aggregates, so a
single corrupted passage is outvoted. It was built against PoisonedRAG, which
plants a passage that *asserts a false answer*. We ran it against a different
deliberate attack in the same taxonomy cell — corpus poisoning, which asserts
nothing and instead *displaces* real passages out of the retrieved set.
**RobustRAG recovers 11.0 pp against its own attack and nothing at all against
the other one.** The reason is structural, and it is visible in the defense's
own code. Keeping the technique and adding one step — refill the evidence set
when passages abstain — **recovers 40.6 pp of a 53 pp hole**, without touching
the aggregation, without tuning, and without knowing the attack exists.

## Results

Natural Questions (`open_nq`), Mistral-7B-Instruct-v0.2, top-k = 10, pool = 30,
**n = 500**. Verdicts gated on the **minimum detectable change at n = 500:
8.9 pp** (α = .05, power = .80). Smaller gaps are not reported as effects.

| condition | undefended | stock RobustRAG | + backfill | backfill − stock |
|---|---:|---:|---:|---:|
| clean (no attack) | 60.6 % | 57.2 % | 57.6 % | +0.4 pp |
| **PoisonedRAG** *(control)* | 45.4 % | **56.4 %** | 57.4 % | +1.0 pp |
| corpus poisoning, displace 1 | 57.8 % | 55.2 % | 55.6 % | +0.4 pp |
| corpus poisoning, displace 5 | 54.0 % | 50.2 % | 52.6 % | +2.4 pp |
| **corpus poisoning, displace 10** | **3.4 %** | **4.6 %** | **45.2 %** | **+40.6 pp** |

Only two cells in the last column clear the threshold in the whole study: the
PoisonedRAG control for stock RobustRAG (**+11.0 pp**), and backfill at
displace-10 (**+40.6 pp**).

## Part 1 — the failure

### The control reproduces, so the negatives are real

RobustRAG recovers **+11.0 pp** against PoisonedRAG, above threshold. The
harness demonstrably detects a working defense, which is what licenses reading
the rest of the column as genuine absence rather than broken plumbing.

### Zero measurable benefit against corpus poisoning

Benefit runs **−3.8 pp to +1.2 pp** across four conditions. None resolvable —
including displace-10, where accuracy falls to **3.4 %** and stock RobustRAG
moves it to 4.6 %.

### Why, from the defense's own source

```python
count_threshold = min(self.absolute, self.relative * len(seperate_responses))
if len(seperate_responses) < abstention_threshold: return "I don't know."
```

PoisonedRAG injects a *claim*: one passage lies, nine tell the truth, the
majority wins. Corpus poisoning performs a *deletion*. Its passage carries no
answer, so it abstains and is correctly discarded — and the real passage it
displaced is simply gone. The evidence set shrinks. Displace all ten and the
defense falls below `abstention_threshold` and returns "I don't know."

**It identifies every passage as useless and then has nothing to aggregate.**
Isolate-then-aggregate asks *"which of these is lying?"* and answers it well.
Corpus poisoning asks *"what if none of them are there?"* — a question the
architecture cannot represent.

## Part 2 — the fix

The technique is not wrong, it is **incomplete**. Isolate-then-aggregate
assumes the retrieved set *is* the evidence. Under displacement the evidence is
still there, just below the cut.

So the core is unchanged and one step is added: **when a passage abstains, pull
the next one from the ranking until the evidence set is full again.** No
knowledge of the attack, no threshold tuning, no new model, no change to the
aggregation.

**displace-10: 4.6 % → 45.2 %, a +40.6 pp recovery.**

Three properties make this a technique result rather than a lucky patch:

- **It refills what it claims to.** `kept/item` holds at **9.0–9.7 of 10**
  across every condition, so the evidence set really is restored.
- **It costs nothing when nothing is wrong.** Clean +0.4 pp, PoisonedRAG
  +1.0 pp — both inside the threshold. It does not break what already worked.
- **Its cost is adaptive.** Probes per item: **17.4** clean → **25.5** at
  displace-10. It pays more only when actually under attack.

### It blunts the attack, it does not neutralise it

At displace-10 the backfilled defense reaches **45.2 %** against a clean
baseline of **57.6 %** — a residual **−12.4 pp**, which *is* above threshold.
The attack still lands.

*(An earlier n=25 pilot put this at 64 %, at or above clean, and was read as
full neutralisation. That was wrong: mdr at n=25 is ~40 pp, so the pilot could
not have supported it. It established the mechanism and nothing more. The
n=500 number is the result.)*

## What this does and does not establish

**It is not the SoK's headline claim.** RobustRAG is coded
`validated_against: adversarial`. This is *deliberate → deliberate* transfer.
The central question is *incidental → deliberate*: whether the **54
incidental-validated** silent-corruption defenses survive an attacker.
**FaithfulRAG** is that test, and it is unrun.

**displace-10 is an artificial worst case.** It repeats *one* adversarial
passage across ten slots; the real attack generates ten *distinct* k-means
passages at 5.3 h each. It models *corpus saturation*, not *one injection*.
Stated plainly because +40.6 pp and −57.2 pp are the most quotable numbers here
and the most likely to escape their conditions.

**At the realistic setting the attack does no resolvable answer damage.**
displace-1 costs 2.8 pp — below threshold — despite the passage being
retrieved for **82.3 %** of queries and ranking **top-1** for 73.6 %. Nine good
passages are enough. Corpus poisoning is devastating to *retrieval* and nearly
harmless to the *answer* until it owns the whole set. The fix therefore matters
for the saturation regime, which is where the attack is dangerous at all.

**Injection is justified, not conceded.** Retrieval success was measured first
on a 2.68 M-passage corpus, and the retrieval stack was validated against a
published baseline before any attack number was trusted (NFCorpus NDCG@10
**0.3173** vs published Contriever **0.3177**).

**One attack, one defense, one dataset, one model.**

## What it means for the SoK

RobustRAG's registry entry records exactly one evaluated pair: PoisonedRAG,
defense wins. That is the shape of the registry — **163 of 197 matched defenses
were tested against exactly one attack**. This is what one of those cells looks
like when a second attack is put in front of it.

The failure is not sloppiness. RobustRAG is a careful, certifiably-robust
defense that does exactly what it claims. The gap is that *"robust to retrieval
corruption"* turns out to mean *"robust to corrupted passages"*, and an attack
that **removes** passages rather than corrupting them walks straight past it.

And the fix generalises past this one defense. **Every isolate-then-aggregate
defense in the registry inherits the same blind spot**, because they all treat
the retrieved set as the evidence set. The check is one question: *what does
this defense do when the passages it discards are the only ones it had?*

## Reproduce

```bash
python3 scripts/corpus_poisoning_vs_robustrag.py --n 500   # stock
python3 scripts/robustrag_backfill.py --n 500              # adapted
```

Setup: `corpus_poisoning_harness/README.md`.
Attack reconstruction: `corpus_poisoning_harness/attack_reconstruction.md`.
Raw: `data/registries/corpus_poisoning_vs_robustrag.json`,
`data/registries/robustrag_backfill.json`.

Cost: attack generation 5.3 h (one passage, 8.3 GB VRAM); stock evaluation ~3 h
(12 conditions); backfill evaluation ~5 h (5 conditions, 26 GB VRAM).

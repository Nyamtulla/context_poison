# Pre-registration: the retrieval cell, rebuilt under the attacks' own protocol

Written before any defense is ported and before any run. Committed first, as
the run predictions have been throughout this project.

## Why the rebuild

The campaign has two dosing protocols and the headline results use the one we
invented.

**Native, 42 registries.** Take an item's top-k retrieved passages and replace
*j* of them with the attacker's passage. This is PoisonedRAG's, BadRAG's and
RobustRAG's own protocol, and it is what our PoisonedRAG and BadRAG runs use.

**Invented, 33 registries.** Cut the context into 20-word chunks and replace a
fraction of them. Every corpus-poisoning headline came from this: ParamMute
-4.2, CK-PLUG -9.9, SpARE -10.2, ACD +9.2, SCR, COIECD, DyPRAG, FaithfulRAG.

It exists because CoConflictQA gives one context passage per item, so there is
no top-k to dose, and we needed the defenses on their own benchmark while the
attack needs retrieval. The fix is to stop making CoConflictQA do two jobs:
it is each defense's **control** (does the method reproduce its published
benefit on its own data), and open NQ with a real pool is the **transfer
test**, dosed the way the attack papers dose.

## The design

| | |
|---|---|
| items | open Natural Questions with the RobustRAG authors' retrieval pool |
| retrieval | top-k = 10, plus a k = 20 arm for the low band |
| doses | j = 0, 1, 2, 3, 5, 10 of 10; at k = 20, j = 1, 2, 3 (5/10/15%) |
| arms | undefended, defended, no-retrieval, every cell |
| payloads | corpus poisoning, PoisonedRAG, BadRAG tone, BadRAG refusal |
| n | 500 per cell |
| decoding | greedy, as everywhere else |

DyPRAG's multi-passage handling is **not ours to choose**. Its released
`test.py` computes one delta per passage, averages them, injects once and
generates with the passages removed. We reproduce that.

## Predictions

**The headline, and the one most able to fail.** At one poisoned passage in
ten - a realistic dose - no safety-regime defense shows a resolvable benefit,
and RobustRAG does. We already see RobustRAG at +9.3 and +6.3 at j=1 and j=5
under the native protocol, against ParamMute -4.0, CK-PLUG -26.4 and SpARE
-19.3. If a safety-regime defense comes out resolvably positive at j=1, the
paper's central claim is in trouble and we say so.

**Per defense.**

- **ParamMute, CK-PLUG, SpARE** - already native. Harm persists and is LARGER
  than the chunk protocol showed. Falsified if any lands within its mdr of
  zero across the dose range.
- **ACD** - *the one we expect to lose.* Its +9.2 came entirely from the
  invented protocol and sits under that run's 9.9pp threshold. We predict ACD
  shows **no resolvable benefit** natively. If it replicates at or above
  threshold, the invented protocol was not the reason and we were wrong about
  it.
- **COIECD** - inert on accuracy natively too, and the abstention conversion
  survives. The accuracy prediction is the testable half.
- **SCR** - the clean-context cost persists. Whether the saturation benefit
  replicates we do not predict; it was +2.8 against a 9.9 threshold, which is
  not a result either way.
- **DyPRAG** - flat and statistically indistinguishable from the closed-book
  arm, because it is not reading the passages. Falsified if it separates from
  closed-book at any dose.
- **RobustRAG** - protective at low dose, collapsing as the honest minority
  shrinks, and still blind to corpus poisoning until the window is backfilled.

**What we will not claim.** These runs measure what a generator does with
poisoned context, not how hard a retriever is to poison. We plant passages
into the retrieved set; we do not attack the retriever.

## What is kept, and what is thrown away

Code, payloads and item sets carry over. **No number does.** Every retrieval
result in the paper is regenerated, and the CoConflictQA chunk runs are
relabelled as what they are - a severity sweep on each defense's own
benchmark - rather than cited as attack doses.

## Cost

~198,000 scored episodes at a measured ~5,800 per GPU-hour, and
contrastive-decoding defenses run at about half that. Four to seven days of
continuous A6000 time.

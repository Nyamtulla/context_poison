# Does it take an adversary? A pre-registration

Committed before any of these runs executed.

## Why this test exists

The paper separates its corpus into two regimes. In the **security** regime an
adversary places the bad text on purpose. In the **safety** regime the text is
wrong on its own: stale, superseded, or simply the wrong document returned by
retrieval. The whole framing — two communities, one failure, a citation gap
that is an error rather than a difference of subject — rests on a claim we have
so far argued only from citation patterns:

> The harm an adversary causes and the harm an ordinary wrong document causes
> are the same harm.

That is an empirical claim and nobody has measured it, us included. If an
optimised attack does far more damage than an ordinary wrong document at the
same dose, the two literatures are studying different phenomena, the citation
gap is defensible, and safety-regime defenses are legitimately out of scope for
adversarial settings. If the damage is comparable, the split is a sociological
artifact and the defenses in one regime are being evaluated against a stimulus
near-equivalent to the other regime's.

Either answer changes what the paper claims. That is why it is worth running.

## The design

Four payload conditions crossed over the taxonomy's own two mechanisms, plus
one reference arm. Same 413 items, same dose grid, same position, same scorers.

| | inserts the lie X | asserts nothing, displaces signal |
|---|---|---|
| **adversarial** | A2 `poisonedrag` | A5 `corpus_poisoning` |
| **incidental** | A3 `incidental_stale` | A4 `incidental_misretrieval` |

Plus **A1** — `poisonedrag` in its published construction, the payload repeated
five times per occupied slot. A1 is the reference point: it is what the attack
paper actually does and what every number in §8 was produced against.

**The repetition confound is why A1 and A2 are separate arms.** PoisonedRAG's
own construction repeats its passage five times inside each slot it takes. An
ordinary stale document does not repeat itself. Comparing A1 against A3 would
therefore confound adversarial craft with sheer volume, and the comparison
would be worthless. A2 is PoisonedRAG's passage placed **once**, so:

- **A2 vs A3** isolates craft, with the lie, the dose, the position and the
  repetition all held fixed. This is the actual test.
- **A1 vs A2** isolates repetition, and prices what the published construction
  buys over a single placement.

### Holding the claim constant

A3 asserts **the same false answer X** that PoisonedRAG targets, taken from the
item's own `incorrect answer` field. The construction takes one of the item's
genuinely retrieved passages and replaces each occurrence of the gold answer
with X. Nothing is added, no instruction appears, the register is the corpus's
own, and the passage is placed once.

So A2 and A3 differ in exactly one respect: whether the sentence asserting X
was written to be believed, or is ordinary prose that happens to be wrong.
`attacked` is computed identically for both, so the comparison needs no new
rubric.

### The two incidental conditions

- **A3 `incidental_stale`** — simulates a superseded document. We author the
  substitution, which is a construct-validity cost stated plainly below.
- **A4 `incidental_misretrieval`** — a real, **unmodified** passage retrieved
  for a different question in the same corpus, checked not to contain this
  item's gold answer. Nothing is fabricated and nobody authored anything. This
  is the cleanest no-adversary-anywhere condition available, and it tests
  signal removal rather than lie insertion.

### Fixed across all arms

- 403 items. An item qualifies when its top-10 retrieved passages contain a
  gold answer string, so the A3 substitution is possible, AND both incidental
  payloads survive a contamination check: the A3 passage must no longer state
  any gold form, and the A4 passage must state neither a gold form nor X. 413
  items reach the first bar and 403 clear all of them. All arms run on this
  same subset so the comparison is exact rather than post-hoc. mdr 9.87pp.
- Doses 0, 1, 2, 3, 5, 10 of top-10, backward order (A5 keeps its own forward
  displacement, noted below).
- Llama-3-8B-Instruct, undefended, plus one closed-book arm.
- `acc_score` unchanged — substring containment after normalisation.

## Predictions

1. **A3 lands within 15pp of A2 at every dose.** An ordinary wrong document is
   nearly as effective as a crafted one once repetition is controlled, because
   the model has no channel through which to tell authored-to-persuade prose
   from prose that is merely wrong.
2. **A1 exceeds A2 by 10–20pp.** A substantial part of PoisonedRAG's measured
   strength is volume, not craft.
3. **A4 lowers accuracy but produces near-zero adoption of X**, because nothing
   in it asserts X. Its accuracy damage is comparable to A5's.
4. **Closed-book overtakes every poisoned arm at some dose**, and the crossover
   dose is lower for the two insert-the-lie arms than for the two
   displace-signal arms.

## Falsification

- Prediction 1 fails if A2 exceeds A3 by more than 20pp at every poisoned dose.
  Adversarial craft would then carry real weight on its own, the regime split
  would be justified on mechanism rather than on community, and **the paper's
  unification claim must be narrowed to the displacement mechanism only**.
- Prediction 2 fails if A1 and A2 sit within each other's mdr. The published
  construction's repetition would then be doing nothing, and §8's numbers would
  not need the repetition caveat.
- Prediction 3 fails if A4 produces X at a rate above its mdr, which would mean
  the scorer is catching something other than payload adoption.

## What each outcome licenses

| result | what the paper may then claim |
|---|---|
| A3 ≈ A2 | The regimes share a failure. The citation gap is an error, and a defense validated only against incidental corruption has been validated against a near-equivalent of the adversarial stimulus. |
| A3 ≪ A2 | The regimes are mechanically distinct. Safety defenses are legitimately out of scope under attack, and the SoK's contribution is the map, not a unification. |
| A3 ≈ A2 only at high dose | The regimes converge under saturation. The claim becomes dose-conditional and the crossover dose is the result. |

## Stated weaknesses

- **A3 is authored by us.** It simulates staleness rather than sampling it. The
  defense is that what makes a payload incidental is the absence of
  optimisation against the model or the retriever, not the identity of whoever
  typed it — and A4, which we do not author at all, is the control for exactly
  this objection. If A3 and A4 disagree about whether an adversary is needed,
  A4 is the one to believe.
- **A5 keeps its own forward displacement** while A1–A4 are placed backward.
  Position is therefore confounded with mechanism in the adversarial half of
  the displacement column. We keep their construction rather than correct it,
  because running the attack as its authors run it is the project's standard;
  the comparison to read is A4 vs A5 on accuracy only, and it is weaker for it.
- **A3 is slightly less fluent than A2.** Substituting a noun phrase into real
  prose can leave a seam ("took about a 10-year period to complete"), while the
  crafted passage is written to read well. This biases the test **against**
  prediction 1: if A3 matches A2 despite the seam, craft is worth even less
  than the gap suggests; if A3 falls short, craft and grammaticality cannot be
  fully separated and we will say so rather than claim the stronger reading.
  Mean context length at dose 3 is 1888 / 1984 / 2006 characters for A2 / A3 /
  A4, so payload size is not a confound even though fluency is. A1 is 4114.
- **Undefended model only.** This measures whether an adversary is needed to
  cause the harm, which is a question about payloads. Whether defenses
  discriminate between the two regimes is the obvious follow-up and is not
  tested here.
- 413 items gives a smaller mdr than the 500-item grid cells. Reported with
  each run rather than assumed.

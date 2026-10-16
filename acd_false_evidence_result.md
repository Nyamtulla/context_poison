# The same defense, two attacks: ACD wins against junk and loses against fluent lies

**ACD vs false evidence, n=400, Llama-3-8B-Instruct, CoConflictQA.**
Prediction committed in `4017824`, before the run.

`acd_result.md` reports ACD beating corpus poisoning: +9.2 pp over the
undefended arm at saturation, p < 0.0001, while still reading a clean document
(+53.5 pp over no-retrieval). That was the campaign's strongest defensive
result, though against a non-adaptive payload only (see `acd_result.md`
Scope). This run
asks whether it survives a different payload.

Everything is held fixed except what gets planted — same 400 items, same
chunk-replacement dosing, same arms, same scorer, same model.

| | corpus poisoning | false evidence |
|---|---|---|
| payload | the attack's optimised token sequence | *"According to IMDB, Season 4 of Chicago Fire (2014-2015) consists of 22 episodes"* |
| reads like | incoherent junk | a credible citation |
| relation to the model's prior | unrelated | **asserts the model's own wrong answer** |

The second is the adversarial worst case for ACD's rule specifically. ACD
decodes from the no-context distribution and moves toward the context in
proportion to how much the context *reduces* uncertainty. Junk raises entropy
and gets discounted. Fluent evidence that **agrees with what the model already
believes** lowers entropy, so the weight moves the other way.

## Result

ctx_acc, recall against the gold answer. mdr 9.9 pp at n=400.

| arm | clean | 10 % | 50 % | 100 % |
|---|---:|---:|---:|---:|
| `rag` | 66.0 | 28.2 | 15.5 | 3.0 |
| `closedbook` | 10.0 | 10.0 | 10.0 | 10.0 |
| **`acd`** | **63.5** | 27.2 | 18.2 | **6.0** |

**The protection collapses.**

| | corpus poisoning | false evidence |
|---|---|---|
| acd vs rag at 100 % | **+9.2 pp**, p < 0.0001 ✱ | +3.0 pp, p = 0.059 |
| acd vs closedbook at 100 % | +0.5 pp, p = 0.91 *(at the floor)* | **−4.0 pp, p = 0.0499 ✱** *(below it)* |

Against junk, ACD restored the no-retrieval floor exactly. Against fluent
evidence it ends up **resolvably below** the floor: the defended model does
worse than a model given no document at all.

## The mechanism, confirmed by the arm that was supposed to show it

The parametric-answer rate is where ACD's weight becomes visible. Under false
evidence the planted passage asserts the model's own prior, so a high `pm_acc`
means the attack has landed.

| | 10 % | 50 % | 100 % |
|---|---:|---:|---:|
| `rag` pm_acc | 46.2 | 54.5 | 65.0 |
| **`acd` pm_acc** | **57.5** | **65.2** | **69.8** |
| `closedbook` pm_acc | 44.8 | 44.8 | 44.8 |

**ACD adopts the planted answer more readily than no defense at all**, at every
dose. And both arms sit far above closedbook's 44.8, so the poison is not
merely confirming the prior — it is *amplifying* it past what the model would
say unaided.

That is precisely the predicted failure path: agreement lowers `ent_pos`,
`d_alpha` rises, the context is weighted up, and the context is the attack. The
defense's own mechanism is the vulnerability.

## The attack is also simply stronger

At 10 % poison the undefended arm scores 28.2 under false evidence against 43.2
under corpus poisoning — a 15-point difference at the same dose, before any
defense is involved. A short, fluent, citation-bearing sentence does more
damage than a long optimised token sequence, and it does it earlier in the dose
curve. Worth separating from the defense story: the two attacks are not
equally hard.

## What this does to the ACD result

`acd_result.md` stands as written — it is scoped to corpus poisoning and says
so — but the generalisation it invites does not.

> **Wrong:** ACD defends against context poisoning.
> **Right:** ACD defends against context that *looks unreliable to the model*.

Those coincide only when the attacker is clumsy. Corpus poisoning plants
optimised nonsense; it is detectable by entropy because it is incoherent, not
because it is adversarial. Any attacker who writes a fluent sentence gets past
the gate — and if the sentence happens to agree with the model's priors, the
gate opens *wider* than if no defense were present.

This is a design-level property, not an implementation bug, and it is inherited
by **any defense keyed on model uncertainty**. A confidence signal cannot
distinguish "this document is right" from "this document agrees with what I
already thought". The campaign has now measured that distinction costing a
defense its entire benefit.

## The committed prediction

| predicted | outcome |
|---|---|
| protection collapses, may reverse into harm | **confirmed** — +9.2 → +3.0 and no longer resolvable; reverses relative to the no-retrieval floor (−4.0, p = 0.0499) |
| pm_acc rises steeply for both arms | **confirmed** — rag 9.0 → 65.0, acd 16.2 → 69.8 |
| mechanism: agreement lowers ent_pos, d_alpha rises, acd trusts the context more | **confirmed** — acd's pm_acc exceeds rag's at every dose |
| acd should sit **at or below rag** at every dose | **wrong** — acd stays slightly above rag (+2.8, +3.0), just not resolvably. ACD is not *harmful relative to the undefended arm*; it simply stops helping. |

The falsifier stated in advance — *"if ACD still wins here, the entropy story is
wrong and the corpus-poisoning result was luck"* — did not trigger. ACD does not
win, and the entropy story survives as the explanation of both runs.

## Provenance note

The first attempt at this run returned numbers identical to the
corpus-poisoning run to one decimal, because the `--attack` flag applied to the
output label but not the payload. It produced a complete, plausible file
recording `attack: "false_evidence"` from a run that planted the
corpus-poisoning passage. It was discarded, and the runner now fingerprints the
text it actually plants (`payload_fingerprint: 3649862167a5310c`), prints it at
startup, stores it in the output, and asserts a false-evidence run is not
planting the other payload. The numbers above carry that fingerprint.

## Limits

- One model, one dataset. The payload asserts the model's *own* prior answer,
  which is the hardest case for an entropy gate but not the only form of
  PoisonedRAG. A fluent passage asserting an answer the model does **not**
  already hold would raise entropy and may behave differently - worth running.
- The `closedbook` floor is 10.0 in both runs by construction (it never sees a
  document), which is what makes the two runs directly comparable.
- `acd` vs `rag` at 100 % is p = 0.059: the residual +3.0 pp is not resolvable
  and should not be reported as a small benefit.

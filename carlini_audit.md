# Auditing our design against Carlini's critique of DeepSec

**Source:** Nicholas Carlini, *A critique of the DeepSec Platform for Security
Analysis of Deep Learning Models*, arXiv:1905.07112, May 2019. Full text read
2026-10-16.

DeepSec (Ling et al., IEEE S&P 2019) is the closest structural precedent for
what this project is becoming: a uniform platform that runs many attacks
against many defenses and reports a comparative table. It was taken apart in
public. Before we claim platform status we should know exactly which of its
errors we repeat.

Carlini's conclusion is the sentence to keep in view:

> "Improperly-performed experiments are worse than experiments not performed
> when published as authoritative results."

## Scorecard

| # | Carlini's criticism | Us |
|---|---|---|
| 1 | Attacks are oblivious to the defense | **Addressed** for ACD (adaptive attack run); conservative elsewhere |
| 2 | Averages computed across different threat models | **Pass** |
| 3 | Permitted distortion too large to be meaningful | **Addressed** (10% dose now leads) |
| 4 | Defenses evaluated outside their stated threat model | **Pass, and it is our thesis** |
| 5 | Defended and undefended rates on different item sets | **Pass, verified** |
| 6 | More attacker power yields a worse attack | **Pass, verified** |
| 7 | Robustness reported as an average, not worst case | **Addressed** (worst payload per defense) |
| 8 | Attacks reimplemented incorrectly | **Pass** |
| 9 | Defense reimplemented incorrectly | **Pass, and we detect it** |
| 10 | No error bars, no variance reported | **Addressed** (3 replicates, byte-identical) |

---

## 1. Oblivious attacks — the one that bites

> "A security defense can only be meaningfully evaluated by measuring the
> effectiveness of attacks crafted against it... DeepSec in effect performs a
> non-adaptive, black-box, zero-query, and transfer-only attack analysis."

**We do this.** Corpus poisoning uses Zhong et al.'s released passage,
optimised against a retriever and against no defense of ours. False evidence
and distractor evidence are not optimised at all. No attack we run is adapted
to the defense it meets. By Carlini's description our analysis is non-adaptive
and transfer-only, exactly as DeepSec's was.

**The asymmetry that saves most of it.** DeepSec used weak attacks and
concluded defenses were robust. That inference is invalid: a weak attack
failing says nothing. We use non-adaptive attacks and mostly conclude defenses
**fail**. That inference is sound in the opposite direction, because a
non-adaptive attack that already defeats a defense is a **lower bound** on
attack strength. If the cheapest payload wins, an adapted one also wins.

So: **every "this defense fails" result survives the critique.** It is
conservative by construction.

**The claim that does not survive.** ACD resisting corpus poisoning is a
robustness claim drawn from a non-adaptive attack, which is precisely DeepSec's
error. We partly corrected ourselves already by adding false evidence, which
broke it. But the corpus-poisoning result as stated is not safe.

**Action.** Either run an adaptive attack against ACD, or downgrade the claim
to its literal scope: *ACD resists this specific non-adaptive optimised
passage*, with the obliviousness stated in the sentence that makes the claim.
We must not write "ACD is robust."

**Done 2026-10-16, by downgrading rather than by running an adaptive attack.**
The scope now appears *before* the result in §8 of the paper, not after it,
and cites Carlini directly. "The best result in our campaign" became "the
strongest defensive result," which is a statement about our measurements rather
than about the defense. The abstract says the attacks are not adapted and that
this makes failures lower bounds and resistances provisional. `acd_result.md`
carries a Scope section saying the result must never be cited as robustness.

**The adaptive attack was then run** (2026-10-16, `adaptive_acd_result.md`).
A white-box best-of-K search minimising ACD's own `ent_pos` removes 29 % of its
protection and lands its accuracy on the undefended arm. All six predictions
committed beforehand held, including the ceiling derived from the rule: ACD
does not fall below undefended RAG, because `d_alpha` is bounded in (0,1).

So this criticism moves from **exposed** to **addressed**: our one robustness
claim has now met an adaptive attacker, the claim is scoped to what that
attacker left standing, and the remaining gap is named rather than hidden.
Best-of-K over five templates is the cheapest adaptive attack that exists;
a gradient search on `ent_pos` is still the proper version and is still
undone.

---

## 2. Averages across threat models — pass

> "The DeepSec report computes the mean over different threat models, which
> gives a number that is completely uninformative."

We report every result per (defense, attack, dose) cell. We never average a
defense's performance across payload classes.

We came close once and caught it: the excess-damage comparison across payload
classes is already labelled in §8 as **confounded by attack strength and not to
be read as a ranking**, because the undefended arms differ between payloads.
That is the same error Carlini names, refused before publication.

The one average in the paper, "the undefended model averages 25.8\% and
ParamMute averages 57.6\%," is over a **dose range within a single threat
model** (one to five poisoned passages, BadRAG denial-of-service), and says so.
Legitimate.

---

## 3. Distortion budget too large — partial

> "These extreme distortions would allow any image to be converted to solid
> grey... contradicting the purpose of ℓp threat models."

Our analogue is the saturation dose, `frac=1.0`, where every chunk of the
context is replaced and the real document is gone entirely.

It is not vacuous the way ε=0.6 is: the model can still answer from memory, so
the three-way split still carries information. But **at saturation no method
can read the real document, because it is not there.** Penalising a defense for
low gold accuracy at that dose partly penalises it for the attack being
complete, not for the defense failing.

Two things already protect us. Excess damage is a **difference against the
undefended arm in the same run**, so the attack's completeness cancels. And we
report the full dose curve, 0 / 10 / 50 / 100 %, not only the corner.

**Action.** Stop leading with saturation. The 10 % dose is the stronger and
more defensible number, because the real document is still mostly present and
the defense still fails. CK-PLUG copying 76.7 % against its undefended arm's
38.5 % **on one tenth of the context replaced** is a better headline than
anything at saturation. Promote the low-dose results; keep saturation as the
limit case it is.

---

## 4. Evaluating outside the stated threat model — pass, and it is the thesis

> "When defenses are evaluated under different threat models than originally
> stated, this fact should be stated explicitly."

This is the whole paper. We deliberately run incidental-validated methods
against adversarial attacks. Carlini does not forbid it; he requires it be
declared. Every defense in the registry carries `validated_against`
(adversarial / incidental / both), it is stated per experiment, and the
sentence that motivates each run names the mismatch.

This is the one place where our design is not merely compliant but is
*answering* his complaint as a research question.

---

## 5. Different item sets — pass, verified

> "DeepSec does not evaluate defenses on all the relevant examples, but only on
> those that fool the baseline model... These numbers are fundamentally
> incomparable."

**Checked mechanically across every result registry: 0 runs where two arms at
the same dose scored a different number of items.** Both arms iterate the same
`data` list in the same order. We never filter to items that defeated the
baseline.

---

## 6. Monotonicity anomalies — pass, verified

> "When given strictly more power, the adversary should never do worse.
> However, Table VII reports that an MNIST attacker is less likely to succeed
> with large permitted ℓ∞ perturbation of at most 0.6 compared to 0.2."

**Checked across all 92 dose curves in the registries: 0 violations**, using a
5 pp slack for noise. Accuracy never rises materially as the attack
strengthens. Worth keeping as a standing assertion in the harness rather than
a one-off check.

---

## 7. Average rather than worst case — partial

> "A key factor differentiating security from general fault tolerance is the
> requirement for worst-case analysis."

We never aggregate a defense's robustness across attacks, so we do not commit
the error directly. But we also do not systematically report the **minimum**
over attacks per defense, which is what a security claim needs.

In practice we have been moving toward it: adding false evidence and then
distractor evidence to defenses already measured on corpus poisoning *is* the
worst-case search, and it is what broke ACD.

**Action.** Make it explicit. For every defense, report the worst payload it
has met, and say how many payloads it has met — a defense beaten by 1 of 3
payloads is not 67 % robust, it is broken.

---

## 8 and 9. Implementation correctness — pass, and we have a detector

> "Of the 4 attacks and 1 defense implementations in DeepSec that we studied,
> all had at least one significant flaw... after reproducing prior work, it is
> critical to compare to existing implementations."

DeepSec reimplemented everything and got it wrong. **We do not reimplement.**
We run each author's released code and released weights, import their scorers
unchanged, and use the attack's own released passage. Where we had to stub
something (a dead `vllm` import in CK-PLUG, a dead import in FaithfulRAG) it is
documented at the call site.

We also have something DeepSec lacked: the **control-fires-first rule**. A
defense that cannot reproduce its own published benefit on clean data yields no
verdict. That is an automated version of the check Carlini had to run by hand,
and it has fired: FaithfulRAG produced no measurable benefit on its own
benchmark and we reported the attempt instead of a number.

This is our strongest position relative to DeepSec and should be stated in the
methodology section, not buried.

---

## 10. Variance — partial, and the weakest technical point

> "When we run the authors' FGSM attack implementation 16 times we observe an
> attack success rate... with a mean of 32.7% and standard deviation of 6.8%.
> Such high variance would make many pairwise comparisons not be statistically
> significant."

What we have:

- **Greedy decoding throughout.** `call_llama` uses HuggingFace `generate`
  with sampling off; ACD, SCR, SHIFT and FaithfulRAG pass `do_sample=False`;
  CK-PLUG runs at `top_k=1`. We found and fixed a case where their own
  `eval_NQ.py` forced `top_k=100`, which made identical base conditions drift
  58–63 % across four runs. ParamMute's stochastic path
  (`run_vllm_infer`, `temperature=1.0, top_p=0.9`) is **not** the path we call.
  Determinism is stronger than error bars: a rerun reproduces exactly.
- **Wilson intervals** on every accuracy.
- **A detectability threshold** (minimum detectable change at α=.05,
  power=.80) that a delta must clear before we read it.

What we do not have:

- **No multi-seed study.** Determinism removes sampling noise but not
  sensitivity to item order, batch composition, or the few-shot examples ACD
  holds out. We have never measured that.
- **No published rerun.** We assert determinism; we have not demonstrated it.

**Done 2026-10-17.** Reran COIECD x distractor evidence, n=400, three times
from scratch with an identical command. **Byte-identical**: 72 numeric cells
across 8 result rows, zero differences, same hash after removing the
timestamp. Recorded in `data/registries/variance_replicates_coiecd.json` and
written into the threats section.

So the claim is now demonstrated rather than asserted, and it is stronger than
error bars would have been: over a deterministic decoder those are zero-width.
What remains untested is sensitivity to item order, batch composition and
few-shot choice, and the threats section says so.

---

## What to change, in order

1. ~~**Downgrade or re-run the ACD robustness claim.**~~ **Done both**: the
   claim is scoped, and the adaptive attack was run and removed 29 % of the
   protection. (§1)
2. ~~**Rerun one cell three times and publish the spread.**~~ **Done**:
   byte-identical across three replicates. (§10)
3. ~~**Promote the 10 % dose over saturation.**~~ **Done**, and it produced a
   better result than saturation: not one of 15 (defense, payload) pairs shows
   a resolvable benefit at the 10 % dose. (§3)
4. ~~**Report worst-payload-met per defense.**~~ **Done**, in the same table.
   (§7)
5. **Put control-fires-first in the methodology section** as a named
   contribution rather than a footnote. It is the thing DeepSec most needed
   and did not have. (§8/9)
6. **Add the monotonicity assertion to the harness** so it is enforced rather
   than audited. (§6)

## What we should say in the paper

Carlini's closing instruction is that conclusions "should be restricted to
non-adaptive, black-box, zero-query, and transfer-only adversarial examples."

We should write that scope into our own threat-model section in his words,
state that our failure results are lower bounds and therefore conservative
under it, and mark every robustness claim as holding only against the
non-adaptive payloads tested. A reviewer who knows this critique will look for
exactly that paragraph, and its absence is what makes a platform paper look
naive.

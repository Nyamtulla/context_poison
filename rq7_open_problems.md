# RQ7 — Open Problems

Generated 2026-09-06. Synthesis pass over RQ2 (`cross_citation_analysis.md`),
RQ5 (`rq5_coverage_matrix.md`) and RQ6 (`rq6_case_studies.md`), with
supporting structure from RQ1 (`rq1_taxonomy_analysis.md`), RQ3
(`rq3_pollution_census.md`) and RQ4 (`rq4_defense_census.md`). Derived
statistics computed by `scripts/rq7_synthesis.py` → `data/registries/rq7_synthesis_stats.json`.

**RQ7 (as stated in the project plan, Section 1):** What follows for research
priorities if RQ2, RQ5, and RQ6 hold — i.e., where should the field invest
next?

RQ7 introduces no new extraction and no new judgment about individual papers.
Every claim below is either a restatement of an earlier RQ's finding, or a
cross-cutting statistic computed mechanically over the registries those RQs
already built. Where RQ7 offers interpretation beyond what the data forces,
it says so explicitly.

---

## Headline result

**The field has a coordination failure, not a knowledge shortage — and the
strongest evidence for that is how much of the protection it has already
built goes unmeasured.**

Three independent measurements converge on this:

1. **The two research communities do not test each other's mechanisms.**
   Of the 190 confirmed defense×mechanism test pairs in RQ5's matrix,
   **188 (98.9%) stay inside a single track. Two cross it, and only one is a
   genuine cross-community test** (MAGE, an ML/AI-track memory defense,
   evaluated against Indirect Prompt Injection). This is a *new* number, not
   reported by any earlier RQ — and it is roughly an order of magnitude worse
   than RQ2's already-stark citation disconnect (10.8% of Track A papers cite
   Track B; 9.2% the reverse). **The two literatures cite each other rarely;
   they evaluate against each other's problems almost never.**

2. **Most defenses have never been tested outside the one scenario they were
   written for.** 97% were validated against a single threat model (RQ4:
   only 14 of 479 against both), and among the 170 that RQ5 could match to a
   named mechanism at all, 88.2% were tested against exactly one — the
   maximum anywhere in the corpus is two.

3. **When you actually run them across that boundary, they often work
   anyway.** RQ6's 9 case studies — every number from the defense's own
   released code and weights — found 4 of 9 fully generalized to the opposite
   threat model and 2 more partially. Of the 7 that ran to a usable result,
   **6 showed some protection nobody had claimed or measured.**

Taken together: the field is very likely *underclaiming* the coverage it
already has, while leaving 116 of 183 named pollution mechanisms with no
defense ever tested against them. The bottleneck is evaluation practice —
what gets tested, and against whose problem — rather than a shortage of
defensive ideas.

For an advisor-facing one-liner: *we found that the security community and
the reliability community have independently built defenses against what is
substantially the same failure, have almost never tested each other's cases,
and that when we ran their code across the divide ourselves, it frequently
worked — so the most valuable next investment is shared evaluation, not more
defenses.*

---

## The bridge finding: citation disconnect is also an evaluation disconnect

RQ2 established that the two literatures barely cite each other. That finding
invites an easy dismissal — citation practice is sociological, and two fields
can solve the same problem well without reading each other. The coverage
matrix lets us test whether the disconnect is merely bibliographic or reaches
into what the field actually measures.

| Defense's community | Mechanism's community | Confirmed test pairs |
|---|---|---:|
| Security | Security | 113 |
| ML/AI | ML/AI | 75 |
| ML/AI | Security | 1 |
| Both | ML/AI | 1 |
| **Cross-track total** | | **2 of 190 (1.1%)** |

RQ1 explains why this persists without anyone behaving irrationally: the two
communities study nearly disjoint *consequences*. Track A's goal-hijack
literature is 391 papers to Track B's 14; Track B's reasoning-corruption
literature is 313 papers to Track A's 11. Each community can look at the
other and honestly conclude it is working on a different problem.

RQ6 is the evidence that this conclusion is wrong. The same unmodified
defense code, handed a matched scenario from the other track, frequently
protects against it — DataSentinel, DataFilter and PISanitizer discriminated
cleanly in both directions; SCR landed at the *same* 67.5% defended accuracy
whether the bad context was an adversarially synthesized deceptive document
or a real, naturally-occurring wrong Reddit answer. A defense that lands on
the same number regardless of who authored the corruption is not solving two
problems. It is solving one.

**The disconnect therefore has a measurable cost**, and it is not primarily
about citations: it is 116 undefended mechanisms and an unknown quantity of
protection that exists but has never been demonstrated.

---

## Open problem 1 — Cross-threat-model evaluation is absent, and the barrier is norms, not feasibility

**Evidence.** 1.1% of test pairs cross tracks; 2.9% of defenses are validated
against both threat models; 88.2% of matched defenses are tested against
exactly one mechanism.

**Why it is open rather than merely unfortunate.** The obvious explanation —
that dual validation is technically hard, or only possible for certain kinds
of defense — does not survive the data. The 14 defenses that *did* validate
against both threat models are spread evenly across every intervention point
(4 ingestion, 4 reasoning, 3 execution, 3 architectural) and both communities
(10 Security, 4 ML/AI). No class of defense is structurally excluded.

RQ6 sharpens this further: constructing the matched counterpart was often
*free*. FaithfulRAG ships its own `synthesize_deceptive_document` template;
ConFiQA ships counterfactual-substitution documents; Open-Prompt-Injection
ships a textbook injection format. In several case studies the opposite
threat model could be built entirely from artifacts the original authors had
already released. The work was not done because nothing in the field's
reviewing or publishing conventions asks for it.

**What would resolve it.** A matched-pair evaluation convention: a defense
claiming to address consequence *C* on channel *X* reports results against
one adversarial and one incidental instantiation of *C*. RQ6's Methodology
section is a working template — an incidental construction must be genuinely
non-adversarial (no attacker intent, no instruction-like framing, ideally
content borrowed from elsewhere in the same dataset), and an adversarial one
a deliberately targeted, confidently worded false claim.

**Falsifiable prediction.** If this convention were adopted, the 2.9%
dual-validated rate should rise substantially *without a single new defense
technique being invented* — because the defenses would turn out to have
already had the coverage. RQ6's 6-of-7 result is a direct, if small, estimate
of how much latent coverage is waiting. This is the cheapest available win in
the entire field, and the prediction is testable by replication rather than
by argument.

---

## Open problem 2 — Nothing predicts which defenses generalize; the intervention-point hypothesis is the first candidate, and it is directly testable

**Evidence.** RQ6's central result is that transfer correlates with where in
the agent pipeline a defense sits: ingestion 3 of 4 fully generalized;
reasoning produced all three outcomes (full, partial, inert) across only
three defenses; execution produced zero usable runs.

The proposed mechanism, offered in RQ6 as a reading rather than a proven
causal claim: ingestion-stage defenses key on *structural* properties of
instruction-like language, which are largely independent of who wrote the
text — so they have no reason to care about attacker intent. Reasoning-stage
defenses calibrate trust between competing signals, a continuous statistical
judgment whose transfer depends on whether the corruption's statistical
signature is similar across threat models — sometimes it is (SCR), sometimes
the defense keys on a property that both threat models fail to produce
(CK-PLUG's entropy gate never fired, on 40 of 40 items in both conditions,
because confident wrongness does not look like uncertainty regardless of its
origin).

**Why it is open.** n=9, non-randomly selected, and further filtered by which
defenses had runnable code. RQ6 says so explicitly and the limitation is
real: this is a hypothesis with supporting evidence, not an established law.

**What would resolve it.** The sampling frame already exists — RQ4's registry
holds 120 ingestion, 189 reasoning and 70 execution defenses, and RQ5 has
already identified the 170 with a confirmed mechanism-level test. A
replication across 30–50 defenses drawn randomly within intervention point
would confirm or kill the hypothesis. It makes a specific ordinal prediction
(ingestion > reasoning > execution in transfer rate) that a null result would
cleanly refute.

**Why it matters if it holds.** It would give defense designers a
design-time expectation of generalization — currently unavailable at any
price — and would tell practitioners that the cheapest robust layer to add is
at ingestion, where protection appears to be threat-model-agnostic by
construction.

---

## Open problem 3 — The field's most-tested "mechanism" may be a category label, not a mechanism

**Evidence.** The single registry entry *Indirect Prompt Injection (IPI)*
absorbs 76 of 190 confirmed test pairs — **40% of all evaluation effort in
the corpus lands on one entry**. Meanwhile, 35 of the 183 registry mechanisms
are named injection variants, and **26 of those 35 have zero defenses ever
tested against them**.

**Why it is open.** IPI as the literature uses it names a *situation* —
attacker-controlled instructions arrive inside retrieved content — not a
specific technique. Seventy-six papers reporting "evaluated against IPI" may
be reporting results against seventy-six different concrete instantiations,
with different injection payloads, positions, phrasings and success criteria.
If so, the field's single largest concentration of evaluation effort produces
numbers that are **not comparable to each other**, and the apparent density in
that cell of the matrix is an artifact of a shared label rather than evidence
of a well-measured mechanism.

This is also, candidly, a limitation of our own registry's granularity. RQ3
kept 46 explicit extensions of prior mechanisms as separate entries
specifically so that RQ5 could distinguish "was the original tested" from
"was this variant tested" — but it inherited IPI from its seminal paper as a
single entry, at a coarser granularity than that rule would otherwise imply.

**What would resolve it.** Decompose the IPI entry into its concrete
instantiations and recompute the coverage matrix at that granularity. The
prediction is uncomfortable: coverage should *collapse further*, as one dense
76-defense cell disperses into many single-defense cells — meaning the field
has even less comparable evaluation than RQ5 already reports. A shared,
versioned IPI benchmark with named variants would be the constructive
counterpart, and would make the 76 existing results commensurable for the
first time.

---

## Open problem 4 — Attack invention outpaces defense evaluation, asymmetrically between the two communities

**Evidence.** Coverage of named mechanisms is starkly asymmetric by
community: **only 30 of 129 Security-track mechanisms (23.3%) have any
defense tested against them, versus 37 of 54 ML/AI-track mechanisms (68.5%)**
— put the other way, 76.7% of Security-track mechanisms have never been
defended against versus 31.5% of ML/AI-track ones, so a named adversarial
mechanism is about 2.4 times more likely to sit entirely untested.

By consequence, the gap concentrates where severity is arguably highest:

| Consequence | Mechanisms covered | Coverage rate |
|---|---:|---:|
| silent-corruption | 14 / 20 | 70.0% |
| reasoning-corruption | 25 / 40 | 62.5% |
| persistence-backdoor | 5 / 12 | 41.7% |
| **goal-hijack** | **22 / 100** | **22.0%** |
| **data-exfiltration** | **1 / 9** | **11.1%** |
| resource-abuse | 0 / 2 | 0.0% |

By channel, supply-chain (0 of 3), cross-modal (2 of 11), tool-output (17 of
62) and RAG (8 of 26) are the least-covered.

**Why it is open.** RQ3 already observed that the adversarial literature
names more distinct mechanisms per paper than the incidental literature
does — consistent with security research's convention of treating each new
attack as a discrete citable contribution. RQ5 and this analysis show the
downstream cost: that invention culture is not matched by a defense-evaluation
culture. The Security track has named 129 mechanisms and tested defenses
against 30 of them — a 4.3-to-1 ratio of invention to evaluation. The ML/AI
track names fewer mechanisms (54) and covers them far better (37), at
1.5-to-1.

**What would resolve it — and this is RQ7's most concrete answer to "where
should the field invest next."** The highest-value undefended targets, ranked
by coverage deficit weighted against plausible severity:

1. **Data-exfiltration (1 of 9 covered).** The worst-covered well-populated
   consequence in the corpus, and one where a single success is
   unrecoverable — exfiltrated data cannot be un-leaked, unlike a hijacked
   goal that can be interrupted.
2. **Goal-hijack (78 uncovered mechanisms).** The largest absolute gap, and
   the consequence the field believes it is working hardest on.
3. **Cross-modal (2 of 11) and supply-chain (0 of 3) channels.** Small, but
   entirely unaddressed, and both are structurally positioned upstream of
   every other channel's defenses.

---

## Open problem 5 — Execution-stage defenses depend on a capability the threat model attacks, and nobody has tested that dependency

**Evidence.** RQ6 attempted two independent execution-stage defenses
(IPIGuard, CaMeL) from different research teams using different mechanisms,
across six local-model attempts. **Zero produced a defended run.** Neither
failed on its security logic: IPIGuard's structured-JSON reflection step
entered a proven unbounded repetition loop (verified by quadrupling the token
budget, which delayed the failure proportionally without resolving it); CaMeL
responded conversationally to its own "fix your code" retry prompt instead of
emitting a code block, and failed outright on Mistral's chat template. Both
*undefended* baselines worked. It is specifically the defenses' rigid
output-format contracts that smaller open-weight models cannot satisfy.

**Two distinct problems follow, and the second is the more serious.**

**(a) A reproducibility and accessibility problem.** RQ4's registry contains
70 execution-stage defenses. If this class systematically requires frontier
models to run at all, then a substantial fraction of it cannot be
independently verified by groups without frontier-model budgets — and the
literature currently reports no minimum-capability requirement that would let
a reader predict this before attempting a reproduction.

**(b) An unexamined security assumption.** Execution-stage defenses derive
their guarantee from the model reliably satisfying a meta-level output
contract — valid JSON, code-only responses, well-formed tool-dependency
declarations. But *reliable instruction-following under adversarial context is
precisely the faculty that context poisoning attacks*. The defense scaffolding
therefore rests on a capability its own threat model targets. RQ6 observed
these defenses collapse under mere capability *insufficiency*, with no
attacker involved. Nobody has tested the adjacent and more troubling case: an
attacker who cannot break the capability policy directly, but who can degrade
the format compliance that policy enforcement is built on — collapsing the
defense into a crash, a retry loop, or a fallback path.

This is, to our reading of the corpus, an untested assumption underlying an
entire class of defense, and RQ7 flags it as such rather than claiming to have
demonstrated the attack.

**What would resolve it.** (i) Evaluate execution-stage defenses under
injections aimed at the *scaffolding* rather than the task. (ii) Report
minimum model capability as a first-class part of a defense's
specification — the way an algorithm reports its complexity.

---

## Open problem 6 — The evidence base cannot currently be audited

**Evidence.** The corpus is overwhelmingly preprint-stage: **757 of 886
included papers (85.4%) are grade C (credible preprint) and 127 (14.3%) grade
B**, with 533 (60%) published in 2026 alone. More concretely, RQ6 provides a
direct empirical measurement of artifact reality, since candidates were
selected *because* they claimed available code:

Of roughly 20 defense candidates worked through, **9 ran at all, and only 7
produced a usable measurement (35%).** The failure modes were: no public
repository (ACD, PromptArmor, AgentSentry), empty repositories (PH3, CD² —
same author), code released without weights or checkpoints (COMBO,
InstructDetector, KnowPO), gated base models (LlamaFirewall, ParamMute), and
one deprioritized on infrastructure cost (DyPRAG).

The `artifacts_released` field in the corpus — populated from each paper's own
text — records only what a paper *claims*. RQ6 caught it as a false positive
three times.

**Why it is open.** A field whose evaluation practice is already narrow
(OP1, OP3) and whose artifacts are unusable roughly half the time cannot
self-correct through replication, because replication is unaffordable. Every
finding in this SoK that rests on reported numbers rather than on our own
reconstruction inherits that fragility.

**What would resolve it.** Artifact claims should distinguish three levels
that the literature currently collapses into one: *code released* /
*weights or checkpoints released* / *runs end-to-end on stated open
hardware*. RQ6 demonstrates the distinction is not pedantic — it separated
the 9 defenses we could study from the 11 we could not.

---

## Open problem 7 — Temporal persistence is coded in the protocol but absent from the data

**Evidence.** The project plan's Section 3 extraction scheme specifies a
`temporal persistence` field (one-shot / session-persistent /
cross-session-dormant / self-propagating). **That column does not exist in
the extracted corpus** — the Papers sheet carries channel, intent,
consequence, intervention point and evidence grade, but persistence was never
coded.

**Why this matters more than a missing column normally would.** OWASP ASI06,
cited in the paper's own introduction as evidence of industry urgency, is
specifically *Memory and Context Poisoning* — and persistence is the property
that distinguishes context poisoning from ordinary prompt injection. A
one-shot hijack and a cross-session dormant backdoor have entirely different
severity, detection windows and defensive requirements, and the corpus
currently cannot distinguish them. RQ3 registers 12 persistence-backdoor
mechanisms and RQ5 finds only 5 covered, but neither can say whether the
uncovered ones are dormant, self-propagating, or merely session-scoped.

**What would resolve it.** Code the field. It is a bounded task over the 183
registry mechanisms rather than all 886 papers, and it would turn RQ1's cube
into a genuinely four-dimensional artifact. RQ7 flags this as a gap in our
own dataset, disclosed rather than quietly dropped.

---

## Ranked research priorities

Consolidating the above into the direct answer RQ7 asks for — ordered by
expected value, defined as impact weighted by how cheaply the question can be
settled:

| # | Priority | Rationale | Cost |
|---|---|---|---|
| 1 | **Matched-pair evaluation as a publishing norm** | Would likely reveal large latent coverage with zero new techniques (OP1); RQ6 measured 6 of 7 defenses protecting against untested threat models | Very low — often reusable from authors' own released artifacts |
| 2 | **Test the intervention-point generalization hypothesis at scale** | The only existing candidate theory of *which* defenses transfer; sampling frame already built (OP2) | Moderate — 30–50 reconstructions |
| 3 | **Defenses for data-exfiltration and the 78 uncovered goal-hijack mechanisms** | Worst coverage against highest irreversibility (OP4) | High — genuinely new defensive work |
| 4 | **Decompose IPI into a versioned, named-variant benchmark** | Would make 40% of all existing evaluation mutually comparable for the first time (OP3) | Low–moderate — benchmark construction, no new science |
| 5 | **Attack execution-stage defenses at their format contracts** | Untested assumption under an entire defense class (OP5) | Low — a targeted attack study |
| 6 | **Three-level artifact reporting** | Precondition for the field being able to replicate anything (OP6) | Very low — a reporting convention |
| 7 | **Code temporal persistence over the 183-mechanism registry** | Closes a gap in this SoK's own dataset on the dimension OWASP ASI06 centers (OP7) | Low — bounded extraction task |

Priorities 1, 4, 6 and 7 are conventions or bounded tasks rather than
research programs: **four of the seven highest-value interventions require no
new science at all.** That is the strongest form of RQ7's central claim — the
field's binding constraint is coordination, not capability.

---

## Methodology

RQ7 performs no new extraction. Its inputs are the finalized RQ1–RQ6
deliverables and the three registries (`data/registries/`). The cross-cutting
statistics reported here — track-crossing in the coverage matrix, coverage-gap
concentration by track/channel/consequence, the dual-validation profile, and
injection-variant dispersion — are computed by `scripts/rq7_synthesis.py`,
which reads the registries directly and writes
`data/registries/rq7_synthesis_stats.json`. Re-run it if any registry changes.

Track attribution for a test pair uses the `track` field of the defense's
registry entry and of the mechanism's registry entry — i.e. the community that
produced each — so a "cross-track pair" means a defense from one research
community was evaluated against a mechanism named by the other. Defenses filed
as `track=Both` are reported separately and excluded from the same/cross split,
since a defense already spanning both communities cannot evidence a crossing.

The evidence-grade and corpus-composition figures in OP6 are read from the
`Papers` sheet of `context_sok_master_workbook.xlsx` over the 886 included
papers. The artifact-reality figures in the same section are counted from
RQ6's own per-candidate record (`rq6_case_studies.md`, "What was tried and
ruled out"), which is a genuine-reconstruction result rather than a
self-reported field.

---

## Known limitations

- **RQ7 inherits every limitation of its inputs**, and they compound. The
  1.1% cross-track figure rests on RQ3/RQ4 track attribution, RQ5's
  entity-resolution matching, and RQ5's deliberate "favor false negatives"
  instruction. That conservative bias means true coverage is more likely
  undercounted than overcounted — but it cuts *toward* the cross-track
  finding being overstated as much as any other cell, so the figure should be
  read as "cross-track testing is rare to the point of near-absence" rather
  than as a precise 1.1%.
- **The cross-track measure is coarse by construction.** It compares the
  community that produced a defense to the community that named a mechanism.
  A Security-track defense tested against a Security-track mechanism may
  still have been evaluated on incidental degradation, and RQ4's
  `validated_against` field is the finer instrument for that question — which
  is why OP1 cites both the 1.1% and the 2.9% figures rather than either
  alone.
- **RQ6's evidence is 9 non-randomly selected case studies**, filtered
  further by runnability. Open problems 2 and 5 rest on it most heavily and
  are stated as hypotheses with supporting evidence, not established results.
  The intervention-point pattern is a real observation about this sample;
  treating it as a law of the field would overreach what 9 case studies can
  support.
- **Open problem 5(b) is an argument, not a demonstration.** We observed
  execution-stage defenses collapse under capability insufficiency with no
  attacker present, and argue by extension that an attacker could induce the
  same collapse deliberately. We did not build that attack, and the corpus
  contains no paper that has.
- **The severity weighting in OP4's ranked targets is our judgment**, not a
  measured quantity. Nothing in the corpus establishes that data-exfiltration
  is more severe than goal-hijack; the ranking reflects the irreversibility
  argument stated inline, and a reader who weighs severity differently should
  reorder accordingly.
- **`evidence_grade` shows no grade-A papers** (peer-reviewed with artifacts).
  This is reported in OP6 as preprint dominance rather than as a claim that no
  such paper exists, because grade A depends on the `artifacts_released`
  field that RQ6 independently showed to be unreliable — the absence is
  plausibly a grading artifact and should not be cited as a finding.

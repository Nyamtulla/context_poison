# Research roadmap — from SoK to contribution

Written 2026-09-22. Live document: tick items, add dated notes, do not rewrite
history.

## The claim we are trying to earn

> Everyone assumes defenses built for adversarial attacks won't help against
> incidental context corruption, so nobody tests it. We tested it by running the
> released code — and they mostly do. The field is wasting coverage it already
> has, and we can predict which defenses will transfer.

The 1,026-paper census is the sampling frame that makes this credible. It is not
the headline. The headline is the empirical transfer result, and right now that
result rests on **9 case studies and 1 validated prediction** — an anecdote with
a survey attached. Everything below exists to turn it into a measured claim.

## Status board

| # | Item | State | Blocked by |
|---|---|---|---|
| 0 | Freeze predictions v1 (timestamped) | **done** 2026-09-22 | — |
| 1 | Defense half-life analysis | **done** 2026-09-22 | — |
| 2 | Fix the attack control in AgentDojo | **in progress** | vllm + model serving |
| 3 | De-confound RQ6: all 9 defenses, one harness | **todo** | #2 |
| 4 | Re-fit transfer priors, pre-register v2 | **todo** | #3 |
| 5 | Out-of-sample transfer study (25–40 pairs) | **todo** | #4 |
| 6 | Manuscript assembly | **todo** | #5 |

---

## 0. Freeze predictions v1

**Why now.** `stage2_transfer_predictions.json` holds 111 ranked hypotheses
generated from the current model. Their evidential value collapses the moment we
start running them without a record that they predated the runs. This is the one
item with a deadline-like quality.

**Done when.** A timestamped, committed snapshot exists, with the model's
parameters (similarity weights, intervention priors) recorded alongside, so the
predictions are reproducible from the frozen inputs.

**Done 2026-09-22.** `data/registries/preregistration/transfer_predictions_v1_frozen.json`
— 111 predictions, model parameters, SHA-256 of all five inputs, git HEAD
`78e55d6`. 80 of 111 top candidates have released code, so the study is
feasible. The file explicitly records that RobustRAG×BadRAG was executed
*before* the freeze and is therefore in-sample: it must not be counted toward
the v2 out-of-sample hit rate.

**Note.** v1 is frozen for provenance, not as the study's pre-registration. The
priors are expected to move once #3 resolves the confound; the registered set is
v2. Freezing v1 lets us show the model was not reverse-engineered from results.

## 1. Defense half-life analysis

**Why.** The reverse scan recovered 37 defense×mechanism pairs from *attack*
papers. Roughly two-thirds record the defense failing, degrading, or being
evaded. The framing is sharp and independent of the transfer work:

> Defenses are evaluated against the attacks that existed when they were
> written, and the record of what happened next is published where their own
> literature never looks.

**Done when.** For every pair with a dated defeat, we have the interval between
defense publication and first published defeat, a survival curve over the
defenses with any recorded outcome, and an explicit statement of the censoring
problem (a defense with no recorded defeat is not a defense that holds — it is
one nobody has attacked in print).

**Needs no GPU.** This is analysis of data already in the repo.

**Done 2026-09-22.** `defense_half_life.md`, `scripts/defense_half_life.py`.
**96% of 24 datable published defeats occur within one year of the defense's
publication; median 1 year, max 2.** 15 distinct defenses, with DataSentinel
defeated 4 separate times. Only 2.8% of the 534-defense registry has any
recorded outcome, so the censoring section states plainly that one year is an
upper bound, not an estimate.

## 2. Fix the attack control

**The blocker, and it is real.** In the runs already executed, undefended ASR is
**4.2%–20.8%**. At those rates the experiment has no power: `asr_undefended ==
asr_defended` is the modal outcome and every verdict reads "DEFENSE FAILS" when
the honest reading is "nothing happened to defend against."

`run_mechanism_transfer.py` already reports `ASR_undefended == 0` as
*inconclusive* rather than as a defense success. That instinct is right and must
be extended: **a floor on undefended ASR is a precondition for reading any
defended number.**

**Done when.** A named (suite, model, attack) configuration reaches an undefended
ASR high enough to detect a meaningful reduction, with benign utility high enough
that the agent is actually working. Target ≥50% undefended ASR at ≥60% utility;
record what it took. If no configuration reaches it, that is itself a finding and
gets written up rather than buried.

**Levers, cheapest first:** stronger injection framing; a more capable
tool-calling model (A6000/49 GB fits a 14B comfortably); more user×injection task
pairs for tighter intervals; suite choice (workspace and banking behave
differently).

### 2026-09-22: the environment was rebuilt, and a transport bug was masking everything

The reconstruction checkout that held `eval.py` no longer exists, so the harness
was rebuilt self-contained. Three things were wrong, and the third matters
beyond this project:

1. **CUDA mismatch.** A bare `vllm` install pulls a CUDA 13 torch; the driver
   here is 12.2. Pinned to `torch==2.10.0+cu128` / `vllm 0.19.1`.
2. **Wrong port.** AgentDojo's `local` provider hardcodes `localhost:8000`; the
   README said 1111. Serving on 8000 rather than patching the library.
3. **AgentDojo's content blocks are not valid OpenAI schema.** It emits
   `{"type":"text","content":...}`; the API requires the text under `text`.
   Every request to a strictly-validating server (vLLM ≥0.19) returned HTTP 400.
   AgentDojo swallows the error, so the turn produced no output and every task
   scored `utility=False, security=False`.

**(3) is the cautionary one.** A harness in that state reports **0% ASR and 0%
utility for every condition** — which reads exactly like "the attack does not
land here" or "this defense blocks everything." It is a plausible,
publishable-looking result produced entirely by a transport bug. Fixed by
`local_llm_compat.py`, which normalises at the transport boundary rather than
reimplementing AgentDojo's message construction.

What caught it was the **utility floor**, not the ASR. A 0% ASR alone is
ambiguous; 0% ASR *at 0% utility* is a broken agent, and the floor made that
distinction mandatory before any defense could be evaluated. After the fix,
utility on workspace went 0% → 100%.

**This casts doubt on the previously-recorded agent-harness numbers.** The
DataSentinel run that flagged 0 of 60 injections and the RobustRAG run whose
control was "too weak to read" were produced on an environment that no longer
exists and cannot be inspected. They should be treated as unreliable until
re-run on this harness, and item 3's de-confounding pass supersedes them.

### 2026-09-22: a usable configuration, and a third infrastructure fault

Escalating the victim model found one configuration where a defense verdict
means something. Measured undefended, `important_instructions`, n=32/suite:

| model | suite | ASR | utility | smallest resolvable reduction |
|---|---|---:|---:|---|
| Qwen2.5-7B | workspace | 6.2% | 31.2% | none |
| Qwen2.5-7B | banking | 15.6% | 37.5% | none |
| Qwen2.5-14B | workspace | 12.5% | 28.1% | none |
| **Qwen2.5-14B** | **banking** | **46.9%** | 40.6% | **32pp — usable** |

Workspace is not usable at any n worth paying for: its undefended ASR is too low
for a working defense to show a resolvable drop. Banking is.

**Third fault: `spotlighting_with_delimiting` cannot run in AgentDojo 0.1.33.**
Its tool-output formatter is a self-referential lambda that recurses to
`RecursionError` on the first tool output. Spotlighting is a registry entry
here and one of the field's better-known defenses; any study selecting defenses
by "what runs in AgentDojo" would have dropped it silently. Fixed in
`agentdojo_defense_compat.py`.

That is three infrastructure faults in one harness in one day — a transport bug
that zeroed every run, a defense that cannot execute, and a prefix-sampling
scheme that stacked structural zeros. **This is worth promoting from a
methods footnote to a named finding**: the field's evaluation infrastructure is
thinner than its publication record implies, which is the same argument the SoK
makes about evaluation coverage, one level down.

### Experimental design: triage before pairing

The paired design (undefended + defended for every mechanism) spends half its
budget on payloads that never hijack the agent. The first four measured corpus
mechanisms came in at 0–3.1% undefended against AgentDojo's own attack at 46.9%,
so those defended runs bought nothing.

Revised: **screen all mechanisms undefended first**, then spend defended runs
only where there is something to defend against. n is kept at 32 for the screen
rather than trimmed — at a true rate around 6% a 16-pair screen expects a single
hijack and could see zero, and wrongly marking a live mechanism inert is the one
error that would quietly shrink the study.

**The likely finding, pending the sweep.** Most corpus mechanisms look inert on
banking, and probably not because the attacks are weak: they assume context the
suite does not provide. Memory persistence needs persistent memory, plan
injection a planner, MAS hijacking multiple agents, SkillJect skills. Banking is
single-agent tool-calling. If that holds, it is RQ6's confound in a sharper
form — **the victim's shape decides which attacks can land at all** — and it
bounds what any agent-benchmark-based transfer study can currently measure.

## 3. De-confound RQ6

**The threat to validity.** "Generalization tracks intervention point" is
currently confounded with harness shape: the ingestion defenses that generalized
were evaluated against a *text-classification* victim, the execution defenses
that failed against an *agent*. If harness shape explains the pattern, the
intervention-point prior is noise — and it is the prior the whole transfer model
is built on.

**There is already a signal that the confound is real.** DataSentinel was rated
*full generalization* in RQ6 under its own text-classifier harness. In the agent
harness it flagged **0 of 60** injections. Same defense, same code, opposite
verdict. That is one data point, taken under a weak control, and it is exactly
why #2 comes first.

**Done when.** All nine RQ6 case studies have a verdict under one agent-shaped
harness with a control that passes #2's floor, and the intervention-point
pattern is reported as holding, weakening, or reversing — whichever it does.

**A reversal is a publishable result, not a failure.** "The field's only
candidate theory of which defenses transfer is an artifact of how defenses are
benchmarked" is a strong paper.

## 4. Re-fit priors and pre-register

**Done when.** Priors are recomputed from #3's de-confounded rates, predictions
are regenerated, and the full ranked set is committed **before any pair in it is
run**, together with the sampling plan for #5 and the stopping rule.

**Sampling plan must include low-scoring predictions.** A model tested only on
its confident predictions cannot be shown to discriminate. Stratify across the
score range and commit to reporting every stratum.

## 5. Out-of-sample transfer study

**Done when.** 25–40 pairs sampled per #4's plan have been executed, with every
failure and every defense that would not run reported. Headline output is an
out-of-sample hit rate with an interval — the number that converts this from a
survey into a predictive result.

**Secondary output, possibly the more durable one:** the executed cells form the
first empirical cross-track transfer matrix in this field. Ship it as an
artifact.

## 6. Manuscript

Sequence the paper around the empirical result, with the census as method:
threat model and scope → the two-literature split (RQ1/RQ2) → the census and
coverage matrix as sampling frame (RQ3–RQ5) → **the transfer study** → the
half-life result → open problems. Threats to validity are largely written
already, including the corpus-boundary null result, which pre-empts the most
obvious reviewer objection.

## Deliberately not doing

- **More corpus expansion.** The 2026-09-21 rebuild tested the
  corpus-boundary objection directly by importing the literature we believed was
  missing. Coverage of previously-registered mechanisms did not move. Further
  screening work has no expected value.
- **RQ7 priority 7 (code `temporal_persistence`).** Stale. The column exists and
  is populated for all 1,026 included papers.

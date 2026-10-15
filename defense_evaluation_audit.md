# Was the "60% untested" figure real? Partly, and the honest number is different

**Recovery pass over the 527 RQ4 defenses, 2026-10-15.** Phase 1 of the
revalidation: how much of the coverage gap is the field not testing, and how
much is our extraction not resolving what the field did test.

Regenerate with `python3 scripts/classify_defense_evaluation.py`.

## The question

RQ5 reports that 214 of 527 defenses (40.6%) have a confirmed test against a
mechanism the RQ3 registry **names**. The remaining 313 have been read, inside
this project and outside it, as "never tested against an attack". Those are not
the same claim.

A defense paper that runs on AgentDojo without naming which injection it used
is evaluated adversarially. It is not a (defense, mechanism) pair, and
`benchmark_resolved_pairs.json` is deliberately strict about that, because
expanding a benchmark to all of its constituent attacks would manufacture
coverage. But it is not untested either.

## What we can state

**14 of 527 defenses (2.7%) report no baseline comparison at all.** Every one
of the 14 was checked by hand against its extraction note. They say so
explicitly: "None. No comparison against existing forensic or IPI-detection
methods is reported", "No empirical baselines. The comparison is conceptual",
"authors explicitly acknowledge the absence of a baseline method comparison".
One, AgenticOS, has no implementation at all: *"no empirical baselines are
compared since there is no implementation or evaluation."*

That is the floor, and it is nothing like 60%. **The published coverage figure
measures resolution against a named registry, not whether anyone ran an
experiment.**

## What we cannot yet state

A keyword classifier over the coded evaluation fields puts the rest roughly as:
214 named-mechanism, 193 evaluated but not adversarially, 58 adversarial in
prose, 36 adversarial benchmark only, 12 unclear. **Those middle numbers are
triage, not measurement.** Hand-checking two samples of the
claims-adversarial-but-shows-no-adversarial-evaluation cell found roughly half
were classifier misses rather than real mismatches: OpenClaw-SRT draws "attack
inputs" from a threat corpus, MedRAGShield ships "an author-released 40-query
adversarial dataset", and SPML-IR compares against text-based prompt-injection
detection. All three are adversarial evaluations the patterns did not catch.

The classifier made the same mistake this audit exists to find. Its first
version matched the bare token `adversar` inside the `threat_model` field and
classified 165 incidental-track papers as adversarially evaluated, because
`threat_model` says things like "non-adversarial" and "no adversarial threat
model". It was matching the word, not the experiment. Fixed by searching only
the fields that describe what was run, and by excluding negated forms.

## What this changes

Nothing in the coverage matrix. 332 pairs, 349 composite, 118 covered
mechanisms: all unchanged. This pass does not add pairs, because adding them on
benchmark names alone is the thing the existing rule correctly refuses.

What changes is the sentence the numbers support. **"60% of defenses were never
tested" is not supported. "60% of defenses have no confirmed test against a
mechanism our registry names, and 2.7% report no baseline at all" is.**

## For phase 2

The classifier's output is kept as `data/registries/defense_evaluation_status.json`
for triage, with its status and matched evidence per defense. The cell worth a
human pass is **claims adversarial, shows no adversarial evaluation**: 18
defenses, of which spot-checking suggests roughly half are real. That is a
small enough worklist to adjudicate by reading, and a real finding if it holds.

Phase 2's extraction needs three fields the current registry lacks:

| field | why |
|---|---|
| `origin` (proposed / extended / applied_as_is / mentioned_only) | `is_extension_of` is populated on 5% of defenses, so the registry cannot tell a method a paper invented from one it applied off the shelf. This is what let two deep-research agent frameworks be counted as fixes. |
| `evidence_quote` + section | A verbatim span from the evaluation section. No quote, no entry. An introduction sentence is not evidence that a method was built or tested. |
| `evaluated_against`, kept separate from the claim | RhinoInsight's entry was justified on "combating context rot" while its evaluation is a report-quality score. The registry had nowhere to record that those differ. |

---

## Phase 2b, 2026-10-15: reading the evaluation sections

Regenerate with `python3 scripts/classify_defense_evaluation_section.py`.

Phase 2a established authorship. It could not catch the RhinoInsight problem,
because RhinoInsight genuinely proposes RhinoInsight. What it fails is the
evaluation test, and only that one. So this pass locates each paper's own
evaluation section and looks only inside it. An introduction that says "we
address context rot" is not evidence that context rot was measured.

### The verified floor

**293 of 527 defenses (55.6%) are confirmed to have been evaluated against an
adversary**, by one of two independent routes: 214 appear in a confirmed
coverage pair, and 211 carry an unambiguous adversarial signal inside their own
evaluation section with the sentence quoted. The two overlap on 132, so each
route found cases the other missed. **79 defenses have adversarial evaluation
evidence that the coverage matrix never saw.**

Against the 14 (2.7%) verified in Phase 1 as reporting no baseline at all, and
220 (41.7%) whose status this project has not established.

So the sentence the numbers support is: **55.6% verifiably evaluated against an
adversary, 2.7% verifiably not, and 41.7% not yet determined.** Not "60%
untested".

### The tool is asymmetric and only half of it is usable

A sample of 10 from the 211 positives was clean. Every one quotes real
adversarial evaluation from inside the evaluation section: attack success rate
as the reported metric, injection subtypes with sample counts, poisoned
documents, named attack benchmarks.

The negative class is not usable, and the mismatch cell shows why. Of the 19
defenses flagged as claiming an adversarial threat model while showing no
adversarial evaluation, most are the pattern's failures rather than the
papers': MCP-Guard's section reads "5,258 samples (2,153 adversarial and 3,105
benign)", ShieldNet runs SC-Inject-Bench, PhantomLint detects hidden prompts in
documents, TRACE runs three agent safety benchmarks. **No number from the
negative class is quoted anywhere, and the mismatch list is not a finding.**

### What three passes established about the method

Three deterministic passes were built today. Each needed a hand-check, and each
hand-check found roughly half the negative class wrong:

| pass | positive class | negative class |
|---|---|---|
| Phase 1, coded fields | usable floor (14 no-baseline, all confirmed) | half were misses |
| Phase 2a, origin from the PDF head | usable (400 with quotes, sample clean) | low precision, kept as a worklist |
| Phase 2b, evaluation section | usable (211 with quotes, sample clean) | low precision, not published |

**The pattern is consistent and is itself the result.** A regex can confirm
that something is present in a paper. It cannot establish that something is
absent, because absence of the phrasing it knows is not absence of the thing.
Every claim in this project that rests on a negative ("never tested", "no
defense evaluated against it") needs either a human read or an explicit
statement that it means "not resolved", never "not done".

### What remains

220 defenses with undetermined evaluation status, plus the 127-entry origin
worklist. Those need reading, not matching. They are now a bounded job with a
specific question each: *does the evaluation section show this method run
against an adversary, yes or no, and quote the line.*

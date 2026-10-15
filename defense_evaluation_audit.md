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

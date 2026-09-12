# The screening gap: why foundational papers are missing (2026-09-11)

## How this was found

Working backwards from a question with an obvious answer: *if a paper proposes a
new attack, it must have tested it against some defense — so how can 102
mechanisms be "never defended"?*

They mostly aren't. **80 of the 102 uncovered mechanisms' papers do evaluate
defenses**, and 65 name a specific one. What they name:

| defense the attack paper ran | uncovered mechanisms | in the RQ4 registry? |
|---|---:|---|
| delimiters | 26 | no |
| paraphrasing | 19 | no |
| sandwich prompting | 16 | no |
| perplexity filtering | 15 | no |
| LLM-as-a-judge | 12 | no |
| input/output filtering | 11 | no |
| spotlighting | 9 | no |
| ProtectAI / DeBERTa | 9 | no |
| StruQ | 7 | no |
| SecAlign | 7 | no |

Not one is in RQ4. So "uncovered" has been measuring *"undefended by defenses in
our corpus"*, which is a much weaker claim than the one the write-ups make.

## It is not a search failure

Every missing paper **was discovered.** They sit in the 25,922-record pool. The
loss happened at screening.

The funnel: 25,922 discovered → 12,250 `auto_include`, 7,434 `auto_exclude`,
**6,238 `needs_review`** → the curated 1,008 = `auto_include` **AND** names a
signature term **AND** ≥1 citation.

`needs_review` papers were never promoted. Of the curated 1,008, only 6 came
from that bucket; **6,232 were never reviewed.**

## The specific cause

`config.yaml`'s `screening.include_signal_terms` requires an agent-era word —
agent, agentic, tool use, RAG, memory, multi-agent, context window. A paper
naming a threat but no agent word lands in `needs_review`.

Foundational prompt-injection papers predate the agent framing. They are about
LLM-integrated *applications*:

- *"StruQ: Defending Against Prompt Injection with **Structured Queries**"*
- *"Defending Against Indirect Prompt Injection Attacks With **Spotlighting**"*
- *"**Formalizing and Benchmarking** Prompt Injection Attacks and Defenses"*
- *"Not What You've Signed Up For: Compromising Real-World **LLM-Integrated
  Applications** with Indirect Prompt Injection"*

None contains an agent-era term. The signal list encodes an assumption that
context-integrity work says "agent", and the field's founding papers do not.

## What was lost

**Defense side — 39 papers with ≥1 citation**, including:

| citations | paper |
|---:|---|
| 410 | Formalizing and Benchmarking Prompt Injection Attacks and Defenses |
| 349 | StruQ: Defending Against Prompt Injection with Structured Queries |
| 313 | Benchmarking and Defending against Indirect Prompt Injection Attacks |
| 228 | Defending Against Indirect Prompt Injection Attacks With Spotlighting |
| 168 | SecAlign: Defending Against Prompt Injection with Preference Optimization |
| 111 | Attention Tracker: Detecting Prompt Injection Attacks in LLMs |
| 62 | PromptShield: Deployable Detection for Prompt Injection Attacks |
| 42 | Defending Against Prompt Injection With a Few DefensiveTokens |

**Attack side — 45 papers with ≥1 citation**, and this one is the serious one:

| citations | paper |
|---:|---|
| **1,639** | **Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection** |
| 210 | Backdooring Instruction-Tuned LLMs with Virtual Prompt Injection |
| 165 | Automatic and Universal Prompt Injection Attacks against LLMs |
| 154 | More than you've asked for: Novel Prompt Injection Threats |
| 144 | Tensor Trust: Interpretable Prompt Injection Attacks from an Online Game |

The 1,639-citation paper is the one that *named* indirect prompt injection. A
census of context-poisoning mechanisms that omits it has a problem no amount of
careful downstream analysis fixes.

## The fix

One rule, not a re-search. `include_signal_terms` currently demands agent
vocabulary; add a second, independent path to `auto_include`:

> a paper whose title or abstract names a context-integrity **threat**
> (prompt injection, context poisoning, knowledge conflict, retrieval
> poisoning) **and** either an attack action or a defense action qualifies,
> regardless of agent vocabulary.

Expected effect at the existing ≥1-citation bar: **+84 papers** (39 defense, 45
attack), which then flow into RQ3/RQ4 extraction.

## What it will do to the findings

It will **shrink the headline gap**, and that is the right direction.

- The ~65 mechanisms "tested only against defenses we don't have" become
  genuinely covered once StruQ, SecAlign, Spotlighting and the Liu et al.
  baselines are registry entries.
- RQ5's sparsity claim weakens further. It has already moved 116 → 102 from the
  benchmark fix; this will move it again.
- RQ7's "invention outpaces evaluation" needs re-checking: part of the apparent
  imbalance was defenses missing from the census, not missing from the field.

The concentration finding survives and probably strengthens: the recovered
defenses are the *same* handful everyone benchmarks against, so more coverage
lands on fewer distinct defenses.

## Recommended sequencing

1. Apply the rule, re-run screening, and report the delta — do not silently
   re-baseline.
2. Extract RQ3/RQ4 for the newly-included papers only (the delta approach in
   the `rebuild-corpus` skill), not the whole corpus.
3. Re-run RQ5 and re-check RQ7's framing against the new numbers.
4. Add a threats-to-validity paragraph stating that the original signal-term
   list was agent-biased, what it cost, and that it was corrected — a reviewer
   who notices Greshake et al. is missing will ask, and the honest answer is
   better told first.

The 6,232 never-reviewed `needs_review` papers remain a live exposure beyond
this fix. This rule addresses the subset that names a threat plus an action; it
does not review the rest.

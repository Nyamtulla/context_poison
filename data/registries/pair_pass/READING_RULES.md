# Pair pass: reading rules (2026-11-12)

A **pair** is one (fix, cause) combination where a paper's own experiment ran the
fix against the cause and reported a result. Causes are the entries in
`causes_list.json`: attacks (security) and honest failure modes (safety), plus
benchmark attack sets. Fixes are the names in `defense_names.json`.

Precision first. A pair needs all three:
- an experiment, not a mention;
- the fix running in it;
- the cause present in it.

## What counts as running the cause

- **Attack.** The experiment runs that attack, either directly or as part of a
  benchmark whose attack set includes it. One example is AgentDojo's
  important-instructions attack. Map it to the benchmark's own registry entry
  where one exists, such as "AgentDojo: important-instructions injection".
- **Honest failure mode** (lost in the middle, knowledge conflict, context
  rot, and so on). The experiment has to vary the condition or isolate it.
  Examples: moving the answer's position, building context-vs-memory conflict
  sets, or reporting results on a conflict subset.
  - A dataset merely "said to suffer from it" does not count.
  - An end-task score alone does not count.
- **Generic match.** "Indirect Prompt Injection (IPI)" counts when the
  experiment injects instructions into third-party content (tool output,
  retrieved documents, web pages, email) and no more specific registry attack
  fits.
  - Payloads in the user's own input slot are direct injection, not IPI.

## Pitfalls already seen

- **Name collisions.** "Overflow" meaning a full context window is not the
  BenchOverflow attack. "Context pollution" can be a paper's own term for
  something else.
- **Reversed direction.** A paper may use injection as its own weapon, for
  example to block scrapers. Then it is not a fix tested against injection.
- **Simulated numbers.** Results from the authors' own model, not from
  running a system, are not an evaluation.
- **Related work, motivation and threat-model mentions** are not experiments.

## Strength of a pair

Mark each pair `strong` or `weak`. Weak covers:
- a single hand-built example (n=1);
- synthetic cases with no model or agent actually run;
- a failure the paper coined itself and measured only through task score;
- an evaluation so sparse it cannot be described.

## Names

Use the exact name from `causes_list.json` or `defense_names.json`.

If something real was tested that is not in the lists, record it under
`unregistered` as free text. Never force a match.

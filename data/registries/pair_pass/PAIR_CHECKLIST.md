# When a (fix, cause) pair counts as tested

A pair means one fix was run against one cause, and a result was reported.
This checklist states what counts, so that others can check our pairs and
rebuild the list themselves.

## The checks

**Core checks (1–5).** A pair needs all five.

| # | Check | Question | Record |
|---|---|---|---|
| 1 | Experiment | Does the paper report a measured result from running a system? Motivation, threat model, related work, "projected" tables and the authors' own simulations do not count. | Table, figure or section |
| 2 | The fix itself | Is the method evaluated the registered fix, or its released code? A single component, an adaptation to another modality or an inspired variant does not count. | Where the fix is configured, plus any deviation |
| 3 | The cause itself | For an attack: are its payloads or procedure actually run? For an honest failure: is the condition varied or isolated (position sweep, conflict subset, length sweep), not merely present in the data? | How the cause was identified: name, citation, payload shown, or benchmark subset |
| 4 | Same run | Is the fix measured under the cause? Two separate reports, the fix on clean data and the attack on an undefended model, do not count. | The cell or row that holds the number |
| 5 | Right direction | Does the fix defend against the cause? It must not be a paper that uses the cause as its own weapon. | One line |

**Strength checks (6–7).**

| # | Check | The pair is weak if… |
|---|---|---|
| 6 | Separate result | The number for this cause is pooled with other attacks or conditions |
| 7 | Real scale | It rests on a single example, on synthetic cases with no model run, or on an evaluation too sparse to describe |

## Verdict

| Checks passed | Verdict |
|---|---|
| All seven | **strong** (counted) |
| 1–5 and 7, but not 6 | **pooled** (counted as tested; left out of outcome counts) |
| 1–5, but not 7 | **weak** (kept, not counted) |
| Any of 1–5 fails | **not a pair** |

A pooled pair was run, but its number is combined with other causes. It
answers "was this fix tested against this cause?" (yes) but not "did the fix
hold against it?", so it counts in coverage and is left out of every outcome
count. Ruling of 2026-11-14.

## Evidence

For every pair, record:
- a verbatim quote;
- where the quote appears (table, section or page).

## Name-mapping rules

Use these when the paper's name for a fix or cause differs from the registry's.

- **AgentDojo's "Delimit" / "spotlighting_with_delimiting"** maps to
  Spotlighting.
- **Generic delimiters** map to Spotlighting only when the paper cites Hines
  et al.
- **An AgentDojo run that does not name its attack** maps to
  "AgentDojo: important-instructions injection" only when the payload shown,
  or the setup, confirms it. Otherwise it maps to generic IPI.
- **"Indirect Prompt Injection (IPI)"** means injected instructions in
  third-party content (tool output, retrieved documents, web pages, email),
  where no more specific registry attack fits. Payloads in the user's own
  input are direct injection.
- **Knowledge conflict (contextual vs parametric)** needs context set against
  the model's own memory. Conflict between retrieved documents is not
  knowledge conflict.

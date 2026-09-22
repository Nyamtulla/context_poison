# RQ5 coverage-matching spec

For each **defense** in your slice, determine which **registry mechanisms it was
actually evaluated against**, from the defense paper's own text.

This builds the RQ5 defense x mechanism coverage matrix: the claim "this defense
has been tested against that attack." It is the spine of the SoK's headline
finding, so a wrong pair is far more damaging than a missed one.

## Input / output

- Your slice: `data/registries/raw/rq5_delta_slice<N>.json` — a JSON array of defenses,
  each with `defense_row`, `defense_name`, and the source paper's
  `baselines_compared`, `key_result`, `technical_summary`, `datasets_benchmarks`.
- Lookup reference: `data/registries/raw/rq3_registry_names.json` — the COMPLETE
  current RQ3 mechanism registry (names + channel/consequence/source title).
  Match against **all** of it, not just recent entries.
- Output: `data/registries/raw/rq5_delta_batch<N>.csv`, columns exactly:

      defense_row,defense_name,matched_mechanism_name,match_justification,match_confidence

  Write incrementally (flush every ~10 defenses). If the file already exists with
  partial results, read it and skip `defense_row`s already present.

One row per (defense, mechanism) pair. A defense evaluated against three registry
mechanisms produces three rows. A defense evaluated against none produces **no
rows at all** — do not emit a blank-mechanism row.

## What counts as a match

The defense paper must show evidence it was **actually run against** that
mechanism — in its evaluation, its baselines, its benchmark suite, or its
attack set. Matching is semantic, not string equality: papers describe the same
attack in different words, so read for the technique, not the token.

**`matched_mechanism_name` MUST be copied verbatim from the RQ3 registry**, exact
characters. A name that does not exactly match a registry entry is dropped at
build time (or silently fuzzy-recovered, which is worse). Copy-paste it.

Counts as a match:
- the paper names the technique and reports a number against it
- the paper evaluates on a benchmark that IS a registry mechanism
- the paper names the technique as a baseline attack it defends against

Does NOT count:
- merely citing the paper in related work
- "future work will consider X"
- a generic category ("we defend against prompt injection") with no specific
  named technique behind it
- the defense's own newly-introduced attack, unless that attack is itself a
  registry entry

## Confidence and the precision bias

`match_confidence` is `high`, `medium` or `low`.

**Favor false negatives over false positives.** Precision matters more than
recall here: the matrix's purpose is to measure how little cross-testing the
field does, so a fabricated pair actively destroys the finding, while a missed
pair leaves it conservative. If you are unsure, either omit the pair or record
it with `match_confidence: low` and say plainly in the justification what the
uncertainty is.

`match_justification` is one or two sentences quoting or closely paraphrasing the
specific text that establishes the pair. "Table 3 reports ASR against the
Combined Attack from Open-Prompt-Injection" is a justification; "appears related"
is not.

## Report back

Defenses processed; total pairs emitted; the confidence split; how many defenses
got zero pairs (this should be a large fraction — most defenses in this corpus
test against nothing the registry recognizes, and that is the actual finding);
and the 8-10 pairs you were least sure about.

# Phase 2a: did the paper propose this defense, or apply someone else's?

**Origin audit over the 527 RQ4 defenses, 2026-10-15.** Regenerate with
`python3 scripts/classify_defense_origin.py`.

## Why this was needed

`is_extension_of` is populated on **5% of RQ4 entries**. The registry could not
distinguish a method a paper invented from one it took off the shelf. That is
the gap that let two deep-research agent frameworks be counted as fixes for
context rot: both "address" it in their framing, neither proposes anything
about contaminated context.

## Result

**400 of 527 defenses (75.9%) are confirmed as the paper's own proposal, each
with a verbatim quote from its own abstract or introduction.** The quotes are
unambiguous: "We present APPA", "we propose ActiveMem", "We introduce PRISM",
"We introduce OBLIVION". These are written into the registry as
`origin: proposed` with `origin_evidence`.

**127 could not be established and are a worklist**
(`defense_origin_worklist.json`), not a verdict:

| | count | why |
|---|---:|---|
| no name to search for | 49 | the entry is `UNNAMED: ...` |
| name found, no proposal phrasing in the head | 42 | may be phrased unusually, may be prior work |
| classifier guessed applied_as_is | 28 | **unreliable, see below** |
| ambiguous | 8 | |

**The headline is reassuring and bounded.** Three quarters of the defense
census verifiably propose what they register, with evidence. The RhinoInsight
problem lives in the remaining quarter, which is now 127 entries to read rather
than 527.

## Two failures of this script, recorded because they are the point

The first version counted proposal-language hits against prior-work-language
hits across the whole document. It classified **SafeSieve as
`applied_as_is` on evidence that literally read "we present Safe- Sieve"**. The
cause: a paper proposes its method once and cites other work fifty times, so
related-work citation density buries the proposal sentence. Vote-counting over
a whole paper measures how much a paper cites, not who wrote the method.

Rewritten to require the proposal verb within 120 characters of the name, in
the first 18% of the document, where abstracts, introductions and contribution
lists live. That is high precision: a sample of the 400 was clean.

The second failure survives into this output and is why the 28
`applied_as_is` are a worklist and not a finding. Spot-checking them shows
LLMON, SecureCAI, SecureRag and chain-of-defensive-thought are plainly their
papers' own methods; they simply do not say "we propose X" in the head. **The
`applied_as_is` class has low precision and no number from it is quoted
anywhere.**

Both failures are the same error this audit exists to catch: matching
vocabulary instead of reading evidence. It is worth saying plainly that the
tool built to find that error committed it twice.

## What is still open

`origin` is now answered for 400 entries. The other two fields Phase 2 needs
are not:

- **`evaluated_against`, separate from the claim.** Phase 1
  (`defense_evaluation_audit.md`) showed the coded fields support a verified
  floor (14 defenses report no baseline at all) but not a reliable middle.
- **An evidence quote drawn from the evaluation section**, rather than from the
  introduction. The quotes collected here prove authorship, not testing.

Those two need the full-text read, and the read is now scoped to the 127-entry
worklist plus whatever the evaluation-section pass requires.

# Paper checklist

This paper will be revised for months. These are the rules it is written to,
drawn from four sources, kept here so that every iteration can be checked
against the same bar.

**Run the automated half first:**

```bash
python3 scripts/check_paper_style.py        # style, structure, the checkable crimes
python3 scripts/check_macros.py             # no orphan or undefined macros
python3 scripts/check_paper_invariants.py --save /tmp/before.json
#   ... revise ...
python3 scripts/check_paper_invariants.py --check /tmp/before.json
```

The invariant check is the one to run around any prose rewrite. It proves no
citation, macro, label, ref or number was lost while sentences moved.

The rest of this file is the half no script can judge. Walk it before each
submission.

## Sources

| | what it governs |
|---|---|
| VUSEC, *Writing a System Security Paper (A Checklist)* | structure, style, what to put where |
| McDaniel, *How to Write a Security Paper* (Penn State SIIS) | what a PC scores; short sentences. **Unfinished draft** — its Introduction, Related Work, Problem Statement, Solution and Evaluation sections are empty |
| van der Kouwe et al., *Benchmarking Crimes* (EuroS&P 2019) | 22 evaluation flaws |
| Roscoe, *Writing reviews for systems conferences* | what a reviewer looks for, in order |

## The six things a PC scores (McDaniel)

Novelty · Importance · Correctness · Presentation · Relevance · Excitement ·
then Overall. Novelty and importance are the two that decide value. Ask of
each: **can a reviewer score this without hunting?**

## What a reviewer does, in order (Roscoe)

A reviewer summarises the paper, states its contributions, then comments. Make
each step easy.

- [ ] **Summarisable.** Can a reader write a neutral paragraph on what this is
      about, why the problem matters, and what we did — from page 1 alone?
- [ ] **Contributions explicit.** Roscoe: failing to state them is "a
      surprisingly common mistake". Do not list ten. Pick what we want
      discussed.
- [ ] **Novelty explicit.** Say it once, plainly. Reviewers check whether
      related work invalidates it or merely re-frames it.
- [ ] **No missed related work.** The standard reviewer complaint. Re-search
      the area before each submission; the field moves monthly.
- [ ] **Flaws pre-empted.** Anything a reviewer could phrase as "I was left
      worried that X" should already be answered in the text.
- [ ] **One moment of delight.** Roscoe tells reviewers to mention what was
      cool. Ours should be the empty cell and the conservation result. Are
      they vivid, or buried?
- [ ] **Venue fit.** Judged against that venue's call for papers. *Not yet
      decided for this paper.*

## Writing (VUSEC, McDaniel)

- [ ] One idea per paper. Two are harder to sell even when both are good.
- [ ] Contributions on page 2 at the latest.
- [ ] Helicopter view first, then zoom. Same story at increasing detail.
- [ ] Short sentences with defined scope. Long multi-topic sentences work only
      when rare.
- [ ] No defensive writing. Argue in the Introduction and Background; from the
      Overview on, just present the work.
- [ ] Modest language. Boastfulness invites a reviewer to find a reason to
      reject.
- [ ] **Be upfront about what we cannot do.** A limit discovered on page 12 is
      worse than the same limit stated on page 2.
- [ ] Every term defined, every abbreviation expanded on first use.
- [ ] Say "first to do X" once. Twice is unnecessary. Three times is annoying.
- [ ] American English, no contractions, no split infinitives.
- [ ] Cite by system or author name, not a bare bracket.

## Evaluation (VUSEC, benchmarking crimes)

- [ ] Every claim backed by an experiment. Check that it actually is.
- [ ] Every plot and table explained: what should the reader notice, and what
      do the outliers mean.
- [ ] Each evaluation subsection converges — end by saying what was learned.
- [ ] Competitors compared fairly, same configuration.

### The 22 flaws, and where we stand

| | flaw | us |
|---|---|---|
| A1 | Not evaluating potential degradation | clean-dose arm reports what each defense costs |
| A2 | Benchmark subsetting without justification | **fixed** — the 2000-character cut is stated and justified |
| A3 | Selective data sets that hide deficiencies | we use each method's own data |
| B1 | Microbenchmarks as overall performance | agent and retrieval episodes stated as non-comparable |
| B2 | Throughput x% ⇒ overhead x% | n/a |
| B3 | Bad math | — |
| B4 | No indication of significance | Wilson intervals, Fisher exact, detectability threshold |
| B5 | Incorrect averaging across scores | per-cell, never across threat models |
| C1 | Simplified or simulated system | **stated limit** — dosing holds the retriever fixed |
| C2 | Inappropriate benchmarks | each method's own |
| C3 | Same data for calibration and validation | **stated** — the adaptive attacker optimises on the items it attacks, which is the threat model; the few-shot block is held out |
| D1 | No proper baseline | three: undefended, closed-book, clean dose |
| D2 | Only evaluate against yourself | we have no system of our own |
| D3 | Unfair benchmarking of competitors | control-fires-first exists for this |
| E1 | Not all contributions evaluated | — |
| E2 | Only measure run-time overhead | **inverted, stated** — we measure no cost at all |
| E3 | False positives/negatives not tested | abstention is one of the three controls |
| E4 | Elements not tested incrementally | gate on/off, alpha sweep, dose curve, model control |
| F1 | Missing platform specification | **fixed** |
| F2 | Missing software versions | **fixed**, including the three-stack problem |
| F3 | Subbenchmarks not listed | the census appendix lists all 783 |
| F4 | Relative numbers only | absolutes with n throughout |

## Figures and layout (VUSEC)

- [ ] Legible in black and white.
- [ ] Captions self-contained.
- [ ] Error bars where applicable — or a statement of why there are none.
- [ ] No widow or orphan lines, no heading at the foot of a page.
- [ ] Floats at the top of the page.

## Standing open items

- [ ] **Compile the paper.** There is no TeX toolchain on the box this is
      written on. The census appendix has never been built, and its
      single-column `longtable` needs one Overleaf run to confirm.
- [ ] **Verify the three 2026 citations** added to `refs.bib`. Their author
      lists are placeholders, each marked `VERIFY`.
- [ ] **Pick a venue**, then re-check scope against its call for papers.

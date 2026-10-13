# What "has code" means in this cell

**Artifact audit of the RAG x silent-corruption defenses, by citation rank.**
2026-10-12. Triggered by trying to run CD2, the best-cited defense we had not
yet tested.

`next_cell_plan.md` screens cells by "defenses w/code", counted from whether a
paper's artifact field names a repository or a release, and calls that an upper
bound. This records how loose that bound is.

## The top five unrun defenses

| defense | cites | artifact named | what is actually there | runnable |
|---|---:|---|---|---|
| CD2 | 117 | `github.com/jinzhuoran/KConflict` | **empty repository** | no |
| PH3 | 93 | `github.com/jinzhuoran/MConflict` | **empty repository** | no |
| Discern-and-Answer | 60 | `github.com/wjdghks950/Discern-and-Answer` | full code, **no checkpoint** | not at this cost |
| COMBO | 57 | `github.com/yunx-z/COMBO` | full code, **no checkpoints** | not at this cost |
| ACD | 22 | `github.com/younanna/ACD` | full code, decoding-time | **yes** |

## The two empty repositories

Both belong to the same group and both are linked from the paper as the place
the code will appear.

**CD2** - `jinzhuoran/KConflict`. GitHub API reports `size: 0`; `git ls-remote`
returns no refs at all; no branches, no tags. Created 2024-03-06 and never
pushed to since. Three open issues, none answered by the authors:

| # | date | title |
|---|---|---|
| 1 | 2024-12-08 | code is empty |
| 2 | 2025-02-21 | code is empty |
| 3 | 2025-12-28 | Could you release your code published at LREC-COLING 2024? |

Issue 1 has two further comments, both from third parties repeating the
request.

**PH3** - `jinzhuoran/MConflict`. Same: `size: 0`, no refs. Four open issues,
none answered:

| # | date | title |
|---|---|---|
| 1 | 2024-09-16 | 代码为空 ("the code is empty") |
| 2 | 2025-04-02 | Whether and when will you publish the code? |
| 3 | 2025-10-25 | Request for the code and dataset. |
| 4 | 2025-12-13 | 请求代码与数据集 ("request for code and dataset") |

**210 citations between them, seven unanswered requests spanning 15 months,
and zero lines of code.** Both papers are indexed in this corpus as having
released artifacts, because both say so.

## The two that ship code but not weights

Neither is blocked by availability. Both are blocked by what it would cost to
get from the repository to a running defense.

- **Discern-and-Answer** releases the full FiD + discriminator implementation
  and the MacNoise dataset, but no trained checkpoint. `test_reader.sh` points
  at `checkpoint/nq_base_640k_semi_parametric_disc_p75/checkpoint/step-640001`,
  which `train_reader.sh` produces in **640,000 steps** of FiD-base over 50
  passages per step. Its other arm is GPT-3.5/GPT-4 behind an API. The repo
  does ship the discriminator's precomputed predictions, but only over the
  authors' own evaluation sets, so they cannot score our poisoned contexts.
- **COMBO** releases the full pipeline but no checkpoints: two discriminators
  trained from silver labels, then a reader built on Atlas. Same shape, same
  cost.

These are recorded as *not attempted at this cost*, not as failures. A lab with
the budget to train both could run them, and the campaign's design is unchanged
by their absence.

## What this does to the screen

The cell's headline count is 42 defenses, 20 with code. That 20 counts CD2 and
PH3, whose repositories are empty, and counts Discern-and-Answer and COMBO,
which cannot be run without multi-day training. **Among the five best-cited
unrun defenses, one is actually executable.**

That ratio matters for how this SoK reports coverage. A table that says "20 of
42 defenses in this cell have code" invites the reading that two thirds of the
untested work is testable, which is not what the artifacts support. The honest
column is narrower, and the pattern inside it is informative:

> **Every defense in this cell we have successfully run is an
> inference-time intervention.** ParamMute, CK-PLUG, SpARE, SHIFT, COIECD and
> RobustRAG all modify decoding or activations on a released base model. Every
> training-based defense we have reached is blocked - by an empty repository,
> or by checkpoints that were never published.

That is a selection effect operating on the whole literature, not on our
choices, and it belongs in the write-up: an SoK that only reports what it could
execute will systematically over-represent decoding-time defenses, because
those are the only ones whose artifacts are self-contained.

## Registry entries that are now known to be wrong

`artifacts_released` is coded `Y` for CD2 on the strength of the paper's
statement that code "will be publicly available". That was a fair reading of
the paper and is false about the world.

**Not changed here.** Flipping it changes a published count, which is the
project lead's call. The two entries are:

| paper_id | defense | current | observed |
|---|---|---|---|
| `812b87876b22260fe046af447c5f40a4ce2906ea` | CD2 | `Y` | empty repo, verified by API and `ls-remote` |
| `2402.18154` (PH3) | PH3 | — | empty repo, same verification |

A `artifacts_verified` field separate from `artifacts_released` would keep both
facts: what the paper claims, and what is on disk.

## Method

For each candidate: GitHub REST API (`size`, `default_branch`, `pushed_at`,
`open_issues_count`), `git ls-remote` for refs, and a shallow clone. An empty
repository is one where all three agree: size 0, no refs, clone warns
"You appear to have cloned an empty repository."

---

# Full-cell audit, 2026-10-12

The sections above were written from the five best-cited untested defenses.
That sample made empty repositories look like the characteristic failure. The
full cell says otherwise, and the correction matters more than the original
observation.

`scripts/audit_cell_artifacts.py` probes every defense in the cell. The primary
test is `git ls-remote`: it is unauthenticated, unrate-limited, and answers
precisely the question — an existing remote with zero refs is a created,
never-pushed repository. The GitHub API is consulted afterwards for size and
issue counts and is allowed to fail.

## Result: 45 defenses

| state | n | share |
|---|---:|---:|
| **has_code** — remote exists, has refs | **21** | 46.7 % |
| **empty** — remote exists, no refs | 2 | 4.4 % |
| **unresolved** — claims a release we could not locate | 2 | 4.4 % |
| **none_named** — no artifact claimed anywhere | **20** | 44.4 % |

**The dominant state is not the empty repository — it is silence.** Nearly half
the defenses in this cell name no artifact at all. Empty repositories are rare
(2 of 45); they stood out in the earlier sample only because that sample was
drawn from the top of the citation ranking, where CD2 (117) and PH3 (93) both
sit and both happen to come from the same group.

The two empty ones are unchanged and remain the sharpest individual cases:

| defense | cites | repository | state |
|---|---:|---|---|
| CD2 | 117 | `jinzhuoran/KConflict` | empty since 2024-03-06, 3 unanswered issues |
| PH3 | 93 | `jinzhuoran/MConflict` | empty since 2024-06-06, 4 unanswered issues |

## What this fixes about the screen

`next_cell_plan.md` counts 20 of this cell's defenses as having code. The
audit's independent count is **21 with a live repository** — close, but the
agreement is coincidental, because the audit also finds 2 whose named
repository is empty and 20 that name nothing. The screen's number is roughly
right in magnitude and wrong in composition.

## The denominator this was run to establish

Of the 21 with live code, **9 have been run or attempted** in this campaign
(ParamMute, CK-PLUG, SpARE/SHIFT, FaithfulRAG, RobustRAG, COIECD, DyPRAG, ACD,
SABER) and **12 have not**:

| defense | cites | repository |
|---|---:|---|
| Discern-and-Answer | 60 | `wjdghks950/Discern-and-Answer` |
| COMBO | 57 | `yunx-z/COMBO` |
| SCR & CR-DPO | 27 | `kkkevinkkkkk/situated_faithfulness` |
| Taxonomy-Aware / conflict-type-aware | 20 | `google-research-datasets/rag_conflicts` |
| Knowledgeable-R1 | 9 | `lcy80366872/knowledgeable-R1` |
| XoT | 3 | `Tianzhe26/ConflictQA` |
| ProbeRAG | 2 | `XMUDeepLIT/ProbeRAG` |
| Micro-Act | 1 | `Nan-Huo/Micro-Act` |
| Swin-VIB | 0 | `JiataiWang/Swin-VIB` |
| CheckRLM | 0 | `AI9Stars/CheckRLM` |
| UNNAMED: Scientist Persona + Provenance Audit | 0 | `gyevnarb/indirect-data-poisoning` |
| UNNAMED: pre/post-research verification | 0 | `whfeLingYu/MisKnow-Agent` |

**A live repository is not a runnable defense**, and this audit does not claim
otherwise. It settles whether code exists; whether that code can be run without
multi-day training is a separate question that requires opening each repository,
and the cases already opened show the gap is wide: DyPRAG ships trained
translator weights and ran in a night, while Discern-and-Answer needs 640,000
FiD training steps and COMBO needs two silver-label discriminators plus an
Atlas reader. Two of the twelve are dataset repositories
(`rag_conflicts`, `ConflictQA`) rather than method implementations, and may not
be runnable as defenses at all.

So the honest frontier statement for the cell is: **21 defenses with code, 9
run, 12 outstanding, of which an unknown but minority fraction is executable
without training budget we do not have.**

## Two corrections this audit forced on its own method

- **A naive scrape is worse than no scrape.** The first pass fell back to
  reading arXiv HTML for GitHub links and marked 13 of 45 defenses `has_code`
  pointing at `brucemiller/LaTeXML` — the renderer that generates arXiv's HTML
  and appears in its footer — plus `langchain-ai/langchain` for RobustRAG and
  `meta-llama/llama3` for ACD. The tell was that CD2 and PH3 came back
  `has_code` when both had been hand-verified empty. A URL is now accepted from
  page text only when a release cue ("our code", "available at", "we release")
  appears within 240 characters before it, and an infrastructure blocklist
  catches the rest.
- **"Not found" is not "does not exist".** Four defenses whose repositories are
  real were initially recorded as having no URL, because the link lives in a
  PDF footnote or a reproducibility paragraph the HTML conversion drops. Three
  of them we had already run. The audit now separates `unresolved` (the paper
  claims a release, we could not locate it — our limitation, and an extraction
  gap) from `none_named` (no claim either), and seeds known repositories
  verified by hand or by execution. Collapsing those two states would have
  inflated the headline in the direction that suits the argument.

## An extraction error this surfaced

ACD's `artifacts_released` field reads *"No code or dataset repository link is
stated in the extracted text"*. The repository exists at `younanna/ACD`, and we
ran the defense from it. PH3's field reads *"N (unconfirmed)"*; its paper names
`jinzhuoran/MConflict`. Both are LLM-extraction misses of exactly the kind the
verification pass described in `CONTRIBUTOR_BRIEF.md` is meant to catch, and
both were found only because a human went looking for the code.

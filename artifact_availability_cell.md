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

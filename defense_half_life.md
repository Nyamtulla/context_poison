# Defense half-life — how long a published defense survives in print

Generated 2026-09-22 by `scripts/defense_half_life.py`. Companion to
`rq5_coverage_matrix.md` (the reverse scan that produced the underlying pairs)
and `rq6_case_studies.md`.

## The question

RQ5's reverse scan established that defenses are often evaluated inside *attack*
papers published after them, and that most such evaluations record the defense
losing. That is a statement about direction. This asks the temporal version:

> When a defense is defeated in print, how long after publication does it happen?

## Headline result

**Of 24 datable published defeats, 96% occur within one year of the defense's
publication, and 29% occur in the same calendar year.** The median interval is
**one year**. The longest is two.

| interval | defeats | cumulative |
|---:|---:|---:|
| same year (0y) | 7 | 29% |
| 1 year | 16 | 96% |
| 2 years | 1 | 100% |

Not one defense in this sample survived three years before something published
its defeat.

## What is actually being measured

The reverse scan recovered 37 defense×mechanism pairs from attack papers. All 37
are datable: the defense by its own paper's year, the defeat by the year of the
attack paper recording it. Of those, **24 record a defeat** (fails, largely
fails, insufficient, exploited, broken, assumption broken, degraded under
adaptation, evaded after adaptation), 12 are neutral evaluations, and 1 records
the defense partially holding.

The 24 defeats fall across **15 distinct defenses**. The repeat entries are not
noise — they are the shape of the finding:

| defense | recorded defeats | defeated by |
|---|---:|---|
| DataSentinel | 4 | DataFlip, tool-selection PI, ObliInjection, PISmith |
| DataFilter | 3 | AutoDojo, PISmith, memory-poisoning study |
| MELON | 3 | PI-Hunter, AdapTools, persistent-control study |
| Progent | 2 | AutoDojo, tool-description poisoning |

A defense does not get defeated once and settle. It gets defeated repeatedly, by
different teams, within the same twelve months.

## Why this matters for the SoK's central claim

RQ6 rated **DataSentinel** as showing *full generalization*. The reverse scan
shows four separate published defeats, all within a year of its publication, all
postdating the evaluation that earned it that rating. Both statements are true.
They describe different moments.

That is the finding in one sentence:

> A defense is evaluated against the attacks that existed when it was written,
> and the record of what happened next is published where its own literature
> never looks.

This is the temporal counterpart to RQ5's coverage gap. RQ5 says the field does
not test defenses against the full space of known attacks. This says that even
where testing happened, it captured a moment that expired quickly — and the
expiry is documented, just not in the defense literature's citation graph.

## Censoring — read before quoting any number above

These intervals describe defenses that were **both** attacked in print **and**
whose defeat our scan recovered. That is not a random sample. Three biases all
push the same direction:

1. **Survivorship.** Only **15 of 534 registry defenses (2.8%)** have any
   recorded outcome at all. A defense with no recorded defeat is not one that
   held; it is one nobody attacked in print, or one whose defeat we missed.
2. **Attention.** The defenses that attract attack papers are the well-known
   ones. DataSentinel has four recorded defeats because people bothered. An
   obscure defense is safe from attack *papers*, not from attacks.
3. **Right-censoring.** A 2025 defense has had less calendar time to be defeated
   than a 2023 one. Recent defenses look durable partly because the record has
   not caught up. With a corpus cutoff in 2026 and most defenses published in
   2025, this is the dominant bias and it inflates apparent durability.

**Treat one year as an upper bound on how long a well-known defense survives
contact with a determined attacker — not an estimate of defense lifetime.** The
true figure for defenses that attract attention is plausibly shorter; for the
97.2% nobody has attacked in print, it is unknown, and this analysis says
nothing about it.

## What would sharpen it

- **A proper survival model.** With publication dates on all 534 defenses and an
  explicit censoring indicator, this becomes a Kaplan-Meier curve rather than a
  histogram over the uncensored subset. The dates already exist in the corpus.
- **Symmetry check.** Run the same analysis in the other direction: how long
  until a published *attack* is defended against? If attacks are answered slower
  than defenses are broken, that asymmetry is itself a result.
- **Venue effect.** Whether peer-reviewed defenses survive longer than preprints
  is testable with `evidence_grade`, which already encodes publication rigor.

## Reproducing

```bash
python3 scripts/defense_half_life.py
```

Reads `data/registries/attack_paper_evaluations.json` and dates every pair
through the RQ3/RQ4 registries and the corpus workbook. Writes
`data/registries/defense_half_life.json`.

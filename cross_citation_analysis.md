# Cross-Citation Analysis (RQ2)

Regenerated 2026-10-27 by `scripts/rq2_cross_citation.py`.

**RQ2:** Do the security-regime and safety-regime literatures cite each other, or have they evolved as disconnected communities studying the same failure mode?

## Headline result

Computed over the **709 analysed papers** -- those that named an attack or a defense, out of 929 screened in -- from the 3,967 citation edges that run between them:

| Direction | Papers citing >=1 paper from the other regime | Papers in regime | Rate |
|---|---|---|---|
| Security -> cites safety | 47 | 426 | **11.0%** |
| Safety -> cites security | 32 | 283 | **11.3%** |

This is a full-population count over the analysed set, not a sample, so no confidence interval is reported.

## By evidence grade

| Grade | Security citing safety | Safety citing security |
|---|---|---|
| B | 8/78 = 10.3% | 10/65 = 15.4% |
| C | 39/348 = 11.2% | 22/218 = 10.1% |

## Methodology note

Both endpoints of every edge are classified by the `regime` column, and the edges come from `data/registries/citation_network_union.json` -- the same graph the paper's Figure 5 draws and the same one `scripts/gen_paper_numbers.py` reads for `\PctSecCitesSafety`, so the report, the prose and the figure cannot disagree.

Two limits bound the rates, and both push the same way:

- The denominator is the analysed papers, not every screened-in paper. A survey cites widely and names no technique, so counting it would measure reading habits rather than whether the two communities build on each other.
- Only citations to papers inside that set register. A paper reaching across to work we did not include does not count.

Every rate here is therefore a **floor**. The regime classification is automated over the discovery pool, so a systematic bias in it would move the rates; see `context_integrity_sok_project_plan.md` Section 12.

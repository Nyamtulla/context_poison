# Paper kit

Every table and figure the manuscript needs, generated from the live
registries by `scripts/build_paper_kit.py`. Re-run after new data; do not
hand-edit.

- **25 tables** in `paper_kit.xlsx` (one sheet each, INDEX sheet lists them)
- **13 figures** in `figures/` as PNG and PDF

## 3. Methodology

- table `S3_corpus_funnel` (8 rows) — Corpus funnel, discovery to inclusion
- table `S3_evidence_grade` (3 rows) — Evidence grade (publication rigor) of included papers
- figure `figures/fig3_1_corpus_funnel.png` — Corpus funnel from discovery to inclusion (log scale).

## 4. Taxonomy (RQ1)

- table `S4_channel` (9 rows) — Papers per context channel
- table `S4_cube_full` (9 rows) — Channel x intent x consequence cube (paper counts)
- table `S4_empty_cells` (98 rows) — Empty cells: 98 of 162
- figure `figures/fig4_1_channel.png` — Distribution of included papers across the nine context channels.
- figure `figures/fig4_2_cube.png` — The channel x intent x consequence cube; '·' marks an empty cell.

## 5. Citation network (RQ2)

- table `S5_cross_citation` (2 rows) — RQ2 cross-citation rates between the two literatures
- figure `figures/fig5_1_cross_citation.png` — Roughly nine in ten papers never cite across the divide.

## 6. Censuses (RQ3, RQ4)

- table `S6_rq3_summary` (17 rows) — RQ3 pollution mechanism registry
- table `S6_rq4_summary` (11 rows) — RQ4 defense registry
- figure `figures/fig6_1_rq3_channel.png` — Named pollution mechanisms per channel.
- figure `figures/fig6_2_rq4_validated.png` — Only 2.8% of defenses were validated against both threat models.

## 7. Coverage matrix (RQ5)

- table `S7_coverage_headline` (8 rows) — RQ5 coverage headline
- table `S7_coverage_gaps` (17 rows) — RQ5 coverage by track, channel and consequence
- table `S7_concentration` (12 rows) — Where defense-testing effort concentrates
- table `S7_uncovered` (131 rows) — The 131 mechanisms with no defense ever tested
- figure `figures/fig7_1_concentration.png` — One umbrella mechanism absorbs most testing; 131 mechanisms absorb none.
- figure `figures/fig7_2_coverage_channel.png` — Covered vs never-defended mechanisms, by channel.

## 7b. Benchmark standardization (new)

- table `S7b_benchmark_primary` (6 rows) — What each attack paper evaluated on
- table `S7b_reusability` (3 rows) — Could another researcher reuse that setup?
- table `S7b_top_benchmarks` (15 rows) — Most-reused evaluation benchmarks
- table `S7b_by_year` (4 rows) — Shared-benchmark use over time
- figure `figures/fig7b_1_benchmarks.png` — The most-shared benchmark covers 11.7% of attacks; 78% of benchmarks are used once.
- figure `figures/fig7b_2_sharing_over_time.png` — Shared-benchmark use roughly halved as the field grew.

## 8. Generalization (RQ6 + new runs)

- table `S8_transfer_matrix` (5 rows) — Defense technique x attack, banking/Qwen2.5-14B, n=32, verdicts gated on detectability
- table `S8_attack_screen_v2` (6 rows) — Attack reconstruction quality: v2 rebuilds vs the harness's own attack
- table `S8_benchmark coverage` (17 rows) — Can the standard agent benchmark host the corpus's attacks?
- figure `figures/fig8_1_transfer.png` — Ingestion detectors lose their effect when the attack's framing changes; the execution-stage technique does not.
- figure `figures/fig8_2_benchmark coverage.png` — Corpus attacks rebuilt on the standard benchmark, undefended.

## 8b. Defense half-life (new)

- table `S8b_half_life` (3 rows) — Interval from defense publication to published defeat
- table `S8b_half_life_rows` (24 rows) — Every datable published defeat
- figure `figures/fig8b_1_half_life.png` — 96% of published defeats occur within one year. Heavily censored -- an upper bound.

## 9. Differentiation

- table `S9_comparators` (6 rows) — The five closest SoKs, coded by our own scheme
- table `S9_differentiation` (7 rows) — What separates this SoK

## 10. Open problems (RQ7)

- table `S10_cross_track` (8 rows) — RQ7 cross-track testing in the coverage matrix
- table `S10_headline_numbers` (10 rows) — Every headline number, for the abstract


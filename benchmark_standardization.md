# The absence of a standard benchmark: what this field evaluates on

Generated 2026-09-23 by `scripts/analyze_benchmark_census.py` over
`data/registries/benchmark_census.json`. Covers **all 223 named mechanisms** in
the RQ3 registry.

## A note on terminology

This uses **benchmark** throughout, because that is what this literature calls
it: 1,665 uses across the corpus, against 32 for "testbed" and 30 for
"substrate" — and every corpus use of *substrate* means an underlying system
layer (coordination substrate, retrieval substrate, agent substrate), not a
thing you evaluate on.

"Fragmentation" is likewise avoided. In this literature **fragmented** describes
splitting an *attack payload* into pieces, which is a different idea entirely.
The field's own phrase for what this section measures is **"no standard
benchmark"** (14 direct uses in the corpus).

## The question

For every named attack, what did its source paper evaluate on — and could
another researcher take that setup off the shelf and run a *different* attack or
defense on it to produce a comparable number?

A paper can have a large, careful, well-documented evaluation and still answer
no, because the setup is bespoke to its own attack.

## Headline result

**The most widely shared evaluation benchmark in this field covers 11.7% of
named attacks. 78% of benchmarks are used by exactly one paper.**

| | mechanisms | share |
|---|---:|---:|
| built its own benchmark / testbed / environment | 98 | 43.9% |
| used a standard NLP/QA corpus, own attack on top | 61 | 27.4% |
| used a shared **security** benchmark | 43 | 19.3% |
| evaluated against a live product | 8 | 3.6% |
| no evaluation benchmark | 5 | 2.2% |
| unclear from the extracted text | 8 | 3.6% |

Reusability of the setup:

| verdict | mechanisms | share |
|---|---:|---:|
| `yes` — another paper could reuse it directly | 49 | 22.0% |
| `partial` — shared corpus, bespoke attack construction on top | 79 | 35.4% |
| `no` — bespoke, live-system, or nothing | 95 | 42.6% |

## The concentration is the finding

255 distinct named benchmarks appear across 223 mechanisms — **more benchmarks
than attacks**. Of those:

- **199 of 255 (78.0%) are used by exactly one paper.**
- The most-shared, AgentDojo, appears in **26 of 223 mechanisms (11.7%)**.
- The next four are general NLP corpora, not security benchmarks: HotpotQA (16),
  Natural Questions (15), InjecAgent (11), MS-MARCO (10).

There is no common ground. The nearest thing to a standard covers roughly one
attack in nine, and the runners-up are QA datasets that papers layer their own
attack construction on top of — which is why they are scored `partial` rather
than `yes`: two papers both using HotpotQA still are not comparable.

## It is getting worse, not better

| year | mechanisms | not reusable | on a shared **security** benchmark |
|---|---:|---:|---:|
| 2023 | 13 | 38.5% | **30.8%** |
| 2024 | 38 | 28.9% | 18.4% |
| 2025 | 68 | 48.5% | 22.1% |
| 2026 | 104 | 44.2% | **16.3%** |

As the field has grown eight-fold, the share of work evaluated on a shared
security benchmark has roughly halved. Growth is producing more bespoke
environments, not more shared ones.

## The two tracks differ sharply

| track | mechanisms | not reusable |
|---|---:|---:|
| ML/AI (incidental degradation) | 55 | **27.3%** |
| Security (adversarial) | 168 | **47.6%** |

The incidental-degradation literature inherited the ML community's benchmark
culture — it evaluates on HotpotQA, MMLU, GSM8K, LongBench, things other people
already use. The security literature builds a new testbed per paper at nearly
twice the rate.

This matters for the SoK's central claim. RQ2 found the two literatures barely
cite each other; RQ5 found they almost never cross-test. This is a *mechanism*
for both: they do not merely disagree about what to study, **they do not share
the ground on which a comparison could be run.**

## Why this explains the coverage gap

RQ5 found only 2.8% of defenses validated against both threat models, and the
2026-09-21 rebuild showed that importing the field's missing foundational papers
did not close the gap at all. That was a negative result without an explanation.

This is the explanation. Cross-testing a defense against an attack requires a
benchmark both can run on. For 42.6% of attacks no such benchmark exists, and
for another 35.4% it exists only partially. The gap is not inattention — it is
that the comparison is, for most pairs, not currently constructible.

It also predicts the 0-of-16 result in
`agent_benchmark_representability.md`: attacks whose papers built bespoke
environments will not run on someone else's benchmark, because they were never
designed to.

## Threats to validity

- **Judged from extracted `datasets_benchmarks` text, not fresh full-text
  reads.** Inherits any imprecision in that field. 13 of 223 were low
  confidence, 86 medium, 124 high.
- **The yes/partial boundary is contestable.** The rule is that a shared corpus
  with a bespoke attack layered on is `partial`, since numbers are not
  comparable across papers. A reviewer preferring a looser rule would move some
  `partial` to `yes`; the `no` column, which carries the headline, is less
  sensitive to this.
- **Classification bias was set against the hypothesis.** Agents were told
  bespoke is *not* the default and to look for a named pre-existing benchmark
  first. The result survives a rubric tilted the other way.
- **"Distinct benchmarks" counts names after normalisation** (alias collapsing,
  parenthetical stripping). Residual spelling variants would inflate the 255
  slightly; the 78%-used-once figure is robust to a few merges.
- **Reuse is judged from the paper's own description**, not from whether anyone
  actually reused it. A released benchmark nobody adopted still scores `yes`.
  The true sharing rate is therefore **lower** than reported here.

## Reproducing

```bash
python3 scripts/analyze_benchmark_census.py
```

Per-mechanism judgments with justifications are in
`data/registries/benchmark_census.json` and the raw agent output in
`data/registries/raw/benchmark_census_out*.jsonl`.

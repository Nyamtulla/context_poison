# How the verification sample was drawn, and what it will support

**100 papers, drawn 2026-10-12, seed 20261012.** Regenerate exactly with
`python3 scripts/build_verification_sample.py --seed 20261012`.

## The one rule that makes this work

The plan is to verify a subset and conclude something about the rest. **That
inference is only valid if the subset is a probability sample.** If papers are
chosen because they are important, familiar, or convenient, the resulting
accuracy describes those papers and nothing else, and a reviewer will say so in
one line. Every paper here was drawn by a seeded random process from a defined
stratum. Nobody picked any of them.

## The frame

| number | what it is |
|---:|---|
| **1,026** | **included papers — what the paper's claims are computed over** |
| 132 | excluded papers |
| 1,158 | total coded rows (1,026 + 132) |
| 1,097 | papers with a local PDF |

The **primary estimand is accuracy over the 1,026 included papers.** The 132
excluded are sampled too, but reported separately — blending them into a single
headline would answer a question nobody asked.

## Strata and weights

| stratum | frame | N | n | weight | sampled |
|---|---|---:|---:|---:|---:|
| S4_main — the bulk | included | 960 | 63 | 15.24 | 6.6 % |
| S1a_no_pdf | included | 47 | 12 | 3.92 | 25.5 % |
| S2_track_both | included | 19 | 10 | 1.90 | 52.6 % |
| S3_excluded | excluded | 118 | 13 | 9.08 | 11.0 % |
| S1b_excl_no_pdf | excluded | 14 | 2 | 7.00 | 14.3 % |

**Three strata are deliberately oversampled**, each for a reason that is not
"they looked interesting":

- **S1a / S1b — no PDF.** The free-text fields are populated at exactly the
  rate PDFs exist (1,097 of 1,158). So these papers' *taxonomy* fields were
  assigned without full text, presumably from the abstract. They are the most
  suspect codings in the corpus and nobody has ever looked at them. At their
  population share they would contribute 5 papers; they get 14.
- **S2 — track = "Both".** Only 19 papers, and RQ2's headline cross-citation
  rates (11.7 % / 9.1 %) depend on track assignment being right. Proportional
  allocation would give 2. Half the stratum is sampled instead.
- **S3 — excluded papers.** A false exclude is invisible in every downstream
  number and can **never** be detected by checking included papers. This is the
  only stratum that can find papers that should have been in the corpus.

Oversampling is not bias as long as the weights are used. Each stratum carries
`weight = N / n`, and the overall accuracy is the weighted combination, not the
raw mean over 100 rows. **A plain average across the sheet will understate
accuracy**, because the hardest papers are deliberately over-represented.

## What 100 papers buys

Each sampled paper contributes one judgement per field, so each field is
estimated at n ≈ 85 (included frame). 95 % Wilson intervals:

| if true accuracy is | n = 85 (per field) | n = 20 (dual-coded) |
|---:|---|---|
| 99 % | [93.7, 99.8] | [83.9, 100.0] |
| 95 % | [88.0, 97.9] | [76.4, 99.1] |
| 90 % | [81.7, 94.6] | [69.9, 97.2] |
| 85 % | [75.7, 90.9] | [64.0, 94.8] |

**This supports a claim of the form "extraction accuracy on field X is at least
Y %."** It does not support "accuracy is exactly 94 %", and it will not resolve
a 3-point difference between two fields. If a field comes back below ~90 %, the
honest response is to verify more of that field, not to argue the interval.

## What the sheet asks for

One row per (paper, field) — 100 × 17 = **1,700 cells**. Four verdicts:

- `correct` — the value is right and the paper says so
- `wrong` — the paper says something different
- `not-in-paper` — the paper does not state this at all. **Distinct from
  `wrong`**, and the more important of the two: it separates a misreading from
  an invention, and those have different fixes.
- `unclear` — ambiguous, or undecidable from what you have

Fields are split into `core` (the seven the headline numbers rest on),
`secondary`, and `freetext`. Score them separately; "wrong" means something
different for a taxonomy label than for a prose summary.

**Record disagreement, do not repair it.** A silently corrected cell destroys
the measurement it was drawn to produce.

## Double coding

**20 of the 100 are marked `dual_coded=YES`** and should be coded independently
by two people who do not see each other's answers, so Cohen's kappa can be
reported. Without it there is no evidence the *humans* agree, and at this venue
that is a question the reviewers will ask. 20 is enough to detect gross
disagreement; it is not enough for a precise kappa, and the write-up should say
so rather than quoting it to two decimals.

**A known weakness, stated rather than hidden:** verifiers see the AI's value
in the same row they judge. That invites anchoring and will inflate agreement.
The clean fix is to blank the `AI_extracted_value` column for the dual-coded
rows and have one coder fill the field from the paper cold. Worth doing for the
20 if the team can bear it.

## What this cannot tell you

- It measures whether extracted values match the papers. It does not measure
  whether the **taxonomy** is the right taxonomy, or whether the screening
  criteria are the right criteria.
- It covers the 1,158 coded papers. It says nothing about the ~24,000 records
  screened out earlier in the pipeline; a systematic false-exclude there would
  be invisible to this exercise entirely.
- Per-field estimates at n ≈ 85 are adequate for a floor claim and weak for
  comparisons between fields.

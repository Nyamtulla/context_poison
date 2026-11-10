# S2 hand check (2026-11-09)

Sample: 15 of 93, drawn with seed 20261109 (5 security, 10 safety), ids in
`hand_check_sample.json`. Checked against the reading-order text
(`text_flow/`) for context_unit, k_main and competes_with, the three fields
the split rests on.

Automated: 1,243 of 1,265 evidence quotes (98%) are found in the paper text
(`quote_check.json` lists the 22 that are not; none is a context_unit or
k_main quote in the sample).

| id | coded | check |
|---|---|---|
| f09 | other, k not stated | agree: the paper gives no k |
| f05 | one-passage (whole Wikipedia article) | agree; long-document would also fit, n_passages=one either way |
| f19 | ranked-set, k=20 | agree (Sec 5.1) |
| f13 | joined-set, k not stated | agree: "top-k" with no value |
| f23 | ranked-set, k=50 | agree (Sec 4.1) |
| f28 | joined-set, k=20 | agree; see FiD note below |
| f47 | ranked-set, k=2 | agree: two contradicting contexts per query |
| f43 | one-passage, memory | agree: questions filtered to those the model knows |
| f31 | tool-output, k=10 | agree (search agent, top 10 results) |
| f01 | ranked-set, k=100 | agree (Table 1) |
| f83 | ranked-set, k=10+10 | agree on count; see FiD note |
| f49 | joined-set, k=10, both | agree (Sec 6.2) |
| f26 | joined-set, k varies | agree: k swept 1-256, no single main k |
| f33 | joined-set, k=10 | agree (Sec 3, Google top-10) |
| f51 | one-passage, memory | **partial**: the main table uses a "mixed context", a conflicting and a supporting passage interleaved every 4 tokens; competes_with should be `both`. A secondary RAG run uses top-5. |

Result: n_passages (one vs many) correct on 15/15; competes_with 14/15.

Consistency note: methods that encode passages separately and let the
decoder attend over all of them (Fusion-in-Decoder style: f28 KV-Fusion, f83
COMBO) were coded joined-set once and ranked-set once. The counts the paper
uses rest on n_passages, which is unaffected; the ranked/joined label for
filter-then-read hybrids (f01, f03, f15, f25, f29, f52, f62, f07) is
arguable and should not be reported as a finding.

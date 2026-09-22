# Manual downloads — screening-delta papers (RESOLVED 2026-09-21)

**Status: closed.** Of the 36 papers this list asked for, **23 were manually
retrieved** by the project lead and are now in the corpus; **13 were not
available from a source judged acceptable** and were discarded by decision.

This file is kept as the audit trail for that decision. The live PDF/coding
state lives in `data/registries/screening_delta_pdf_status.json`.

## Outcome

| | papers |
|---|---:|
| recovered by the 2026-09-11 screening rule | 164 |
| retrieved automatically (2026-09-13, two passes) | 128 |
| retrieved manually by the project lead (2026-09-21) | 23 |
| **total with full text** | **151** |
| discarded — not available / not an acceptable source | 13 |

The 23 manual retrievals were all from the IEEE Xplore block (23 of that
block's 24). Every one was verified before ingest: PDF magic bytes, extractable
text (18k–168k characters), and the paper's own title present in its own
extracted text — so no paywall login page or wrong-paper save entered the
corpus. Those checks are the same ones `fetch_missing_pdfs.py` applies to
automated downloads.

## Discarded (13)

Not retrievable from an open or institutionally-available source. Recorded here
as a **known, bounded gap rather than a silent one** — a reviewer can see
exactly what is missing and how much it could matter.

| cites | year | title | DOI / link | why not retrieved |
|---:|---:|---|---|---|
| 26 | 2024 | GUARDIAN: A Multi-Tiered Defense Architecture for Thwarting Prompt Inj | 10.4236/jsea.2024.171003 | publisher not open |
| 24 | 2025 | Vulnerability of Large Language Models to Prompt Injection When Provid | 10.1001/jamanetworkopen.2025.49963 | JAMA paywall |
| 14 | 2024 | Text-Based Prompt Injection Attack Using Mathematical Functions in Mod | 10.3390/electronics13245008 | MDPI - not retrieved |
| 8 | 2025 | Comprehensive Analysis of Machine Learning and Deep Learning models on | 10.54392/irjmt2523 | publisher not open |
| 6 | 2025 | Prevention of Prompt Injection Attacks Over Financial Applications Int | 10.1109/incacct65424.2025.11011372 | IEEE Xplore paywall |
| 6 | 2024 | A Methodology for Risk Management of Generative AI based Systems | 10.23919/softcom62040.2024.10721790 | publisher not open |
| 3 | 2026 | Securing the Cognitive Layer: A Survey on Security Threats, Defenses,  | 10.3390/jcp6020063 | MDPI - not retrieved |
| 3 | 2025 | Bypassing Guardrails: Lessons Learned from Red Teaming ChatGPT | 10.1145/3747288 | ACM DL paywall |
| 1 | 2025 | Threats and Defenses for Large Language Models: A Survey | 10.1145/3773365.3773631 | ACM DL paywall |
| 1 | 2024 | The Impact of Prompting Techniques on the Security of the LLMs and the | 10.3390/app14198711 | MDPI - not retrieved |
| 1 | 2025 | Secure Model Context Protocol for Large Language Models with Dual Sign | 10.1145/3737897.3767287 | ACM DL paywall |
| 1 |  | LLM-PIEval: A benchmark for indirect prompt injection attacks in Large | https://www.semanticscholar.org/paper/c2fe003d159227305ae6d04451f6492ba05f4edb | Semantic Scholar landing page only; no PDF |
| 1 | 2026 | Evaluation of NeMo Guardrails as a Firewall for User–LLM Interaction | 10.3390/fi18050252 | MDPI - not retrieved |
**Materiality.** The highest-cited discard has 26 citations; 9 of the 13 have
6 or fewer; 5 are explicitly surveys, taxonomies or curriculum/risk-management
papers, which this project's RQ3/RQ4 criteria code as contributing no mechanism
and no defense regardless. The discards are therefore unlikely to move any
headline number. The one worth naming in a threats-to-validity paragraph is
GUARDIAN (26 cites), which does propose a named multi-tiered defense and would
plausibly have been an RQ4 entry had the PDF been reachable.

**Reversible.** Each row keeps its DOI. If institutional access changes, the 13
can be fetched and coded without redoing anything else — they are already in
`screening_delta_pdf_status.json` under `discarded_unavailable`.

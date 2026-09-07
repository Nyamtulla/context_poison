# RQ3 — Context Pollution Census

Generated 2026-08-17, on the 886-paper working corpus (post re-screening and
duplicate-paper corrections). Regenerate if the corpus or registry changes.

**RQ3 (as stated in the project plan, Section 1):** How many distinct,
*named* mechanisms by which an LLM agent's context can become poisoned or
polluted have been identified in the literature — whether introduced
deliberately as an attack technique (Track A) or arising incidentally as a
degradation mechanism (Track B) — and how are they distributed across
channels and consequences?

## Headline result

**183 distinct pollution mechanisms** identified across the corpus:
- **129 (70.5%) are adversarial (Track A)** — named attack techniques
  (PoisonedRAG, AgentPoison, ToolHijacker, GCG-based corpus poisoning, and
  126 others).
- **54 (29.5%) are incidental (Track B)** — named degradation mechanisms
  (lost-in-the-middle, context rot, knowledge conflict, distraction by
  irrelevant context, and 50 others).

This 70/30 split is itself worth noting alongside RQ1's channel/consequence
imbalance: not only do the two tracks study different consequences (RQ1),
the adversarial literature also names and catalogs more *distinct
mechanisms* per paper than the incidental literature does — consistent with
security research's convention of treating each new attack as a discrete,
citable contribution, versus incidental-degradation research more often
measuring or mitigating an already-established phenomenon (lost-in-the-middle,
knowledge conflict) rather than naming new ones. 480 of 890 papers processed
across both tracks did **not** introduce a registry-worthy mechanism — they
were benchmarks, defenses, surveys, or measurement-only papers applying an
existing named mechanism rather than characterizing a new one.

## By channel

| Channel | Mechanisms |
|---|---:|
| tool-output | 62 |
| direct-input | 43 |
| RAG | 26 |
| memory | 13 |
| tool-metadata | 12 |
| cross-modal | 11 |
| multi-agent | 9 |
| skill | 4 |
| supply-chain | 3 |

Tool-output dominates (mostly Track A indirect-injection variants); this
tracks RQ1's channel totals directionally but isn't the same metric — RQ1
counts *papers per channel*, this counts *distinct named mechanisms per
channel*, so a channel can have many papers but few distinct techniques
(suggesting a mature, incrementally-studied channel) or few papers but many
distinct techniques (a channel where each new paper stakes out new ground).

## By consequence

| Consequence | Mechanisms |
|---|---:|
| goal-hijack | 100 |
| reasoning-corruption | 40 |
| silent-corruption | 20 |
| persistence-backdoor | 12 |
| data-exfiltration | 9 |
| resource-abuse | 2 |

Goal-hijack alone accounts for over half the registry (100/183) — the
single most "invented" consequence, in the sense of attracting the most
distinct named techniques, consistent with it being the dominant Track A
consequence per RQ1.

## Registry construction notes

- **46 of 183 (25%) are explicit extensions** of a prior named mechanism
  (tagged `is_extension_of`) — e.g. Approximate Greedy Gradient Descent as
  an improved GCG/HotFlip search, or a mechanistic explanation of an
  existing phenomenon like lost-in-the-middle. These are kept as separate
  registry entries with their lineage noted, not merged into their parent —
  a judgment call favoring registry granularity over consolidation, since
  RQ5's coverage matrix benefits from distinguishing "was the *original*
  technique tested" from "was this *specific variant* tested."
- **36 of 183 (20%) are unnamed** — the introducing paper didn't coin its own
  term, so a short descriptive label was assigned during extraction (tagged
  `UNNAMED:` in the raw data). These are real, distinct mechanisms, just
  without an established citable name in the literature yet.
- **4 duplicate paper entries were found and corrected during this
  construction pass** (not a registry-entity-resolution issue — literal
  duplicate rows in the corpus itself): PoisonedRAG, AgentVigil, "Multi-Agent
  Framework for Threat Mitigation," and a position-bias mechanism paper each
  had a second, no-arXiv-ID corpus entry. See `rescreening_log.md` addendum
  for detail; RQ1 and RQ2's published numbers were updated accordingly.

## Methodology

Extraction delegated to 4 parallel subagents (2 for the 466 Track A papers,
2 for the 404 Track B papers), each judging per-paper whether it introduces
a genuinely new, named mechanism (vs. a benchmark/survey/defense-only/
measurement-only paper applying an existing one), following explicit
include/exclude criteria and confidence self-flagging. Raw candidates (186
before corpus corrections, 183 after) were then deduplicated: exact-name
matching found zero shared names (technique names are, by construction,
mostly unique per paper); fuzzy matching (rapidfuzz, threshold 70) surfaced
7 candidate near-duplicate name pairs, of which 1 (a position-bias mechanism
paper indexed twice) turned out to be a genuine duplicate *paper*, not a
naming coincidence — corrected as above — and the remaining 6 were confirmed
as distinct techniques with superficially similar names (e.g. "IterInject"
vs. "ChatInject" vs. "AutoInject" — a common naming convention, not the same
technique).

## Known limitations

- Registry construction used already-extracted `technical_summary`/
  `key_result` fields (from the earlier full-text extraction pass), not a
  fresh full-text read specifically for this task — inherits whatever
  imprecision exists in those summaries.
- The include/exclude bar ("does this paper's core contribution deserve a
  distinct, citable name") is inherently a judgment call, especially for the
  36 unnamed entries and 46 extension entries. A different coder applying
  the same criteria might draw the line a few entries differently in either
  direction — this is flagged in the plan's threats-to-validity section
  (entity resolution risk) and should be treated as directionally reliable,
  not a precise ground truth.
- Fuzzy-match deduplication used a single threshold (70) and only checked
  registry *names* against each other, not full paper content — it's
  possible for two mechanisms with very differently-worded names to still be
  the same underlying phenomenon (this is a real risk the plan already
  flags for RQ5's harder attack-defense matching step, and applies here too,
  just not caught by name-similarity alone).

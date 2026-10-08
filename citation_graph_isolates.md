# The isolated papers in the citation graph

**Why 191 of 1,026 papers show no link, and whether that is a problem.**
2026-10-08.

## The short answer

It is a gap in the **edge store**, not in the corpus. Of the 191 papers that
draw as outliers, **171 have no reference list in our citation store at all**,
so no edge could be drawn from them whatever they cite. Only **20** are
papers whose references we hold and which genuinely reach nothing else in
the corpus.

| | papers |
|---|---:|
| look like outliers in the graph | 191 |
| — their reference list was never fetched | **171** |
| — genuinely isolated: we have their references, none land in the corpus | **20** |

Coverage of the edge store: **828 of 1,026** corpus papers have a fetched
reference list. The missing 198 are concentrated exactly where you would
expect — 158 of them are 2025 or 2026, and 164 arrived through keyword search
rather than through citation snowballing, so no edge was ever traversed to
reach them in the first place.

## Why they are in the corpus anyway

Inclusion never depended on citing anything. A paper is included if it is
about LLM agents and presents an attack, a defense, a benchmark or a
measurement of context contamination or degradation. Those criteria are read
off the paper's own content.

And the content was read. **186 of the 198 papers with no fetched references
were read in full text**, which is how their channel, consequence and
evidence grade were coded in the first place. A paper can be fully analysed
and still have no edge in the graph; the two come from different passes.

## This does not move RQ2

My first reading of this was wrong and is worth recording. The thought was
that `cites_track_a` and `cites_track_b` are derived from the edge store, so
198 papers with no edges would be defaulting to "cites neither" and dragging
the cross-citation rate down. Recomputed on the 828 papers with fetched
references, the rates do move — 11.7 % to 12.8 %, and 9.1 % to 12.6 %.

**But those columns are not derived from the edge store.** They are full-text
extraction fields, coded by reading each paper's own reference section
(`scripts/apply_delta_extraction.py`). A paper with no API edges still has a
real, read coding. So the restricted recomputation above answers a question
nobody asked, and the published **11.7 % / 9.1 %** stands unchanged.

The lesson is about the graph, not the finding: **the picture understates the
connections, the numbers do not.**

## The 20 genuine outliers

| year | track | role | cites A/B | title |
|---|---|---|---|---|
| 2026 | ML/AI | defense | N/N | G-MemLLM: Gated Latent Memory Augmentation |
| 2026 | ML/AI | defense | N/N | Trust-Aware Runtime Verification for Autonomous LLM Agents |
| 2026 | ML/AI | both | N/N | SAM: State-Adaptive Memory for Long-Horizon Reasoning |
| 2026 | ML/AI | both | N/N | Goal-Autopilot: Anti-Fabrication Firewall |
| 2026 | ML/AI | neither | N/N | Agentic Test-Time Scaling for WebAgents |
| … | | | | *(12 more, all 2025–2026 agent-systems papers found by search)* |
| 2024 | Security | defense | Y/N | SPIN: Self-Supervised Prompt Injection |
| 2024 | Security | defense | Y/N | Data Defenses Against Large Language Models |
| 2024 | ML/AI | both | N/Y | Discerning and Resolving Knowledge Conflicts through Adaptive Decoding |

Two different things are in this list.

The **2024 security ones** are not really isolated. They cite Track A (`Y/N`),
they were found by forward snowballing from papers we hold, and the only
reason no edge lands inside the corpus is that the specific papers they cite
are in the 26,000-paper discovery pool rather than the 1,026 we carried
forward. That is a boundary effect, not disconnection.

The **2025–2026 ML/AI ones** are the real thing: agent-architecture and
long-horizon-memory papers that engage neither literature. They are coded
`N/N` honestly. Ten of the twenty contribute no attack and no defense to the
registries, so they sit in the corpus without entering RQ3, RQ4 or RQ5.

> **Worth a decision, not a silent edit.** Those ten are in scope by the
> written criteria — they are about agents and about context management — but
> they add nothing to any research question and they are the papers a reader
> would point at if they wanted to argue the corpus is padded. Tightening the
> criterion to require a *named* mechanism or defense would remove them, and
> would also remove some of the 466 other `neither` papers. That changes a
> published count, so it is the project lead's call.

## What would actually fix the picture

Fetch the missing 198 reference lists and rebuild `citation_edges`. That is an
API pass, not a re-reading: the papers are already analysed. It would not
change any reported number, but it would stop the graph from showing a
disconnection that is partly our own data collection.

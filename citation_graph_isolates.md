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


---

## Addendum, 2026-10-08: the API pass, and what it could not fix

Re-fetched reference lists for the 197 corpus papers that had no outbound edge,
using the project's existing Semantic Scholar client. 196 fetched, 1 failed.

| | before | after |
|---|---:|---:|
| edge store rows | 42,123 | **45,861** |
| edges with both ends inside the corpus | 2,089 | **2,310** |
| corpus papers with a reference list | 828 | **962** |
| papers drawing as isolated | 191 | **118** |
| — reference list unavailable | 171 | **52** |
| — genuinely isolated, references in hand | 20 | **66** |

*(Separately, 64 corpus papers have no reference list at all. 52 of them are
isolated; the other 12 are still connected by inbound edges from papers that
cite them.)*

**73 papers stopped being isolated.** The graph now shows 221 more in-corpus
links than it did, and the disconnection it displays is that much less our own
making.

Two things the pass established that guessing would have got wrong.

**The remaining 52 are not a backlog.** Semantic Scholar returned no reference
list for them at all — of the 64 corpus papers in that position, 60 are 2025 or
2026 and 31 are arXiv preprints with no venue. The data does not exist upstream yet. Re-running this
will not help; only time will. That belongs in the threats to validity, not on
a to-do list.

**The count of genuinely isolated papers went up, not down — from 20 to 66.**
That is the pass working, not failing. Those papers moved out of "we have no
idea what they cite" and into "we know what they cite, and none of it is in
this corpus". It is a worse-looking number and a better-founded one.

Nothing reported anywhere moved. `cites_track_a` and `cites_track_b` are
full-text codings and were not touched, so RQ2 still reads 11.7 % and 9.1 %.


## Why 66 papers still cite nothing in the corpus

The backfill left 66 papers whose references we hold and whose references reach
nothing in the 1,026. That is not a data gap any more, so it needs a reason.

Two, in order of size.

**Most of their references were never retrieved.** Of the 1,037 references held
for these 66 papers, **668 (64 %) point at works that are not in the
25,922-paper discovery pool at all** — never searched for, never fetched. We
cannot say whether those works are in the corpus because we have no record of
them. So even the "genuine" isolation is measured on a third of the evidence.

**What we can see, they cite the wrong literature — for us.** The references
that do land in the pool are the agent-building canon:

| cited by how many of the 66 | work |
|---:|---|
| 10 | Toolformer |
| 6 | GPT-4 Technical Report |
| 5 | Self-Refine |
| 4 | AutoGen · Reflexion · MemGPT · Gorilla · Search-R1 |

None of those is in the analysed corpus, because none of them is about context
integrity. They are about how to *build* an agent. The isolated papers are
mostly 2025–2026 agent-architecture and long-horizon-memory work, and they are
citing the architecture conversation, not the attack-and-defense one.

> **So the honest answer is: they are in our corpus because they match our
> criteria on content, and they are disconnected because they belong to a
> neighbouring conversation that our corpus deliberately does not carry.**
> That is a boundary effect, and it is the expected shape of one. It is not
> evidence that the corpus is wrong, and it is not evidence that these papers
> are isolated in the field — only that they are isolated from the slice of
> the field we kept.

### One caveat about the edge store itself

The original snowball recorded an edge only when it kept the target paper, so
`citation_edges` was a within-pool graph rather than a reference list. The
backfill stored every reference the API returned, in-pool or not. The store now
mixes the two conventions: 39,196 edges point inside the pool and 6,665 point
outside it. Anything that counts edges globally should say which it wants.

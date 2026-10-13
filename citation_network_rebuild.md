# The citation network, rebuilt from the PDFs

Built 2026-10-13 by `scripts/rebuild_citation_network.py`. Every edge comes
from a reference list read out of a PDF, not from the Semantic Scholar graph.

## What it is

| | |
|---|---:|
| PDFs processed | 1,097 |
| reference list extracted | **1,087** |
| no extractable reference section | 10 *(unknown, not isolated)* |
| match targets (included titles) | 1,024 |
| **edges** | **4,838** |
| cite ≥1 corpus paper | 927 |
| cite 0 corpus papers | 160 |

Citations into the corpus per paper: median 3, mean 4.5, max 77.

Sanity check — the most-cited papers *inside* the corpus come out exactly where
they should: *Not What You've Signed Up For* (335), *Lost in the Middle* (160),
StruQ (156), InjecAgent (155), *Prompt Injection attack against LLM-integrated
Applications* (146).

Matching is a contiguous slice of the normalised title. An earlier version
required 80 % of a title's distinctive words to appear *anywhere* in the
reference section and returned 174 corpus citations for a six-page paper,
because common words co-occur by chance across sixty references.

## Both edge sources are wrong, in opposite directions

Over the same 1,087 papers:

| | n |
|---|---:|
| isolated per Semantic Scholar edges | 199 |
| isolated per full text | 160 |
| **S2 says isolated, the PDF says otherwise** | **79** |
| full text says isolated, S2 has an edge | 40 |
| both agree | 120 |

**40 % of S2's isolates are false** — the API simply lacks the edge. And the
full-text pass has its own 40 misses, where a reference is abbreviated or the
title is printed in a variant form. Neither source alone supports a deletion
decision. The intersection (120) is the only defensible candidate set, and
even that is not a delete list — see below.

## Why "cites nothing in our corpus" is not a relevance signal

Of the 120 papers isolated by **both** measures:

| | |
|---|---|
| 2023 papers that are isolated | **12 of 33 — 36 %** |
| 2026 papers that are isolated | 53 of 580 — 9 % |
| mean in-degree of the 120 | **6.1** |
| mean in-degree of everyone else | 4.2 |

The isolates are **more cited by the corpus than the corpus average**, and a
2023 paper is four times more likely to be one. The four most-cited:

| in-degree | year | paper |
|---:|---|---|
| **335** | 2023 | Not What You've Signed Up For *(the most-cited paper in the whole network)* |
| **160** | 2023 | Lost in the Middle |
| 87 | 2023 | WebArena |
| 46 | 2023 | LLMs Can Be Easily Distracted by Irrelevant Context |

These papers cite nothing in the corpus **because they came first.** Citation
isolation here measures *being foundational*, not being peripheral. Deleting on
out-degree would delete the origin of both literatures — the paper that defined
indirect prompt injection and the paper that defined context degradation.

**39 of the 120 also contribute an RQ3 or RQ4 registry entry**, so removing
them moves published counts.

## The criterion that does work

Out-degree alone cannot separate *foundational* from *peripheral*, because both
cite nothing. **In-degree separates them**: a foundational paper is heavily
cited by the corpus; a disconnected one is cited by nobody either.

So: cites nothing in the corpus **and nothing in the corpus cites it**, by
**both** edge sources, restricted to included papers, excluding anything that
contributes a registry entry.

That yields **26 papers** — `data/registries/citation_disconnected.json`.

They are a coherent group: long-horizon agent benchmarks and frameworks
(*SearchArt*, *ToolVerse*, *VideoSeek*, *VSearcher*, *SWE-TRACE*, *CarePilot*),
agentic-AI security posture and framework reports (*Cisco Integrated AI
Security Framework*, *ASTRIDE*, *MCP Server Security Posture*), and
architecture papers with no attack, defense or measurement. **All 26 are coded
`role='neither'`** — none contributes an attack or a defense. They are mostly
2025–2026, mostly uncited, and mostly adjacent-topic rather than on-topic.

These are a defensible exclusion candidate list. They are still not an
automatic delete: the criterion says *disconnected*, and relevance is a separate
judgement that wants eyes on the paper.

## What this does not do

Removing all 26 takes the corpus from **1,023 to 997**. That crosses under
1,000, but the mechanism is "drop 26 role=neither adjacent papers", not a
principled tightening. If the goal is a corpus small enough to cite in a paper,
that is a decision about the **inclusion criteria** — and the honest version is
to tighten `config.yaml` and re-screen, which changes the published numbers
openly rather than by attrition.

## Reusable output

`data/registries/citation_network_fulltext.json` holds all 4,838 edges and the
per-paper record, including the 10 papers whose reference section could not be
read. Those are recorded as `unknown`, never as isolated — collapsing the two
is precisely how a measurement failure becomes a deletion.

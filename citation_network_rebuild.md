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


---

# v3: identifiers first, and matching that ignores how a PDF breaks text

v1 above matched a 9-word title phrase and found 4,838 edges, but missed 40
papers Semantic Scholar had edges for. Diagnosing three of them gave three
different causes, and fixing each in turn produced two more bugs worth
recording, because each one was found by a number refusing to make sense.

| version | edges | isolates | what changed |
|---|---:|---:|---|
| v1 | 4,838 | 160 | 9-word title phrase |
| v2 | 6,503 | 116 | + arXiv/DOI matching, 6-word phrase, de-hyphenation |
| **v3** | **6,954** | **105** | space-free matching, unique-prefix selection |
| **union with S2** | **6,985** | **101** | each edge labelled by source |

**v3 is a strict superset of v1** — zero edges lost — which is the check that
matters when a rewrite claims to be an improvement.

## What each fix was worth

- **arXiv IDs were being ignored entirely.** A reference list prints
  `arXiv:2302.12173`, which is an exact identifier, and v1 looked only at
  titles. Adding identifier matching contributed **3,135 edges**, nearly half
  the final network. DOIs added 138 more.
- **The title phrase was too long.** Reference lists truncate titles and PDFs
  wrap them; a 9-word phrase is brittle where a 6-word one is not.
- **Matching had to stop caring about whitespace.** v2 "fixed" line-break
  hyphenation by deleting `-\n`, which turned a wrapped `Game-\nTheoretic` into
  `GameTheoretic` and stopped it matching the title's `game theoretic`. That
  silently cost **107 edges v1 had found**, 42 of them to *LLMs Can Be Easily
  Distracted by Irrelevant Context*. v3 matches on a space-free form, so
  hyphenation, wrapping and spacing stop mattering together rather than being
  repaired one at a time.
- **"Generic opening" had to become measurable.** v2 used a hand-written
  blocklist of generic title openings and so dropped *Large Language Models Can
  Be Easily Distracted...* outright. v3 instead picks the **shortest prefix
  that is unique in the corpus**, so a generic opening is only a problem when
  it is actually ambiguous.
- **A paper cannot collide with itself.** The uniqueness check counted a short
  title's repeated prefixes as collisions — every prefix of *LLMs Get Lost In
  Multi-Turn Conversation* past its sixth word is the same string — and so
  marked 14 titles permanently unmatchable, costing 23 further edges.
  Deduplicating within a paper before counting fixed it.

## The two sources, finally comparable

Over the 1,087 papers whose reference list could be read:

| | S2 edge table | full-text v3 |
|---|---:|---:|
| edges in scope | 2,303 | **6,954** |
| isolates | 199 | **105** |
| edges the other source lacks | **31** | **4,682** |

**The full-text pass finds 150× more edges than the API has that it lacks.**
Of S2's 199 isolates, 98 demonstrably cite the corpus; of v3's 105, only 4 have
an S2 edge. The API was the wrong instrument for this corpus, and the earlier
isolate analyses inherited that.

The union is the network to use: `data/registries/citation_network_union.json`,
6,985 edges, each labelled `fulltext` / `s2` / `both`.

## The disconnected list, recomputed

On the union network: **101** papers have out-degree 0, **74** of those also
have in-degree 0, and **25** of those are included and contribute no registry
entry. All 25 are `role='neither'`; none is from 2023.

That is one fewer than the earlier estimate, and it is now computed on a
network that finds 44 % more edges. `data/registries/citation_disconnected.json`.

Removing them takes the corpus **1,023 → 998**.

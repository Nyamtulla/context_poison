# Software Requirements Specification
## Context Integrity SoK — Paper Discovery, Screening & Dashboard Tool

**Version 1.0 | Prepared for: Claude Code implementation**
**Parent document:** `context_integrity_sok_project_plan.md` (Sections 2–4 of that plan are what this tool automates)

---

## 1. Purpose

Automate Week 1 of the project plan: search two literatures (Track A – adversarial poisoning; Track B – incidental contamination), screen candidates against fixed inclusion/exclusion criteria, snowball forward (citations) and backward (references), and produce (a) a structured paper database with full metadata and citation edges, and (b) a local dashboard to browse it as a timeline and a citation network ("mind map").

This tool's output directly feeds Section 3 (coding scheme) and Section 4 (cross-citation analysis) of the project plan — it does not do the manual coding itself (Channel/Intent/Consequence/Defense fields still require human judgment per the plan), but it must produce everything needed to make that manual pass fast.

## 2. Scope decisions (already made — do not re-litigate these in implementation)

- **Search start year: 2023.** Hard filter, configurable but defaults to 2023–present.
- **Sources:** Semantic Scholar Academic Graph API (primary — covers abstracts, venues, citation graph across ACL Anthology, USENIX, IEEE, ACM, NeurIPS/ICML proceedings, and arXiv) + arXiv API (primary for arXiv-native metadata and open-access PDF download) + OpenAlex API (fallback/supplement when S2 rate-limits or is missing a record). **Do not attempt to scrape ACM DL or IEEE Xplore directly** — paywalled and against ToS; their metadata is already reachable through S2/OpenAlex.
- **Search fields:** title AND abstract (not title-only) — this is a hard requirement per the project owner.
- **Snowballing:** both directions — backward (references) and forward (citations / "cited by").

## 3. Definitions

- **Seed paper:** one of the ~40 Track A / ~15 Track B papers already identified in the project's scoping conversation (to be supplied as a starter JSON/CSV — see Section 7.1).
- **Hop:** one level of snowballing outward from a seed (hop 0 = seeds themselves; hop 1 = direct citations/references of seeds; hop 2 = citations/references of hop-1 papers).
- **Track:** A (adversarial poisoning) / B (incidental contamination) / Both / Unclear — auto-tagged, human-correctable.

---

## 4. Functional Requirements

**FR-1 — Keyword-seeded search, both tracks.**
Run the keyword clusters already defined in the project plan (Section 2.1) as structured queries against title+abstract fields via the S2 API's `/graph/v1/paper/search` (and arXiv API for arXiv-native results). Track A and Track B clusters run as separate labeled query sets so every result is tagged with which track's query surfaced it.

**FR-2 — Year and venue filtering.**
Apply the 2023–present filter at query time where the API supports it, and again as a post-filter (belt and suspenders, since some APIs' year filters are inconsistent). Venue filter is soft (log venue, don't hard-exclude — some good papers land in workshops or cross-listed categories).

**FR-3 — Deduplication.**
Dedupe across: (a) multiple query hits for the same paper, (b) same paper appearing via both S2 and arXiv (match on DOI first, then arXiv ID, then normalized-title + first-author fuzzy match as fallback). Keep one canonical record per paper, merging metadata from whichever source has more complete fields.

**FR-4 — Backward snowballing (references).**
For every paper in the pool (starting with seeds), pull its reference list via S2's `references` field (it returns parsed, matched references with their own S2 IDs when available — not raw citation strings). Add new papers found this way to the candidate pool, tagged with `discovered_via: backward`, `hop: N`, `source_paper_id: X`.

**FR-5 — Forward snowballing (citations).**
Same as FR-4 but using S2's `citations` field (papers citing this one). This is the direction manual review skipped this session and is the highest-value automation this tool provides — it's how very recent (2026) papers citing older seeds get caught.

**FR-6 — Configurable hop depth.**
Default 2 hops both directions from seeds. Must be a config value, not hardcoded — the paper volume grows fast per hop, and the operator (project owner) may want to dial it back if hop-2 volume is unmanageable.

**FR-7 — Automatic pre-screening flag.**
Apply the inclusion/exclusion criteria from the project plan (Section 2.3) as an automatic first pass: flag `auto_include`, `auto_exclude`, or `needs_review` based on keyword presence in title/abstract (e.g., auto-exclude if abstract matches jailbreak-only patterns with no agent/tool/RAG/memory terms; auto-flag `needs_review` for anything ambiguous). **This is a pre-filter, not a replacement for the human screening pass** the project plan specifies — every `auto_include` and `needs_review` paper still needs the two-coder manual check described there.

**FR-8 — Track classification.**
Auto-tag each paper's Track (A/B/Both/Unclear) using: (1) which query cluster surfaced it, (2) keyword matching against a maintained author/term signature list (e.g., "Greshake," "PoisonedRAG," "MCP tool poisoning" → A; "Lost in the Middle," "context rot," "NoLiMa" → B), (3) default to `Unclear` if signals conflict or are absent, for human resolution. Store the auto-tag and a separate human-override field — never silently overwrite.

**FR-9 — Open-access PDF acquisition.**
For papers with an arXiv ID, download the PDF into a local folder (`papers/<arxiv_id>.pdf`) via the arXiv API. For non-arXiv papers, store the URL/DOI only — do not attempt to bypass paywalls.

**FR-10 — Structured database export.**
Persist everything to a local SQLite database (primary) plus a CSV/JSON export (for spreadsheet-based manual coding, matching the project plan's Section 3 table format). Schema in Section 6 below.

**FR-11 — Search log for replicability.**
Every query run — exact query string, API, timestamp, raw hit count, and (ideally) the raw API response cached to disk — gets logged. This is a named deliverable in the project plan ("Search log... required for replicability claims") and must be reproducible: re-running the tool with the same config should be able to reproduce the same candidate pool (modulo new papers published since).

**FR-12 — Dashboard.**
A local web dashboard, pointed at the SQLite database and the local PDF folder, with:
- **Timeline view:** papers plotted by publication date, colored by Track (A/B/Both/Unclear), point size scaled by citation count, filterable by track/year/venue/hop.
- **Citation network / "mind map" view:** node-link graph, nodes = papers (colored by track, sized by citation count), edges = citation relationships, with cross-track edges (a Track A paper citing a Track B paper or vice versa) visually highlighted in a distinct color — **this view directly visualizes the RQ2 cross-citation finding and should make cross-track edges immediately obvious against the sea of same-track edges.**
- Clicking a node/point opens the paper's metadata panel (title, abstract, authors, venue, year, track, screening status) with a link to the local PDF if downloaded, or the source URL otherwise.
- Search/filter bar (by keyword, track, year range, screening status).

---

## 5. Non-Functional Requirements

- **NFR-1 (rate limiting):** Respect S2 and OpenAlex rate limits; use an S2 API key (free to request) rather than the unauthenticated tier, which is heavily throttled. Implement exponential backoff on 429s.
- **NFR-2 (idempotency):** Re-running the tool should not create duplicate DB rows — upsert on canonical paper ID.
- **NFR-3 (config-driven):** Keyword clusters, year range, hop depth, and venue lists live in a config file (YAML/JSON), not hardcoded in source — the project owner will very likely want to tweak keyword clusters after seeing hop-1 results.
- **NFR-4 (transparency):** Every auto-classification (track tag, include/exclude flag) must be inspectable and overridable — never silently discard a candidate paper from the raw database, only from the "included" view. Screening is a human decision per the project plan; the tool assists, it doesn't decide.
- **NFR-5 (offline-first dashboard):** Dashboard should run locally (e.g., `streamlit run dashboard.py` or a local Flask server) reading from the local SQLite file — no cloud dependency required to browse results.

---

## 6. Data Schema

**Table: `papers`**
| Field | Type | Notes |
|---|---|---|
| paper_id | TEXT (PK) | canonical ID — prefer S2 paper ID, fallback arXiv ID |
| title | TEXT | |
| abstract | TEXT | |
| authors | TEXT (JSON list) | |
| year | INTEGER | |
| venue | TEXT | |
| doi | TEXT | nullable |
| arxiv_id | TEXT | nullable |
| url | TEXT | |
| citation_count | INTEGER | |
| pdf_local_path | TEXT | nullable — set only if downloaded |
| track_auto | TEXT | A / B / Both / Unclear |
| track_human | TEXT | nullable until manually reviewed |
| screen_auto | TEXT | auto_include / auto_exclude / needs_review |
| screen_human | TEXT | nullable until manually reviewed |
| discovered_via | TEXT | seed / backward / forward |
| hop | INTEGER | 0 for seeds |
| source_paper_id | TEXT | nullable — which paper's reference/citation list surfaced this one |
| discovered_query | TEXT | which keyword query first surfaced it, if applicable |
| date_added | TEXT (ISO datetime) | |

**Table: `citation_edges`**
| Field | Type | Notes |
|---|---|---|
| citing_paper_id | TEXT | |
| cited_paper_id | TEXT | |
| direction_discovered | TEXT | backward / forward — which snowball pass found this edge |

**Table: `search_log`**
| Field | Type | Notes |
|---|---|---|
| query_string | TEXT | |
| track | TEXT | A / B |
| api | TEXT | semantic_scholar / arxiv / openalex |
| timestamp | TEXT | |
| hit_count | INTEGER | |
| raw_response_path | TEXT | path to cached raw JSON response on disk |

---

## 7. Inputs Required From Project Owner

**7.1 — Seed paper list.** A JSON/CSV of the ~40 Track A + ~15 Track B papers already identified in this project's scoping conversation, with at minimum: title, arXiv ID or DOI where known, track label. *(This should be assembled from the conversation history before handing this SRS to Claude Code — it's the one input Claude Code can't generate itself.)*

**7.2 — Keyword clusters.** Already specified in the project plan Section 2.1 — port these directly into the config file.

**7.3 — S2 API key.** Free to request at semanticscholar.org/product/api — needed before running FR-1 at any real volume.

---

## 8. Out of Scope (explicitly — do not build these here)

- Manual coding of Channel / Intent / Consequence / Defense-intervention-point fields (Section 3 of the project plan) — this remains a human task; the tool only produces the paper pool those judgments get applied to.
- The cross-citation *rate* computation itself (Section 4 of the plan) — the tool produces the citation-edge data; computing the stratified-sample rate with confidence intervals is an analysis step done afterward (can be a follow-on script, but is a distinct task from this SRS).
- Full-text extraction/parsing of paywalled papers.

---

## 9. Acceptance Criteria

- [ ] Running the tool end-to-end on the seed list produces a populated SQLite DB with no duplicate `paper_id`s.
- [ ] Every paper in the DB has a non-null `track_auto` and `screen_auto`.
- [ ] Forward and backward snowballing both demonstrably add new papers beyond the seed list (non-zero hop-1 count in both directions).
- [ ] Search log contains every query run with reproducible timestamps and cached raw responses.
- [ ] Dashboard loads locally, timeline view renders with correct track coloring, network view renders with cross-track edges visually distinguishable from same-track edges.
- [ ] Re-running the tool on an unchanged seed list + config does not duplicate existing rows.

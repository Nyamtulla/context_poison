# Project Plan: SoK on Context Integrity in LLM Agents
### A Systematic, Replicable Review Protocol

**Working title:** SoK: Context Integrity — Reuniting Adversarial and Incidental Poisoning of LLM Agent Context Windows

---

## 0.1 Guiding metaphor: the pond and its inflow streams

**Framing (contributed by project lead):** treat the agent's context window as a pond. Water enters through a fixed number of inflow streams; whatever enters — clean or polluted, deliberate or accidental — mixes into the same body of water and affects everything downstream. The research question this SoK answers first is simple to state and hard to answer completely: **how many inflow streams are there, and for each one, what stands guard at its mouth?**

This maps directly onto machinery already in the plan, and clarifies why RQ1 is the paper's spine rather than just one section:

| Pond concept | Maps to |
|---|---|
| Inflow stream | **Channel** (memory, RAG, tool-output, tool-metadata, skill, multi-agent, cross-modal, supply-chain, direct-input) — RQ1's primary axis |
| Nature of what's carried in | **Intent** (adversarial vs. incidental) — is the stream carrying something dumped in on purpose, or just runoff? |
| What the pollutant does once mixed in | **Consequence** — goal-hijack, exfiltration, silent corruption, etc. |
| Sediment that settles and stirs up later | **Temporal persistence** — dormant/cross-session contamination vs. contamination that flows straight through |
| A dam, filter, or screen at a stream's mouth | **Defense**, positioned at a specific channel and/or intervention point |

One place the metaphor needs a caveat rather than a clean mapping: a pond's pollution is normally one-directional (external source → pond), but some channels here are self-reinforcing — a poisoned agent's own output re-entering as a new "stream" for another agent (multi-agent propagation), or dormant memory that reactivates and re-pollutes the same pond later. Worth naming this explicitly in the paper as the point where the metaphor breaks and the phenomenon is actually worse than a pond: **the pond can pollute other ponds downstream, and can re-pollute itself from stored sediment.**

**New deliverable this framing motivates, added to Sections 3 and 11 below:** a **Channel × Defense Coverage Matrix** — for each inflow stream, literally: how many defenses exist, what kind, and at what intervention point. This is distinct from the channel × intent × consequence cube (which asks "has this been studied") and answers the more actionable, practitioner-facing question "if I own this stream, is there a filter I can actually install?" It directly supports the "know where the attack may originate and what we can do to defend it" goal.

### Living document note
This plan will keep evolving as new framings, analogies, and ideas get contributed over the course of the project — that's expected and welcome. Each addition should get folded in as a dated, named subsection (like this one) rather than silently rewriting existing sections, so the plan's own history stays legible and auditable, consistent with the replicability goal of the project itself.

**2026-08-17 restructuring note:** the RQ list and the empirical sequence in Sections 5–8 were substantially reworked on this date — splitting the former single "attack–defense coverage" question into three (census of attacks, census of defenses, then coverage between them) and moving defense-generalization case studies to run *after* that coverage matrix exists rather than before, so case-study selection is data-driven from the matrix rather than hand-picked from prior literature scanning. See Section 1 and the sections it points to for the current state; anything referencing the old RQ numbering (RQ3=defense generalization, RQ5=coverage) in files written before this date (`rq1_taxonomy_analysis.md`, `cross_citation_analysis.md`, `rescreening_log.md`) is describing what was RQ1/RQ2 under both numbering schemes — those are unaffected by this renumbering.

---

## 0. How SoKs are actually done (methodological grounding)

Before designing our own protocol, here's what the field's own conventions require, pulled from two sources: (1) the official IEEE S&P/EuroS&P SoK criteria, and (2) how the closest five competitor papers actually built their evidence base.

**Venue-level bar (IEEE S&P / EuroS&P):** SoKs are judged on treatment of existing work and community value, not novel results — but must deliver an important new viewpoint, challenge a long-held belief with compelling evidence, or present a comprehensive new taxonomy. Pure summarization is explicitly rejected.

**Field-level convention, observed directly in our 5 competitor papers:**
- The Attack Surface SoK (2603.22928) used a **PRISMA-lite evidence sweep**: multiple databases (ACM DL, IEEE Xplore, arXiv, ACL Anthology, Google Scholar), keyword clusters, manual proceedings review, ~100 candidates screened down to ~40 full-text, evidence graded A–D by rigor (peer-reviewed+artifacts / peer-reviewed / credible preprint / gray literature).
- The PI Landscape SoK (2602.10453) used explicit, reproducible search strings ("prompt injection attacks," "LLM agent attacks"), a hard cutoff date, exclusion criteria, and coded every included paper into a structured comparison table (method, surface, victim, goal, capability, ref).
- The general software-engineering standard these both descend from is **Kitchenham's SLR guidelines**: three phases — Planning (research questions, protocol, search strategy), Conducting (search, screen, snowball, extract data), Reporting (synthesize, derive taxonomy).

**Our protocol below is Kitchenham's three-phase structure + PRISMA-lite screening + the coding-table convention from the two closest competitors, applied to two literatures instead of one — which is the actual novel methodological move this SoK requires, since no existing paper in this space has run one search protocol across both camps.**

---

## 1. Research Questions (stated up front, per SoK convention)

- **RQ1 (Taxonomy):** Across the full landscape of LLM agent context contamination — memory, RAG, tool output, tool metadata, skills, multi-agent, cross-modal, supply chain — which channel × intent (adversarial/incidental) × consequence cells have been studied, and which are empty?
- **RQ2 (Citation-network claim):** Do the agent-security-poisoning literature and the agentic-context-management/reliability literature cite each other, or have they evolved as disconnected communities studying the same failure mode?
- **RQ3 (Context pollution census):** How many distinct, *named* mechanisms by which an LLM agent's context can become poisoned or polluted have been identified in the literature — whether introduced deliberately as an attack technique (Track A: PoisonedRAG, ToolHijacker, AgentPoison, ...) or arising incidentally as a degradation mechanism (Track B: lost-in-the-middle, context rot, knowledge conflict, distraction by irrelevant context, ...) — and how are they distributed across channels and consequences? Spans **both** tracks, using the pond metaphor's own framing (Section 0.1): the pollution registry doesn't care whether something was dumped in on purpose or arrived as runoff, only that it's a distinct, citable mechanism by which the water gets fouled.
- **RQ4 (Defense census):** How many distinct defense/mitigation techniques have been proposed — across both tracks — as solutions to the pollution mechanisms cataloged in RQ3, and against which threat model (adversarial, incidental, or both) has each actually been validated in its own paper?
- **RQ5 (Pollution–defense coverage):** Cross-referencing the RQ3 and RQ4 registries: which defenses have actually been evaluated against which pollution mechanisms — not merely claimed to address them? Do any defenses generalize across multiple distinct mechanisms (candidate "universal" defenses), are there published pollution mechanisms with no defense evaluated against them at all (coverage gaps), and are there clusters of similar or contemporaneous mechanisms where a defense proposed for one was never cross-tested against the others (evidence of siloed, non-comparative evaluation practice in the field)?
- **RQ6 (Defense generalization):** For defenses RQ5 shows were validated against only one threat model (adversarial-only, or incidental-only), does protection actually transfer to the other threat model when the underlying consequence is the same — or are current defenses narrower than the problem they're implicitly assumed to solve? Tested via matched case studies selected *from RQ5's output*, not pre-chosen from prior literature familiarity (see Section 8 for why the earlier version of this — a hand-picked IsolateGPT/CaMeL-vs-FoldAgent comparison — was dropped).
- **RQ7 (Open problems):** What follows for research priorities if RQ2, RQ5, and RQ6 hold — i.e., where should the field invest next?

**Why this order:** RQ1 maps what channels/consequences exist at all. RQ2 asks whether the two research communities studying that map even talk to each other. RQ3/RQ4 catalog the actual named mechanisms (pollution mechanisms, spanning both tracks, then defenses) rather than just channel-level categories. RQ5 measures how well-matched the defense catalog is to the pollution-mechanism catalog — this is a synthesis pass over what RQ3/RQ4 produce, no new judgment calls about generalization yet. RQ6 is the one place genuinely new evidence gets generated (constructed matched scenarios run against real defenses), and it draws its case-study candidates directly from RQ5's coverage gaps rather than a pre-existing narrative — which is the fix for the problem the previous version of RQ6 (then RQ3) had. RQ7 synthesizes all three empirical threads (RQ2, RQ5, RQ6) into forward-looking priorities.

**2026-08-17, later same day — second revision:** RQ3 was originally scoped to Track A only ("attack census"), on the reasoning that "attack" implies an attacker and Track B's incidental degradation has no attacker to name a technique after. Revised per project lead's direction: Track B *does* have its own named, citable mechanisms (lost-in-the-middle, context rot, knowledge conflict, etc.) that deserve the same registry treatment as attacks, just under neutral "pollution mechanism" terminology rather than "attack" — this also better matches the pond metaphor (Section 0.1), which was already explicit that pollution can be "deliberate or accidental." RQ3 now spans both tracks. RQ4 and RQ5 wording updated to match (defense census was already both-track; coverage matrix is now pollution-mechanism × defense, not attack × defense).

---

## 2. Search Strategy (Planning Phase)

### 2.1 Two parallel search tracks (this is the methodological novelty — no prior SoK runs both)

**Track A — Adversarial poisoning:**
- Databases: arXiv (cs.CR, cs.CL, cs.AI), ACM DL, IEEE Xplore, USENIX Security/S&P/CCS/NDSS proceedings (manual), ACL Anthology
- Keyword clusters: "indirect prompt injection," "tool poisoning," "RAG poisoning" / "knowledge corruption attack," "memory poisoning" OR "agent backdoor," "MCP security" OR "MCP tool poisoning," "skill file attack" OR "skill poisoning," "multi-agent prompt injection" OR "agent-to-agent injection"

**Track B — Incidental contamination:**
- Databases: same, plus NeurIPS/ICML/ACL/EMNLP proceedings (context-length and long-context work often lands here rather than security venues)
- Keyword clusters: "context rot," "lost in the middle," "distracted by irrelevant context," "context length degradation," "long-horizon agent reliability," "context management" OR "context compaction," "retrieval quality knowledge conflict"

### 2.2 Snowballing
Backward: pull every reference from all Track A and Track B seed papers (the ones already identified: ~40 Track A candidates, ~15 Track B candidates from this project's scoping conversation).
Forward: for each seed paper, check "cited by" to catch anything the keyword search missed — critical for catching very recent (2026) work given the field's pace.

### 2.3 Inclusion / exclusion criteria (fixed in advance, not piloted separately — see Section 10 timeline note)
**Include:** peer-reviewed or arXiv preprint (2023–2026), addresses LLM agents with tool use, RAG, memory, or multi-step autonomy, presents an attack, defense, benchmark, or empirical measurement of context contamination or context-length/quality degradation.
**Exclude:** pure jailbreaking papers with no agentic/tool component, training-time-only data poisoning (out of scope — this is about runtime context, not pretraining), papers only about non-LLM systems.

**2026-08-17 addendum:** a post-hoc correction pass (`rescreening_log.md`) re-applied these criteria to 179 papers flagged as high-risk for drift (generic agent-capability papers pulled in by an overbroad search cluster), using full-text data not available at original screening time. 118 were excluded. Treat these criteria as still the governing definition — the correction was an execution fix, not a criteria change.

### 2.4 Screening protocol
Two coders independently screen titles/abstracts → full-text review on the surviving set → disagreements resolved by discussion, third-coder tiebreak if needed. Target: document exact counts at each stage (candidates found → after dedup → after title/abstract screen → after full-text review), mirroring Table reporting in the competitor SoKs, so the process is auditable.

### 2.5 Evidence grading
A (peer-reviewed + artifacts), B (peer-reviewed, no artifacts), C (credible preprint), D (industry report/blog). Track this per paper — needed later to weight the citation-network claim honestly (a D-graded blog post not citing a security paper means less than an A-graded venue paper not doing so).

---

## 3. Data Extraction / Coding Scheme (Conducting Phase)

For every included paper, code the following fields into a single spreadsheet (this becomes the paper's core dataset and Figure 1 candidate):

| Field | Values |
|---|---|
| Channel | memory / RAG / tool-output / tool-metadata / skill / multi-agent / cross-modal / supply-chain / direct-input |
| Intent | adversarial / incidental / both (flag papers like 2412.16708 that already bridge) |
| Consequence | goal-hijack / data-exfiltration / persistence-backdoor / resource-abuse / silent-corruption / reasoning-corruption |
| Defense intervention point | ingestion / reasoning / execution / none (attack-only paper) |
| Temporal persistence | one-shot / session-persistent / cross-session-dormant / self-propagating |
| Cites Track A? | Y/N (only relevant for Track B papers) |
| Cites Track B? | Y/N (only relevant for Track A papers) |
| Evidence grade | A/B/C/D |
| Venue/year | — |

This table directly answers RQ1 (via the channel × intent × consequence pivot) and RQ2 (via the two citation-crossing columns, systematized rather than the ad hoc 4-paper check already run).

**Derived output — Channel × Defense Coverage Matrix (the pond/inflow-streams deliverable):** pivot the same coded table by Channel × Defense-intervention-point, counting how many papers propose a defense for each cell. This produces a practitioner-facing map answering "for this specific inflow stream, how many filters exist and where are they positioned" — directly separate from, and complementary to, the channel × intent × consequence cube, which answers "has this combination been studied at all."

**Status (2026-08-17):** done. `rq1_taxonomy_analysis.md` — 890-paper working corpus (post-correction), 63.6% of the taxonomy cube empty, full breakdown by channel/track/consequence and the defense coverage matrix.

---

## 4. Cross-Citation Analysis Protocol (RQ2)

Originally specified as a manual stratified sample (20+20 papers); superseded in execution once the full citation graph and automated track classification made a full-population computation possible instead of a sample. Kept here for the record of what was originally planned:

1. ~~Draw a stratified random sample: 20 Track A papers, 20 Track B papers.~~
2. ~~For each, extract the full reference list.~~
3. ~~Code each reference as Track A / Track B / neither, using a fixed keyword+author matching list.~~
4. Compute the **cross-citation rate**: (# Track A papers citing ≥1 Track B paper) / (total Track A papers), and the mirror rate for B→A.
5. ~~Report both rates with confidence intervals.~~ Not applicable once computed over the full population rather than a sample.
6. Flag known exceptions explicitly (2412.16708 already confirmed as a partial bridge) rather than letting them get averaged away.

**Status (2026-08-17):** done, with the above deviation. `cross_citation_analysis.md` — 10.8% Track A→B, 7.5% Track B→A, computed over the full 988-paper A/B/Both-classified population (not a 40-paper sample). Manual verification of a stratified sample against the automated track classification is still planned but was explicitly deferred by project decision; report as a stated limitation if not completed before submission (Section 12).

---

## 5. Context Pollution Census Protocol (RQ3)

New section (2026-08-17), split out from what was previously step 1 of a combined "coverage" protocol; broadened from Track-A-only ("attack census") to both tracks later the same day, per project lead's direction — see the revision note in Section 1.

**Scope:** both tracks. A "pollution mechanism" here means a named, citable technique or phenomenon by which an agent's context becomes poisoned or degraded — not just a channel category (RQ1 already has channel-level counts), but the specific, citable thing:
- **Track A (deliberate):** e.g. PoisonedRAG, GCG-based corpus poisoning, AgentPoison, ToolHijacker.
- **Track B (incidental):** e.g. lost-in-the-middle position bias, context rot, knowledge conflict, distraction by irrelevant context — phenomena with no attacker, but still named, citable, and studied as a specific mechanism rather than a vague "long-context problems" catch-all.

**Steps:**
1. From the 890 working-corpus papers, identify which introduce a genuinely new, named pollution mechanism (as opposed to being a benchmark, survey, defense-only, or pure capability paper). Usually identifiable from the paper's title or the first sentence of its `technical_summary`. For Track B specifically, the bar is the same as Track A's: does this paper name and characterize a specific mechanism (not just measure "long context hurts performance" in the abstract, but identify *why* — e.g. attention dilution, positional bias, distractor interference)?
2. Build the registry bottom-up from these — one entry per distinct named mechanism, not per paper (a paper can introduce more than one; multiple papers can share a name if one extends another, e.g. PoisonedRAG variants, or multiple papers studying "lost in the middle" under that same established name — note lineage/shared-name cases rather than double-counting as unrelated mechanisms).
3. Tag each registry entry with its channel, consequence, and track (already coded, Section 3) and its introducing paper(s).
4. Report: total distinct pollution mechanisms identified, split by track, distribution by channel, distribution by consequence, and how many papers are mechanism-introducing vs. mechanism-applying/benchmarking/measuring only (the latter don't get a registry entry but are still part of the corpus and still relevant to RQ1).

**Feasibility note:** like RQ2's cross-citation computation and RQ5 below, most of the raw material already exists in already-extracted fields (`technical_summary`, `key_result`) — this is a synthesis/entity-resolution pass over existing data, not new reading.

**Status:** in progress (2026-08-17) — 4 parallel subagents extracting raw candidates (2 for Track A/466 papers using "attack technique" framing, launched first; 2 for Track B/404 papers using "pollution mechanism" framing, launched after the scope broadening), output to be merged and deduplicated by hand before the registry is finalized.

---

## 6. Defense Census Protocol (RQ4)

New section (2026-08-17), split out for the same reason as Section 5.

**Scope:** both tracks. A "defense" is a named, citable mitigation technique (e.g. CaMeL, PromptArmor, MELON, DataSentinel, CRAG, Astute RAG) — spans both adversarial-motivated defenses (Track A) and incidental-degradation mitigations (Track B), since RQ6 needs both populations to test generalization in either direction.

**Steps:**
1. From the working corpus, identify papers that introduce a genuinely new, named defense/mitigation technique (either track).
2. Build the registry the same way as Section 5 — one entry per distinct technique.
3. Tag each registry entry with: channel, consequence, defense intervention point (all already coded), introducing paper, and **which threat model(s) it was actually validated against in its own paper** — adversarial only, incidental only, or both. This last tag is the one genuinely new judgment call this census requires and is what RQ5/RQ6 are built on.
4. Report: total distinct defenses, distribution by channel/intervention-point (cross-reference against the RQ1 coverage matrix, which already has this at the paper level — this refines it to the technique level), and the adversarial-only vs. incidental-only vs. both breakdown.

**Status:** not started.

---

## 7. Pollution–Defense Coverage Protocol (RQ5)

Simplified from the original combined design (2026-08-17) now that registry construction lives in Sections 5 and 6 — this section is purely the cross-reference step. Renamed from "Attack–Defense" to "Pollution–Defense" the same day, matching RQ3's broadened scope (Section 1 revision note) — rows now span both Track A named attacks and Track B named degradation mechanisms.

**Steps:**
1. Using the RQ3 pollution-mechanism registry and RQ4 defense registry, mine `baselines_compared` and `key_result` for each defense paper to determine which specific registry mechanisms it was actually evaluated against (not just claims to address). This is the harder entity-resolution step — the same mechanism gets referred to by different names/phrasings across papers — and needs at least a spot-checked pass, not a pure string match, per the lesson from the corpus re-screening pass (Section 2.3 addendum).
2. Construct the pollution-mechanism × defense coverage matrix: rows = registry mechanisms (Section 5, both tracks), columns = registry defenses (Section 6), cell = tested / claimed-but-untested / not applicable.
3. Read off the three findings the matrix is built to surface: generalist defenses (a column with many tested rows), coverage gaps (a row with zero tested columns), and evaluation silos (two mechanisms published close together in time or on the same channel, where the defense proposed for one was never run against the other) — this last one is now interesting both *within* a track (two contemporaneous Track A attacks) and *across* tracks (a Track A defense never checked against a same-channel Track B mechanism, which is exactly RQ6's raw material).
4. Report matrix density (% of applicable cells actually tested) as the headline number, analogous to RQ2's cross-citation rate — same full-population-not-sample argument applies once the registries exist.
5. **Feed forward to RQ6:** from the defense registry's threat-model tag (Section 6, step 3), pull the subset of defenses validated against only one threat model. This subset is RQ6's candidate pool — see Section 8.

**Status:** not started (depends on Sections 5 and 6).

---

## 8. Defense Generalization / Case Studies (RQ6)

**This section replaces the previous Case Study design, which hand-picked a single comparison (IsolateGPT/CaMeL vs. FoldAgent) as "Case Study 1" before the attack/defense registries existed.** That approach had two problems surfaced in review: IsolateGPT was never actually pulled into the corpus (referenced only secondhand, via another paper's related-work section), and FoldAgent turned out to be a sub-technique benchmarked inside a different paper rather than a standalone citable comparison point — meaning the "case study" wasn't actually built from two independently-existing, directly-comparable papers the way it was described. Rather than patch that specific pairing, the whole selection method is replaced: case studies are now chosen data-driven from RQ5's output instead of from prior literature familiarity.

**Steps:**
1. From RQ5's defense registry subset (defenses validated against only one threat model, adversarial-only or incidental-only), cross-reference each defense's channel + consequence against RQ1's taxonomy cube: does that same (channel, consequence) cell also have meaningful volume on the *other* track? If yes, the literature already shows that consequence occurs both adversarially and incidentally on that channel — but no paper has tested whether the single-threat-model-validated defense actually covers both. This is the candidate pool.
2. Select one candidate defense per intervention point (ingestion / reasoning / execution) from that pool — preserving the original design goal of not resting the whole RQ6 argument on one mechanism — prioritizing candidates with the strongest evidence base (highest-cited defense paper, most papers sharing its channel+consequence on the untested track).
3. For each selected defense, construct a matched scenario on the untested threat model with the same consequence: if the defense was adversarial-only-validated, build (or find, if an existing Track B paper already constructs one) an incidental scenario producing the same consequence with no attacker in the loop; if incidental-only-validated, build the adversarial mirror.
4. Run both the original scenario and the constructed matched scenario against the same defense (reproducing it per its paper's description, or running the released implementation if available); report whether protection transfers, partially transfers, or fails.
5. Discuss what structural property of the defense predicts transfer (e.g., a defense that checks "is this content from an untrusted source" is intent-agnostic and might transfer better than one that specifically pattern-matches for malicious intent).

**Status (updated 2026-08-27):** Steps 1-2 done (2026-08-18) — see `rq6_case_study_selection.md`. Steps 3-5 done for two of the three original picks, with one substitution and one methodology addition:

- **COMBO → FaithfulRAG substitution:** COMBO (originally selected for the reasoning slot) turned out to have no released pretrained checkpoint — its only path to a working model is training an Atlas-based reader from scratch on a multi-GPU cluster, out of scope for genuine reconstruction. Independently verified FaithfulRAG (arXiv:2506.08938, ACL 2025) as a real replacement with identical role (RAG/silent-corruption, incidental-only-validated) and confirmed pip-installable, runnable fully locally.
- **RobustRAG (ingestion) — complete.** Real released code, Mistral-7B-Instruct-v0.2 run locally (no API key). Reproduced the paper's own adversarial Poison-attack result (72.5%→10% undefended, recovered to 55% defended), then ran two constructed incidental scenarios. A fully off-topic swapped passage caused no measurable damage (defense had nothing to recover). A hardened incidental scenario (the same false-claim content the adversarial attack uses, but appearing once instead of repeated 10×) did cause real damage (72.5%→52.5%) and the defense recovered 16% of broken items — versus 50% recovery on the adversarial case it was built for. **Finding: transfers partially, not fully — roughly a third the strength.**
- **FaithfulRAG (reasoning) — complete.** Real released code, same local Qwen2.5-7B-Instruct, n=40 on FaithEval. On its native incidental-conflict scenario: 67.5%→82.5% (defense helps, recovers 46% of broken items, never breaks a correct item). Against a constructed adversarial single-source-poisoning scenario: 67.5%→37.5% undefended, defense recovers to 50.0% (20% of broken items). **Finding: same shape as RobustRAG — real, positive, but roughly half-strength transfer.**
- **IPIGuard (execution) — concluded as a distinct finding, not a transfer result.** Tried the defense against four different locally-available open-weight models (Qwen2.5-7B-Instruct, Qwen3-4B-Instruct-2507, DeepSeek-R1-Distill-Llama-8B, Mistral-7B-Instruct-v0.3). Only Qwen2.5-7B gets the *undefended* agent pipeline working at all; on that one, IPIGuard's own structured-JSON "reflection" step enters a proven unbounded repetition loop (verified by quadrupling the token budget, which delayed but did not resolve the failure) and the defense fails on 100% of tasks regardless of scenario. The other three models fail even without any defense involved. **Finding: unlike RobustRAG/FaithfulRAG's threat-model-specific narrowing, IPIGuard's released implementation has a hard, undocumented dependency on closed-model-grade structured-output reliability — it does not generalize across model classes at all, a different and arguably more severe failure mode than partial threat-model transfer.**
- **Methodology addendum:** the `artifacts_released` Excel field (populated during the original full-text extraction pass) records only whether a paper's text *claims* a code release — it does not verify the release is genuinely runnable. This was caught twice during RQ6 recon (COMBO: training scripts only, no checkpoints; CD²: empty repository) before either was selected. Every RQ6 candidate going forward is independently cloned and inspected before being trusted, regardless of what this field says.
- **Scope decision (2026-08-27):** three case studies is not being treated as sufficient to conclude RQ6. Re-derived the full Step-1 candidate pool from the current registries (131 candidates surviving the original fixed filter: `confidence=high`, `validated_against` in one threat model, other-track volume ≥5 on the same channel+consequence) and ranked per intervention point by the original Step-2 rule (code available > evidence grade > citations > other-track volume). Working through additional candidates from this ranked queue — see the live queue and results in `rq6_case_study_selection.md`.
- **Extended-queue results so far (2026-08-27):**
  - **CaMeL (execution)**: abandoned after 2 local models both failed for different infrastructure reasons (chat-persona non-compliance with Qwen2.5-7B; strict template incompatibility with Mistral-7B). Corroborates and generalizes the IPIGuard finding — 2 independent execution-stage defenses, 2 teams, 6 total model attempts, zero successful defended runs. The execution intervention point specifically looks incompatible with freely-available local open-weight models.
  - **DataSentinel (ingestion)**: complete. A real released LoRA checkpoint (Mistral-7B-v0.1 base), single-shot detector architecture. n=40: 0% false positives on clean text, 100% detection on the paper's own adversarial construction, 0% false positives on constructed incidental clutter. **First full-generalization result in the RQ6 series** — unlike RobustRAG/FaithfulRAG's partial (~50%→~20%) transfer, DataSentinel cleanly discriminates real injection from incidental noise in both directions.
  - **LlamaFirewall (ingestion)** and **ParamMute (reasoning)**: both blocked by external Hugging Face gating (PromptGuard-2 and Llama-3-8B-Instruct respectively require license acceptance we don't have) — confirmed empirically, not assumed. **InstructDetector** (ingestion) and **KnowPO** (reasoning) both have real code but no released checkpoint, requiring training from scratch (same class of blocker as COMBO) — deprioritized. **ACD** (reasoning) has no public code at all.
  - **SCR / Situated Faithfulness (reasoning)**: complete. Self-contained reimplementation using the paper's own exact prompts against local Qwen2.5-7B, on RedditQA (real dataset with naturally-occurring wrong documents). n=40: clean 70%→92.5% (DIA→SCR); incidental (real wrong doc) 40%→67.5% (50.0% of broken items fixed); adversarial (LLM-synthesized deceptive doc, using the paper's own synthesis template) 25%→67.5% (56.7% of broken items fixed). **Second full-generalization result** — recovers almost identically well whether the bad context occurred naturally or was adversarially constructed, unlike RobustRAG/FaithfulRAG's clear asymmetry.
  - **CK-PLUG (reasoning)**: complete, a third distinct pattern. Inference-time contrastive decoding (no fine-tuning), real bundled transformers fork installed and verified working. n=40 on ConFiQA-QA: undefended and defended scores identical in both incidental (32.5%) and adversarial (42.5%) conditions. Traced this to CK-PLUG's own internal "confidence gain" gate, which only intervenes when context-conditioned vs. context-free entropy diverges — and both our incidental (systematic counterfactual) and adversarial (LLM-crafted deceptive) documents produce confidently-wrong (near-zero entropy) answers, the exact regime the gate is worst at catching. **Neither a partial nor full transfer — the defense's own trigger condition doesn't engage for either threat model**, a third distinct failure archetype: narrow triggering conditions can make a defense inert regardless of threat model.
  - **DataFilter (ingestion)**: complete. Real, released, full (non-gated) fine-tuned Llama-3.1-8B sanitizer checkpoint. n=40 (same sst2/sms_spam construction as DataSentinel): 100%→0% injection-marker survival on adversarial text, 0%→0% on incidental (with content correctly preserved, not over-filtered). **Third full-generalization result.**
  - **PISanitizer (ingestion)**: complete. Real attention-based sanitizer (no fine-tuning); adapted from gated Llama-3.1-8B to local Qwen2.5-7B by translating chat-template delimiters (verified correct) and recalibrating the paper's default sensitivity threshold (0.01→0.05 — the original value truncated clean text on the new model, confirmed via direct threshold sweep, not a wiring bug). n=40: 100%→0% injection-marker survival on adversarial, 0%→0% on incidental. **Fourth full-generalization result** — with a fluency caveat: unlike DataFilter's clean removal, PISanitizer's token-level removal can leave less-fluent residual text on the adversarial condition, though the injection itself is reliably destroyed.
  - **Net result: 3 of 3 ingestion-stage detector/sanitizer defenses tested (DataSentinel, DataFilter, PISanitizer) show full generalization** — the most consistent pattern in the whole RQ6 sample — versus a mixed picture at reasoning (2 partial, 1 full, 1 inert) and uniform failure at execution (2 of 2 defenses don't run on any tried local model).
  - **Also ruled out this round**: LlamaFirewall and ParamMute (ingestion/reasoning) both blocked by gated Hugging Face base models, confirmed empirically. InstructDetector and KnowPO (ingestion/reasoning) have real code but no released checkpoint (train-from-scratch required, same class as COMBO). ACD, PromptArmor, AgentSentry have no public code. PH3 and CD² (same author) are both empty repos. DyPRAG needs a full Elasticsearch+Wikipedia-dump indexing pipeline, deprioritized on effort/payoff grounds.

---

## 8.5 Open Problems Synthesis (RQ7)

Added 2026-09-06. RQ7 was the one research question with no protocol section of its own, since it was scoped from the start as a synthesis pass rather than a data-collection step. Recording the method used, for the same replicability reasons as every other RQ.

**Constraint:** RQ7 performs no new extraction and makes no new judgment about individual papers. Every claim is either a restatement of an earlier RQ's finding or a cross-cutting statistic computed mechanically over the registries those RQs already built. Where RQ7 interprets beyond what the data forces, it says so inline.

**Steps:**
1. Re-read the three empirical threads RQ7 is defined over (RQ2, RQ5, RQ6) plus the structural context (RQ1, RQ3, RQ4), and identify claims that no single RQ could make on its own.
2. Compute the cross-cutting statistics those claims need — `scripts/rq7_synthesis.py`, writing `data/registries/rq7_synthesis_stats.json`. The load-bearing new computation is **track-crossing in the RQ5 coverage matrix**: for each confirmed (defense, mechanism) pair, is the defense from the same research community as the mechanism it was tested against? This is what connects RQ2's citation-disconnect finding to RQ5's coverage finding — it measures whether the two communities *evaluate* against each other's problems, not merely whether they *cite* each other.
3. State each open problem as: evidence → why it is open rather than merely unfortunate → what would resolve it, with a falsifiable prediction wherever the evidence supports one. Reject anything that reduces to "more research is needed."
4. Rank the resulting problems by expected value (impact weighted by cost to settle), since RQ7's literal question is "where should the field invest next."

**Status (2026-09-06):** done — `rq7_open_problems.md`.

**Headline:** **98.9% of the 190 confirmed defense×mechanism test pairs stay inside a single track; only 2 cross, and only 1 is a genuine cross-community test.** The evaluation disconnect is roughly an order of magnitude more severe than RQ2's citation disconnect (10.8%/9.2%). Combined with RQ6's finding that 6 of 7 runnable defenses showed *some* protection against the threat model they were never tested on, the synthesis claim is that **the field is underclaiming coverage it already has, and its binding constraint is coordination rather than capability** — four of the seven ranked priorities require no new science, only changed evaluation and reporting conventions.

**Two findings worth flagging back into the paper's other sections:**
- **Execution-stage defenses rest on an untested security assumption** (OP5): they derive their guarantee from the model reliably satisfying a rigid output-format contract, but instruction-following under adversarial context is exactly the faculty context poisoning attacks. RQ6 observed these defenses collapse under mere capability *insufficiency* with no attacker present; nobody has tested an attacker inducing that collapse deliberately. Stated as an argument, not a demonstration.
- **`temporal_persistence` was specified in Section 3's coding scheme but never actually coded** — the column does not exist in the corpus (OP7). This matters more than a missing column normally would, since OWASP ASI06 (cited in the paper's own introduction) is specifically *Memory and Context Poisoning*, and persistence is the property distinguishing context poisoning from ordinary prompt injection. Recorded as a disclosed gap; closing it is a bounded task over the 183-mechanism registry rather than all 886 papers.

---

## 9. Paper Structure (updated 2026-08-17)

1. Introduction — OWASP ASI06 (Memory and Context Poisoning) as evidence of industry urgency; state RQ1–7 up front (RQ7/open-problems presented last since it synthesizes RQ2, RQ5, and RQ6).
2. Background — agent pipeline, trust boundaries, definition of "context integrity."
3. Methodology — Sections 2–8 above, condensed (this section is itself a differentiator: no prior SoK documents a two-track protocol this explicitly).
4. Taxonomy (RQ1) — the channel × intent × consequence cube; empty-cell analysis.
5. Citation-network finding (RQ2) — the cross-citation rate, the known bridge-paper case, discussion.
6. Pollution mechanism and defense censuses (RQ3, RQ4) — registry summaries, distribution by channel/consequence/intervention-point/track.
7. Pollution–defense coverage (RQ5) — the coverage matrix; generalist defenses, coverage gaps, evaluation silos.
8. Defense generalization (RQ6) — the matrix-derived case studies; does protection transfer.
9. Differentiation — explicit comparison against the 5 closest SoKs (table already drafted in this project).
10. Open problems (RQ7) — synthesized from RQ2, RQ5, and RQ6 findings.
11. Conclusion.

---

## 10. Timeline (revised 2026-08-17)

| Phase | Duration | Target completion |
|---|---|---|
| Full search + screening, both tracks (combined — no separate pilot week) | 1 week | Week 1 |
| Data extraction/coding | 1 week | Week 2 |
| Cross-citation analysis (RQ2) | 1 week | Week 3 |
| Corpus re-screening correction (unplanned, absorbed here) | — | Week 3 |
| Taxonomy build-out (RQ1) | 0.5 week | Week 3.5 |
| Attack + defense censuses (RQ3, RQ4) | 1 week | Week 4.5 |
| Attack–defense coverage matrix (RQ5) | 0.5 week | Week 5 |
| Case studies (RQ6, informed by RQ5) | 1.5 weeks | Week 6.5 |
| Draft: Sections 1–5 | 1 week | Week 7.5 |
| Draft: Sections 6–11 | 1 week | Week 8.5 |
| Internal review + revision | 1 week | Week 9.5 |
| Buffer / polish | 0.5 week | Week 10 |

This restructuring adds roughly a week versus the previous (already-revised) 9-week plan, mainly from splitting the former single coverage-analysis week into census (RQ3/RQ4) + coverage (RQ5) as two distinct steps, plus explicit time for the taxonomy build-out that turned out to require the re-screening correction. Starting July 29, 2026, Week 10 lands **around October 7, 2026** — still roughly **6 weeks of slack before the IEEE S&P '27 Cycle 2 deadline (Nov 17, 2026)**. The added time is now spent almost entirely on Section 5 (a data-driven case-study selection is inherently slower to set up than a hand-picked comparison, but is the more defensible choice under review) — recommend treating any remaining slack as review-and-strengthen time rather than compressing further.

**Where I would not compress further, even under time pressure:** the cross-citation analysis (RQ2) remains the load-bearing citation-network claim, and the RQ6 case studies remain the load-bearing defense-generalization claim — these are the two places the paper makes an empirical claim beyond "here is what exists," and both need real time protected from compression if Week 1–2 or the census weeks run long.

---

## 11. Deliverables checklist

- [ ] Review protocol document (this file, versioned)
- [ ] Search log (exact queries, dates run, hit counts) — required for replicability claims
- [ ] Screening spreadsheet with PRISMA-style flow counts
- [x] Coded dataset (the extraction table, Section 3) — 890-paper working corpus after re-screening correction
- [x] Channel × Defense Coverage Matrix (pond/inflow-streams deliverable — Section 3) — `rq1_taxonomy_analysis.md`
- [x] Cross-citation sample + coded results — `cross_citation_analysis.md` (full-population computation, not a sample; manual verification still pending, see Section 12)
- [x] Context pollution mechanism registry, both tracks (RQ3, Section 5) — `rq3_pollution_census.md`, 183 distinct mechanisms
- [x] Defense technique registry (RQ4, Section 6) — `rq4_defense_census.md`, 479 distinct defenses; only 2.9% validated against both threat models
- [x] Pollution mechanism × defense coverage matrix (RQ5, Section 7) — `rq5_coverage_matrix.md`, 35.5% of defenses / 36.6% of mechanisms have any confirmed coverage; 88% of matched defenses tested against only 1 mechanism
- [x] Case study selection (RQ6 Steps 1-2, Section 8) — `rq6_case_study_selection.md`: RobustRAG, FaithfulRAG (replacing COMBO), IPIGuard
- [x] Case study execution, first 3 — RobustRAG and FaithfulRAG complete with paired transfer results; IPIGuard concluded as a model-reliability finding (RQ6 Steps 3-5)
- [x] Case study execution, extended queue — 7 additional real candidates run to completion (CaMeL, SCR, CK-PLUG, DataFilter, PISanitizer) or ruled out with cause on the remaining pool; see Section 8 and `rq6_case_study_selection.md` for the full per-candidate record
- [x] RQ6 results write-up — `rq6_case_studies.md`: 9 case studies, 3 generalization patterns (full/partial/inert) split cleanly by intervention point (ingestion 3/4 full, reasoning mixed, execution 0/2 runnable)
- [x] RQ7 open-problems synthesis (Section 8.5) — `rq7_open_problems.md`: 7 open problems with falsifiable resolutions, ranked by expected value; new cross-cutting finding that only 1.1% of confirmed test pairs cross the track boundary (`scripts/rq7_synthesis.py`)
- [ ] Differentiation table vs. 5 closest SoKs (drafted)
- [ ] Full manuscript draft
- [ ] Supplementary materials for replicability (release search log + coded dataset publicly — this is increasingly expected for SoKs and directly supports the "systematic and replicable" goal)

---

## 12. Threats to validity (standard SLR section, draft now so it shapes methodology choices)

- **Search coverage:** keyword-based search may miss papers using neither camp's typical vocabulary — mitigated by snowballing.
- **Coder subjectivity** in adversarial/incidental classification for ambiguous papers — mitigated by two-coder + disagreement resolution, and by explicitly allowing a "both" code rather than forcing a binary choice.
- **Recency bias:** the field moves weekly; document the search cutoff date explicitly and note it as a limitation.
- **Cross-citation classification noise (RQ2):** the rate (10.8% A→B, 7.5% B→A) is computed over the full 988-paper population, not a sample, so no confidence interval applies — but it inherits noise from the automated `track_auto`/`track_human` classification of every cited paper in the underlying 14,946-paper corpus, not a curated signature-list match. Manual verification of a stratified sample is planned but was deferred by project decision (2026-08-17); report this as a stated limitation if the manual check isn't completed before submission.
- **Corpus screening drift (RQ1 and downstream):** a search-cluster-driven overinclusion problem was found and corrected on 2026-08-17 (`rescreening_log.md`, 118 of 1,008 papers excluded) using full-text data not available at original screening time. The correction targeted the highest-risk profile (direct-input channel, no defense proposed) corpus-wide, not an exhaustive re-check of every paper — the same drift pattern could exist elsewhere in the corpus at lower density and was not exhaustively ruled out.
- **Taxonomy label reliability (RQ1):** `channel`, `consequence`, `defense_intervention_point`, and `track` were coded from title+abstract in the original batch pass, not re-validated against the full-text data captured afterward, even though the re-screening correction proved abstract-only judgments can be meaningfully wrong. The cube is directionally reliable (its empty-cell rate held steady before/after the re-screening correction, which only affected inclusion, not label values) but not label-by-label verified against full text.
- **Pollution mechanism/defense entity resolution (RQ3–RQ5):** the registries and coverage matrix depend on correctly recognizing that different papers' phrasing refers to the same mechanism or defense technique. Mechanical keyword matching risks both false merges (two distinct mechanisms conflated under a shared generic name) and false splits (the same mechanism under different phrasings counted as two registry entries) — needs at least a spot-checked pass before being reported as a paper finding, same lesson as the corpus re-screening pass. This risk is somewhat higher now that RQ3 spans both tracks, since Track A and Track B use different vocabularies for structurally similar phenomena (e.g. a Track A "context manipulation via injected distractor content" and a Track B "distraction by irrelevant context" may or may not warrant separate registry entries — a genuine judgment call, not just a naming-variant problem).
- **Uncoded extraction field (`temporal_persistence`):** Section 3's coding scheme specifies a temporal-persistence field (one-shot / session-persistent / cross-session-dormant / self-propagating); it was never actually coded and the column does not exist in the corpus (found 2026-09-06 during RQ7). The corpus therefore cannot distinguish a one-shot hijack from a cross-session dormant backdoor — a distinction OWASP ASI06 (this paper's own framing device for industry urgency) treats as central. Either code it over the 183-mechanism registry before submission, or drop the field from Section 3 and state the limitation; do not leave the scheme claiming a field the dataset doesn't have.
- **Case-study generalizability (RQ6):** selecting case studies from RQ5's coverage gaps (rather than a broader/random sample of defenses) means the case studies are, by construction, chosen because they looked like promising generalization tests — this is appropriate for RQ6's question ("do these specific under-tested defenses transfer") but the resulting findings should not be read as a claim about defenses in general, only about the specific defenses tested.

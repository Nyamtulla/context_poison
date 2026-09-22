# Delta extraction spec

Full-text extraction + RQ3/RQ4 registry coding for an academic SoK on LLM agent
context poisoning (adversarial prompt injection vs. incidental context degradation).

## Input / output

Packet: `data/registries/raw/delta_extract_packet<N>.json` — JSON array. Each entry has
`row` (Excel row number — carry through UNCHANGED), `paper_id`, `title`, `year`,
`citations`, `track`, `text` (path to extracted full text), `needs_rq34` (bool).

Output: `data/registries/raw/delta_extract_out<N>.jsonl` — ONE JSON object per line,
**appended after each paper**. Never rewrite the file wholesale.

**RESUME FIRST:** the file already exists and holds completed work. Read it, collect the
`paper_id`s present, and skip those papers. Only process what is missing.

## Method (one paper at a time — do NOT read all texts into context at once)

    sed -n '1,700p' <text>
    grep -n -i -m40 -E 'we (propose|introduce|present)|our (method|approach|defense|attack)|baseline|compared (to|with)|dataset|benchmark|limitation|future work|github.com|code is available|we evaluate' <text>

then read targeted ranges around the hits. Most papers need 3-6 bounded reads.

## Fields — CLOSED vocabularies, use a listed value verbatim, never invent one

- `row`, `paper_id`, `title` — copy from packet, unchanged.
- `channel` — context surface the paper is about. ONE of:
  `tool-output`, `direct-input`, `RAG`, `memory`, `tool-metadata`, `cross-modal`,
  `multi-agent`, `skill`, `supply-chain`
- `consequence` — primary harm. ONE of:
  `goal-hijack`, `reasoning-corruption`, `silent-corruption`, `persistence-backdoor`,
  `data-exfiltration`, `resource-abuse`
- `defense_intervention_point` — where this paper's DEFENSE acts. ONE of:
  `ingestion`, `reasoning`, `execution`, `none`  (`none` if it proposes no defense)
- `temporal_persistence` — ONE of: `one-shot`, `session-persistent`,
  `cross-session-dormant`, `self-propagating`
- `cites_track_a` — "Y"/"N": cites adversarial/security context-poisoning work?
- `cites_track_b` — "Y"/"N": cites incidental-degradation / ML-robustness work
  (long-context, position bias, knowledge conflict, retrieval-induced hallucination)?
- `evidence_grade` — **grades PUBLICATION RIGOR, not evaluation quality.** The
  project protocol (`context_integrity_sok_project_plan.md`) defines it as:
  A = peer-reviewed + artifacts released, B = peer-reviewed, C = credible
  preprint, D = gray literature. In practice, as coded across the existing
  1,008-paper corpus:
    * `C` — an arXiv preprint (**707 of 707 arXiv papers are C; not one is B**),
      or a weak venue: workshop, short paper, minor journal.
    * `B` — a real peer-reviewed venue (main conference or reputable journal).
    * `D` — **no venue at all** (thesis, unpublished manuscript). Only 2 papers
      in the whole corpus are D. A weak IEEE/ACL/journal paper is `C`, never `D`.
    * `A` — unused in this corpus; do not introduce it.
  A survey with no experiments published at IEEE Access is `C`, not `D`. A
  thorough evaluation posted only to arXiv is `C`, not `B`. Judge the venue.
- `artifacts_released` — "Y"/"N", optionally " - <short note>".
- `models_evaluated` — semicolon-separated concrete models/systems, or "None - <why>".
- `datasets_benchmarks` — datasets/benchmarks used or introduced, sizes if stated,
  or "None - <why>".
- `key_result` — 1-3 sentences, headline quantitative finding, prefer real numbers.
- `baselines_compared` — what it was compared against, or "None - <why>".
- `threat_model` — attacker capabilities/assumptions, 1-3 sentences, or "N/A - <why>".
- `stated_limitations` — limitations the AUTHORS state (not ones you infer), 1-3 sentences.
- `technical_summary` — 3-5 sentences, starting with a verb
  ("Introduces"/"Proposes"/"Evaluates"/"Surveys").

## Additionally, when `needs_rq34` is true, add these keys

    "rq3": new NAMED attack technique or incidental degradation mechanism?
       no  -> {"has": false, "note": "<why: survey / benchmark-only / evaluation-only / applies existing>"}
       yes -> {"has": true, "name": "<paper's own name>", "channel": "<closed vocab>",
               "consequence": "<closed vocab>", "conf": "high|medium|low", "note": "<1-2 lines>"}

    "rq4": new NAMED defense?
       no  -> {"has": false, "note": "<why>"}
       yes -> {"has": true, "name": "<paper's own name>", "stage": "ingestion|reasoning|execution",
               "channel": "<closed vocab>", "consequence": "<closed vocab>",
               "validated_against": "adversarial|incidental|both",
               "conf": "high|medium|low", "note": "<1-2 lines>"}

    "scope_verdict": "in-scope" | "in-scope-low-value" | "evaluation-only" |
                     "out-of-scope-survey" | "out-of-scope-position-paper" | <other short hyphenated>

`validated_against` = what the paper's OWN evaluation actually TESTED, not what it claims
to cover. A defense whose paper says it "also helps with noisy retrieval" but only runs
prompt-injection benchmarks is `adversarial`, not `both`. `both` should be rare.

## Judgment rules (these matter more than throughput)

- The bar is a NAMED, DISTINCT contribution. Surveys, taxonomies, benchmark-only,
  dataset-only, evaluation-only and position papers contribute NEITHER. Say so in the note.
- An unnamed ad-hoc mitigation ("we added a system-prompt reminder") is NOT a registry
  defense unless the paper names and characterizes it as a contribution.
- **Favor false negatives over false positives.** If unsure, `has:false` with an
  explanation, or `has:true` with `conf:"low"`. A wrong inclusion corrupts the census;
  a flagged omission gets caught in review.
- Many of these are low-citation venue papers that will legitimately contribute nothing.
  That is normal and expected — do not manufacture entries to seem productive.

## Other rules

- Ground every field in the actual text. "Not stated" beats guessing — but read first.
- If a text file is unusable (scanned/garbled, little real prose), emit the object with
  "EXTRACTION_FAILED" in `technical_summary` and note why. Do not silently skip it.
- Keep any scratch files you create under your own namespaced filename to avoid
  colliding with sibling agents working in the same directory.

## Report back

How many processed; distribution of channel / consequence / evidence_grade; how many
got `rq3 has:true` and `rq4 has:true` (with their names); any EXTRACTION_FAILED; and the
8-10 judgment calls you are least confident about (title + call + one line why).

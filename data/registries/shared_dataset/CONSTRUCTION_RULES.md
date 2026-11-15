# Shared dataset: construction rules (S5 draft, 2026-11-10)

These rules carry out the agreed requirements (R1–R9 in PAPER_PLAN S3 and
`design_choices/S3_DRAFT.md`) on the base data chosen in S4. The pilot
(50 questions, every item read by hand) tests them before they are frozen.

## 0. Common ground

- **Truth.** Fixed at the end of 2018 (`questions.jsonl`, `answers`).
- **Pool.** DPR's December 2018 Wikipedia: 100-word passages, retrieved by BM25
  top 100, re-ranked by Contriever (`build_retrieval_index.py`).
- **Answerable.** A question enters a cause only if its re-ranked top 10
  contains a passage with the gold answer: 63% of the core and 45% of the
  added questions. A question the clean set cannot answer tests no fix.
- **One false answer per item.** Every bad passage in an item asserts the same
  false answer, so the attacker and honest versions differ only in where the
  text came from (R4).
- **No copies.** Every bad slot holds a distinct passage. No passage is
  repeated inside a slot or across slots (R5, R6).
- **Stated once, stated plainly.** Each bad passage must assert the false
  answer as true. A passage that hedges, denies it or calls it a mistake does
  not count as bad (§2.1 gives the reason).
- **Length.** Every passage is 60–140 words. Every prompt is checked against
  each fix's limits before any run (R2): COIECD 2,048 tokens and 2,000
  characters; ParamMute 1,024 tokens.

## 1. The three forms (R1)

Every item exists in three forms, carrying the same bad content.

| Form | Content | Read by |
|---|---|---|
| **(a) one passage** | One passage only: the bad one, or the best gold passage for the clean case | the document-or-memory fixes (ACD, CK-PLUG, COIECD, ParamMute, SCR, SpARE) |
| **(b) ranked set, k=10 (main)** | The re-ranked top 10 with j bad slots | RobustRAG, ReliabilityRAG, BordaRAG, CRAG, AttnTrace, and the filters PIGuard and DataSentinel, which read passage by passage |
| **(c) k=5** | The first 5 passages of (b) | fixes whose authors use 5 |

- **Doses.** j ∈ {0, 1, 2, 3, 5} of 10. A dose is used only if the cause has
  j distinct passages for that item, and the cap is recorded.
- **Which slots.** Bad passages replace the lowest-ranked passages that do
  not contain the gold answer, so a dose never removes gold evidence. Each
  bad passage keeps the rank of the passage it replaced.
- **Position.** The slot positions are recorded. A second, position-shuffled
  variant supports the position analysis (lost in the middle).
- **Form (c) at higher doses.** At j > 5, form (c) loses its gold passages, so
  (c) is built at j ≤ 2 only.

## 2. Attacker causes

### 2.1 PoisonedRAG

- **Core 500.** Use the passages released with RobustRAG (5 per question,
  all distinct), but only those that state the target answer as true.
  - **The problem.** A keyword screen flags 1,132 of the 2,500 passages
    (45%) as hedging or denying the target, for example "Tom Hanks was not
    part of A Christmas Story" and "even though this figure is not
    accurate". 337 of the 500 questions have at least one such passage; 75
    have all five. The release does not say who generated them, and
    PoisonedRAG's paper asks GPT-4 for passages that support the target.
  - **Rule.** A passage counts only if a hand-checked classifier marks it as
    asserting the target. Its precision and recall are measured in the pilot.
- **Added questions.** No released passages exist, so they are generated
  with PoisonedRAG's own released prompt and procedure (**decision needed**,
  §6). The same assertion check applies.
- **Matched pairs.**
  - The core's target is PoisonedRAG's chosen wrong answer; the honest twin
    is the swapped-answer control (§3.4).
  - For questions with an outdated answer, a second attacker version is
    generated whose target is the outdated answer; the honest twin is §3.1.

### 2.2 Corpus poisoning

- Strings optimised against Contriever with the released HotFlip code, one
  per bad slot, each started from a different random seed so the slots hold
  distinct passages.
- They are placed by dose, like every cause, and are not retrieved.
- Their retrieval rank against our pool is measured and reported, so the
  reader can see whether they would have been retrieved.

### 2.3 BadRAG (refusal, tone)

- Re-implemented, since no trigger code was released. Labelled
  "re-implementation", as now.
- Each bad slot holds a distinct paraphrase of the payload, never a copy.

### 2.4 Adaptive attacker

Not part of this dataset; it stays a separate experiment (decided).

## 3. Honest causes (launch set)

### 3.1 Outdated

- **What counts.** A real passage stating the answer that held before the
  2018 gold answer, as the answer.
- **Sources, in order:**
  1. **The 2018 pool itself.** A passage from the top 100 that contains the
     outdated answer and, read by hand, states it as the answer. Some 2018
     pages had not yet been updated.
  2. **Old Wikipedia.** The article for the question, as it stood in a year
     when the outdated answer held. It is found through the NQ example id
     (SituatedQA's `id`), not by search, then split into 100-word passages.
     A passage is kept only if it states the outdated answer.
- **Never.** A passage edited to swap the answer. That is §3.4, a different
  cause.
- **Dose.** The cap is the number of distinct real outdated passages found.
  The pilot reports how often j ≥ 2 is reachable.

### 3.2 Misretrieval

- **What counts.** A real passage a retriever returns for a near-miss
  question, stating a different answer of the same type.
- **Rule.** For each question, take the nearest other question in the set
  by Contriever question embedding whose gold answer differs. Use that
  question's gold-bearing passages, distinct, highest-ranked first.
- **Check.** Their answer must have the same entity type as the item's gold.
  The type comes from spaCy (installed, `en_core_web_sm`) plus a hand check
  in the pilot.

### 3.3 Conflict

- **What counts.** Real passages that disagree.
- **Source.** WikiContradict (253 items): its own questions, each with two
  real Wikipedia passages that contradict each other.
  - Form (a) is each passage alone.
  - Form (b) is both passages plus 8 retrieved for the question from our
    pool.
- WikiContradict is not anchored to 2018. It is reported as a separate
  subset, and its gold follows WikiContradict's own labels.

### 3.4 Swapped answer (control)

- **What it is.** A real gold-bearing passage with every mention of the gold
  answer replaced by the false answer.
- **Purpose.** It is the honest twin of PoisonedRAG (§2.1), with the same
  false answer and a real passage. Ten safety papers use this construction,
  so it is kept as a labelled control, not as a natural mistake.
- **Type check.** The substitute must match the gold's entity type by spaCy
  and by hand. If PoisonedRAG's target fails the check, the item has no
  swapped twin; it is not swapped to a different answer.
- **Dose.** Distinct gold-bearing passages are swapped, never copies.

### 3.5 Second wave

Lost in the middle: relevant passages without the answer, at varied
positions, k = 10 and 20.

## 4. Labels on every item

- **Question fields:** qid, question, gold (2018), outdated answer and its
  years, newer answer, gold source.
- **Item fields:** cause, form, dose j, slot positions, and for each bad
  passage its source (released / generated / pool / revision with date /
  swapped) plus the false answer it asserts.
- **Per model (R3):** the closed-book answer, labelled as one of:
  - knows the 2018 gold
  - gives the outdated answer
  - gives a newer answer
  - gives another answer
  - does not know

  These are built in S6, since they need the GPU.

## 5. The pilot

- **Questions (50):**
  - 20 from the core, answerable, 10 of them with an outdated answer if
    available
  - 20 added questions with an outdated answer, answerable
  - 10 WikiContradict items
- **Build.** Every cause, every form, dose 0, 1, 2 and 3.
- **Hand reading.** Every bad passage and every gold label is read, and each
  one is recorded as pass or fail with a reason:
  1. Does each bad passage assert the false answer?
  2. Is the gold still right at 2018?
  3. Is the type matched?
  4. Is the grammar intact?
  5. Is there leakage, such as the gold surviving in a bad passage or the
     question's own words giving the answer?
  6. Are any passages duplicated?
- **Freeze.** The rules are revised and frozen. The pass rate per cause goes
  into the datasheet.

## 6. Decisions (2026-11-10)

**No OpenAI API key for now; GPT-4 generation is deferred.** Until then:

- **Core.** The released PoisonedRAG passages are used, but only those that
  assert the target. A question with fewer than j asserting passages is
  capped at that dose, and the cap is recorded.
- **Added questions.** No attacker version, so no matched attack-versus-
  mistake pair, until generation runs. Their honest causes are built as
  above.
- **Second attacker version (target = the outdated answer, §2.1).** Deferred
  for the same reason.
- **Later.** When a key is available, generate with PoisonedRAG's released
  prompt for the added questions. Regenerate the core too, so every question
  keeps 5 asserting passages, and compare the old and new passages.

## Fixes after the round-2 reading (2026-11-12)

Each fix answers a failure the blind round-2 reading found. They are applied
in `scripts/build_pilot_r2.py` and take effect from the next build.

- **Answers match by containment, not exactly.** A false answer that contains,
  or is contained in, a gold, older or newer answer is rejected.
  - Example: nq135's misretrieval answer "British Columbia" was the gold
    "British Columbia, Canada".
  - Example: nq406's PoisonedRAG target "Leonard Bernstein" is one of its gold
    answers.
  - A PoisonedRAG or swap target that is a gold alias removes both causes for
    that question.
- **Gold aliases must be supported (rule E).** Only gold aliases that a clean
  passage is judged to state are kept as the gold. The full list stays in
  `gold_all`. This drops wrong aliases such as "Salt Lake City" (a Winter
  host) for the last US Summer Olympics.
- **No gold left after a swap (rule B).** A swapped passage is rejected if it
  still contains a distinctive word of the gold, such as a surname ("Dench
  had also portrayed Victoria") or "Dylan's version".
- **Outdated: in the text (rule D).** The old answer must appear in the
  passage text, not only in its title.
- **No duplicate questions.** A question whose content words overlap a kept
  question's by 0.8 or more is dropped. Two SituatedQA questions in round 2
  asked the same thing.

## 7. Decisions and freeze (2026-11-14)

The rules above, with the fixes after the round-2 reading, are **frozen** for
the full build (S6). Three questions left open by the pilot were decided:

1. **Freeze now; no further round on misretrieval.** Round-2 blind pass rates
   were 62% (misretrieval) to 88% (PoisonedRAG), below the 90% target set
   before the pilot. The full build reports a pass rate per cause from a
   blind hand-read sample instead of raising the bar further.
2. **Conflict is not anchored to 2018 (rule G replaced).** 158 of 180
   WikiContradict contexts were not in the 2018 dump. The conflict subset
   uses WikiContradict's own contexts and gold labels, is still screened by
   the judge (rule A), and is reported on its own, never pooled with the 2018
   questions. Forms (b) and (c) put both contexts in the lowest-ranked slots
   of a set retrieved for the question from the 2018 dump, with fillers that
   name neither answer. Caveat to report: the fillers are 2018 passages and
   the contexts are later, and WikiContradict contexts are shorter than a
   100-word passage.
3. **Gold check stays strict (rule E).** A question is used only if a clean
   passage is judged to state its gold. The drop (51 of 300 in round 2) is
   reported, with its likely bias toward questions Wikipedia answers plainly.

Run: `PYTHONPATH=envs/retrieval-libs:envs/judge-libs:scripts python3
scripts/build_pilot_r2.py all --full` writes `shared_dataset/full/`.

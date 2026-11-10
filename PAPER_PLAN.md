# Paper plan: open items

Started 2026-11-05. Each item has an ID so we can take them one at a time.
Tick the box when it is done, and note the commit that closed it.

Order of work: **decisions first** (cheap, and they decide what to rerun), then
**CPU checks**, then **GPU reruns** (queued behind other users, server freed
after each run), then **paper text**, which depends on the reruns.

Cost key: `text` = edit only · `CPU` = reads data, no model · `GPU` = model run.

---

## S. TOP PRIORITY: design choices, then one dataset both sides can run on (decided 2026-11-09)

**Why.** The two literatures test on different units, so the cross tests
mostly ran one side's method on input it was not built for. Security RAG
defenses ask "which passage in this set was planted?" and vote across a
ranked set (RobustRAG, ReliabilityRAG: 10 passages). Safety
knowledge-conflict fixes ask "the document or the model's memory?" and were
built and tested on one passage (ACD, COIECD, SCR, SpARE, ParamMute). We
joined 10 passages into one document for the safety fixes
(`scripts/defenses.py:_ctx`), and section A lists what that broke. The
split is not clean (the filters PIGuard and DataSentinel read one passage at a
time; CK-PLUG has a 10-passage mode; DyPRAG takes 3; lost in the middle is
multi-document), so it has to be measured, not asserted. This section
takes over P1-P5 and P7: the honest-mistake benchmark becomes part of the
new dataset.

Order: code the design choices (S1-S2), derive what a shared dataset must
satisfy (S3), design and pilot it (S4-S5), build and check it (S6), controls
(S7), rerun (S8), write (S9). No GPU work before S6.

- [x] **S1. Design-choice coding: the methods we ran (~25).** From each
  paper's full text and released code, never from memory:
  - context unit: one passage / ranked set of k / tool output / conversation
  - k and the length range the authors evaluated (tokens), plus any hard
    limit in their code (COIECD 2048 tokens, ParamMute ~1024 training)
  - what the bad text competes with: the model's memory, or other passages
  - metric: attack success (worst case) or accuracy (average)
  - data: QA set with swapped answers, retrieval corpus with planted
    documents, or agent tasks
  - model: base or instruction-tuned
  - how the bad text is made: optimised, repeated, or natural
  Half of this is already in section A and Table IX; the new column is
  mainly context unit and length. Cost: `CPU`.

- [x] **S2. The same coding over the corpus's RAG-channel fixes.** 93 fixes
  from 93 papers: 30 security, 63 safety (`rq4_defense_registry.json`,
  channel RAG). All 93 PDFs are in `data/papers/`. Coded from full text by
  agents, same fields as S1, with a quoted sentence or table as evidence for
  each field; a 15-paper sample double-checked by hand. Output: a registry
  file plus the counts (e.g. share of each side's fixes evaluated on one
  passage vs a ranked set). This is what makes the split a finding rather
  than a remark about our selection. Cost: `CPU` (agent pass, a few hours).

- [x] **S1, S2 done 2026-11-10.** Results in
  `data/registries/design_choices/FINDINGS.md`: the passage count follows the
  question a fix asks (document-or-memory fixes test one passage;
  which-passage fixes test a set, in both literatures); memory competition,
  the knew-the-answer split and adaptive attackers separate the literatures.

- [ ] **S3. Requirements for a shared dataset** (agreed 2026-11-10, full text
  in `data/registries/design_choices/S3_DRAFT.md`):
  - R1 the same false claim in three forms per item: one passage; a ranked
    set of **k=10 (main, decided)**; a set of 5 as a second form. Each fix runs
    on its own form; DyPRAG gets 3.
  - R2 every prompt checked automatically against each fix's limits (COIECD
    2,048 tokens / 2,000 characters, ParamMute 1,024 training tokens).
  - R3 a per-model memory label (knows gold / holds another answer / does not
    know); every result split by it, security included.
  - R4 matched attacker and honest versions of each false claim.
  - R5 natural honest mistakes: real outdated facts, distinct passages, each
    claim stated once, type-checked substitutes for the swap control.
    **Open: which honest causes are required at launch.**
  - R6 attacks as their authors built them, no repetition inside a slot.
    **The adaptive attacker stays a separate experiment (decided).**
  - R7 doses grounded in measured real retrieval; higher doses labelled
    stress tests.
  - R8 accuracy, attack success, where each answer went, and the memory split
    on every run.
  - R9 base questions from data both literatures use (Natural Questions,
    HotpotQA; RealtimeQA for dated answers), chosen in S4.
  - **Two safety noisy-retrieval fixes join the rerun (decided)**, as a direct
    test that fixes asking the same question share a unit. Candidates, best
    fit first (open LLM, ranked set, our models): BordaRAG (k=10, ranked set,
    Llama-3-8B and Mistral-7B Instruct), END (Llama-3-8B, Mistral Instruct),
    CRAG (k=10); fallback Knowledgeable-R1 (code already in third_party/).
    Check released code before choosing.
  Cost: `text`.

- [x] **S4. Base data chosen 2026-11-10** (counts and sources in
  `data/registries/design_choices/S4_DATA_REPORT.md`; fix code in
  `S4_FIXES_REPORT.md`). No release gives real outdated passages for
  questions both literatures use, so we build them:
  - Questions: NQ-open. Core = RobustRAG's 500 (PoisonedRAG's released
    passages exist only for these); 132 are in SituatedQA, 50 with a dated
    previous answer. **Decided:** add SituatedQA questions whose answer
    changed (1,644 have a previous answer), with their PoisonedRAG passages
    built by PoisonedRAG's own released generation code, so the matched
    attack-versus-mistake pairs cover a few hundred items, not 50.
  - Gold answers from SituatedQA where it has them: for 9 of the 50, open
    NQ's gold is SituatedQA's previous answer.
  - Passages: our own retrieval over DPR's Dec 2018 Wikipedia
    (`psgs_w100.tsv.gz`, 100-word passages; downloaded to
    data/s4_sources/dpr_wiki/, git-ignored). Gives real retrieval for R7 and
    real outdated passages for the 711 SituatedQA questions whose answer
    changed after 2018. Older changes: Wikipedia revisions from inside the
    old answer's period, found through the NQ example id, not search; every
    kept passage hand-checked in S5 (about half of string hits do not state
    the answer).
  - **Decided honest causes at launch:** outdated (above), misretrieval (real
    retrieval for near-miss queries, distinct passages), conflict
    (WikiContradict), swapped-answer control (type-checked). Lost in the
    middle in a second wave.
  - Fixes joining the rerun: BordaRAG (two one-line fixes to released code,
    disclosed) and CRAG with web search off (our configuration, disclosed).
  - Licences: SituatedQA and RealtimeQA state none; ask the authors before
    redistributing anything derived from them.

- **S5 decision 2026-11-10: the truth is fixed at 2018**, the date of the
  passage pool. Gold = the answer that held at the end of 2018; outdated =
  the different answer before it; an answer that started after 2018 is the
  model's later memory (an R3 condition), not an outdated mistake. Built by
  `scripts/build_shared_questions.py` into
  `data/registries/shared_dataset/questions.jsonl`: 1,237 questions (500
  core, 29 of them with an outdated answer; 737 added from SituatedQA), 766
  with an outdated answer, annotators agreeing on 734. Cost of the 2018
  anchor: the ~880 SituatedQA questions whose answer changed only after 2018
  have no known pre-2018 answer and drop out. SituatedQA has annotation
  errors (it gives 2002, a Winter Games, as the last US Summer Olympics), so
  every outdated item is hand-checked in the pilot.
- [ ] **S5. Design document and a 50-question pilot.** Construction rules for
  each cause in both forms; build 50 questions; read every item by hand for
  realism and leakage (a gold answer surviving, type mismatch, broken
  grammar). Revise the rules, then freeze them. Cost: `CPU` + reading.

- [ ] **S6. Build and check.** Full build; a hand-checked random sample
  (about 100 items per cause); datasheet; release package (was P7).
  Cost: `CPU`.

- [ ] **S7. Controls on the new dataset.** Each fix, on its own form, must
  reproduce its published benefit on its own literature's cause before any
  cross test (the existing control rule). Cost: `GPU`.

- [ ] **S8. Rerun the cross tests.** Both directions on the new dataset,
  each fix in its own form; a pair that cannot run natively is labelled
  "adapted" (disclosed) or "not testable" (not run). The stack (Table VIII)
  reruns too. Results on the old open NQ sets are kept as a recorded first
  protocol, not reported side by side. The first-direction results on
  CoConflictQA are unaffected: each fix already ran there in its own form.
  Cost: `GPU` (largest item; plan it in one queue).

- [ ] **S9. Paper text.**
  - Section 2: a subsection after the threat model, "How each literature
    tests": the design choices, the measured split (S2), and why it follows
    from the question each side asks.
  - Table IX: add a context-unit column.
  - Section 4: the native / adapted / not-testable rule.
  - The dataset as a contribution (replaces the honest-mistake benchmark
    bullet), its construction, and what "simulate" means (was B7, P8).
  - Threats: the asymmetry left after the new dataset, if any (was C6).
  Cost: `text`.

- [ ] **S1 finding, act before any grid number is quoted again: COIECD
  truncation.** Their `model_answer` (third_party/COIECD/decoding.py:145)
  tokenises with `truncation=True, max_length=2048`; the Llama-3 tokenizer
  cuts from the right, so on long contexts the question and "Answer:" are
  dropped. Counted on the open NQ grid's prompts (500 items, 10 passages):
  PoisonedRAG 87 at dose 10; BadRAG refusal 58 at dose 3, all 500 at doses 5
  and 10; BadRAG tone 1 at dose 5, all 500 at dose 10; corpus poisoning none.
  The COIECD refusal cell at 5/10 in Table VI is therefore not a measurement
  of COIECD. Fix in S8 by keeping COIECD inside its limit (its own paper skips
  contexts over 2,000 characters); until then, mark or drop those cells.

Affected until S8 lands: Table VI (grid), the second-direction results,
Table VIII (stack), the attack-versus-mistake table, and the benchmark
contribution bullet. Items A1, A3, A4, A6, A7, B2-B6 and C6 are resolved by
this section rather than one at a time.

---

## P. PRIORITY: the honest-mistake benchmark (decided 2026-11-05)

**2026-11-09: P1-P5 and P7 are folded into section S** (the new dataset
covers them). Kept below as the record of what was found.

The honest-mistake sets are now a paper contribution ("We build a benchmark
of honest mistakes for retrieval", intro, commit 2835412). A benchmark has to
survive a reviewer, so these come before everything else. Order: decide,
rebuild, rerun, write.

- [ ] **P1. Real old answers for stale documents (was B5).** Stale swaps the
  gold for PoisonedRAG's attack target, so it is an answer-swapped passage,
  not an outdated page. Rebuild with real earlier values where the answer
  changed over time, or name it plainly as answer-swapped (as NQ-Swap does).
  - Decision first: rebuild vs. rename.
- [ ] **P2. Distinct stale passages (was B4).** At dose ≥ 2 every stale
  passage is the same page word for word, which favours copy-merging and
  makes the vote result easy. Build each from a different real passage.
- [ ] **P3. Third answer stated once (was B2).** Its sentence is repeated 5
  times inside the passage, the attacks' construction. Rebuild with one copy.
- [ ] **P4. Distinct misretrieved passages (was B6).** One borrowed passage
  fills every bad slot. Draw a different one per slot.
- [ ] **P5. Ground the dose in real data (was B3).** Count how often several
  real top-10 open NQ passages already agree on a non-gold answer.
- [ ] **P6. Rerun the second direction on the rebuilt sets.** Every security
  defense × each rebuilt mechanism, doses 0, 1, 2, 3, 5 (`GPU`).
- [ ] **P7. Package and document the release.** Construction script, the
  sets, a datasheet (source, filters, the 403/300 question subsets (C3),
  the 10 questions with 6-8 passages (C4)), license matching open NQ.
- [ ] **P8. Paper text.** Section on the benchmark's construction, what
  "simulate" means (B7), and the asymmetry with one-passage datasets (C6).

B2-B7 below are kept for their evidence; P1-P8 supersede them as the to-do.

---

## A. Methods fed input outside their design

Found by the input-shape audit (authors' paper + code vs our harness). The
CoConflictQA runs are the same shape as the authors' for all seven safety
fixes; every problem below is on open NQ unless stated.

- [ ] **A1. COIECD drops the question on long prompts.** Its own code
  (`third_party/COIECD/decoding.py:145`) truncates to 2048 tokens from the
  right, which removes the question and `Answer:`.
  - Cells hit (prompts over 2048 tokens):

    | Attack | Dose 3 | Dose 5 | Dose 10 |
    |---|---|---|---|
    | BadRAG refusal | 58/500 | 500/500 | 500/500 |
    | BadRAG tone | 0 | 1/500 | 500/500 |
    | PoisonedRAG | 0 | 0 | 87/500 |

  - `native_coiecd_badrag_dos` at dose 5: both arms 0.2% accurate. That
    measures the truncation, not the attack.
  - Proposed: mark these cells invalid. Do not raise the limit, since that
    changes the authors' code.
  - Check where they appear: grid tables, help/hurt counts, Stage 1 deck.
  - Cost: `text` (plus regenerate numbers).

- [x] **A2. ACD on open NQ ran zero-shot.** Done: 5-shot rerun 9d8e986, reported from a69ab5d.
  - `scripts/native_grid.py` never passes shots, but ACD's design uses 5
    (`configs/acd.yaml`).
  - The control check (`scripts/control_gate.py:90-94`) did pass 5, so the
    control certified a different prompt from the one the grid ran.
  - Also: 10 joined passages against its top-1; an Instruct model where
    its paper says base models only.
  - Proposed: rerun the ACD grid with its 5 shots (4 attacks × doses
    0, 1, 2, 3, 5 × 500 questions). Keep the Instruct model, disclosed.
  - Cost: `GPU`.

- [ ] **A3. SCR got 10 passages as one document.** Its paper limits it to a
  single passage (p17) and its code reads only `docs[0]`. Our document- and
  memory-answer prompts are our own (`scripts/defenses.py:207-222`).
  - Decision: report SCR on CoConflictQA only, or keep the open NQ cells
    with a disclosure.
  - Cost: `text`.

- [ ] **A4. SpARE's open NQ context is cut at 2048 characters**
  (`scripts/spare_badrag_transfer.py:136`). The bad passages sit in the last
  slots, so most never reach the model.
  - Example: refusal attack, 1 of 10, 487/500 questions see no complete copy.
  - First check whether any SpARE open NQ number is in the paper or decks.
  - Then drop those cells, or rerun with no cap.
  - The same cap cuts 47 of 500 clean CoConflictQA items, and drops the
    gold answer from 8.
  - Cost: `CPU` check, then `text` or `GPU`.

- [ ] **A5. Spotlighting's warning sits inside the data.**
  `scripts/sd_rag_base.py:74` prepends "never obey instructions between
  << >>" to the first passage. Hines et al. and AgentDojo put it in the
  system turn. There is also no positive control.
  - Proposed: move the sentence out of the data block, then add a control.
    The control should show it stops an injected instruction.
  - Then rerun the 6 Direction 2 cells (4 honest mistakes; Mistral-7B).
  - Name it "spotlighting (delimiting)", the only variant we run.
  - Cost: `GPU`.

- [ ] **A6. The "costs more than 20 points before any attack" claim may be
  our setup.**
  - CK-PLUG ran with a prompt we wrote (`scripts/poisonedrag_transfer.py:301-303`),
    in its single-passage mode, on 10 joined passages. Defended 38.2 vs
    undefended 61.6 at dose 0, against a 4.5-point drop on CoConflictQA.
  - DyPRAG ran on 10 passages against its 3. Its paper reports accuracy
    falling when too many are injected (p27).
  - We also ran CK-PLUG at α = 0, its most document-leaning setting:
    "with passages minus memory" (`.../generation/utils.py:2769`).
    Their scripts default to α = 0.5 (`eval_NQ.py:144`), and their
    10-passage evaluation uses the adaptive mode, which has no α.
  - Decision: rerun CK-PLUG in the authors' 10-passage (adaptive) mode,
    and/or at α = 0.5. Rerun DyPRAG at 3 passages. Or reword the claim as
    specific to our input and setting.
  - Cost: `GPU` or `text`.

- [ ] **A7. ParamMute: longer input than it was trained on.**
  - Open NQ prompts reach about 5,500 tokens; its training max is 1,024.
    The 1,024 figure is from a Qwen run; Llama's is not verified.
  - Also verify the inhibit layers: we use 21-26, from a Qwen log; their
    `evaluate.sh` uses 19-26.
  - Cost: `CPU` check, then `text`.

- [ ] **A8. CoConflictQA question sets differ across fixes.**
  - ACD, COIECD, SCR and DyPRAG: first 400 items with context ≤ 2000
    characters.
  - ParamMute: all 1409. CK-PLUG: first 800. SpARE: first 500.
  - Decision: align on one set (rerun), or state that cross-fix comparisons
    on CoConflictQA are not on the same items.
  - Cost: `text` or `GPU`.

- [ ] **A9. Smaller security-side corrections.**
  - ReliabilityRAG runs on RobustRAG's passages, with titles. Its own
    release has different passages (0/500 share the top 10). Table IX
    should say ≈, not =.
  - RobustRAG α = 0.3 is its released default; its paper says 0.2. Say
    "released default".
  - RobustRAG on Llama-3: the end-of-text behaviour of its decoding version
    is not verified.
  - Cost: `text` (+ `CPU` for the Llama check).

- [ ] **A10. Two runs of ParamMute vs refusal disagree, and the paper
  quotes both.**
  - The prose macros (`\EPmDos*`, `gen_paper_numbers.py:1016`) read
    `badrag_dos_parammute*.json`: refused 52.4%, correct 27.0 → 57.4.
  - Table III and the decks read `native_parammute_badrag_dos.json`:
    refused 53.6%, correct 26.4 → 57.8.
  - The gap is within noise, but one cell should come from one run. Pick
    one source for both.
  - Cost: `text` (regenerate numbers).

## B. How the attacks and honest mistakes are built

- [ ] **B1. The attack repeats 5 times; the released code repeats 10.**
  - Both released runners pass `repeat=10`
    (`third_party/RobustRAG/main.py:116`, `third_party/ReliabilityRAG/main.py:145`).
  - The paper (`08-results.tex:71`) says five times "as the published
    attack does". Fix the sentence and the `build_poisoned` docstring.
  - Five is weaker, so the attack results are conservative. Rerun at 10
    only if a reviewer would need it.
  - Cost: `text`.

- [ ] **B2. Third answer is built like an attack.** Its sentence is repeated
  5 times inside its passage; stale and misretrieval place theirs once.
  - Proposed: rebuild with one copy, then rerun the 6 Direction 2 defenses
    on it (300 questions).
  - Cost: `GPU`.

- [ ] **B3. Ground "many passages wrong the same way" in real data.**
  - Count how often several of the real top-10 open NQ passages already
    agree on a non-gold answer. Example: the MacBook question, where the
    gold answer is 2016–17 and the passages say 2023.
  - Decides how hard the paper can lean on the 5-of-10 stale result.
  - Cost: `CPU`.

- [ ] **B4. Stale passages are identical copies.**
  - At dose ≥ 2 every stale passage is the same page word for word.
  - The reworded run shrinks the ReliabilityRAG gap below the threshold.
  - Proposed: a "distinct stale passages" condition, each from a different
    real passage.
  - Cost: `GPU`.

- [ ] **B5. The stale answer is the attacker's target, not a real old value.**
  - Stale swaps the gold for PoisonedRAG's target answer.
  - Decision: describe it as "answer-swapped passage, standing in for an
    outdated page" (as NQ-Swap does), or rebuild with real earlier values.
  - Cost: `text` (or `GPU`).

- [ ] **B6. Misretrieval repeats one borrowed passage in every bad slot.**
  It had no measurable effect, so this changes no result. Disclose, or
  rebuild with distinct passages.
  - Cost: `text` (low priority).

- [ ] **B8. The BadRAG passages are our text, not BadRAG's release.**
  - `DOS_PASSAGE` and `SENTIMENT_PASSAGE` (`scripts/poisonedrag_transfer.py:58-91`)
    are fixed passages we wrote to reimplement BadRAG's two attack goals.
  - BadRAG's own attack also has a retrieval trigger; we plant the passage
    directly instead.
  - Check whether BadRAG released its passages. Then either use theirs, or
    mark both BadRAG rows in Table IX as our implementation of their attack.
  - Cost: `CPU` check, then `text` (or `GPU` if switching passages).

- [ ] **B7. Say what "simulate" means.**
  - Threats section: we change where a failure arrives (inside a retrieved
    set), never its content to beat a defense.
  - Built from real passages, no optimisation against the model or
    defense.
  - The dose is a stress axis, not a real-world rate.
  - Cost: `text`.

## C. Dose, passage count and question sets

- [ ] **C1. Corpus poisoning takes the first slots, not the last.**
  `10-threats.tex:42` says every planted passage takes the last slots.
  - Cost: `text`.

- [ ] **C2. k is fixed at 10.**
  - Decision: a limitation sentence (results are tied to the share of bad
    passages at k = 10).
  - Or measure stale + ReliabilityRAG at k = 5 and k = 20. Open NQ has 30
    passages for 487 questions, so no new data is needed.
  - Cost: `text` or `GPU`.

- [ ] **C3. The 403 stale-document questions are filtered, not the first
  403.** They are the 500 minus 97 with no passage stating the right
  answer. Third answer is the first 351 minus 51. Check the paper's wording.
  - Cost: `text`.

- [ ] **C4. 10 of 500 questions have only 6–8 passages.** Disclose.
  - Cost: `text`.

- [ ] **C5. Open NQ facts to state.**
  - Passages are web search snippets, not Wikipedia.
  - RobustRAG's authors used the first 100 questions; we use up to 500.
  - Cost: `text`.

- [ ] **C6. Input format sentence.**
  - Five safety fixes received the 10 passages joined into one document.
  - Direction 1 is also tested in each fix's own one-passage format
    (CoConflictQA). Direction 2 cannot be: honest-mistake datasets give one
    passage, and voting cannot run on one. Say this asymmetry plainly.
  - Cost: `text`.

## D. Figures and tables

- [ ] **D1. Experiment flowchart in the paper.** It is already in the Stage 1
  deck (slide 6).
  - Decision: placement. It replaces setup prose, or goes in the appendix
    next to Table IX.
  - Build it with `scripts/gen_paper_figures.py` or TikZ, never by hand.
  - Cost: `text`.

- [ ] **D2. Table IX corrections.**
  - ReliabilityRAG ≈ (A9).
  - Possibly an "input given" column, or footnotes for A1–A5.
  - Cost: `text`.

## E. Already queued (from earlier sessions)

- [ ] **E1. Phase 1 Stage 2 (specvote) analysis.** All 15 runs finished
  2026-11-05 04:39; not yet scored.
  - Check `specvote_incidental_stale_reworded_mistral7b.json`: it is half
    the size of the others.
  - Then commit `scripts/build_sd_attack_contexts.py`,
    `scripts/phase1_stage2.sh` and the results.
  - Note: the `p1_*` attack contexts use the 5× repeat (B1).
- [ ] **E2. Phase 1 Stage 3** (Llama-3.1-8B), **Stage 4** (adaptive attacks,
  CorruptRAG template), **Stage 5** (paper).
- [ ] **E3. Recheck the Stale-Document Poisoning benchmark release** before
  the paper is final.

---

## Paper workflow reminder

1. `scripts/sync_paper.sh pull`
2. `python3 scripts/gen_paper_numbers.py`
3. Edit.
4. `scripts/build_paper.sh`
5. `python3 scripts/check_paper_style.py`
6. Commit.
7. `scripts/sync_paper.sh push`

Never type a count into the prose; add a macro instead.

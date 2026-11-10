# S1–S2 findings: how each literature tests (2026-11-10)

PAPER_PLAN section S, steps S1 and S2. Everything below is read from the
papers' full text and, for S1, from the released code and our own harness.
The data:
- `s2_design_choices.json`: 93 corpus RAG fixes
- `s1_fixes.jsonl`: the 16 fixes we ran
- `s1_causes.jsonl`: the 12 causes we ran

The coding fields are in `CODING_SCHEMA.md`, the checks are in `HAND_CHECK.md`,
and `scripts/merge_design_choices.py` rebuilds the counts.

## Quality checks

- **Quotes.** Every coded field carries a quote. 1,243 of 1,265 quotes (98%)
  appear word for word in the paper text.
- **Hand check.** 15 random papers (5 security, 10 safety), checked against the
  paper:
  - one vs many passages: correct 15 of 15
  - what the bad text competes with: correct 14 of 15. Swin-VIB should read
    "both", not "memory".
- **Not reported as a finding.** For methods that filter each passage and then
  read the survivors together, "keeps passages separate" vs "reads them joined"
  is a judgment call. Only the passage count is used.

## S2: the 93 RAG-channel fixes in the corpus

78 of the 93 put misleading text into the evaluation (23 security, 55 safety);
the other 15 test chunking, privacy or plain quality. Counts below are over
the 78.

| The bad text competes with | Security: one passage / many | Safety: one passage / many |
|---|---|---|
| the model's memory | — (none) | 18 / 7 |
| other passages | 0 / 12 | 0 / 18 |
| memory and other passages | — | 0 / 8 |
| injected instructions | 7 / 3 | — |

Not shown: 8 papers that never state how many passages, and 1 with no
competitor.

**Finding 1. The number of passages follows the question a fix asks, not its
literature.**
- *Document or memory?* Fixes that ask whether to trust the passage or the
  model's memory are tested on one passage: 18 of the 25 that state a count.
  Every safety fix we ran is one of these.
- *Which passage is right?* Fixes that ask which retrieved passage to trust are
  tested on a set, in both literatures:
  - 12 security defenses
  - 26 safety fixes for noisy or conflicting retrieval (18 "other passages"
    plus 8 "both")
- *Is there an instruction?* Prompt-injection detectors read one text at a
  time (7 of 10).
- The median set size is k=5 in both literatures.

**Finding 2. Three design choices separate the literatures cleanly.**
- **Memory.** No security fix's bad text competes with the model's memory
  (0 of 23).
- **Did the model already know?** Only safety papers split results by whether
  the model already knew the answer: 12 of 55 safety, 0 security.
- **Adaptive attacker.** Only security papers test an attacker who knows the
  fix: 10 security, 0 safety. No safety paper reports a worst case (0 of 55).

**Finding 3. The bad text is made differently.**
- **Security:** mostly injected instructions (21 papers) or LLM-written false
  passages and optimised strings (10 together).
- **Safety:**
  - real noisy retrieval (34)
  - LLM-written false passages (17)
  - answer swaps in a real passage (10)
  - real sources that disagree (7)
  - a genuinely outdated fact (1)
- Real outdated text is almost absent on both sides, so our stale-document
  cause has no published construction to follow.

**Finding 4. Shared ground for a common dataset.**
- **Datasets in both literatures:** HotpotQA (7 security papers, 9 safety) and
  Natural Questions (5 security, 11 safety). TriviaQA is common in safety (11).
  RealtimeQA appears in security papers, and in FaithfulRAG on the safety side.
- **Set size:** k=5 is the typical size on both sides.

## S1: the methods we ran, against their own design

| Fix | Authors' unit, k | What we gave it on open NQ | Gap |
|---|---|---|---|
| ACD, CK-PLUG, COIECD, ParamMute, SCR, SpARE | one passage, k=1 | 10 passages joined into one text | wrong unit for all six |
| ParamMute | training prompts ≤1,024 tokens | 477–5,517 tokens | outside its training length |
| SpARE | one passage | 10 joined, cut to 2,048 characters | the cut drops the planted passages in the last slots |
| COIECD | one passage; its paper skips contexts over 2,000 characters | 10 joined | its code cuts prompts at 2,048 tokens, from the end (below) |
| DyPRAG | 3 passages, each turned into weights | 10 | k |
| RobustRAG, ReliabilityRAG | ranked set, k=10 | ranked set, k=10 | essentially native. Our payload is repeated 5 times; RobustRAG's code repeats 10 |
| PIGuard, DataSentinel | one text per call | one passage per call | native |
| AttnTrace | 50 retrieved texts | 10; the step that removes the top 5 is ours | k |
| Spotlighting | one document | 10 marked passages, warning inside the data | placement |
| SHIFT, FaithfulRAG | one passage | controls only | never entered the grid |

On CoConflictQA, every safety fix ran on one passage, its own unit.

**New defect: COIECD's refusal cell in Table VI is not a measurement of COIECD.**
- *Cause.* `third_party/COIECD/decoding.py:145` tokenises with
  `truncation=True, max_length=2048`. Llama-3 truncates from the right, so on
  long prompts the question and the "Answer:" cue are lost.
- *Prompts over the limit* (500 items, counted 2026-11-10):

  | Attack | Over the limit |
  |---|---|
  | PoisonedRAG | 87 at dose 10 |
  | BadRAG refusal | 58 at dose 3; all 500 at doses 5 and 10 |
  | BadRAG tone | 1 at dose 5; all 500 at dose 10 |
  | corpus poisoning | none |

- *Effect.* The grid quotes dose 5, so its COIECD refusal cell is built from
  prompts with no question in them. The defect is recorded in PAPER_PLAN
  section S.

## S1: the causes we ran, against their sources

| Cause | Source setup | Ours | Gap |
|---|---|---|---|
| PoisonedRAG | joined set, k=5, all 5 retrieved are planted (GPT-4-written, ~30 words) | the last j of 10 slots, one released passage repeated 5× per slot, no retrieval | repetition; ranked-set placement |
| Corpus poisoning | retriever only: optimised 50-token strings, no generator | read by a generator, on open NQ and CoConflictQA | the source never tests a generator |
| BadRAG | trigger-optimised passages in the corpus; generator k not stated | hand-written 90- and 54-word payloads, no trigger, last j of 10, repeated 5× | re-implementation |
| False evidence | CoConflictQA field, one passage | same | the paper never describes the field |
| Third answer (ours) | — | answer swapped to a same-type wrong answer, repeated 5× in each bad slot | repetition; type only loosely matched |
| Stale (ours) | — | gold answer swapped for PoisonedRAG's target, one copy per slot | not a real outdated fact; same passage in every slot |
| Misretrieval (ours) | — | one passage from another question, copied into all j slots | copies, not distinct passages |
| Dilution (ours) | — | other questions' passages appended at the end | unlike lost in the middle (relevant passages without the answer, in any position) |

Lost in the middle has construction code but was never run. The
irrelevant-context paper (GSM-IC) uses math word problems, so it is no model
for passage-level causes.

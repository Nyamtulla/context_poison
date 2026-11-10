# S3: requirements for the shared dataset (agreed 2026-11-10)

Replaces the draft S3 list in PAPER_PLAN.md once agreed. The evidence for
each requirement is in `FINDINGS.md`.

## The design principle

A cross test is fair only when each fix reads the kind of input it was built
for. S2 shows that input is set by the question a fix asks, not by its
literature:

| Question the fix asks | Unit it is tested on | Who asks it |
|---|---|---|
| Document or memory? | one passage | safety: knowledge-conflict fixes (ACD, CK-PLUG, COIECD, ParamMute, SCR, SpARE) |
| Which passage is right? | a set of k (median 5) | security: RobustRAG, ReliabilityRAG, AttnTrace; safety: 26 noisy-retrieval fixes |
| Is there an instruction in this text? | one text | security: PIGuard, DataSentinel, Spotlighting |

So the dataset carries **the same bad content in every unit**, and each fix is
run on its own unit.

## Requirements

**R1. Three forms per item, one bad content.** Each item has a question, a
gold answer, and one false claim (from an attacker or an honest mistake). The
same claim appears in three forms:
- **(a) One passage.** The bad passage on its own. This is the unit of the
  document-or-memory fixes.
- **(b) A ranked set of k=10 (main).** j of the 10 slots are bad and the rest
  are real retrieved passages. Each bad slot is a distinct passage. This is the
  unit of the voting defenses and the noisy-retrieval fixes.
- **(c) k=5.** The corpus median, for fixes whose authors use 5. It is the
  first five passages of (b). A fix with its own k gets
that k: DyPRAG 3, AttnTrace 50 as a stated extension.

**R2. Inside every fix's limits.** Every form must fit the strictest limit of
the fixes that read it. Passages are about 100 words. The one-passage form
stays under 2,000 characters (COIECD) and under 1,024 tokens of prompt
(ParamMute's training length). A test checks every prompt's token count
against each fix's cap before any run; the COIECD defect shows why this has to
be automated.

**R3. Memory label per model.** For every item and every model, a closed-book
answer and a label: knows the gold, holds a different answer, or does not
know. Every safety result is reported split by this label (12 safety papers
already do this). Security results get the same split, which no security paper
reports.

**R4. Matched attacker and honest-mistake pairs.** For each item, an attacker
version and an honest version assert the same false answer, with the same
length, position and number of copies. Only the origin differs. This keeps the
attack-versus-mistake comparison exact.

**R5. Honest mistakes that are natural.** Each honest cause is built the way
the safety literature finds it:
- **Outdated:** a real older answer with a real dated passage, not a swap.
  Only 1 of 55 safety fixes uses one, so this is new ground and must be
  sourced, not simulated.
- **Misretrieval:** distinct real passages retrieved for a near-miss query,
  never copies.
- **Conflict:** real sources that disagree, where they exist.
- **Swapped answer:** kept as a labelled control, since 10 safety papers use
  it, with the substitute matched to the gold answer's type by a checked
  entity type. Shape alone does not count.
- **Lost in the middle:** relevant passages without the answer, in varied
  positions, as in its source.

Every false claim is stated once per passage.

**R6. Attacks as their authors built them.**
- **PoisonedRAG:** the released passages, distinct, joined with k=5 as in its
  paper. The ranked-set form is reported as our extension.
- **Corpus poisoning:** the released construction against the retriever, with
  the generator reading what is retrieved.
- **BadRAG:** a trigger-optimised version if one can be built from the paper.
  Otherwise it is labelled as a re-implementation.
- **Adaptive:** at least one adaptive attacker against a document-or-memory
  fix, since no safety paper tests one.

No payload is repeated inside a slot.

**R7. Grounded dose.** Measure, on real retrieval for the base questions, how
often j of 5 retrieved passages already carry a wrong answer. Doses inside
that range are reported as realistic and higher doses as a stress test.

**R8. Both literatures' metrics on every run.**
- accuracy (EM)
- attack success
- where each answer went: gold, the model's own answer, the planted answer, or
  a refusal
- the memory split from R3

That puts each literature's headline number beside the other's on every run.

**R9. Base data shared by both sides.** Prefer questions both literatures
already test on:
- Natural Questions (5 security, 11 safety)
- HotpotQA (7 security, 9 safety)
- RealtimeQA (for dated answers, R5)

S4 checks which of these can supply real outdated answers and per-question
retrieval.

## Not required

- **Agent and tool-output causes.** They stay on AgentDojo. The prompt-injection
  detectors get form (a) and form (b) passages as text to classify, and no new
  agent data is built.
- **Long-form tasks** such as BadRAG's tone writing task. The tone cause is
  measured as refusal or negativity in short answers, as now, and labelled
  adapted.

## Decisions (2026-11-10)

1. **Main set size: k=10**, so the existing RobustRAG and ReliabilityRAG results
   stay comparable. The set of 5 (the corpus median) is the second form.
2. **The adaptive attacker stays a separate experiment.** It is not part of
   this dataset.
3. **Honest causes at launch: still open.** The candidates are outdated,
   misretrieval, conflict, the swapped control and lost in the middle.
   Outdated depends on S4.
4. **Two safety noisy-retrieval fixes join the rerun.** Candidates are listed
   in PAPER_PLAN S3. BordaRAG and END fit our models and units best; their
   released code is still to be checked.

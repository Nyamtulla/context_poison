# Pilot report, round 1 (2026-11-10)

## What was checked

- **The pilot.** 50 questions: 20 core, 20 added from SituatedQA and 10 from
  WikiContradict. The builder (`scripts/build_pilot.py`) produced 597 items
  and 353 distinct bad passages.
- **The reading.** Every bad passage was read against
  `READING_RUBRIC.md` by three readers, one slice each
  (`read_out{1,2,3}.jsonl`).
- **Check on the readers.** I re-read 15 verdicts drawn at random
  (`my_check_sample.json`) and agreed with all 15. One is borderline: a
  PoisonedRAG passage saying "what many believe to be the record", which the
  reader failed as a hedge.

## Pass rates

| Cause | Pass | Main failure |
|---|---|---|
| PoisonedRAG (released passages) | 27/100 (27%) | 73 deny or hedge the target |
| Swapped answer | 16/54 (30%) | swap hit the wrong span, self-contradiction, broken grammar |
| Outdated | 10/64 (16%) | passage contains the old answer's string but does not state it as the answer |
| Misretrieval | 38/115 (33%) | passage mentions the false answer without stating it; type mismatch; duplicates |
| Conflict (WikiContradict) | 16/20 (80%) | widening the sentence to 100 words changed or settled the contradiction |

Only conflict is near usable. The other four constructions fail most of the
time.

## Findings

**1. Most released PoisonedRAG passages do not assert the attacker's answer.**
- The readers judged 73 of 100 to deny or hedge it. Examples: "the incorrect
  assertion that the Broncos beat the Patriots", and "setting what many
  believe to be the record".
- Questions tend to go all one way. Several deny on every passage, and others
  assert on every passage.
- **The keyword screen:**
  - Every passage it flagged (51) truly denies, so its precision is 100%.
  - It catches only 51 of the 73 deniers (70%).
  - It misses soft hedges such as "many believe", "the belief that",
    "popular lore" and "claims".
- **Consequence for the paper.** Every PoisonedRAG result used these
  passages, so the attack measured was much weaker than the one PoisonedRAG
  describes. The pilot sample is 100 passages from 20 questions. The rate over
  all 2,500 passages still needs measuring, and the assertion judge proposed
  below can do that.

**2. String matching cannot find honest mistakes.**
- **Outdated.** The old answer turns up as another date, another team or a
  side fact ("7 Teen Choice Awards", a 1997 win mentioned in passing).
- **Misretrieval.** It finds passages that mention a name without stating
  anything about it, such as a cast list.
- **Pages the readers flagged:**
  - One 2018 passage is dated after the 2018 change and states the gold.
  - One fetched revision reads "As of 10 November 2026": a date template was
    filled in when the page was fetched.

**3. Replacing every occurrence of the gold answer breaks passages.**
- "LeBron James and LeBron James are the only two players"
- "Super Bowl X1985X"
- "saliva in Large intestine"
- A leftover "Bryan survived ... longest" leaks the gold.

**4. The type check matched the question, not the answer.** A person (Yuzuru
Hanyu) passed as a country. The "nearest question" was sometimes a rewording
of the same question, so its answer is an older answer, not a misretrieval.

**5. Gold answers are wrong on 2 of 40 NQ questions at 2018.**
- nq368: the Ontario PC leader was Doug Ford from March 2018, not Patrick
  Brown.
- nq197: the Vikings' last Super Bowl was XI, January 1977, not 1969.

Three more are ambiguous: Wimbledon men vs women, the Mount Bromo eruption
date, and the Kentucky sport. In both clear cases the true answer leaks into
the bad set.

**6. WikiContradict.**
- Widening each sentence to 100 words worked for 6 of 20 contexts. The rest
  could not be found in today's article.
- In one case, widening changed the claim from "nine" to "eight" cities.
- One item's contradiction was settled only by a 2021 change, so it does not
  fit a 2018 frame.

**7. The 2018 dump is missing some numbers.** 2.1% of top-10 passages contain
an empty slot where a year or number was removed ("On December 2, ,"). This
matters for year answers: 190 questions have a bare year as gold.

## Proposed changes to the rules

**A. One assertion judge for every cause.**
- **What it is.** A local instruction-tuned model asked, for a question, a
  passage and a candidate answer, whether the passage states that answer as
  the answer to the question.
- **Which model.** Not one of the models the fixes are tested on; Qwen2.5-14B
  is used for this.
- **Validation.** The 353 hand labels from this pilot are its validation set.
  It is used only if it agrees with them at or above an agreed level, for
  example 90% precision on "asserts".
- **What it does:**
  - filters the released PoisonedRAG passages, replacing the keyword screen
  - selects outdated and misretrieved passages from the candidates that
    string matching finds
  - checks every swapped passage

**B. Swap one span, not every occurrence.**
- Replace only the mention of the gold answer in the sentence that answers
  the question.
- Skip passages that mention the gold more than once outside that sentence.
- Skip golds that name more than one entity.
- The judge then checks that the result asserts the false answer and no
  longer states the gold.

**C. Type checks from the answer.**
- Each answer's type is read from the passage that states it.
- Granularity must match: a year with a year, a full date with a full date.
- A neighbour question must have a different subject from the item's
  question, so it is not a rewording.

**D. Outdated passages.**
- Candidates from the 2018 pool and from revisions, kept only if the judge
  says they state the old answer as the answer.
- Revisions are fetched as stored wikitext, so date templates are not filled
  in at fetch time.
- 2018-pool passages dated after the change are dropped.

**E. Gold check.** Every gold is checked against 2018 before the full build.
The judge flags disagreements between the gold and the clean passages, and
each flagged item is read.

**F. Passage hygiene.** Drop passages with a removed year or number.

**G. WikiContradict.**
- Keep its original sentences as the conflict unit, padded with the
  surrounding text from the 2018 dump rather than from today's article.
- Items whose contradiction postdates 2018 are excluded.

After these changes, round 2 rebuilds the pilot and reads it again. The rules
freeze when every cause passes at about 90% or better.

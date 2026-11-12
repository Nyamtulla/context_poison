# Pilot report, round 2 (2026-11-11)

## What was built

- **Builder.** `scripts/build_pilot_r2.py` applies rules A–G from
  `../PILOT_REPORT.md`. Rule A is the assertion judge in
  `scripts/assertion_judge.py`: Qwen2.5-14B-Instruct, threshold 0.5, run on the
  CPU because the shared GPU was full.
- **Questions.** New questions only; round-1 qids are excluded.
  - 44 kept of 300 tried: 20 core, 20 added from SituatedQA, and 4 from
    WikiContradict (10 were wanted).
  - Assembled into 440 items (`items.jsonl`) holding 162 bad passages.
- **Why questions were dropped:**

  | Reason | Questions |
  |---|---|
  | WikiContradict context not found in the 2018 dump (rule G) | 158 |
  | WikiContradict passage judged not to state its claim, or both sides in one passage | 18 |
  | No clean passage judged to state the gold (rule E) | 51 |
  | No cause produced an acceptable bad passage | 29 |

## The reading

- All 162 bad passages were read blind by three readers, one slice each
  (`read_out{1,2,3}.jsonl`), against `../READING_RUBRIC.md`.
- The slices (`read_slice*.json`) carry no judge scores.

| Cause | Round 1 pass | Round 2 pass | Round 2 states the false answer |
|---|---|---|---|
| PoisonedRAG | 27/100 (27%) | 22/25 (88%) | 22/25 |
| Outdated | 10/64 (16%) | 30/40 (75%) | 33/40 |
| Swapped answer | 16/54 (30%) | 9/13 (69%) | 13/13 |
| Misretrieval | 38/115 (33%) | 47/76 (62%) | 56/76 |
| Conflict | 16/20 (80%) | 6/8 (75%) | 6/8 |
| **All** | 107/353 (30%) | **114/162 (70%)** | 130/162 |

No cause reaches the 90% target set for freezing the rules.

## The judge on new questions

- **Precision.** Every passage on the sheet passed the judge, so the
  share the readers say states the false answer is the judge's precision:
  130/162 = 80%. On the round-1 labels, which its prompt was tuned on, it was
  93%.
- **Threshold.** Raising the threshold barely helps: 83% at P(A) ≥ 0.97,
  which keeps 144 passages.
- **Recall.** It cannot be measured from this round, because rejected
  passages were not read.

## Findings

1. **Misretrieval is the weak cause.** Its passages often mention the
   neighbour's year or name without answering "when was the last time"
   (Georgia 1980, Maple Leafs, Yankees). Some match a title rather than the
   answer: the Bon Jovi song instead of Warren Zevon.
2. **The PoisonedRAG screen and judge work.** No kept passage denies its
   target; 3 hedge ("purported", "allegedly", "often credited").
3. **Construction bugs, each cheap to fix:**
   - nq135: the misretrieval false answer equals the gold answer.
   - nq406: the PoisonedRAG target is one of the gold answers.
   - A swapped passage still names the gold elsewhere in its text
     ("Dylan's version", "Dench had also portrayed Victoria").
   - Two SituatedQA questions ask the same thing (England's last World Cup
     semi-final).
4. **Gold problems:**
   - nq251 includes Salt Lake City, a Winter host, for a Summer Olympics
     question.
   - nq072 is doubtful: the quoted line is from *Independence Day*, not
     Dylan Thomas.
   - Two golds are contested: the most English speakers; men's snowboarding
     gold.
5. **Outdated passages sometimes carry the old answer only in the title,**
   not in the text.

## Open, for the advisor meeting

- Whether 70–90% per cause, plus a hand check in the full build, is enough,
  or whether to run one more round on misretrieval.
- What to do with conflicts written after 2018.
- Whether to loosen the gold check (rule E) or keep it strict and report the
  drop.

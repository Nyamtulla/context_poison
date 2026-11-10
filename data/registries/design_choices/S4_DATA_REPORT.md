# S4: which base data can supply real outdated answers (checked 2026-11-10)

Serves S3 requirements R1 (question, gold, one false claim in three forms), R3
(memory label), R5 (outdated = a real older answer with a real dated passage),
R7 (dose measured on real retrieval) and R9 (questions both literatures test
on).

Every number below was computed from the downloaded release files by the
scripts in `data/s4_sources/_scripts/` (run with `python3 -I`; parquet files
read with the pyarrow in `/home/n646s681/helm/.venv`, also `-I`). Downloads are
in `data/s4_sources/<name>/`. Question overlap uses a normalised form
(lower-case, punctuation removed, whitespace collapsed); exact-text and
normalised overlap came out identical wherever both were computed.

"Real older answer" means the release itself records an answer that held
earlier and was later replaced. "Passage stating the older answer" means a
passage in the release (or reachable from it by a stable pointer) whose text
contains the older answer. A string match is a necessary condition, not proof:
the Atlanta sample below shows a current passage that names the old answer as
the thing that was replaced.

---

## 1. open NQ, RobustRAG release

- **Source:** `third_party/RobustRAG/data/open_nq.json`, from
  github.com/inspire-group/RobustRAG at commit `9bc35b2` (2024-09-15). The repo
  API reports no licence. The questions come from NQ-open (CC BY-SA 3.0 as
  distributed by Google).
- **Questions:** 500. All 500 are in the NQ-open validation split (3,610
  questions; checked against `google-research-datasets/nq_open`), 1 also
  appears in train.
- **Fields:** `question`, `correct answer` (list), `expanded answer` (GPT-4
  expansions, per the README), `context` (list of `{title, text, link}`),
  `incorrect answer`, `incorrect_context` (5 PoisonedRAG passages per item),
  `id`.
- **Passages per question:** min 6, median 30, max 30; 10 items have fewer than
  10. The README says they are Google Search results. They are **snippets**,
  not passages: median 26 words, max 62. Gold answer string appears in some
  passage for 447/500 items, in the top 10 for 419/500.
- **Pool:** none. The snippets are the whole retrieval; there is no corpus to
  retrieve from again.
- **Real older answer:** none in the release.
- **Linked through SituatedQA (section 2):** 132 of the 500 questions are
  SituatedQA temporal questions; 50 of those have a dated previous answer. For
  those 50:
  - RobustRAG's gold is SituatedQA's current answer for 18, its previous answer
    for 9, neither for 23. So for at least 9 items the open NQ gold is itself
    the outdated answer.
  - The Google snippets (retrieved 2023-24) contain the previous-answer string
    for 26 items (21 within the top 10; 109 snippets in all) and the current
    answer for 33.
- **Samples (old answer appears in a real snippet):**
  1. "how many seasons of vampire diaries r there": previous `7`, current `8`;
     snippet: "...concluded on March 10, 2017, having aired 171 episodes over eight
     seasons." (states the current answer; matched `7` inside `171`, so a
     false hit).
  2. "when was the last time the crows were in the grand final": previous
     `1998`, current `2017`; snippet (Adelaide Football Club, Wikipedia): "The
     men's team won both the 1997 and 1998 Grand Finals..."
  3. "where is the new football stadium in atlanta": previous `Georgia Dome`,
     current `Mercedes-Benz Stadium`; snippet: "Opened in August 2017 as a
     replacement for the Georgia Dome..." (names the old answer as replaced).

  These three show why string hits are an upper bound: of the first four hits,
  one is a substring artefact and one is a passage that refutes the old answer.

## 2. SituatedQA, temporal part

- **Source:** github.com/mikejqzhang/SituatedQA, commit `1ef8545`
  (2022-08-10), files `data/raw_data/temp.{train,dev,test}.jsonl` and
  `data/qa_data/temp.*.jsonl`. The repo has no LICENSE file and the API reports
  none; the README does not state one. **Licence unverified.**
- **Questions:** 5,061 (train 2,904, dev 1,227, test 930). Every one is an
  NQ-open question: 4,131 in NQ-open train, 930 in NQ-open validation (the test
  split is exactly the NQ-open validation subset).
- **Fields (raw):** `question`, `id`, `nq_answers`, `is_dependent`,
  `cur_answers`, `prev_answers`, `timelines` (each with `cur_answers`,
  `cur_start{year,month,date}`, `prev_answers`, `prev_start{...}`, and the
  `*_full` strings), `context_answer_pairs` (edited question "as of YEAR",
  answers, date, date_type). QA files: `question`, `edited_question`, `date`,
  `date_type` (`start`, `sampled_year`, `sampled_date`, `orig`), `answer`,
  `any_answer`.
- **Passages:** none. No passage, title or URL field.
- **Real older answer:**
  - `is_dependent` true: 2,358.
  - non-null `prev_answers`: **1,644** (train 812, dev 459, test 373).
  - of those, the period the old answer held is dated at both ends
    (`prev_start` year and `cur_start` year): **1,474**; start of the new
    answer only: 49; no year: 117; prev start only: 4.
  - questions whose dated answers differ across `context_answer_pairs`: 1,465.
  - when the current answer began (earliest across timelines): before 2018:
    610, in 2018: 202, after 2018: 711, no year: 121. The 711 matter: in the
    Dec 2018 Wikipedia that DPR and most NQ work retrieve from, the
    *previous* answer was the current one.
- **Overlap with RobustRAG open NQ:** 132 questions (all in the test split);
  50 with a previous answer.
- **Passage stating the older answer:** none in the release. See the
  Wikipedia-revision probe (section 9) for how often one can be fetched.
- **Samples (verbatim):**
  1. "what university has the most students in the us": nq `Texas A&M
     University`, current `University of Central Florida` (from 2019),
     previous `Texas A&M University` (from 2018).
  2. "who sang the american anthem at the super bowl": nq `Pink`, current
     `Jazmine Sullivan and Eric Church` (2021), previous `Demi Lovato` (2020).
  3. "who has the most net worth in the us": nq `Jeff Bezos`, current `Elon
     Musk` (from "November 2020"), previous `Jeff Bezos` (no start year).

## 3. RealtimeQA

- **Source:** github.com/realtimeqa/realtimeqa_public, commit `850b0ab`
  (2026-11-06; still updated weekly). No licence in the repo or README.
  **Licence unverified.**
- **What the release contains:** weekly files `past/YYYY/DATE_qa.jsonl` and
  `backnumber/YYYY/DATE_qa.jsonl` (361 files read), plus per-week retrieval
  `DATE_gcs.jsonl` (Google custom search, full article text) and for 2023
  `DATE_dpr.jsonl`; `_gcs` files total 404 MB, of which only two weeks were
  downloaded.
- **Questions:** 9,564 rows, 2020-01-03 to 2026-10-30 (2020: 856, 2021: 1,370,
  2022: 2,851, 2023: 1,439, 2024: 1,478, 2025: 830, 2026: 740). 8,093 unique
  normalised questions.
- **Fields:** `question_id`, `question_date`, `question_source`,
  `question_url`, `question_sentence`, `choices`, `answer` (index into
  choices), `evidence` (an excerpt of the source article).
- **Passages:** `_gcs`: 10 results per question (min 0), each `{url, title,
  text, publish_date, authors}`; full articles, median ~1,100-1,200 words, not
  passages. RobustRAG's copy (`third_party/RobustRAG/data/realtimeqa.json`):
  100 questions from 9 weeks, 2023-10-06 to 2023-12-08, with 25-50 Google
  snippets each (median 49, median 24 words) and 5 PoisonedRAG passages.
- **Real older answer:** effectively none. 586 normalised questions recur;
  only 8 recur with a different answer, and on reading them most are not
  changed facts (a picture quiz "what is this", a duplicated question with two
  answers in the same week, "20 years" vs "20"). Two are real recurring
  events: "Which MLB team won the World Series this week" (2023/11/02 `Texas
  Rangers`; 2026-10-30 `Milwaukee Brewers`) and "Which awards show announced
  its 2024 nominees this week" (2023/12/14 `Golden Globe Awards`; 2024-07-18
  `Emmy Awards`). Questions are about one week's news; the answer does not
  change because the question is pinned to the week.
- **Passage stating the older answer:** not applicable.
- **Overlap with NQ-open:** 0 of 8,093 unique questions.
- **Samples:** the two recurring-event pairs above are the only usable ones;
  there is no third.

## 4. FreshQA

- **Source:** github.com/freshllms/freshqa (Apache-2.0 licence on the repo),
  README lists 69 dated Google-Sheets snapshots from Feb 26, 2024 to Apr 21,
  2026; 67 exported as CSV (May 6 and May 13, 2024 returned an HTML page, not
  a CSV). The Oct 6, 2023 version is available as a third-party copy,
  `natyou/freshqa_10_06` on HuggingFace (no licence on the card).
- **Questions:** 600 per snapshot (500 TEST, 100 DEV); 667 distinct
  normalised question texts across snapshots (some questions were reworded).
  Fact type in the latest snapshot: never-changing 225, slow-changing 220,
  fast-changing 155. False premise: 149.
- **Fields:** `id`, `split`, `question`, `effective_year`, `next_review`,
  `false_premise`, `num_hops`, `fact_type`, `source` (URLs only),
  `answer_0..answer_9`, `note`.
- **Passages:** none. `source` holds URLs (often Wikipedia, sometimes with a
  text fragment anchor); no text, no retrieval.
- **Real older answer:** the release has no old-answer field, but the dated
  snapshots are one. Diffing `answer_0` across the 67 snapshots: **210**
  questions changed at least once (fast-changing 152, slow 53, never 5; 8 are
  false-premise). Each old answer comes with the first and last snapshot date
  it was seen in. Oct 2023 vs Apr 2026: 170 of 531 shared questions differ.
  This is an upper bound: some changes are rewordings ("1 year" to "more than
  1 year", rephrased explanations).
- **Passage stating the older answer:** none in the release. The `source` URL
  plus the snapshot date gives the page and date to fetch an old revision.
- **Overlap with NQ-open:** 2 of 600.
- **Samples (verbatim, with snapshot dates the answer was seen):**
  1. "Who is the spouse of the President of the United States?": `Jill Biden`
     (2024-08-02 to 2024-12-18), then `Melania Trump` (2025-02-03 to
     2026-04-21).
  2. "On what date did Kendrick Lamar release his most recent studio album?":
     `May 13, 2022` (2024-02-26 to 2024-11-18), then `Nov 22, 2024`
     (2024-11-25 to 2026-04-21).
  3. "What was the Weeknd's last studio album titled?": `Dawn FM` (2024-08-02
     to 2024-12-18), then `Hurry Up Tomorrow` (2025-02-03 to 2026-04-21).

## 5. HotpotQA

- **Source:** HuggingFace `hotpotqa/hotpot_qa`, revision `1908d6a`, licence
  CC BY-SA 4.0. Only the distractor validation parquet (27 MB) was downloaded;
  the full Wikipedia corpus was not.
- **Questions:** distractor train 90,447, validation 7,405 (fullwiki has the
  same plus a 7,405 test).
- **Fields:** `id`, `question`, `answer`, `type` (bridge 5,918 / comparison
  1,487 in validation), `level`, `supporting_facts`, `context` (titles and
  sentences).
- **Passages:** distractor setting has 10 paragraphs for 7,345 of 7,405
  validation questions (60 have 2-9); median 80 words per paragraph. The 10
  are 2 gold + 8 retrieved distractors, so form (b) exists natively.
- **Real older answer:** none. No date or time field; 152 of 7,405 questions
  contain a time cue word (current, latest, now, ...), with no older answer
  recorded.
- **Overlap with open NQ:** not a NQ derivative; not computed.

## 6. Other datasets with old-vs-new answers (each checked from its release)

| Dataset | Release checked | Licence | What it gives | Old answer + date | Passage with old answer | NQ overlap |
|---|---|---|---|---|---|---|
| **TimeQA** | github wenhuchen/Time-Sensitive-QA `dataset/dev.easy.json` | BSD-3 | 3,021 dev-easy questions, each time-scoped ("from May 1997 to May 2001"), with the whole Wikipedia article as ~19 paragraphs | 686 of 739 subject-relation groups have 2+ distinct answers for different periods | yes: the same (current) article states the older role with its dates | none (Wikidata-generated) |
| **TempLAMA** | HF `Yova/templama` (community copy of Google's TempLAMA) `val_with_aliases.json` | none stated | 4,654 cloze queries ("X plays for _X_."), one per year 2010-2020 | 516 of 539 subject-relation pairs change across years | no passages | none |
| **StreamingQA** | storage.googleapis.com/dm-streamingqa `streaminqa_eval.jsonl.gz` (md5 matches README) | Apache-2.0 | 36,378 eval questions with question date, evidence date, evidence document id into WMT News Crawl | 64 recurring questions with no shared answer (upper bound; e.g. "who is the white house press secretary": `Josh Earnest` evidence 2015, `Kayleigh McEnany` 2020) | the evidence article is dated, but its text is only in WMT News Crawl (several GB a year; not downloaded) | not computed |
| **EvolvingQA** | HF `kat-research/EvolvingQA` `edited/*` (+ `wiki_0304`) | none stated | 18,968 `edited` items: `question`, `answer1` (old), `answer2` (new), in six monthly splits (0203 ... 0708) | yes, dated only to the month pair | `wiki_*` splits hold changed-article text for the new month (median 322 words); old answer string found in title-matched text for 34 of 200 sampled items. Questions are model-generated and some are poor ("neural network architecture used for LaMDA": `Transformer` -> `seq2seq`) | none |
| **TemporalWiki** | HF `seonghyeonye/TemporalWiki` `TWiki_Probes.zip` | none stated | changed/unchanged Wikidata triples for 4 month pairs of 2021 (1,776-1,951 changed each) | **no**: changed probes give only the new object | Wikipedia snapshots exist (`Wikipedia_Full.zip`, not downloaded) | none |
| **DynamicQA** | github copenlu/dynamicqa `Data/Temporal_final.csv` | none in API | 2,495 temporal questions with a masked Wikipedia context and an edit count | **no**: one object only; `replace_name` is a substituted entity, a swap | context states the current object, masked | none |
| **WikiContradict** | HF `ibm-research/Wikipedia_contradict_benchmark` | MIT | 253 questions, each with two contradicting real Wikipedia passages and both answers | not temporal; serves R5 "conflict" | yes, both passages are real | none |
| ChroKnowledge, TAQA | no release found by GitHub or HuggingFace search under these names | - | - | - | - | - |

Not checked: ArchivalQA (a HuggingFace copy exists, `meithnav/archivalqa`;
not opened). No dataset release was found for "Dated Data" or WikiDated.

## 7. Retrieval pool for NQ questions

None of the NQ-based releases ships a pool. The standard pool is DPR's Dec
2018 Wikipedia split, `psgs_w100.tsv.gz` (21M 100-word passages):
4,694,541,059 bytes at dl.fbaipublicfiles.com, last modified 2020-03-17.
**Not downloaded (over the 2 GB cap).** It matches R2's ~100-word passage
and is the corpus PoisonedRAG and corpus poisoning attack, so the attacks of
R6 run against it as their authors built them.

## 8. What is still missing everywhere

No release gives, for a question both literatures use, an older answer
**and** a real passage, written while that answer held, that states it. The
nearest are:
- SituatedQA: old answer + dates, NQ questions, no passage.
- FreshQA snapshots: old answer + snapshot dates + source URL, no passage, not
  NQ.
- TimeQA: old answer + dates + passage, but the passage is the current article
  and the questions are time-scoped and Wikidata-generated, not NQ.

## 9. Probe: can an old Wikipedia revision supply the passage?

`_scripts/wiki_probe.py` took SituatedQA dev+test items with a dated previous
answer (the 50 that overlap RobustRAG's open NQ, plus 100 random others),
searched Wikipedia for the question (top 2 titles), fetched the revision in
force on Dec 31 of the year before the current answer started (i.e. inside the
old answer's period), cut it into 100-word windows, and checked whether a
window contains the old answer; it also checked the current revision for the
current answer. Results in `_scripts/wiki_probe_results.json`.

The run covered 143 items: 43 open NQ overlap items (7 of the 50 have no
year on the current answer, so no snapshot date could be set, and the script
skipped them) plus 100 random ones. Nothing was lost.

| | open NQ overlap | random SituatedQA dev/test |
|---|---|---|
| items | 43 | 100 |
| old period ends 2002 or later (revision history usable) | 35 | 86 |
| a Wikipedia page found and fetched | 12 | 32 |
| old revision contains the previous answer | 7 | 16 |
| ... and does not contain the current answer | 5 | 9 |
| current revision contains the current answer | 5 | 14 |

What this shows:
- **The bottleneck is finding the page, not the revision.** Searching the
  Wikipedia API with the raw question returned no page for most items (44 of
  121 eligible). Where a page was found, the old revision held the old answer
  in 23 of 44.
- **A string hit is not yet a usable passage.** Of four random hits read by
  hand, two state the old answer as the answer:
  - "when does the new season of law and order svu come on" (previous
    `September 26, 2019`), revision 2019-12-30: "On March 29, 2019, NBC renewed
    the series for a record-breaking twenty-first season, which premiered on
    September 26, 2019."
  - "who is the oldest president to be elected" (previous `Donald Trump`,
    current `Joe Biden` from 2021), revision 2020-12-22: "The oldest person to
    assume the presidency was Donald Trump, at the age of , on Inauguration
    Day."

  One is the wrong article ("Superteams in the NBA" mentions Robert Parish's
  All-Star count for "who has been playing the longest in the nba"), and one
  is an infobox line naming O. Panneerselvam as predecessor.
- **Fix for the lookup:** SituatedQA's `id` is the Natural Questions example
  id (README), and full Natural Questions records the source Wikipedia page
  for each example. Joining on it would give the exact article instead of a
  search guess. **Not verified:** I did not download full NQ (the dev set is
  about 1 GB in shards), so neither the join rate nor the page field was
  checked here.

## 10. Comparison

| Candidate | Questions | Both literatures? | Passages / question | Pool | Real older answer (dated) | Passage stating older answer | Overlap with RobustRAG open NQ |
|---|---|---|---|---|---|---|---|
| open NQ (RobustRAG) | 500 | yes (NQ: 5 security, 11 safety) | 6-30 Google snippets, median 30, ~26 words | no (DPR 2018 Wikipedia, 4.7 GB, exists) | 0 in release; 50 via SituatedQA | 0 in release | - |
| SituatedQA temporal | 5,061 (all NQ-open) | yes, via NQ | 0 | no | 1,644 (1,474 dated both ends) | 0 | 132 (50 with older answer) |
| RealtimeQA | 9,564 (2020-2026) | yes (RobustRAG, ReliabilityRAG; FaithfulRAG) | 10 full articles (gcs); RobustRAG copy: 100 q, ~49 snippets | no | ~2 | 0 | 0 |
| FreshQA | 600 per snapshot, 67 snapshots | safety only (SCR) | 0 (URLs) | no | <=210 (snapshot-dated) | 0 | 2 of 600 in NQ-open |
| HotpotQA | 7,405 val | yes (7 security, 9 safety) | 10 (distractor) | Wikipedia 2017 (not downloaded) | 0 | 0 | not NQ |
| TimeQA | 3,021 dev-easy | no | ~19 paragraphs | the article | 686 groups | yes (current article) | 0 |
| EvolvingQA | 18,968 edited | no | changed text per month | monthly diffs | 18,968 (month pairs) | partial | 0 |
| StreamingQA | 36,378 eval | no | 1 dated news doc (WMT, not downloaded) | WMT News Crawl | <=64 | dated doc | not computed |

## 11. Recommendation

**Base questions: NQ-open validation (3,610), with RobustRAG's 500 as the
core.** It is the one base both literatures test on (R9), it has PoisonedRAG
passages for the 500 (R6), and it is the only base that a dated-old-answer
release (SituatedQA) is built on. RealtimeQA and FreshQA share no questions
with it (0 and 2). HotpotQA has no time data.

**Outdated answers: SituatedQA temporal, restricted to NQ-open validation.**
- 373 validation questions have a previous answer; 50 of them are in
  RobustRAG's 500. If the outdated set needs more than that, SituatedQA's
  train and dev add 1,271 more NQ-open (train-split) questions with the same
  fields. They are still NQ questions, but they lack RobustRAG's PoisonedRAG
  passages, so the attack forms would have to be built for them (PoisonedRAG
  releases its construction for NQ, but its released passages cover only its
  own question set).
- Each item gives the old answer, the year it started and the year it was
  replaced (1,474 of 1,644 dated at both ends).

**Passages: retrieve them ourselves from DPR's Dec 2018 Wikipedia
(`psgs_w100.tsv.gz`, 4.7 GB, over this step's 2 GB cap, so it needs a go-ahead).**
- RobustRAG's Google snippets are fixed, are not a pool, and average 26 words
  against the ~100 words R2 assumes. They stay as the comparison point for the
  existing RobustRAG and ReliabilityRAG results.
- A pool lets us measure R7 (how often real retrieval already carries a wrong
  answer) and build form (b) from real retrieved passages.
- **It also carries real outdated passages by construction.** For the 711
  SituatedQA questions whose current answer began after 2018, the Dec 2018
  Wikipedia stated what is now the old answer as current. Passages retrieved
  from that pool for those questions are real, dated (the dump date), and
  written while the old answer held. Embedding the pool is the one step in S4
  that would use the GPU; I did not run it.

**Old passages for changes before 2018, or to check the 2018 ones: Wikipedia
revisions.** For each item, take the article (via the NQ example id, once that
join is checked), fetch the revision from inside the old answer's period
through the MediaWiki API, split it into 100-word passages, and keep the
passage that states the old answer. The probe found the old answer in about
half of the old revisions it could locate. Every kept passage still needs the
hand check S5 already plans, because about half of string hits are not
statements of the answer.

**Kept as secondary sources, not the base:**
- **FreshQA snapshots** (up to 210 changes between Feb 2024 and Apr 2026,
  dated by snapshot, with source URLs). Their old answers fall inside or near
  our models' training cutoffs, so the R3 memory split may show models holding
  the old answer. But only safety papers (SCR) use FreshQA, and it shares no
  questions with NQ.
- **WikiContradict** (253 real contradicting Wikipedia passage pairs, MIT) for
  the R5 "conflict" cause.
- **HotpotQA distractor** (10 real paragraphs per question) for misretrieval
  and lost-in-the-middle, if those causes need a second base.
- **RealtimeQA** cannot supply outdated answers. Its questions are pinned to a
  week, and only about 2 recur with a changed answer.

**Not verifiable from releases:**
- The SituatedQA and RealtimeQA licences (neither repository states one).
- The NQ-example-id-to-page join.
- The two FreshQA snapshots that would not export (May 6 and May 13, 2024).
- StreamingQA evidence text and the DPR pool, both left undownloaded for size.

# Contribution screen: task prompt

Paste everything below the line into Cowork, with the bundle folder attached.
The folder holds one spreadsheet and a `pdfs/` directory with the 60 papers.

---

You are helping screen papers for an academic systematization of knowledge on
**context poisoning in LLM agents**: the problem of an agent reading content it
should not trust, whether an attacker planted it deliberately or it arrived
through ordinary pipeline failure.

Attached is a spreadsheet and a folder of PDFs. **Read the `start here`,
`contribution` and `fields` sheets first.** They define every allowed value.
Then work through the `papers` sheet, one row per paper, and fill the empty
columns from the PDF named in the `pdf` column.

## The one question

For each paper: **what does it actually contribute, and did it invent that,
improve it, or just use it?**

## How to answer it

Read in this order, and no further than you need to:

1. **Abstract and contributions list** gives you `contribution` and `origin`.
2. **The evaluation or experiments section** gives you `evaluated_against`.
3. **Related work** gives you `parent_technique`.

**Do not answer from the introduction alone.** An introduction saying "we
address context rot" is not evidence that context rot was measured. That exact
confusion is the reason this screen exists: two papers were found registered as
fixes for context rot on the strength of their framing, while their evaluations
measured report quality on a capability benchmark. Finding more of those is the
job.

`evaluated_against` must record what the evaluation section **runs the method
against**, not what the paper claims to address. If those differ, that is the
finding, and it belongs in `notes`.

## Four rules that matter more than the rest

**Every row needs a verbatim quote.** `evidence_quote` takes one sentence,
copied exactly, with its section name. No quote, no entry. If you cannot find a
sentence that supports your answer, the answer is `unsure`.

**Do not mark a paper out of scope because it proposes no technique.**
Benchmarks, surveys and measurement studies belong in this corpus. They are how
the field evaluates and they are part of what we are studying. `out_of_scope`
means something narrower: the paper is not about untrustworthy context at all.
It studies agent capability, planning or task performance, and uses the word
"context" or "long-horizon" in a different sense.

**`names_registry_technique` is the column to think hardest about.** It asks
whether the paper names a specific attack or failure mode that other papers
then cite and test against, *even if the paper is a benchmark or a harness*.
AgentDojo is an evaluation environment **and** it names seven injections that
38 of this project's confirmed defense-attack pairs depend on, so for AgentDojo
the answer is **yes**. WebArena is also a harness and names none, so **no**.
Genre does not decide this. Read the section headings and tables and answer
what the paper **names**.

**When you are not sure, write `unsure` and explain in `notes`.** An honest
`unsure` is useful. A confident wrong answer is expensive, because these
decisions remove papers from a corpus.

## Output

Fill the spreadsheet in place and return it with the same filename. Do not add,
remove or reorder rows or columns. Leave a cell blank only if the question does
not apply; blank is treated as "no decision made", which is safe.

Work through every row. If you run out of room, stop at a clean row rather than
half-filling one, and say which row number you reached.

## A note on what you are being trusted with

A paper marked out of scope is removed from the corpus, and every count in the
study moves. The ingest refuses to remove a paper on a partial answer, so an
incomplete row is safe. A confidently wrong one is not. Prefer `unsure`.

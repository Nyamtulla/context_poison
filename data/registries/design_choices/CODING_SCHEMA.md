# Design-choice coding (PAPER_PLAN S1, S2)

Purpose: measure how security papers and safety papers set up their
experiments, so the paper can state the difference as a finding and a shared
dataset can be designed to fit both. Code what the paper's **own evaluation**
did, not what the method could do in principle. Every value must come from the
paper's text (or, for S1, the released code). Never fill a field from memory or
from what is typical. If the paper does not say, write `"not stated"`.

One JSON object per method, one per line (JSONL). Fields:

| field | values | notes |
|---|---|---|
| `id` | from the worklist | |
| `name` | method name | |
| `literature` | from the worklist | security / safety (copy, do not recode) |
| `task` | `qa` / `long-form` / `agent` / `classification` / `other: ...` | what the model is asked to do in the main evaluation |
| `context_unit` | `one-passage` / `ranked-set` / `joined-set` / `long-document` / `conversation` / `tool-output` / `other: ...` | the input the method is evaluated on. `one-passage`: each question comes with a single context passage (NQ-Swap, ConFiQA, counterfactual contexts). `ranked-set`: k retrieved passages that the **method keeps separate** (votes, filters, scores each). `joined-set`: k passages concatenated into one prompt and read together. If the paper runs more than one setting, code the **main** one here and list the others in `other_units`. |
| `other_units` | list | secondary settings, e.g. `["ranked-set k=5"]` |
| `k_main` | integer or `"not stated"` | passages per question in the main setting (1 for one-passage) |
| `k_values` | list of integers | every k the paper reports |
| `passage_length` | string | e.g. `"100-word Wikipedia chunks"`, `"~2000 tokens"`, `"not stated"` |
| `hard_limit` | string | any stated cap on context length or k (input truncated at N tokens, max k). `"none stated"` if absent |
| `retrieval` | `real-retriever` / `gold-given` / `both` / `none` | did a retriever pick the passages (name it in evidence), or was the context handed to the model |
| `bad_text_kind` | list from: `optimised-attack`, `llm-written-false`, `entity-swap`, `instruction-injection`, `real-noise`, `real-outdated`, `natural-conflict`, `none`, `other: ...` | how the misleading text in the evaluation was made. `entity-swap`: answer replaced in a real passage (NQ-Swap style). `llm-written-false`: an LLM generated a passage supporting a false answer (PoisonedRAG, ConFiQA counterfactuals). `real-noise`: irrelevant or distracting retrieved passages. `real-outdated`: a genuinely old version of a fact. `natural-conflict`: real sources that disagree. |
| `bad_share` | string | how much of the context is bad, e.g. `"1 of 10"`, `"5 of 5"`, `"the whole passage"`, `"varies 1-5 of 10"` |
| `competes_with` | `memory` / `other-passages` / `both` / `instructions` / `not-applicable` | what the misleading text has to beat for the method's problem to exist. `memory`: the question is whether the model follows the context or its own knowledge. `other-passages`: correct passages are present in the same context and the bad ones must outnumber or outrank them. |
| `memory_split` | `yes` / `no` | does the evaluation split results by whether the model already knew the answer (closed-book correct vs not) |
| `metric` | list from: `attack-success`, `accuracy`, `em`, `f1`, `faithfulness-rate`, `memory-rate`, `refusal-rate`, `certified`, `detection`, `other: ...` | the headline metrics |
| `worst_case` | `yes` / `no` | is the headline number an attacker's best case (adaptive or optimised attack, attack success) rather than an average over a dataset |
| `datasets` | list | evaluation datasets, names as the paper gives them |
| `models` | list | evaluated generator models |
| `model_kind` | `base` / `instruct` / `api` / `mixed` | |
| `adaptive_attack` | `yes` / `no` / `not-applicable` | did the evaluation include an attacker who knew the method |
| `evidence` | object | for **every** field above except id/name/literature, a short verbatim quote (≤ 40 words) from the paper, with the section or table it is in, e.g. `{"k_main": "Table 2: ... top-5 retrieved passages (Sec 5.1)"}`. Use `"absent"` when the field is `"not stated"`. |
| `confidence` | `high` / `medium` / `low` | overall |
| `notes` | string | anything that does not fit: two-stage designs, a method that converts passages to weights, an evaluation that varies k as its main result |

Rules:
- Read the experimental-setup and evaluation sections, and the tables. The
  method section matters only for how passages are handled (separate or joined).
- `context_unit` is about the **evaluation input**. A method that would work
  on any input but was only evaluated on single passages is `one-passage`.
- Do not infer k from a dataset's usual setup. If the paper says "top-5", k=5;
  if it does not say, `"not stated"`.
- Quotes must be copied from the text file, not paraphrased. Hyphenation or
  line breaks from PDF extraction may be repaired; nothing else.
- Write each paper's line as soon as it is coded (append to the output file),
  so an interruption loses at most one paper. On start, skip ids already in the
  output file.

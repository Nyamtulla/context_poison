# S4: can the four safety noisy-retrieval fixes run on our setup? (2026-11-10)

Context: S3 decision 4. Two safety fixes join the rerun next to the security
defenses RobustRAG and ReliabilityRAG. Each has to read a ranked set of
passages, run on Llama-3-8B-Instruct (also Mistral-7B-Instruct, Qwen2.5-7B-Instruct)
from local weights, on one shared GPU (RTX A6000, 48 GB), with k=10 passages of
about 100 words and short NQ answers. Project rule: the authors' released code
and weights only.

Method: code was read, not run. No package was installed and no shipped script
was executed. Clones are in `data/s4_sources/repos/<name>/`. Every claim below
cites a file and line, the README, the paper, or a GitHub or Hugging Face API
response. "Not found" means it was searched for and is absent.

---

## 1. BordaRAG (f34)

- **Code.** The paper's link, `github.com/RUCYuxinLi/BordaRAG` (paper line 633), returns
  404, and that GitHub user does not exist. The same repo is at
  **`github.com/RUC-YuxinLi/BordaRAG`**, the only result of a GitHub search for
  "BordaRAG". README: "This is the official implementation of BordaRAG."
  Commit `51d5df428c4adcdb3cfec36b2732501ab3516775` (2025-08-22). Clone:
  `data/s4_sources/repos/BordaRAG/`.
- **Licence.** None. There is no LICENSE file and the GitHub API reports `license: null`.
  So the code is all-rights-reserved by default. Running it for research is
  normal practice, but we cannot redistribute it.
- **Complete?** Inference only, which is all the method needs. It is
  training-free: the generator LLM produces candidate answers, the same LLM judges
  them, and a Borda vote follows. No weights to release. The test data
  (Google-search snippets) is on Google Drive (README).
- **Unit.**
  - Stage 1: each passage is handled separately and gives its own
    candidate answer (`candidate_generator.py:35-46`).
  - Stage 2: each (candidate, passage) pair is judged separately
    (True/False probability; `preference_calculator.py:41-56`, `:78`).
  - Stage 3: the vote picks the winning answer and the k passages that rank
    it highest (`main.py:63-77`). Those passages are **joined** into one prompt
    (`main.py:82`).

  The unit is therefore a ranked set of k passages, read one at a time. This
  matches how RobustRAG and ReliabilityRAG read their input.
- **k.** Input k is whatever the data holds; the paper uses 10 Google results
  (paper Sec 5.1). The number kept for the final answer is `-topk`, default 5
  (`main.py:27`). The paper does not state the value used.
- **Generators.** Any HF model served by vLLM, with the same model in all three
  stages (`candidate_generator.py:25`, `preference_calculator.py:32`, `main.py:53`).
  The paper used Llama3-8B-Instruct, Qwen2-7B-Instruct and Mistral-7B-Instruct-v0.3.
  **Llama-3-8B-Instruct drops in directly.** Prompts go through
  `tokenizer.apply_chat_template` with a system role. Our local
  Mistral-7B-Instruct-v0.2 template accepts a system message (checked in its
  `tokenizer_config.json`). Qwen2.5 is not in the paper but needs no code change.
- **Extra trained component.** None.
- **External APIs.** None at run time. Google Custom Search was used only to
  build the authors' dataset (README).
- **GPU.** Each of the three stages makes its own `vllm.LLM(...)` at the
  default `gpu_memory_utilization` (0.9). `main.py:134-155` builds them one after
  another in one process and keeps the earlier objects referenced. This is
  inferred, not tested: the second `LLM()` will probably fail to get memory on a
  48 GB card. Each 8B model needs about 16 GB of weights in bf16, which fits the
  A6000 if the stages run one at a time. Pins: vllm 0.6.3.post1, transformers
  4.46.1, torch 2.4.0. Our `envs/reliabilityrag-venv` has vllm 0.8.3.
- **Blockers found in the released code.** It does not run as shipped:
  1. `Candidate_Generator.generate_prompts` never returns its list
     (`candidate_generator.py:31-47`; `run()` uses the result at `:69`).
     `generate_answers(None)` then raises a TypeError.
  2. `SamplingParams` sets no `logprobs` (`preference_calculator.py:34`).
     So `output.outputs[0].logprobs` is `None` and `:78` raises a TypeError.
  3. The three vLLM engines live in one process (see GPU above).

  The fixes are a missing `return prompts`, `logprobs=k` with `max_tokens=1` in
  the judge, and freeing or splitting the stages. None changes the method. We
  have to report them as bug fixes to the released code.
- **Cost.** For one question: 10 candidate calls, up to 10x10 judge calls, and
  1 final call. Calls go out one prompt at a time, not batched
  (`candidate_generator.py:61-64`).
- **Data adapter.** It expects `{"query", "context":[{"title","snippet"}], "answer"}`
  (`candidate_generator.py:49-55`). Our passages map `text` to `snippet`. That
  changes the format, not the method.

## 2. END, Early Noise Dropping (f30)

- **Code: not found.** The paper (arXiv 2502.18915v3) contains no URL to code
  or weights (searched for github, http, release, open-source). The arXiv record
  has no code comment. Hugging Face has no paper page ("Paper not found").
  GitHub repository searches found nothing: "early noise dropping",
  "END early noise dropping", "EarlyNoiseDropping", "END-denoising llm".
  The first author's GitHub account (Mooler0410, Hongye Jin) has no END repo.
  An HF model search for "early-noise-dropping" and "noise-dropping" also found
  nothing.
- **Licence, commit:** not applicable.
- **What it would need.** END puts a linear probe on an early layer of each
  generator (layer 13 in Fig. 2) to score each chunk. It drops chunks that score
  low and runs one forward pass on the rest (paper Sec 3). The probe is trained
  per model, and **no probe weights are released (not found)**. Using END would
  mean re-implementing it and training a probe for each of our models.
- **Unit (from the paper).** Chunks are scored separately and the kept chunks are
  joined. NoisyRetrieval uses 13 segments; the NQ setting does not state k.
- **Generators (paper).** Llama3-8B-Instruct, Qwen2.5-7B-Instruct, Mistral-Inst-v0.3.
  These would be ideal, but there is nothing released to run.
- **Verdict:** cannot be used under the real-code rule.

## 3. CRAG, Corrective Retrieval Augmented Generation (f03)

- **Code.** The paper's link (paper line 55) is `github.com/HuskyInSalt/CRAG`.
  Commit `de7c2961ae624a1483a138c5798e1f6d0c4fb0e0` (2024-10-08). Clone:
  `data/s4_sources/repos/CRAG/`.
- **Licence.** None. There is no LICENSE file and the GitHub API reports `license: null`.
- **Complete?** Mostly.
  - Released: evaluator training (`scripts/train_evaluator.py`, T5-large) and
    the evaluator's fine-tuned weights. These are on Google Drive (README); the
    folder lists `config.json`, `model.safetensors` and `spiece.model`.
  - Released: the knowledge-preparation and inference scripts, and precomputed
    `ref/{correct,incorrect,ambiguous}` files for PopQA, PubQA, Bio and ARC
    (`data/*/ref/`).
  - The external-knowledge path, which is web search, is broken as shipped:
    - `external_knowledge_preparation.py:147-155` calls `select_relevants(..., mode="cross_encode")`,
      but `utils.py:274` takes no `mode` argument, which raises a TypeError.
    - `utils.py:248` calls `openai.ChatCompletion` and `:253` uses `openai.error`.
      Both were removed in openai>=1.0, and `requirements.txt` pins `openai==1.4.0`.
    - `external_knowledge_preparation.py:180` keeps only the first 10 questions (`[:10]`).
  - `combined_knowledge_preparation.py` builds the Ambiguous input and fails
    three ways. It never imports `argparse` (line 2 uses it). It loops with
    `enumerate(zip(...))`, so `correct` is an int (line 13). It appends to
    `ambiguous_lines`, which is never defined (line 14). Each raises an error.
- **Unit.**
  - The evaluator scores each (question, passage) pair separately. Input is one
    `q [SEP] p` line per pair, truncated to 512 T5 tokens
    (`CRAG_Inference.py:158-171`).
  - The action is chosen over the set of k scores: Correct if any passage is
    above the upper threshold, Incorrect if all are below the lower one, and
    Ambiguous otherwise (`CRAG_Inference.py:174-196`).
  - The generator then reads **joined** text. Correct gives the top-3 passages
    by evaluator score joined with "; " (`internal_knowledge_preparation.py:61`, `utils.py:298`).
  - The plain-RAG mode joins with " [sep] " (`CRAG_Inference.py:126,131`).

  So the unit is a ranked set, scored one passage at a time.
- **k.** `--ndocs 10` (`run_crag_inference.sh`). `CRAG_Inference.py:163` hardcodes
  `n % 10`, so the code assumes exactly 10 passages per question.
- **Generators.** Any vLLM model (`CRAG_Inference.py:223`, `dtype="half"`). The
  paper used LLaMA2-hf-7b and SelfRAG-LLaMA2-7b.
  - The prompt is a raw string with no chat template (`CRAG_Inference.py:58-60`,
    `:266`). An unknown task such as NQ takes the PopQA prompt.
  - Llama-3-8B-Instruct loads without code changes, but it is prompted without
    its chat template. That matches how the authors ran their own models, and is
    still a mismatch for an instruct model.
  - Pins: vllm 0.2.5 and transformers 4.36.1. Both predate Llama-3 and Qwen2.5;
    whether they load them was not tested. A newer vLLM would be needed, and the
    code uses only `LLM` and `SamplingParams`.
- **Extra trained component.** The retrieval evaluator, a T5-large (0.77B)
  regression head. **Weights are released** (Google Drive). It was trained on
  PopQA (`run_evaluator_training.sh`, README). The thresholds are tuned per
  dataset: PopQA uses upper 0.592 and lower -0.995 (`run_crag_inference.sh`;
  the lower value is negated at `CRAG_Inference.py:221`). There are none for NQ,
  so the PopQA ones would carry over.
- **External APIs.** The Incorrect and Ambiguous actions need:
  - OpenAI `gpt-3.5-turbo-16k`, which rewrites the query (`utils.py:229-272`).
    Its current availability was not checked.
  - Serper.dev Google search (`external_knowledge_preparation.py:25-62`).
  - Live page fetching with `requests.get` (`:64-95`).
- **GPU.** The paper reports over 40 GB for LLaMA-2-7B generation on an A800
  (paper App. B). In code, vLLM starts at the default 0.9 memory share
  (`CRAG_Inference.py:223`), and then T5-large in fp32 (about 3 GB) moves to the
  same device (`:229`). On a 48 GB card that leaves about 5 GB, which is tight,
  and 0.9 cannot be granted while other users hold memory.
- **Can the web-search fallback be disabled without breaking the method? No, not
  without changing it.**
  - The Incorrect action's context is the web result alone (`CRAG_Inference.py:253-254`).
  - Ambiguous is internal plus web (`combined_knowledge_preparation.py:14`).
    Two of the three actions therefore depend on search.
  - The paper has no variant without search. Algorithm 1 lines 6-12 define both
    actions through `Web_Search`. Table 2 removes an action by merging it into
    Ambiguous, which still searches. Table 3 removes refinement, rewriting or
    selection, but never search.
  - What can run from released code is the evaluator, the action choice and
    internal refinement. The repo also has a `no_retrieval` prompt path
    (`CRAG_Inference.py:269-273`).
  - A search-free CRAG would map Incorrect to no retrieval and Ambiguous to
    internal only. That is our configuration, not the authors' method, and has
    to be labelled that way.
  - There is also a threat-model reason not to keep search. Web search gives
    CRAG a fresh source outside the poisoned corpus, which RobustRAG and
    ReliabilityRAG never get, and the cross test would not be like for like.

## 4. Knowledgeable-R1 (f71)

- **Code.** Paper link `github.com/lcy80366872/knowledgeable-R1` (paper line 39).
  Commit `1a01cbad65529ac5c8585813ba03bbabeed92c01` (2026-01-27). Clone:
  `data/s4_sources/repos/knowledgeable-R1/`. It is identical to
  `third_party/knowledgeable-R1` (same commit; `diff -rq` is empty).
- **Licence.** MIT (`LICENSE`, "Copyright (c) 2025 chenyu lin"; the GitHub API agrees).
- **Complete?** Training (verl GRPO, `training_scripts/`) and evaluation
  (`main_knowledge.py`, `eval_*.sh`) are both present. Data is on Google Drive (README).
- **Weights. This corrects CELL_CAMPAIGN.md:110 and
  SYNTHESIS_silent_corruption_cell.md:178, which say "no released weights".**
  - Trained checkpoints are on Hugging Face under user `chenyu666`, created
    2025-09-26. Repos include:
    - `chenyu666/llama3.1_8b_confiqa_mr_knowledgeable-r1` (sha `16eb94d0`, 4 shards)
    - `chenyu666/Llama-3.1-8B_conflictqa_sc_knowledgeable-r1` (`d822530a`)
    - `chenyu666/qwen2_5_7b_hotpotqa_knowledgeable-r1` (`3dc0ee64`)
    - `chenyu666/qwen2_5_7b_conflict_mc_knowledgeable-r1` (`88e81923`)
    - `chenyu666/qwen2_5_7b_conflict_mr_knowledgeable-r1` (`0d2217fd`)
    - 3B and 14B variants, and GRPO baselines
  - The Llama `config.json` has `_name_or_path`
    `checkpoints/ICLR25-knowledgeable-r1/llama3.1_8b_conflict_mr_our_32_rag_add_adv_adapt_0.01_l3/...`.
  - The README and the paper do not link these repos. The attribution rests on
    the author's name (Chenyu Lin) and the matching run names, not on an
    official link.
- **Unit.** Joined text. The top-5 passages are formatted as
  `[webpage i begin]...` blocks and joined into one string (`data_process/hotpot.py:2-12`).
  ConFiQA's context is a single pre-joined string (`data_process/conflict_qa.py:15`).
  That string goes before the question in one prompt (`data_process/processing_knowledge.py:21-25`).
  Each passage is not handled separately. This is the "document or memory" kind
  of fix, not "which passage is right".
- **k.** 5, hardcoded (`main_knowledge.py:47`).
- **Generators.** It is an RL-tuned replacement for the generator, not an add-on
  to it. Checkpoints exist for Qwen2.5-3B/7B/14B-Instruct and Llama-3.1-8B-Instruct
  (README line 80; HF).
  - **Llama-3-8B-Instruct and Mistral cannot be dropped in.** Doing so needs
    retraining. Training asks for 8 GPUs (`training_scripts/config.yaml:83`
    `n_gpus_per_node: 8`; the script sets rollout `tensor_parallel_size=4` and
    `n=16`), which is not feasible on one shared GPU.
  - Qwen2.5-7B-Instruct, which we use, has released checkpoints.
- **Prompt mismatch.** Evaluation hardcodes Qwen's ChatML template
  (`processing_knowledge.py:25`) for every model, the Llama-3.1 checkpoints
  included. Training applies each model's own chat template
  (`verl/utils/dataset.py:156`).
- **Extra component.** None beyond the tuned generator.
- **External APIs.** None at inference. The eval scripts export a dummy
  `GOOGLE_API_KEY` that the code does not use. Training uses wandb and swanlab keys.
- **GPU.** Inference uses vLLM at `gpu_memory_utilization=0.7` with
  `max_model_len 8192` (`main_knowledge.py:114-121`). That is about 34 GB of 48 GB,
  and it fits one A6000.
- **Blockers.** Not on our main generator; the input is joined text; and the
  checkpoints are trained on ConFiQA and HotpotQA, not NQ.

---

## Summary table

| | BordaRAG (f34) | END (f30) | CRAG (f03) | Knowledgeable-R1 (f71) |
|---|---|---|---|---|
| Official code | `RUC-YuxinLi/BordaRAG` @ `51d5df4` (paper link 404s: typo) | **not found** | `HuskyInSalt/CRAG` @ `de7c296` | `lcy80366872/knowledgeable-R1` @ `1a01cba` |
| Licence | none | – | none | MIT |
| Complete | inference only; training-free, so nothing missing | no | training + inference + evaluator weights; web-search path broken | training + eval; checkpoints on HF (not linked from README) |
| Unit in code | each passage separately (`candidate_generator.py:35-46`, `preference_calculator.py:41-56`), top-k then joined (`main.py:82`) | (paper) chunk-wise probe, kept chunks joined | evaluator per passage (`CRAG_Inference.py:158-171`), generator gets joined top-3 (`internal_knowledge_preparation.py:61`) | joined text (`hotpot.py:2-12`, `processing_knowledge.py:22`) |
| k | input 10 (paper); keeps `-topk` default 5 (`main.py:27`) | 13 segments (paper) | 10, hardcoded (`CRAG_Inference.py:163`) | 5, hardcoded (`main_knowledge.py:47`) |
| Generators | any vLLM; paper: Llama3-8B-Inst, Qwen2-7B-Inst, Mistral-7B-Inst-v0.3 | (paper) same three | any vLLM, raw prompt; paper: LLaMA2-7B, SelfRAG | own RL checkpoints: Qwen2.5-3/7/14B, Llama-3.1-8B |
| Llama-3-8B-Inst drop-in | **yes** | – | loads, no chat template; pinned vllm 0.2.5 too old | **no** (needs 8-GPU RL training) |
| Extra trained part | none | per-model linear probe, **not released** | T5-large evaluator, **released** (Drive), PopQA-trained | the generator itself |
| External APIs | none | – | OpenAI gpt-3.5-turbo-16k + Serper web search (Incorrect/Ambiguous) | none |
| GPU | 3 vLLM engines at 0.9 in one process: run stages separately; ~16 GB each | – | vLLM 0.9 + T5-large on same device: tight on 48 GB | vLLM 0.7, ~34 GB |
| Runs as shipped? | no: 2 one-line bugs + engine memory | – | internal path yes; search/ambiguous path no (3 bugs) | yes, on its own checkpoints |
| Search removable? | – | – | **no** without changing the method (2 of 3 actions use it; no paper ablation without it) | – |

## Recommendation

**1. BordaRAG.** This is the clear first choice:
- It reads the ranked set one passage at a time and votes, which is the same
  question RobustRAG and ReliabilityRAG ask.
- It is training-free, with no extra weights and no APIs.
- Our three generators drop in, and two of them are the ones its paper used.
- The cost is two one-line bug fixes and running the three stages in separate
  processes. The fixes have to be reported as fixes to the released code.

**2. CRAG, restricted to no search and labelled as our configuration.** This is
the second choice:
- It is the only other candidate whose released code scores each passage of a
  ranked set of 10, and its evaluator weights are released.
- It must run without web search. Two reasons: the search pipeline does not run
  as shipped, and search would give CRAG a clean source the security defenses
  never get.
- Incorrect becomes the repo's own `no_retrieval` path, and Ambiguous becomes
  internal refinement only. The paper defines no such variant, so the result is
  "CRAG's evaluator and refinement, search disabled", not CRAG as published.
- Other caveats: the PopQA-trained evaluator and thresholds carry over to NQ;
  the generator gets no chat template; and a vLLM newer than the pinned 0.2.5 is needed.

**Not chosen.**
- END: no code or probe weights were found, so it cannot meet the real-code rule.
- Knowledgeable-R1: weights exist after all, but it reads joined text (k=5).
  It also replaces the generator: Llama-3.1-8B or Qwen2.5-7B only, with no
  Llama-3-8B or Mistral without 8-GPU training. It suits the document-or-memory
  comparison better. If the lead prefers released code run unmodified over a
  ranked-set unit, it is the alternative to CRAG, on Qwen2.5-7B only.

# Silent-corruption cell: incidental defenses vs deliberate attack

Working through every incidental-validated defense in the silent-corruption
cell against the reconstructed corpus-poisoning attack. **The SoK's central
claim, tested one defense at a time.**

Standing rules for every entry:
- **The control gates the result.** If a defense cannot reproduce its own
  benefit on its own benchmark, no transfer number is reported from it.
- **Verdicts gated on minimum detectable change** (α=.05, power=.80).
- **Scoring, prompts and generation are the authors' own code**, imported
  unchanged. Harness adaptation is allowed; evaluation rubrics are not touched.
- **Roadblocks are recorded, not worked around silently**, then we move on.

Attack held constant: the adversarial passage from
`corpus_poisoning_harness/attack_reconstruction.md` (82.3 % top-20 retrieval on
NQ), injected at 10 / 50 / 100 % of the context.

## Results

| defense | venue | control | transfer verdict | n | mdr |
|---|---|---|---|---:|---:|
| **ParamMute** | NeurIPS 2025 | **fires** (+9.3 pp ctx, −12.4 pp mr) | **HARMFUL — 13.5 pp more damage than undefended** | 1409 | 5.3 pp |
| FaithfulRAG | ACL 2025 | **fails** (−5.0 pp, below threshold) | not reportable | 400 | 9.9 pp |
| CK-PLUG | arXiv 2025 | mechanism engages, no net benefit (mr −10.7 pp, ctx −5.0 pp) | *full run, n=800* | | 7.0 pp |

## Roadblocks

| defense | blocker |
|---|---|
| FaithfulRAG | CoT paths need OpenAI JSON mode; stripping the flag makes them run and score 0.0 %. Only the ablated `wo_cot` runs on open weights, and its control does not fire. |
| JUICE | Viable but four-stage: NQ-Swap download → `generate_dataset_split.py` → `dataset.py` per model → head selection → intervention. The repo ships only a README pointing at the HF dataset, and `head_size_N/test.json` must be built. Needs `nnsight`. |
| **SABER** | **BLOCKED at stage 3 of 6.** Stages 1–3a completed (PK/CK labelling, self-prior extraction, K=3 trace generation for all 7 datasets). Stage 3b needs `prompts/multipath_prompts.yaml` with keys `prompt_1_reasoning_ck`, `prompt_1_reasoning_pk`, `prompt_2_judgment` — **the file is not in the repo**. It is not gitignored; the repo is a single anonymised commit and it was dropped. Those three templates *are* the self-evaluation method, so writing them myself would be inventing SABER, not reproducing it. Five further defects hit on the way, below. |

## What setting these up keeps turning into: a reproducibility finding

None of this is cherry-picked; it is every obstacle hit, in order, across five
repos from this one cell.

| defect | repos |
|---|---|
| **Dead `vllm` import** blocking startup — `from vllm import LLM, SamplingParams`, name never used anywhere in the package | FaithfulRAG, CK-PLUG |
| **Eval script contradicts the module's own default**, injecting sampling noise larger than the measured effect (`top_k` 1 → 100; identical conditions drifted 58–63 %) | CK-PLUG |
| **Undocumented sign convention on the main knob.** `alpha * parametric + (1-alpha) * context`, with the script defaulting to a 50/50 mix — running the default tests the opposite of the paper's direction | CK-PLUG |
| **Headline configuration silently needs a commercial API.** Open-weight path is an ablation the paper never reports separately | FaithfulRAG |
| **Deprecated API in the shipped code** (`temperature=0.0` into `generate`; `batch_encode_plus`) | FaithfulRAG, corpus-poisoning |
| **Ships a full fork of `transformers`** that must be installed in place of the real one | ParamMute, CK-PLUG |
| **Missing module-level constant** — `saber.config` never defines `HF_CACHE_DIR`, which two extract modules import at line 34/48 and use as `cache_dir`. Every GPU stage dies on import | SABER |
| **Shipped run scripts do not match their modules' CLIs** — `01` passes `--in-jsonl/--out-jsonl`, `02` passes `--split-file/--out`; the modules take `--datasets/--out-dir`. The documented end-to-end command cannot run | SABER |
| **Code reads the wrong key from its own shipped data** — `multipath_vllm_gen` does `manifest["datasets"].items()`, but in `saber_split.json` `datasets` is a list of names and the qids live under `partition` | SABER |
| **A required prompt file is absent from the repository** | SABER |
| **CUDA 13 wheels resolved by default** on a CUDA 12.2 driver, so `torch.cuda.is_available()` is False until pinned | JUICE, SABER |

The smoke test is worth singling out. SABER ships a genuinely good one — it
passes cleanly, reports **ALL SMOKE CHECKS PASSED**, and the pipeline then
fails on the very next command. It `--help`s four entry points, none of them in
the `extract` package where all five defects live.

Five of six are silent: the code runs and produces numbers that are wrong or
noisy rather than failing. Every one was found by insisting the control fire
before reading a result.

## Queue

Ordered by expected runnability. `api=N` throughout — an OpenAI dependency is
what made FaithfulRAG unreadable.

1. **CK-PLUG** (arXiv 2025) — token-level fusion of parametric/contextual
   distributions. Ships a transformers fork; `mode=base_rag` vs `mode=ck` is a
   clean on/off. Same metric family as ParamMute, so directly comparable.
2. **SABER** (arXiv 2026) — belief estimation **with abstention**. The only
   candidate whose mechanism is *arbitration* rather than *trust the context
   more*, so the one most likely to actually transfer.
3. **JUICE** (ICML 2025) — dual-run attention-head intervention.
4. **SpARE** (NAACL 2024) — sparse-autoencoder representation engineering.
5. **KScope** (NeurIPS 2025) — constrained context summarization. Notebook-driven.
6. **Knowledgeable-R1** (arXiv 2025) — RL-trained; needs a trained checkpoint.
7. **SHIFT** (arXiv 2026) — gate-modulated activation steering.
8. **COMBO** (EMNLP 2023) — RQ6 previously found no released checkpoint.
9. **DCD** (arXiv 2024) — cross-modal VLM; different channel, likely out of scope.
10. **VideoSEAL** (arXiv 2026) — video; out of scope.

## The prediction being tested

Defenses in this cell mostly work by **increasing reliance on retrieved
context** at the expense of parametric memory. That is correct when context is
merely stale or conflicting — the incidental case — and removes the model's
only fallback when an attacker controls the context. ParamMute confirmed the
strong form of this. CK-PLUG, Knowledgeable-R1 and SpARE are in the same
family; SABER is not, which is what makes it the interesting one.

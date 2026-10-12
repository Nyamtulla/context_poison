# DyPRAG setup notes

`third_party/` is gitignored, so this records what has to exist on disk before
`scripts/dyprag_vs_corpus_poisoning.py` will run.

## What the paper says vs what is actually released

The README's news item (18 Apr 2025) says only the Llama3.2-1B and Qwen2.5-1.5B
parameter translators are released, "others coming soon". **That is out of
date.** The linked Drive folder actually contains four checkpoints, two of them
for Llama-3-8B:

| file | size |
|---|---|
| `llama3-8b-p32-1ep-main-2400sample.pt` | 554 MB |
| `llama3-8b-p32-1ep-main-480sample(2WQA).pt` | 554 MB |
| `llama3.2-1b-p32-1ep-main-4800sample.pt` | 151 MB |
| `qwen2.5-1.5b-p32-ep1-main-4800sample.pt` | 259 MB |

This matters: it means DyPRAG runs on the **same Llama-3-8B-Instruct** as every
other defense in the cell, so no model substitution is needed and the result is
directly comparable. Had only the 1B/1.5B translators existed, DyPRAG would
have had to run on a different backbone and the comparison would have been
confounded with model size - the variable `model_dependence.md` already shows
dominates this matrix.

The 2400sample checkpoint is the main one; the 480sample one is 2WikiMultihopQA
specific. We use the main one.

## Reproducing

```bash
cd third_party
git clone --depth 1 https://github.com/Trae1ounG/DyPRAG.git
cd DyPRAG
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python \
    gdown transformers==4.49.0 peft==0.13.2 numpy pandas termcolor \
    accelerate sentencepiece protobuf torch
mkdir -p projector_dl
.venv/bin/python -m gdown --folder \
    "https://drive.google.com/drive/folders/1FLu3_rMcAMaXfQKQSqf6nALhBv841-ko" \
    -O projector_dl
```

## Checkpoint shape, verified against the architecture

The released llama3-8b checkpoint has 768 tensors and matches
`ParameterTranslator(["down_proj","up_proj","gate_proj"], range(32), 4096,
14336, lora_rank=2, hidden_dim=32)`:

- `pre_A_linear.weight` is `(32, 4097)` - hidden_size 4096 plus the layer index
  the Projector concatenates
- `post_A_linear.weight` for `down_proj` is `(28672, 32)` = intermediate_size
  14336 x lora_rank 2
- `post_B_linear.weight` is `(8192, 32)` = hidden_size 4096 x lora_rank 2
- layers 0..31, modules down_proj / gate_proj / up_proj

So `--lora_rank 2 --projector_p 32` are not guesses; they are the only values
consistent with the released tensor shapes, and they match
`configs/DyPRAG/inference_main.sh`.

## Deviations from requirement.sh

- `torch==2.1.0` is pinned but the installed torch is newer; nothing in the
  DyPRAG path depends on the pinned version.
- `transformers==4.49.0` and `peft==0.13.2` are installed exactly as pinned.
  These are not optional: `delta_inject` sets a `delta` attribute that only
  their vendored `src/models/modeling_llama.py` reads, and that file tracks a
  specific transformers internal layout.
- `elasticsearch` and `faiss-cpu` are skipped. They are for BM25 retrieval over
  a Wikipedia dump, and this harness supplies the context itself - the same
  choice made for every other defense in the cell.

## Hardcoded paths that must be patched

- `src/root_dir_path.py` sets `ROOT_DIR = "/netdisk/tanyuqiao/PRAG"`, the
  authors' machine. The runner overrides it before their modules use it.
- `src/utils.py:get_model_path` has an empty `path = ""` placeholder for the
  three named models, but falls through to returning the name unchanged for
  anything else, so an HF repo id can be passed straight in.

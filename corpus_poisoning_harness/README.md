# Corpus poisoning (Zhong et al., EMNLP 2023) — genuine reconstruction

The first deliberate cause in the **silent-corruption** cell. Tests whether
defenses built for *incidental* RAG corruption survive corruption that was
optimized to happen.

Attack: `github.com/princeton-nlp/corpus-poisoning` (authors' released code,
unmodified). Clone lives in `third_party/corpus-poisoning` — gitignored,
it has its own git history.

## Setup, and the two things that bite

```bash
cd third_party
git clone --depth 1 https://github.com/princeton-nlp/corpus-poisoning.git
cd corpus-poisoning
(cd src && git clone --depth 1 https://github.com/facebookresearch/contriever.git)
uv venv .venv --python 3.11
VIRTUAL_ENV=.venv uv pip install torch --torch-backend=cu128
VIRTUAL_ENV=.venv uv pip install beir transformers sentence-transformers \
    datasets scikit-learn pandas pytrec_eval-terrier
```

**1. The pinned requirements are not needed.** `requirements.txt` pins
python 3.7, `torch==1.10.2`, `transformers==4.21.1`. None of that installs on
a CUDA 12.x box, and none of it is necessary: the code runs unmodified on
**torch 2.11.0+cu128 and transformers 5.18.0**. Nothing was patched.

**2. There is a `src/` name collision, and the path order is the whole fix.**
corpus-poisoning has `src/utils.py`; contriever has `src/contriever/src/utils.py`
and its `contriever.py` does `from src import utils`. Get the order wrong and
you get a circular-import error that looks like a broken clone. The order that
works:

```bash
PYTHONPATH="src:src/contriever:src/contriever/src"
```

corpus-poisoning's `src` first (so bare `utils` is its own), then contriever's
repo root (its `src/` has `__init__.py`, so it wins `import src` as a regular
package over the namespace dir), then contriever's `src` (so bare `contriever`
and `beir_utils` resolve to modules rather than the namespace directory).

## Running the attack

```bash
PYTHONPATH="src:src/contriever:src/contriever/src" .venv/bin/python -u src/attack_poison.py \
  --dataset nq-train --split train --model_code contriever \
  --num_cand 100 --per_gpu_eval_batch_size 64 --num_iter 5000 --num_grad_iter 1 \
  --output_file results/advp/nq-train-contriever-k1-s0.json --k 1 --kmeans_split 0
```

## Cost, measured on this box (RTX A6000)

| | |
|---|---|
| per iteration | ~11 s |
| 5000 iterations (paper default), k=1 | **~15 h** |
| **VRAM** | **712 MiB** |
| BEIR `nq-train` download | 7.2 GB, one time |

The VRAM number is the one that matters on a shared machine: this is a long
job but not a blocking one — it leaves 48 of 49 GB free. It is not idle VRAM.

## Reading `best_acc` — it is not attack success

`evaluate_acc` returns the fraction of queries where the **gold** passage still
scores above the adversarial passage. **Lower is better for the attacker.**
0.992 at iteration 1 means the attack has done nothing yet; the paper's
headline (>75 % success with a single passage against unsupervised Contriever)
corresponds to driving this far down. Observed descent on this box:

| iteration | best_acc |
|---:|---:|
| 1 | 0.992 |
| 10 | 0.987 |
| 30 | 0.952 |
| 50 | 0.873 |

Attack success proper is measured afterwards by `evaluate_adv.py`, which asks
whether an adversarial passage outranks the top-20 of the clean corpus.

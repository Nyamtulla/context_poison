#!/bin/bash
# CPU-side preparation for CheckRLM (third_party/CheckRLM).
#
# CheckRLM is a reasoning-stage defense for the RAG x reasoning-corruption
# cell, which no paper in the corpus has tested against any mechanism. Running
# it needs three things this script does without touching the GPU: its own
# dependency set (it pins Python 3.12 against our 3.10), its retrieval corpus,
# and its config pointed at this checkout and at one card. The GPU half -- two
# vLLM services, the dense index and the runs -- is a separate job, because
# the card is shared.
#
# Dataset: 2wikimultihopqa, which is their own default in config.sh. Their
# downloader fetches five corpora; we fetch one. HotpotQA would have been the
# other candidate and is not reachable from this box: its corpus lives on
# nlp.stanford.edu, which does not answer here, while the Dropbox, KILT and
# IIRC hosts in the same script do.
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
CR="$REPO/third_party/CheckRLM"
LIBS="$REPO/envs/checkrlm-libs"
LOG="$REPO/data/registries/raw/checkrlm_prep.log"
mkdir -p "$(dirname "$LOG")"
exec > >(tee -a "$LOG") 2>&1
echo "=== checkrlm prep $(date -Is) ==="

# There is no python3-venv on this box, which is why every other defense here
# is a --target directory on PYTHONPATH rather than a virtualenv. Same pattern.
mkdir -p "$LIBS"
# Their requirement.txt pins `faiss==1.9.0`, which is not a package: FAISS
# ships as faiss-cpu and faiss-gpu. The pinned VERSION exists under both, so
# the substitution is the distribution name and nothing else. Recorded here
# because a pin that cannot resolve is an artifact finding, not a detail.
REQ="$LIBS/requirement.resolved.txt"
sed 's|^faiss==1\.9\.0$|faiss-cpu==1.9.0|' "$CR/requirement.txt" > "$REQ"
if [ ! -s "$LIBS/.deps_ok" ]; then
    python3 -m pip install -q --target "$LIBS" -r "$REQ" || {
        echo "PREP FAILED: requirements did not install"; exit 1; }
    touch "$LIBS/.deps_ok"
fi
echo "deps: $(du -sh "$LIBS" | cut -f1)"

# ---------------------------------------------------------------------------
# config: one card, two 8B services
# ---------------------------------------------------------------------------
# Their config runs the reasoning model across two GPUs at 0.9 memory each and
# pairs it with a 14B check model. We have one 48 GB card and the grid shares
# it, so both services are Qwen3-8B -- a reasoning backbone and a check
# backbone the paper itself reports -- at a memory split that fits beside each
# other. Decoding parameters are the authors' own row for Qwen3-8B.
cfg="$CR/src/scripts/config.sh"
[ -f "$cfg.orig" ] || cp "$cfg" "$cfg.orig"
sed -i \
  -e "s|^PROJECT_ROOT=\"\"|PROJECT_ROOT=\"$CR\"|" \
  -e 's|^REASONING_MODEL_PATH="" |REASONING_MODEL_PATH="Qwen/Qwen3-8B" |' \
  -e 's|^CHECK_MODEL_PATH="" |CHECK_MODEL_PATH="Qwen/Qwen3-8B" |' \
  -e 's|^REASONING_TENSOR_PARALLEL_SIZE=2|REASONING_TENSOR_PARALLEL_SIZE=1|' \
  -e 's|^DATASET_NAME="[a-z0-9]*"|DATASET_NAME="2wikimultihopqa"|' \
  -e 's|^REASONING_GPU_MEMORY_UTILIZATION=0.9|REASONING_GPU_MEMORY_UTILIZATION=0.42|' \
  -e 's|^CHECK_GPU_MEMORY_UTILIZATION=0.9|CHECK_GPU_MEMORY_UTILIZATION=0.40|' \
  "$cfg"
grep -q 'Qwen3-8B' "$cfg" || { echo "PREP FAILED: config not patched"; exit 1; }

# Their launchers hard-code CUDA_VISIBLE_DEVICES=2 and =3, the cards the
# authors had. This box has one.
for s in start_check_model.sh start_reasoning_model.sh; do
    [ -f "$CR/src/scripts/$s.orig" ] || cp "$CR/src/scripts/$s" "$CR/src/scripts/$s.orig"
    sed -i 's|^CUDA_VISIBLE_DEVICES=[0-9,]* vllm serve|CUDA_VISIBLE_DEVICES=0 vllm serve|' \
        "$CR/src/scripts/$s"
done

# The check model's decoding parameters belong to the backbone, and their
# shipped values are the 14B row (greedy). Qwen3-8B is their 0.7/0.8/20 row.
# This is the one place in the campaign that does not decode greedily, so the
# threats section cannot claim byte-identical reruns for these cells.
yml="$CR/src/config/check_model.yaml"
[ -f "$yml.orig" ] || cp "$yml" "$yml.orig"
sed -i -e 's|^  temperature: 0\([^.]\)|  temperature: 0.7\1|' \
       -e 's|^  top_p: 0.95|  top_p: 0.8|' \
       -e 's|^  top_k: -1|  top_k: 20|' "$yml"

# ---------------------------------------------------------------------------
# corpus
# ---------------------------------------------------------------------------
WIKI="$CR/data/2wikimultihopqa/corpus"
mkdir -p "$WIKI"
if [ ! -s "$WIKI/train.json" ]; then
    tmp="$(mktemp -d)"
    wget -q --show-progress "https://www.dropbox.com/s/7ep3h8unu2njfxv/data_ids.zip?dl=1" \
        -O "$tmp/2wiki.zip" || { echo "PREP FAILED: corpus download"; exit 1; }
    unzip -jo "$tmp/2wiki.zip" -d "$WIKI" -x "*.DS_Store" >/dev/null
    find "$WIKI" -maxdepth 1 -name '._*' -delete
    # Keep exactly what their own script keeps.
    for f in "$WIKI"/*; do
        case "$(basename "$f")" in
            id_aliases.json|train.json|dev.json|test.json) ;;
            *) rm -f "$f" ;;
        esac
    done
    rm -rf "$tmp"
fi
echo "corpus: $(du -sh "$WIKI" | cut -f1)  files: $(ls "$WIKI" | tr '\n' ' ')"
echo "=== prep done $(date -Is) ==="

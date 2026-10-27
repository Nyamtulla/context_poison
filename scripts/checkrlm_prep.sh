#!/bin/bash
# CPU-side preparation for CheckRLM (third_party/CheckRLM).
#
# CheckRLM is a reasoning-stage defense for the RAG x reasoning-corruption
# cell, which no paper in the corpus has tested against any mechanism. Running
# it needs three things this script does without touching the GPU: its own
# Python environment (it pins 3.12 against our 3.10), its retrieval corpus,
# and its config pointed at this checkout. The GPU half -- two vLLM services
# and the dense index -- is a separate job, because the card is shared.
#
# Only HotpotQA is fetched. Their downloader pulls five corpora including the
# full KILT knowledge source, which is tens of gigabytes and four datasets we
# have no use for.
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
python3 -m pip install -q --target "$LIBS" -r "$REQ" || {
    echo "PREP FAILED: requirement.txt did not install"; exit 1; }

# Their config.sh ships with PROJECT_ROOT empty and tensor parallel 2. We have
# one card, so the reasoning service runs tp=1. Nothing else is changed.
cfg="$CR/src/scripts/config.sh"
[ -f "$cfg.orig" ] || cp "$cfg" "$cfg.orig"
sed -i "s|^PROJECT_ROOT=\"\"|PROJECT_ROOT=\"$CR\"|" "$cfg"
sed -i 's|^REASONING_TENSOR_PARALLEL_SIZE=2|REASONING_TENSOR_PARALLEL_SIZE=1|' "$cfg"
sed -i 's|^DATASET_NAME="2wikimultihopqa"|DATASET_NAME="hotpotqa"|' "$cfg"

mkdir -p "$CR/data/hotpotqa/corpus"
cd "$CR/data/hotpotqa/corpus" || exit 1
if [ ! -s enwiki-20171001-pages-meta-current-withlinks-abstracts.tar.bz2 ] \
   && [ ! -d enwiki-20171001-pages-meta-current-withlinks-abstracts ]; then
    wget -q --show-progress \
      "https://nlp.stanford.edu/projects/hotpotqa/enwiki-20171001-pages-meta-current-withlinks-abstracts.tar.bz2" \
      -O enwiki-abstracts.tar.bz2 || { echo "PREP FAILED: corpus download"; exit 1; }
    tar -xjf enwiki-abstracts.tar.bz2 && rm -f enwiki-abstracts.tar.bz2
fi
echo "corpus: $(du -sh "$CR/data/hotpotqa/corpus" | cut -f1)"
echo "=== prep done $(date -Is) ==="

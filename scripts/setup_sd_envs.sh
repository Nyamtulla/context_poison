#!/bin/bash
# Build the pinned environments the second-direction defenses run in.
#
# Each defense keeps its authors' own dependency set, as ACD, CK-PLUG, DyPRAG
# and RobustRAG already do under envs/. Three of these are too large or too
# entangled for a PYTHONPATH overlay -- ReliabilityRAG needs vLLM, AttnTrace
# pins its whole stack, DataSentinel pins torch 2.3 and an 8-bit loader -- so
# they get a virtual environment each. Nothing here touches the GPU.
#
#   scripts/setup_sd_envs.sh             # build whatever is missing
#   scripts/setup_sd_envs.sh attntrace   # just one
set -u
cd "$(dirname "$0")/.."
E=envs
UV="${UV:-$HOME/.local/bin/uv}"

build() {  # name, then pip arguments
    local name=$1; shift
    local venv="$E/$name-venv"
    if [ -x "$venv/bin/python" ] && [ -f "$venv/.complete" ]; then
        echo "[skip] $name"; return 0
    fi
    echo "[build] $name $(date +%H:%M)"
    "$UV" venv --quiet --clear --python 3.10 "$venv" || return 1
    "$UV" pip install --python "$venv/bin/python" "$@" > "$E/$name-install.log" 2>&1
    local rc=$?
    [ $rc -eq 0 ] && touch "$venv/.complete"
    echo "[done ] $name exit $rc $(date +%H:%M)"
    return $rc
}

want() { [ $# -eq 0 ] || [[ " $* " == *" $1 "* ]]; }
ARGS="$*"

# ReliabilityRAG: the authors' requirements.txt, which pins vLLM 0.8.3 on
# torch 2.6. flashinfer is an optional vLLM kernel that builds from source and
# changes nothing about greedy decoding, so it is left out. sentencepiece and
# protobuf are what the DeBERTa-v3 NLI tokenizer their MIS step loads needs.
if [ -z "$ARGS" ] || [[ " $ARGS " == *" reliabilityrag "* ]]; then
    # litellm 1.35.1 is no longer on PyPI; it serves only their API-model
    # classes, which no run here instantiates, so it is left unpinned.
    grep -v '^flashinfer' third_party/ReliabilityRAG/requirements.txt \
        | sed 's/^litellm==.*/litellm/' > "$E/reliabilityrag-requirements.txt"
    # src/defense.py imports sentence_transformers, which their requirements
    # omit; 3.4.1 is the newest release that leaves their transformers pin.
    echo -e "sentencepiece\nprotobuf\nsentence-transformers==3.4.1" \
        >> "$E/reliabilityrag-requirements.txt"
    build reliabilityrag -r "$E/reliabilityrag-requirements.txt"
fi

# AttnTrace: the authors' full requirements.txt, as released, except that
# flash-attn 2.7.0.post2 comes from the project's own prebuilt wheel for this
# torch and python rather than from source: the source build needs nvcc, which
# this box does not have. Same version, same kernels.
FA_WHEEL="https://github.com/Dao-AILab/flash-attention/releases/download/v2.7.0.post2/flash_attn-2.7.0.post2+cu12torch2.5cxx11abiFALSE-cp310-cp310-linux_x86_64.whl"
if [ -z "$ARGS" ] || [[ " $ARGS " == *" attntrace "* ]]; then
    grep -v '^flash-attn' third_party/AttnTrace/requirements.txt \
        > "$E/attntrace-requirements.txt"
    echo "flash-attn @ $FA_WHEEL" >> "$E/attntrace-requirements.txt"
    build attntrace -r "$E/attntrace-requirements.txt"
fi

# DataSentinel: the pip pins of Open-Prompt-Injection's environment.yml.
if [ -z "$ARGS" ] || [[ " $ARGS " == *" datasentinel "* ]]; then
    # conda ships setuptools in every env, and their environment.yml takes spacy
    # from the conda channel; peft and their PromptLocate import them at load.
    build datasentinel -r "$E/datasentinel-requirements.txt" "setuptools<70" spacy
fi

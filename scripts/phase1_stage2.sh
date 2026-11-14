#!/bin/bash
# Phase 1, stage 2: the proposed fix on Mistral-7B across every condition,
# then ReliabilityRAG on the attack conditions it had not run. Each step waits
# behind other users (gpu_gate), resumes from its answer log, and exits when
# done, so nothing stays resident on the shared card.
cd "$(dirname "$0")/.."
PY=envs/reliabilityrag-venv/bin/python
L=data/sd_queue/phase1_stage2.log
mkdir -p data/sd_queue
step() { python3 scripts/gpu_gate.py --need_gb 28 >> $L 2>&1 || exit 1
         echo "[start] $* $(date '+%m-%d %H:%M')" >> $L
         HF_HUB_OFFLINE=1 "$@" >> $L 2>&1 && echo "[done] $* $(date '+%m-%d %H:%M')" >> $L \
           || { echo "[FAIL] $*" >> $L; exit 1; }; }
for f in incidental_stale incidental_stale_reworded distractor_evidence misretrieval context_dilution \
         p1_poisonedrag p1_poisonedrag_distinct p1_corpus_poisoning p1_badrag_dos p1_badrag_sentiment; do
  step $PY scripts/sd_specvote.py --failure $f --model mistral7b
done
for f in p1_poisonedrag p1_poisonedrag_distinct p1_corpus_poisoning p1_badrag_dos p1_badrag_sentiment; do
  step $PY scripts/sd_reliabilityrag.py --failure $f --out data/registries/ours/baseline_reliabilityrag_${f}_mistral7b.json
done
echo "[stage 2 complete] $(date '+%m-%d %H:%M')" >> $L

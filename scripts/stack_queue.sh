#!/bin/bash
# RQ4, measured: every stacked cell, one after another on the shared card.
# Each run is resumable (data/stack_logs/), so rerunning this after a crash
# picks up where it stopped. Nothing stays resident: each cell is its own
# process, and the card is free when the queue ends.
#
#   nohup scripts/stack_queue.sh > data/stack_logs/queue.log 2>&1 &
cd "$(dirname "$0")/.." || exit 1
FIX=${FIX:-acd}
MECHS=${MECHS:-"incidental_stale p1_poisonedrag_distinct distractor_evidence p1_badrag_dos misretrieval p1_corpus_poisoning"}
for m in $MECHS; do
    if [ -f "data/registries/stack_${FIX}_${m}.json" ]; then
        echo "[skip] $m"; continue
    fi
    echo "[start] $FIX $m $(date '+%m-%d %H:%M')"
    PYTHONPATH=envs/acd-libs python3 scripts/stack_run.py --fix "$FIX" \
        --mechanism "$m" > "data/stack_logs/run_${FIX}_${m}.log" 2>&1
    rc=$?
    echo "[done ] $FIX $m exit $rc $(date '+%m-%d %H:%M')"
    tail -4 "data/stack_logs/run_${FIX}_${m}.log"
done
echo "queue complete $(date '+%m-%d %H:%M')"

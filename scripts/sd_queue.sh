#!/bin/bash
# The second-direction campaign, queued behind everyone else on the card.
#
# Every GPU step first waits at scripts/gpu_gate.py until no other user has a
# process on the card and enough memory is free, so it never shares the card
# with someone else's job. Steps run one at a time and each exits when done,
# which frees the card for whoever is next.
#
#   stage A  smoke: 5 items, stale document, 0/1/5 passages, every defense
#   stage B  controls: each traced/consistency defense on PoisonedRAG
#   check    scripts/sd_smoke_check.py; the full runs start only if it passes
#   stage C  full: every defense on all four honest failures
#
# Resumable: every cell logs each answer, a finished cell is skipped, and a
# restarted queue picks up where it stopped.
#
#   setsid nohup scripts/sd_queue.sh > data/sd_queue/queue.log 2>&1 &
set -u
cd "$(dirname "$0")/.."
Q=data/sd_queue
mkdir -p "$Q"
RR="env PYTHONPATH=envs/robustrag-libs python3"
RELI=envs/reliabilityrag-venv/bin/python
ATT=envs/attntrace-venv/bin/python
DSV=envs/datasentinel-venv/bin/python
FAILURES="incidental_stale distractor_evidence misretrieval context_dilution"

step() {  # name, GB needed, command...
    local name=$1 need=$2; shift 2
    if [ -f "$Q/$name.done" ]; then echo "[skip] $name"; return 0; fi
    python3 scripts/gpu_gate.py --need_gb "$need" || return 1
    echo "[start] $name $(date '+%m-%d %H:%M')"
    "$@" > "$Q/$name.log" 2>&1
    local rc=$?
    echo "[done ] $name exit $rc $(date '+%m-%d %H:%M')"
    [ $rc -eq 0 ] && touch "$Q/$name.done"
    return $rc
}

SM="--n 5 --doses 0 1 5"
# ---- stage A: smoke -------------------------------------------------------
step datasentinel_smoke 10 $DSV scripts/sd_detect_datasentinel.py --n 5 --controls
step smoke_spotlighting 18 $RR scripts/sd_rag_base.py --defense spotlighting --failure incidental_stale $SM
step smoke_piguard      18 $RR scripts/sd_rag_base.py --defense filter:piguard --failure incidental_stale $SM
step smoke_datasentinel 18 $RR scripts/sd_rag_base.py --defense filter:datasentinel --failure incidental_stale $SM
step smoke_reliabilityrag 28 $RELI scripts/sd_reliabilityrag.py --failure incidental_stale $SM
step smoke_attntrace    22 $ATT scripts/sd_attntrace.py --failure incidental_stale $SM

# ---- stage B: each defense against its own paper's attack ------------------
CT="--doses 0 1 5"
step control_reliabilityrag 28 $RELI scripts/sd_reliabilityrag.py --failure poisonedrag $CT \
    --out data/registries/control_native_reliabilityrag_poisonedrag.json
step control_attntrace 22 $ATT scripts/sd_attntrace.py --failure poisonedrag $CT \
    --out data/registries/control_native_attntrace_poisonedrag.json

# ---- gate on the smoke results ---------------------------------------------
if ! python3 scripts/sd_smoke_check.py > "$Q/smoke_check.log" 2>&1; then
    echo "[stop ] smoke check failed; see $Q/smoke_check.log"
    cat "$Q/smoke_check.log"
    exit 1
fi
cat "$Q/smoke_check.log"

# ---- stage C: full ----------------------------------------------------------
step datasentinel_flags 10 $DSV scripts/sd_detect_datasentinel.py
for f in $FAILURES; do
    step "spotlighting_$f"   18 $RR scripts/sd_rag_base.py --defense spotlighting --failure "$f"
    step "piguard_$f"        18 $RR scripts/sd_rag_base.py --defense filter:piguard --failure "$f"
    step "datasentinel_$f"   18 $RR scripts/sd_rag_base.py --defense filter:datasentinel --failure "$f"
    step "reliabilityrag_$f" 28 $RELI scripts/sd_reliabilityrag.py --failure "$f"
    step "attntrace_$f"      22 $ATT scripts/sd_attntrace.py --failure "$f"
done
echo "[queue complete] $(date '+%m-%d %H:%M')"

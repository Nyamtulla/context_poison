#!/bin/bash
# The second-direction campaign, queued behind everyone else on the card.
#
# Every GPU step first waits at scripts/gpu_gate.py until no other user has a
# process on the card and enough memory is free, so it never starts beside
# someone else's job. Our own jobs may share the card: the full runs go in
# four lanes, and as many run at once as the free memory allows. Only one job
# loads at a time -- a step waits for room unlocked, then holds $Q/gpu.lock
# from a re-check until gpu_settle.py sees its memory stop growing, so the
# next gate reads what the card really has left and a small job is never stuck
# behind a big one. Each job exits when done, freeing what it held.
#
#   stage A  smoke: 5 items, stale document, 0/1/5 passages, every defense
#   stage B  controls: each traced/consistency defense on PoisonedRAG
#   check    scripts/sd_smoke_check.py; the full runs start only if it passes
#   stage C  full, in parallel lanes:
#              rag    spotlighting, piguard filter, datasentinel filter (one
#                     lane: they share one cached undefended pipeline)
#              ds     DataSentinel flags (the datasentinel filter waits on it)
#              reli   ReliabilityRAG, with the card to itself: vLLM sizes its
#                     cache as a share of the whole card and counts our other
#                     jobs against it, so it fails to start beside them
#              attn   AttnTrace
#   stage D  AttnTrace's PoisonedRAG control again, with trace ranks logged
#
# Resumable: every cell logs each answer, a finished cell is skipped, and a
# restarted queue picks up where it stopped, adopting any job still running.
#
#   setsid nohup scripts/sd_queue.sh >> data/sd_queue/queue.log 2>&1 &
set -u
cd "$(dirname "$0")/.."
Q=data/sd_queue
mkdir -p "$Q"
RR="env PYTHONPATH=envs/robustrag-libs python3"
RELI=envs/reliabilityrag-venv/bin/python
ATT=envs/attntrace-venv/bin/python
DSV=envs/datasentinel-venv/bin/python
FAILURES="incidental_stale distractor_evidence misretrieval context_dilution"

rm -f "$Q"/exclusive.*   # markers left by an earlier queue

step() {  # name, GB needed (or "excl": the card to itself), command...
    local name=$1 need=$2 lk pid rc pat; shift 2
    if [ -f "$Q/$name.done" ]; then echo "[skip] $name"; return 0; fi
    # a job an earlier queue left running is watched, not started twice;
    # it still writes to $Q/$name.log, which says whether it finished
    pat="$*"; pat="${pat#*scripts/}"
    pid=$(pgrep -u "$USER" -f -- "scripts/${pat}\$" | head -1)
    if [ -n "$pid" ]; then
        echo "[adopt] $name (pid $pid)"
        while kill -0 "$pid" 2>/dev/null; do sleep 30; done
        grep -q "wrote " "$Q/$name.log" && rc=0 || rc=1
        echo "[done ] $name exit $rc (adopted) $(date '+%m-%d %H:%M')"
        [ $rc -eq 0 ] && touch "$Q/$name.done"
        return $rc
    fi
    # an exclusive step raises its marker first, so no lane starts another
    # job while it waits for ours to drain; every other step waits it out
    local owner=${EXCL_OWNER:-$name}
    if [ "$need" = excl ]; then
        touch "$Q/exclusive.$owner"; need=46
    fi
    while ls "$Q"/exclusive.* 2>/dev/null | grep -qv "/exclusive.$owner\$"; do
        sleep 30
    done
    # wait for room without the lock, so a smaller job behind a bigger one
    # still starts; then take the lock and re-check, since another lane may
    # have loaded in between
    exec {lk}>"$Q/gpu.lock"
    while true; do
        python3 scripts/gpu_gate.py --need_gb "$need" > /dev/null \
            || { exec {lk}>&-; [ -z "${EXCL_OWNER:-}" ] && rm -f "$Q/exclusive.$name"; return 1; }
        flock -x "$lk"
        python3 scripts/gpu_gate.py --need_gb "$need" --once && break
        flock -u "$lk"
        sleep 30
    done
    echo "[start] $name $(date '+%m-%d %H:%M')"
    "$@" > "$Q/$name.log" 2>&1 {lk}>&- &
    pid=$!
    python3 scripts/gpu_settle.py --pid "$pid" | sed "s/^/  $name /"
    flock -u "$lk"; exec {lk}>&-
    wait "$pid"; rc=$?
    [ -z "${EXCL_OWNER:-}" ] && rm -f "$Q/exclusive.$name"
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

# ---- stage C: full, one background lane per pipeline ------------------------
lane_rag() {
    for f in $FAILURES; do
        step "spotlighting_$f" 18 $RR scripts/sd_rag_base.py --defense spotlighting --failure "$f"
        step "piguard_$f"      18 $RR scripts/sd_rag_base.py --defense filter:piguard --failure "$f"
    done
    until [ -f "$Q/datasentinel_flags.done" ] || [ -f "$Q/datasentinel_flags.failed" ]; do
        sleep 60
    done
    [ -f "$Q/datasentinel_flags.done" ] || { echo "[skip] datasentinel filter: no flags"; return 1; }
    for f in $FAILURES; do
        step "datasentinel_$f" 18 $RR scripts/sd_rag_base.py --defense filter:datasentinel --failure "$f"
    done
}
lane_ds()   {
    rm -f "$Q/datasentinel_flags.failed"
    step datasentinel_flags 10 $DSV scripts/sd_detect_datasentinel.py \
        || touch "$Q/datasentinel_flags.failed"
}
# the whole lane holds the card, so other lanes do not refill it between cells
lane_reli() {
    EXCL_OWNER=reli; touch "$Q/exclusive.reli"
    for f in $FAILURES; do
        step "reliabilityrag_$f" excl $RELI scripts/sd_reliabilityrag.py --failure "$f"
    done
    rm -f "$Q/exclusive.reli"
}
lane_attn() { for f in $FAILURES; do step "attntrace_$f" 22 $ATT scripts/sd_attntrace.py --failure "$f"; done; }

# raised before any lane starts, so none slips a job in ahead of it
[ "$(ls "$Q"/reliabilityrag_*.done 2>/dev/null | wc -l)" -lt 4 ] && touch "$Q/exclusive.reli"
lane_ds & lane_reli & lane_attn & lane_rag &
wait

# ---- stage D: AttnTrace's control again, logging trace ranks ---------------
# the first control predates rank logging; the same seed should reproduce its
# traced sets exactly, which the forensic analysis checks
step control_attntrace_ranked 22 $ATT scripts/sd_attntrace.py --failure poisonedrag $CT \
    --arms defended --log_suffix _ranked \
    --out data/registries/control_native_attntrace_poisonedrag_ranked.json
echo "[queue complete] $(date '+%m-%d %H:%M')"

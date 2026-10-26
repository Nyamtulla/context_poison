#!/bin/bash
# One slot of the parallel grid. Claims cells from a queue by mkdir (atomic,
# so two slots never take the same cell) and runs them one at a time.
#
# The card is shared, so a slot only starts a cell when the memory it needs is
# really free. Three things went wrong with the first version of that gate and
# are fixed here:
#
#   1. A failed or non-numeric nvidia-smi read fell through bash arithmetic as
#      zero used, i.e. "the card is empty". Slots launched into a full card and
#      died at model load. A bad read now reads as no free memory.
#   2. The lock was released on a fixed 240 s timer, whether or not the new job
#      had claimed its VRAM yet. A model load can take longer than that, so the
#      next slot measured a card that still looked free and launched into the
#      same space. The lock is now held until the allocation is VISIBLE on the
#      card, with a cap, rather than for a guess.
#   3. The lock was held while WAITING for memory, so a 30 GB job at the head
#      blocked 22 GB jobs behind it even when 27 GB was free. The wait now
#      happens with the lock released.
cd /home/n646s681/context_sok
S=/tmp/claude-100624149/-home-n646s681-context-sok/d861e294-d4cd-466f-82de-0113acc90d13/scratchpad
Q="$S/sched"
SLOT=$1
FREE_MIN_DEFAULT=${FREE_MIN:-22000}
SETTLE_MAX=${SETTLE_MAX:-90}        # x10s: cap on waiting for VRAM to appear
JOBS=${JOBS:-$Q/jobs.tsv}

cell_registry () {
  case "$1" in
    regime_framing_test) echo "data/registries/regime_framing_test.json" ;;
    *) echo "data/registries/native_$1.json" ;;
  esac
}

# Used MiB, or a number so large the caller refuses to launch. Never report an
# empty card because the query failed.
used_mib () {
  local u
  u=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1)
  case "$u" in ''|*[!0-9]*) echo 999999; return ;; esac
  echo "$u"
}

TOTAL=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1)
case "$TOTAL" in ''|*[!0-9]*) echo "[$SLOT] cannot read GPU total; refusing to run"; exit 1 ;; esac

# --requeue-stale: release claims nobody is working on and move those cells to
# the tail of the queue.
#
# A claim is a directory, taken with mkdir so two slots cannot race for the
# same cell. It is released when the cell finishes or when the cell fails. It
# is NOT released when the worker itself is killed, and a worker reads its
# queue once, top to bottom. So a claim orphaned by stopping a worker is
# invisible twice over: no process holds it, and every live worker has already
# read past that line. The cell is silently skipped for the rest of the run.
#
# Stale means: a claim exists, the registry is not complete, and no process is
# running that cell. The last test is the one that makes this safe to run while
# the grid is live -- a cell someone is working on right now is never touched.
requeue_stale () {
  local q=${1:-$Q/jobs.tsv} label reg n=0
  for d in "$Q"/claims/*/; do
    [ -d "$d" ] || continue
    label=$(basename "$d")
    reg=$(cell_registry "$label")
    python3 "$Q/done_check.py" "$reg" && continue          # finished, keep it
    if pgrep -af 'python3 scripts/' | grep -q -- "$(queue_cmd_fragment "$label" "$q")"; then
      echo "  busy    $label"; continue
    fi
    if grep -q "^$label	" "$q"; then
      rmdir "$d" 2>/dev/null || { echo "  locked  $label"; continue; }
      grep -m1 "^$label	" "$q" >> "$q"
      echo "  requeue $label"
      n=$((n + 1))
    else
      echo "  orphan  $label (not in $q; left claimed)"
    fi
  done
  echo "requeued $n stale cell(s)"
}

# The distinguishing part of a cell's command, used to tell whether that exact
# cell is running. Matching on the label alone is wrong: labels are not in the
# command line, and several cells share a script.
queue_cmd_fragment () {
  awk -F'\t' -v l="$1" '$1==l {print $3; exit}' "$2" \
    | sed 's/^[A-Z_]*=[^ ]* //' | cut -d' ' -f2-
}

launch () {
  local label=$1 cmd=$2 need=$3 before got
  while :; do
    flock 9
    before=$(used_mib)
    [ "$((TOTAL - before))" -ge "$need" ] && break
    flock -u 9
    sleep 60
  done
  echo "[$SLOT] start $label $(date +%H:%M)  free=$((TOTAL - before))MiB need=${need}MiB"
  eval "$cmd" > "$S/grid_$label.log" 2>&1 < /dev/null &
  JOB=$!
  for _ in $(seq "$SETTLE_MAX"); do
    sleep 10
    kill -0 $JOB 2>/dev/null || break              # died; nothing to settle
    got=$(used_mib)
    # 85% of the declared need, not half of it. Half released the lock while
    # a job that would end up at 27 GB was holding 15 GB, and the next slot
    # measured phantom headroom and launched into it. SpARE died that way at
    # 23:08 with the gate reporting 33.7 GB free.
    [ "$got" -ne 999999 ] && [ "$((got - before))" -ge "$((need * 85 / 100))" ] && break
  done
  flock -u 9
  wait $JOB
  return $?
} 9>"$Q/launch.lock"

if [ "$SLOT" = "--requeue-stale" ]; then
  requeue_stale "$JOBS"
  exit 0
fi

while read -r label need cmd <&3; do
  [ -z "$label" ] && continue
  mkdir "$Q/claims/$label" 2>/dev/null || continue
  if python3 "$Q/done_check.py" "$(cell_registry "$label")"; then
    echo "[$SLOT] skip $label (already complete)"; continue
  fi
  launch "$label" "$cmd" "${need:-$FREE_MIN_DEFAULT}"
  rc=$?
  echo "[$SLOT] done  $label exit $rc $(date +%H:%M)"
  # A cell that failed leaves no output and must not keep its claim, or no
  # slot will ever retry it. Four cells sat stuck this way for a day.
  if [ $rc -ne 0 ] && ! python3 "$Q/done_check.py" "$(cell_registry "$label")"; then
      rmdir "$Q/claims/$label" 2>/dev/null && echo "[$SLOT] released $label for retry"
  fi
  grep -E "^  dose .* acc" "$S/grid_${label}.log" | tail -2
  sleep 20
done 3< "$JOBS"
echo "[$SLOT] queue exhausted $(date +%H:%M)"

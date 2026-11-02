"""Block until one of our jobs has finished claiming GPU memory, then exit 0.

The parallel queue lets several of our jobs share the card, but only one may
be loading at a time: gpu_gate.py reads free memory, and a job that has
started but not yet allocated looks like free memory to the next gate. So a
step holds the queue's lock from its gate until this script sees the job's
memory stop growing -- `--stable` seconds within `--tol_mb` -- or the job
exit, and prints what it settled at, which is the number to size `--need_gb`
by next time.

    python3 scripts/gpu_settle.py --pid 12345
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time


def tree(pid):
    """The pid and every descendant (vLLM and torch may spawn workers)."""
    kids = {}
    for d in os.listdir("/proc"):
        if d.isdigit():
            try:
                with open(f"/proc/{d}/stat") as f:
                    ppid = int(f.read().rsplit(")", 1)[1].split()[1])
                kids.setdefault(ppid, []).append(int(d))
            except (OSError, IndexError, ValueError):
                pass
    out, todo = set(), [pid]
    while todo:
        p = todo.pop()
        out.add(p)
        todo.extend(kids.get(p, []))
    return out


def used_mb(pids):
    q = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,used_memory",
                        "--format=csv,noheader,nounits"],
                       capture_output=True, text=True).stdout
    total = 0
    for line in q.splitlines():
        p, m = (x.strip() for x in line.split(","))
        if p.isdigit() and int(p) in pids:
            total += int(m)
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--stable", type=int, default=60)
    ap.add_argument("--tol_mb", type=int, default=256)
    ap.add_argument("--poll", type=int, default=5)
    ap.add_argument("--max_wait", type=int, default=1200)
    args = ap.parse_args()
    start = time.time()
    last, since = -1, time.time()
    while time.time() - start < args.max_wait:
        if not os.path.exists(f"/proc/{args.pid}"):
            print("[settle] job exited while loading", flush=True)
            return 0
        mb = used_mb(tree(args.pid))
        if mb == 0 or abs(mb - last) > args.tol_mb:
            last, since = mb, time.time()
        elif time.time() - since >= args.stable:
            print(f"[settle] job {args.pid} settled at {mb / 1024:.1f} GB",
                  flush=True)
            return 0
        time.sleep(args.poll)
    print(f"[settle] job {args.pid} still growing after {args.max_wait}s; "
          f"releasing at {max(last, 0) / 1024:.1f} GB", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

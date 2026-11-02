"""Block until the shared card is ours to use, then exit 0.

The box has one GPU and other people's jobs on it. A job of ours waits behind
theirs rather than squeezing into the memory they leave: two jobs on one card
slow both, and a model that fits today may not after their next allocation.
So the gate waits until no other user has a process on the card AND the free
memory covers what our job needs, and checks again every `--poll` seconds.
It never touches anyone else's process.

    python3 scripts/gpu_gate.py --need_gb 26
"""
from __future__ import annotations

import argparse
import datetime
import getpass
import pwd
import subprocess
import sys
import time


def card():
    q = subprocess.run(["nvidia-smi", "--query-gpu=memory.total,memory.used",
                        "--format=csv,noheader,nounits"],
                       capture_output=True, text=True, check=True).stdout
    total, used = (int(x) for x in q.split("\n")[0].split(","))
    apps = subprocess.run(["nvidia-smi", "--query-compute-apps=pid",
                           "--format=csv,noheader"],
                          capture_output=True, text=True, check=True).stdout
    others = []
    me = getpass.getuser()
    for pid in apps.split():
        try:
            with open(f"/proc/{pid}/status") as f:
                uid = next(int(l.split()[1]) for l in f if l.startswith("Uid:"))
            owner = pwd.getpwuid(uid).pw_name
        except (FileNotFoundError, StopIteration, KeyError):
            owner = "?"   # cannot see it: treat as someone else's
        if owner != me:
            others.append((pid, owner))
    return (total - used) / 1024, others


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--need_gb", type=float, required=True)
    ap.add_argument("--poll", type=int, default=120)
    ap.add_argument("--report_every", type=int, default=1800)
    args = ap.parse_args()
    last = 0.0
    while True:
        free, others = card()
        if not others and free >= args.need_gb:
            print(f"[gate] {datetime.datetime.now():%H:%M} card free "
                  f"({free:.1f} GB), proceeding", flush=True)
            return 0
        if time.time() - last > args.report_every:
            who = ", ".join(f"{u}:{p}" for p, u in others) or "none"
            print(f"[gate] {datetime.datetime.now():%m-%d %H:%M} waiting: "
                  f"{free:.1f} GB free, need {args.need_gb}; other users' "
                  f"processes: {who}", flush=True)
            last = time.time()
        time.sleep(args.poll)


if __name__ == "__main__":
    sys.exit(main())

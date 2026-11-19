#!/usr/bin/env python3
"""Summarise pmload.py logs: per timed step, the loader calls (res:n = disk / file system, c = RAM cache, skip = kept out of the cache by
pm_cachecap) and the VBL at which the last loader call of the step returned, counted from the click that started the step.

    python3 tools/pmloadsum.py work/release/runs/ld_ste_fl_cap.txt [...] [--hz 50]

A step's window is [its click, the next step's click).  The 'poll' figure of the log (click -> the screen was seen) is only good to about
+-1 s (screenshot polling); the loader-return figure is exact to a VBL and is what the load-time comparisons use.
"""
from __future__ import annotations

import re
import sys


def parse(path):
    steps, ev = [], []
    for ln in open(path, errors="replace"):
        m = re.match(r"TIME (.*?): (\d+) VBL \((\d+) -> (\d+)\)", ln)
        if m:
            steps.append((m.group(1), int(m.group(3)), int(m.group(4))))
        if ln.startswith("TRACE raw"):
            for tok in ln.split(":", 1)[1].split():
                v, k, d = tok.split("/")
                ev.append((int(v), k, int(d, 16) if d else None))
    return steps, ev


def summarise(path, hz):
    steps, ev = parse(path)
    rows = []
    for i, (label, v0, v1) in enumerate(steps):
        end = steps[i + 1][1] if i + 1 < len(steps) else 10**9
        calls, last_ret, pending, first_call = [], None, None, None
        for v, k, d in ev:
            if not v0 - 2 <= v < end:
                continue
            if k == "call":
                pending = [v, d & 0xFFFF, "c"]
                calls.append(pending)
                first_call = first_call if first_call is not None else v
            elif k == "miss" and pending:
                pending[2] = "n"
            elif k == "skip" and pending:
                pending[2] = "n+skip"
            elif k == "ret":
                last_ret = v
        rows.append((label, v1 - v0, calls, None if last_ret is None else last_ret - v0))
    print(f"== {path}")
    for label, poll, calls, lr in rows:
        cl = " ".join(f"{r}:{c}" for _, r, c in calls) or "-"
        print(f"  {label}\n      poll {poll} VBL ({poll / hz:.1f} s); loader [{cl}]; last loader return " + ("-" if lr is None else f"+{lr} VBL ({lr / hz:.1f} s)"))


if __name__ == "__main__":
    a = sys.argv[1:]
    hz = 50.0
    if "--hz" in a:
        i = a.index("--hz")
        hz = float(a[i + 1])
        del a[i:i + 2]
    for f in a:
        summarise(f, hz)

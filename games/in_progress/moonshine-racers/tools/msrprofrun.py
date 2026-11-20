#!/usr/bin/env python3
"""Restore a snapshot, settle, dump RAM, profile N VBLs.

    python3 tools/msrprofrun.py work/snapshots/ste1m_race_start.sav race_start [--vbls 150] [--clock 8]
Writes work/dumps/ram_<name>.bin (1 MB), work/prof/<name>.txt (Hatari profile save), work/shots/<name>.png."""
import argparse, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from msr import Moonshine, prof, GAME


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("snap"); ap.add_argument("name")
    ap.add_argument("--vbls", type=int, default=150); ap.add_argument("--clock", type=int, default=8)
    ap.add_argument("--settle", type=int, default=60); ap.add_argument("--machine", default="ste")
    a = ap.parse_args()
    h = Moonshine(snapshot=a.snap, machine=a.machine)
    try:
        time.sleep(3)
        if a.clock != 8: h.set_cpuclock(a.clock)
        v0 = h.vbl()
        while h.vbl() < v0 + a.settle: time.sleep(0.3)
        h.dump(str(GAME / f"work/dumps/ram_{a.name}.bin"), 0, 0x100000)
        h.shot(str(GAME / f"work/shots/{a.name}.png"))
        o = prof(h, a.vbls, str(GAME / f"work/prof/{a.name}.txt"))
        print(o[o.find("Normal RAM"):][:400])
    finally:
        h.close()

if __name__ == "__main__":
    main()

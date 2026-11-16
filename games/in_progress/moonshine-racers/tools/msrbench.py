#!/usr/bin/env python3
"""fps + world-rate benchmark of a snapshot at several CPU clocks.

    python3 tools/msrbench.py work/snapshots/ste1m_race_up.sav --clocks 8 16 32 --vbls 500
Each clock: restore the snapshot in a fresh Hatari (--cpuclock N), 100 VBL settle, then
  - presented frames (executions of the flip routine $d1ca) in --vbls VBLs,
  - change of the world words ($5ff8 position accumulator, $100e frame counter, $11c2 distance) per emulated second."""
import argparse, json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from msr import Moonshine, flips_pc, peeks


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("snap"); ap.add_argument("--clocks", type=int, nargs="+", default=[8])
    ap.add_argument("--vbls", type=int, default=500); ap.add_argument("--machine", default="ste")
    ap.add_argument("--tos"); ap.add_argument("--mem", type=int, default=1024)
    a = ap.parse_args(); res = []
    for mhz in a.clocks:
        kw = dict(machine=a.machine, memsize_kb=a.mem)
        h = Moonshine(snapshot=a.snap, **kw)
        try:
            time.sleep(3)
            if mhz: h.set_cpuclock(mhz)      # 0 = leave the snapshot clock; the memstate carries its own cpu clock; --cpuclock on the cmdline is ignored
            v0 = h.vbl()
            while h.vbl() < v0 + 100: time.sleep(0.5)
            w0, vb0 = peeks(h), h.vbl()
            f = flips_pc(h, a.vbls)
            w1, vb1 = peeks(h), h.vbl()
            d = {k: ((w1[k] - w0[k] + 0x8000) & 0xFFFF) - 0x8000 for k in w0}
            r = dict(clock=mhz, **f, vbl_elapsed=vb1 - vb0, delta=d,
                     per_sec={k: round(v * 50.0 / (vb1 - vb0), 2) for k, v in d.items()})
            print(json.dumps(r), flush=True); res.append(r)
        finally:
            h.close()
    return res

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""1 MB RAM dumps of the running game from the stage-5 snapshots (input of tools/wwfill_test.py and tools/wwptr_test.py).
    python3 tools/wwdumps.py [--machine ste] [--scenes map_idle get_men random]  ->  /tmp/pmww1s5/dumps/<machine>_<scene>.bin"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pmww  # noqa: E402

MACH = {"ste": ("ste", "1.62", 1024), "st": ("st", "1.04", 1024), "megaste": ("megaste", "2.06", 4096)}
ap = argparse.ArgumentParser()
ap.add_argument("--machine", default="ste")
ap.add_argument("--scenes", nargs="*", default=["map_idle", "get_men", "random"])
a = ap.parse_args()
out = Path("/tmp/pmww1s5/dumps")
out.mkdir(parents=True, exist_ok=True)
m, tos, mem = MACH[a.machine]
for sc in a.scenes:
    h = pmww.PMW(snapshot=f"/tmp/pmww1s5/snaps/{a.machine}_{sc}.sav", machine=m, tos=pmww.TOS[tos], memsize_kb=mem, workdir=f"/tmp/pmww1s5/dump_{sc}")
    try:
        time.sleep(1.5)
        h.debug("b all", 0.3)
        d = h.ram(0, 0x100000)
        (out / f"{a.machine}_{sc}.bin").write_bytes(d)
        print(sc, len(d), "camera words", [hex(h.peekw(x)) for x in (0x50FD4, 0x50FD6, 0x1040A, 0x10406, 0x10408, 0x1040C, 0x5A860)], flush=True)
    finally:
        h.close()

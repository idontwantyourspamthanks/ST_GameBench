#!/usr/bin/env python3
"""Sprite-stage event trace: persistent breakpoints with debugger scripts; raw log -> work/sprite/raw/<name>.log
    python3 work/sprite/trace.py SNAP NAME [--frames 6] [--live IMG-PREFIX]
Events: e406 entry/exit, e598/e568 slot entry, kernel call sites (regs), ISR entries/rtes (excluded from slot time)."""
import argparse, re, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parent.parent
sys.path.insert(0, str(GAME / "tools"))
from msr import Moonshine  # noqa
import msrabtest as ab  # noqa

CALLSITES = [0xe710, 0xe8c8, 0xe920, 0xe9f2, 0xeaba, 0xeb0a, 0xec94, 0xed6e, 0xe7ae,
             0x1551a, 0x1554a, 0x1556a, 0x155ac, 0x155cc, 0x15604]
RETS = [0xed70, 0xe716]
ISR_IN = [0xd11e, 0xd616]
ISR_OUT = [0xd136, 0xd6ba, 0xd68e]
SITES = {}
SITES[0xe406] = (1, ["m $100e 2"])
SITES[0xe4fc] = (4, [])
SITES[0xe598] = (2, ["e a2", "m a2 56"])
SITES[0xe568] = (3, ["e a2", "m a2 56"])
for p in CALLSITES: SITES[p] = (0x100, ["r"])
for p in RETS: SITES.setdefault(p, (0x200, []))
for p in ISR_IN: SITES[p] = (0x10, [])
for p in ISR_OUT: SITES[p] = (0x20, [])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("snap"); ap.add_argument("name")
    ap.add_argument("--frames", type=int, default=6); ap.add_argument("--live", default=None)
    ap.add_argument("--wait", type=float, default=0)
    a = ap.parse_args()
    h = Moonshine(snapshot=ab.snap_path(a.snap))
    try:
        time.sleep(2)
        h.debug("b all", 0.3)
        for pc, (tag, extra) in SITES.items():
            (h.R / f"ev_{pc:x}.txt").write_text(f"e $e{tag:04x}0\ne VBL\ne FrameCycles\n" + "\n".join(extra) + "\n")
        n0 = len(h._logtext())
        pcs = [p for p in SITES if p != 0xe406] + [0xe406]      # e406 armed last: every frame it reports has all sites armed
        for pc in pcs:
            h.cmd(f"hatari-debug b pc = ${pc:x} :trace :file {h.R}/ev_{pc:x}.txt")
            time.sleep(0.05)
        t0 = time.time()
        wait = a.wait or (a.frames * 0.5 * 6 + 3)
        while time.time() - t0 < wait:
            time.sleep(1)
            if len(re.findall(r"\$e00010", h._logtext()[n0:])) > a.frames + 1 and False: break
        try:
            h.debug("b all", 1)
        except Exception as ex:
            print("EXC", ex)
        log = h._logtext()[n0:]
    finally:
        h.close()
    out = HERE / "raw"; out.mkdir(exist_ok=True)
    (out / f"{a.name}.log").write_text(log)
    print(len(log), "bytes;", log.count("Reading debugger commands"), "hits")

main()

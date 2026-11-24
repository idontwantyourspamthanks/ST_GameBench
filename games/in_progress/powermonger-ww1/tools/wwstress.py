#!/usr/bin/env python3
"""IKBD overrun stress for the blitter patches (master pmbuserr.py `stress`, work/notes/buserr.md), WW1.

    python3 tools/wwstress.py --snapshot S.sav --set p4_ptr_a p4_ptr_b p4_spr p6_slope p6_tri p6_cpy [--machine ste] [--mhz 8] [--vbls 9000] [--keys 0.04]

Restores a snapshot (the committed default set live), applies `--set` + test_ovr (an ACIA overrun counter in the game's keyboard handler) at a flip, then moves the host pointer at random (and taps a few keys) for
--vbls EMULATED VBLs while the game runs in real time (no fast-forward: the IKBD byte timing is the point).  Reports bytes received / overruns / the Hatari log's bus + address errors / whether the main loop
still ticks.  Gate: 0 overruns and 0 errors.  The IKBD reply is 9 bytes back to back, one per 20 HBL; an ACIA interrupt held off longer than a byte time (a long blitter chunk with the CPU stalled) loses one.
"""
from __future__ import annotations
import argparse
import random
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pmww  # noqa: E402
import wwab  # noqa: E402

OVC = 0xEF900


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--set", nargs="*", default=[])
    ap.add_argument("--machine", default="ste")
    ap.add_argument("--mhz", type=int, default=8)
    ap.add_argument("--vbls", type=int, default=9000)
    ap.add_argument("--keys", type=float, default=0.04, help="probability per step of a random key tap (cursor keys, Shift, Ctrl)")
    ap.add_argument("--tag", default="stress")
    ap.add_argument("--no-test-ovr", action="store_true")
    a = ap.parse_args()
    m, tos, mem = wwab.MACH[a.machine]
    info = wwab.snap_info(Path(a.snapshot), a.machine)
    h = wwab.make_pm(snapshot=a.snapshot, machine=m, tos=pmww.TOS[tos], memsize_kb=mem, workdir=f"/tmp/pmww1s5/stress_{a.tag}")
    rng = random.Random(5)
    try:
        time.sleep(1.0)
        if a.mhz != 8:
            h.set_cpuclock(a.mhz)
        names = a.set + ([] if a.no_test_ovr else ["test_ovr"])
        cmds = wwab.make_live(names, f"stress_{a.tag}", a.machine)
        (h.R / "apply.txt").write_text("\n".join(cmds) + "\n")
        start_log = len(h._logtext())
        h.cmd(f"hatari-debug b VBL > {info['at']} && pc = ${wwab.APPLYPC:x} :trace :once :file {h.R / 'apply.txt'}")
        t0 = time.time()
        while h.vbl() < info["at"] + 20:
            if time.time() - t0 > 600:
                raise TimeoutError("apply never happened")
            time.sleep(1.0)
        v0 = h.vbl()
        c0 = h.counter()
        steps = 0
        t1 = time.time()
        keys = ["Left", "Right", "Up", "Down", "Shift_L", "Control_L", "space"]
        while True:
            if steps % 40 == 0:
                if h.vbl() - v0 >= a.vbls:
                    break
                if time.time() - t1 > a.vbls / 50 * 6 + 300:
                    print("WARN: wall-clock cap reached before the VBL target", flush=True)
                    break
            dx, dy = rng.randint(-120, 120), rng.randint(-90, 90)
            h._xdo("mousemove_relative", "--", str(dx), str(dy))
            if rng.random() < 0.05:
                h._xdo("mousemove", "--window", h.win, str(rng.randint(100, 700)), str(rng.randint(100, 500)))
            if rng.random() < a.keys:
                k = rng.choice(keys)
                h._xdo("keydown", k)
                time.sleep(0.03)
                h._xdo("keyup", k)
            steps += 1
            time.sleep(0.02)
        v1 = h.vbl()
        c1 = h.counter()
        ovc = h.peekw(OVC) if "test_ovr" in names else -1
        rx = h.peekl(OVC + 2) if "test_ovr" in names else -1
        text = h._logtext()[start_log:]
        errs = len(re.findall(r"Bus Error|Address Error", text))
        ticking = h.ticking(2.0)
    finally:
        h.close()
    ok = (ovc == 0 or ovc == -1) and errs == 0 and ticking and c1 > c0
    print(f"STRESS {Path(a.snapshot).stem} {a.machine} {a.mhz} MHz set [{' '.join(a.set)}]: {v1 - v0} VBL, {steps} pointer steps, loop passes {c0} -> {c1}, IKBD bytes {rx}, overruns {ovc}, bus/address errors {errs}, "
          f"still ticking {ticking} -> {'PASS' if ok else 'FAIL'}", flush=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

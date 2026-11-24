#!/usr/bin/env python3
"""Tearing trace for the triple-buffer patches (master pmtriple.py `trace`, work/notes/triple.md section 4.5), WW1 addresses.

    python3 tools/wwtriple.py trace --snapshot S.sav [--machine ste] [--mhz 8] [--vbls 700] [--only p7_triple_wait p7_triple_flip p7_triple_tail] [--base ...] [--tag X]

Restores a snapshot (the committed default set live), applies `--base` + `--only` at the first flip after an absolute VBL, then four persistent breakpoints log, atomically, VBL, the cycle counter, the video base
register ($ff8201 / $ff8203), the shown / pointer buffer [$2ed98] and the drawing buffer [$2ed9c]: at the VBL handler ($774: the base register at that moment is the buffer scanned from this VBL on, and the handler
draws the pointer into [$2ed98]), at the start of the draw ($13e0a, the window copy), at the flip entry ($e0e) and after the flip ($145e8).  A draw interval = start of the draw -> flip entry with D = [$2ed9c] constant
in it.  CHECK: at its start, at every VBL inside it and at its end, D must differ from the scanned buffer AND from the pointer buffer.  Also: the (L, D) pairs at the flip entry and the VBLs between flips.
`--only test_nowait` = the negative control (the double buffer with the loop-head wait removed): it must report violations.
"""
from __future__ import annotations
import argparse
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pmww  # noqa: E402
import wwab  # noqa: E402

PCS = dict(vbl=0x774, s1=0x13E0A, flip=0xE0E, after=0x145E8)
EXPR = ["e VBL", "e CycleCounter", "e ($ff8201).b", "e ($ff8203).b", "e ($2ed98).l", "e ($2ed9c).l"]
NAMES = {0x1D500: "A", 0x25200: "B", 0xB0000: "C"}


def nm(a):
    return NAMES.get(a, f"${a:x}")


def run(a):
    m, tos, mem = wwab.MACH[a.machine]
    info = wwab.snap_info(Path(a.snapshot), a.machine)
    h = wwab.make_pm(snapshot=a.snapshot, machine=m, tos=pmww.TOS[tos], memsize_kb=mem, workdir=f"/tmp/pmww1s5/trace_{a.tag}")
    try:
        time.sleep(1.0)
        if a.mhz != 8:
            h.set_cpuclock(a.mhz)
        names = a.base + a.only
        cmds = wwab.make_live(names, f"trace_{a.tag}", a.machine) if names else []
        for k, pc in PCS.items():
            (h.R / f"{k}.txt").write_text(f"e ${pc:x}\n" + "\n".join(EXPR) + "\n")
            cmds.append(f"b pc = ${pc:x} :trace :file {h.R / (k + '.txt')}")
        end = h.R / "end.txt"
        end.write_text(f"b all\nsavebin {h.R}/end.flag $0 2\ne VBL\n")
        at = info["at"]
        cmds.append(f"b VBL > {at + a.vbls} :trace :once :file {end}")
        (h.R / "apply.txt").write_text("\n".join(cmds) + "\n")
        start = len(h._logtext())
        h.cmd(f"hatari-debug b VBL > {at} && pc = ${wwab.APPLYPC:x} :trace :once :file {h.R / 'apply.txt'}")
        time.sleep(0.3)
        h.cmd("hatari-option --fast-forward on")
        t = time.time()
        while not (h.R / "end.flag").exists():
            if time.time() - t > 900:
                raise TimeoutError("trace run did not complete")
            time.sleep(0.5)
        time.sleep(0.8)
        text = h._logtext()[start:]
    finally:
        h.close()
    ev = []
    for blk in text.split("CPU breakpoint condition(s) matched")[1:]:
        v = [int(x) for x in wwab.NUM.findall(blk)]
        if len(v) >= 7 and v[0] in PCS.values():
            k = [k for k, p in PCS.items() if p == v[0]][0]
            ev.append((k, v[1], v[2], (v[3] << 16) | (v[4] << 8), v[5], v[6]))
    return ev


def analyse(ev):
    viol, intervals, vbls_in, pairs, flips = [], 0, 0, {}, []
    scanned = None
    active = False
    last_flip_vbl = None
    gaps = []
    for k, vbl, cyc, base, L, D in ev:
        if k == "vbl":
            scanned = base
            if active and (D == scanned or D == L):
                viol.append((vbl, "VBL inside the draw", f"drawing into {nm(D)} while scanned {nm(scanned)} / pointer buffer {nm(L)}"))
            if active:
                vbls_in += 1
        elif k == "s1":
            active = True
            intervals += 1
            if scanned is not None and (D == scanned or D == L):
                viol.append((vbl, "draw start", f"drawing into {nm(D)} while scanned {nm(scanned)} / pointer buffer {nm(L)}"))
        elif k == "flip":
            if active and scanned is not None and (D == scanned or D == L):
                viol.append((vbl, "flip entry", f"drawing into {nm(D)} while scanned {nm(scanned)} / pointer buffer {nm(L)}"))
            active = False
            pairs[(nm(L), nm(D))] = pairs.get((nm(L), nm(D)), 0) + 1
            if last_flip_vbl is not None:
                gaps.append(vbl - last_flip_vbl)
            last_flip_vbl = vbl
    return viol, intervals, vbls_in, pairs, gaps


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["trace"])
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--machine", default="ste")
    ap.add_argument("--mhz", type=int, default=8)
    ap.add_argument("--vbls", type=int, default=700)
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--base", nargs="*", default=[])
    ap.add_argument("--expect-violations", action="store_true", help="negative control: PASS only if violations are found")
    ap.add_argument("--tag", default="t")
    a = ap.parse_args()
    ev = run(a)
    viol, intervals, vbls_in, pairs, gaps = analyse(ev)
    ok = (len(viol) > 0) if a.expect_violations else (len(viol) == 0 and intervals > 5)
    print(f"TRACE {Path(a.snapshot).stem} {a.machine} {a.mhz} MHz {a.vbls} VBL, set {' '.join(a.base + a.only) or '(snapshot only)'}: draw intervals {intervals}, VBLs inside {vbls_in}, violations {len(viol)}, "
          f"(L,D) at flip entry {dict(sorted(pairs.items()))}, VBLs between flips min/max/mean {min(gaps) if gaps else 0}/{max(gaps) if gaps else 0}/{sum(gaps) / len(gaps) if gaps else 0:.2f} -> "
          + ("PASS" if ok else "FAIL"), flush=True)
    for v in viol[:6]:
        print("   violation", v)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

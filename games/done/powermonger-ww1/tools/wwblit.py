#!/usr/bin/env python3
"""Differential test of the p4_spr sprite paths inside the running WW1 (master's test_blit method, work/notes/p4_raster.md section 5).

    python3 tools/wwblit.py --snapshot /tmp/pmww1s5/snaps/ste_get_men.sav [--machine ste] [--trials 20000] [--modes 1 2] [--control]

Applies p4_spr + the test patch test_blit live (patches/test_blit.s: a main-loop hook at $13dd2) on a snapshot of the running game, pokes the trial count / BLT mode / sheet flag and lets the game run until the
test writes its DONE marker.  Per mode (1 = blitter, 2 = pre-shifted cache) and per source (SHEET 0 = random words in a scratch sprite, 1 = random even addresses of the real sprite sheets $320c0..$4475c):
random shift 0..15, rows 1..32, column 0..17, random destination; the patched entry is called twice (a cache miss that builds the entry, then a hit) and compared with the original code path byte for byte over
the 160-byte rows, plus the final a0 / a1 / d0 / d1 / d2.  --control: the same with a deliberately wrong destination X increment (the blitter's `move.w #8,$ffff8a2e.w` poked to 9 through p4_spr's own code) must
report mismatches (the test can fail).
"""
from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pmww  # noqa: E402
import wwab  # noqa: E402

TESTGO, TESTN, RES, TMODE, SHEET, FORCES = 0xEF100, 0xEF104, 0xEF110, 0xEF174, 0xEF16C, 0xEF16E
MACH = wwab.MACH


def run_one(a, mode: int, sheet: int, work: Path, control: bool) -> dict:
    m, tos, mem = MACH[a.machine]
    h = wwab.make_pm(snapshot=a.snapshot, machine=m, tos=pmww.TOS[tos], memsize_kb=mem, workdir=str(work))
    try:
        time.sleep(1.0)
        info = wwab.snap_info(Path(a.snapshot), a.machine)
        cmds = wwab.make_live(["p4_spr", "test_blit"], f"blit_{mode}_{sheet}_{int(control)}")
        if control:                                   # blitter: destination X increment 8 -> 10; cache: first `or.l (a3)+,d3` of the draw loop becomes `and.l (a3)+,d3`
            import wwpatch
            p = [x for x in wwpatch.load_all() if x.name == "p4_spr"][0]
            org, lines = [sg for sg in p.segments if sg[0] != p.site][0]
            blob = wwpatch.assemble(org, lines, "\n".join(p.preamble))
            k = blob.index(bytes.fromhex("31fc00088a2e"))
            cmds.append(f"w ${org + k + 2:x} $00 $0a")
            k2 = blob.index(bytes.fromhex("869b"))
            cmds.append(f"w ${org + k2:x} $c6 $9b")
        cmds += [f"w ${TESTN:x} $00 $00 ${a.trials >> 8:02x} ${a.trials & 255:02x}",
                 f"w ${TMODE:x} $b1 $7e $00 ${mode:02x}", f"w ${SHEET:x} $00 ${sheet:02x}", f"w ${FORCES:x} $ff $ff", f"w ${TESTGO:x} $00 $01"]
        (h.R / "apply.txt").write_text("\n".join(cmds) + "\n")
        v = h.vbl()
        at = (v // 100 + 3) * 100
        h.cmd(f"hatari-debug b VBL > {at} && pc = ${wwab.APPLYPC:x} :trace :once :file {h.R / 'apply.txt'}")
        h.cmd("hatari-option --fast-forward on")
        t = time.time()
        while time.time() - t < 1500:
            time.sleep(3)
            try:
                if h.peekl(RES + 32) == 0x600D:
                    break
            except Exception:
                pass
        else:
            raise TimeoutError("test did not finish")
        return dict(done=h.peekl(RES), bad=h.peekl(RES + 4), first=(h.peekw(RES + 8), h.peekw(RES + 10), h.peekw(RES + 12), h.peekw(RES + 14)), regs=h.peekl(RES + 28),
                    blt=h.peekl(0xDF004), hdr=h.peekl(0xDF000))
    finally:
        h.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--machine", default="ste")
    ap.add_argument("--trials", type=int, default=20000)
    ap.add_argument("--modes", nargs="*", type=int, default=[1, 2])
    ap.add_argument("--sheets", nargs="*", type=int, default=[0, 1])
    ap.add_argument("--control", action="store_true", help="negative control (see docstring)")
    a = ap.parse_args()
    ok = True
    for mode in a.modes:
        for sheet in a.sheets:
            r = run_one(a, mode, sheet, Path(f"/tmp/pmww1s5/blit_{mode}_{sheet}"), a.control)
            good = r["done"] == a.trials and r["bad"] == 0 and r["regs"] == 0
            ok &= good
            print(f"BLIT mode {mode} ({'blitter' if mode == 1 else 'pre-shifted cache'}) source {'sheet' if sheet else 'random words'}: trials {r['done']}, mismatching trials {r['bad']}, register mismatches {r['regs']}, "
                  f"first fail (s, rows, col, which) {r['first']}, BLT {r['blt']:08x} HDR {r['hdr']:08x} -> {'PASS' if good else 'FAIL'}", flush=True)
    print("BLIT ALL PASS" if ok else "BLIT FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

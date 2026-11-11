#!/usr/bin/env python3
"""Random differential test of pop2_spr's two paths against the game's original sprite code, inside the running game (work/notes/display.md section 3).

    python3 tools/p2blit.py [--trials 30000] [--modes 1 2] [--snapshot busy1] [--neg]

Applies the live set `test_blit pop2_spr pop2_spr16` (see patches/test_blit.s for the trial) and runs TRIALS trials per mode in one Hatari each:
mode 1 = the STE blitter path, mode 2 = the pre-shifted cache (the plain-ST path).  Each trial draws a random sprite (real sheet
rows or random rows, x -48..339, y -40..229, rows 1..33, one trial in eight with a mutated source word) through the game's own front
end $2122e on two identical random screens, once with the original code and once with the path under test, and compares the
affected rows (every 64th trial the whole screens).  --neg pokes a deliberately wrong byte into pop2_spr's blob (NOPs one `or.l`
in the cache draw loop / flips the skew in the blitter setup) and the test must report mismatches.
Exit status 0 = every mode ran all trials with 0 mismatches (and, with --neg, only if the broken code is detected).
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE)]
from p2abtest import NUM, Populous2, WORK, apply_cmds, make_live, snap_path  # noqa: E402

TRIALS, TMODE, RES = 0x86F30, 0x86F32, 0x86F40
FLIP, APPLYPC = 0x1BFE, 0x1C04


def mem_dump(text: str, addr: int, n: int) -> bytes:
    """bytes of a debugger `m $addr n` dump (lines `00086f40: 00 00 ...`)"""
    out = {}
    for m in re.finditer(r"^([0-9a-f]{8}):\s+((?:[0-9a-f]{2} )+)", text, re.M | re.I):
        a = int(m.group(1), 16)
        for i, b in enumerate(m.group(2).split()):
            out[a + i] = int(b, 16)
    return bytes(out.get(addr + i, 0) for i in range(n))


def run(mode: int, trials: int, snap: Path, pokes: list[str], live: str) -> dict:
    h = Populous2(snapshot=snap)
    try:
        R = h.R
        time.sleep(1.0)
        at = (h.vbl() // 100 + 3) * 100
        cmds = apply_cmds(live) + pokes
        cmds.append(f"w ${TMODE:x} $00 ${mode:02x}")
        cmds.append(f"w ${TRIALS:x} ${trials >> 8:02x} ${trials & 255:02x}")
        (R / "end.txt").write_text(f"b all\nsavebin {R}/end.flag $0 2\nm ${RES:x} 48\ne VBL\n")
        cmds.append(f"b (${TRIALS:x}).w = 0 :trace :once :file {R / 'end.txt'}")
        (R / "apply.txt").write_text("\n".join(cmds) + "\n")
        start = len(h._logtext())
        h.cmd(f"hatari-debug b VBL > {at} && pc = ${APPLYPC:x} :trace :once :file {R / 'apply.txt'}")
        time.sleep(0.3)
        h.cmd("hatari-option --fast-forward on")
        t = time.time()
        while not (R / "end.flag").exists() and time.time() - t < 3000:
            time.sleep(1.0)
        time.sleep(1.0)
        text = h._logtext()[start:]
    finally:
        h.close()
    b = mem_dump(text, RES, 48)
    be = lambda o, n: int.from_bytes(b[o:o + n], "big")
    return dict(mode=mode, done=be(0, 4), mism=be(4, 4), x=be(8, 2) - (65536 if be(8, 2) > 32767 else 0),
                y=be(10, 2) - (65536 if be(10, 2) > 32767 else 0), rows=be(12, 2), a1=be(14, 4), full=be(0x18, 4), pool=be(0x1C, 4), px16=be(0x20, 4),
                finished=(R / "end.flag").exists() if False else "Wrote 0x2 bytes" in text)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--trials", type=int, default=30000, help="per mode, 1..32767")
    ap.add_argument("--modes", nargs="*", type=int, default=[1, 2])
    ap.add_argument("--snapshot", default="busy1")
    ap.add_argument("--neg", action="store_true", help="negative control: a wrong byte in the code under test")
    ap.add_argument("--neg-verify", action="store_true", help="negative control for the cache's source-row verify: its five `bne.s` become nops (mode 2 only)")
    a = ap.parse_args()
    if not 0 < a.trials <= 32767:
        raise SystemExit("--trials must be 1..32767 (the trial counter is a signed word)")
    WORK.mkdir(exist_ok=True)
    sp = snap_path(a.snapshot)
    live = make_live(["test_blit", "pop2_spr", "pop2_spr16"])
    pokes = {1: [], 2: []}
    if a.neg_verify:
        img = Path(live + ".img").read_bytes()
        m = re.search(rb"(?:\xb5\x89\x66.){5}", img[0x4000:0x5000], re.S)
        base = 0x80000 + 0x4000 + m.start()
        pokes[2] = [f"w ${base + 4 * k + 2:x} $4e $71" for k in range(5)]
        a.neg = True
        a.modes = [2]
    elif a.neg:        # deliberately broken code: the blitter's OR pass becomes LOP 5 (D), the cache draw loses one `or.l (a3)+,d5`
        img = Path(live + ".img").read_bytes()
        lop = img.find(bytes.fromhex("11fc00078a3b")) + 3
        orl = img.find(bytes.fromhex("8a9b"), 0x4000)
        pokes = {1: [f"w ${0x80000 + lop:x} $05"], 2: [f"w ${0x80000 + orl:x} $4e $71"]}
    with ThreadPoolExecutor(2) as ex:
        futs = [ex.submit(run, m, a.trials, sp, pokes[m], live) for m in a.modes]
        res = [f.result() for f in futs]
    ok = True
    for r in res:
        good = r["finished"] and r["done"] == a.trials and r["full"] == 0
        if a.neg:
            good = good and r["mism"] > 0
        else:
            good = good and r["mism"] == 0
        ok &= good
        print(f"mode {r['mode']} ({'blitter' if r['mode'] == 1 else 'pre-shifted cache'}): trials {r['done']}/{a.trials}, mismatching trials {r['mism']}, whole-screen "
              f"mismatches {r['full']}, trials on the pool sprites {r['pool']}, through the 16 px front end {r['px16']}; first mismatch x={r['x']} y={r['y']} rows={r['rows']} a1=${r['a1']:x}  -> "
              f"{'OK' if good else 'FAIL'}")
    print("ALL OK" if ok else "FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

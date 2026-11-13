#!/usr/bin/env python3
"""Per-frame picture gate for triple buffering (HunterTriple; notes work/notes/triple.md).

    python3 tools/hunttb_ab.py --base p4_ikbd ... test_tblock --only p4_ikbd ... tb_flip tb_frame tb_vbl test_tblock \
        --snapshot foot_stand foot_walk car_stand car_drive car_turn hills_stand 4mb_foot_stand --flips 4 [--views K]

Why not `huntab.py`: with three screen pages the drawn frame is not always at $23000/$2ad00, so a fixed-address capture
compares the wrong bytes (a stale page against a fresh one).  Here, at every flip, the three pages A=$23000, B=$2ad00 and
C=$81000 are saved and `$144(a5)` (the page the pass just drew into) is logged; the gate compares the *picture* - the
32000 bytes at the draw pointer - frame by frame, so the page addresses may differ between the runs.

Both runs get `test_tblock` (the elapsed-VBL latch pinned to 15), otherwise the frames are a different number of VBLs
long and the simulation legitimately diverges after the first frame.  The only difference between the two runs is the
patch set under test.
"""
from __future__ import annotations

import argparse
import os
import hashlib
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path[:0] = [str(GAME.parent.parent.parent / "tools"), str(HERE)]
from hunter import Hunter, SNAP  # noqa: E402
import huntab  # noqa: E402

FLIP = 0x5FEE
APPLY_PC = 0x253E                  # the 3D loop top: applying the sites AT the flip would leave the in-flight `bsr $5fd2`
                                   # return address pointing into the middle of the patched instruction (illegal instruction)
FLIP_ENTRY = 0x5FD2
DRAW = 0x94A                       # $144(a5) with a5 = $806: captured at the flip ENTRY ($5fd2, before the swap), so $144 is the page the pass just drew
CAP_PC = 0x5FD2
PAGES = {"A": 0x23000, "B": 0x2AD00, "C": 0x81000}
PAGE_LEN = 32000
WORK = Path("/tmp/huntbab")


def run_one(snap: Path, at: int, live, flips, pokes) -> dict:
    h = Hunter(snapshot=str(snap), memsize_kb=huntab.memsize_of(snap))
    try:
        return frame_of(h, snap, at, live, flips, pokes)
    finally:
        h.close()


def frame_of(h, snap: Path, at: int, live, flips: list[int], pokes: list[str]) -> dict:
    """Restore, apply `live` at the first flip after VBL `at`, and for every flip n in `flips` save the three pages + the draw pointer."""
    out = h.R
    caps = {}
    for i, n in enumerate(flips):
        cf = out / f"c{n}.txt"
        body = ("".join(f"savebin {out}/f{n}_{p}.bin ${a:x} ${PAGE_LEN:x}\n" for p, a in PAGES.items())
                + f"m ${DRAW:x} 4\ne ${FLIP:x}\ne VBL\ne FrameCycles\n")
        cf.write_text(body)
        caps[n] = cf
    cmds = [f"e ${APPLY_PC:x}", "e VBL", "e FrameCycles"]
    if live:
        spec = json.loads(Path(live + ".json").read_text())
        cmds.append(f"loadbin {Path(live + '.img')} ${spec['img_base']:x}")
        for s in spec["sites"]:
            cmds.append(f"w ${s['addr']:x} " + " ".join(f"${b:02x}" for b in bytes.fromhex(s["new"])))
    cmds += pokes
    for n, cf in caps.items():                       # armed at the apply flip ($5fee); capture PC is the flip ENTRY, so hit n = flip n
        cnt = f" :{n}" if n > 1 else ""
        cmds.append(f"b pc = ${CAP_PC:x}{cnt} :trace :once :file {cf}")
    end = out / "end.txt"
    end.write_text("b all\n")
    cmds.append(f"b VBL > {at + 400} :trace :once :file {end}")
    app = out / "apply.txt"
    app.write_text("\n".join(cmds) + "\n")
    if len(max(cmds, key=len)) > 235:
        raise SystemExit("debugger command line too long")
    if h.vbl() >= at:
        raise SystemExit(f"at_vbl {at} already passed")
    h.debug("b all", 0.3)
    start = len(h._logtext())
    h.cmd(f"hatari-debug b VBL > {at} && pc = ${APPLY_PC:x} :trace :once :file {app}")
    time.sleep(0.3)
    h.cmd("hatari-option --fast-forward on")
    t = time.time()
    while h._logtext()[start:].count("Removed CPU breakpoint") < len(flips) + 2:   # apply, captures, end
        if time.time() - t > 400:
            raise TimeoutError("run did not finish")
        time.sleep(0.3)
    time.sleep(0.5)
    # each capture runs in its own breakpoint block: find the frame number from the savebin file names of that block and the
    # $148 value printed in the same block (a single shared `m` read would give only the last flip's value)
    res = {}
    text = h._logtext()
    for blk in text.split("CPU breakpoint condition(s) matched")[1:]:
        fm = re.search(r"f(\d+)_A\.bin", blk)
        mm = re.search(r"0000094[aA]:\s+([0-9a-f]{2}) ([0-9a-f]{2}) ([0-9a-f]{2}) ([0-9a-f]{2})", blk)
        if not fm or not mm:
            continue
        n = int(fm.group(1))
        draw = int("".join(mm.groups()), 16)
        name = next((p for p, a in PAGES.items() if a == draw), None)
        pg = {p: (out / f"f{n}_{p}.bin").read_bytes() for p in PAGES}
        res[n] = {"draw": draw, "page": name, "md5": hashlib.md5(pg[name]).hexdigest() if name else None}
    if os.environ.get("TBAB_DEBUG"):
        print(f"debug: text {len(text)} B, blocks {len(text.split('CPU breakpoint condition(s) matched')) - 1}, parsed {sorted(res)}")
    missing = [n for n in flips if n not in res]
    if missing:
        raise SystemExit(f"captures missing for flips {missing}")
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--base", nargs="*", default=[])
    ap.add_argument("--snapshot", nargs="*", default=list(huntab.DEFAULT_SNAPS))
    ap.add_argument("--flips", nargs="*", type=int, default=[1, 2, 3, 4])
    ap.add_argument("--views", type=int, default=0)
    ap.add_argument("--points", type=int, default=2)
    a = ap.parse_args()
    WORK.mkdir(exist_ok=True)
    flips = sorted(set(a.flips))
    btag, ptag = huntab.tag_for(a.base), huntab.tag_for(a.only)
    blive, plive = huntab.make_live(a.base), huntab.make_live(a.only)
    ok = True
    for sn in a.snapshot:
        sp = huntab.snap_path(sn)
        at0 = huntab.at_vbl_for(sp)
        npts = a.views or a.points
        bad = []
        rows = []
        for pi in range(npts):
            at = at0 + pi * huntab.POINT_STEP
            pk = huntab.pokes_for(pi if a.views else None, False)
            with ThreadPoolExecutor(2) as ex:
                fb = ex.submit(run_one, sp, at, blive, flips, pk)
                fp = ex.submit(run_one, sp, at, plive, flips, pk)
                b, p = fb.result(), fp.result()
            for n in flips:
                same = b[n]["md5"] == p[n]["md5"]
                rows.append(f"p{pi}: frame {n} base {b[n]['page']} patched {p[n]['page']} "
                            f"{'IDENTICAL' if same else 'DIFFER'}")
                if not same:
                    bad.append((pi, n))
        print(f"{sn}: {'IDENTICAL' if not bad else 'DIFFER'} ({len(flips)} frames x {npts} points)")
        for r in rows:
            print("   ", r)
        ok &= not bad
    print("ALL IDENTICAL" if ok else "MISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

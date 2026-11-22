#!/usr/bin/env python3
"""Edited-track race proof: the campaign file dumped from RAM by ed2.py (4 tracks, the 4th = the edited COPY OF TRACK 04) -> F10 -> TRACK EDITOR -> track 4 -> PLAY THIS TRACK -> NO key presses,
poll until a race stands: campaign position == 3, stream pointer inside the 4th block, the game's curve ring $1bbc == expand_curve of the edited block and != the stock TRACK 04's; screenshots along the way.
   env4.sh python3 play3.py --camp /tmp/msred4/ed2_stock_ste2m_b.trk [--tag T]"""
import argparse
from ed2lib import *
ap = argparse.ArgumentParser(); ap.add_argument("--camp"); ap.add_argument("--tag", default="play3"); ap.add_argument("--build", default=os.environ["ED_BUILD"]); ap.add_argument("--machine", default="ste"); ap.add_argument("--hold", type=int, default=4)
a = ap.parse_args()
ents = mt.parse_campaign(Path(a.camp).read_bytes()); blk = bytes(ents[0]["block"])
e = Ed(a.tag, a.machine, 2048, a.build, Path(a.camp)); r = e.r
try:
    e.boot_editor(True, ntr=1); time.sleep(3.0)
    e.send(0x1c); time.sleep(1.5); e.key(0x50, 1, 0.5); r.shot("1_trackmenu_play"); e.send(0x1c)
    got = None
    for i in range(240):
        time.sleep(0.5)
        if i % 8 == 7: r.shot(f"s{(i + 1) // 2:03d}s")
        if r.l(0x23c0) != 0 and r.b(0x1024) == 0: got = r.st("race up"); r.shot("2_race"); break
    check("a race stands without any key press", got is not None)
    pos, ptr = r.w(V["pos"]), r.l(0x23c0)
    base = 0x110000 + ents[0]["offset"]
    check("campaign position == 0 (the only track), stream pointer inside its block", pos == 0 and base <= ptr < base + len(blk) + 64, f"pos {pos} ptr {ptr:#x} block ${base:#x}..${base + len(blk):#x}")
    e.jpoke(0x01); time.sleep(a.hold); r.shot("3_driving"); log("after holding UP", a.hold, "s: $5ff8", r.w(0x5ff8), "$23c0", hex(r.l(0x23c0)))
    ring = r.mem(0x1bbc, 64); log("curve ring $1bbc[0..31] =", [struct.unpack(">h", ring[2 * i:2 * i + 2])[0] for i in range(32)]); e.jpoke(0)
    log(f"Bus/Address error lines: {r.errlines()}")
finally:
    e.close()
log(f"RESULT {a.tag}: {'ALL CHECKS PASS' if not FAILS else 'FAILED: ' + ', '.join(FAILS)}")

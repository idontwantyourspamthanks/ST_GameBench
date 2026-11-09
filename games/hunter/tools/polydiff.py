#!/usr/bin/env python3
"""Differential test of p4_poly against the original polygon code, polygon by polygon, in the running game (4 MB snapshot).

    python3 games/hunter/tools/polydiff.py [--views 12] [--flips-per-view 3] [--snapshot 4mb_foot_stand]

patches/test_polydiff.s hooks $7554 (the entry of the polygon body), runs p4_poly's blob and then the original code on the same
input (the 3D window is saved/restored around them) and compares the 22400-byte window plus $1600/$1618. Counters at $8dfe0 are read
back at the end (see the patch header). Every view = a teleport of the player (huntab.pokes_for); every polygon of every frame in
between is one test case. Frames are very slow here (3 window copies + a compare per polygon): the emulator runs in fast-forward.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path[:0] = [str(GAME.parent.parent / "tools"), str(HERE)]
from hunter import Hunter  # noqa: E402
import huntab  # noqa: E402


def live(names, out):
    subprocess.run([sys.executable, str(HERE / "huntpatch.py"), "live", "--only", *names, "--out", str(out)], check=True,
                   cwd=GAME, stdout=subprocess.DEVNULL)
    return json.loads(Path(str(out) + ".json").read_text())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--views", type=int, default=12)
    ap.add_argument("--flips-per-view", type=int, default=3)
    ap.add_argument("--view-base", type=int, default=0, help="seed offset of the first view (Hatari crashes with > ~15 breakpoints: run several)")
    ap.add_argument("--snapshot", default="4mb_foot_stand")
    ap.add_argument("--test", default="test_polydiff")
    ap.add_argument("--target", default="p4_poly")
    ap.add_argument("--extra", nargs="*", default=[], help="more patches applied live (their images + sites) besides the test pair")
    a = ap.parse_args()
    tmp = Path("/tmp/hp4/pd"); tmp.mkdir(parents=True, exist_ok=True)
    lt = live([a.test], tmp / "t")
    lp = live([a.target], tmp / "p")
    sn = huntab.snap_path(a.snapshot)
    h = Hunter(snapshot=str(sn), memsize_kb=huntab.memsize_of(sn))
    try:
        R = h.R
        cmds = [f"loadbin {tmp / 't.img'} ${lt['img_base']:x}", f"loadbin {tmp / 'p.img'} ${lp['img_base']:x}"]
        for s in lt["sites"]:
            cmds.append(f"w ${s['addr']:x} " + " ".join(f"${b:02x}" for b in bytes.fromhex(s["new"])))
        total = a.views * a.flips_per_view + 2
        for i in range(a.views):
            f = R / f"v{i}.txt"
            f.write_text("\n".join(huntab.pokes_for(a.view_base + i, False)) + "\n")
            n = 1 + i * a.flips_per_view
            cmds.append(f"b pc = ${huntab.FLIP:x} :{n} :trace :once :file {f}" if n > 1 else
                        f"b pc = ${huntab.FLIP:x} :trace :once :file {f}")
        end = R / "end.txt"
        end.write_text("m $8dfe0 40\n")
        cmds.append(f"b pc = ${huntab.FLIP:x} :{total} :trace :once :file {end}")
        app = R / "apply.txt"
        app.write_text("\n".join(cmds) + "\n")
        assert len(max(cmds, key=len)) < 235
        at = huntab.at_vbl_for(sn)
        start = len(h._logtext())
        h.cmd(f"hatari-debug b VBL > {at} && pc = ${huntab.FLIP:x} :trace :once :file {app}")
        time.sleep(0.3)
        h.cmd("hatari-option --fast-forward on")
        t = time.time()
        last = (-1, 0)
        data = b""
        while True:
            time.sleep(2.0)
            out = h.debug("m $8dfe0 48", 0.8)
            data = b""
            for ln in out.splitlines():
                m = re.match(r"0008DF([EF][0-9A-F]):\s+((?:[0-9a-f]{2} )+)", ln, re.I)
                if m:
                    data += bytes(int(x, 16) for x in m.group(2).split())
            n = int.from_bytes(data[0:4], "big") if len(data) >= 4 else -1
            done = "Removed CPU breakpoint" in h._logtext()[start:] and h._logtext()[start:].count("Removed CPU breakpoint") >= a.views + 2
            if n != last[0]:
                last = (n, time.time())
            if done or time.time() - last[1] > 40 or time.time() - t > 1500:
                break
        print("finished" if done else f"STALLED at {n} polygons (vbl {h.vbl()})")
        L = lambda o: int.from_bytes(data[o:o + 4], "big")
        W = lambda o: int.from_bytes(data[o:o + 2], "big")
        print(f"polygons tested {L(0)}  window mismatches {L(4)}  variable mismatches {L(0x12)}  "
              f"(views {a.views} x {a.flips_per_view} flips)")
        if L(4):
            print(f"first mismatch: polygon list ${L(8):x} n={W(0xc)} first differing long at window offset ${L(0xe):x}")
        sys.exit(0 if L(4) == 0 and L(0x12) == 0 and L(0) > 0 else 1)
    finally:
        h.close()


if __name__ == "__main__":
    main()

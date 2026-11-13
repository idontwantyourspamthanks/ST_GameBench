#!/usr/bin/env python3
"""PopRelease: tooltip frame captured in a RENDER-ONLY pass (tick kind R) and in a turn pass (kind T), release set + tick, snapshot at 16 MHz
(test scaffolding).  A breakpoint after the flip (pc $b946) with the RON flag (word $bb010) = 1 (R) / 0 (T) saves both screen buffers, the
displayed-buffer pointer and the palette; the frame is rebuilt as a PNG.   python3 ttshot.py [icon id] [snap]"""
import re, sys, time
from pathlib import Path
GAME = Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous")
sys.path[:0] = [str(GAME / "tools"), str(GAME.parent.parent.parent / "tools")]
import poptick as pt, popuitest as pu           # noqa: E402
from populous import Populous                    # noqa: E402
from PIL import Image                             # noqa: E402

ICON = int(sys.argv[1]) if len(sys.argv) > 1 else 1
SNAP = sys.argv[2] if len(sys.argv) > 2 else "genesis_start"
OUT = GAME / "work" / "shots"


def planar(buf: bytes, pal: bytes) -> Image.Image:
    cols = []
    for i in range(16):
        w = int.from_bytes(pal[i * 2:i * 2 + 2], "big")
        cols.append(tuple((((n & 7) << 1) | (n >> 3)) * 17 for n in ((w >> 8) & 15, (w >> 4) & 15, w & 15)))
    im = Image.new("RGB", (320, 200))
    px = im.load()
    for y in range(200):
        for g in range(20):
            o = y * 160 + g * 8
            p = [int.from_bytes(buf[o + 2 * k:o + 2 * k + 2], "big") for k in range(4)]
            for b in range(16):
                v = sum(((p[k] >> (15 - b)) & 1) << k for k in range(4))
                px[g * 16 + b, y] = cols[v]
    return im


def main():
    live = pt.make_live(pt.RELEASE + pt.TICKSET)
    h = Populous(snapshot=pt.snap_path(SNAP))
    try:
        time.sleep(1.5)
        h.set_cpuclock(16)
        pt.at_pc(h, pt.apply_cmds(live) + [pu.NOP_ACIA], pt.APPLYPC)
        h.debug("b all", 0.3)
        time.sleep(1.0)
        x, y = pu.HOVER[ICON]
        pu.poke_pointer(h, x, y)
        time.sleep(1.0)
        R = h.R
        res = {}
        for kind, ron in (("R", 1), ("T", 0)):
            f = R / f"cap_{kind}.txt"
            f.write_text(f"savebin {R}/{kind}_a.bin $4f500 32000\nsavebin {R}/{kind}_b.bin $57200 32000\nsavebin {R}/{kind}_pal.bin $ff8240 32\n"
                         f"savebin {R}/{kind}_ptr.bin $3c50c 4\nsavebin {R}/{kind}_ron.bin $bb010 2\nsavebin {R}/{kind}_done.flag $0 2\n")
            h.debug("b all", 0.3)
            h.cmd(f"hatari-debug b pc = $b946 && ($bb010).w = {ron} :trace :once :file {f}")
            t = time.time()
            while not (R / f"{kind}_done.flag").exists():
                if time.time() - t > 120:
                    raise TimeoutError(kind)
                time.sleep(0.3)
            time.sleep(0.5)
            ptr = int.from_bytes((R / f"{kind}_ptr.bin").read_bytes(), "big")
            ronv = int.from_bytes((R / f"{kind}_ron.bin").read_bytes(), "big")
            buf = (R / f"{kind}_a.bin").read_bytes() if ptr == 0x4F500 else (R / f"{kind}_b.bin").read_bytes()
            im = planar(buf, (R / f"{kind}_pal.bin").read_bytes())
            p = OUT / f"release_tooltip_{kind}pass_icon{ICON}.png"
            im.save(p)
            im.crop((60, 0, 240, 20)).resize((180 * 4, 80), Image.NEAREST).save(OUT / f"release_tooltip_{kind}pass_icon{ICON}_top.png")
            res[kind] = (hex(ptr), ronv, str(p))
        print("icon", ICON, (x, y), res)
    finally:
        h.close()


main()

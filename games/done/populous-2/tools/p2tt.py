#!/usr/bin/env python3
"""Screenshot gate for pop2_tooltip (work/notes/ui_impl.md).

    python3 tools/p2tt.py shots SNAP [--set pop2_tooltip ..] [--prefix ui_] [--only cat0 eff00 strip3 ..]

Loads the snapshot, applies the live patch set at a flip, hovers every icon with the host pointer (the game's pointer then sits
at the icon's centre cell) and saves work/shots/<prefix><name>.png (the 640x400 game picture, full) for each.
Icon centres follow the game's iso cells: category k (59+16k, 145+8k), effect e (42+16e, 159+8e), strip k=1..6 (317-16k, 148+8k).
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path[:0] = [str(HERE), str(GAME.parent.parent.parent / "tools")]
from populous2 import Populous2, HOME  # noqa: E402
import p2abtest as AB  # noqa: E402
import p2tick as TK  # noqa: E402
from PIL import Image  # noqa: E402

SHOTS = GAME / "work" / "shots"


def targets():
    t = {}
    for k in range(6):
        t[f"cat{k}"] = (59 + 16 * k, 145 + 8 * k)
    for e in range(6):
        t[f"eff{e}"] = (42 + 16 * e, 159 + 8 * e)
    for k in range(1, 7):
        t[f"strip{k}"] = (317 - 16 * k, 148 + 8 * k)
    t["none"] = (160, 100)
    return t


def game_crop(path: Path) -> Image.Image:
    im = Image.open(path).convert("RGB")
    return im.crop((HOME[0], HOME[1], HOME[0] + 640, HOME[1] + 400))


def px(buf: bytes, y: int, x: int) -> int:
    off = y * 160 + (x // 16) * 8
    w = [int.from_bytes(buf[off + 2 * p:off + 2 * p + 2], "big") for p in range(4)]
    b = 15 - (x % 16)
    return sum(((w[p] >> b) & 1) << p for p in range(4))


def rpass(snap, a):
    """Render-only passes (kind R, 16 MHz) must carry the tooltip: run busy1 + tick set + pop2_tooltip with the walk driver (the pointer sits on the
    Air category icon at (96,170) for two turns in 32) and test the back buffer of every flip, T and R, against the black sky."""
    live = AB.make_live(TK.WALK + TK.TICKSET + a.set)
    t0 = AB.start_turn_for(snap)
    R = TK.one(snap, t0, live, TK.WORK / "ttr", a.turns, a.mhz, 50, True, True)
    print("pointer positions at the flips:", sorted({(f["x"], f["y"]) for f in R["flips"]}))
    rows = {"T": [0, 0], "R": [0, 0]}
    for f in R["flips"]:
        if (f["x"], f["y"]) != (96, 170):
            continue
        kind = "R" if f["ron"] else "T"
        lit = sum(1 for yy in (2, 4) for xx in range(120, 256, 8) if px(f["sb"], yy, xx) != 0)
        rows[kind][1 if lit else 0] += 1
    print(f"flips with the pointer on the icon: T without text {rows['T'][0]}, T with text {rows['T'][1]}; R without text {rows['R'][0]}, R with text {rows['R'][1]}")


def tour(snap, a):
    """Per category: click its icon, hover every effect slot of the row; save the top-bar strip of each (work/shots/<prefix>effects_cat<k>.png:
    one 2x crop of ST (96,0)-(272,16) per slot, stacked) and the full picture of slot 0 of the category."""
    live = AB.make_live(a.set)
    h = Populous2(snapshot=snap)
    try:
        time.sleep(1.0)
        TK.at_flip(h, AB.apply_cmds(live) + [AB.poke_cmd(p) for p in a.pokes])
        time.sleep(0.5)
        for k in range(6):
            x, y = 59 + 16 * k, 145 + 8 * k
            h.goto(HOME[0] + 2 * x, HOME[1] + 2 * y, HOME)
            time.sleep(0.5)
            h.click(hold=0.4)
            time.sleep(1.5)
            crops = []
            for e in range(5):
                ex, ey = 42 + 16 * e, 159 + 8 * e
                h.goto(HOME[0] + 2 * ex, HOME[1] + 2 * ey, HOME)
                time.sleep(1.5)
                im = game_crop(h.shot())
                if e == 0:
                    im.save(SHOTS / f"{a.prefix}{a.snap}_catclick{k}_eff0.png")
                crops.append(im.crop((192, 0, 544, 32)))
                print(k, e, "pointer", h.peekw(0x393FA), h.peekw(0x393FC), "slot ptr", h.peekw(0x39794))
            sheet = Image.new("RGB", (352, 32 * 5))
            for i, c in enumerate(crops):
                sheet.paste(c, (0, 32 * i))
            sheet.save(SHOTS / f"{a.prefix}effects_cat{k}.png")
    finally:
        h.close()


def rect_report(h, tag: str):
    """The clean background the game copies every pass ($392e4 -> $392e0) at the tooltip rect (120,0)-(255,15): the colour indices there and the palette."""
    ptr = h.peekl(0x392E4)
    f = Path(f"/tmp/p2tt_bg_{tag}.bin")
    f.unlink(missing_ok=True)
    h.debug(f"savebin {f} ${ptr:x} 32000", 1.5)
    bg = f.read_bytes()
    cols = {}
    for y in range(16):
        for x in range(120, 256):
            c = px(bg, y, x)
            cols[c] = cols.get(c, 0) + 1
    pal = [h.peekw(0xFF8240 + 2 * i) & 0xFFF for i in range(16)]
    print(f"[{tag}] bg ${ptr:x} rect (120,0)-(255,15) colour index counts {cols}; palette {' '.join('%03x' % p for p in pal)}", flush=True)
    return cols, pal


def land(a):
    """Cold boot the original game to the first conquest, then run CUSTOM GAMEs (a random landscape each) and report the tooltip rect in each."""
    h = Populous2()
    try:
        if not h.boot_to_game():
            print("boot failed"); return 1
        time.sleep(20)
        rect_report(h, "conquest1")
        game_crop(h.shot()).save(SHOTS / f"{a.prefix}land_conquest1.png")
        for i in range(a.turns):
            h._click(707, 374, 3)
            h._click(560, 194, 10)
            h._click(384, 274, 10)
            time.sleep(3)
            if not h.in_play():
                print(f"custom {i}: not in play"); continue
            time.sleep(8)
            tag = f"custom{i}"
            rect_report(h, tag)
            game_crop(h.shot()).save(SHOTS / f"{a.prefix}land_{tag}.png")
    finally:
        h.close()


def lcycle(snap, a):
    """The four landscapes in one run: the game's own command $7a (the Game options dialog's land-type item: `addi.w #1,$4737c` mod 4, fade, `$2d326` loads the
    landscape's files, `$1f764` redraws the clean background) is written into the command slot at [$473c4]+1.  Per landscape: hover a category icon with the
    tooltip patch live, full picture, the bg rect colour counts and the palette."""
    live = AB.make_live(a.set)
    h = Populous2(snapshot=snap)
    try:
        time.sleep(1.0)
        TK.at_flip(h, AB.apply_cmds(live))
        time.sleep(0.5)
        for i in range(4):
            print("landscape $4737c =", h.peekw(0x4737C), flush=True)
            for name, (x, y) in (("cat2", (59 + 32, 145 + 16)), ("eff0", (42, 159)), ("strip2", (285, 164)), ("none", (160, 100))):
                h.goto(HOME[0] + 2 * x, HOME[1] + 2 * y, HOME)
                time.sleep(1.5)
                game_crop(h.shot()).save(SHOTS / f"{a.prefix}land{h.peekw(0x4737C)}_{name}.png")
            rect_report(h, f"land{h.peekw(0x4737C)}")
            slot = h.peekl(0x473C4)
            h.debug(f"w ${slot + 1:x} $7a", 0.5)
            time.sleep(12)
    finally:
        h.close()


DEFAULT = ["pop2_credit", "pop2_ntsc", "pop2_ntsc2", "pop2_clamp", "pop2_ptr_a", "pop2_ptr_b", "pop2_spr", "pop2_spr16"] + [t for t in TK.TICKSET]


def cold(a):
    """HD build with the default set + pop2_tooltip, cold boot (--machine/--tos/--mem), to the first battle, hover a category icon and a strip icon, screenshots."""
    import subprocess
    from stharness import TOS
    out = Path(f"/tmp/p2tt_hd_{a.machine}")
    subprocess.run([sys.executable, str(HERE / "pop2patch.py"), "build", "--out", str(out), "--only", *DEFAULT, "pop2_tooltip"], check=True, cwd=GAME, stdout=subprocess.DEVNULL)
    kw = dict(game_dir=out, machine=a.machine, memsize_kb=a.mem)
    if a.tos:
        kw["tos"] = TOS[a.tos]
    h = Populous2(**kw)
    try:
        ok = h.boot_to_game()
        time.sleep(5)
        print(f"{a.machine} {a.mem} KB: in_play={ok} marker={h.marker()!r} turn {h.peekw(h.TURN)}")
        for name, (x, y) in (("cat2", (91, 161)), ("strip4", (253, 180)), ("none", (160, 100))):
            h.goto(HOME[0] + 2 * x, HOME[1] + 2 * y, HOME)
            time.sleep(2.5)
            game_crop(h.shot()).save(SHOTS / f"{a.prefix}cold_{a.machine}_{name}.png")
            print(name, "pointer", h.peekw(0x393FA), h.peekw(0x393FC), flush=True)
    finally:
        h.close()


def zoom(snap, a):
    """Zoomed views ($39766 != 8): hold keypad Enter / - / + and look at the rect with the pointer where an icon would be."""
    live = AB.make_live(a.set)
    h = Populous2(snapshot=snap)
    try:
        time.sleep(1.0)
        TK.at_flip(h, AB.apply_cmds(live))
        time.sleep(0.5)
        h.goto(HOME[0] + 2 * 91, HOME[1] + 2 * 161, HOME)
        for name, key in (("kpenter", "KP_Enter"), ("kpminus", "KP_Subtract"), ("kpplus", "KP_Add")):
            for back in range(2):
                h.key(key, 0.5)
                time.sleep(1.5)
                v = h.peekw(0x39766)
                print(name, "press", back, "$39766 =", hex(v), "pointer", h.peekw(0x393FA), h.peekw(0x393FC))
                game_crop(h.shot()).save(SHOTS / f"{a.prefix}zoom_{name}_{back}_v{v:x}.png")
    finally:
        h.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["shots", "rpass", "tour", "land", "zoom", "lcycle", "cold"])
    ap.add_argument("snap")
    ap.add_argument("--set", nargs="*", default=["pop2_tooltip"])
    ap.add_argument("--prefix", default="ui_")
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--turns", type=int, default=130)
    ap.add_argument("--mhz", type=int, default=16)
    ap.add_argument("--machine", default="ste")
    ap.add_argument("--tos", default=None)
    ap.add_argument("--mem", type=int, default=2048)
    ap.add_argument("--pokes", nargs="*", default=[], help="ADDR:HEX applied with the live set")
    a = ap.parse_args()
    snap = AB.snap_path(a.snap) if a.snap != "-" else None
    if a.cmd == "cold":
        return cold(a)
    if a.cmd == "lcycle":
        return lcycle(snap, a)
    if a.cmd == "land":
        return land(a)
    if a.cmd == "zoom":
        return zoom(snap, a)
    if a.cmd == "tour":
        return tour(snap, a)
    if a.cmd == "rpass":
        return rpass(snap, a)
    live = AB.make_live(a.set)
    h = Populous2(snapshot=snap)
    try:
        time.sleep(1.0)
        TK.at_flip(h, AB.apply_cmds(live) + [AB.poke_cmd(p) for p in a.pokes])
        time.sleep(0.5)
        for name, (x, y) in targets().items():
            if a.only and name not in a.only:
                continue
            h.goto(HOME[0] + 2 * x, HOME[1] + 2 * y, HOME)
            time.sleep(1.5)
            out = SHOTS / f"{a.prefix}{a.snap}_{name}.png"
            raw = h.shot()
            game_crop(raw).save(out)
            print(name, (x, y), "pointer", h.peekw(0x393FA), h.peekw(0x393FC), "->", out.name)
    finally:
        h.close()


if __name__ == "__main__":
    main()

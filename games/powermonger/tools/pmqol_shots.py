#!/usr/bin/env python3
"""Hover screenshots for qol_hover (feature 3 + 4): several settlements / inventions / sword levels, from the get_men snapshot with the
patches applied live.  Writes work/shots/qol_*.png (full screenshots) and prints the tooltip state words.   python3 tools/pmqol_shots.py"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import pmab
import pmtick
from pm import GAME, PM, SNAP

OUT = GAME / "work" / "shots"
OUT.mkdir(exist_ok=True)
HOUSES = 0x4F916


def find_house(h, town_off, secs=3.0):
    """Pointer position on a house of settlement `town_off`: the sprite routine $12138 is traced for a moment (a3 = object record, d0/d1 = sprite
    top-left); the first house record whose $e is the settlement wins; the point is the sprite centre."""
    f = h.R / "probe.txt"
    f.write_text("r\n")
    h.debug("b all", 0.3)
    s0 = len(h._logtext())
    h.cmd(f"hatari-debug b pc = $12138 :trace :file {f}")
    time.sleep(secs)
    h.debug("b all", 0.3)
    txt = h._logtext()[s0:]
    best = None
    for b in txt.split("Reading debugger commands")[1:]:
        m = re.search(r"D0 ([0-9A-F]{8}).*?D1 ([0-9A-F]{8}).*?A3 ([0-9A-F]{8})", b, re.S)
        if not m:
            continue
        d0, d1, a3 = (int(x, 16) for x in m.groups())
        if HOUSES <= a3 < 0x51536:
            if h.peekw(a3 + 0xE) == town_off:
                best = (a3, d0 & 0xFFFF, d1 & 0xFFFF)
                break
    return best


def bar(png, out):
    from PIL import Image
    im = Image.open(png)
    im.crop((96 + 112 * 2, 58, 96 + 320 * 2, 58 + 12)).resize((208 * 4, 12 * 4), Image.NEAREST).save(out)


def main():
    names = pmab.TICK + ["pm_tooltip", "qol_keys", "qol_keys2", "qol_hover", "qol_hover2"]
    live = pmab.make_live(names)
    h = PM(snapshot=str(SNAP / "get_men.sav"))
    shots = []
    try:
        time.sleep(1.5)
        h.set_cpuclock(16)
        pmtick.at_flip(h, pmab.apply_cmds(live))
        time.sleep(1.0)

        def pk(addr, *bs):
            h.debug(f"w ${addr:x} " + " ".join(f"${b:02x}" for b in bs), 0.25)

        def hover(tag, x, y, wait=3.0):
            h.goto_st(x, y)
            time.sleep(wait)
            p = OUT / f"qol_{tag}.png"
            h.shot(str(p))
            bar(p, OUT / f"qol_{tag}_bar.png")
            print(f"{tag}: pointer ({x},{y}) HIT ${h.peekl(0xCF78A):x} sHK {h.peekw(0xCDC12)} sID {h.peekw(0xCDC04)} -> {p.name}", flush=True)
            shots.append(tag)

        # settlement 0 (offset 0): the village in view at the snapshot
        a = find_house(h, 0)
        print("house of settlement 0:", a)
        if not a:
            raise SystemExit("no house found")
        hx, hy = a[1] + 12, a[2] + 12
        pk(0x57FD4, 0, 0)                                           # no command selected (the snapshot has Get Men)
        hover("s0_idle", hx, hy)                                    # $c = 0: workshop idle
        for tag, c, cd in (("s0_sword", 4, 7), ("s0_plough", 8, 2), ("s0_pike", 2, 12), ("s0_catapult", 0xE, 4000), ("s0_cannon", 0x10, 100)):
            pk(0x4E520, 0, c)
            pk(0x4E524, cd >> 8, cd & 255)
            h.goto_st(150, 60)
            time.sleep(1.0)
            hover(tag, hx, hy)
        # no workshop: kind byte of the workshop house of settlement 0 (house 4, +7)
        pk(HOUSES + 0x48 + 7, 3)
        pk(0x4E520, 0, 0)
        h.goto_st(150, 60)
        time.sleep(1.0)
        hover("s0_noworkshop", hx, hy)
        pk(HOUSES + 0x48 + 7, 7)
        # Invent selected: "Invent here"
        pk(0x57FD4, 0, 0xE)
        for lvl, post in ((1, 4), (2, 3), (3, 2)):               # swords 1/2/3 = posture word 4/3/2
            pk(0x516FC, 0, post)
            h.goto_st(150, 60)
            time.sleep(1.0)
            hover(f"s0_invent_{lvl}sword", hx, hy)
        # variations of the resources under the same village: high ground + forest near = alternates; far forest = pots; mine = iron
        pk(0x516FC, 0, 2)
        for tag, (addr, val) in (("s0_invent_mine", (0x4E526, (0, 0x10))),):
            pk(addr, *val)
            h.goto_st(150, 60)
            time.sleep(1.0)
            hover(tag, hx, hy)
            pk(addr, 0, 0)
        # icon tooltips with keys (Invent icon, level 3)
        hover("icon_invent_3sword_keys", 274, 188, 2.0)
        pk(0x57FD4, 0, 0)
        pk(0x516FC, 0, 3)
        hover("icon_invent_2sword_keys", 274, 188, 2.0)
        hover("icon_getfood_keys", 202, 181, 2.0)
        hover("icon_rotate_left_keys", 28, 158, 2.0)
        hover("icon_compass", 16, 183, 2.0)
        # settlement 1 and 2: scroll the view onto them (the camera words are the centre cell; settlement 1 = cell (29,62), 2 = (40,51))
        for n, (cx, cy, off) in (("s1", (29, 62, 0x20)), ("s2", (40, 51, 0x40))):
            pk(0x4BB3A, 0, cx)
            pk(0x4BB3C, 0, cy)
            pk(0x57FD4, 0, 0)
            h.goto_st(150, 60)
            time.sleep(2.0)
            a = find_house(h, off)
            print(f"house of settlement {n}:", a)
            if a:
                hover(f"{n}_idle", a[1] + 12, a[2] + 12)
                pk(0x4E520 + off, 0, 6)
                pk(0x4E524 + off, 0, 9)
                h.goto_st(150, 60)
                time.sleep(1.0)
                hover(f"{n}_bow", a[1] + 12, a[2] + 12)
    finally:
        h.close()
    print("screens:", " ".join(f"qol_{t}.png" for t in shots))


if __name__ == "__main__":
    sys.exit(main())

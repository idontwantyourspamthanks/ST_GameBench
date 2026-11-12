#!/usr/bin/env python3
"""TT cold boot -> Raids map (NOVICE click) -> 70 s time series: flips per 50 VBL window, pointer presence in the screenshot, pointer moved every ~12 s.
usage: tt_series.py NAME BUILD MACHINE MEM"""
import sys, time, re
from pathlib import Path
from PIL import Image
ROOT = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2')
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools')
from mw2harness import Hatari
import mw2raids
from stharness import MACHINE_TOS
name, bd, machine, mem = sys.argv[1:5]
out = ROOT/'work/mapptr'/name; out.mkdir(exist_ok=True)
h = Hatari(snapshot=None, machine=machine, tos=MACHINE_TOS[machine], memsize_kb=int(mem), game_dir=ROOT/bd, extra=['--mmu','true'] if machine=='tt' else None)
tt = machine == 'tt'
def arrow(im, px, py):
    ox, oy = (0, 0) if tt else (96, 58)
    cx, cy = ox+2*px, oy+2*py; c = 0; p = im.load()
    for yy in range(cy-2, cy+28):
        for xx in range(cx-2, cx+22):
            if 0 <= xx < im.width and 0 <= yy < im.height:
                r, g, b = p[xx, yy]
                if r > 200 and 50 < g < 140 and b < 80: c += 1
    return c
try:
    time.sleep(70 if tt else 25)
    ref = ROOT / 'work/ref/mode_select.png'
    for i in range(60):
        h.cmd('hatari-event keypress 57'); time.sleep(5)
        if h.screen_matches(ref, (280, 350, 560, 420)): break
    for i in range(6):
        time.sleep(3); h.cmd('hatari-event keypress 50'); time.sleep(6)
        if not h.screen_matches(ref, (280, 350, 560, 420)): break
    time.sleep(45 if tt else 4)
    for _ in range(4):
        h.goto(*((294, 216) if tt else (300, 230))); h.click()
        t0 = time.time(); ok = False
        while time.time() - t0 < 60:
            time.sleep(3 if time.time() - t0 > 9 else 10 - (time.time() - t0))
            if h.peekw(0xEB9C) == 0xFFFF and mw2raids._screen_has_levels(h): ok = True; break
        if ok: break
    h.goto(175, 390); h.click()
    t0 = time.time(); k = 0; mv = [(300, 250), (450, 200), (200, 300), (380, 330)]
    while time.time() - t0 < 80:
        if k % 5 == 3: h.goto(*mv[(k // 5) % 4])
        f = h.fps(50)
        s = h.shot(str(out / f'{k:03d}.png'))
        px, py = h.peekw(0x6fae), h.peekw(0x6fb2)
        c = arrow(Image.open(s).convert('RGB'), px, py)
        print(f'{time.time()-t0:5.1f}s {k:03d} mode={h.peekw(0x700a)} flips/50vbl={f["flips"]} px={px} py={py} arrow_px={c}', flush=True)
        k += 1
finally:
    h.close()

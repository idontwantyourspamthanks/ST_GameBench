#!/usr/bin/env python3
"""Restore SRC/map.sav, optionally set CPU clock, park the pointer, then take N fast shots and report whether the arrow is drawn in each.
usage: sample.py SRC BUILD MACHINE CLK N [X Y]"""
import sys, time
from pathlib import Path
from PIL import Image
ROOT = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2')
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools')
from mw2harness import Hatari
from stharness import MACHINE_TOS
src, bd, machine, clk, n = sys.argv[1:6]; n=int(n)
x, y = (int(sys.argv[6]), int(sys.argv[7])) if len(sys.argv) > 7 else (300, 250)
mem = int(sys.argv[8]) if len(sys.argv) > 8 else 1024
out = ROOT/'work/mapptr'/f'samp_{src}_{clk}'; out.mkdir(exist_ok=True)
h = Hatari(snapshot=str(ROOT/'work/mapptr'/src/'map.sav'), machine=machine, tos=MACHINE_TOS[machine], memsize_kb=mem, game_dir=ROOT/bd, extra=['--mmu','true'] if machine=='tt' else None)
def arrow(im, px, py):
    cx, cy = 96+2*px, 58+2*py; c=0
    p=im.load()
    for yy in range(cy-4, cy+30):
        for xx in range(cx-4, cx+24):
            r,g,b=p[xx,yy]
            if r>200 and 50<g<140 and b<80: c+=1
    return c
try:
    time.sleep(3)
    if int(clk): h.set_cpuclock(int(clk))
    h.goto(x, y); time.sleep(1)
    print('FPS', h.fps(250), flush=True)
    px, py = h.peekw(0x6fae), h.peekw(0x6fb2)
    res=[]
    for i in range(n):
        f = h.shot(str(out/f's{i:03d}.png'))
        c = arrow(Image.open(f).convert('RGB'), px, py)
        res.append(c); print(i, px, py, 'arrow_px', c, flush=True)
    print('SUMMARY', src, clk, 'present', sum(1 for c in res if c>20), 'of', n)
finally:
    h.close()

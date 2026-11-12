#!/usr/bin/env python3
"""Cold boot -> NOVICE click -> dense screenshots of the island map from the moment it appears. Pointer is moved every 6 s.
usage: tl.py NAME BUILD MACHINE MEM"""
import sys, time
from pathlib import Path
ROOT = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2')
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools')
from mw2harness import Hatari
import mw2raids
from stharness import MACHINE_TOS
name, bd, machine, mem = sys.argv[1:5]
out = ROOT/'work/mapptr'/name; out.mkdir(exist_ok=True)
h = Hatari(snapshot=None, machine=machine, tos=MACHINE_TOS[machine], memsize_kb=int(mem), game_dir=ROOT/bd, extra=['--mmu','true'] if machine=='tt' else None)
try:
    time.sleep(70 if machine == 'tt' else 25)
    ref = ROOT / 'work/ref/mode_select.png'
    for i in range(60):
        h.cmd('hatari-event keypress 57'); time.sleep(5)
        if h.screen_matches(ref, (280, 350, 560, 420)): break
    for i in range(6):
        time.sleep(3); h.cmd('hatari-event keypress 50'); time.sleep(6)
        if not h.screen_matches(ref, (280, 350, 560, 420)): break
    time.sleep(45 if machine == 'tt' else 4)
    # corridor -> RAIDS door -> level screen (copy of _enter_raids_from_hall up to the NOVICE click)
    for _ in range(4):
        h.goto(*((294, 216) if machine == "tt" else (300, 230))); h.click()
        t0 = time.time(); ok = False
        while time.time() - t0 < 60:
            time.sleep(3 if time.time() - t0 > 9 else 10 - (time.time() - t0))
            if h.peekw(0xEB9C) == 0xFFFF and mw2raids._screen_has_levels(h): ok = True; break
        if ok: break
    h.goto(175, 390); h.click()
    t0 = time.time(); k = 0
    mv = [(300, 250), (450, 200), (200, 300), (380, 330)]
    while time.time() - t0 < 60:
        if k % 8 == 4: h.goto(*mv[(k // 8) % 4])
        h.shot(str(out / f'{k:03d}.png'))
        print(f'{time.time()-t0:5.1f}s {k:03d} vbl={h.vbl()} mode={h.peekw(0x700a)} px={h.peekw(0x6fae)} py={h.peekw(0x6fb2)} 540e={h.peekw(0x540e):x}', flush=True)
        k += 1
    h.savemem(str(out / 'map.sav'))
finally:
    h.close()

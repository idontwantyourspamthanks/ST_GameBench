#!/usr/bin/env python3
"""Cold boot -> Raids island map, then watch the pointer over time.
usage: repro.py NAME BUILD_DIR MACHINE [TOS] [memKB]   -> work/mapptr/NAME/*.png + log, snapshot NAME/map.sav"""
import sys, time
from pathlib import Path
ROOT = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2')
sys.path.insert(0, str(ROOT / "tools"))
from mw2harness import Hatari
import mw2raids
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools')
from stharness import MACHINE_TOS
name, bd, machine = sys.argv[1:4]
tos = MACHINE_TOS[machine]
mem = int(sys.argv[5]) if len(sys.argv) > 5 else 1024
out = ROOT / "work/mapptr" / name; out.mkdir(parents=True, exist_ok=True)
kw = dict(machine=machine, memsize_kb=mem, game_dir=ROOT / bd, snapshot=None)
if tos: kw["tos"] = tos
extra = ["--mmu", "true"] if machine == "tt" else None
h = Hatari(extra=extra, **kw)
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
    mw2raids._enter_raids_from_hall(h)
    import os
    if os.environ.get('CLK'): h.set_cpuclock(int(os.environ['CLK']))
    t0 = time.time()
    def snap(tag):
        h.shot(str(out / f"{tag}.png"))
        print(f"{time.time()-t0:6.1f}s {tag} vbl={h.vbl()}", flush=True)
    snap("t000_parked")
    h.savemem(str(out / "map.sav"))
    h.goto(300, 250); snap("t001_moved")
    for i in range(1, 16):
        time.sleep(2)
        snap(f"t{i*2+1:03d}_still")
    h.goto(450, 200); snap("t040_moved2")
    for k in range(6):
        h.rel(40, 20 if k % 2 else -20, 4); time.sleep(1.5); snap(f"t{41+k:03d}_moving")
    for i in range(6):
        time.sleep(3); snap(f"t{50+i*3:03d}_still2")
finally:
    h.close()

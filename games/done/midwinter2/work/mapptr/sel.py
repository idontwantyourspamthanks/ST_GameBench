#!/usr/bin/env python3
"""From NAME/map.sav: hover an island, SPACE, then screenshots + pointer state over time.
usage: select.py SRC_NAME OUT_NAME BUILD_DIR MACHINE X Y"""
import sys, time
from pathlib import Path
ROOT = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2')
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools')
from mw2harness import Hatari
from stharness import MACHINE_TOS
src, name, bd, machine, x, y = sys.argv[1:7]
out = ROOT / "work/mapptr" / name; out.mkdir(parents=True, exist_ok=True)
mem = 1024
h = Hatari(snapshot=str(ROOT/'work/mapptr'/src/'map.sav'), machine=machine, tos=MACHINE_TOS[machine], memsize_kb=mem, game_dir=ROOT / bd,
           extra=["--mmu","true"] if machine=="tt" else None)
def st():
    return dict(mode=h.peekw(0x700a), px=h.peekw(0x6fae), py=h.peekw(0x6fb2), flag6fc2=h.peekw(0xeb9c-0xeb9c+0x6fc2), island=h.peekw(0xeb9c))
try:
    time.sleep(3)
    t0 = time.time()
    def snap(tag):
        h.shot(str(out / f"{tag}.png"))
        print(f"{time.time()-t0:6.1f}s {tag} vbl={h.vbl()} {st()}", flush=True)
    snap("a000_restored")
    h.goto(int(x), int(y)); snap("a001_hover")
    h.key("space")
    for i in range(1, 25):
        time.sleep(2); snap(f"a{i*2+1:03d}_sel")
    h.rel(30, 10, 3)
    for i in range(6):
        time.sleep(2); snap(f"b{i:03d}_moved")
finally:
    h.close()

#!/usr/bin/env python3
"""Campaign flow from NAME/map.sav: Lobos+SPACE, book icon, ? icon, thumbs-up page; shots+pointer vars every ~3 s.
usage: flow.py SRC OUT BUILD MACHINE"""
import sys, time
from pathlib import Path
ROOT = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2')
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools')
from mw2harness import Hatari
from stharness import MACHINE_TOS
src, name, bd, machine = sys.argv[1:5]
out = ROOT / "work/mapptr" / name; out.mkdir(parents=True, exist_ok=True)
h = Hatari(snapshot=str(ROOT/'work/mapptr'/src/'map.sav'), machine=machine, tos=MACHINE_TOS[machine], memsize_kb=int(__import__('os').environ.get('MEM','1024')), game_dir=ROOT / bd, extra=['--mmu','true'] if machine=='tt' else None)
def st():
    return dict(mode=h.peekw(0x700a), px=h.peekw(0x6fae), py=h.peekw(0x6fb2), f6fc2=h.peekw(0x6fc2), draw=h.peekw(0x62fa), ring=h.peekw(0x62fc), sav=h.peekw(0x6306), island=h.peekw(0xeb9c))
t0 = time.time(); n = [0]
def snap(tag):
    n[0] += 1
    h.shot(str(out / f"{n[0]:03d}_{tag}.png"))
    print(f"{time.time()-t0:6.1f}s {n[0]:03d}_{tag} vbl={h.vbl()} {st()}", flush=True)
def watch(tag, secs):
    t = time.time()
    while time.time() - t < secs:
        snap(tag); time.sleep(1.5)
try:
    time.sleep(3); snap("restored")
    h.goto(150, 280); snap("hover"); h.key("space")
    watch("lobos_page", 35)
    h.goto(230, 410); h.click(); watch("book", 30)
    h.goto(140, 415); h.click(); watch("q", 30)
    h.rel(20, 10, 2); watch("q_moved", 12)
finally:
    h.close()

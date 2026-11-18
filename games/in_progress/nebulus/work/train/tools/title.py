#!/usr/bin/env python3
"""T/E on the title screen: do they toggle anything, visible effect, carry into a new game?  usage: title.py LABEL GAMEDIR"""
import sys, time, struct
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/tools')
from pathlib import Path
from nebulus import Nebulus
G = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus'); SH = G / 'work/train/shots/gate'
label, game = sys.argv[1], Path(sys.argv[2]).resolve()
h = Nebulus(workdir=f'/tmp/strun-ntg-{label}', game=game)
def grab(addr, n):
    p = f'/tmp/ntg_{label}.bin'; Path(p).unlink(missing_ok=True)
    h.debug(f"savebin {p} ${addr:x} ${n:x}", 0.6)
    for _ in range(30):
        if Path(p).exists() and Path(p).stat().st_size == n: break
        time.sleep(0.2)
    d = Path(p).read_bytes(); Path(p).unlink(); return d
def S(tag):
    b = grab(0x76c00, 6); t = struct.unpack('>3H', grab(0x3ad98, 6)); st = struct.unpack('>4H', grab(0x3398c, 8)); run = struct.unpack('>H', grab(0x33938, 2))[0]
    print(f'[{label}] {tag}: blob prev={b[0]:02x} frz={b[2]:02x}{b[3]:02x} noen={b[4]:02x}{b[5]:02x} | timer {t} states {st} run {run} lastkey {grab(0x38498,1).hex()}', flush=True)
try:
    print(f'[{label}] boot_to_title', h.boot_to_title(timeout=120)); time.sleep(2)
    S('title'); h.shot(str(SH / f'{label}_t0_title.png'))
    h.key('t', hold=0.5); time.sleep(0.5); S('title, after T'); h.shot(str(SH / f'{label}_t1_T.png'))
    h.key('e', hold=0.5); time.sleep(0.5); S('title, after E'); h.shot(str(SH / f'{label}_t2_E.png'))
    h.key('t', hold=0.5); time.sleep(0.5); S('title, after T again')
    h.key('e', hold=0.5); time.sleep(0.5); S('title, after E again')
    # leave T and E ON and start a game: do the flags carry into it?
    h.key('t', hold=0.5); time.sleep(0.3); h.key('e', hold=0.5); time.sleep(0.5); S('title, T+E on')
    h.key('Right', hold=0.5); time.sleep(0.5); h.key('Control_R', hold=1.0); time.sleep(3.0)
    for i in range(4):
        S(f'new game {i}'); time.sleep(2.0)
    h.shot(str(SH / f'{label}_t3_game.png'))
finally:
    h.close()

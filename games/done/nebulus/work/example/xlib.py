"""Harness helpers for the example-campaign playtests (NebExamplePlay).  Import with work/editor on sys.path (ed.py: grab, W, poke)."""
import sys, os, time, struct, shutil, re
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor')
from ed import *
from pathlib import Path
X = G + 'work/example/'
GAME = Path('/tmp/neb_ex/game')

def K(h, k, n=1, hold=0.2, gap=0.4):
    for _ in range(n):
        h.key(k, hold=hold); time.sleep(gap)
def F(h, gap=0.9): K(h, 'Control_R', hold=0.35, gap=gap)

def gamedir_with(ovl_path, name):
    d = Path('/tmp/neb_ex') / name
    if d.exists(): shutil.rmtree(d)
    shutil.copytree(GAME, d)
    shutil.copy(ovl_path, d / 'NEBLEVEL.OVL')
    return d

def frog(h):
    return dict(x=W(h, 0x33a16), y=W(h, 0x33a18), st=W(h, 0x33a20), t=grab(h, 0x3ad98, 6).hex(), run=W(h, 0x33938), tower=W(h, 0x3390c), done=W(h, 0x33a46))

def wait_play(h, timeout=90):
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(1.5)
        if W(h, 0x33a20) == 0 and W(h, 0x33938) == 1: return True
    return False

#!/usr/bin/env python3
"""cold boot a game folder to the first race, shoot at the standing start, drive, shoot again.  usage: run_race.py GAMEDIR TAG"""
import sys, time
from pathlib import Path
G = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers')
sys.path.insert(0, str(G/'tools')); sys.path.insert(0, str(G.parent.parent.parent/'tools'))
from msr import Moonshine
gd, tag = sys.argv[1], sys.argv[2]
out = Path(__file__).resolve().parent/'shots'
h = Moonshine(game_dir=gd, workdir=f'/tmp/trackstudy_{tag}')
try:
    ok = h.boot_to_race()
    print('in_race', ok, 'vbl', h.vbl(), flush=True)
    for k in range(12):                       # in_race can fire on the title screen: SPACE until the race is set up ($23c0 = track stream pointer)
        if h.peekl(0x23c0) != 0 and h.peekw(0x100e) > 30: break
        h.keypress(57); time.sleep(6)
        print('wait race', k, 'vbl', h.vbl(), '23c0', hex(h.peekl(0x23c0)), '100e', h.peekw(0x100e), flush=True)
    time.sleep(3.0)
    print('102c', hex(h.peekw(0x102c)), '5ff8', h.peekw(0x5ff8), '130c', h.peekw(0x130c), '100e', h.peekw(0x100e), flush=True)
    for n in range(3):
        h.shot(str(out/f'{tag}_grid{n}.png')); time.sleep(0.5)
    h.debug('m $23c0 4'); print(h.debug('m $1bb0 8'), h.debug('m $23c0 4'), flush=True)
    print(h.debug('m $1bbc 64'), flush=True)
    h.drive(True)
    for k in range(4):
        time.sleep(8)
        print('drive', k, 'vbl', h.vbl(), '5ff8', h.peekw(0x5ff8), '130c', h.peekw(0x130c), flush=True)
        h.shot(str(out/f'{tag}_drive{k}.png'))
    h.drive(False)
finally:
    h.close()

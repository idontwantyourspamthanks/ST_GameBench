"""mkenemy.py OUT.sav: cold boot (default build + p7_skip? no: plain default build), Training/Mortars/Bombers OFF, wait for the enemy
object (slot $1ce02, flag $26 > 0) and save a 1 MB snapshot at that moment (unpatched code in RAM: apply the live sets over it)."""
import sys, time, struct
sys.path[:0] = ['/home/ryan/Code/AtariST/gamebench/tools', '/home/ryan/Code/AtariST/gamebench/games/midwinter/tools']
from mw1 import MW1
from stharness import TOS
from pathlib import Path
out, game = sys.argv[1], sys.argv[2]
h = MW1(snapshot=None, memsize_kb=1024, tos=TOS['1.62'])
try:
    h.boot_to_game('M', training=False, mortars=False, bombers=False)
    t = time.time()
    while time.time() - t < 300:
        slot = h.peek(0x1ce02, 0x2c)
        flag = struct.unpack('>h', slot[0x26:0x28])[0]
        if flag > 0:
            print('enemy active', slot.hex()); h.savemem(out); print('saved', out); break
    else:
        print('no enemy')
finally:
    h.close()

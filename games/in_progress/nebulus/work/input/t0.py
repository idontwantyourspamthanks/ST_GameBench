import sys, time
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0, 'tools')
from nebulus import Nebulus
h = Nebulus(snapshot='work/snapshots/1mb_tower.sav', workdir='/tmp/strun-ni2')
try:
    time.sleep(2)
    print(h.vbl())
    print(hex(h.peekw(0x3ad98)), hex(h.peekw(0x3390c)))
    h.shot('work/input/s/t0.png')
    print(h.fps(100))
    print(h.debug('m $38498 2'))
finally:
    h.close()

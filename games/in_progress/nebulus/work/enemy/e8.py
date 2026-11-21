"""Hatari confirmation: 8 enemy markers in one area -> how many slots are active (work/notes/enemies.md).
run: HOME=/tmp/nebenemy/home python3 work/enemy/e8.py [value-hex-default 30]"""
import sys
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/level/tools')
from nl2 import *
val=int(sys.argv[1],16) if len(sys.argv)>1 else 0x60
h=Nebulus(workdir='/tmp/nebenemy')
def slots():
    d=grab(h,0x33944,0x80,'sl'); W=lambda o,s: struct.unpack('>H',d[o+2*s:o+2*s+2])[0]
    return [(W(0,s),W(0xc,s),W(0x48,s),W(0x6c,s)) for s in range(4)]
try:
    h.boot_to_title(); time.sleep(2); cheat(h); time.sleep(1)
    h.key('Right',hold=0.5); time.sleep(0.5); h.key('Control_R',hold=1.0); time.sleep(4)
    h.key('F1',hold=0.6); time.sleep(1.0)   # restart: fresh grid decode
    ang=range(0,8); row=5
    poke(h,0x327f0+0x100*6+row,' '.join([f'{val:02x}']*8))   # one column, 8 consecutive rows (one poke = fast)
    poke(h,0x3393c,'00 03 27 f0')      # rewind the scan pointer
    for i in range(8):
        time.sleep(0.05)
        print('t',i,'scan ptr',grab(h,0x3393c,4,'p').hex(),'slots(x,y,state,kind)',slots(),flush=True)
    print('grid col 6 rows 5..12',grab(h,0x327f0+0x600+row,8,'g').hex(),flush=True)
    h.shot('/tmp/nebenemy/e8.png')
finally:
    h.close()

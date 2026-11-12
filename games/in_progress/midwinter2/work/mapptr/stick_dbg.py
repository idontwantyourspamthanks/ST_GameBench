import sys, time
from pathlib import Path
ROOT = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2')
sys.path.insert(0, str(ROOT / "tools"))
from mw2harness import Hatari
h = Hatari(snapshot=str(ROOT/'work/snapshots/corridor_agent.sav'), memsize_kb=2048, extra=['--joy1','keys'])
def pos(): return h.peekw(0x6fae), h.peekw(0x6fb2)
try:
    time.sleep(3)
    h.debug('w $eb76 $ff $ff $00 $00 $00 $00')
    print('mode', hex(h.peekw(0xeb76)), hex(h.peekw(0xeb7a)), pos())
    for key, t in (('Right',0.5),('Right',0.3),('Down',0.5),('Left',0.2),('Up',0.4),('Right',0.1)):
        h._xdo('keydown','--window',h.win,key); time.sleep(t); h._xdo('keyup','--window',h.win,key); time.sleep(0.6)
        print(key,t,pos(), hex(h.peekw(0x75a8)))
finally: h.close()

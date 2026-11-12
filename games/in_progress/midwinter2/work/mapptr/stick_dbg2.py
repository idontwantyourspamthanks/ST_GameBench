import sys, time
from pathlib import Path
ROOT = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2')
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools')
from mw2harness import Hatari
from stharness import MACHINE_TOS
h = Hatari(snapshot=str(ROOT/'work/mapptr/tl_tt_fix/map.sav'), machine='tt', tos=MACHINE_TOS['tt'], memsize_kb=2048, game_dir=ROOT/'build/MW2MapPtr', extra=['--mmu','true','--joy1','keys'])
def pos(): return h.peekw(0x6fae), h.peekw(0x6fb2)
try:
    time.sleep(3)
    h.debug('w $eb76 $ff $ff $00 $00 $00 $00'); h.debug('w $eb7a $00 $00')
    print('mode', hex(h.peekw(0xeb76)), hex(h.peekw(0xeb7a)), pos(), 'vbl', h.vbl())
    for key, t in (('Right',0.5),('Right',0.3),('Down',0.5),('Left',0.2),('Up',0.4),('Right',0.1)):
        v0=h.vbl()
        h._xdo('keydown','--window',h.win,key); time.sleep(t); h._xdo('keyup','--window',h.win,key); time.sleep(0.6)
        print(key,t,pos(), hex(h.peekw(0x75a8)), 'vbls', h.vbl()-v0)
finally: h.close()

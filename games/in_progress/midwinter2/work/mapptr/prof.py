import sys, time, collections
from pathlib import Path
ROOT = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2')
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools')
from mw2harness import Hatari
from stharness import MACHINE_TOS
src, bd = sys.argv[1:3]
h = Hatari(snapshot=str(ROOT/'work/mapptr'/src/'map.sav'), machine='ste', tos=MACHINE_TOS['ste'], memsize_kb=1024, game_dir=ROOT/bd)
try:
    time.sleep(3)
    print('fps', h.fps(250))
    p = h.profile(250)
    tot = sum(c for a,c in p)
    b = collections.Counter()
    for a,c in p: b[a>>8]+=c
    for k,v in b.most_common(15): print(f'{k<<8:06x} {100*v/tot:.1f}%')
    print('total', tot)
    for a in (0x67aa,0x770e,0x7712,0x6306,0x6312,0x62fa,0x6fc2,0x700a,0x540e):
        print(hex(a), hex(h.peekw(a)), hex(h.peekw(a+2)))
    print(h.debug('m $6306 $18'))
finally:
    h.close()

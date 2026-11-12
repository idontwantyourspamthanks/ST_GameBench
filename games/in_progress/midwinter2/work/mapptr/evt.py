import sys, time, re
from pathlib import Path
ROOT = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2')
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools')
from mw2harness import Hatari
from stharness import MACHINE_TOS
src, bd = sys.argv[1:3]
h = Hatari(snapshot=str(ROOT/'work/mapptr'/src/'map.sav'), machine='tt', tos=MACHINE_TOS['tt'], memsize_kb=2048, game_dir=ROOT/bd, extra=['--mmu','true'])
try:
    time.sleep(3)
    v = h.vbl()
    cd = h.R / 'cd_draw.txt'; cd.write_text('info video\nm $67aa 4\n')
    cf = h.R / 'cd_flip.txt'; cf.write_text('info video\nm $770e 8\n')
    h.debug('b all', 0.3)
    lo, hi = v + 500, v + 503
    h.cmd(f'hatari-debug b pc = $266d4 && VBL > {lo} && VBL < {hi} :trace :file {cd}')
    h.cmd(f'hatari-debug b pc = $26ea2 && VBL > {lo} && VBL < {hi} :trace :file {cf}')
    time.sleep(14)
    h.debug('b all', 0.3)
    txt = h._logtext()
    i = txt.find('Breakpoint')
    print(txt[i-200:i+6000] if i >= 0 else txt[-3000:])
finally: h.close()

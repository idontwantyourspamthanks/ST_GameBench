"""cold_hd.py dir tag machine tos mem : HD cold boot to the Lobos 3D view; print MWPO marker + state"""
import sys, time
from pathlib import Path
ROOT = Path('/home/ryan/Code/AtariST/midwinter2')
sys.path.insert(0, str(ROOT / 'tools'))
from mw2harness import Hatari
B = Path.home() / "Emulators/BIOS/AtariST"
TOS = {'162': B / "TOS v1.62 (1990)(Atari Corp)(STE)(GB)[STE TOS, Rev 2].img",
       '104': B / "TOS v1.04 (1989)(Atari Corp)(Mega ST)(GB)[Rainbow TOS].img"}
src, tag, machine, tos, mem = sys.argv[1:6]
h = Hatari(snapshot=None, memsize_kb=int(mem), machine=machine, tos=TOS[tos], game_dir=Path(src))
try:
    p = h.boot_to_game('M')
    print('MWPO', h.debug('m $b2ff8 4').strip().splitlines()[-1])
    print('6220=%x 700a=%x' % (h.peekw(0x6220), h.peekw(0x700A)))
    h.shot(str(ROOT / f'work/credit/{tag}_3d.png'))
finally:
    h.close()

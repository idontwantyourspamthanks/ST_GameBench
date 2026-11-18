"""Make a pre-window snapshot (START still before SR=$2700, VBL ~2500) of a cold boot, patched or orig."""
import sys
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/ikbd')
from lib import *
variant = sys.argv[1]; vbl = int(sys.argv[2]) if len(sys.argv) > 2 else 2500
h = boot(variant, f'snap-{variant}')
try:
    h.cmd(f'hatari-debug b VBL > {vbl} :trace :once')
    m, n = wait_log(h, r'matched 1 times', 0, timeout=120)
    h.savemem(str(G/f'work/ikbd/snap_{variant}.sav'))
    print('saved', variant, 'at VBL >', vbl, 'size', (G/f'work/ikbd/snap_{variant}.sav').stat().st_size)
finally:
    h.close()

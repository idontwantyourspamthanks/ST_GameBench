import sys, time
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0, 'tools')
from nebulus import Nebulus
from pathlib import Path
out = Path('work/input/shots'); out.mkdir(exist_ok=True)
h = Nebulus(workdir='/tmp/strun-ni1')
try:
    h.boot_to_game()
    h.shot(str(out/'a0.png'))
    # hold fire (Right Ctrl) for 3 s
    h._xdo('keydown','--window',h.win,'Control_R')
    for i in range(8):
        time.sleep(1.0); h.shot(str(out/f'hold_{i}.png'))
    h._xdo('keyup','--window',h.win,'Control_R')
    for i in range(6):
        time.sleep(2.0); h.shot(str(out/f'after_{i}.png'))
finally:
    h.close()

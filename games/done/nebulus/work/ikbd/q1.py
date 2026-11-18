import sys
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/ikbd')
from lib import *
v=sys.argv[1]
h = boot(v, '', snapshot=str(G/f'work/ikbd/snap_{v}.sav'))
try:
    for i in range(4):
        print(h.debug('e VBL', 0.3).strip().splitlines()[-1], '|', [l for l in h.debug('r', 0.3).splitlines() if 'SR=' in l or l.strip().startswith('0')][-3:])
        time.sleep(0.5)
finally:
    h.close()

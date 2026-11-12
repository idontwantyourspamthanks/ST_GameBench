import sys, time, struct
from pathlib import Path
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/tools')
from mw2harness import Hatari
h = Hatari(snapshot='/home/ryan/Code/AtariST/midwinter2/work/snapshots/1mb_ingame_foot.sav', memsize_kb=1024)
try:
    h.shot('/tmp/fire_0.png')
    for i in range(3):
        h.key('space', hold=0.3); time.sleep(1.0)
    for i in range(6):
        time.sleep(1.5)
        h.shot(f'/tmp/fire_{i+1}.png')
        out = h.debug('m $3cee 288', 0.8)
        print(i, out[-600:].replace('\n',' | ')[:500])
finally:
    h.close()

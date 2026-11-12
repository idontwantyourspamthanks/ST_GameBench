"""Enter a raid from the map snapshot a cold boot saved (cold.py), then pad tests.
usage: raid_from_map.py TAG MAPTAG X Y SEQ [shotname]"""
import sys, time
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/work/jagpad')
from jt import *
import mw2raids
tag, maptag, x, y, seq = sys.argv[1:6]
h = Hatari(snapshot=str(G / 'work/snapshots' / f'jag_{maptag}_map.sav'), memsize_kb=1024, game_dir=G / 'build/jag_a', extra=PADX)
try:
    time.sleep(4)
    print('marker', memb(h, 0xb2ff8, 4))
    r = mw2raids.enter_raid(h, int(x), int(y))
    print(tag, 'entered', r, flush=True)
    time.sleep(5)
    jmode(h); time.sleep(2)
    S(h, 'J idle')
    battery(h, seq.split(','))
    d = memb(h, 0xb9ee0, 1)
    print(tag, 'FLAG', d[0], 'PASS' if d[0] == 1 else 'FAIL')
    print(tag, 'bus-error log lines:', bus_errors(h)[:6])
    h.shot(str(G / 'work/jagpad' / f'{tag}_end.png'))
finally:
    h.close()

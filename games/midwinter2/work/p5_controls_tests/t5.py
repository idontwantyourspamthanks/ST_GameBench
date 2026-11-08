import sys; sys.path.insert(0,'/tmp/p5')
from lib import *
from pathlib import Path
h=Hatari(snapshot=None, memsize_kb=1024, game_dir=ROOT/'build/p5')
try:
    h.boot_to_game('M')
    print('marker MWPO/MWPF @ $b2ff8:', h.debug("m $b2ff8 4",0.6).strip().splitlines()[-1])
    print('p5 sites:', h.debug("m $262c8 8",0.6).strip().splitlines()[-1], '|', h.debug("m $34152 6",0.6).strip().splitlines()[-1])
    print('mode:', h.debug("m $eb76 6",0.6).strip().splitlines()[-1], '$6220=',hex(h.peekw(0x6220)),'$700a=',hex(h.peekw(0x700a)))
    start_log(h)
    time.sleep(2)
    h.rel(-150,0)
    time.sleep(6)
    rows=stop_log(h)
    for r in rows:
        hd=r.get(0x6742)
        if hd is None: continue
        print(f" vbl {r['vbl']} heading {hd:4d} $6766={sgn(r.get(0x6766,0))} $6fb6hi={sgn(r.get(0x6fb6,0))}")
finally:
    h.close()

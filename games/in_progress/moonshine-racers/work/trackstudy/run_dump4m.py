#!/usr/bin/env python3
"""cold boot the shipped-default patched HD build at STE 4 MB, SPACE to the race, dump RAM + low-RAM facts."""
import sys, time, struct
from pathlib import Path
G = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers')
sys.path.insert(0, str(G/'tools')); sys.path.insert(0, str(G.parent.parent.parent/'tools'))
from msr import Moonshine
mem = int(sys.argv[2]); tag = sys.argv[1]
h = Moonshine(game_dir=str(G/'build/hd'), workdir=f'/tmp/trackstudy_{tag}', memsize_kb=mem)
try:
    ok = h.boot_to_race()
    for k in range(14):
        if h.peekl(0x23c0) != 0 and h.peekw(0x100e) > 30: break
        h.keypress(57); time.sleep(6)
        print('wait', k, h.vbl(), hex(h.peekl(0x23c0)), flush=True)
    time.sleep(5)
    print('marker', h.debug('m $b2700 8').strip(), flush=True)
    for a, n in ((0x42e, 4), (0x436, 4), (0x2dc, 4), (0x4ba, 4), (0x5a0, 4)):
        print(h.debug(f'm ${a:x} {n}').strip(), flush=True)
    out = str(Path(__file__).resolve().parent/f'ram_{tag}.bin')
    h.dump(out, 0, mem*1024); time.sleep(3)
    print('dumped', out, flush=True)
finally:
    h.close()

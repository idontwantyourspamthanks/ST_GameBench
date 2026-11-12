import sys, time
from jlib import *
h = MW1(snapshot=None, game_dir=str(GAME/'build'/'jag'), machine='falcon', memsize_kb=4096, extra=PAD)
try:
    print('options', h.boot_to_options(timeout=300), flush=True)
    S = Sampler(h, [(0xb6bf0, 10), (0xb2ff8, 4), (0x2c178, 2), (0x8, 4), (0x70, 4)])
    def show(t):
        r = S(); print(t, 'vbl', r['vbl'], 'PAD', r[0xb6bf0].hex(), 'MWPO', r[0xb2ff8], '2c178', r[0x2c178].hex(), 'v8', r[8].hex(), 'v70', r[0x70].hex(), flush=True)
    show('before')
    h.debug('w $2c178 $ff $ff', 0.5)
    for i in range(4):
        time.sleep(1.0); show(f'after {i}')
    print(h.debug('r', 1.0)[-900:])
    h.shot('/tmp/falcon_dbg.png')
finally:
    h.close()

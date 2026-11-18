"""Cold boot (patched or stock game dir), enable the HELLOIAMJMP cheat flag, F2..F8 in the tower, snapshot each tower at its start.
usage: mksnap_towers.py GAMEDIR OUTPREFIX [machine]"""
from lp import *
game, out = sys.argv[1], sys.argv[2]; machine = sys.argv[3] if len(sys.argv) > 3 else 'ste'
h = mk(game, '/tmp/lp/w_mk_' + Path(out).name, machine)
try:
    print('boot', boot_tower(h, machine))
    h.debug('w $33a40 0 1', 0.3)
    h.savemem(f'{out}_t1.sav')
    for k in range(2, 9):
        h.key(f'F{k}', hold=0.4)
        t0 = time.time()
        while time.time() - t0 < 40:
            time.sleep(1.0)
            if w16(h, 0x3390c) == k - 1 and w16(h, 0x33a20) == 0 and w16(h, 0x3ad98) != 0 and w16(h, 0x33938) == 1: break
        time.sleep(1.0)
        print(k, 'tower', w16(h, 0x3390c), 'state', w16(h, 0x33a20), 'timer', hex(w16(h, 0x3ad98)), 'x,y', w16(h, 0x33a16), w16(h, 0x33a18), flush=True)
        h.savemem(f'{out}_t{k}.sav')
finally:
    h.close()

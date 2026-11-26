"""Fast per-tower snapshots at the first loop of the tower (frog alive, standing): usage mksnap2.py GAMEDIR OUTPREFIX machine T1 T2 ..."""
from lp import *
game, out, machine = sys.argv[1], sys.argv[2], sys.argv[3]; towers = [int(x) for x in sys.argv[4:]]
h = mk(game, '/tmp/nlm/w_mk2_' + Path(out).name, machine)
try:
    print('boot', boot_tower(h, machine), flush=True)
    h.debug('w $33a40 0 1', 0.3)
    h.debug('w $3792c $4e $75', 0.2); h.debug('w $3398c 0 0 0 0 0 0 0 0', 0.2)   # spawn routine = rts: frog survives until the snapshot; ride2.py re-enables it
    for k in towers:
        # arm: first loop-top poll with the new tower index, state 0, timer running -> snapshot is taken by the harness right after (CPU is stopped at the bp)
        h.key(f'F{k}', hold=0.4)
        t0 = time.time()
        while time.time() - t0 < 60:
            if w16(h, 0x3390c) == k - 1 and w16(h, 0x33a20) == 0 and w16(h, 0x33938) == 1 and w16(h, 0x33a18) == 8: break
        h.savemem(f'{out}_t{k}.sav')
        print(k, 'tower', w16(h, 0x3390c), 'state', w16(h, 0x33a20), 'xy', w16(h, 0x33a16), w16(h, 0x33a18), 'c0', ' '.join('%02x' % b for b in rd(h, 0x327f0, 4)), flush=True)
finally:
    h.close()

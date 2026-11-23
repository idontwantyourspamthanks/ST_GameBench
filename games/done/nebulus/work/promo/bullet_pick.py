"""Pick the bullet-clip attempt with the Unicorn sim (== Hatari, work/notes/shotmiss.md): stock = the shot misses the ball, np_shot = it kills it.
Prints, for stock and fix, the per-attempt outcome (ball state 4 = dying, frog player state) for fire delays 0..6 loops after the scene pokes."""
import sys, json
HERE = '/home/ryan/Code/AtariST/gamebench/games/done/nebulus/work/'
sys.path.insert(0, HERE + 'shotmiss'); sys.path.insert(0, HERE + 'input')
from sim import *
import hatt
FIX = [(0x3b87a, b'\x66\x08\x48\x80')]
def run(at, fix, delay, n=60):
    s = Sim('/tmp/shot_ledge.bin')
    for a, b in fix: s.uc.mem_write(a, bytes(b))
    for a, b in hatt.attempt_pokes(at, False): s.uc.mem_write(a, b)
    s.uc.mem_write(0x3ad98, struct.pack('>HHH', 0x48, 0x48, 0x48))
    rows = []
    for i in range(n):
        s.wb(0x38498, 0x80 if delay <= i < delay + 2 else 0)
        loop(s, extra=False)
        b = slot(s, 0)
        rows.append((i, b['x'], b['y'], b['st'], s.rw(PST), s.rw(PX), slot(s, SHOT)['st']))
    return rows
if __name__ == '__main__':
    d = json.load(open(HERE + 'shotmiss/attempts.json'))
    for idx, at in enumerate(d['targeted_miss']):
        for delay in (0, 2, 4):
            st, fx = run(at, [], delay), run(at, FIX, delay)
            hit = lambda r: any(x[3] == 4 for x in r)
            dead = lambda r: sorted({x[4] for x in r})
            print(idx, at['bx'], at['cnt'], at['spd'], at['fx'], 'delay', delay, 'stock ballDies', hit(st), 'pst', dead(st), '| fix ballDies', hit(fx), 'pst', dead(fx))

"""Natural-spawn bullet scene in the sim: the spawner (not a poked slot) creates the ball from the tower-1 marker `$30` at col 9 row 15 (x=76),
the frog starts outside the ball's 32-unit trigger range, walks left into it, then fires.  Search (start x, walk start, walk loops, fire loop)
for: stock misses and the ball hits the frog; np_shot kills the ball."""
import sys, struct, itertools
HERE = '/home/ryan/Code/AtariST/gamebench/games/done/nebulus/work/'
sys.path.insert(0, HERE + 'shotmiss'); sys.path.insert(0, HERE + 'input')
from sim import *
FIX = [(0x3b87a, b'\x66\x08\x48\x80')]
LEFT, FIRE = 0x04, 0x80
def setup(s, fix, x0):
    for a, b in fix: s.uc.mem_write(a, bytes(b))
    for r in (15, 16): s.wb(cell(12, r), 0)
    s.ww(0x3792c, 0x3039)
    s.uc.mem_write(0x3393c, struct.pack('>I', cell(0, 15)))
    for k in range(4): s.ww(fld(k, F_ST), 0)
    s.ww(fld(SHOT, F_ST), 0); s.ww(fld(SHOT, F_CNT), -1)
    s.uc.mem_write(0x3ad98, struct.pack('>HHH', 0x48, 0x48, 0x48))
    s.ww(PX, x0); s.ww(PY, 60); s.ww(PST, 0); s.ww(PSTEP, 0); s.ww(PDIR, 0)
def run(fix, x0, w0, wn, f0, n=110):
    s = Sim('/tmp/shot_ledge.bin'); setup(s, fix, x0)
    rows = []
    for i in range(n):
        v = (LEFT if w0 <= i < w0 + wn else 0) | (FIRE if f0 <= i < f0 + 2 else 0)
        s.wb(0x38498, v)
        loop(s, extra=True)
        b = slot(s, 0)
        rows.append((i, b['x'], b['y'], b['st'], b['spd'], s.rw(PX), s.rw(PY), s.rw(PST), slot(s, SHOT)['st']))
    return rows
if __name__ == '__main__':
    if len(sys.argv) > 1:
        a = list(map(int, sys.argv[1:6])); f = FIX if sys.argv[6] == 'fix' else []
        for r in run(f, *a): print(r)
        sys.exit()
    for x0, w0, wn, f0 in itertools.product((110, 111), (8, 12, 16), (3, 4, 5, 6), range(16, 56)):
        st = run([], x0, w0, wn, f0); fx = run(FIX, x0, w0, wn, f0)
        dies = lambda r: any(x[3] == 4 for x in r)
        hurt = lambda r: any(x[7] == 7 for x in r)
        if (not dies(st)) and hurt(st) and dies(fx) and not hurt(fx):
            print('CAND', x0, w0, wn, f0, 'frog x end', st[-1][5], fx[-1][5])
